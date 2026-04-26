"""
Alignment pipeline for Phase 3 Milestone 4.
Cross-references Whisper transcription segments with pyannote diarization chunks.
Fills the chunk.text field by aggregating overlapping transcription segments.
"""

from loguru import logger
from sqlalchemy.orm import Session

from src.ingestion.database import (
    Episode,
    Chunk,
    TranscriptionSegment,
    get_engine,
)


def find_segments_for_chunk(
    chunk_start: float,
    chunk_end: float,
    segments: list,
    min_overlap_ratio: float = 0.5,
) -> list:
    """
    Finds transcription segments that overlap significantly with a diarization chunk.

    Args:
        chunk_start: Start time of diarization chunk in seconds.
        chunk_end: End time of diarization chunk in seconds.
        segments: List of TranscriptionSegment objects.
        min_overlap_ratio: Minimum ratio of segment duration that must overlap with chunk.

    Returns:
        List of segments that overlap with the chunk.
    """
    matched = []

    for seg in segments:
        overlap_start = max(chunk_start, seg.start_time)
        overlap_end = min(chunk_end, seg.end_time)
        overlap = overlap_end - overlap_start

        if overlap <= 0:
            continue

        seg_duration = seg.end_time - seg.start_time
        if seg_duration <= 0:
            continue

        overlap_ratio = overlap / seg_duration

        if overlap_ratio >= min_overlap_ratio:
            matched.append(seg)

    return matched


def align_episode(engine, episode: Episode) -> int:
    """
    Aligns transcription segments with diarization chunks for an episode.
    Updates chunk.text by joining text from overlapping transcription segments.

    Args:
        engine: SQLAlchemy engine instance.
        episode: Episode database model instance.

    Returns:
        Number of chunks updated.
    """
    with Session(engine) as session:
        # Load all segments for episode
        segments = session.query(TranscriptionSegment).filter(
            TranscriptionSegment.episode_id == episode.id,
        ).order_by(TranscriptionSegment.start_time).all()

        # Load all chunks for episode
        chunks = session.query(Chunk).filter(
            Chunk.episode_id == episode.id,
        ).order_by(Chunk.start_time).all()

        if not segments or not chunks:
            logger.warning(f"Missing data for episode: {episode.title[:60]}")
            return 0

        updated_count = 0

        for chunk in chunks:
            matched_segments = find_segments_for_chunk(
                chunk.start_time,
                chunk.end_time,
                segments,
            )

            if matched_segments:
                text = " ".join(s.text.strip() for s in matched_segments)
                chunk.text = text
                updated_count += 1

        session.commit()

    return updated_count


def run(max_episodes: int = None):
    """
    Main entry point for the alignment pipeline.
    Aligns transcription with diarization for all eligible episodes.

    Args:
        max_episodes: Maximum number of episodes to align (None = all).
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
    logger.info(f"Episodes for alignment: {total}")

    if total == 0:
        logger.warning("No episodes ready for alignment")
        return

    success_count = 0
    failed_count = 0
    failed_episodes = []

    for i, episode in enumerate(episodes, 1):
        logger.info(f"[{i}/{total}] Aligning: {episode.title[:60]}")

        try:
            updated = align_episode(engine, episode)
            success_count += 1
            logger.success(f"Updated {updated} chunks with text")

        except Exception as e:
            logger.error(f"Failed to align {episode.title[:60]}: {e}")
            failed_count += 1
            failed_episodes.append(episode.title)

    # Final report
    logger.info("=== Alignment Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully aligned: {success_count}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()