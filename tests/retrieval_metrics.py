"""
Pure retrieval-quality metrics: Precision@K, Recall@K, and per-query
reciprocal rank (mean is computed by the caller). No I/O, no ChromaDB —
takes plain lists of ids so these are fast and fully deterministic.
"""

def precision_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    """
    Fraction of the top-k retrieved ids that are actually relevant.
    Divides by k (not by however many ids were actually retrieved), so a
    search that returns fewer than k results is correctly penalized.

    Args:
        retrieved_ids: ids returned by the search, in rank order.
        expected_ids: ground-truth relevant ids for the query.
        k: cutoff — only the first k retrieved ids are considered.

    Returns:
        Precision in [0.0, 1.0]. 0.0 if k <= 0.
    """
    if k <= 0:
        return 0.0

    top_k = retrieved_ids[:k]
    relevant_retrieved = [rid for rid in top_k if rid in expected_ids]
    return len(relevant_retrieved) / k

def recall_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    """
    Fraction of all relevant ids that were retrieved within the top-k.

    Args:
        retrieved_ids: ids returned by the search, in rank order.
        expected_ids: ground-truth relevant ids for the query.
        k: cutoff — only the first k retrieved ids are considered.

    Returns:
        Recall in [0.0, 1.0]. 0.0 if there are no expected ids.
    """
    if not expected_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    relevant_retrieved = [rid for rid in top_k if rid in expected_ids]
    return len(relevant_retrieved) / len(expected_ids)

def reciprocal_rank(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """
    1 / (1-indexed rank of the first relevant id). 0.0 if none found.

    Args:
        retrieved_ids: ids returned by the search, in rank order.
        expected_ids: ground-truth relevant ids for the query.

    Returns:
        Reciprocal rank in [0.0, 1.0].
    """
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in expected_ids:
            return 1.0 / rank
    return 0.0

def r_precision(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """
    Precision evaluated at cutoff R = len(expected_ids) — the
    "ceiling-aware" companion to precision_at_k. Because the cutoff
    always matches the ground-truth size, this removes the artifact
    where precision_at_k can never reach 1.0 when len(expected_ids) < k.
    Recalculates automatically whenever expected_ids is edited — no
    hardcoded ceiling to keep in sync.

    Args:
        retrieved_ids: ids returned by the search, in rank order.
        expected_ids: ground-truth relevant ids for the query.

    Returns:
        R-Precision in [0.0, 1.0]. 0.0 if there are no expected ids.
    """
    if not expected_ids:
        return 0.0
    return precision_at_k(retrieved_ids, expected_ids, k=len(expected_ids))