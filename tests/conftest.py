"""
Shared pytest fixtures for M2 integration tests.
"""

import pytest
from sqlalchemy.orm import Session

from src.ingestion.database import (
    init_db,
    Episode,
    Transcription,
    TranscriptionSegment,
    Chunk,
)


@pytest.fixture
def engine():
    """Fresh in-memory SQLite database, isolated per test."""
    return init_db(":memory:")


@pytest.fixture
def episode_with_transcription_and_diarization(engine):
    """
    Builds a small fixture episode with:
    - 1 Episode row (transcribed=True, diarized=True)
    - 1 Transcription row
    - 3 TranscriptionSegment rows (Phase 2 / Whisper output)
    - 2 Chunk rows (Phase 3 / pyannote diarization output, text not yet filled)

    Time ranges are designed so alignment has a predictable outcome:
    - Chunk 0 (0.0-4.5s) fully overlaps segments 0 and 1
    - Chunk 1 (5.0-9.0s) fully overlaps segment 2
    """
    episode_id = "ep-fixture-1"

    with Session(engine) as session:
        episode = Episode(
            id=episode_id,
            title="Fixture Episode",
            downloaded=True,
            transcribed=True,
            diarized=True,
        )
        session.add(episode)
        session.flush()

        transcription = Transcription(
            episode_id=episode_id,
            full_text="Hello there. How are you. I am fine thanks.",
            language="en",
        )
        session.add(transcription)
        session.flush()

        session.add_all([
            TranscriptionSegment(
                episode_id=episode_id, transcription_id=transcription.id,
                segment_index=0, text="Hello there.", start_time=0.0, end_time=2.0,
            ),
            TranscriptionSegment(
                episode_id=episode_id, transcription_id=transcription.id,
                segment_index=1, text="How are you.", start_time=2.0, end_time=4.5,
            ),
            TranscriptionSegment(
                episode_id=episode_id, transcription_id=transcription.id,
                segment_index=2, text="I am fine thanks.", start_time=5.0, end_time=9.0,
            ),
        ])
        session.add_all([
            Chunk(
                episode_id=episode_id, transcription_id=transcription.id,
                chunk_index=0, start_time=0.0, end_time=4.5, speaker="SPEAKER_00",
            ),
            Chunk(
                episode_id=episode_id, transcription_id=transcription.id,
                chunk_index=1, start_time=5.0, end_time=9.0, speaker="SPEAKER_01",
            ),
        ])
        session.commit()

    return episode_id