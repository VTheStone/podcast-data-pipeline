"""
Transcription pipeline for podcast episodes.
Uses faster-whisper with GPU support to transcribe MP3 files.
Idempotent: skips episodes already transcribed.

For very long episodes (> LONG_TRANSCRIPTION_THRESHOLD_SECONDS), uses
temporal chunking with per-chunk JSON persistence. This allows resuming
mid-episode if processing is interrupted.
"""

import json
import shutil
import numpy as np
import soundfile as sf
from pathlib import Path
from loguru import logger
from faster_whisper import WhisperModel
from sqlalchemy.orm import Session

from config import settings
from src.ingestion.database import (
    Episode,
    Transcription,
    TranscriptionSegment,
    get_engine,
)


def load_model() -> WhisperModel:
    """
    Loads the Whisper model with configured device and compute type.

    Returns:
        Loaded WhisperModel instance.
    """
    logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL} on {settings.DEVICE} ({settings.COMPUTE_TYPE})")
    model = WhisperModel(settings.WHISPER_MODEL, device=settings.DEVICE, compute_type=settings.COMPUTE_TYPE)
    logger.success(f"Model loaded successfully")
    return model

def load_audio_as_array(audio_path: Path) -> tuple[np.ndarray, int]:
    """
    Loads audio file as a mono numpy array using soundfile.

    Args:
        audio_path: Path to MP3 audio file.

    Returns:
        Tuple of (mono waveform array, sample_rate).
    """
    waveform, sample_rate = sf.read(str(audio_path), always_2d=True)
    # Convert to mono by averaging channels
    if waveform.shape[1] > 1:
        mono = waveform.mean(axis=1)
    else:
        mono = waveform[:, 0]
    return mono.astype(np.float32), sample_rate

def stream_audio_chunks(audio_path: Path):
    """
    Generator that yields audio chunks read directly from the file,
    without ever loading the full audio into memory.

    Each yielded chunk is a dict with: waveform (numpy mono array),
    sample_rate, start_offset (seconds), and index.

    Args:
        audio_path: Path to MP3 audio file.

    Yields:
        Chunk dicts ready for transcription.
    """
    with sf.SoundFile(str(audio_path)) as f:
        sample_rate = f.samplerate
        total_frames = len(f)
        channels = f.channels

        chunk_frames = int(settings.TRANSCRIPTION_CHUNK_DURATION_SECONDS * sample_rate)
        overlap_frames = int(settings.TRANSCRIPTION_CHUNK_OVERLAP_SECONDS * sample_rate)
        stride = chunk_frames - overlap_frames

        # Estimate total chunks for logging
        if total_frames <= chunk_frames:
            estimated_chunks = 1
        else:
            estimated_chunks = ((total_frames - chunk_frames) // stride) + 2

        logger.info(
            f"Streaming audio in chunks of "
            f"{settings.TRANSCRIPTION_CHUNK_DURATION_SECONDS}s with "
            f"{settings.TRANSCRIPTION_CHUNK_OVERLAP_SECONDS}s overlap "
            f"(~{estimated_chunks} chunks expected)"
        )

        start = 0
        index = 0
        while start < total_frames:
            f.seek(start)
            end = min(start + chunk_frames, total_frames)
            num_frames = end - start

            # Read this chunk's frames
            chunk_data = f.read(num_frames, dtype="float32", always_2d=True)

            # Convert to mono
            if channels > 1:
                mono = chunk_data.mean(axis=1)
            else:
                mono = chunk_data[:, 0]

            yield {
                "waveform": mono.astype(np.float32),
                "sample_rate": sample_rate,
                "start_offset": start / sample_rate,
                "index": index,
            }

            if end == total_frames:
                break
            start += stride
            index += 1

def get_temp_chunk_dir(episode_id: str) -> Path:
    """Returns the directory path for an episode's temporary chunk files."""
    temp_dir = Path(settings.TEMP_TRANSCRIPTS_DIR) / str(episode_id)
    return temp_dir


def save_chunk_result(
    episode_id: str,
    chunk_result: dict,
) -> Path:
    """
    Persists a single chunk's transcription result to a JSON file.

    Args:
        episode_id: Episode ID for organizing temp files.
        chunk_result: Dict with index, start_offset, segments, language.

    Returns:
        Path to the saved JSON file.
    """
    temp_dir = get_temp_chunk_dir(episode_id)
    temp_dir.mkdir(parents=True, exist_ok=True)

    chunk_file = temp_dir / f"chunk_{chunk_result['index']:03d}.json"
    with chunk_file.open("w", encoding="utf-8") as f:
        json.dump(chunk_result, f, ensure_ascii=False, indent=2)

    return chunk_file


def load_existing_chunks(episode_id: str) -> dict[int, dict]:
    """
    Loads all previously-saved chunks for an episode.

    Used to resume interrupted transcriptions without redoing work.

    Args:
        episode_id: Episode ID.

    Returns:
        Dict mapping chunk index to chunk result data.
    """
    temp_dir = get_temp_chunk_dir(episode_id)
    if not temp_dir.exists():
        return {}

    existing = {}
    for chunk_file in sorted(temp_dir.glob("chunk_*.json")):
        try:
            with chunk_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            existing[data["index"]] = data
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping corrupt chunk file {chunk_file.name}: {e}")

    return existing


def cleanup_temp_chunks(episode_id: str) -> None:
    """
    Removes the temporary chunks directory after successful final save.

    Args:
        episode_id: Episode ID.
    """
    temp_dir = get_temp_chunk_dir(episode_id)
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        logger.debug(f"Cleaned up temp chunks at {temp_dir}")

def _transcribe_single_chunk(
    model: WhisperModel,
    chunk: dict,
) -> dict:
    """
    Transcribes a single audio chunk via faster-whisper.

    Args:
        model: Loaded WhisperModel instance.
        chunk: Dict with waveform, sample_rate, start_offset, index.

    Returns:
        Dict with index, start_offset, segments, language, language_probability.
    """
    # faster-whisper accepts numpy arrays directly
    segments_gen, info = model.transcribe(
        chunk["waveform"],
        language=settings.WHISPER_LANGUAGE,
        beam_size=settings.WHISPER_BEAM_SIZE,
        initial_prompt=settings.WHISPER_INITIAL_PROMPT,
        vad_filter=settings.WHISPER_VAD_FILTER,
        no_speech_threshold=settings.WHISPER_NO_SPEECH_THRESHOLD,
        compression_ratio_threshold=settings.WHISPER_COMPRESSION_RATIO_THRESHOLD,
        condition_on_previous_text=settings.WHISPER_CONDITION_ON_PREVIOUS_TEXT,
        chunk_length=settings.WHISPER_CHUNK_LENGTH,
    )

    # Materialize segments (faster-whisper returns a generator)
    segments = []
    for seg in segments_gen:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "avg_logprob": round(seg.avg_logprob, 4),
        })

    return {
        "index": chunk["index"],
        "start_offset": chunk["start_offset"],
        "segments": segments,
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
    }


def merge_chunk_transcripts(
    chunk_results: list[dict],
    overlap_seconds: float,
) -> list[dict]:
    """
    Merges per-chunk transcription results into a single segment list.

    Applies time offsets and drops segments in overlap zones to prevent
    duplicate content at chunk boundaries.

    Args:
        chunk_results: List of chunk result dicts (sorted by index).
        overlap_seconds: Overlap duration between chunks in seconds.

    Returns:
        List of merged segments with global timestamps.
    """
    if not chunk_results:
        return []

    merged = []

    for i, chunk in enumerate(chunk_results):
        offset = chunk["start_offset"]
        is_last_chunk = (i == len(chunk_results) - 1)

        for seg in chunk["segments"]:
            # Apply time offset
            global_start = seg["start"] + offset
            global_end = seg["end"] + offset

            # For all chunks except the last, drop segments that fall
            # entirely in the overlap zone (the next chunk will cover them)
            if not is_last_chunk:
                next_chunk_start = chunk_results[i + 1]["start_offset"]
                # Skip if segment is entirely past the next chunk's start
                if global_start >= next_chunk_start:
                    continue

            merged.append({
                "start": round(global_start, 2),
                "end": round(global_end, 2),
                "text": seg["text"],
                "avg_logprob": seg["avg_logprob"],
            })

    # Final sort to ensure chronological order
    merged.sort(key=lambda s: s["start"])

    logger.info(
        f"Merged {sum(len(c['segments']) for c in chunk_results)} "
        f"raw segments into {len(merged)} final segments"
    )
    return merged


def transcribe_in_chunks(
    model: WhisperModel,
    audio_path: Path,
    episode_id: str,
) -> tuple[list[dict], object]:
    """
    Transcribes a long episode by streaming temporal chunks from disk.

    Audio is never loaded into memory in full — each chunk is read on
    demand. Per-chunk JSON files persist progress for resumability.

    Args:
        model: Loaded WhisperModel instance.
        audio_path: Path to MP3 audio file.
        episode_id: Episode ID for organizing temp files.

    Returns:
        Tuple of (merged segments list, info-like object).
    """
    # Check for existing partial work to resume
    existing = load_existing_chunks(episode_id)
    if existing:
        logger.info(
            f"Found {len(existing)} previously-saved chunks for this episode. "
            f"Resuming from chunk {max(existing.keys()) + 1}"
        )

    chunk_results = []

    # Stream chunks one at a time
    for chunk in stream_audio_chunks(audio_path):
        if chunk["index"] in existing:
            logger.info(
                f"  Chunk {chunk['index'] + 1} already done, skipping"
            )
            chunk_results.append(existing[chunk["index"]])
            # Free the chunk's audio data we just read but don't need
            del chunk
            continue

        logger.info(
            f"  Transcribing chunk {chunk['index'] + 1} "
            f"(offset={chunk['start_offset']:.0f}s)"
        )
        result = _transcribe_single_chunk(model, chunk)

        # Persist immediately to disk
        save_chunk_result(episode_id, result)
        chunk_results.append(result)

        # Free chunk waveform — we have what we need in result
        del chunk

    # Sort by index (in case resumed out of order)
    chunk_results.sort(key=lambda c: c["index"])

    # Merge into final segment list
    merged_segments = merge_chunk_transcripts(
        chunk_results,
        overlap_seconds=settings.TRANSCRIPTION_CHUNK_OVERLAP_SECONDS,
    )

    # Build an info-like object for compatibility with calculate_metrics
    languages = [c["language"] for c in chunk_results]
    most_common_lang = max(set(languages), key=languages.count)
    avg_lang_prob = sum(c["language_probability"] for c in chunk_results) / len(chunk_results)

    info = type("ChunkedInfo", (), {
        "language": most_common_lang,
        "language_probability": avg_lang_prob,
    })()

    return merged_segments, info

def transcribe_episode(
    model: WhisperModel,
    audio_path: Path,
    episode_id: str | None = None,
    episode_duration: float | None = None,
) -> tuple[list[dict], object]:
    """
    Transcribes a single audio file into segments.

    Chooses between single-pass and chunked strategy based on duration.
    For chunked transcription, partial results are persisted to disk for
    resumability.

    Args:
        model: Loaded WhisperModel instance.
        audio_path: Path to MP3 audio file.
        episode_id: Episode ID, required for chunked transcription persistence.
        episode_duration: Audio duration in seconds. Used to decide chunking
            strategy. If not provided, single-pass is used.

    Returns:
        Tuple of (segments list, transcription info object).
    """
    use_chunking = (
        episode_duration is not None
        and needs_chunking(episode_duration)
    )

    if use_chunking:
        if episode_id is None:
            raise ValueError(
                "episode_id is required for chunked transcription "
                "(used for partial-results persistence)"
            )
        logger.info(
            f"Episode duration: {episode_duration:.0f}s "
            f"(> {settings.LONG_TRANSCRIPTION_THRESHOLD_SECONDS}s threshold). "
            f"Using chunked transcription."
        )
        return transcribe_in_chunks(model, audio_path, episode_id)

    # Single-pass path (original behavior)
    duration_log = (
        f"{episode_duration:.0f}s" if episode_duration else "unknown duration"
    )
    logger.info(f"Episode duration: {duration_log}. Using single-pass transcription.")

    segments_gen, info = model.transcribe(
        str(audio_path),
        language=settings.WHISPER_LANGUAGE,
        beam_size=settings.WHISPER_BEAM_SIZE,
        initial_prompt=settings.WHISPER_INITIAL_PROMPT,
        vad_filter=settings.WHISPER_VAD_FILTER,
        no_speech_threshold=settings.WHISPER_NO_SPEECH_THRESHOLD,
        compression_ratio_threshold=settings.WHISPER_COMPRESSION_RATIO_THRESHOLD,
        condition_on_previous_text=settings.WHISPER_CONDITION_ON_PREVIOUS_TEXT,
        chunk_length=settings.WHISPER_CHUNK_LENGTH,
    )

    logger.info(
        f"Detected language: {info.language} "
        f"(confidence: {info.language_probability:.2f})"
    )

    results = []
    for segment in segments_gen:
        results.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
            "avg_logprob": round(segment.avg_logprob, 4),
        })

    return results, info


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


def save_transcription(
    engine,
    episode: Episode,
    segments: list[dict],
    metrics: dict,
) -> None:
    """
    Saves transcription, quality metrics and individual segments to the database.

    Args:
        engine: SQLAlchemy engine instance.
        episode: Episode database model instance.
        segments: List of transcription segments.
        metrics: Quality metrics dictionary.
    """
    full_text = " ".join(seg["text"] for seg in segments)

    with Session(engine) as session:
        transcription = Transcription(
            episode_id=episode.id,
            full_text=full_text,
            language=settings.WHISPER_LANGUAGE,
            model_used=settings.WHISPER_MODEL,
            **metrics,
        )
        session.add(transcription)
        session.flush()  # get transcription.id before saving segments

        # Save individual segments with timestamps
        for i, seg in enumerate(segments):
            segment = TranscriptionSegment(
                episode_id=episode.id,
                transcription_id=transcription.id,
                segment_index=i,
                text=seg["text"],
                start_time=seg["start"],
                end_time=seg["end"],
                avg_logprob=seg.get("avg_logprob"),
            )
            session.add(segment)

        ep = session.get(Episode, episode.id)
        ep.transcribed = True

        session.commit()
        logger.success(
            f"Transcription saved: {metrics['total_segments']} segments, "
            f"{metrics['total_chars']} chars, "
            f"repetition_rate={metrics['repetition_rate']}, "
            f"hallucination={metrics['hallucination_flag']}"
        )


def calculate_metrics(
    segments: list[dict],
    info,
    episode: Episode,
) -> dict:
    """
    Calculates quality metrics for a transcription.

    Args:
        segments: List of transcription segments.
        info: Whisper transcription info object.
        episode: Episode database model instance.

    Returns:
        Dictionary with quality metrics.
    """
    full_text = " ".join(seg["text"] for seg in segments)
    total_chars = len(full_text)
    estimated_words = total_chars // 5

    # Repetition rate — detect hallucination loops
    words = full_text.split()
    window = 50
    if len(words) >= window:
        chunks = [
            " ".join(words[i:i+window])
            for i in range(0, len(words) - window, window)
        ]
        unique_chunks = len(set(chunks))
        repetition_rate = unique_chunks / len(chunks) if chunks else 1.0
    else:
        repetition_rate = 1.0

    # Coverage — chars per minute of audio
    duration_minutes = episode.duration_seconds / 60
    chars_per_minute = total_chars / duration_minutes if duration_minutes > 0 else 0

    # Confidence score — average log probability
    avg_logprob = (
        sum(seg.get("avg_logprob", 0) for seg in segments) / len(segments)
        if segments else 0
    )

    # Hallucination flag
    hallucination_flag = repetition_rate < 0.5

    return {
        "total_segments": len(segments),
        "total_chars": total_chars,
        "estimated_words": estimated_words,
        "avg_logprob": round(avg_logprob, 4),
        "repetition_rate": round(repetition_rate, 4),
        "chars_per_minute": round(chars_per_minute, 1),
        "language_confidence": round(info.language_probability, 4),
        "hallucination_flag": hallucination_flag,
    }


def run(max_episodes: int = None):
    """
    Main entry point for the transcription pipeline.
    Processes downloaded episodes that have not been transcribed yet.

    Args:
        max_episodes: Maximum number of episodes to transcribe (None = all).
    """
    engine = get_engine()

    # Query episodes that are downloaded but not transcribed
    with Session(engine) as session:
        query = (
            session.query(Episode)
            .filter(Episode.downloaded == True)
            .filter(Episode.transcribed == False)
        )

        if max_episodes:
            query = query.limit(max_episodes)

        episodes = query.all()

    total = len(episodes)
    logger.info(f"Episodes pending transcription: {total}")

    if total == 0:
        logger.success("All downloaded episodes already transcribed")
        return

    # Load model once for all episodes
    model = load_model()

    success_count = 0
    failed_count = 0
    failed_episodes = []

    for i, episode in enumerate(episodes, 1):
        logger.info(f"[{i}/{total}] Transcribing: {episode.title[:60]}")

        audio_path = get_audio_path(episode, settings.RAW_AUDIO_DIR)
        if not audio_path:
            failed_count += 1
            failed_episodes.append(episode.title)
            continue

        try:
            segments, info = transcribe_episode(
                model,
                audio_path,
                episode_id=episode.id,
                episode_duration=episode.duration_seconds,
            )
            metrics = calculate_metrics(segments, info, episode)
            save_transcription(engine, episode, segments, metrics)
            cleanup_temp_chunks(episode.id)
            success_count += 1
            logger.info(f"Progress: {i}/{total} | Success: {success_count} | Failed: {failed_count}")

        except Exception as e:
            logger.error(f"Failed to transcribe {episode.title[:60]}: {e}")
            failed_count += 1
            failed_episodes.append(episode.title)

    # Final report
    logger.info("=== Transcription Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully transcribed: {success_count}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()