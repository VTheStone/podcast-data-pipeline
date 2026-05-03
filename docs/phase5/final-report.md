# Phase 5 — Vector Indexing

## Executive Summary

Phase 5 converts text chunks into semantic vectors using a multilingual
embedding model and indexes them in ChromaDB for fast similarity search.
This is the retrieval foundation for the RAG pipeline.

| Metric | Value |
|---|---|
| Total chunked episodes | 357 (will scale to 1052) |
| Total indexed episodes | 357 |
| Indexing coverage | 100% |
| Total chunks in ChromaDB | 29,180 |
| Embedding model | paraphrase-multilingual-mpnet-base-v2 |
| Embedding dimensions | 768 |
| Distance metric | cosine |
| Avg indexing time | ~1.3s per episode |
| Estimated full dataset time | ~25 minutes |
| Vector DB | ChromaDB embedded |

## Objectives

- Generate semantic embeddings for all chunks
- Store embeddings in a queryable vector database with metadata
- Maintain SQL ↔ ChromaDB consistency for traceability
- Enable fast (sub-second) semantic search

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Indexer | `src/processing/indexer.py` | ✅ Complete |
| Searcher | `src/processing/searcher.py` | ✅ Complete |
| Validator | `src/processing/indexing_validator.py` | ✅ Complete |

## Architectural Decisions

### Embedding model: paraphrase-multilingual-mpnet-base-v2

Chosen as the balance between quality and cost:

- 768 dimensions — moderate vector size
- Multilingual — works across 50+ languages including Portuguese
- 1.1GB model size — fits in 4GB VRAM alongside other workloads
- Industry standard for multilingual semantic search

A/B testing with bge-m3 and e5-large is on the v2 backlog.

### Distance metric: cosine

Cosine similarity is the standard for text embeddings because it isolates
semantic meaning from vector magnitude. Two documents on the same topic
with different lengths should be similar regardless of length.

### Vector DB: ChromaDB embedded

Chosen for the MVP because:

- No server setup required (file-based persistence)
- Native HNSW for fast approximate search
- Native metadata filtering
- Clear migration path to Qdrant/Weaviate for production

Migration to a hosted vector DB is on the v2 backlog.

### Embedding ID in SQL for traceability

Each chunk in `rag_chunks` stores an `embedding_id` matching its ChromaDB
record. This allows:

- Re-indexing without losing references
- Validation that SQL and ChromaDB are in sync
- Debugging when retrieval seems wrong

### Batch encoding (32)

Embeddings generated in batches of 32 for GPU efficiency. Larger batches
risk OOM on 4GB VRAM, smaller batches underutilize the GPU.

## Quality Validation

Sample queries on the indexed corpus produced semantically relevant results:

- **Topic queries:** match thematic content with similarity 0.6-0.7
- **Entity queries:** find self-introduction segments
- **Synonym handling:** works across Portuguese variations (e.g., "filme"
  matches "longa-metragem")

Database consistency verified: SQL chunks with `embedding_id` count matches
ChromaDB document count exactly.

## Configuration

| Parameter | Default | Where to configure |
|---|---|---|
| `EMBEDDING_MODEL` | mpnet-base-v2 | `src/processing/config.py` |
| `EMBEDDING_DIMENSIONS` | 768 | Derived from model |
| `CHROMA_DB_PATH` | `data/chroma_db/` | `src/processing/config.py` |
| `CHROMA_COLLECTION_NAME` | podcast_chunks | `src/processing/config.py` |
| `DISTANCE_METRIC` | cosine | `src/processing/config.py` |
| `BATCH_SIZE` | 32 | `src/processing/indexer.py` |

See [REPLICATION_GUIDE.md](../REPLICATION_GUIDE.md).

## Known Limitations

- **Speaker labels are raw:** Metadata stores SPEAKER_XX, not real names.
  Phase 8 / v2 will add name resolution
- **Single embedding model:** No A/B comparison done yet. v2 backlog
- **No re-ranking:** All chunks retrieved by initial similarity score.
  Cross-encoder re-ranking is on the v2 backlog
- **Embedded ChromaDB:** Not multi-process safe; production needs hosted
  vector DB

## Language Considerations

The embedding model `paraphrase-multilingual-mpnet-base-v2` supports 50+
languages including Portuguese, English, Spanish, French, German, Italian,
Chinese, Japanese, Arabic, etc.

For specific language scenarios:

- **Multilingual content:** Current model handles cross-language similarity
  reasonably well (e.g., Portuguese query can match English content)
- **Best quality for Portuguese:** Consider BERTimbau or Sabiá-specific models
  for v2
- **Best quality for English:** all-mpnet-base-v2 is slightly better but
  doesn't handle non-English content
- **Asian languages:** bge-m3 may perform better than mpnet for Chinese,
  Japanese, Korean

The choice of distance metric (cosine) is language-independent.

## Next Steps

- Phase 6: Use the indexed embeddings for RAG retrieval and LLM generation

## How to Run

```bash
# Test with one episode
python -c "from src.processing.indexer import run; run(max_episodes=1)"

# Full indexing
python -m src.processing.indexer

# Test semantic search
python -m src.processing.searcher

# Validate
python -m src.processing.indexing_validator
```