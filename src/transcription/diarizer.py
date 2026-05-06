"""
Diarization pipeline for podcast episodes.
Uses pyannote/audio 4.x to identify speakers in each episode.
Saves speaker segments to the chunks table in the database.
Idempotent: skips episodes already diarized.
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

from config import settings
from src.ingestion.database import Episode, Chunk, Transcription, get_engine


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
    logger.success("Pipeline loaded successfully")
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


def diarize_episode(pipeline: Pipeline, audio_path: Path) -> tuple[list[dict], np.ndarray]:
    """
    Runs diarization on a single episode.

    Args:
        pipeline: Loaded pyannote Pipeline instance.
        audio_path: Path to MP3 audio file.

    Returns:
        Tuple of (segments list, speaker embeddings array).
    """
    audio_input = load_audio(audio_path)

    diarization = pipeline(
        audio_input,
        min_speakers=settings.DIARIZATION_MIN_SPEAKERS,
        max_speakers=settings.DIARIZATION_MAX_SPEAKERS,
    )

    annotation = diarization.speaker_diarization
    embeddings = diarization.speaker_embeddings

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
            "duration": round(turn.end - turn.start, 2),
        })

    speakers = list(set(seg["speaker"] for seg in segments))
    logger.info(f"Detected {len(speakers)} speakers: {sorted(speakers)}")
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
        # Get transcription id for this episode
        transcription = session.query(Transcription).filter(
            Transcription.episode_id == episode.id
        ).first()

        transcription_id = transcription.id if transcription else None

        # Save each segment as a chunk with speaker label
        for i, seg in enumerate(segments):
            chunk = Chunk(
                episode_id=episode.id,
                transcription_id=transcription_id,
                chunk_index=i,
                text=None,          # text will be filled in phase 4 (alignment)
                start_time=seg["start"],
                end_time=seg["end"],
                speaker=seg["speaker"],
            )
            session.add(chunk)

        # Update episode flag
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

    # Load pipeline once for all episodes
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
            logger.info(f"Progress: {i}/{total} | Success: {success_count} | Failed: {failed_count}")

        except Exception as e:
            logger.error(f"Failed to diarize {episode.title[:60]}: {e}")
            failed_count += 1
            failed_episodes.append(episode.title)

    # Final report
    logger.info("=== Diarization Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully diarized: {success_count}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()