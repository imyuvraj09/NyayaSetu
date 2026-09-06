"""Unit tests for system error analysis taxonomy."""

import unittest
from evaluation.error_analysis import (
    FailureCategory,
    classify_retrieval_failure,
    analyze_experiment_errors,
    summarize_failure_categories,
)


class TestErrorAnalysis(unittest.TestCase):
    """Verify error taxonomy and classification rules."""

    def test_ambiguity_classification(self):
        cat, _ = classify_retrieval_failure(
            query_id="ambiguous_01",
            question="What is the law here?",
            expected_target="",
            retrieved_docs=[],
            rank=None,
            is_ambiguous=True,
        )
        self.assertEqual(cat, FailureCategory.QUERY_AMBIGUITY)

    def test_missing_corpus_evidence(self):
        cat, _ = classify_retrieval_failure(
            query_id="foreign_01",
            question="What is the law under French Civil Code?",
            expected_target="French Civil Code",
            retrieved_docs=["Constitution of India"],
            rank=None,
            corpus_known_docs=["Constitution of India", "Bharatiya Nyaya Sanhita"],
        )
        self.assertEqual(cat, FailureCategory.MISSING_CORPUS_EVIDENCE)

    def test_statute_confusion_on_complete_miss(self):
        cat, _ = classify_retrieval_failure(
            query_id="bns_miss",
            question="What does Bharatiya Nyaya Sanhita state about theft?",
            expected_target="Bharatiya Nyaya Sanhita, 2023",
            retrieved_docs=["Information Technology Act, 2000", "Indian Evidence Act"],
            rank=None,
        )
        self.assertEqual(cat, FailureCategory.STATUTE_CONFUSION)

    def test_section_confusion_degraded_rank(self):
        cat, _ = classify_retrieval_failure(
            query_id="bns_degraded",
            question="What section prescribes punishment for murder under BNS?",
            expected_target="Bharatiya Nyaya Sanhita, 2023",
            retrieved_docs=["Code of Criminal Procedure", "Bharatiya Nyaya Sanhita, 2023"],
            rank=2,  # ranked at 2, displaced at rank 1
        )
        self.assertEqual(cat, FailureCategory.SECTION_CONFUSION)

    def test_analyze_experiment_errors(self):
        mock_preds = [
            {
                "query_id": "q1",
                "question": "Theft penalty",
                "expected_document": "BNS",
                "is_negative_or_out_of_scope": False,
                "retrieved_documents": ["BNS", "BNSS"],
                "reciprocal_rank": 1.0,  # Rank 1 hit -> not degraded
            },
            {
                "query_id": "q2",
                "question": "Murder penalty",
                "expected_document": "BNS",
                "is_negative_or_out_of_scope": False,
                "retrieved_documents": ["BNSS", "BNS"],
                "reciprocal_rank": 0.5,  # Rank 2 hit -> degraded!
            },
            {
                "query_id": "q3",
                "question": "Cyber theft",
                "expected_document": "IT Act",
                "is_negative_or_out_of_scope": False,
                "retrieved_documents": ["BNS", "BSA"],
                "reciprocal_rank": 0.0,  # Miss!
            }
        ]

        errors = analyze_experiment_errors(mock_preds, baseline_name="test_baseline")
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].query_id, "q2")
        self.assertEqual(errors[1].query_id, "q3")
        self.assertEqual(errors[0].analysis_type, "SYSTEM_ERROR_ANALYSIS")

        counts = summarize_failure_categories(errors)
        self.assertGreater(len(counts), 0)


if __name__ == "__main__":
    unittest.main()
