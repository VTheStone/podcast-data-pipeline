# Phase 6 — RAG + LLM

## Executive Summary

Phase 6 delivers the core value proposition of the project: end-to-end
question answering over the podcast catalog using Retrieval Augmented
Generation (RAG) with Large Language Models. Combines semantic search
with LLM synthesis to produce cited, faithful answers.

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

## Objectives

- Build the end-to-end RAG pipeline integrating Phases 4-5 with an LLM
- Engineer prompts that enforce source citation and prevent hallucination
- Establish an evaluation framework to measure quality systematically
- Identify quality limitations to feed the v2 backlog

## Pipeline Architecture

The complete RAG pipeline integrates components from previous phases:

1. **User Query** — natural language question
2. **Query Embedding** — same model used for indexing (Phase 5)
3. **Vector Search** — top-K chunks above similarity threshold
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

Evaluated trade-offs between cost, quality, latency, and infrastructure:

- **Groq selected** — free tier with generous quota, excellent latency via
  specialized LPU chips, quality comparable to proprietary models
- **Local LLM (Ollama)** rejected — RTX 3050 Ti VRAM (4GB) insufficient for
  8B+ models without aggressive quantization
- **OpenAI/Anthropic** rejected — cost not justified for portfolio project

### Prompt Engineering Strategy

System prompt enforces:

- **Source restriction** — only use provided chunks, no external knowledge
- **Mandatory citations** — format `[Trecho N, Ep: title, MM:SS]`
- **Honest refusal** — "Não encontrei essa informação" when context is insufficient
- **Consistent language** — Portuguese, matching the podcast corpus

User prompt structure separates context from question for better attention
allocation by the LLM.

### Similarity Threshold (min_similarity=0.5)

- Initial value of 0.3 produced false positives from unrelated episodes
- Tightened to 0.5 after observing cross-topic noise
- Trade-off: higher threshold = fewer chunks, potentially missing valid context
- Configurable via `RAG_MIN_SIMILARITY` in config

### Chunk Count (n_chunks=5)

- Standard for RAG with mid-size LLMs
- Balances context richness against prompt length
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

Each query manually evaluated for faithfulness, answer relevance, and
citation accuracy. See [evaluation-report.md](./evaluation-report.md) for
detailed results.

## Key Findings

### Strengths

- Thematic queries work excellently with high precision
- Honest refusal on out-of-scope queries prevents hallucination
- Cross-episode retrieval works for well-defined topics
- Citation format is consistently correct

### Weaknesses

- Named entity queries fail because embeddings don't prioritize proper nouns
  (e.g., "Quem é o Alexandre Ottoni" matches weak mentions across episodes
  instead of the introduction segment)
- Metadata queries like "what was the episode about" don't match content
  semantically
- Abstract comparative queries are too vague for precise retrieval
- Quantitative cross-episode queries (e.g., "in how many episodes...")
  underperform due to top-K=5 limit

## Configuration

| Parameter | Default | Where to configure |
|---|---|---|
| `LLM_MODEL` | llama-3.3-70b-versatile | `src/rag/config.py` |
| `LLM_TEMPERATURE` | 0.3 | `src/rag/config.py` |
| `LLM_MAX_TOKENS` | 1024 | `src/rag/config.py` |
| `RAG_MIN_SIMILARITY` | 0.5 | `src/rag/config.py` |
| `RAG_N_CHUNKS` | 5 | `src/rag/config.py` |
| `SYSTEM_PROMPT` | Portuguese, NerdCast-specific | `src/rag/prompts.py` |
| `GROQ_API_KEY` | env variable | `.env` |

See [REPLICATION_GUIDE.md](../REPLICATION_GUIDE.md).

## Known Limitations

- **Top-K=5 limits scope:** Quantitative queries underperform
- **Named entity searches:** Don't prioritize exact matches
- **Single LLM provider:** No fallback if Groq is down. v2 may add Ollama
- **No re-ranking:** Initial retrieval determines final results

These limitations are documented in the v2 backlog.

## Improvements Identified for v2

- Named Entity Recognition layer to boost proper name matches
- Episode summaries as additional RAGChunk metadata
- Query classification to route different query types optimally
- Cross-encoder re-ranking for better context precision
- RAGAS automated evaluation for regression testing
- Adaptive K (larger top-K for quantitative queries)

## Language Considerations

The RAG pipeline has multiple language touchpoints:

- **System prompt** must be in the response language for best results
- **LLM choice** affects language quality:
  - Llama 3.3 70B works well in English, Spanish, French, Portuguese
  - For better Portuguese specifically, consider Sabiá-3 or BERTimbau-tuned
  - For other languages, check model documentation
- **Citation format strings** like "Trecho", "Ep" are Portuguese; would
  need translation for other languages
- **Refusal messages** ("Não encontrei essa informação") are language-specific
- **Embedding model** must match the language of indexed content

When adapting to a different language, update:

1. `src/rag/prompts.py` — system prompt and labels
2. `src/rag/refusals.py` — out-of-scope responses
3. Possibly the LLM model in `config/podcasts/{name}.py`

## What This Enables

With Phase 6 complete, the project has a working end-to-end RAG system.
This unblocks:

- **Phase 7:** Streamlit interface — wraps this pipeline in a UI
- **MVP delivery:** users can ask questions and get cited answers
- **v2 quality optimization** — based on evaluation findings

## Next Steps

- Phase 7: Build Streamlit interface for end-user delivery
- Continue indexing remaining episodes as transcription completes

## How to Run

```bash
# Activate environment
.\venv\Scripts\Activate.ps1

# Run interactive Q&A
python -m src.rag.pipeline

# Run evaluation suite
python -m tests.evaluate_rag
```