"""Unit tests for evaluate_routing metrics and safety calculations."""

import tempfile
import json
import unittest
from pathlib import Path

from evaluation.routing.evaluate_routing import evaluate_routing_dataset


class TestRoutingEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_evaluate_routing_metrics(self):
        mock_data = {
            "metadata": {
                "name": "Test Benchmark",
                "version": "1.0",
                "creation_date": "2026-09-06",
                "review_status": "provisional_research"
            },
            "routing_queries": [
                {
                    "query_id": "q1",
                    "question": "What is the punishment for theft under Section 303 of BNS?",
                    "gold_primary_regime": "BNS_SUBSTANTIVE",
                    "gold_candidate_regimes": ["BNS_SUBSTANTIVE"],
                    "query_type": "direct_statutory",
                    "annotation_source": "unit_test",
                    "review_status": "provisional_research"
                },
                {
                    "query_id": "q2",
                    "question": "When can police arrest someone without warrant under BNSS?",
                    "gold_primary_regime": "BNSS_PROCEDURAL",
                    "gold_candidate_regimes": ["BNSS_PROCEDURAL"],
                    "query_type": "direct_statutory",
                    "annotation_source": "unit_test",
                    "review_status": "provisional_research"
                },
                {
                    "query_id": "q3",
                    "question": "How to file a patent in the United States?",
                    "gold_primary_regime": "OUT_OF_SCOPE",
                    "gold_candidate_regimes": [],
                    "query_type": "out_of_scope",
                    "annotation_source": "unit_test",
                    "review_status": "provisional_research"
                }
            ]
        }

        test_file = Path(self.temp_dir.name) / "test_routing.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        metrics = evaluate_routing_dataset(str(test_file))

        self.assertEqual(metrics["total_queries"], 3)
        self.assertIn("top1_regime_accuracy", metrics)
        self.assertIn("top3_regime_coverage", metrics)
        self.assertIn("macro_f1", metrics)
        self.assertIn("incorrect_high_confidence_routing_rate", metrics)
        self.assertIn("confusion_matrix", metrics)


if __name__ == "__main__":
    unittest.main()
