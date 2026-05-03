# Phase 1 Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| feedparser | 6.0+ | RSS feed parsing |
| requests | 2.32+ | HTTP downloads |
| SQLAlchemy | 2.0+ | ORM for database |
| Alembic | 1.14+ | Database migrations |

### External Services

- **RSS Feed Source** — must be publicly accessible. Examples:
  - Direct podcast feed (e.g., Megaphone, Anchor, RSS.com)
  - Custom proxy endpoint (this project uses `jn-feed.vercel.app`)

### Hardware

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| Disk | 100 GB free | 200 GB free | 56 GB used |
| Network | Stable connection | High bandwidth | — |

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install Phase 1 dependencies
pip install feedparser requests sqlalchemy alembic
```

## Configuration

### Environment Variables

```env
PODCAST_RSS_URL=https://example.com/podcast.rss
```

### Podcast-Specific Configuration

The following items must be customized per podcast in
`config/podcasts/{name}.py`:

```python
PODCAST_NAME = "nerdcast"
PODCAST_DISPLAY_NAME = "NerdCast"
RSS_URL = "https://jn-feed.vercel.app/api/filter?podcast=nerdcast"
LANGUAGE = "pt-BR"
```

## Validation

After setup, verify the configuration is correct:

```bash
# Test RSS feed parsing
python -c "
import feedparser
feed = feedparser.parse('YOUR_RSS_URL')
print(f'Episodes found: {len(feed.entries)}')
print(f'Sample title: {feed.entries[0].title}')
"
```

Expected output:

Episodes found: 1052
Sample title: NerdCast 1026 - Artemis II...

## Project Structure

podcast-data-pipeline/
├── data/
│   ├── raw/           # downloaded audio files
│   ├── metadata/      # SQLite database
│   ├── transcripts/   # phase 2 output
│   └── chroma_db/     # phase 5 output
├── src/
│   ├── ingestion/     # phase 1
│   ├── transcription/ # phase 2 and 3
│   ├── processing/    # phase 4 and 5
│   ├── rag/           # phase 6
│   └── ui/            # phase 7
├── docs/              # documentation by phase
├── tests/             # validation and exploration
├── migrations/        # Alembic migrations
└── config/            # default and podcast-specific configs

## Decision Log

**Decision:** Use venv over conda or poetry
**Context:** Need a lightweight environment that works on Windows without
extra tooling.
**Options considered:**
- conda — heavier, requires installing Miniconda first
- poetry — extra learning curve, less common in ML projects
- venv — built into Python, universal
**Outcome:** venv chosen for simplicity and portability.

**Decision:** Use SQLite for the MVP catalog
**Context:** Need a queryable store for metadata that grows from hundreds
to thousands of records.
**Options considered:**
- JSON files — fast to write, hard to query at scale
- PostgreSQL — production-grade but requires a server
- SQLite — file-based, queryable, no server needed
**Outcome:** SQLite chosen for the MVP. Phase 8 backlog includes migration
to PostgreSQL for production.

## Known Issues

- **Python 3.13 compatibility:** Some ML libraries (pyannote, faster-whisper)
  are validated only up to Python 3.12. Validated to work in this project,
  but may require workarounds in Phase 2 and 3.
- **PowerShell execution policy:** First-time activation requires:
```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Platform Considerations

- **Windows:** Tested. Uses PowerShell. Path separators are handled by `pathlib.Path`.
- **Linux/Mac:** Should work without changes since `pathlib` is OS-aware.
- **Docker:** Not currently containerized. See Phase 8 backlog for production
  containerization plans.