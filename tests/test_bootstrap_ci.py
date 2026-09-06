"""Unit tests for non-parametric bootstrap confidence interval estimation."""

import unittest
import numpy as np

from evaluation.statistics.bootstrap_ci import (
    BootstrapResult,
    compute_bootstrap_ci,
    compute_experiment_bootstrap_cis,
)


class TestBootstrapCI(unittest.TestCase):
    """Verify bootstrap confidence interval computation."""

    def test_deterministic_seed(self):
        """Verify that identical seeds produce identical confidence intervals."""
        values = [1.0, 1.0, 0.0, 1.0, 0.5, 1.0, 0.0, 1.0, 1.0, 0.5]
        res1 = compute_bootstrap_ci(values, metric_name="Hit@1", num_bootstraps=500, random_seed=42)
        res2 = compute_bootstrap_ci(values, metric_name="Hit@1", num_bootstraps=500, random_seed=42)

        self.assertEqual(res1.mean, res2.mean)
        self.assertEqual(res1.ci_lower, res2.ci_lower)
        self.assertEqual(res1.ci_upper, res2.ci_upper)
        self.assertEqual(res1.standard_error, res2.standard_error)

    def test_seed_variation_changes_samples(self):
        """Verify that distinct seeds produce slightly different estimates."""
        values = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
        res1 = compute_bootstrap_ci(values, metric_name="MRR", num_bootstraps=500, random_seed=42)
        res2 = compute_bootstrap_ci(values, metric_name="MRR", num_bootstraps=500, random_seed=999)

        self.assertEqual(res1.mean, res2.mean)  # point mean is identical
        # CIs should be close but not necessarily identical due to different resamples
        self.assertAlmostEqual(res1.ci_lower, res2.ci_lower, delta=0.1)

    def test_degenerate_constant_array(self):
        """Verify handling of zero-variance constant sequences."""
        values = [1.0] * 20
        res = compute_bootstrap_ci(values, metric_name="Hit@5", num_bootstraps=500)

        self.assertEqual(res.mean, 1.0)
        self.assertEqual(res.ci_lower, 1.0)
        self.assertEqual(res.ci_upper, 1.0)
        self.assertEqual(res.standard_error, 0.0)

    def test_empty_array(self):
        """Verify empty array edge case."""
        res = compute_bootstrap_ci([], metric_name="Hit@1")
        self.assertEqual(res.mean, 0.0)
        self.assertEqual(res.num_queries, 0)

    def test_interval_contains_point_mean(self):
        """Verify that point mean lies within the 95% confidence interval."""
        np.random.seed(123)
        values = np.random.uniform(0.6, 1.0, size=39).tolist()
        res = compute_bootstrap_ci(values, metric_name="MRR", num_bootstraps=1000, random_seed=42)

        self.assertTrue(res.ci_lower <= res.mean <= res.ci_upper)
        self.assertEqual(res.num_queries, 39)

    def test_experiment_predictions_aggregation(self):
        """Verify extraction and calculation across prediction objects."""
        mock_predictions = [
            {
                "query_id": f"q_{i}",
                "expected_document": "BNS",
                "is_negative_or_out_of_scope": False,
                "hit_at_1": 1.0 if i % 3 != 0 else 0.0,
                "hit_at_5": 1.0,
                "reciprocal_rank": 1.0 if i % 3 != 0 else 0.33,
                "ndcg_at_5": 0.95,
            }
            for i in range(1, 10)
        ]
        # Add out-of-scope query
        mock_predictions.append({
            "query_id": "neg_1",
            "expected_document": None,
            "is_negative_or_out_of_scope": True,
            "hit_at_1": 0.0,
        })

        results = compute_experiment_bootstrap_cis(
            predictions=mock_predictions,
            num_bootstraps=500,
            random_seed=42,
            statutory_only=True,
        )

        self.assertIn("Hit@1", results)
        self.assertIn("Hit@5", results)
        self.assertIn("MRR", results)
        self.assertIn("nDCG@5", results)
        self.assertEqual(results["Hit@1"].num_queries, 9)  # 10 minus 1 out of scope


if __name__ == "__main__":
    unittest.main()
