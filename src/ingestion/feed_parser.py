"""
RSS feed parser for podcast episode catalog generation.
Parses feed, saves JSON catalog and populates SQLite database.
"""

import json
import feedparser
from datetime import datetime
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session

from src.ingestion.config import RSS_URL, PODCAST_NAME, METADATA_DIR
from src.ingestion.database import Episode, init_db


def parse_episode(entry: dict) -> dict:
    audio_url = None
    if hasattr(entry, "enclosures") and entry.enclosures:
        audio_url = entry.enclosures[0].get("url", None)

    image_url = ""
    if hasattr(entry, "image") and entry.image:
        image_url = entry.image.get("href", "")

    # content is always the real description regardless of episode
    # summary sometimes contains just the title (inconsistent feed)
    description = ""
    if entry.get("content"):
        description = entry["content"][0].get("value", "")
    if not description:
        description = entry.get("summary", "")

    return {
        "id": entry.get("id", ""),
        "title": entry.get("title", ""),
        "published_at": entry.get("published", ""),
        "duration_seconds": int(entry.get("itunes_duration", 0)),
        "description": description,
        "audio_url": audio_url,
        "image_url": image_url,
        "explicit": "no" if not entry.get("itunes_explicit") else entry.get("itunes_explicit"),
    }


def parse_feed(rss_url: str) -> list[dict]:
    """
    Parses the RSS feed and returns a list of episode metadata.

    Args:
        rss_url: URL of the podcast RSS feed.

    Returns:
        List of normalized episode metadata dictionaries.
    """
    logger.info(f"Fetching RSS feed from {rss_url}")
    feed = feedparser.parse(rss_url)

    if feed.bozo:
        logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

    episodes = [parse_episode(entry) for entry in feed.entries]
    logger.info(f"Parsed {len(episodes)} episodes from feed")
    return episodes


def save_catalog(episodes: list[dict], output_dir: str) -> Path:
    """
    Saves the episode catalog as a JSON file for documentation and backup.

    Args:
        episodes: List of episode metadata dictionaries.
        output_dir: Directory where the catalog will be saved.

    Returns:
        Path to the saved catalog file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    catalog_path = output_path / "catalog.json"
    catalog = {
        "podcast": PODCAST_NAME,
        "generated_at": datetime.now().isoformat(),
        "total_episodes": len(episodes),
        "episodes": episodes,
    }

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    logger.success(f"Catalog saved to {catalog_path}")
    return catalog_path


def save_to_database(episodes: list[dict], engine) -> None:
    """
    Inserts episodes into the SQLite database.
    Skips episodes that already exist (idempotent).

    Args:
        episodes: List of episode metadata dictionaries.
        engine: SQLAlchemy engine instance.
    """
    with Session(engine) as session:
        new_count = 0
        skipped_count = 0

        for ep_data in episodes:
            exists = session.get(Episode, ep_data["id"])
            if exists:
                skipped_count += 1
                continue

            episode = Episode(**ep_data)
            session.add(episode)
            new_count += 1

        session.commit()

    logger.success(f"Database updated: {new_count} new, {skipped_count} skipped")


def validate_episodes(episodes: list[dict]) -> None:
    """
    Runs basic data quality checks on parsed episodes.

    Args:
        episodes: List of episode metadata dictionaries.
    """
    missing_audio = [ep for ep in episodes if not ep["audio_url"]]
    missing_duration = [ep for ep in episodes if ep["duration_seconds"] == 0]
    missing_title = [ep for ep in episodes if not ep["title"]]

    logger.info(f"Total episodes parsed: {len(episodes)}")
    logger.info(f"Missing audio_url: {len(missing_audio)}")
    logger.info(f"Missing duration: {len(missing_duration)}")
    logger.info(f"Missing title: {len(missing_title)}")

    if missing_audio:
        logger.warning("Episodes without audio URL:")
        for ep in missing_audio:
            logger.warning(f"  - {ep['title']}")


def run():
    """Main entry point for the feed parser."""
    # Initialize database
    engine = init_db()

    # Parse feed
    episodes = parse_feed(RSS_URL)

    # Validate
    validate_episodes(episodes)

    # Save JSON catalog (backup + documentation)
    save_catalog(episodes, METADATA_DIR)

    # Save to database (source of truth)
    save_to_database(episodes, engine)


if __name__ == "__main__":
    run()