# Data Source Mapping

## Source Overview

| Field | Value |
|---|---|
| Podcast | NerdCast |
| Publisher | Jovem Nerd |
| Language | pt-BR |
| RSS URL | https://jn-feed.vercel.app/api/filter?podcast=nerdcast |
| Feed Host | Megaphone (megaphone.fm) |
| Audio Host | pdst.fm / traffic.megaphone.fm |

> **Note:** This file documents the specific data source used by this
> implementation. To adapt to a different podcast, update
> `config/podcasts/{name}.py` and validate the new feed against the
> schema below.

## Episode Schema

| Field | XML Tag | Type | Notes |
|---|---|---|---|
| id | `<guid>` | string | Unique, isPermaLink=false |
| title | `<title>` | string | Includes episode number |
| published_at | `<pubDate>` | string | RFC 2822 format |
| duration_sec | `<itunes:duration>` | integer | In seconds |
| audio_url | `<enclosure url>` | string | Direct MP3 link |
| description | `<itunes:summary>` | string | Full episode description |
| image_url | `<itunes:image href>` | string | Episode cover art |
| explicit | `<itunes:explicit>` | string | "yes" or "no" |

## Known Limitations

### Custom RSS endpoint dependency

The RSS URL is a custom Vercel proxy filter, not the original Megaphone feed.
This adds an external dependency outside the project's control.

### Description field inconsistency

- Some episodes use `summary` for real description
- Others repeat the title in `summary` and use `content` for real description
- **Solution implemented:** Use `content[0].value` as primary source with
  `summary` as fallback

### Missing image URL on legacy episodes

- Episodes from NerdCast 01 to NerdCast 669 (587 episodes) have no image
  in the RSS feed
- The `<itunes:image>` tag is absent in the XML for these episodes
- **Impact:** Low — image URL is metadata only, not required for transcription
  or RAG pipelines

### File size unavailable before download

- `<enclosure length>` is always 0 in this feed
- Pre-emptive disk space validation is therefore not possible
- **Mitigation:** Monitor `data/raw/` size during long downloads

## Decision Log

**Decision:** Use RSS feed over Spotify API
**Context:** Needed direct access to audio files for transcription pipeline
**Options considered:**
- Spotify API — does not expose audio files
- Web scraping — fragile, breaks with HTML changes
- RSS feed — open standard, stable, contains direct audio URLs
**Outcome:** RSS feed via feedparser. Dependent on feed availability;
custom endpoint adds an external dependency.

## Validation Results

Validated on: 2026-04-21
Tool: feedparser 6.0.11

| Check | Result |
|---|---|
| Feed accessible | ✅ |
| Episodes found | ✅ 1052 |
| `audio_url` present | ✅ |
| `guid` unique per episode | ✅ |
| `duration` field available | ✅ |
| `enclosure length` available | ❌ Always 0 |