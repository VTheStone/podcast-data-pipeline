"""
Validation script for Phase 1 — Data Collection.
Generates a full quality report of the collected data.
"""

from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session

from src.ingestion.database import Episode, get_engine
from config import settings


def validate_database(session: Session) -> dict:
    """
    Validates episode data quality in the database.

    Args:
        session: SQLAlchemy session instance.

    Returns:
        Dictionary with validation results.
    """
    total = session.query(Episode).count()
    downloaded = session.query(Episode).filter(Episode.downloaded == True).count()
    pending = session.query(Episode).filter(Episode.downloaded == False).count()

    missing_audio_url = session.query(Episode).filter(
        Episode.audio_url == None
    ).count()

    missing_duration = session.query(Episode).filter(
        Episode.duration_seconds == 0
    ).count()

    missing_description = session.query(Episode).filter(
        Episode.description == ""
    ).count()

    missing_image = session.query(Episode).filter(
        Episode.image_url == ""
    ).count()

    return {
        "total_episodes": total,
        "downloaded": downloaded,
        "pending_download": pending,
        "missing_audio_url": missing_audio_url,
        "missing_duration": missing_duration,
        "missing_description": missing_description,
        "missing_image": missing_image,
    }


def validate_audio_files(downloaded_episodes: list, audio_dir: str) -> dict:
    """
    Validates audio files on disk against database records.

    Args:
        downloaded_episodes: List of episodes marked as downloaded in DB.
        audio_dir: Directory where audio files are stored.

    Returns:
        Dictionary with file validation results.
    """
    audio_path = Path(audio_dir)
    files_on_disk = list(audio_path.glob("*.mp3"))

    # Check for corrupted files (size = 0)
    corrupted = [f for f in files_on_disk if f.stat().st_size == 0]

    # Total size
    total_size_bytes = sum(f.stat().st_size for f in files_on_disk)
    total_size_mb = total_size_bytes / (1024 * 1024)

    return {
        "files_on_disk": len(files_on_disk),
        "files_in_database": len(downloaded_episodes),
        "corrupted_files": len(corrupted),
        "total_size_mb": round(total_size_mb, 2),
        "corrupted_names": [f.name for f in corrupted],
    }


def validate_duration(session: Session) -> dict:
    """
    Generates duration statistics for all episodes.

    Args:
        session: SQLAlchemy session instance.

    Returns:
        Dictionary with duration statistics.
    """
    episodes = session.query(Episode).filter(Episode.duration_seconds > 0).all()
    durations = [ep.duration_seconds for ep in episodes]

    if not durations:
        return {}

    total_seconds = sum(durations)
    avg_seconds = total_seconds / len(durations)
    total_hours = total_seconds / 3600

    return {
        "total_hours": round(total_hours, 1),
        "average_minutes": round(avg_seconds / 60, 1),
        "shortest_minutes": round(min(durations) / 60, 1),
        "longest_minutes": round(max(durations) / 60, 1),
    }


def print_report(db_results: dict, file_results: dict, duration_results: dict) -> None:
    """
    Prints a formatted validation report to the console.

    Args:
        db_results: Database validation results.
        file_results: File validation results.
        duration_results: Duration statistics.
    """
    logger.info("=" * 50)
    logger.info("PHASE 1 VALIDATION REPORT")
    logger.info("=" * 50)

    logger.info("--- Database ---")
    logger.info(f"Total episodes catalogued: {db_results['total_episodes']}")
    logger.info(f"Downloaded: {db_results['downloaded']}")
    logger.info(f"Pending download: {db_results['pending_download']}")

    logger.info("--- Data Quality ---")
    logger.info(f"Missing audio URL: {db_results['missing_audio_url']}")
    logger.info(f"Missing duration: {db_results['missing_duration']}")
    logger.info(f"Missing description: {db_results['missing_description']}")
    logger.info(f"Missing image URL: {db_results['missing_image']}")

    logger.info("--- Audio Files ---")
    logger.info(f"Files on disk: {file_results['files_on_disk']}")
    logger.info(f"Files in database: {file_results['files_in_database']}")
    logger.info(f"Total size: {file_results['total_size_mb']} MB")

    if file_results['corrupted_files'] > 0:
        logger.warning(f"Corrupted files: {file_results['corrupted_files']}")
        for name in file_results['corrupted_names']:
            logger.warning(f"  - {name}")
    else:
        logger.success("No corrupted files found")

    logger.info("--- Duration Statistics ---")
    logger.info(f"Total audio: {duration_results['total_hours']} hours")
    logger.info(f"Average episode: {duration_results['average_minutes']} minutes")
    logger.info(f"Shortest episode: {duration_results['shortest_minutes']} minutes")
    logger.info(f"Longest episode: {duration_results['longest_minutes']} minutes")

    logger.info("=" * 50)

    # Overall status
    has_issues = (
        db_results['missing_audio_url'] > 0 or
        file_results['corrupted_files'] > 0 or
        file_results['files_on_disk'] != file_results['files_in_database']
    )

    if has_issues:
        logger.warning("VALIDATION STATUS: ISSUES FOUND - review warnings above")
    else:
        logger.success("VALIDATION STATUS: ALL CHECKS PASSED")


def run():
    """Main entry point for the validator."""
    engine = get_engine()

    with Session(engine) as session:
        db_results = validate_database(session)
        downloaded_episodes = session.query(Episode).filter(
            Episode.downloaded == True
        ).all()
        duration_results = validate_duration(session)

    file_results = validate_audio_files(downloaded_episodes, settings.RAW_AUDIO_DIR)
    print_report(db_results, file_results, duration_results)


if __name__ == "__main__":
    run()