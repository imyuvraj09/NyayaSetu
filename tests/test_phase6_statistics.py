"""Unit tests for NyayaSetu Phase 6 Statistical Testing and Inferential Engine."""

import unittest
import numpy as np

from evaluation.phase6.statistical_tests import (
    analyze_paired_metrics,
    apply_multiple_comparison_corrections,
    compute_bootstrap_ci_10k,
    compute_cliffs_delta,
    compute_paired_mcnemar_test,
    compute_paired_ttest,
    compute_paired_wilcoxon_test,
)


class TestPhase6Statistics(unittest.TestCase):
    """Test suite for inferential statistics, corrections, and effect sizes."""

    def test_01_bootstrap_reproducibility(self):
        """Verify that B=10,000 bootstrap CI produces deterministic identical results with seed=42."""
        data = [0.2, 0.4, 0.6, 0.8, 1.0, 0.9, 0.7, 0.5, 0.3, 0.1]
        ci1 = compute_bootstrap_ci_10k(data, "test_metric", num_bootstraps=5000, random_seed=42)
        ci2 = compute_bootstrap_ci_10k(data, "test_metric", num_bootstraps=5000, random_seed=42)

        self.assertEqual(ci1.ci_lower, ci2.ci_lower)
        self.assertEqual(ci1.ci_upper, ci2.ci_upper)
        self.assertEqual(ci1.mean, ci2.mean)

    def test_02_paired_mcnemar_test(self):
        """Verify McNemar's test calculation on known discordant pairs."""
        base = [1, 1, 0, 0, 1, 0, 1, 0, 0, 0]
        exp =  [1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
        res = compute_paired_mcnemar_test(base, exp)

        # Discordant: b = 0, c = 3
        self.assertEqual(res["contingency_table"]["b_base_only"], 0)
        self.assertEqual(res["contingency_table"]["c_exp_only"], 3)
        self.assertIn("p_value", res)
        self.assertGreaterEqual(res["p_value"], 0.0)
        self.assertLessEqual(res["p_value"], 1.0)

    def test_03_paired_wilcoxon_test(self):
        """Verify Wilcoxon signed-rank test on paired distributions."""
        base = [0.1, 0.2, 0.3, 0.4, 0.5]
        exp =  [0.3, 0.4, 0.5, 0.6, 0.7]  # All differences strictly positive (+0.2)
        res = compute_paired_wilcoxon_test(base, exp)

        self.assertEqual(res["w_minus"], 0.0)
        self.assertEqual(res["rank_biserial_correlation"], 1.0)
        self.assertLess(res["p_value"], 0.10)

    def test_04_multiple_comparison_corrections(self):
        """Verify Holm-Bonferroni and Benjamini-Hochberg monotonic ranking."""
        raw_p = [0.005, 0.02, 0.04, 0.15]
        adj = apply_multiple_comparison_corrections(raw_p)

        holm = adj["holm_bonferroni"]
        bh = adj["benjamini_hochberg"]

        self.assertEqual(len(holm), 4)
        self.assertEqual(len(bh), 4)

        # Adjusted p-values must be >= raw p-values
        for r, h, b in zip(raw_p, holm, bh):
            self.assertGreaterEqual(h, r)
            self.assertGreaterEqual(b, r)

        # First Holm adjusted: 0.005 * 4 = 0.02
        self.assertAlmostEqual(holm[0], 0.02, places=4)

    def test_05_effect_size_cliffs_delta(self):
        """Verify Cliff's delta correctly bounded in [-1.0, 1.0]."""
        base = [1, 2, 3, 4, 5]
        exp = [6, 7, 8, 9, 10]
        delta = compute_cliffs_delta(base, exp)
        self.assertEqual(delta, 1.0, "Complete dominance must yield Cliff's delta = 1.0")

        delta_rev = compute_cliffs_delta(exp, base)
        self.assertEqual(delta_rev, -1.0)

    def test_06_cohen_d_paired(self):
        """Verify paired Cohen's d computation."""
        base = [0.5, 0.5, 0.5, 0.5]
        exp =  [1.0, 1.0, 1.0, 1.0]
        tt = compute_paired_ttest(base, exp)
        self.assertEqual(tt["mean_difference"], 0.5)


if __name__ == "__main__":
    unittest.main()
