# Phase 6 RAG Evaluation Report

## Test Configuration

| Parameter | Value |
|---|---|
| Episodes indexed | 357 |
| Total chunks | 29,180 |
| Embedding model | paraphrase-multilingual-mpnet-base-v2 |
| LLM | llama-3.3-70b-versatile (Groq) |
| min_similarity | 0.5 |
| n_chunks | 5 |
| Evaluation date | 2026-05-01 |

## Performance Metrics

| Metric | Value |
|---|---|
| Total queries evaluated | 11 |
| Overall score | 64% (7/11 good or excellent) |
| Avg response time | 9.90s |
| Avg tokens per query | 2,706 |
| Total tokens used | 29,770 |

## Results by Query Type

| Type | Score | Notes |
|---|---|---|
| Factual (specific) | 2/3 ✅ | Fails on named entity queries |
| Comparative | 1/2 ✅ | Works for specific, fails for abstract |
| Resumo | 0/2 ❌ | Metadata queries don't match content |
| Causal | 2/2 ✅ | Honest when context is insufficient |
| Negativa | 2/2 ✅ | Correctly admits missing information |

## Key Findings

### Strengths
- Thematic queries work excellently (F02, F03, C01)
- Honest "I don't know" responses for out-of-scope queries (N02)
- Cross-episode retrieval works for well-defined topics (F03, N01)
- Citation format is consistently correct

### Weaknesses
- Named entity queries (F01): embeddings don't treat proper names
  as special entities — "Alexandre Ottoni" matches weak mentions
  across many episodes instead of the introduction segment
- Metadata queries (R01): "what was the episode about" has no
  semantic similarity with episode content
- Abstract comparative queries (C02): too vague to retrieve
  precisely

## Recommended Improvements

### Short term (before Phase 7)
- Add episode summary as RAGChunk metadata for metadata queries
- Tune min_similarity to 0.55 for better context precision

### Phase 8 backlog
- Named entity recognition to boost proper name matches
- Query classification to route metadata queries differently
- Re-ranking with cross-encoder for better context precision
- RAGAS automated evaluation for regression testing