"""Unit tests for Phase 6 Data Integrity, Leakage Prevention, and Experiment Configurations."""

import json
import unittest
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE6_DIR = REPO_ROOT / "evaluation" / "phase6"
CONFIGS_DIR = REPO_ROOT / "experiments" / "configs"

from evaluation.phase6.data_integrity import check_data_integrity


class TestPhase6DataIntegrity(unittest.TestCase):
    """Test suite ensuring zero split leakage, zero duplicate IDs, and config validity."""

    def test_01_zero_split_leakage_and_id_collisions(self):
        """Audit full benchmark for split leakage and ID collisions."""
        report = check_data_integrity()
        self.assertTrue(report["is_data_clean"], f"Data integrity failure: {report}")
        self.assertEqual(report["cross_split_leakage_count"], 0)
        self.assertEqual(report["id_collisions_count"], 0)
        self.assertEqual(report["exact_duplicates_count"], 0)

    def test_02_provenance_completeness(self):
        """Ensure 100% of benchmark queries have valid non-empty provenance."""
        for s_name in ["benchmark_train.json", "benchmark_validation.json", "benchmark_test.json"]:
            path = PHASE6_DIR / s_name
            with open(path, "r", encoding="utf-8") as f:
                queries = json.load(f)["queries"]
            for q in queries:
                self.assertTrue(bool(q.get("source_origin")), f"Missing provenance in {q['id']}")

    def test_03_ablation_experiment_configs(self):
        """Verify all Phase 6 experiment configs exist and specify valid switches."""
        cfg_files = [
            "phase6_baseline.yaml",
            "phase6_phase3.yaml",
            "phase6_phase4.yaml",
            "phase6_phase5.yaml",
            "phase6_full_pipeline.yaml",
        ]
        for cf in cfg_files:
            p = CONFIGS_DIR / cf
            self.assertTrue(p.exists(), f"Missing config file: {p}")
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self.assertIn("experiment_id", data)
            self.assertIn("pipeline", data)
            self.assertTrue(data["pipeline"].get("use_retrieval"))


if __name__ == "__main__":
    unittest.main()
