# Phase 4 — Chunking

## Executive Summary

Phase 4 splits transcribed text into chunks of consistent size (~500 tokens)
optimized for embedding and retrieval. Each chunk preserves timestamp
information and speaker metadata from earlier phases, enabling precise
citation in the RAG pipeline.

| Metric | Value |
|---|---|
| Total transcribed episodes | 357 (will scale to 1052) |
| Total chunked episodes | 357 |
| Avg chunks per episode | 71 |
| Avg tokens per chunk | 443 |
| Avg chunk duration | 82.9s (~1.4 min) |
| Token range | 201 - 486 |
| Strategy | Recursive chunking via SentenceSplitter |
| Tokenizer | tiktoken cl100k_base |
| Chunk size target | 500 tokens |
| Overlap | 50 tokens (10%) |
| Avg chunking time | <1s per episode |
| Estimated full dataset time | ~15 minutes |

## Objectives

- Split transcriptions into uniform, semantically coherent chunks
- Preserve timestamps and speaker metadata for citation
- Produce input optimized for the embedding model in Phase 5
- Avoid splitting in the middle of sentences when possible

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Chunker | `src/processing/chunker.py` | ✅ Complete |
| Validator | `src/processing/validator.py` | ✅ Complete |
| RAGChunk Schema | `src/ingestion/database.py` | ✅ Complete |
| Migration | `migrations/versions/` | ✅ Applied |

## Architectural Decisions

### Recursive chunking strategy

Chosen over fixed-size, semantic, or sentence-only chunking because it offers
the best balance of:

- **Predictability** — chunk sizes always close to target
- **Semantic coherence** — splits at natural boundaries (paragraphs, sentences)
- **Simplicity** — no need to compute embeddings during chunking

Trade-offs accepted: not as semantically aware as embedding-based chunking,
but much faster and more deterministic.

### Tokenizer-based size control

Used tiktoken `cl100k_base` (OpenAI's tokenizer) for accurate token counts.
This is the industry standard for measuring context size and applies even
when using non-OpenAI models.

### Position-based timestamp tracking

Custom logic tracks character offsets in the original transcription to
correctly assign `start_time` and `end_time` to each chunk, even when overlap
causes the same text to appear in multiple chunks. Uses an `overlap_buffer`
of 500 characters to find chunk positions correctly.

### Speakers as metadata only

Chunks are NOT split by speaker boundaries. This decision ensures:

- Errors in diarization don't compromise retrieval quality
- Chunk sizes remain uniform regardless of conversation dynamics
- The RAG pipeline retrieves based on content, with speakers as optional filter

## Quality Validation

All quality checks passed for the test corpus:

- No invalid timestamps (`start_time < end_time` for all chunks)
- No oversized chunks (>512 tokens)
- No undersized chunks (<50 tokens)
- All chunks have speaker metadata when available from Phase 3
- All chunks within an episode are in temporal order

## Configuration

| Parameter | Default | Where to configure |
|---|---|---|
| `CHUNK_SIZE` | 500 | `src/processing/config.py` |
| `CHUNK_OVERLAP` | 50 | `src/processing/config.py` |
| `TOKENIZER_NAME` | cl100k_base | `src/processing/config.py` |
| `OVERLAP_BUFFER_CHARS` | 500 | `src/processing/chunker.py` |

See [REPLICATION_GUIDE.md](../REPLICATION_GUIDE.md).

## Known Limitations

- **Speaker metadata reflects raw labels:** Chunks contain SPEAKER_XX from
  diarization, not real names. Phase 8 / v2 will add name resolution
- **Sentence-aware splitting in Portuguese:** SentenceSplitter handles common
  punctuation but may not perfectly handle abbreviations or unusual punctuation
- **No semantic chunking:** Considered for v2/v3 backlog as a quality improvement

## Language Considerations

- **Tokenizer choice matters:** `cl100k_base` is optimized for English. For
  Portuguese, it tokenizes ~30% more characters per token than English.
  This means a 500-token chunk holds less text than the same chunk in English
- **Alternative tokenizers per language:**
  - **Chinese, Japanese, Korean:** Use SentencePiece-based tokenizers
  - **Arabic, Hebrew:** Direction handling required
  - **Languages with rich morphology** (Finnish, Turkish): May need
    custom token counting
- **Sentence boundaries vary:** Portuguese uses `.`, `!`, `?`. Other languages
  may use different punctuation (e.g., `。` in Japanese, `។` in Khmer)
- **The SentenceSplitter** from LlamaIndex handles most punctuation
  conventions but should be validated for new languages

## Next Steps

- Phase 5: Generate embeddings for all chunks and index in ChromaDB

## How to Run

```bash
# Test with one episode
python -c "from src.processing.chunker import run; run(max_episodes=1)"

# Full chunking
python -m src.processing.chunker

# Validate
python -m src.processing.validator
```