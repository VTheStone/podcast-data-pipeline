"""
Validation script for Phase 4 — Chunking.
Generates a quality report of generated RAG chunks.
"""

from loguru import logger
from sqlalchemy.orm import Session

from src.ingestion.database import Episode, RAGChunk, get_engine


def validate_coverage(session: Session) -> dict:
    """Validates chunking coverage against transcribed episodes."""
    total_transcribed = session.query(Episode).filter(
        Episode.transcribed == True
    ).count()
    total_chunked = session.query(Episode).filter(
        Episode.chunked == True
    ).count()
    pending = session.query(Episode).filter(
        Episode.transcribed == True,
        Episode.chunked == False,
    ).count()

    return {
        "total_transcribed": total_transcribed,
        "total_chunked": total_chunked,
        "pending_chunking": pending,
        "coverage_pct": round(total_chunked / total_transcribed * 100, 1) if total_transcribed else 0,
    }


def validate_chunk_quality(session: Session) -> dict:
    """Validates RAG chunk quality metrics."""
    chunks = session.query(RAGChunk).all()

    if not chunks:
        return {}

    token_counts = [c.token_count for c in chunks if c.token_count]
    durations = [c.end_time - c.start_time for c in chunks if c.end_time > c.start_time]

    invalid_time = sum(1 for c in chunks if c.start_time >= c.end_time)
    oversized = sum(1 for c in chunks if c.token_count and c.token_count > 512)
    undersized = sum(1 for c in chunks if c.token_count and c.token_count < 50)
    no_speaker = sum(1 for c in chunks if not c.speakers)

    return {
        "total_chunks": len(chunks),
        "avg_tokens": round(sum(token_counts) / len(token_counts)) if token_counts else 0,
        "min_tokens": min(token_counts) if token_counts else 0,
        "max_tokens": max(token_counts) if token_counts else 0,
        "avg_duration_seconds": round(sum(durations) / len(durations), 1) if durations else 0,
        "invalid_timestamps": invalid_time,
        "oversized_chunks": oversized,
        "undersized_chunks": undersized,
        "chunks_without_speaker": no_speaker,
    }


def validate_temporal_order(session: Session) -> dict:
    """Validates that chunks within each episode are in temporal order."""
    episodes = session.query(Episode).filter(Episode.chunked == True).all()

    out_of_order = 0
    episodes_with_issues = []

    for ep in episodes:
        chunks = session.query(RAGChunk).filter(
            RAGChunk.episode_id == ep.id
        ).order_by(RAGChunk.chunk_index).all()

        for i in range(1, len(chunks)):
            if chunks[i].start_time < chunks[i-1].start_time:
                out_of_order += 1
                if ep.title not in episodes_with_issues:
                    episodes_with_issues.append(ep.title)
                break

    return {
        "out_of_order_episodes": len(episodes_with_issues),
        "total_violations": out_of_order,
    }


def validate_chunks_per_episode(session: Session) -> dict:
    """Validates chunk count distribution per episode."""
    episodes = session.query(Episode).filter(Episode.chunked == True).all()

    counts = []
    for ep in episodes:
        count = session.query(RAGChunk).filter(
            RAGChunk.episode_id == ep.id
        ).count()
        counts.append(count)

    if not counts:
        return {}

    return {
        "avg_chunks_per_episode": round(sum(counts) / len(counts)),
        "min_chunks": min(counts),
        "max_chunks": max(counts),
    }


def print_report(
    coverage: dict,
    quality: dict,
    temporal: dict,
    distribution: dict,
) -> None:
    """Prints formatted validation report."""
    logger.info("=" * 50)
    logger.info("PHASE 4 VALIDATION REPORT")
    logger.info("=" * 50)

    logger.info("--- Coverage ---")
    logger.info(f"Total transcribed: {coverage['total_transcribed']}")
    logger.info(f"Total chunked: {coverage['total_chunked']}")
    logger.info(f"Pending chunking: {coverage['pending_chunking']}")
    logger.info(f"Coverage: {coverage['coverage_pct']}%")

    if quality:
        logger.info("--- Chunk Quality ---")
        logger.info(f"Total chunks: {quality['total_chunks']}")
        logger.info(f"Avg tokens: {quality['avg_tokens']}")
        logger.info(f"Min tokens: {quality['min_tokens']}")
        logger.info(f"Max tokens: {quality['max_tokens']}")
        logger.info(f"Avg duration: {quality['avg_duration_seconds']}s")
        logger.info("--- Issues ---")
        logger.info(f"Invalid timestamps: {quality['invalid_timestamps']}")
        logger.info(f"Oversized (>512 tokens): {quality['oversized_chunks']}")
        logger.info(f"Undersized (<50 tokens): {quality['undersized_chunks']}")
        logger.info(f"Without speaker metadata: {quality['chunks_without_speaker']}")

    if temporal:
        logger.info("--- Temporal Consistency ---")
        logger.info(f"Episodes with order issues: {temporal['out_of_order_episodes']}")
        logger.info(f"Total violations: {temporal['total_violations']}")

    if distribution:
        logger.info("--- Distribution ---")
        logger.info(f"Avg chunks per episode: {distribution['avg_chunks_per_episode']}")
        logger.info(f"Min chunks: {distribution['min_chunks']}")
        logger.info(f"Max chunks: {distribution['max_chunks']}")

    logger.info("=" * 50)

    has_issues = (
        coverage['pending_chunking'] > 0 or
        quality.get('invalid_timestamps', 0) > 0 or
        quality.get('oversized_chunks', 0) > 0 or
        temporal.get('total_violations', 0) > 0
    )

    if has_issues:
        logger.warning("VALIDATION STATUS: ISSUES FOUND - review warnings above")
    else:
        logger.success("VALIDATION STATUS: ALL CHECKS PASSED")


def run():
    """Main entry point for the Phase 4 validator."""
    engine = get_engine()

    with Session(engine) as session:
        coverage = validate_coverage(session)
        quality = validate_chunk_quality(session)
        temporal = validate_temporal_order(session)
        distribution = validate_chunks_per_episode(session)

    print_report(coverage, quality, temporal, distribution)


if __name__ == "__main__":
    run()