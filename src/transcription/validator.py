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
    Validates transcription quality metrics across all transcriptions.

    Args:
        session: SQLAlchemy session instance.

    Returns:
        Dictionary with aggregated quality metrics.
    """
    transcriptions = session.query(Transcription).all()

    if not transcriptions:
        return {}

    char_counts = [t.total_chars for t in transcriptions if t.total_chars]
    logprobs = [t.avg_logprob for t in transcriptions if t.avg_logprob]
    repetitions = [t.repetition_rate for t in transcriptions if t.repetition_rate]
    cpm = [t.chars_per_minute for t in transcriptions if t.chars_per_minute]
    lang_conf = [t.language_confidence for t in transcriptions if t.language_confidence]

    empty = [t for t in transcriptions if not t.full_text or len(t.full_text) < 100]
    hallucinations = [t for t in transcriptions if t.hallucination_flag]

    poor_logprob = [t for t in transcriptions if t.avg_logprob and t.avg_logprob < -0.7]
    poor_coverage = [t for t in transcriptions if t.chars_per_minute and t.chars_per_minute < 300]
    poor_repetition = [t for t in transcriptions if t.repetition_rate and t.repetition_rate < 0.8]

    return {
        "total_transcriptions": len(transcriptions),
        "empty_or_short": len(empty),
        "hallucination_flagged": len(hallucinations),
        "poor_confidence": len(poor_logprob),
        "poor_coverage": len(poor_coverage),
        "poor_repetition": len(poor_repetition),
        "avg_chars": round(sum(char_counts) / len(char_counts)) if char_counts else 0,
        "total_chars": sum(char_counts) if char_counts else 0,
        "estimated_total_words": round(sum(char_counts) / 5) if char_counts else 0,
        "avg_logprob": round(sum(logprobs) / len(logprobs), 4) if logprobs else 0,
        "avg_repetition_rate": round(sum(repetitions) / len(repetitions), 4) if repetitions else 0,
        "avg_chars_per_minute": round(sum(cpm) / len(cpm), 1) if cpm else 0,
        "avg_language_confidence": round(sum(lang_conf) / len(lang_conf), 4) if lang_conf else 0,
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


def get_flagged_episodes(session: Session) -> list:
    """
    Returns episodes flagged for quality issues.

    Args:
        session: SQLAlchemy session instance.

    Returns:
        List of flagged episode titles with their issues.
    """
    flagged = []

    hallucinations = (
        session.query(Transcription, Episode)
        .join(Episode, Transcription.episode_id == Episode.id)
        .filter(Transcription.hallucination_flag == True)
        .all()
    )
    for t, ep in hallucinations:
        flagged.append({
            "title": ep.title,
            "issue": "hallucination_loop",
            "repetition_rate": t.repetition_rate,
        })

    poor_confidence = (
        session.query(Transcription, Episode)
        .join(Episode, Transcription.episode_id == Episode.id)
        .filter(Transcription.avg_logprob < -0.7)
        .all()
    )
    for t, ep in poor_confidence:
        flagged.append({
            "title": ep.title,
            "issue": "poor_confidence",
            "avg_logprob": t.avg_logprob,
        })

    poor_coverage = (
        session.query(Transcription, Episode)
        .join(Episode, Transcription.episode_id == Episode.id)
        .filter(Transcription.chars_per_minute < 300)
        .all()
    )
    for t, ep in poor_coverage:
        flagged.append({
            "title": ep.title,
            "issue": "poor_coverage",
            "chars_per_minute": t.chars_per_minute,
        })

    return flagged


def print_report(
    coverage: dict,
    quality: dict,
    models: dict,
    flagged: list,
) -> None:
    """
    Prints a formatted validation report.

    Args:
        coverage: Coverage validation results.
        quality: Quality validation results.
        models: Model usage statistics.
        flagged: List of flagged episodes.
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
        logger.info(f"Hallucination flagged: {quality['hallucination_flagged']}")
        logger.info(f"Poor confidence (logprob < -0.7): {quality['poor_confidence']}")
        logger.info(f"Poor coverage (< 300 chars/min): {quality['poor_coverage']}")
        logger.info(f"Poor repetition (< 0.8): {quality['poor_repetition']}")
        logger.info("--- Averages ---")
        logger.info(f"Avg chars per episode: {quality['avg_chars']}")
        logger.info(f"Avg logprob: {quality['avg_logprob']}")
        logger.info(f"Avg repetition rate: {quality['avg_repetition_rate']}")
        logger.info(f"Avg chars/min: {quality['avg_chars_per_minute']}")
        logger.info(f"Avg language confidence: {quality['avg_language_confidence']}")
        logger.info(f"Total chars: {quality['total_chars']}")
        logger.info(f"Estimated total words: {quality['estimated_total_words']}")

    logger.info("--- Models Used ---")
    for model, count in models.items():
        logger.info(f"{model}: {count} episodes")

    if flagged:
        logger.warning("--- Flagged Episodes ---")
        for ep in flagged:
            logger.warning(f"  {ep['title'][:60]} | issue: {ep['issue']}")

    logger.info("=" * 50)

    has_issues = (
        coverage['pending_transcription'] > 0 or
        quality.get('empty_or_short', 0) > 0 or
        quality.get('hallucination_flagged', 0) > 0 or
        quality.get('poor_confidence', 0) > 0
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
        flagged = get_flagged_episodes(session)

    print_report(coverage, quality, models, flagged)


if __name__ == "__main__":
    run()