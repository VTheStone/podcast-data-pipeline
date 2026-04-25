"""
Transcription pipeline for podcast episodes.
Uses faster-whisper with GPU support to transcribe MP3 files.
Idempotent: skips episodes already transcribed.
"""

from pathlib import Path
from loguru import logger
from faster_whisper import WhisperModel
from sqlalchemy.orm import Session

from src.ingestion.config import (
    RAW_AUDIO_DIR,
    WHISPER_MODEL,
    WHISPER_LANGUAGE,
    WHISPER_BEAM_SIZE,
    WHISPER_INITIAL_PROMPT,
    WHISPER_VAD_FILTER,
    WHISPER_NO_SPEECH_THRESHOLD,
    WHISPER_COMPRESSION_RATIO_THRESHOLD,
    WHISPER_CONDITION_ON_PREVIOUS_TEXT,
    DEVICE,
    COMPUTE_TYPE,
)
from src.ingestion.database import Episode, Transcription, get_engine


def load_model() -> WhisperModel:
    """
    Loads the Whisper model with configured device and compute type.

    Returns:
        Loaded WhisperModel instance.
    """
    logger.info(f"Loading Whisper model: {WHISPER_MODEL} on {DEVICE} ({COMPUTE_TYPE})")
    model = WhisperModel(WHISPER_MODEL, device=DEVICE, compute_type=COMPUTE_TYPE)
    logger.success(f"Model loaded successfully")
    return model


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
        language=WHISPER_LANGUAGE,
        beam_size=WHISPER_BEAM_SIZE,
        initial_prompt=WHISPER_INITIAL_PROMPT,
        vad_filter=WHISPER_VAD_FILTER,
        no_speech_threshold=WHISPER_NO_SPEECH_THRESHOLD,
        compression_ratio_threshold=WHISPER_COMPRESSION_RATIO_THRESHOLD,
        condition_on_previous_text=WHISPER_CONDITION_ON_PREVIOUS_TEXT,
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
    Saves transcription and quality metrics to the database.

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
            language=WHISPER_LANGUAGE,
            model_used=WHISPER_MODEL,
            **metrics,
        )
        session.add(transcription)

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

        audio_path = get_audio_path(episode, RAW_AUDIO_DIR)
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