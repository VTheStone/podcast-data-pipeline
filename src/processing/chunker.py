"""
Chunking pipeline for Phase 4.
Generates RAG-optimized chunks from transcribed episodes.
Uses recursive character text splitting with token-based size control.
"""

import json
from loguru import logger
from sqlalchemy.orm import Session
from llama_index.core.node_parser import SentenceSplitter
import tiktoken

from config import settings
from src.ingestion.database import (
    Episode,
    Transcription,
    TranscriptionSegment,
    Chunk,
    RAGChunk,
    get_engine,
)


# Tokenizer for accurate token counting
TOKENIZER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Counts tokens in text using tiktoken."""
    return len(TOKENIZER.encode(text))


def get_full_text_with_timestamps(session: Session, episode: Episode) -> list[dict]:
    """
    Loads transcription segments with timestamps for an episode.

    Args:
        session: SQLAlchemy session.
        episode: Episode database model instance.

    Returns:
        List of dicts with text and timestamps.
    """
    segments = session.query(TranscriptionSegment).filter(
        TranscriptionSegment.episode_id == episode.id
    ).order_by(TranscriptionSegment.start_time).all()

    return [
        {
            "text": s.text.strip(),
            "start_time": s.start_time,
            "end_time": s.end_time,
        }
        for s in segments
    ]


def get_speakers_for_range(
    session: Session,
    episode_id: str,
    start_time: float,
    end_time: float,
) -> list[str]:
    """
    Returns unique speakers active during a time range.

    Args:
        session: SQLAlchemy session.
        episode_id: Episode ID.
        start_time: Range start in seconds.
        end_time: Range end in seconds.

    Returns:
        List of unique speaker labels.
    """
    chunks = session.query(Chunk).filter(
        Chunk.episode_id == episode_id,
        Chunk.start_time < end_time,
        Chunk.end_time > start_time,
    ).all()

    speakers = sorted(set(c.speaker for c in chunks if c.speaker))
    return speakers


def build_text_with_offsets(segments: list[dict]) -> tuple[str, list[dict]]:
    """
    Builds full text and tracks character offsets for each segment.

    Args:
        segments: List of transcription segments with timestamps.

    Returns:
        Tuple of (full_text, list of segment offsets with start_char, end_char).
    """
    full_text_parts = []
    offsets = []
    current_offset = 0

    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue

        if current_offset > 0:
            full_text_parts.append(" ")
            current_offset += 1

        full_text_parts.append(text)
        offsets.append({
            "start_char": current_offset,
            "end_char": current_offset + len(text),
            "start_time": seg["start_time"],
            "end_time": seg["end_time"],
        })
        current_offset += len(text)

    return "".join(full_text_parts), offsets


def find_timestamps_by_position(
    chunk_text: str,
    full_text: str,
    offsets: list[dict],
    search_start: int = 0,
) -> tuple[float, float, int]:
    """
    Finds chunk timestamps by locating its position in the full text.
    """
    # Account for overlap: search a bit before the previous end
    overlap_buffer = 500  # chars to look back for overlapping chunks
    effective_search_start = max(0, search_start - overlap_buffer)
    
    # Try progressively shorter prefixes until we find a match
    chunk_start = -1
    for prefix_len in [200, 100, 50, 30]:
        if len(chunk_text) < prefix_len:
            continue
        prefix = chunk_text[:prefix_len]
        chunk_start = full_text.find(prefix, effective_search_start)
        if chunk_start != -1:
            break

    if chunk_start == -1:
        chunk_start = search_start

    chunk_end = chunk_start + len(chunk_text)

    start_time = None
    end_time = None

    for offset in offsets:
        if start_time is None and offset["end_char"] >= chunk_start:
            start_time = offset["start_time"]

        if offset["start_char"] <= chunk_end:
            end_time = offset["end_time"]

    if end_time is None and offsets:
        end_time = offsets[-1]["end_time"]

    if start_time is None:
        for offset in offsets:
            if offset["start_char"] >= chunk_start:
                start_time = offset["start_time"]
                break

    return (
        start_time or 0.0,
        end_time or 0.0,
        chunk_end,
    )


def chunk_episode(engine, episode: Episode) -> int:
    """
    Generates RAG chunks for an episode.
    """
    splitter = SentenceSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        tokenizer=TOKENIZER.encode,
    )

    with Session(engine) as session:
        segments = get_full_text_with_timestamps(session, episode)
        if not segments:
            logger.warning(f"No segments found for: {episode.title[:60]}")
            return 0

        # Build full text with char-level offsets
        full_text, offsets = build_text_with_offsets(segments)

        # Split into chunks
        text_chunks = splitter.split_text(full_text)
        logger.info(f"Generated {len(text_chunks)} chunks")

        # Save each chunk with metadata
        search_pos = 0
        for i, chunk_text in enumerate(text_chunks):
            start_time, end_time, search_pos = find_timestamps_by_position(
                chunk_text, full_text, offsets, search_pos
            )
            speakers = get_speakers_for_range(
                session, episode.id, start_time, end_time
            )
            token_count = count_tokens(chunk_text)

            rag_chunk = RAGChunk(
                episode_id=episode.id,
                chunk_index=i,
                text=chunk_text,
                token_count=token_count,
                start_time=start_time,
                end_time=end_time,
                speakers=json.dumps(speakers) if speakers else None,
            )
            session.add(rag_chunk)

        ep = session.get(Episode, episode.id)
        ep.chunked = True

        session.commit()

    return len(text_chunks)


def run(max_episodes: int = None):
    """
    Main entry point for the chunking pipeline.

    Args:
        max_episodes: Maximum episodes to process (None = all).
    """
    engine = get_engine()

    with Session(engine) as session:
        query = session.query(Episode).filter(
            Episode.transcribed == True,
            Episode.chunked == False,
        )

        if max_episodes:
            query = query.limit(max_episodes)

        episodes = query.all()

    total = len(episodes)
    logger.info(f"Episodes pending chunking: {total}")

    if total == 0:
        logger.success("All transcribed episodes already chunked")
        return

    success_count = 0
    failed_count = 0
    failed_episodes = []
    total_chunks_generated = 0

    for i, episode in enumerate(episodes, 1):
        logger.info(f"[{i}/{total}] Chunking: {episode.title[:60]}")

        try:
            chunks_count = chunk_episode(engine, episode)
            success_count += 1
            total_chunks_generated += chunks_count

        except Exception as e:
            logger.error(f"Failed to chunk {episode.title[:60]}: {e}")
            failed_count += 1
            failed_episodes.append(episode.title)

    # Final report
    logger.info("=== Chunking Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully chunked: {success_count}")
    logger.info(f"Total chunks generated: {total_chunks_generated}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()