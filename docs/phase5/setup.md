# Phase 5 Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| chromadb | 1.5+ | Embedded vector database |
| sentence-transformers | <5.0 | Embedding generation |
| torch | 2.6+cu124 | GPU inference |

> **Note:** sentence-transformers >= 5.0 requires torchcodec which has
> Windows compatibility issues. Pinned to <5.0.

### External Services

None for the MVP. Models download automatically from HuggingFace Hub on
first use (~1.1GB for mpnet-base-v2).

### Hardware

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| GPU | 2GB VRAM | 4GB+ VRAM | RTX 3050 Ti (4GB) |
| RAM | 8GB | 16GB | 16GB |
| Disk | 5GB free | — | ~2GB used by ChromaDB at 30K chunks |

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install Phase 5 dependencies
pip install chromadb "sentence-transformers<5.0"
```

## Configuration

### Environment Variables

None required for Phase 5.

### Podcast-Specific Configuration

No podcast-specific configuration in Phase 5. The embedding model and
distance metric work uniformly across podcasts and languages.

For language-specific quality improvements (v2), consider switching the
embedding model based on the podcast's language.

## Validation

After setup, verify embeddings work:

```bash
python tests/explore_embeddings.py
```

Expected output:

Loading model: paraphrase-multilingual-mpnet-base-v2
Device: CUDA (NVIDIA GeForce RTX 3050 Ti Laptop GPU)
Model loaded in 24.3s
Embedding shape: (4, 768)
Query: 'missão para a lua'
[0.730] Os astronautas vão voltar para a lua...
[0.599] O Alexandre Ottoni fala sobre exploração espacial...
[0.114] Episódio sobre RPG e Dungeons and Dragons.
Estimated indexing time for full dataset: ~1.5 hours

## Decision Log

**Decision:** ChromaDB over Pinecone or Qdrant for the MVP
**Context:** Need a vector DB for ~75K chunks
**Options considered:**
- **Pinecone** — SaaS, pay-per-use, fast but adds cost and latency
- **Qdrant self-hosted** — production-grade but requires Docker setup
- **Weaviate** — feature-rich but heavier
- **ChromaDB embedded** — file-based, zero setup, good HNSW
**Outcome:** ChromaDB embedded for the MVP. Migration to Qdrant or
Weaviate is on the v2 backlog when production deployment requires
multi-process access.

**Decision:** mpnet-base-v2 over bge-m3 or e5-large
**Context:** Need an embedding model that works on 4GB VRAM with reasonable quality
**Options considered:**
- **bge-m3** — 1024 dims, best multilingual quality, 2.3GB
- **e5-large** — 1024 dims, similar quality to bge-m3, 2.2GB
- **mpnet-multilingual** — 768 dims, good quality, 1.1GB, fits in 4GB VRAM
- **MiniLM-multilingual** — 384 dims, lower quality, very fast
**Outcome:** mpnet-multilingual chosen. A/B test with bge-m3 is on the
v2 backlog when GPU constraints relax.

**Decision:** sentence-transformers <5.0
**Context:** Version 5.0 added torchcodec as runtime dependency, which
breaks on Windows
**Options considered:**
- Install full FFmpeg shared build — complex, version-specific
- Pin to <5.0 — works, slightly older API
**Outcome:** Pinned to <5.0. Re-evaluate when torchcodec issues are resolved.

## Known Issues

- **First model load slow:** Initial download takes 1-2 minutes; subsequent
  loads are fast (~10s)
- **Symlink warning on Windows:** HuggingFace cache uses symlinks by default;
  Windows requires Developer Mode or admin rights. Functions correctly with
  warning otherwise

## Language Considerations

Phase 5 is largely language-agnostic at the architecture level. The choice
of embedding model determines language support:

- **Current model:** 50+ languages, mpnet-base-v2
- **For monolingual best quality:** use language-specific models (BERTimbau
  for Portuguese, etc)
- **For Asian languages:** bge-m3 generally outperforms mpnet
- **For low-resource languages:** check the model's language list before
  using

The vector store and search logic don't change per language.

## Platform Considerations

- **Windows:** Validated. Requires sentence-transformers <5.0
- **Linux:** Should work with any version of sentence-transformers
- **Mac:** Untested but should work with MPS device support
- **Production:** Embedded ChromaDB is single-process. Production
  deployment requires hosted vector DB