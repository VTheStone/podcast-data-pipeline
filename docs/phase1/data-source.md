# Data Source Mapping — NerdCast RSS Feed

## Source Overview

| Field        | Value                                              |
|--------------|----------------------------------------------------|
| Podcast      | NerdCast                                           |
| Publisher    | Jovem Nerd                                         |
| Language     | pt-br                                              |
| RSS URL      | https://jn-feed.vercel.app/api/filter?podcast=nerdcast |
| Feed Host    | Megaphone (megaphone.fm)                           |
| Audio Host   | pdst.fm / traffic.megaphone.fm                     |

## Episode Schema

| Field         | XML Tag                        | Type    | Notes                        |
|---------------|--------------------------------|---------|------------------------------|
| id            | `<guid>`                       | string  | Unique, isPermaLink=false    |
| title         | `<title>`                      | string  | Includes episode number      |
| published_at  | `<pubDate>`                    | string  | RFC 2822 format              |
| duration_sec  | `<itunes:duration>`            | integer | In seconds                   |
| audio_url     | `<enclosure url>`              | string  | Direct MP3 link              |
| description   | `<itunes:summary>`             | string  | Full episode description     |
| image_url     | `<itunes:image href>`          | string  | Episode cover art            |
| explicit      | `<itunes:explicit>`            | string  | "yes" or "no"                |

## Known Limitations

- `<enclosure length>` is always 0 — file size unavailable before download
- RSS URL is a custom filter endpoint, not the original Megaphone feed
- Feed may not contain full episode history (to be validated in Milestone 3)

## Decision Log

**Decision:** Use RSS feed over Spotify API  
**Context:** Needed direct access to audio files for transcription pipeline  
**Options considered:**
- Spotify API — does not expose audio files
- Web scraping — fragile, breaks with HTML changes
- RSS feed — open standard, stable, contains direct audio URLs

**Decision:** RSS feed via feedparser  
**Consequences:** Dependent on feed availability; 
custom endpoint (vercel.app) adds a dependency outside our control

## Validation Results

Validated on: 2026-04-21  
Tool: feedparser 6.0.11

| Check                          | Result      |
|--------------------------------|-------------|
| Feed accessible                | ✅          |
| Episodes found                 | ✅ 1052     |
| `audio_url` present            | ✅          |
| `guid` unique per episode      | ✅          |
| `duration` field available     | ✅          |
| `enclosure length` available   | ❌ Always 0 |