"""
Diarization pipeline for podcast episodes.
Uses pyannote/audio 4.x to identify speakers in each episode.
Saves speaker segments to the chunks table in the database.

Idempotent: skips episodes already diarized.

Strategy:
1. Try single-pass diarization (fast, works for most episodes)
2. If CUDA OOM detected, fall back to chunked processing via ffmpeg:
   - Audio is split into temporary MP3 chunks
   - Each chunk is diarized independently
   - Speakers are kept distinct across chunks (no re-identification yet)
"""

import os
import json
import shutil
import subprocess
from pathlib import Path

import torch
import soundfile as sf
import numpy as np
from loguru import logger
from pyannote.audio import Pipeline
from sqlalchemy.orm import Session
import gc
import time

from config import settings
from src.ingestion.database import Episode, Chunk, Transcription, get_engine


# ---------- Pipeline loading ----------

def load_pipeline(device: str) -> Pipeline:
    """
    Loads the pyannote diarization pipeline.

    Args:
        device: Device to run on (cuda or cpu).

    Returns:
        Loaded pyannote Pipeline instance.
    """
    logger.info(f"Loading pyannote pipeline: {settings.DIARIZATION_MODEL} on {device}")
    pipeline = Pipeline.from_pretrained(
        settings.DIARIZATION_MODEL,
        token=settings.HF_TOKEN,
    )
    pipeline.to(torch.device(device))
    pipeline.embedding_batch_size = settings.DIARIZATION_EMBEDDING_BATCH_SIZE
    logger.success("Pipeline loaded successfully")
    return pipeline


# ---------- OOM detection ----------

def safe_cuda_cleanup(wait_seconds: int = 10) -> None:
    """
    Safely attempts to recover CUDA memory/state after OOM.

    CUDA can enter an unstable state after OOM, so every cleanup
    operation must be guarded individually.
    """
    if not torch.cuda.is_available():
        return

    logger.warning(
        f"Waiting {wait_seconds}s for CUDA memory recovery before retry"
    )

    time.sleep(wait_seconds)

    try:
        gc.collect()
    except Exception as e:
        logger.warning(f"gc.collect failed: {e}")

    try:
        torch.cuda.synchronize()
    except Exception as e:
        logger.warning(f"cuda synchronize failed: {e}")

    try:
        torch.cuda.empty_cache()
    except Exception as e:
        logger.warning(f"cuda empty_cache failed: {e}")

    try:
        torch.cuda.ipc_collect()
    except Exception as e:
        logger.warning(f"cuda ipc_collect failed: {e}")

def is_oom_error(exc: Exception) -> bool:
    """
    Checks if an exception is a CUDA out-of-memory error or its known
    masked variants (like 'GET was unable to find an engine').

    Args:
        exc: The exception to inspect.

    Returns:
        True if it looks like a memory issue.
    """
    msg = str(exc).lower()
    oom_signatures = [
        "out of memory",
        "cuda error: out of memory",
        "get was unable to find an engine",
        "cuda out of memory",
        "batch_size",
        "memory error",
    ]
    return any(sig in msg for sig in oom_signatures)


# ---------- Single-pass diarization ----------

def diarize_single_pass(
    pipeline: Pipeline,
    audio_path: Path,
) -> tuple[list[dict], np.ndarray]:
    """
    Runs single-pass diarization on the entire audio file.

    Args:
        pipeline: Loaded pyannote Pipeline instance.
        audio_path: Path to MP3 audio file.

    Returns:
        Tuple of (segments list, speaker embeddings array).

    Raises:
        RuntimeError: If diarization fails (including OOM cases).
    """
    temp_wav = audio_path.with_suffix(".diarization.wav")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(audio_path),
        "-ac", "1",          # mono
        "-ar", "16000",      # 16kHz
        "-vn",
        "-loglevel", "error",
        str(temp_wav),
    ]

    subprocess.run(ffmpeg_cmd, check=True)

    waveform, sample_rate = sf.read(
        str(temp_wav),
        always_2d=True,
    )

    # Convert stereo -> mono to reduce VRAM usage
    if waveform.shape[1] > 1:
        waveform = waveform.mean(axis=1, keepdims=True, dtype=np.float32)

    waveform = torch.tensor(waveform.T, dtype=torch.float32)
    waveform = waveform.contiguous()

    audio_input = {"waveform": waveform, "sample_rate": sample_rate}

    with torch.inference_mode():
        diarization = pipeline(
            audio_input,
            min_speakers=settings.DIARIZATION_MIN_SPEAKERS,
            max_speakers=settings.DIARIZATION_MAX_SPEAKERS,
        )

    annotation = diarization.speaker_diarization
    embeddings = np.asarray(diarization.speaker_embeddings)
    del diarization
    del waveform
    gc.collect()

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
            "duration": round(turn.end - turn.start, 2),
        })
        
    try:
        temp_wav.unlink(missing_ok=True)
    except Exception:
        pass

    return segments, embeddings


# ---------- Chunked diarization (fallback) ----------

def extract_audio_chunks_with_ffmpeg(
    audio_path: Path,
    episode_id: str,
) -> list[dict]:
    """
    Extracts audio chunks as temporary MP3 files using ffmpeg.

    Each chunk gets its own file, allowing independent processing
    without holding the full audio in memory.

    Args:
        audio_path: Path to source MP3 file.
        episode_id: Used to name the temporary directory.

    Returns:
        List of chunk metadata dicts with: path, start_offset, index.
    """
    # Probe duration via ffprobe
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    total_duration_s = float(result.stdout.strip())

    chunk_s = settings.DIARIZATION_CHUNK_DURATION_SECONDS
    overlap_s = settings.DIARIZATION_CHUNK_OVERLAP_SECONDS
    stride_s = chunk_s - overlap_s

    temp_dir = Path(settings.DIARIZATION_TEMP_DIR) / str(episode_id)
    temp_dir.mkdir(parents=True, exist_ok=True)

    chunks = []
    start_s = 0.0
    index = 0

    while start_s < total_duration_s:
        end_s = min(start_s + chunk_s, total_duration_s)
        duration_s = end_s - start_s

        chunk_path = temp_dir / f"chunk_{index:03d}.mp3"

        # ffmpeg extracts the chunk
        # -ss / -t: start and duration
        # -c copy: no re-encoding (super fast)
        # -y: overwrite
        # -loglevel error: silent unless error
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-ss", str(start_s),
            "-t", str(duration_s),
            "-i", str(audio_path),
            "-c", "copy",
            str(chunk_path),
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        chunks.append({
            "path": chunk_path,
            "start_offset": start_s,
            "index": index,
        })

        if end_s == total_duration_s:
            break
        start_s += stride_s
        index += 1

    logger.info(
        f"Extracted {len(chunks)} audio chunks to {temp_dir} "
        f"(chunk_duration={chunk_s}s, overlap={overlap_s}s)"
    )
    return chunks


def cleanup_temp_chunks(episode_id: str) -> None:
    """Removes the temporary diarization chunks directory."""
    temp_dir = Path(settings.DIARIZATION_TEMP_DIR) / str(episode_id)
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug(f"Cleaned up temp chunks at {temp_dir}")


def diarize_chunked(
    pipeline: Pipeline,
    audio_path: Path,
    episode_id: str,
) -> tuple[list[dict], np.ndarray]:
    """
    Diarizes a long audio file by splitting it into MP3 chunks via ffmpeg
    and processing each chunk independently.

    Speakers are kept distinct across chunks (no re-identification).
    Chunk N's local speakers (SPEAKER_00..SPEAKER_NN) are mapped to
    global labels by adding an offset based on previous chunks' counts.

    Args:
        pipeline: Loaded pyannote Pipeline instance.
        audio_path: Path to source MP3 file.
        episode_id: Episode ID (for temp file organization).

    Returns:
        Tuple of (merged segments with global speaker labels, embeddings).
    """
    chunks = extract_audio_chunks_with_ffmpeg(audio_path, episode_id)
    total_chunks = len(chunks)

    global_segments = []
    global_embeddings_list = []
    speaker_offset = 0  # how many global speakers have been seen so far

    try:
        for chunk_meta in chunks:
            i = chunk_meta["index"]
            logger.info(
                f"  Diarizing chunk {i + 1}/{total_chunks} "
                f"(offset={chunk_meta['start_offset']:.0f}s)"
            )

            chunk_segments, chunk_embeddings = diarize_single_pass(
                pipeline,
                chunk_meta["path"],
            )

            # Build mapping: local SPEAKER_XX → global SPEAKER_YY
            local_speakers = sorted({seg["speaker"] for seg in chunk_segments})
            local_to_global = {}
            for local_idx, local_label in enumerate(local_speakers):
                global_idx = speaker_offset + local_idx
                local_to_global[local_label] = f"SPEAKER_{global_idx:02d}"

            # Apply time offset and remap speakers
            time_offset = chunk_meta["start_offset"]
            for seg in chunk_segments:
                global_segments.append({
                    "start": round(seg["start"] + time_offset, 2),
                    "end": round(seg["end"] + time_offset, 2),
                    "speaker": local_to_global[seg["speaker"]],
                    "duration": seg["duration"],
                })

            # Append embeddings in same order as local_speakers
            if len(chunk_embeddings) > 0:
                global_embeddings_list.append(chunk_embeddings)

            speaker_offset += len(local_speakers)

            safe_cuda_cleanup(wait_seconds=0)

        # Sort by start time
        global_segments.sort(key=lambda s: s["start"])

        # Stack embeddings if any
        if global_embeddings_list:
            global_embeddings = np.vstack(global_embeddings_list)
        else:
            global_embeddings = np.array([])

        logger.info(
            f"Chunked diarization complete: {speaker_offset} unique speakers "
            f"across {total_chunks} chunks, {len(global_segments)} total segments"
        )
        return global_segments, global_embeddings

    finally:
        # Always clean up temp files, even on failure
        cleanup_temp_chunks(episode_id)


# ---------- Main per-episode entry point ----------

def diarize_episode(
    pipeline: Pipeline,
    audio_path: Path,
    episode_id: str,
) -> tuple[list[dict], np.ndarray, Pipeline]:
    """
    Diarizes an episode using smart fallback strategy:
    1. Try single-pass diarization
    2. If OOM, fall back to chunked diarization via ffmpeg

    Args:
        pipeline: Loaded pyannote Pipeline instance.
        audio_path: Path to MP3 audio file.
        episode_id: Episode ID (for temp file organization).

    Returns:
        Tuple of (segments list, speaker embeddings array).

    Raises:
        RuntimeError: If both single-pass and chunked strategies fail.
    """
    safe_cuda_cleanup()

    # Try single-pass first
    try:
        logger.info("Attempting single-pass diarization")
        segments, embeddings = diarize_single_pass(pipeline, audio_path)

        speakers = sorted({seg["speaker"] for seg in segments})
        logger.info(f"Detected {len(speakers)} speakers: {speakers}")
        logger.info(f"Total segments: {len(segments)}")

        return segments, embeddings, pipeline

    except Exception as e:
        if not is_oom_error(e):
            raise

        logger.warning(f"Single-pass failed with OOM: {e}")
        logger.warning("Falling back to chunked diarization via ffmpeg")

        logger.warning("Releasing corrupted CUDA state")

        try:
            del pipeline
        except Exception:
            pass

        safe_cuda_cleanup(wait_seconds=15)

        logger.warning(
            "CUDA context corrupted after OOM. "
            "Reloading fallback pipeline on CPU."
        )

        pipeline = load_pipeline("cpu")

    # Fallback: chunked
    segments, embeddings = diarize_chunked(
        pipeline,
        audio_path,
        episode_id,
    )
    speakers = sorted({seg["speaker"] for seg in segments})
    logger.info(f"Detected {len(speakers)} speakers (chunked): {speakers}")
    logger.info(f"Total segments: {len(segments)}")
    return segments, embeddings, pipeline


# ---------- Utility: audio path resolution ----------

def get_audio_path(episode: Episode, audio_dir: str) -> Path | None:
    """Finds the audio file for an episode on disk."""
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in episode.title
    )[:80].strip()

    audio_path = Path(audio_dir) / f"{safe_title}.mp3"

    if not audio_path.exists():
        logger.warning(f"Audio file not found: {audio_path.name}")
        return None

    return audio_path


# ---------- Persistence ----------

def save_diarization(
    engine,
    episode: Episode,
    segments: list[dict],
    embeddings: np.ndarray,
) -> None:
    """Saves diarization segments to the chunks table."""
    with Session(engine) as session:
        transcription = session.query(Transcription).filter(
            Transcription.episode_id == episode.id
        ).first()

        transcription_id = transcription.id if transcription else None

        for i, seg in enumerate(segments):
            chunk = Chunk(
                episode_id=episode.id,
                transcription_id=transcription_id,
                chunk_index=i,
                text=None,
                start_time=seg["start"],
                end_time=seg["end"],
                speaker=seg["speaker"],
            )
            session.add(chunk)

        ep = session.get(Episode, episode.id)
        ep.diarized = True

        session.commit()

    logger.success(f"Saved {len(segments)} diarization segments")


# ---------- Main runner ----------

def run(max_episodes: int = None, skip_transcription_check: bool = False):
    """
    Main entry point for the diarization pipeline.

    Args:
        max_episodes: Maximum number of episodes to diarize (None = all).
        skip_transcription_check: If True, ignores Episode.transcribed flag.
    """
    engine = get_engine()

    with Session(engine) as session:
        query = session.query(Episode).filter(
            Episode.downloaded == True,
            Episode.diarized == False,
        )

        if not skip_transcription_check:
            query = query.filter(Episode.transcribed == True)

        if max_episodes:
            query = query.limit(max_episodes)

        episodes = query.all()

    total = len(episodes)
    logger.info(f"Episodes pending diarization: {total}")

    if total == 0:
        logger.success("All episodes already diarized")
        return

    pipeline = load_pipeline(settings.DEVICE)

    success_count = 0
    failed_count = 0
    failed_episodes = []

    for i, episode in enumerate(episodes, 1):
        logger.info(f"[{i}/{total}] Diarizing: {episode.title[:60]}")

        audio_path = get_audio_path(episode, settings.RAW_AUDIO_DIR)
        if not audio_path:
            failed_count += 1
            failed_episodes.append(episode.title)
            continue

        try:
            segments, embeddings, pipeline = diarize_episode(
                pipeline,
                audio_path,
                episode.id,
            )
            save_diarization(engine, episode, segments, embeddings)
            success_count += 1
            logger.info(
                f"Progress: {i}/{total} | "
                f"Success: {success_count} | Failed: {failed_count}"
            )

            safe_cuda_cleanup(wait_seconds=1)

            # Restore CUDA pipeline if fallback switched to CPU
            if settings.DEVICE == "cuda":
                try:
                    current_device = next(
                        pipeline.model.parameters()
                    ).device.type
                except Exception:
                    current_device = "unknown"

                if current_device != "cuda":
                    logger.warning(
                        "Reloading main CUDA pipeline for next episodes"
                    )

                    try:
                        pipeline = load_pipeline("cuda")
                    except Exception as reload_error:
                        logger.warning(
                            f"Could not reload CUDA pipeline, "
                            f"continuing on CPU: {reload_error}"
                        )

        except Exception as e:
            logger.error(f"Failed to diarize {episode.title[:60]}: {e}")
            failed_count += 1
            failed_episodes.append(episode.title)

            safe_cuda_cleanup(wait_seconds=0)

    logger.info("=== Diarization Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully diarized: {success_count}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()