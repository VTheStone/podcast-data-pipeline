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
- **RAGAS Evaluation**: deferred. Implemented as a custom LLM-as-judge
  instead (`tests/generation_metrics.py`), using the Groq client already
  in the project. RAGAS pulls ~30 packages centered on LangChain
  (langchain-core, langgraph, langsmith) plus `datasets`/`pyarrow` — and
  `pyarrow` already caused a `Windows fatal exception: access violation`
  during test collection in this environment. The custom judge keeps the
  same industry-standard metric vocabulary (faithfulness, answer
  relevancy, answer correctness) without inheriting a framework this
  project doesn't otherwise use. Revisit if the evaluation needs grow
  beyond three metrics.

### Evaluation Baseline (M3 + M4)

First automated measurement over the 11-query golden dataset
(`tests/rag_evaluation_queries.py`), establishing the baseline that
future retrieval work is measured against.

**Retrieval** (`tests/evaluate_retrieval.py`, 5 extractive queries, K=10):

| Metric | Value |
|---|---|
| Avg Precision@10 | 0.100 |
| Avg Recall@10 | 0.479 |
| MRR | 0.540 |
| Avg R-Precision | 0.279 |

**Generation** (`tests/evaluate_generation.py`, 11 queries, LLM-as-judge):

| Metric | Value |
|---|---|
| Faithfulness | 4.82 / 5 |
| Answer Relevancy | 4.73 / 5 |
| Answer Correctness | 3.45 / 5 |

**Primary finding:** high faithfulness with low correctness, combined
with 0.479 recall, localizes the bottleneck to **retrieval, not
generation** — the model answers faithfully from what it receives, but
retrieval doesn't surface enough relevant chunks. Prompt tuning will not
move these numbers; the re-ranking, adaptive-K and NER items above will.
CA02 is the clearest failure: 0.00 recall in M3 and correctness 2/5 in
M4, confirmed independently by both measurements.

### Known limitations of the current evaluation

These affect how much weight the numbers above can carry:

- **Self-evaluation bias**: the judge model is
  `llama-3.3-70b-versatile` — the same model that generates the answers.
  Models tend to favor their own output style, so faithfulness and
  relevancy scores likely skew optimistic. Using a different model as
  judge would harden this.
- **Unreachable reference answers**: F01, R02 and C02 have gold answers
  written from information that is not in the indexed corpus. F01 asks
  who the host is, but M0 confirmed the corpus contains no biographical
  segment about him (self-introductions are always the standard jingle);
  R02 and C02 were written from *episode titles*, which are not indexed
  in ChromaDB — only transcript text is. Their low correctness scores
  measure the gap in the ground truth, not only a system failure.
- **Sample size**: 11 queries total, 5 of them extractive. One outlier
  moves any average substantially. This is a baseline, not a
  statistically robust benchmark.
- **Score variance**: LLM-as-judge is not fully deterministic even at
  `temperature=0.0`. Treat these as monitored metrics with a regression
  tolerance, never as binary pass/fail gates.

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

### 10. Functional Model Review

Address limitations identified during Phase 7 testing:

**Quantitative queries across multiple episodes**

The current architecture retrieves top-K chunks (default 5) before LLM
synthesis. Queries that require counting or surveying many episodes
fail because the retrieval window is too narrow:

- "Quantos episódios falam sobre Disney?"
- "Em quantos episódios o Azaghal apareceu?"
- "Quais foram todos os episódios de RPG?"

**Proposed improvements:**

- **Adaptive K**: detect quantitative queries via classification and
  expand retrieval window (e.g., K=50 for counting queries)
- **Aggregation layer**: pre-compute episode-level metadata (topics,
  recurring themes, guests) to answer survey questions without scanning
  all chunks
- **Two-stage retrieval**:
  - Stage 1: identify candidate episodes via metadata search
  - Stage 2: confirm with chunk-level retrieval
- **Query intent classification**: route different query types to
  different retrieval strategies (factual, quantitative, summary, etc.)

This is part of the broader Functional Model Review effort — systematic
identification of query patterns where the current pipeline underperforms,
and architectural changes to address them.

## Success Criteria

- Hosts (Alexandre Ottoni, Azaghal) correctly identified in 95%+ of their episodes
- Recurring guests automatically grouped across episodes
- Speaker-aware queries enabled in the Phase 7 interface