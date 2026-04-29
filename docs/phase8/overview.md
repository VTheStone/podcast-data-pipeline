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

## Database Schema

The schema for this phase is already in place (Speaker and SpeakerEmbedding
tables) since Phase 3, allowing incremental refinement without migrations.

## Success Criteria

- Hosts (Alexandre Ottoni, Azaghal) correctly identified in 95%+ of their episodes
- Recurring guests automatically grouped across episodes
- Speaker-aware queries enabled in the Phase 7 interface