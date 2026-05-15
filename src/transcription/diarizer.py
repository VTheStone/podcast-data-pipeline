"""
Diarization pipeline for podcast episodes.
Uses pyannote/audio 4.x to identify speakers in each episode.
Saves speaker segments to the chunks table in the database.
Idempotent: skips episodes already diarized.

For long episodes (> LONG_EPISODE_THRESHOLD_SECONDS), uses temporal
chunking with speaker re-identification across chunks to avoid VRAM
exhaustion during embedding aggregation.
"""

import os
import json
import torch
import soundfile as sf
import numpy as np
from pathlib import Path
from loguru import logger
from pyannote.audio import Pipeline
from sqlalchemy.orm import Session
import gc

from config import settings
from src.ingestion.database import Episode, Chunk, Transcription, get_engine


def load_pipeline(device: str) -> Pipeline:
    """
    Loads the pyannote diarization pipeline.
    Configures embedding_batch_size as pipeline attribute (pyannote 4.x).

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

    logger.success(
        f"Pipeline loaded successfully "
        f"(embedding_batch_size={pipeline.embedding_batch_size})"
    )
    return pipeline


def load_audio(audio_path: Path) -> dict:
    """
    Loads audio file as tensor using soundfile.
    Bypasses torchcodec/FFmpeg dependency.

    Args:
        audio_path: Path to MP3 audio file.

    Returns:
        Dictionary with waveform tensor and sample_rate.
    """
    waveform, sample_rate = sf.read(str(audio_path), always_2d=True)
    waveform = torch.tensor(waveform.T, dtype=torch.float32)
    return {"waveform": waveform, "sample_rate": sample_rate}


def get_audio_duration(audio_input: dict) -> float:
    """
    Returns audio duration in seconds from a loaded waveform.

    Args:
        audio_input: Dictionary with waveform tensor and sample_rate.

    Returns:
        Duration in seconds.
    """
    waveform = audio_input["waveform"]
    sample_rate = audio_input["sample_rate"]
    num_samples = waveform.shape[-1]
    return num_samples / sample_rate


def needs_chunking(duration_seconds: float) -> bool:
    """
    Determines if an episode is long enough to require temporal chunking.

    Args:
        duration_seconds: Episode duration in seconds.

    Returns:
        True if chunking should be applied.
    """
    return duration_seconds > settings.LONG_EPISODE_THRESHOLD_SECONDS


def split_audio_into_chunks(audio_input: dict) -> list[dict]:
    """
    Splits an audio waveform into overlapping temporal chunks.

    Each chunk is created as an independent copy (not a view) so the
    original waveform can be garbage-collected after splitting.

    Args:
        audio_input: Dictionary with waveform tensor and sample_rate.

    Returns:
        List of chunk dictionaries, each with waveform, sample_rate, start_offset.
    """
    waveform = audio_input["waveform"]
    sample_rate = audio_input["sample_rate"]

    chunk_samples = int(settings.CHUNK_DURATION_SECONDS * sample_rate)
    overlap_samples = int(settings.CHUNK_OVERLAP_SECONDS * sample_rate)
    stride = chunk_samples - overlap_samples

    total_samples = waveform.shape[-1]
    chunks = []
    start = 0

    while start < total_samples:
        end = min(start + chunk_samples, total_samples)
        # .clone() forces a new tensor copy, not a view
        # This allows the original waveform to be freed later
        chunk_waveform = waveform[:, start:end].clone()

        chunks.append({
            "waveform": chunk_waveform,
            "sample_rate": sample_rate,
            "start_offset": start / sample_rate,
        })

        if end == total_samples:
            break
        start += stride

    logger.info(
        f"Split audio into {len(chunks)} chunks of "
        f"{settings.CHUNK_DURATION_SECONDS}s with {settings.CHUNK_OVERLAP_SECONDS}s overlap"
    )
    return chunks


def reidentify_speakers_across_chunks(
    chunk_results: list[dict],
) -> tuple[list[dict], np.ndarray]:
    """
    Merges diarization results from multiple chunks by re-identifying
    speakers based on embedding similarity.

    Each chunk produces local speaker labels (SPEAKER_00, SPEAKER_01, ...).
    This function maps local labels to global labels by comparing embeddings.

    Args:
        chunk_results: List of dicts, each with:
            - 'segments': list of segments from that chunk
            - 'embeddings': speaker embeddings from that chunk
            - 'local_speakers': speaker labels seen in that chunk
            - 'start_offset': chunk start time in original audio

    Returns:
        Tuple of (merged segments with global speaker labels, merged embeddings).
    """
    if not chunk_results:
        return [], np.array([])

    # First chunk defines the initial speaker set
    first = chunk_results[0]
    global_segments = []
    global_speakers = list(first["local_speakers"])
    global_embeddings = first["embeddings"].copy()

    # Add segments from first chunk with no offset
    for seg in first["segments"]:
        global_segments.append({
            **seg,
            "speaker": seg["speaker"],
        })

    # For subsequent chunks, match speakers via cosine similarity
    for chunk in chunk_results[1:]:
        local_to_global = {}

        for local_idx, local_speaker in enumerate(chunk["local_speakers"]):
            local_emb = chunk["embeddings"][local_idx]

            # Compare to all known global speakers
            best_global_speaker = None
            best_similarity = -1.0

            for global_idx, global_speaker in enumerate(global_speakers):
                global_emb = global_embeddings[global_idx]
                similarity = _cosine_similarity(local_emb, global_emb)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_global_speaker = global_speaker

            # Decide: match existing speaker or create new one?
            if best_similarity >= settings.REID_SIMILARITY_THRESHOLD:
                local_to_global[local_speaker] = best_global_speaker
            else:
                # New speaker not seen in previous chunks
                new_label = f"SPEAKER_{len(global_speakers):02d}"
                local_to_global[local_speaker] = new_label
                global_speakers.append(new_label)
                global_embeddings = np.vstack([global_embeddings, local_emb])

        # Add segments from this chunk with global labels and time offset
        offset = chunk["start_offset"]
        for seg in chunk["segments"]:
            global_segments.append({
                "start": round(seg["start"] + offset, 2),
                "end": round(seg["end"] + offset, 2),
                "duration": round(seg["duration"], 2),
                "speaker": local_to_global[seg["speaker"]],
            })

    # Sort segments by start time (chunks may have slight overlap)
    global_segments.sort(key=lambda s: s["start"])

    logger.info(
        f"Re-identification complete: {len(global_speakers)} unique speakers "
        f"across {len(chunk_results)} chunks"
    )
    return global_segments, global_embeddings


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes cosine similarity between two vectors."""
    dot = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _diarize_single_chunk(
    pipeline: Pipeline,
    chunk_input: dict,
) -> dict:
    """
    Runs diarization on a single audio chunk.

    Args:
        pipeline: Loaded pyannote Pipeline instance.
        chunk_input: Dict with waveform, sample_rate, and start_offset.

    Returns:
        Dict with segments, embeddings, local_speakers, and start_offset.
    """
    audio_for_pipeline = {
        "waveform": chunk_input["waveform"],
        "sample_rate": chunk_input["sample_rate"],
    }

    # Run diarization
    with torch.no_grad():
        diarization = pipeline(
            audio_for_pipeline,
            min_speakers=settings.DIARIZATION_MIN_SPEAKERS,
            max_speakers=settings.DIARIZATION_MAX_SPEAKERS,
        )

    annotation = diarization.speaker_diarization
    # Convert embeddings to CPU numpy immediately to free GPU memory
    embeddings = np.asarray(diarization.speaker_embeddings)

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
            "duration": round(turn.end - turn.start, 2),
        })

    local_speakers = sorted(set(seg["speaker"] for seg in segments))

    result = {
        "segments": segments,
        "embeddings": embeddings,
        "local_speakers": local_speakers,
        "start_offset": chunk_input["start_offset"],
    }

    # Explicitly delete the diarization object (holds references to GPU tensors)
    del diarization
    del annotation

    return result


def diarize_in_chunks(
    pipeline: Pipeline,
    audio_input: dict,
    device: str = "cuda",
) -> tuple[list[dict], np.ndarray]:
    """
    Diarizes a long audio by splitting into temporal chunks and
    re-identifying speakers across chunks.

    Periodically reloads the pipeline to prevent VRAM fragmentation
    that accumulates over many chunks.

    Args:
        pipeline: Loaded pyannote Pipeline instance.
        audio_input: Dict with waveform and sample_rate of the full audio.
        device: Device used by the pipeline (needed for reload).

    Returns:
        Tuple of (merged segments with global labels, merged embeddings).
    """
    chunks = split_audio_into_chunks(audio_input)
    total_chunks = len(chunks)

    # Release the original waveform now that chunks are independent copies
    del audio_input
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    chunk_results = []
    reload_interval = settings.RELOAD_PIPELINE_EVERY_N_CHUNKS

    for i in range(total_chunks):
        chunk = chunks[i]
        logger.info(
            f"  Diarizing chunk {i+1}/{total_chunks} "
            f"(offset={chunk['start_offset']:.0f}s)"
        )

        # Reload pipeline periodically to prevent VRAM fragmentation
        if reload_interval and i > 0 and i % reload_interval == 0:
            logger.info(f"  Reloading pipeline to clear VRAM fragmentation")
            del pipeline
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            pipeline = load_pipeline(device)

        result = _diarize_single_chunk(pipeline, chunk)
        chunk_results.append(result)

        # Aggressively free this chunk's waveform after processing
        chunks[i] = None
        del chunk
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # All chunks processed, release the list shell
    del chunks
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return reidentify_speakers_across_chunks(chunk_results)


def diarize_episode(
    pipeline: Pipeline,
    audio_path: Path,
) -> tuple[list[dict], np.ndarray]:
    """
    Runs diarization on a single episode.
    Chooses between single-pass or chunked strategy based on duration.

    Args:
        pipeline: Loaded pyannote Pipeline instance.
        audio_path: Path to MP3 audio file.

    Returns:
        Tuple of (segments list, speaker embeddings array).
    """
    # Clear any leftover GPU memory before starting
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    audio_input = load_audio(audio_path)
    duration = get_audio_duration(audio_input)

    if needs_chunking(duration):
        logger.info(
            f"Episode duration: {duration:.0f}s "
            f"(> {settings.LONG_EPISODE_THRESHOLD_SECONDS}s threshold). "
            f"Using temporal chunking."
        )
        segments, embeddings = diarize_in_chunks(pipeline, audio_input, device=settings.DEVICE)
    else:
        logger.info(
            f"Episode duration: {duration:.0f}s. "
            f"Using single-pass diarization."
        )
        with torch.no_grad():
            diarization = pipeline(
                audio_input,
                min_speakers=settings.DIARIZATION_MIN_SPEAKERS,
                max_speakers=settings.DIARIZATION_MAX_SPEAKERS,
            )

        annotation = diarization.speaker_diarization
        embeddings = np.asarray(diarization.speaker_embeddings)

        segments = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            segments.append({
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "speaker": speaker,
                "duration": round(turn.end - turn.start, 2),
            })

        del diarization
        del annotation

    speakers = sorted(set(seg["speaker"] for seg in segments))
    logger.info(f"Detected {len(speakers)} speakers: {speakers}")
    logger.info(f"Total segments: {len(segments)}")

    return segments, embeddings


def get_audio_path(episode: Episode, audio_dir: str) -> Path | None:
    """
    Finds the audio file for an episode on disk.

    Args:
        episode: Episode database model instance.
        audio_dir: Directory where audio files are stored.

    Returns:
        Path to audio file or None if not found.
    """
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in episode.title
    )[:80].strip()

    audio_path = Path(audio_dir) / f"{safe_title}.mp3"

    if not audio_path.exists():
        logger.warning(f"Audio file not found: {audio_path.name}")
        return None

    return audio_path


def save_diarization(
    engine,
    episode: Episode,
    segments: list[dict],
    embeddings: np.ndarray,
) -> None:
    """
    Saves diarization segments to the chunks table.
    Updates episode diarized flag.

    Args:
        engine: SQLAlchemy engine instance.
        episode: Episode database model instance.
        segments: List of diarization segments.
        embeddings: Speaker embeddings numpy array.
    """
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


def run(
    max_episodes: int = None,
    skip_transcription_check: bool = False,
):
    """
    Main entry point for the diarization pipeline.

    Args:
        max_episodes: Maximum number of episodes to diarize (None = all).
        skip_transcription_check: If True, runs diarization on all downloaded
            episodes regardless of transcription status. Useful for testing.
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
            segments, embeddings = diarize_episode(pipeline, audio_path)
            save_diarization(engine, episode, segments, embeddings)
            success_count += 1
            logger.info(
                f"Progress: {i}/{total} | "
                f"Success: {success_count} | Failed: {failed_count}"
            )

            # Clear CUDA cache between episodes to prevent fragmentation
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        except Exception as e:
            logger.error(f"Failed to diarize {episode.title[:60]}: {e}")
            failed_count += 1
            failed_episodes.append(episode.title)

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    logger.info("=== Diarization Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully diarized: {success_count}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()