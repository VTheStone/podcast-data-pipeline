# Phase 6 Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| groq | 1.2+ | Groq API client |
| python-dotenv | 1.2+ | Environment variable management |

All Phase 5 dependencies must also be installed (embeddings, ChromaDB).

### External Services

- **Groq Account** — required for LLM API access
  - Sign up at https://console.groq.com
  - Generate an API key in **API Keys** section
  - Free tier: ~14,400 requests/day (sufficient for development and demos)

### Hardware

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| GPU | Optional (for embeddings) | 4GB+ VRAM | RTX 3050 Ti (4GB) |
| RAM | 8GB | 16GB | 16GB |
| Network | Required | Stable | — |

The LLM runs on Groq's infrastructure, not locally. Only the embedding
model uses GPU.

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install Phase 6 dependencies
pip install groq python-dotenv
```

## Configuration

### Environment Variables

Create or update `.env`:

```env
GROQ_API_KEY=gsk_your_key_here
```

### Podcast-Specific Configuration

In `config/podcasts/{name}.py`:

```python
PODCAST_DISPLAY_NAME = "NerdCast"
SYSTEM_PROMPT_PODCAST_CONTEXT = (
    "You are an assistant specialized in the NerdCast podcast..."
    # Or in the target language
)
```

In `src/rag/prompts.py`, the system prompt template uses the podcast name
and language settings to construct the final prompt.

### Language Configuration

If using a non-Portuguese podcast, update `src/rag/prompts.py`:

```python
# Example for English
SYSTEM_PROMPT = """You are an assistant specialized in the {podcast_name} podcast.

Your role is to answer questions using ONLY the provided excerpts.

Rules:
1. Use ONLY the information from provided excerpts. Never use external knowledge.
2. Cite sources using [Excerpt N, EP:MM:SS] format.
3. If the information isn't in the excerpts, respond: "I couldn't find this information in the available episodes."
4. Always respond in {language}.
..."""
```

## Validation

After setup, verify Groq API works:

```bash
python tests/explore_groq.py
```

Expected output:

Testing model: llama-3.3-70b-versatile
Test 1: Portuguese generation
Response time: 1.10s
Tokens used: 178
Response: RAG (Retrieval-Augmented Generation) é uma abordagem...
Test 2: RAG-style prompt
Response time: 0.34s
Tokens used: 240
Response: A missão Artemis II é a continuação...

## Decision Log

**Decision:** Groq over OpenAI/Anthropic for the MVP
**Context:** Need an LLM API for portfolio project with no budget
**Options considered:**
- **OpenAI GPT-4** — best quality, but $0.03/1K tokens adds up quickly
- **Anthropic Claude** — excellent quality, similar pricing
- **Groq llama-3.3-70b** — free tier, comparable quality to GPT-4 on
  many tasks, much faster (~500 tokens/s vs ~50 tokens/s)
- **Local Ollama** — free but VRAM-limited on 4GB GPU
**Outcome:** Groq chosen. Free, fast, quality good enough for the MVP.
v2 may add Ollama as offline fallback.

**Decision:** Temperature 0.3
**Context:** Need to balance determinism with natural language quality
**Options considered:**
- 0.0 — fully deterministic but produces robotic responses
- 0.3 — minor variation, still consistent
- 0.7 (default) — too creative for RAG
**Outcome:** 0.3 chosen. Deterministic enough for testing, natural enough
for users.

**Decision:** min_similarity 0.5
**Context:** Initial threshold of 0.3 produced false positives
**Options considered:**
- 0.3 — too permissive, unrelated episodes appearing
- 0.5 — balanced, filters out noise
- 0.7 — too restrictive, valid topics missed
**Outcome:** 0.5 chosen after observing query quality. Future v2
improvement: query-adaptive threshold.

## Known Issues

- **API rate limiting:** Free tier has daily limits. Heavy use may require
  upgrading or implementing caching
- **Network dependency:** Groq API is external; offline use requires Ollama
  alternative (v2 backlog)
- **Quota uncertainty:** Free tier limits change; check Groq's documentation
  for current values

## Language Considerations

The LLM provider and model affect language quality:

- **Groq llama-3.3-70b-versatile** quality tiers:
  - Excellent: English, Spanish, French
  - Good: Portuguese, German, Italian, Chinese, Japanese
  - Lower quality: Less common languages
- **Alternative providers per language:**
  - Portuguese: Sabiá (Maritaca AI) for native quality
  - Chinese: DeepSeek, Qwen
  - Multilingual: Anthropic Claude is generally strong

When adapting to a non-Portuguese podcast, validate response quality with
test queries before deciding on the LLM model.

## Platform Considerations

Groq API is platform-independent. Works identically on Windows, Linux, Mac.

Network connectivity required for every query. For offline scenarios,
consider local Ollama (v2 backlog).