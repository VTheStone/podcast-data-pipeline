# Phase 7 Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| streamlit | 1.42+ | Web framework |

All Phase 6 dependencies must also be installed (LLM, embeddings, ChromaDB).

### External Services

- **Groq API key** (from Phase 6 setup) — required for LLM responses

### Hardware

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| RAM | 8GB | 16GB | 16GB |
| GPU | Optional | 4GB+ VRAM | RTX 3050 Ti (4GB) |
| Network | Required | Stable | — |

GPU is optional but recommended — speeds up the embedding model on query.

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install Streamlit
pip install streamlit
```

## Configuration

### Environment Variables

Inherits from previous phases:

```env
GROQ_API_KEY=your_groq_api_key
PODCAST_PROFILE=nerdcast
```

### Podcast-Specific Configuration

In `config/podcasts/{name}.py`:

```python
PODCAST_DISPLAY_NAME = "NerdCast"
EXAMPLE_QUERIES = [
    "Quais astronautas participaram da Artemis II?",
    "Qual a diferença entre Artemis I e Artemis II?",
    "O que falaram sobre o Senhor dos Anéis?",
    "Por que voltar à Lua é importante?",
]
LANGUAGE = "pt-BR"
```

### Streamlit Configuration (Optional)

Create `.streamlit/config.toml` for theming:

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

## Validation

After setup, run the app and verify:

```bash
streamlit run src/ui/app.py
```

Expected behavior:

- Page loads at `http://localhost:8501`
- Sidebar shows correct chunk count and model name
- Welcome message displays with example queries
- Clicking an example query produces an answer with sources

## Decision Log

**Decision:** Use Streamlit over Flask/FastAPI/React
**Context:** Need a quick MVP interface for portfolio demonstration
**Options considered:**
- React/Next.js — professional but requires JavaScript expertise
- Flask/FastAPI + Jinja templates — backend control but slower to develop
- Streamlit — Python-native, fast to build, recognized in ML/DS community
**Outcome:** Streamlit chosen. Trade-off accepted: limited customization,
single-threaded per session.

**Decision:** Cache pipeline with `@st.cache_resource`
**Context:** Pipeline initialization (loading embedding model + ChromaDB)
takes 10-15 seconds. Re-running on every interaction is unacceptable.
**Options considered:**
- No caching — too slow
- Module-level globals — works but breaks Streamlit conventions
- `@st.cache_resource` — Streamlit-native, handles lifecycle properly
**Outcome:** `@st.cache_resource` chosen. Pipeline shared across all sessions.

## Known Issues

- **First load slow:** ~25-30 seconds. No way around this without
  pre-warming, which adds deployment complexity.
- **Memory growth:** Long sessions with many queries accumulate history
  in session state. Acceptable for MVP, but production would need
  history truncation.

## Language Considerations

The Streamlit app inherits the podcast's `LANGUAGE` setting. Two layers
need to match:

1. **UI strings** — buttons, captions, placeholders
2. **System prompt for LLM** — affects response language and quality

For non-Portuguese podcasts, both layers must be updated. UI strings
are loaded from `src/ui/translations/{lang}.py`, and the system prompt
from `src/rag/prompts/{lang}.py`.

## Platform Considerations

- **Local execution:** Validated on Windows. Should work on Linux/Mac
  without changes.
- **Production deployment:** Streamlit Community Cloud, HuggingFace Spaces,
  or self-hosted via Docker. See v2 backlog for deployment plans.
- **Browser support:** Modern browsers (Chrome, Firefox, Edge, Safari).
  No mobile-specific optimization.