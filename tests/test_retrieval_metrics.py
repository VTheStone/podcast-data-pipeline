"""
Unit tests for tests/retrieval_metrics.py — verifies the metric
calculations themselves are correct, using hand-computed cases.
"""

from tests.retrieval_metrics import precision_at_k, recall_at_k, reciprocal_rank, r_precision


def test_precision_at_k_counts_relevant_among_top_k():
    retrieved = ["a", "b", "c", "d", "e"]
    expected = ["b", "d", "x", "y"]  # x, y don't appear in retrieved at all

    assert precision_at_k(retrieved, expected, k=5) == 2 / 5


def test_precision_at_k_only_considers_top_k_cutoff():
    retrieved = ["a", "b", "c", "d", "e"]
    expected = ["e"]  # only relevant id, but it's at position 5

    assert precision_at_k(retrieved, expected, k=3) == 0.0


def test_precision_at_k_zero_k_returns_zero():
    assert precision_at_k(["a"], ["a"], k=0) == 0.0


def test_recall_at_k_counts_fraction_of_all_relevant_found():
    retrieved = ["a", "b", "c"]
    expected = ["b", "x", "y", "z"]  # 4 relevant total, only "b" retrieved

    assert recall_at_k(retrieved, expected, k=3) == 1 / 4


def test_recall_at_k_finds_all_relevant():
    retrieved = ["a", "b", "c"]
    expected = ["a", "b"]

    assert recall_at_k(retrieved, expected, k=3) == 1.0


def test_recall_at_k_empty_expected_returns_zero():
    assert recall_at_k(["a", "b"], [], k=5) == 0.0


def test_reciprocal_rank_first_position():
    assert reciprocal_rank(["a", "b", "c"], ["a"]) == 1.0


def test_reciprocal_rank_third_position():
    assert reciprocal_rank(["a", "b", "c"], ["c"]) == 1 / 3


def test_reciprocal_rank_no_match_returns_zero():
    assert reciprocal_rank(["a", "b", "c"], ["x"]) == 0.0
    
def test_r_precision_uses_cutoff_equal_to_expected_size():
    retrieved = ["a", "b", "c", "d", "e"]
    expected = ["a", "x"]  # R=2, only top 2 retrieved are considered

    assert r_precision(retrieved, expected) == 1 / 2


def test_r_precision_perfect_when_all_relevant_are_in_top_r():
    retrieved = ["a", "b", "c"]
    expected = ["a", "b"]  # R=2, top 2 = ["a","b"], both relevant

    assert r_precision(retrieved, expected) == 1.0


def test_r_precision_empty_expected_returns_zero():
    assert r_precision(["a", "b"], []) == 0.0


def test_r_precision_is_stricter_than_precision_at_wider_k():
    # Relevant item is at rank 3, but R (size of expected) is only 1,
    # so R-Precision only looks at rank 1 and misses it — even though
    # a wider precision_at_k(k=3) would find it.
    retrieved = ["a", "b", "c"]
    expected = ["c"]

    assert r_precision(retrieved, expected) == 0.0
    assert precision_at_k(retrieved, expected, k=3) == 1 / 3