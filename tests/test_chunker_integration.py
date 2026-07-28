"""
Integration test for src/processing/chunker.chunk_episode.
Uses the same fixture as test_aligner.py to confirm Phase 4 correctly
consumes Phase 2's transcription segments end-to-end.
"""

from sqlalchemy.orm import Session

from src.ingestion.database import Episode, RAGChunk
from src.processing.chunker import chunk_episode


def test_chunk_episode_creates_rag_chunks_from_short_transcript(
    engine, episode_with_transcription_and_diarization
):
    episode_id = episode_with_transcription_and_diarization

    with Session(engine) as session:
        episode = session.get(Episode, episode_id)

    chunks_created = chunk_episode(engine, episode)

    assert chunks_created == 1  # short fixture text fits in a single chunk

    with Session(engine) as session:
        rag_chunks = session.query(RAGChunk).filter(RAGChunk.episode_id == episode_id).all()
        updated_episode = session.get(Episode, episode_id)

    assert len(rag_chunks) == 1
    assert rag_chunks[0].text == "Hello there. How are you. I am fine thanks."
    assert updated_episode.chunked is True