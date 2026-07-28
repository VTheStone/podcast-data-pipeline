"""
Integration test for src/transcription/aligner.py.
Verifies Phase 2 (transcription) + Phase 3 (diarization) output merges
correctly into Chunk.text. No mocking — this phase has no GPU dependency.
"""

from sqlalchemy.orm import Session

from src.ingestion.database import Chunk, Episode, Transcription, TranscriptionSegment
from src.transcription.aligner import align_episode


def test_align_episode_fills_chunk_text_from_overlapping_segments(
    engine, episode_with_transcription_and_diarization
):
    episode_id = episode_with_transcription_and_diarization

    with Session(engine) as session:
        episode = session.get(Episode, episode_id)

    updated_count = align_episode(engine, episode)

    assert updated_count == 2

    with Session(engine) as session:
        chunks = session.query(Chunk).filter(
            Chunk.episode_id == episode_id
        ).order_by(Chunk.chunk_index).all()

    assert chunks[0].text == "Hello there. How are you."
    assert chunks[1].text == "I am fine thanks."


def test_align_episode_skips_chunk_with_insufficient_overlap(engine):
    # Segment is 10s long; the chunk below only overlaps 3s of it (30%),
    # below the 0.5 min_overlap_ratio threshold — should NOT match.
    episode_id = "ep-partial-overlap"

    with Session(engine) as session:
        session.add(Episode(id=episode_id, title="Partial Overlap Episode", transcribed=True, diarized=True))
        session.flush()
        t = Transcription(episode_id=episode_id, full_text="Some text.")
        session.add(t)
        session.flush()
        session.add(TranscriptionSegment(
            episode_id=episode_id, transcription_id=t.id,
            segment_index=0, text="Some text.", start_time=0.0, end_time=10.0,
        ))
        session.add(Chunk(
            episode_id=episode_id, transcription_id=t.id,
            chunk_index=0, start_time=7.0, end_time=10.0, speaker="SPEAKER_00",
        ))
        session.commit()
        episode = session.get(Episode, episode_id)

    updated_count = align_episode(engine, episode)

    with Session(engine) as session:
        chunk = session.query(Chunk).filter(Chunk.episode_id == episode_id).first()

    assert updated_count == 0
    assert chunk.text is None