"""
Audio downloader for podcast episodes.
Downloads MP3 files from URLs stored in the database.
Idempotent: skips episodes already downloaded.
"""

from pathlib import Path
from loguru import logger
from tqdm import tqdm
import requests
from sqlalchemy.orm import Session

from config import settings
from src.ingestion.database import Episode, get_engine


def get_audio_filename(episode: Episode) -> str:
    """
    Generates a safe filename for an episode audio file.

    Args:
        episode: Episode database model instance.

    Returns:
        Safe filename string with .mp3 extension.
    """
    # Remove characters that are invalid in filenames
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in episode.title
    )
    safe_title = safe_title[:80].strip()
    return f"{safe_title}.mp3"


def download_audio(episode: Episode, output_dir: str) -> bool:
    """
    Downloads the audio file for a single episode.
    Skips if file already exists (idempotent).

    Args:
        episode: Episode database model instance.
        output_dir: Directory where audio files will be saved.

    Returns:
        True if download succeeded or file already exists, False otherwise.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = get_audio_filename(episode)
    filepath = output_path / filename

    # Idempotency check
    if filepath.exists():
        logger.debug(f"Already exists, skipping: {filename}")
        return True

    if not episode.audio_url:
        logger.warning(f"No audio URL for episode: {episode.title}")
        return False

    try:
        logger.info(f"Downloading: {filename}")
        response = requests.get(episode.audio_url, stream=True, timeout=60)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))

        with open(filepath, "wb") as f, tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=filename[:50],
            leave=False,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))

        logger.success(f"Downloaded: {filename}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {filename}: {e}")
        # Remove partial file if download failed
        if filepath.exists():
            filepath.unlink()
        return False


def update_episode_status(engine, episode_id: str, downloaded: bool) -> None:
    """
    Updates the downloaded flag for an episode in the database.

    Args:
        engine: SQLAlchemy engine instance.
        episode_id: Episode ID to update.
        downloaded: New downloaded status.
    """
    with Session(engine) as session:
        episode = session.get(Episode, episode_id)
        if episode:
            episode.downloaded = downloaded
            session.commit()


def run(batch_size: int = 10, max_episodes: int = None):
    """
    Main entry point for the downloader.
    Downloads episodes in batches, updating database after each.

    Args:
        batch_size: Number of episodes to download per batch.
        max_episodes: Maximum number of episodes to download (None = all).
    """
    engine = get_engine()

    with Session(engine) as session:
        query = session.query(Episode).filter(Episode.downloaded == False)

        if max_episodes:
            query = query.limit(max_episodes)

        episodes = query.all()

    total = len(episodes)
    logger.info(f"Episodes pending download: {total}")

    if total == 0:
        logger.success("All episodes already downloaded")
        return

    success_count = 0
    failed_count = 0
    failed_episodes = []

    for i, episode in enumerate(episodes, 1):
        logger.info(f"[{i}/{total}] Processing: {episode.title[:60]}")

        success = download_audio(episode, settings.RAW_AUDIO_DIR)

        if success:
            update_episode_status(engine, episode.id, downloaded=True)
            success_count += 1
        else:
            failed_count += 1
            failed_episodes.append(episode.title)

        # Progress summary every batch_size episodes
        if i % batch_size == 0:
            logger.info(f"Progress: {i}/{total} | Success: {success_count} | Failed: {failed_count}")

    # Final report
    logger.info("=== Download Summary ===")
    logger.info(f"Total processed: {total}")
    logger.success(f"Successfully downloaded: {success_count}")

    if failed_episodes:
        logger.warning(f"Failed: {failed_count}")
        for title in failed_episodes:
            logger.warning(f"  - {title}")


if __name__ == "__main__":
    run()