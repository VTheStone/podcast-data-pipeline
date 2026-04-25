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


def transcribe_episode(model: WhisperModel, audio_path: Path) -> list[dict]:
    """
    Transcribes a single audio file into segments.

    Args:
        model: Loaded WhisperModel instance.
        audio_path: Path to the MP3 audio file.

    Returns:
        List of segment dictionaries with start, end and text.
    """
    segments, info = model.transcribe(
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
    for segment in segments:
        results.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
        })

    return results


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
) -> None:
    """
    Saves transcription segments to the database.
    Updates episode transcribed flag.

    Args:
        engine: SQLAlchemy engine instance.
        episode: Episode database model instance.
        segments: List of transcription segments.
    """
    full_text = " ".join(seg["text"] for seg in segments)

    with Session(engine) as session:
        transcription = Transcription(
            episode_id=episode.id,
            full_text=full_text,
            language=WHISPER_LANGUAGE,
            model_used=WHISPER_MODEL,
        )
        session.add(transcription)

        ep = session.get(Episode, episode.id)
        ep.transcribed = True

        session.commit()
        logger.success(f"Transcription saved: {len(segments)} segments, {len(full_text)} chars")


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
            segments = transcribe_episode(model, audio_path)
            save_transcription(engine, episode, segments)
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