# Phase 1 — Data Collection

## Executive Summary

Phase 1 establishes the foundation of the project: ingest the podcast catalog
from its RSS feed, download all audio files, and persist metadata in a queryable
local database.

| Metric | Value |
|---|---|
| Total episodes catalogued | 1052 |
| Episodes downloaded | 1052 |
| Total audio size | 55.6 GB |
| Total audio duration | 1734.4 hours |
| Average episode duration | 98.9 minutes |
| Shortest episode | 12.5 minutes |
| Longest episode | 1012.8 minutes |
| Missing audio URL | 0 |
| Missing description | 0 |
| Missing image (feed limitation) | 587 (episodes 01–669) |
| Corrupted files | 0 |
| Estimated full dataset time | ~10 hours |

## Objectives

Build the data foundation for downstream phases:
- Catalog every episode of the podcast with metadata
- Download all audio files for offline processing
- Validate data integrity before proceeding to transcription

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Feed Parser | `src/ingestion/feed_parser.py` | ✅ Complete |
| Downloader | `src/ingestion/downloader.py` | ✅ Complete |
| Validator | `src/ingestion/validator.py` | ✅ Complete |
| Database Schema | `src/ingestion/database.py` | ✅ Complete |

## Architectural Decisions

### RSS Feed as primary data source

Selected RSS over Spotify API or web scraping because RSS provides direct access
to audio files (`enclosure url`) which is required for transcription. Spotify
API does not expose audio downloads, and web scraping is fragile.

### Streaming downloads

Used `requests.get(stream=True)` to avoid loading large MP3 files into memory.
Critical because some episodes exceed 1GB.

### Idempotency by design

Both feed ingestion and download check for existing records and files before
processing, allowing safe re-runs and incremental updates as new episodes are
published.

### SQLite as catalog database

SQLite chosen for portability and zero-config setup. Schema designed to support
the full pipeline (transcription, diarization, chunking, indexing) without
needing migration to a different database for the MVP.

## Quality Validation

Validation performed via `src/ingestion/validator.py`:

| Check | Result |
|---|---|
| Feed accessible | ✅ |
| All episodes have unique GUIDs | ✅ |
| All episodes have audio URLs | ✅ |
| All episodes have duration metadata | ✅ |
| All audio files downloaded successfully | ✅ |
| No corrupted files detected | ✅ |

## Configuration

This phase has the most podcast-specific configuration. The following items
need to be customized for a different podcast:

| Parameter | Where | Notes |
|---|---|---|
| RSS feed URL | `config/podcasts/{name}.py` | Direct URL to podcast's RSS |
| Podcast metadata fields | `src/ingestion/feed_parser.py` | Some podcasts use `summary`, others `content[0].value` |
| Image expectations | `data-source.md` | Documented limitations of the source feed |

See [REPLICATION_GUIDE.md](../REPLICATION_GUIDE.md) for adapting this phase.

## Known Limitations

- **Custom RSS endpoint dependency:** The project uses a Vercel proxy
  (`jn-feed.vercel.app`) instead of the original Megaphone feed. This adds
  an external dependency outside the project's control.
- **Inconsistent description fields:** Some episodes use `summary` for the
  real description, others use `content[0].value`. Handled with fallback logic.
- **Missing images on legacy episodes:** Episodes 01–669 (587 episodes) have
  no image in the RSS feed. This is a feed limitation, not a pipeline bug.
- **`enclosure length` always 0:** File size is unavailable before download,
  preventing pre-emptive disk space validation.

## Language Considerations

This phase is largely language-agnostic since it operates on metadata and
binary audio files. However:

- **RSS feed structure** may vary by region. Some podcasts use namespaces or
  fields specific to certain platforms (Apple Podcasts, Spotify).
- **Date formats** in `pubDate` follow RFC 2822 universally, but timezone
  handling may need adjustment per region.
- **Character encoding** in titles and descriptions should be UTF-8, but some
  legacy feeds use Latin-1 or other encodings.

## Next Steps

Phase 2 (Transcription) consumes the downloaded audio files. The database
schema already includes flags (`transcribed`, `diarized`, `chunked`, `indexed`)
to track pipeline progress per episode.

## How to Run

```bash
# Activate environment
.\venv\Scripts\Activate.ps1

# Step 1: Parse RSS feed and populate database
python -m src.ingestion.feed_parser

# Step 2: Download all audio files
python -m src.ingestion.downloader

# Step 3: Validate the catalog
python -m src.ingestion.validator
```