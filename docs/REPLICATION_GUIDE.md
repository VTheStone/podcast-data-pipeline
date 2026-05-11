# Replication Guide

This guide walks through replicating the podcast data pipeline for a
different podcast. The project was built around NerdCast (Portuguese)
but is designed to work with any podcast in any language.

## When to use this guide

You want to:

- Build a RAG-based Q&A system over a podcast catalog
- Use this project as a starting point and adapt for your podcast
- Understand which parts are generic and which are podcast-specific

You don't need:

- Deep ML experience — the guide assumes solid programming background
  but explains ML-specific decisions
- Knowledge of all the underlying tools — each phase has its own setup
  documentation in `docs/phaseN/`

---

## Prerequisites

### Software

| Component | Version | Notes |
|---|---|---|
| Python | 3.13 | 3.11+ should also work |
| Git | latest | Standard version control |
| CUDA | 12.x | Required for GPU acceleration |
| FFmpeg | 4-8 | Required for audio processing |

### External accounts

You'll need free accounts on:

- **HuggingFace** — for downloading the pyannote diarization model
  - Accept terms for `pyannote/speaker-diarization-3.1`
  - Accept terms for `pyannote/segmentation-3.0`
  - Generate a token at https://huggingface.co/settings/tokens
- **Groq** — for LLM inference
  - Sign up at https://console.groq.com
  - Generate an API key

### Hardware

| Component | Minimum | Recommended |
|---|---|---|
| GPU | 4GB VRAM (NVIDIA) | 8GB+ VRAM |
| RAM | 16GB | 32GB |
| Disk | 100GB free | 200GB+ free |
| Network | Stable connection | High bandwidth |

Without a GPU, transcription becomes impractically slow (50x slower).
Diarization and embeddings can run on CPU but with significant
performance penalty.

---

## Step-by-step replication

### Step 1 — Clone and set up the environment

```bash
git clone https://github.com/VTheStone/podcast-data-pipeline.git
cd podcast-data-pipeline

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2 — Set up environment variables

Create a `.env` file in the project root:

```env
HF_TOKEN=hf_your_huggingface_token_here
GROQ_API_KEY=gsk_your_groq_api_key_here
PODCAST_PROFILE=nerdcast
```

Leave `PODCAST_PROFILE=nerdcast` for now — we'll change it after
creating your profile.

### Step 3 — Validate the original pipeline works

Before adapting, verify the project runs as-is. This isolates
environment issues from your customizations.

```bash
# Test feed parsing (lightweight, no GPU needed)
python -m src.ingestion.feed_parser

# Test the RAG pipeline with existing indexed data
python -m src.rag.pipeline
```

If this works, you have a working baseline. If not, fix environment
issues before continuing.

### Step 4 — Create your podcast profile

The project isolates everything podcast-specific into a "profile" file.

```bash
# Copy the template
cp config/podcasts/_template.py config/podcasts/your_podcast.py
```

Open `config/podcasts/your_podcast.py` and fill in the values. The
template has comments explaining each field, but the critical ones are:

```python
# Identity
PODCAST_NAME = "your_podcast"          # Internal name, lowercase, no spaces
PODCAST_DISPLAY_NAME = "Your Podcast"  # Shown to users
LANGUAGE = "en"                        # "pt_br" or "en" (see Step 5)

# Phase 1: Data source
RSS_URL = "https://your-podcast-feed-url.com/feed.rss"

# Phase 2: Transcription
WHISPER_LANGUAGE = "en"  # ISO 639-1 code for your podcast's language
WHISPER_INITIAL_PROMPT = (
    "Transcript of an English podcast about technology. "
    "Preserve proper nouns and technical terms. "
    "Examples: HostName1, HostName2, PodcastName."
)

# Phase 3: Diarization
DIARIZATION_MAX_SPEAKERS = 4  # Tune based on your podcast format
KNOWN_HOSTS = {
    "host alias": "Host Name",
    "another alias": "Host Name",
}

# Phase 7: UI
EXAMPLE_QUERIES = {
    "en": [
        "What did they discuss in the most recent episode?",
        "Tell me about a recurring topic",
        # ... 4 questions tailored to your podcast
    ],
    "pt_br": [...],  # If you also support Portuguese
}
```

Then update `.env`:

```env
PODCAST_PROFILE=your_podcast
```

### Step 5 — Configure for your language

The project includes UI strings, prompts, and regex patterns for
**Portuguese (pt_br)** and **English (en)**. If your podcast is in
one of these languages, you're done with language setup.

For other languages, you need to create three new files. Use English
as the reference since it's most commonly used.

**5.1 — UI strings**

```bash
cp src/ui/translations/en.py src/ui/translations/your_lang.py
```

Translate the strings in the new file. Keep the placeholder
`{podcast_name}` intact — it gets filled at runtime.

**5.2 — RAG prompts**

```bash
cp src/rag/prompts/en.py src/rag/prompts/your_lang.py
```

Translate the system prompt, citation labels, and refusal messages.
The system prompt is the most important — it controls how the LLM
behaves. Pay attention to:

- Citation format instructions (must match what users will see)
- Refusal language ("I couldn't find this information...")
- Rules about using only the provided context

**5.3 — Self-introduction regex patterns**

```bash
cp src/transcription/intro_patterns/en.py src/transcription/intro_patterns/your_lang.py
```

This file contains regex patterns that detect phrases like
"this is X" or "my name is X" at the start of episodes. Examples:

```python
# English patterns
INTRODUCTION_PATTERNS = [
    r"this is ([^,]+?)(?:,|\s+from\s|\s+and\s|$)",
    r"i'?m ([^,]+?)(?:,|\s+from\s|\s+and\s|$)",
    r"my name is ([^,]+?)(?:,|\s+from\s|\s+and\s|$)",
]

# Spanish patterns (example)
INTRODUCTION_PATTERNS = [
    r"aquí es ([^,]+?)(?:,|\s+y\s|$)",
    r"soy ([^,]+?)(?:,|\s+y\s|$)",
    r"me llamo ([^,]+?)(?:,|\s+y\s|$)",
]
```

**5.4 — Update the language loader**

The loaders in `src/ui/translations/__init__.py`,
`src/rag/prompts/__init__.py`, and
`src/transcription/intro_patterns/__init__.py` have a
`_SUPPORTED_LANGUAGES` set. Add your language code:

```python
_SUPPORTED_LANGUAGES = {"pt_br", "en", "your_lang"}
```

Set `LANGUAGE = "your_lang"` in your podcast profile.

### Step 6 — Run the pipeline

The project has 7 phases that run sequentially with some
parallelization opportunities (covered in
[PIPELINE_ORCHESTRATION.md](./PIPELINE_ORCHESTRATION.md)).

For an initial test, run each phase manually:

```bash
# Phase 1: Get the podcast catalog
python -m src.ingestion.feed_parser
python -m src.ingestion.downloader

# Phase 2: Transcribe (slow — start with one episode)
python -c "from src.transcription.transcriber import run; run(max_episodes=1)"

# Phase 3: Diarize and align
python -c "from src.transcription.diarizer import run; run(max_episodes=1)"
python -c "from src.transcription.aligner import run; run(max_episodes=1)"
python -c "from src.transcription.speaker_enrollment import run; run(max_episodes=1)"

# Phase 4: Chunk
python -c "from src.processing.chunker import run; run(max_episodes=1)"

# Phase 5: Index
python -c "from src.processing.indexer import run; run(max_episodes=1)"

# Phase 6 + 7: Run the interface
streamlit run src/ui/app.py
```

If everything works on one episode, scale up by removing `max_episodes`.

### Step 7 — Validate end-to-end

Open `http://localhost:8501`, ask a question about an episode, and
verify:

- UI displays in your configured language
- LLM responds in your configured language
- Sources cite real timestamps and episode titles

---

## Decisions you'll need to make

### RSS feed structure

Different podcast hosts (Megaphone, Anchor, RSS.com, Apple Podcasts)
use slightly different RSS field conventions. The default `FEED_FIELDS`
mapping works for most podcasts, but you may need to adjust:

- `description`: some feeds use `summary`, others use `content`,
  others use `subtitle`
- `image`: format varies between `itunes_image` and `image`
- `duration`: nearly always `itunes_duration` but format varies

Validate your feed by running:

```python
import feedparser
feed = feedparser.parse("YOUR_RSS_URL")
print(feed.entries[0].keys())  # Inspect available fields
```

### Diarization parameters

`DIARIZATION_MAX_SPEAKERS` should match your podcast's typical format:

| Podcast format | Recommended |
|---|---|
| Solo + occasional guest | 2-3 |
| Two hosts | 3-4 |
| Talk show with rotating guests | 5-6 |
| Round table with panel | 7-8 |

Tighter limits help diarization quality. If you set it too low,
voices get merged; too high, voices get split.

### Embedding model choice

The default `paraphrase-multilingual-mpnet-base-v2` works for 50+
languages but isn't the best for any specific one. Consider switching
if quality matters:

- **English-only podcast**: `sentence-transformers/all-mpnet-base-v2`
- **Asian languages**: `BAAI/bge-m3`
- **Higher quality multilingual**: `BAAI/bge-m3` (heavier, 2.3GB)

To switch, update `EMBEDDING_MODEL` in your podcast profile and
re-run Phase 5. The vector DB will need to be rebuilt.

### LLM model choice

`llama-3.3-70b-versatile` is the default on Groq's free tier. It works
well in English, Spanish, French, Portuguese, and major European
languages. For better quality in specific languages or for production
usage, consider:

- **OpenAI GPT-4o** for highest quality (paid)
- **Anthropic Claude** for nuanced responses (paid)
- **Local Ollama** for offline use (requires more VRAM)

Switching providers requires modifying `src/rag/pipeline.py`. The
current code uses the Groq client; you'd swap it for the appropriate
SDK.

---

## Troubleshooting

### Phase 1 — Data Collection

**Problem:** RSS feed returns 404 or empty entries

**Solution:** Verify the RSS URL is publicly accessible. Some podcasts
use proxy services that may be temporarily down. Try fetching the URL
in a browser first.

**Problem:** Audio downloads fail or are corrupted

**Solution:** The downloader uses streaming requests. If downloads
fail mid-transfer, partial files are cleaned up automatically. Re-run
the downloader to retry — it's idempotent.

### Phase 2 — Transcription

**Problem:** Whisper produces empty or repetitive output

**Solution:** Check `repetition_rate` in `transcriptions` table.
If below 0.5, the episode hit a hallucination loop. Solutions:

- Lower `compression_ratio_threshold` from 3.0 to 2.4
- Re-encode the audio if it has unusual codecs
- Try a smaller Whisper model (`medium`) — sometimes more stable

**Problem:** Wrong language detected

**Solution:** Set `WHISPER_LANGUAGE` explicitly in your profile.
Auto-detection fails on episodes with multiple languages or unusual
audio.

**Problem:** Out of GPU memory

**Solution:** Lower `WHISPER_CHUNK_LENGTH` in `config/default.py`
from 30 to 20 seconds. Or use `int8` instead of `int8_float16`
for compute type.

### Phase 3 — Diarization

**Problem:** Same person split into multiple speakers

**Solution:** Diarization quality varies with audio characteristics.
Episodes with background music, sound effects, or similar voices
suffer most. Documented limitation — Phase 8/v2 backlog includes
diarization tuning.

**Problem:** Different people merged into one speaker

**Solution:** Lower `DIARIZATION_MAX_SPEAKERS` if you set it too high.
The model overfits when given too many candidate speakers.

### Phase 5 — Indexing

**Problem:** Embedding generation OOM

**Solution:** Reduce `BATCH_SIZE` in `src/processing/indexer.py`
from 32 to 16 or 8.

**Problem:** Search returns irrelevant results

**Solution:** Raise `RAG_MIN_SIMILARITY` in `config/default.py`
from 0.5 to 0.6. Trade-off: fewer results but higher quality.

### Phase 6 — RAG

**Problem:** "GROQ_API_KEY not found"

**Solution:** Verify `.env` file exists in project root and has the
correct variable. Restart your terminal after changing `.env`.

**Problem:** LLM responds in wrong language

**Solution:** Check the system prompt in `src/rag/prompts/{lang}.py`
includes an explicit instruction like "Always respond in English".

### Phase 7 — UI

**Problem:** Page loads but pipeline doesn't initialize

**Solution:** Check terminal logs. The first load takes 25-30 seconds
because the embedding model needs to download/initialize. Wait it out.

**Problem:** UI in mixed languages

**Solution:** Make sure `LANGUAGE` in your podcast profile matches a
language module that exists in `src/ui/translations/`. The fallback
is `pt_br`.

---

## Going beyond

### When to migrate from SQLite

SQLite works well for the MVP scale (~1000 episodes). Consider
migrating to PostgreSQL when:

- Multiple users access the data simultaneously
- You need full-text search beyond what SQL LIKE provides
- You deploy to multiple machines and need centralized data

### When to deploy

The local Streamlit app is fine for demos and development. Deploy when:

- You want to share the project publicly (portfolio, blog post)
- Multiple users will use it concurrently
- You need it accessible from mobile

Deployment options range from Streamlit Community Cloud (easiest,
free for portfolio) to AWS/GCP with Docker (production-grade).

### When to add new features

The project intentionally stops at MVP scope. Features deferred to
v2 and v3 include:

- Speaker-aware queries
- Quantitative cross-episode queries
- Episode summarization at metadata level
- Cross-encoder re-ranking
- Real-time transcription of new episodes

These are documented in `docs/phase8/overview.md` as a backlog.

---

## Getting help

If you get stuck:

1. Check the phase-specific documentation in `docs/phaseN/`
2. Review the troubleshooting section above
3. Look at issues in the original repository
4. Open a new issue with reproduction steps

For ML-specific questions (model choice, parameter tuning, quality
issues), the phase reports include the rationale behind each
decision — start there to understand the trade-offs.