"""
Validation script for Phase 2 — Transcription.
Generates a quality report of the transcribed episodes.
"""

from loguru import logger
from sqlalchemy.orm import Session

from src.ingestion.database import Episode, Transcription, get_engine


def validate_coverage(session: Session) -> dict:
    """
    Validates transcription coverage against downloaded episodes.

    Args:
        session: SQLAlchemy session instance.

    Returns:
        Dictionary with coverage results.
    """
    total_downloaded = session.query(Episode).filter(
        Episode.downloaded == True
    ).count()

    total_transcribed = session.query(Episode).filter(
        Episode.transcribed == True
    ).count()

    pending = session.query(Episode).filter(
        Episode.downloaded == True,
        Episode.transcribed == False,
    ).count()

    return {
        "total_downloaded": total_downloaded,
        "total_transcribed": total_transcribed,
        "pending_transcription": pending,
        "coverage_pct": round(total_transcribed / total_downloaded * 100, 1) if total_downloaded else 0,
    }


def validate_quality(session: Session) -> dict:
    """
    Validates transcription quality metrics.

    Args:
        session: SQLAlchemy session instance.

    Returns:
        Dictionary with quality metrics.
    """
    transcriptions = session.query(Transcription).all()

    if not transcriptions:
        return {}

    char_counts = [len(t.full_text) for t in transcriptions]
    empty = [t for t in transcriptions if not t.full_text or len(t.full_text) < 100]

    return {
        "total_transcriptions": len(transcriptions),
        "empty_or_short": len(empty),
        "avg_chars": round(sum(char_counts) / len(char_counts)),
        "min_chars": min(char_counts),
        "max_chars": max(char_counts),
        "total_chars": sum(char_counts),
        "estimated_words": round(sum(char_counts) / 5),
    }


def validate_models(session: Session) -> dict:
    """
    Checks which models were used for transcription.

    Args:
        session: SQLAlchemy session instance.

    Returns:
        Dictionary with model usage stats.
    """
    transcriptions = session.query(Transcription).all()
    models_used = {}

    for t in transcriptions:
        models_used[t.model_used] = models_used.get(t.model_used, 0) + 1

    return models_used


def print_report(
    coverage: dict,
    quality: dict,
    models: dict,
) -> None:
    """
    Prints a formatted validation report.

    Args:
        coverage: Coverage validation results.
        quality: Quality validation results.
        models: Model usage statistics.
    """
    logger.info("=" * 50)
    logger.info("PHASE 2 VALIDATION REPORT")
    logger.info("=" * 50)

    logger.info("--- Coverage ---")
    logger.info(f"Total downloaded: {coverage['total_downloaded']}")
    logger.info(f"Total transcribed: {coverage['total_transcribed']}")
    logger.info(f"Pending transcription: {coverage['pending_transcription']}")
    logger.info(f"Coverage: {coverage['coverage_pct']}%")

    if quality:
        logger.info("--- Quality Metrics ---")
        logger.info(f"Total transcriptions: {quality['total_transcriptions']}")
        logger.info(f"Empty or too short: {quality['empty_or_short']}")
        logger.info(f"Average chars per episode: {quality['avg_chars']}")
        logger.info(f"Shortest transcription: {quality['min_chars']} chars")
        logger.info(f"Longest transcription: {quality['max_chars']} chars")
        logger.info(f"Total chars: {quality['total_chars']}")
        logger.info(f"Estimated total words: {quality['estimated_words']}")

    logger.info("--- Models Used ---")
    for model, count in models.items():
        logger.info(f"{model}: {count} episodes")

    logger.info("=" * 50)

    has_issues = (
        coverage['pending_transcription'] > 0 or
        quality.get('empty_or_short', 0) > 0
    )

    if has_issues:
        logger.warning("VALIDATION STATUS: ISSUES FOUND - review warnings above")
    else:
        logger.success("VALIDATION STATUS: ALL CHECKS PASSED")


def run():
    """Main entry point for the transcription validator."""
    engine = get_engine()

    with Session(engine) as session:
        coverage = validate_coverage(session)
        quality = validate_quality(session)
        models = validate_models(session)

    print_report(coverage, quality, models)


if __name__ == "__main__":
    run()