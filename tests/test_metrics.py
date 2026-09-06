"""Comprehensive Unit Tests for NyayaSetu Evaluation Metrics.

Verifies mathematical correctness across:
- Hit@K
- Precision@K
- Recall@K (True Multi-Target)
- Reciprocal Rank (RR) & Mean Reciprocal Rank (MRR)
- Discounted Cumulative Gain (DCG) & Normalized DCG (nDCG@K)
- Edge cases: empty inputs, duplicate items, out-of-range K, missing targets
"""

import math
import os
import sys
import unittest

# Ensure root is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from evaluation.metrics.hit_at_k import calculate_hit_at_k, calculate_mean_hit_at_k
from evaluation.metrics.mrr import calculate_mrr, calculate_reciprocal_rank
from evaluation.metrics.ndcg import (
    calculate_dcg_at_k,
    calculate_idcg_at_k,
    calculate_mean_ndcg_at_k,
    calculate_ndcg_at_k,
)
from evaluation.metrics.precision_at_k import (
    calculate_mean_precision_at_k,
    calculate_precision_at_k,
)
from evaluation.metrics.recall_at_k import (
    calculate_mean_recall_at_k,
    calculate_recall_at_k,
)
import evaluation.metrics as legacy_metrics


class TestHitAtK(unittest.TestCase):
    """Unit tests for Hit@K metric."""

    def test_hit_at_rank_1(self):
        retrieved = ["doc_a", "doc_b", "doc_c"]
        relevant = {"doc_a"}
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=1), 1.0)
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=3), 1.0)

    def test_hit_at_rank_k(self):
        retrieved = ["doc_a", "doc_b", "doc_c"]
        relevant = {"doc_c"}
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=1), 0.0)
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=2), 0.0)
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=3), 1.0)

    def test_no_relevant_item(self):
        retrieved = ["doc_a", "doc_b", "doc_c"]
        relevant = {"doc_x", "doc_y"}
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=3), 0.0)

    def test_multiple_relevant_items(self):
        retrieved = ["doc_a", "doc_b", "doc_c"]
        relevant = {"doc_b", "doc_c"}
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=1), 0.0)
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=2), 1.0)
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=3), 1.0)

    def test_partial_match_mode(self):
        retrieved = ["The Constitution of India, 1950"]
        relevant = "Constitution of India"
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=1, partial_match=False), 0.0)
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=1, partial_match=True), 1.0)

    def test_mean_hit_at_k(self):
        all_retrieved = [
            ["doc_a", "doc_b"],
            ["doc_x", "doc_y"],
            ["doc_1", "doc_2"],
            ["doc_m", "doc_n"],
        ]
        all_relevant = [
            {"doc_a"},  # Hit@1 = 1.0
            {"doc_y"},  # Hit@1 = 0.0
            {"doc_1"},  # Hit@1 = 1.0
            {"doc_z"},  # Hit@1 = 0.0
        ]
        expected_mean = round((1.0 + 0.0 + 1.0 + 0.0) / 4, 4)
        self.assertEqual(calculate_mean_hit_at_k(all_retrieved, all_relevant, k=1), expected_mean)


class TestPrecisionAtK(unittest.TestCase):
    """Unit tests for Precision@K metric."""

    def test_precision_all_relevant(self):
        retrieved = ["doc_a", "doc_b"]
        relevant = {"doc_a", "doc_b"}
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=2), 1.0)

    def test_precision_none_relevant(self):
        retrieved = ["doc_a", "doc_b"]
        relevant = {"doc_x", "doc_y"}
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=2), 0.0)

    def test_precision_partial_relevance_documented_example(self):
        # Retrieved: [A, B, C], Relevant: [B, C, D]
        retrieved = ["A", "B", "C"]
        relevant = ["B", "C", "D"]
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=1), 0.0)
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=2), 0.5)
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=3), 0.6667)

    def test_fewer_results_than_k_conventions(self):
        retrieved = ["A", "B"]
        relevant = ["A", "B"]
        # Default evaluated_positions = min(K, |retrieved|) = 2
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=5, strict_k=False), 1.0)
        # strict_k=True divides by K = 5 -> 2/5 = 0.4
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=5, strict_k=True), 0.4)

    def test_mean_precision_at_k(self):
        all_retrieved = [
            ["A", "B"],  # 2/2 = 1.0
            ["A", "X"],  # 1/2 = 0.5
        ]
        all_relevant = [
            {"A", "B"},
            {"A", "B"},
        ]
        self.assertEqual(calculate_mean_precision_at_k(all_retrieved, all_relevant, k=2), 0.75)


class TestRecallAtK(unittest.TestCase):
    """Unit tests for true Multi-Target Recall@K metric."""

    def test_recall_documented_example(self):
        # Retrieved: [A, B, C, D], Relevant: [B, D, E] (total 3 unique relevant items)
        retrieved = ["A", "B", "C", "D"]
        relevant = ["B", "D", "E"]
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=1), 0.0)
        # At k=2: 'B' is retrieved -> 1 / 3 = 0.3333
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=2), 0.3333)
        # At k=3: 'B' is retrieved -> 1 / 3 = 0.3333
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=3), 0.3333)
        # At k=4: 'B' and 'D' retrieved -> 2 / 3 = 0.6667
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=4), 0.6667)

    def test_recall_single_target(self):
        retrieved = ["A", "B", "C"]
        relevant = "B"
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=1), 0.0)
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=2), 1.0)

    def test_recall_full_retrieval(self):
        retrieved = ["A", "B", "C"]
        relevant = ["A", "B", "C"]
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=3), 1.0)

    def test_recall_no_relevant_targets(self):
        retrieved = ["A", "B"]
        relevant = []
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=2), 0.0)

    def test_recall_duplicate_retrieved_items(self):
        retrieved = ["B", "B", "B"]
        relevant = ["B", "C"]
        # Unique retrieved in top 3 is {'B'} -> 1 out of 2 = 0.5
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=3), 0.5)

    def test_mean_recall_at_k(self):
        all_retrieved = [
            ["A", "B"],  # 2/2 = 1.0
            ["A", "C"],  # 1/2 = 0.5
        ]
        all_relevant = [
            {"A", "B"},
            {"A", "B"},
        ]
        self.assertEqual(calculate_mean_recall_at_k(all_retrieved, all_relevant, k=2), 0.75)


class TestMRR(unittest.TestCase):
    """Unit tests for Reciprocal Rank and MRR."""

    def test_first_item_relevant(self):
        retrieved = ["A", "B", "C"]
        relevant = ["A"]
        self.assertEqual(calculate_reciprocal_rank(retrieved, relevant), 1.0)

    def test_rank_2_relevant(self):
        retrieved = ["A", "B", "C"]
        relevant = ["B"]
        self.assertEqual(calculate_reciprocal_rank(retrieved, relevant), 0.5)

    def test_later_rank_documented_example(self):
        # Retrieved: [A, B, C, D], Relevant: [C, D] -> First match is C at rank 3 -> 1/3 = 0.3333
        retrieved = ["A", "B", "C", "D"]
        relevant = ["C", "D"]
        self.assertEqual(calculate_reciprocal_rank(retrieved, relevant), 0.3333)

    def test_no_relevant_found(self):
        retrieved = ["A", "B"]
        relevant = ["Z"]
        self.assertEqual(calculate_reciprocal_rank(retrieved, relevant), 0.0)

    def test_mrr_multi_query(self):
        all_retrieved = [
            ["A", "B"],  # RR = 1.0 (rank 1)
            ["X", "A"],  # RR = 0.5 (rank 2)
            ["X", "Y"],  # RR = 0.0 (none)
        ]
        all_relevant = [
            ["A"],
            ["A"],
            ["A"],
        ]
        # (1.0 + 0.5 + 0.0) / 3 = 0.5
        self.assertEqual(calculate_mrr(all_retrieved, all_relevant), 0.5)


class TestNDCG(unittest.TestCase):
    """Unit tests for DCG, IDCG, and nDCG@K."""

    def setUp(self):
        self.graded_rel = {
            "doc_a": 3.0,
            "doc_b": 2.0,
            "doc_c": 1.0,
            "doc_d": 0.0,
        }

    def test_perfect_ranking(self):
        retrieved = ["doc_a", "doc_b", "doc_c"]
        ndcg = calculate_ndcg_at_k(retrieved, self.graded_rel, k=3)
        self.assertEqual(ndcg, 1.0)

    def test_imperfect_ranking_manually_verified(self):
        # Retrieved: ["doc_c", "doc_b", "doc_a"], k = 3
        # Gains: 2^1-1 = 1, 2^2-1 = 3, 2^3-1 = 7
        # Discounts: log2(2)=1, log2(3)=1.5849625, log2(4)=2
        # DCG = 1/1 + 3/1.5849625 + 7/2 = 1.0 + 1.892789 + 3.5 = 6.392789
        # IDCG = 7/1 + 3/1.5849625 + 1/2 = 7.0 + 1.892789 + 0.5 = 9.392789
        # Expected nDCG = 6.392789 / 9.392789 = 0.680606 -> round 0.6806
        retrieved = ["doc_c", "doc_b", "doc_a"]
        ndcg = calculate_ndcg_at_k(retrieved, self.graded_rel, k=3)
        self.assertEqual(ndcg, 0.6806)

    def test_all_zero_relevance(self):
        retrieved = ["doc_x", "doc_y"]
        rel = {"doc_x": 0.0, "doc_y": 0.0}
        self.assertEqual(calculate_ndcg_at_k(retrieved, rel, k=2), 0.0)

    def test_binary_relevance_input(self):
        retrieved = ["doc_a", "doc_x"]
        binary_relevant = ["doc_a"]
        self.assertEqual(calculate_ndcg_at_k(retrieved, binary_relevant, k=2), 1.0)

    def test_mean_ndcg(self):
        all_retrieved = [
            ["doc_a", "doc_b"],  # perfect: 1.0
            ["doc_x", "doc_y"],  # none: 0.0
        ]
        all_rel = [
            {"doc_a": 2.0, "doc_b": 1.0},
            {"doc_a": 2.0, "doc_b": 1.0},
        ]
        self.assertEqual(calculate_mean_ndcg_at_k(all_retrieved, all_rel, k=2), 0.5)


class TestEdgeCasesAndBoundaryConditions(unittest.TestCase):
    """Test boundary conditions across all metrics."""

    def test_empty_retrieved_list(self):
        self.assertEqual(calculate_hit_at_k([], ["A"], k=5), 0.0)
        self.assertEqual(calculate_precision_at_k([], ["A"], k=5), 0.0)
        self.assertEqual(calculate_recall_at_k([], ["A"], k=5), 0.0)
        self.assertEqual(calculate_reciprocal_rank([], ["A"]), 0.0)
        self.assertEqual(calculate_ndcg_at_k([], {"A": 1.0}, k=5), 0.0)

    def test_empty_relevant_target(self):
        self.assertEqual(calculate_hit_at_k(["A"], [], k=1), 0.0)
        self.assertEqual(calculate_precision_at_k(["A"], [], k=1), 0.0)
        self.assertEqual(calculate_recall_at_k(["A"], [], k=1), 0.0)
        self.assertEqual(calculate_reciprocal_rank(["A"], []), 0.0)
        self.assertEqual(calculate_ndcg_at_k(["A"], {}, k=1), 0.0)

    def test_k_is_zero_or_negative(self):
        self.assertEqual(calculate_hit_at_k(["A"], ["A"], k=0), 0.0)
        self.assertEqual(calculate_hit_at_k(["A"], ["A"], k=-1), 0.0)
        self.assertEqual(calculate_precision_at_k(["A"], ["A"], k=0), 0.0)
        self.assertEqual(calculate_precision_at_k(["A"], ["A"], k=-2), 0.0)
        self.assertEqual(calculate_recall_at_k(["A"], ["A"], k=0), 0.0)
        self.assertEqual(calculate_recall_at_k(["A"], ["A"], k=-5), 0.0)
        self.assertEqual(calculate_ndcg_at_k(["A"], {"A": 1.0}, k=0), 0.0)

    def test_k_equals_1(self):
        retrieved = ["A", "B"]
        relevant = ["A"]
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=1), 1.0)
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=1), 1.0)
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=1), 1.0)

    def test_k_larger_than_retrieved(self):
        retrieved = ["A", "B"]
        relevant = ["B"]
        self.assertEqual(calculate_hit_at_k(retrieved, relevant, k=10), 1.0)
        # 1 relevant / 2 evaluated positions = 0.5
        self.assertEqual(calculate_precision_at_k(retrieved, relevant, k=10), 0.5)
        self.assertEqual(calculate_recall_at_k(retrieved, relevant, k=10), 1.0)


class TestLegacyMetricsCompatibility(unittest.TestCase):
    """Verify evaluation/metrics.py maintains exact backward compatibility."""

    def test_legacy_hit_at_k_returns_bool(self):
        res = legacy_metrics.calculate_hit_at_k(["Constitution of India"], "Constitution of India", 1)
        self.assertTrue(bool(res))
        self.assertEqual(float(res), 1.0)

    def test_legacy_calculate_precision(self):
        res = legacy_metrics.calculate_precision_at_k(["Constitution of India", "IPC"], "Constitution of India", 2)
        self.assertEqual(res, 0.5)

    def test_legacy_calculate_recall_corrected_to_true_recall(self):
        # Multi-target recall through legacy module
        res = legacy_metrics.calculate_recall_at_k(["BNS"], ["BNS", "BNSS"], 2)
        self.assertEqual(res, 0.5)

    def test_legacy_calculate_keyword_coverage(self):
        text = "This section specifies murder and culpable homicide under Part III."
        expected = ["murder", "Part III", "warrant"]
        # 2 found out of 3 = 0.6667
        cov = legacy_metrics.calculate_keyword_coverage(text, expected)
        self.assertEqual(cov, 0.6667)


if __name__ == "__main__":
    unittest.main()
