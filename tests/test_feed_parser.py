"""
Unit tests for src/ingestion/feed_parser.py.

Builds real feedparser.parse() output from a minimal in-memory RSS string
instead of hand-constructing feedparser.FeedParserDict directly — manually
setting items on a bare FeedParserDict() does not reliably reproduce its
custom __getattr__/.get() keymap aliasing (verified empirically: a raw
FeedParserDict() built outside the real parser loses hasattr/.get access
to keys that are present via plain dict lookup).
"""

import feedparser

from src.ingestion.feed_parser import parse_episode, validate_episodes


def _make_entry(
    guid="guid-123",
    title="Episode Title",
    content="Full description",
    summary="Short summary",
    enclosure_url="https://example.com/ep.mp3",
    duration="600",
    include_enclosure=True,
    include_content=True,
    include_duration=True,
):
    enclosure_xml = (
        f'<enclosure url="{enclosure_url}" length="123" type="audio/mpeg"/>'
        if include_enclosure else ""
    )
    content_xml = (
        f"<content:encoded><![CDATA[{content}]]></content:encoded>"
        if include_content else ""
    )
    duration_xml = f"<itunes:duration>{duration}</itunes:duration>" if include_duration else ""

    rss = f"""<?xml version="1.0"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>Test Feed</title>
<item>
<title>{title}</title>
<guid>{guid}</guid>
<description>{summary}</description>
{content_xml}
{enclosure_xml}
{duration_xml}
</item>
</channel></rss>"""
    feed = feedparser.parse(rss)
    return feed.entries[0]


def test_parse_episode_prefers_content_over_summary():
    entry = _make_entry()
    result = parse_episode(entry)
    assert result["description"] == "Full description"


def test_parse_episode_falls_back_to_summary_when_content_missing():
    entry = _make_entry(include_content=False)
    result = parse_episode(entry)
    assert result["description"] == "Short summary"


def test_parse_episode_extracts_audio_url_from_enclosure():
    entry = _make_entry()
    result = parse_episode(entry)
    assert result["audio_url"] == "https://example.com/ep.mp3"


def test_parse_episode_handles_missing_enclosure():
    entry = _make_entry(include_enclosure=False)
    result = parse_episode(entry)
    assert result["audio_url"] is None


def test_parse_episode_handles_missing_duration():
    entry = _make_entry(include_duration=False)
    result = parse_episode(entry)
    assert result["duration_seconds"] == 0


def test_parse_episode_defaults_explicit_to_no():
    entry = _make_entry()
    result = parse_episode(entry)
    assert result["explicit"] == "no"


def test_validate_episodes_does_not_raise_on_missing_fields():
    episodes = [
        {"title": "", "audio_url": None, "duration_seconds": 0},
        {"title": "Good Episode", "audio_url": "https://x.mp3", "duration_seconds": 600},
    ]
    validate_episodes(episodes)  # should not raise