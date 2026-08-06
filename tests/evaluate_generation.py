"""
Generation evaluation script (M4).
Runs every golden query through the real RAG pipeline, then scores each
answer with an LLM judge on faithfulness, answer relevancy and answer
correctness. Complements M3 (tests/evaluate_retrieval.py), which measures
search quality in isolation — this measures what the LLM does with it.

Costs two LLM calls per query (one to answer, one to judge), so this is
run on demand, not on every commit.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from groq import Groq
from loguru import logger

from config import settings
from src.rag.pipeline import RAGPipeline
from tests.generation_metrics import SCORE_FIELDS, judge_answer
from tests.rag_evaluation_queries import EVALUATION_QUERIES


def run_evaluation():
    """Answers and judges every golden query that has a reference answer."""
    queries = [q for q in EVALUATION_QUERIES if q["reference_answer"]]

    if not queries:
        logger.warning("No queries with a reference_answer — nothing to evaluate")
        return []

    logger.info("Initializing RAG pipeline and judge client...")
    pipeline = RAGPipeline()
    judge_client = Groq(api_key=settings.GROQ_API_KEY)

    results = []

    print("\n" + "=" * 70)
    print("GENERATION EVALUATION (LLM-as-judge)")
    print(f"Queries: {len(queries)}")
    print(f"Judge model: {settings.LLM_MODEL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    for q in queries:
        result = pipeline.answer(q["query"])
        scores = judge_answer(
            client=judge_client,
            model=settings.LLM_MODEL,
            question=q["query"],
            context_chunks=result["context_chunks"],
            answer=result["answer"],
            reference_answer=q["reference_answer"],
        )

        print(f"\n[{q['id']}] {q['type'].upper()} — {q['query']}")
        print(f"  Faithfulness:       {scores['faithfulness']}/5")
        print(f"  Answer Relevancy:   {scores['answer_relevancy']}/5")
        print(f"  Answer Correctness: {scores['answer_correctness']}/5")
        print(f"  Judge: {scores['reasoning']}")

        results.append({
            "id": q["id"],
            "type": q["type"],
            "query": q["query"],
            "answer": result["answer"],
            "reference_answer": q["reference_answer"],
            "chunks_used": result["chunks_used"],
            **{field: scores[field] for field in SCORE_FIELDS},
            "judge_reasoning": scores["reasoning"],
        })

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    averages = {
        field: sum(r[field] for r in results) / len(results)
        for field in SCORE_FIELDS
    }
    for field in SCORE_FIELDS:
        print(f"Avg {field.replace('_', ' ').title():<20} {averages[field]:.2f}/5")

    # Per-category breakdown — shows which query types the system handles
    # well, matching the categories defined in the golden dataset.
    by_type = defaultdict(list)
    for r in results:
        by_type[r["type"]].append(r)

    print("\nBy query type:")
    for query_type, items in sorted(by_type.items()):
        type_avg = sum(
            item[field] for item in items for field in SCORE_FIELDS
        ) / (len(items) * len(SCORE_FIELDS))
        print(f"  {query_type:<14} {type_avg:.2f}/5  (n={len(items)})")

    output_path = Path("docs/phase8/generation_evaluation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "judge_model": settings.LLM_MODEL,
            "averages": {field: round(averages[field], 4) for field in SCORE_FIELDS},
            "per_query": results,
        }, f, ensure_ascii=False, indent=2)
    logger.success(f"Results saved to {output_path}")

    return results


if __name__ == "__main__":
    run_evaluation()