# Phase 6 Final Report — RAG + LLM

## Executive Summary

Phase 6 delivers the core value proposition of the project: end-to-end
question answering over the NerdCast podcast catalog using Retrieval
Augmented Generation (RAG) with Large Language Models.

| Metric | Value |
|---|---|
| Episodes indexed | 357 (33.9% of catalog) |
| Total chunks searchable | 29,180 |
| LLM model | llama-3.3-70b-versatile (Groq) |
| Embedding model | paraphrase-multilingual-mpnet-base-v2 |
| Vector DB | ChromaDB embedded |
| Avg response time | 9.9s end-to-end |
| Avg tokens per query | 2,706 |
| Evaluation score | 64% good or excellent (11 queries tested) |

## Pipeline Architecture

The complete RAG pipeline integrates components from previous phases:

1. **User Query** — natural language question in Portuguese
2. **Query Embedding** — same model used for indexing (Phase 5)
3. **Vector Search** — top-5 chunks above 0.5 similarity threshold
4. **Prompt Construction** — chunks + system instructions + query
5. **LLM Generation** — Groq API with llama-3.3-70b
6. **Response with Citations** — answer in prose with source references

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Prompts | `src/rag/prompts.py` | ✅ Complete |
| RAG Pipeline | `src/rag/pipeline.py` | ✅ Complete |
| Evaluation Suite | `tests/rag_evaluation_queries.py` | ✅ Complete |
| Evaluation Runner | `tests/evaluate_rag.py` | ✅ Complete |

## Architectural Decisions

### LLM Choice — Groq API with llama-3.3-70b-versatile

Evaluated trade-offs between cost, quality, latency and infrastructure:

- **Groq selected** for free tier with generous quota, excellent latency
  via specialized LPU chips, and quality comparable to proprietary models
- **Local LLM (Ollama)** rejected because RTX 3050 Ti VRAM (4GB)
  insufficient for 8B+ models without aggressive quantization
- **OpenAI/Anthropic** rejected for cost — not justified for portfolio project

### Prompt Engineering Strategy

System prompt enforces:

- **Source restriction**: only use provided chunks, no external knowledge
- **Mandatory citations**: format `[Trecho N, Ep: title, MM:SS]`
- **Honest refusal**: "Not found in episodes" when context is insufficient
- **Consistent language**: Portuguese (matches corpus)

User prompt structure separates context from question for better
attention allocation by the LLM.

### Similarity Threshold (min_similarity=0.5)

- Initial value of 0.3 produced false positives (unrelated episodes)
- Tightened to 0.5 after observing cross-topic noise
- Trade-off: higher threshold = fewer chunks, potentially missing valid context
- Configurable via `RAG_MIN_SIMILARITY` in config

### Chunk Count (n_chunks=5)

- Standard for RAG with mid-size LLMs
- Balances context richness vs prompt length
- Each chunk averages ~440 tokens, total ~2,200 tokens of context

## Evaluation Methodology

Custom golden dataset with 11 queries across 5 categories:

| Category | Count | Purpose |
|---|---|---|
| Factual | 3 | Specific information retrieval |
| Comparative | 2 | Multi-source synthesis |
| Resumo | 2 | Episode-level summarization |
| Causal | 2 | Reasoning and explanation |
| Negativa | 2 | Out-of-scope handling |

Each query manually evaluated for faithfulness, answer relevance,
and citation accuracy.

## Key Findings

### Strengths
- Thematic queries (F02, F03, C01) work excellently with high precision
- Honest refusal on out-of-scope queries (N02) prevents hallucination
- Cross-episode retrieval works for well-defined topics
- Citation format is consistently correct

### Weaknesses
- Named entity queries (F01) fail because embeddings don't prioritize
  proper nouns as special entities
- Metadata queries (R01) like "what was the episode about" don't match
  content semantically
- Abstract comparative queries (C02) are too vague for precise retrieval

## Improvements Identified for Phase 8

- Named Entity Recognition layer to boost proper name matches
- Episode summaries as additional RAGChunk metadata
- Query classification to route different query types optimally
- Cross-encoder re-ranking for better context precision
- RAGAS automated evaluation for regression testing

## What This Enables

With Phase 6 complete, the project has a working end-to-end RAG system.
This unblocks:

- **Phase 7**: Streamlit interface — wraps this pipeline in a UI
- **Phase 8**: Quality optimization — based on evaluation findings
- **MVP delivery**: users can ask questions and get cited answers

## Next Steps

- Phase 7: Build Streamlit interface for end-user delivery
- Continue indexing remaining episodes as transcription completes