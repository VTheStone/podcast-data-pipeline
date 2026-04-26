"""
Speaker Enrollment — Phase 3 Milestone 3.
Identifies speakers by cross-referencing transcription segments
with diarization chunks using timestamp overlap.
Extracts speaker names from self-introduction phrases.
"""

import re
import json
import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from src.ingestion.database import (
    Episode,
    Transcription,
    TranscriptionSegment,
    Chunk,
    Speaker,
    SpeakerEmbedding,
    get_engine,
)


# Known hosts for NerdCast
KNOWN_HOSTS = {
    "alexandre ottoni": "Alexandre Ottoni",
    "alottoni": "Alexandre Ottoni",
    "azaghal": "Azaghal",
    "zagal": "Azaghal",
    "deive pazos": "Azaghal",
}

# Patterns to detect self-introduction phrases
INTRODUCTION_PATTERNS = [
    r"aqui [eé] [oa]?\s*([\w][\w\s]{2,30}?)(?:\s*,|\s+e\s|\s+do\s|\s+da\s|\s+de\s|$)",
    r"eu sou [oa]?\s*([\w][\w\s]{2,30}?)(?:\s*,|\s+e\s|\s+do\s|\s+da\s|\s+de\s|$)",
    r"aqui quem vos fala [eé] [oa]?\s*([\w][\w\s]{2,30}?)(?:\s*,|\s+e\s|\s+do\s|\s+da\s|\s+de\s|$)",
]


def find_speaker_for_segment(
    segment_start: float,
    segment_end: float,
    chunks: list,
    tolerance: float = 2.0,
) -> str | None:
    """
    Finds the speaker with maximum overlap for a transcription segment.
    Falls back to nearest chunk within tolerance if no overlap found.

    Args:
        segment_start: Start time of transcription segment in seconds.
        segment_end: End time of transcription segment in seconds.
        chunks: List of diarization chunks.
        tolerance: Max distance in seconds to consider nearest chunk.

    Returns:
        Speaker label string or None if no match found within tolerance.
    """
    max_overlap = 0
    best_speaker = None

    # First pass: find chunk with maximum overlap
    for chunk in chunks:
        overlap = min(segment_end, chunk.end_time) - max(segment_start, chunk.start_time)
        if overlap > max_overlap:
            max_overlap = overlap
            best_speaker = chunk.speaker

    if best_speaker:
        return best_speaker

    # Fallback: find nearest chunk within tolerance
    min_distance = float('inf')
    nearest_speaker = None

    for chunk in chunks:
        # Distance to chunk (0 if overlapping)
        if chunk.end_time < segment_start:
            distance = segment_start - chunk.end_time
        elif chunk.start_time > segment_end:
            distance = chunk.start_time - segment_end
        else:
            distance = 0

        if distance < min_distance and distance <= tolerance:
            min_distance = distance
            nearest_speaker = chunk.speaker

    return nearest_speaker


def extract_name_from_text(text: str) -> str | None:
    """
    Extracts person name from self-introduction phrases.

    Args:
        text: Transcription segment text.

    Returns:
        Extracted name string or None if no match found.
    """
    text_lower = text.lower()

    # Check against known hosts first — by alias
    for alias, real_name in KNOWN_HOSTS.items():
        # Word boundary check to avoid false positives
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            return real_name

    # Patterns capture name until comma, "e ", or preposition
    INTRODUCTION_PATTERNS = [
        r"aqui [eé] [oa] ([^,]+?)(?:,|\s+e\s|$)",
        r"eu sou [oa]? ?([^,]+?)(?:,|\s+e\s|$)",
        r"aqui quem vos fala [eé] [oa] ([^,]+?)(?:,|\s+e\s|$)",
    ]

    for pattern in INTRODUCTION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            raw_name = match.group(1).strip()
            # Limit to max 2 words
            words = raw_name.split()[:2]
            name = " ".join(words).title()
            if len(name) > 2:
                return name

    return None


def enroll_episode(
    engine,
    episode: Episode,
    intro_duration: int = 300,
) -> dict:
    """
    Runs speaker enrollment for a single episode.
    Analyzes first N seconds to identify speakers by name.

    Args:
        engine: SQLAlchemy engine instance.
        episode: Episode database model instance.
        intro_duration: Duration in seconds to analyze for introductions.

    Returns:
        Dictionary mapping speaker labels to identified names.
    """
    with Session(engine) as session:
        # Get transcription segments in intro window
        segments = session.query(TranscriptionSegment).filter(
            TranscriptionSegment.episode_id == episode.id,
            TranscriptionSegment.start_time <= intro_duration,
        ).order_by(TranscriptionSegment.start_time).all()

        # Get diarization chunks in intro window
        chunks = session.query(Chunk).filter(
            Chunk.episode_id == episode.id,
            Chunk.start_time <= intro_duration,
        ).order_by(Chunk.start_time).all()

    if not segments or not chunks:
        logger.warning(f"No segments or chunks found for episode: {episode.title[:60]}")
        return {}

    # Map speaker labels to identified names
    speaker_names = {}

    for seg in segments:
        name = extract_name_from_text(seg.text)
        if not name:
            continue

        speaker = find_speaker_for_segment(seg.start_time, seg.end_time, chunks)
        if not speaker:
            continue

        if speaker not in speaker_names:
            speaker_names[speaker] = name
            logger.info(f"Identified: {speaker} → {name} (via: '{seg.text[:60]}')")
        else:
            if speaker_names[speaker] != name:
                logger.warning(
                    f"Speaker collision: {speaker} already mapped to '{speaker_names[speaker]}', "
                    f"skipping '{name}' (via: '{seg.text[:60]}')"
                )

    return speaker_names


def save_speakers(
    engine,
    episode: Episode,
    speaker_names: dict,
) -> None:
    """
    Saves identified speakers to the database.
    Updates existing speakers or creates new ones.

    Args:
        engine: SQLAlchemy engine instance.
        episode: Episode database model instance.
        speaker_names: Dictionary mapping speaker labels to names.
    """
    with Session(engine) as session:
        for label, name in speaker_names.items():
            # Check if speaker already exists
            existing = session.query(Speaker).filter(
                Speaker.name == name
            ).first()

            if existing:
                existing.total_appearances += 1
                existing.last_seen_episode = episode.id
                logger.info(f"Updated existing speaker: {name} (appearances: {existing.total_appearances})")
            else:
                is_host = name in KNOWN_HOSTS.values()
                speaker = Speaker(
                    name=name,
                    role="host" if is_host else "guest",
                    is_host=is_host,
                    total_appearances=1,
                    first_seen_episode=episode.id,
                    last_seen_episode=episode.id,
                    embedding_count=0,
                )
                session.add(speaker)
                logger.success(f"Created new speaker: {name} (host={is_host})")

        session.commit()


def run(max_episodes: int = None):
    """
    Main entry point for speaker enrollment.
    Processes diarized episodes to identify speakers.

    Args:
        max_episodes: Maximum number of episodes to process (None = all).
    """
    engine = get_engine()

    with Session(engine) as session:
        query = session.query(Episode).filter(
            Episode.transcribed == True,
            Episode.diarized == True,
        )

        if max_episodes:
            query = query.limit(max_episodes)

        episodes = query.all()

    total = len(episodes)
    logger.info(f"Episodes for speaker enrollment: {total}")

    if total == 0:
        logger.warning("No episodes ready for enrollment — need both transcribed and diarized")
        return

    all_identified = {}

    for i, episode in enumerate(episodes, 1):
        logger.info(f"[{i}/{total}] Enrolling: {episode.title[:60]}")

        try:
            speaker_names = enroll_episode(engine, episode)
            if speaker_names:
                save_speakers(engine, episode, speaker_names)
                all_identified[episode.title] = speaker_names
            else:
                logger.warning(f"No speakers identified in: {episode.title[:60]}")

        except Exception as e:
            logger.error(f"Failed enrollment for {episode.title[:60]}: {e}")

    # Summary
    logger.info("=== Enrollment Summary ===")
    logger.info(f"Episodes processed: {total}")
    logger.info(f"Episodes with identified speakers: {len(all_identified)}")

    # Print identified speakers per episode
    for title, speakers in all_identified.items():
        logger.info(f"\n{title[:60]}")
        for label, name in speakers.items():
            logger.info(f"  {label} → {name}")


if __name__ == "__main__":
    run()