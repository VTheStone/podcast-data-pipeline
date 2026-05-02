"""
Batch evaluation script for the RAG pipeline.
Runs all queries from the golden dataset and generates a report.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from loguru import logger

from src.rag.pipeline import RAGPipeline
from tests.rag_evaluation_queries import EVALUATION_QUERIES


def run_evaluation():
    """Runs all evaluation queries and generates a report."""
    logger.info("Initializing RAG pipeline for evaluation...")
    pipeline = RAGPipeline()

    results = []
    total_tokens = 0
    total_time = 0

    print("\n" + "=" * 70)
    print("RAG PIPELINE EVALUATION")
    print(f"Queries: {len(EVALUATION_QUERIES)}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    for q in EVALUATION_QUERIES:
        print(f"\n[{q['id']}] {q['type'].upper()} — {q['query']}")
        print(f"Notes: {q['notes']}")
        print("-" * 60)

        start = time.time()
        result = pipeline.answer(q["query"])
        elapsed = time.time() - start

        total_tokens += result.get("tokens_used", 0)
        total_time += elapsed

        # Print answer
        print(f"Answer:\n{result['answer']}")
        print(f"\nSources ({result['chunks_used']} chunks):")
        for source in result["sources"]:
            print(f"  [{source['time']}] {source['episode_title'][:60]} (sim: {source['similarity']})")
        print(f"\nTime: {elapsed:.2f}s | Tokens: {result.get('tokens_used', 'N/A')}")

        # Manual evaluation prompts
        print("\nManual evaluation:")
        print("  Faithfulness    (1=fail, 2=partial, 3=good): ?")
        print("  Answer Relevance(1=fail, 2=partial, 3=good): ?")
        print("  Citation Accuracy(1=fail, 2=partial, 3=good): ?")

        results.append({
            "id": q["id"],
            "type": q["type"],
            "query": q["query"],
            "answer": result["answer"],
            "sources": result["sources"],
            "chunks_used": result["chunks_used"],
            "elapsed_seconds": round(elapsed, 2),
            "tokens_used": result.get("tokens_used", 0),
            "expected_episodes": q["expected_episodes"],
            "notes": q["notes"],
        })

    # Summary
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total queries: {len(EVALUATION_QUERIES)}")
    print(f"Total tokens used: {total_tokens:,}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Avg time per query: {total_time/len(EVALUATION_QUERIES):.2f}s")
    print(f"Avg tokens per query: {total_tokens//len(EVALUATION_QUERIES):,}")

    # Save results to JSON
    output_path = Path("docs/phase6/evaluation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.success(f"Results saved to {output_path}")

    return results


if __name__ == "__main__":
    run_evaluation()