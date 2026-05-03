# Phase 4 Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| llama-index-core | 0.14+ | SentenceSplitter for chunking |
| tiktoken | 0.13+ | Tokenizer for size measurement |

### External Services

None — chunking is fully local.

### Hardware

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| RAM | 4GB | 8GB | 16GB |
| GPU | Not used | Not used | — |

Phase 4 runs entirely on CPU and is the only phase that does not benefit
from a GPU.

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install Phase 4 dependencies
pip install llama-index-core tiktoken
```

## Configuration

### Environment Variables

None required.

### Podcast-Specific Configuration

Currently no podcast-specific configuration in Phase 4. The default chunk
size and overlap work well across podcasts and languages.

If you observe issues:

- Tokens per chunk seem off (too few characters): try a different tokenizer
- Sentence boundaries wrong: validate SentenceSplitter for your language

## Validation

After setup, verify the chunker works on a small dataset:

```bash
python -c "from src.processing.chunker import run; run(max_episodes=1)"
python -m src.processing.validator
```

Expected validator output:

Total chunked episodes: 1
Avg chunks per episode: ~70
Avg tokens per chunk: ~440
No oversized chunks
No undersized chunks
All chunks have valid timestamps

## Decision Log

**Decision:** Recursive chunking over semantic chunking
**Context:** Need to choose chunking strategy for ~75K chunks total
**Options considered:**
- **Fixed-size** — simple but cuts sentences mid-stream
- **Sentence chunking** — coherent but variable size, hard to tune for embeddings
- **Recursive** — splits at natural boundaries when possible, falls back to
  smaller units. Predictable size with good coherence
- **Semantic chunking** — uses embeddings to find topic boundaries. Highest
  quality but expensive (requires embedding pass)
**Outcome:** Recursive chunking. Quality is good enough for the MVP and
performance is much better. Semantic chunking is on the v2 backlog.

**Decision:** tiktoken cl100k_base
**Context:** Need accurate token counting for chunk size limits
**Options considered:**
- Word counting — inaccurate, doesn't reflect LLM token consumption
- Hugging Face tokenizers — work but tied to specific model
- tiktoken — fast, OpenAI's standard, works well for size estimation
**Outcome:** tiktoken cl100k_base. Standard reference even when using
non-OpenAI models.

## Known Issues

- **None currently identified.** Phase 4 is the most stable phase.

## Language Considerations

The chunker is largely language-agnostic but two parameters may need tuning
for non-Portuguese, non-English content:

1. **Tokenizer:** cl100k_base is optimized for English. For other languages,
   consider:
   - **Latin-script languages** (Spanish, French, German, Portuguese):
     cl100k_base works adequately
   - **Asian languages** (Chinese, Japanese, Korean): use SentencePiece
   - **Right-to-left languages** (Arabic, Hebrew): cl100k_base works but
     may produce larger token counts

2. **Sentence boundary detection:** SentenceSplitter uses standard punctuation
   patterns. For languages with unusual conventions:
   - Chinese: uses `。` and `！`
   - Japanese: uses `。` and `？`
   - Khmer: uses `។`

## Platform Considerations

CPU-bound and platform-independent. Works identically on Windows, Linux, Mac.
No special configuration needed.