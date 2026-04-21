"""
Podcast pipeline configuration.
"""

# RSS Feed
RSS_URL = "https://jn-feed.vercel.app/api/filter?podcast=nerdcast"
PODCAST_NAME = "nerdcast"

# Paths
RAW_AUDIO_DIR = "data/raw"
METADATA_DIR = "data/metadata"

# Feed fields mapping
FEED_FIELDS = {
    "id": "id",
    "title": "title",
    "published": "published",
    "duration": "itunes_duration",
    "description": "summary",
    "image": "itunes_image",
    "audio_url": "enclosure",
}