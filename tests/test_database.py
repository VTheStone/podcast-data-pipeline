"""
Unit tests for idempotency in src/ingestion/feed_parser.save_to_database.
Uses an in-memory SQLite engine (no filesystem, no fixtures needed).
"""

import pytest
from sqlalchemy.orm import Session

from src.ingestion.database import init_db, Episode
from src.ingestion.feed_parser import save_to_database


@pytest.fixture
def engine():
    return init_db(":memory:")


def _episode_dict(episode_id="ep-1", title="Test Episode"):
    return {
        "id": episode_id,
        "title": title,
        "published_at": "2026-01-01",
        "duration_seconds": 600,
        "description": "desc",
        "audio_url": "https://example.com/audio.mp3",
        "image_url": "",
        "explicit": "no",
    }


def test_save_to_database_inserts_new_episode(engine):
    save_to_database([_episode_dict()], engine)

    with Session(engine) as session:
        assert session.get(Episode, "ep-1") is not None


def test_save_to_database_is_idempotent(engine):
    save_to_database([_episode_dict()], engine)
    save_to_database([_episode_dict()], engine)

    with Session(engine) as session:
        count = session.query(Episode).count()

    assert count == 1


def test_save_to_database_does_not_overwrite_existing_row(engine):
    save_to_database([_episode_dict(title="Original Title")], engine)
    save_to_database([_episode_dict(title="Changed Title")], engine)

    with Session(engine) as session:
        ep = session.get(Episode, "ep-1")

    assert ep.title == "Original Title"