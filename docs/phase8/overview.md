# Phase 8 — Identification Optimization

## Overview

Post-MVP phase focused on refining speaker identification quality after the
initial RAG pipeline is delivered. This phase enables speaker-aware queries
in the existing interface.

## Components

### 1. Diarization Fine-Tuning
- Experiment with clustering thresholds and segmentation parameters
- Test alternative diarization models
- Per-episode parameter optimization based on audio characteristics

### 2. Enrollment Refinement
- Improve self-introduction regex patterns
- Expand known hosts dictionary
- Handle speaker collisions when diarization groups multiple voices

### 3. Cross-Episode Speaker Consolidation
- Aggregate speaker embeddings across all episodes
- Detect recurring guests via embedding similarity
- Build robust voice profiles for hosts using progressive enrollment
- Use weighted average of embeddings based on confidence scores

### 4. Semantic Chunking Evaluation
- Compare current recursive chunking with semantic chunking approach
- Measure retrieval quality improvement on representative queries
- Evaluate cost vs quality trade-off (semantic chunking requires embedding pass)
- Consider hybrid approach (recursive with semantic boundary detection)

### 5. Infrastructure Migration

When moving from local development to production deployment, migrate:

- **SQLite → PostgreSQL** for relational data
  - Multi-application access
  - Better concurrency and transaction handling
  - Industry-standard for production
- **ChromaDB embedded → Qdrant or Weaviate self-hosted**
  - Multi-application access to vector index
  - Better performance at scale
  - Advanced filtering and re-ranking features
- **Alternative consideration: pgvector**
  - Single database for both relational and vector data
  - Simpler operations, fewer dependencies
  - Trade-off: less specialized than dedicated vector DBs

The current SQLAlchemy abstraction means the migration is mostly a connection
string change for SQLite → PostgreSQL. ChromaDB → Qdrant requires changes
in the indexing and retrieval modules.

### 6. Embedding Model A/B Testing

After MVP delivery, evaluate alternative embedding models with domain-specific
queries:

- Current baseline: paraphrase-multilingual-mpnet-base-v2 (768 dim)
- Candidates: BAAI/bge-m3 (1024 dim), intfloat/multilingual-e5-large (1024 dim)
- Methodology: same query set, measure precision@5 and MRR
- Decision criteria: improvement must be statistically significant and
  worth the additional computational cost
- Test should use real user queries collected from the Phase 7 interface

### 7. RAG Quality Improvements

Based on Phase 6 evaluation findings:

- **Named Entity Queries**: improve retrieval for person name searches
  by boosting chunks containing exact name matches
- **Metadata Queries**: add episode summary to RAGChunk metadata
  to handle "what was the episode about" type queries
- **Query Classification**: route abstract vs specific queries
  differently (abstract → broader search, specific → tighter filter)
- **Re-ranking**: implement cross-encoder re-ranking for top-20 chunks
  before selecting top-5 for the LLM
- **RAGAS Evaluation**: automated faithfulness and relevance scoring
  for regression testing

## Database Schema

The schema for this phase is already in place (Speaker and SpeakerEmbedding
tables) since Phase 3, allowing incremental refinement without migrations.

### 8. Streamlit Interface Enhancements (Phase 7 polish)

After MVP delivery, enhance the user experience:

- Sidebar with runtime configuration (n_chunks, min_similarity)
- Charts visualizing result quality (similarity distribution)
- Episode filters for scoped queries
- Export conversations as Markdown/PDF
- Multi-page navigation (chat, browse episodes, statistics)
- Light/dark mode toggle

### 9. Production Deployment

Move from local Streamlit to publicly accessible deployment:

- **Option A**: Streamlit Community Cloud (simple, free)
  - Trade-off: ChromaDB storage limits, may need Qdrant Cloud
- **Option B**: Hugging Face Spaces with Docker
  - Better for ML community visibility
- **Option C**: Cloud provider (AWS/GCP) with full control
  - Justifies if scaling beyond demo

Prerequisites for any deployment:
- Migrate ChromaDB embedded → Qdrant/Weaviate hosted
- Move SQLite → PostgreSQL (mentioned in section 5)
- Environment variable management for secrets
- HTTPS and domain setup

## Success Criteria

- Hosts (Alexandre Ottoni, Azaghal) correctly identified in 95%+ of their episodes
- Recurring guests automatically grouped across episodes
- Speaker-aware queries enabled in the Phase 7 interface