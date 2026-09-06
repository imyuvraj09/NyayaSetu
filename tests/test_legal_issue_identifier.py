"""Unit tests for LegalIssueIdentifier."""

import unittest
from research.fact_extraction import ConservativeFactExtractor
from research.fact_normalization import FactNormalizer
from research.legal_issue_identifier import LegalIssueIdentifier


class TestLegalIssueIdentifier(unittest.TestCase):
    def setUp(self):
        self.extractor = ConservativeFactExtractor()
        self.normalizer = FactNormalizer()
        self.identifier = LegalIssueIdentifier()

    def test_cyber_identity_theft_multi_issue(self):
        q = "Someone hacked my account and impersonated me to steal money online."
        facts = self.extractor.extract(q)
        normalized = self.normalizer.normalize(facts, q)
        issues = self.identifier.identify_issues(normalized, q)

        issue_ids = [i.issue_id for i in issues]
        self.assertIn("cyber_identity_theft_personation", issue_ids)
        self.assertIn("cyber_unauthorized_access", issue_ids)

        top_issue = issues[0]
        self.assertGreaterEqual(top_issue.confidence, 0.50)
        self.assertTrue(len(top_issue.supporting_facts) > 0)

    def test_procedural_arrest_powers(self):
        q = "When can a police officer arrest an accused without warrant under BNSS?"
        facts = self.extractor.extract(q)
        normalized = self.normalizer.normalize(facts, q)
        issues = self.identifier.identify_issues(normalized, q)

        issue_ids = [i.issue_id for i in issues]
        self.assertIn("procedural_police_arrest_powers", issue_ids)

    def test_evidentiary_electronic_record(self):
        q = "What are the rules for admissibility of electronic records under Bharatiya Sakshya Adhiniyam?"
        facts = self.extractor.extract(q)
        normalized = self.normalizer.normalize(facts, q)
        issues = self.identifier.identify_issues(normalized, q)

        issue_ids = [i.issue_id for i in issues]
        self.assertIn("evidentiary_electronic_records_admissibility", issue_ids)

    def test_fallback_on_unspecified_inquiry(self):
        q = "What is the general legal procedure in India?"
        facts = self.extractor.extract(q)
        normalized = self.normalizer.normalize(facts, q)
        issues = self.identifier.identify_issues(normalized, q)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_id, "general_legal_inquiry")
        self.assertLess(issues[0].confidence, 0.40)


if __name__ == "__main__":
    unittest.main()
