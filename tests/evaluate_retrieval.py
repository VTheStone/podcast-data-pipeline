"""
Retrieval evaluation script (M3).
Runs the golden dataset's extractive queries against the real ChromaDB
index and reports Precision@K, Recall@K, MRR and R-Precision. No LLM
call — this measures search quality in isolation from generation
quality (M4).
"""

import json
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.processing.searcher import SemanticSearcher
from tests.retrieval_metrics import precision_at_k, recall_at_k, reciprocal_rank, r_precision
from tests.rag_evaluation_queries import EVALUATION_QUERIES

# Larger than RAG_N_CHUNKS (5, in config/default.py) on purpose — gives
# visibility into whether relevant chunks exist just past the production
# cutoff, not just whether the production config finds them.
K = 10


def run_evaluation():
    """Runs retrieval metrics for every extractive golden query."""
    extractive_queries = [q for q in EVALUATION_QUERIES if q["expected_chunk_ids"]]

    if not extractive_queries:
        logger.warning("No queries with expected_chunk_ids found — nothing to evaluate")
        return []

    logger.info("Loading embedding model and connecting to ChromaDB...")
    searcher = SemanticSearcher()

    results = []

    print("\n" + "=" * 70)
    print("RETRIEVAL EVALUATION")
    print(f"Queries: {len(extractive_queries)} (extractive only)")
    print(f"K: {K}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    for q in extractive_queries:
        expected_ids = q["expected_chunk_ids"]
        # Search for at least as many results as the ground truth has,
        # so R-Precision is never truncated below its own cutoff.
        search_n = max(K, len(expected_ids))

        retrieved = searcher.search(q["query"], n_results=search_n)
        retrieved_ids = [r["id"] for r in retrieved]

        precision = precision_at_k(retrieved_ids, expected_ids, K)
        recall = recall_at_k(retrieved_ids, expected_ids, K)
        rr = reciprocal_rank(retrieved_ids, expected_ids)
        rp = r_precision(retrieved_ids, expected_ids)

        print(f"\n[{q['id']}] {q['query']}")
        print(f"  Precision@{K}: {precision:.2f}")
        print(f"  Recall@{K}:    {recall:.2f}")
        print(f"  Reciprocal Rank: {rr:.2f}")
        print(f"  R-Precision (R={len(expected_ids)}): {rp:.2f}")

        results.append({
            "id": q["id"],
            "query": q["query"],
            "k": K,
            "r": len(expected_ids),
            "precision_at_k": round(precision, 4),
            "recall_at_k": round(recall, 4),
            "reciprocal_rank": round(rr, 4),
            "r_precision": round(rp, 4),
            "retrieved_ids": retrieved_ids[:K],
            "expected_ids": expected_ids,
        })

    avg_precision = sum(r["precision_at_k"] for r in results) / len(results)
    avg_recall = sum(r["recall_at_k"] for r in results) / len(results)
    mrr = sum(r["reciprocal_rank"] for r in results) / len(results)
    avg_r_precision = sum(r["r_precision"] for r in results) / len(results)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Avg Precision@{K}:  {avg_precision:.3f}")
    print(f"Avg Recall@{K}:     {avg_recall:.3f}")
    print(f"MRR:                {mrr:.3f}")
    print(f"Avg R-Precision:    {avg_r_precision:.3f}")

    output_path = Path("docs/phase8/retrieval_evaluation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "k": K,
            "avg_precision_at_k": round(avg_precision, 4),
            "avg_recall_at_k": round(avg_recall, 4),
            "mrr": round(mrr, 4),
            "avg_r_precision": round(avg_r_precision, 4),
            "per_query": results,
        }, f, ensure_ascii=False, indent=2)
    logger.success(f"Results saved to {output_path}")

    return results


if __name__ == "__main__":
    run_evaluation()