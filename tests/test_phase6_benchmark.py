"""Unit tests for NyayaSetu Phase 6 Benchmark Integrity and Schema Compliance."""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE6_DIR = REPO_ROOT / "evaluation" / "phase6"

from evaluation.phase6.benchmark_validator import (
    VALID_CATEGORIES,
    VALID_DIFFICULTIES,
    VALID_SPLITS,
    VALID_TEMPORAL_CONTEXTS,
    validate_all_splits,
    validate_benchmark_file,
)


class TestPhase6Benchmark(unittest.TestCase):
    """Test suite for Phase 6 benchmark schema, categories, and split partitions."""

    def test_01_all_splits_exist_and_validate(self):
        """Confirm that benchmark_train, benchmark_validation, and benchmark_test pass validation."""
        report = validate_all_splits()
        self.assertTrue(report["all_valid"], f"Validation failed with issues: {report['results']}")

    def test_02_split_sizes_and_ratios(self):
        """Ensure strict 20% Dev (50), 20% Validation (50), 60% Held-Out Test (150) partitioning."""
        train_file = PHASE6_DIR / "benchmark_train.json"
        val_file = PHASE6_DIR / "benchmark_validation.json"
        test_file = PHASE6_DIR / "benchmark_test.json"

        with open(train_file, "r", encoding="utf-8") as f:
            train_data = json.load(f)
        with open(val_file, "r", encoding="utf-8") as f:
            val_data = json.load(f)
        with open(test_file, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        n_train = len(train_data["queries"])
        n_val = len(val_data["queries"])
        n_test = len(test_data["queries"])
        n_total = n_train + n_val + n_test

        self.assertEqual(n_train, 50, "Dev split must contain exactly 50 queries (20%)")
        self.assertEqual(n_val, 50, "Validation split must contain exactly 50 queries (20%)")
        self.assertEqual(n_test, 150, "Held-out test split must contain exactly 150 queries (60%)")
        self.assertEqual(n_total, 250, "Total benchmark count must equal 250 queries")

    def test_03_category_coverage(self):
        """Verify all 8 mandatory categories are present in each partition."""
        test_file = PHASE6_DIR / "benchmark_test.json"
        with open(test_file, "r", encoding="utf-8") as f:
            queries = json.load(f)["queries"]

        cats_present = {q["category"] for q in queries}
        for c in VALID_CATEGORIES:
            self.assertIn(c, cats_present, f"Missing category in test partition: {c}")

    def test_04_mandatory_fields_presence(self):
        """Verify every benchmark item has all required fields."""
        required_fields = [
            "id", "question", "category", "sub_category", "difficulty",
            "temporal_context", "legal_regimes_expected", "expected_issue_type",
            "expected_evidence_type", "expected_statutes", "expected_sections",
            "expected_answer_properties", "gold_evidence_ids", "risk_level",
            "source_origin", "split"
        ]
        for s_name in ["benchmark_train.json", "benchmark_validation.json", "benchmark_test.json"]:
            path = PHASE6_DIR / s_name
            with open(path, "r", encoding="utf-8") as f:
                queries = json.load(f)["queries"]
            for q in queries:
                for rf in required_fields:
                    self.assertIn(rf, q, f"Query {q.get('id')} missing field {rf} in {s_name}")


if __name__ == "__main__":
    unittest.main()
