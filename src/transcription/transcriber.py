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


def get_audio_duration(waveform: np.ndarray, sample_rate: int) -> float:
    """Returns audio duration in seconds."""
    return len(waveform) / sample_rate


def needs_chunking(duration_seconds: float) -> bool:
    """
    Determines if an episode is long enough to require temporal chunking.

    Args:
        duration_seconds: Episode duration in seconds.

    Returns:
        True if chunking should be applied.
    """
    return duration_seconds > settings.LONG_TRANSCRIPTION_THRESHOLD_SECONDS


def split_audio_for_transcription(
    waveform: np.ndarray,
    sample_rate: int,
) -> list[dict]:
    """
    Splits an audio waveform into overlapping temporal chunks for
    transcription. Each chunk is an independent numpy array copy.

    Args:
        waveform: Mono audio array.
        sample_rate: Audio sample rate in Hz.

    Returns:
        List of chunk dicts, each with: waveform, sample_rate, start_offset, index.
    """
    chunk_samples = int(settings.TRANSCRIPTION_CHUNK_DURATION_SECONDS * sample_rate)
    overlap_samples = int(settings.TRANSCRIPTION_CHUNK_OVERLAP_SECONDS * sample_rate)
    stride = chunk_samples - overlap_samples

    total_samples = len(waveform)
    chunks = []
    start = 0
    index = 0

    while start < total_samples:
        end = min(start + chunk_samples, total_samples)
        # .copy() makes the chunk independent so the original can be freed
        chunk_waveform = waveform[start:end].copy()

        chunks.append({
            "waveform": chunk_waveform,
            "sample_rate": sample_rate,
            "start_offset": start / sample_rate,
            "index": index,
        })

        if end == total_samples:
            break
        start += stride
        index += 1

    logger.info(
        f"Split audio into {len(chunks)} chunks of "
        f"{settings.TRANSCRIPTION_CHUNK_DURATION_SECONDS}s with "
        f"{settings.TRANSCRIPTION_CHUNK_OVERLAP_SECONDS}s overlap"
    )
    return chunks

def transcribe_episode(model: WhisperModel, audio_path: Path) -> tuple[list[dict], object]:
    """
    Transcribes a single audio file into segments.

    Args:
        model: Loaded WhisperModel instance.
        audio_path: Path to the MP3 audio file.

    Returns:
        Tuple of (segments list, transcription info object).
    """
    segments_gen, info = model.transcribe(
        str(audio_path),
        language=settings.WHISPER_LANGUAGE,
        beam_size=settings.WHISPER_BEAM_SIZE,
        initial_prompt=settings.WHISPER_INITIAL_PROMPT,
        vad_filter=settings.WHISPER_VAD_FILTER,
        no_speech_threshold=settings.WHISPER_NO_SPEECH_THRESHOLD,
        compression_ratio_threshold=settings.WHISPER_COMPRESSION_RATIO_THRESHOLD,
        condition_on_previous_text=settings.WHISPER_CONDITION_ON_PREVIOUS_TEXT,
        chunk_length=settings.WHISPER_CHUNK_LENGTH,  # process in chunks to avoid OOM
    )

    logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")

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
            segments, info = transcribe_episode(model, audio_path)
            metrics = calculate_metrics(segments, info, episode)
            save_transcription(engine, episode, segments, metrics)
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