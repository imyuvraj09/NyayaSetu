"""Unit tests for ConservativeFactExtractor."""

import unittest
from research.fact_extraction import ConservativeFactExtractor


class TestFactExtraction(unittest.TestCase):
    def setUp(self):
        self.extractor = ConservativeFactExtractor()

    def test_empty_and_whitespace_query(self):
        facts = self.extractor.extract("")
        self.assertTrue(facts.is_empty())
        self.assertEqual(len(facts.actions), 0)

        facts_ws = self.extractor.extract("   \n\t  ")
        self.assertTrue(facts_ws.is_empty())

    def test_phone_theft_fact_pattern(self):
        q = "Someone stole my mobile phone and later sold it online."
        facts = self.extractor.extract(q)

        self.assertIn("unknown_person", facts.actors)
        self.assertIn("theft", facts.actions)
        self.assertIn("sale", facts.actions)
        self.assertIn("mobile_phone", facts.objects)
        self.assertIn("phone_theft", facts.events)
        # Verify zero hallucinated facts:
        self.assertIsNone(facts.location_context)
        self.assertEqual(len(facts.statutory_references), 0)

    def test_direct_statutory_reference(self):
        q = "What is the punishment for theft under Section 303 of the Bharatiya Nyaya Sanhita?"
        facts = self.extractor.extract(q)

        self.assertIn("BNS", facts.statutory_references)
        self.assertIn("theft", facts.actions)
        self.assertIn("section_303", facts.explicit_legal_terms)

    def test_cyber_hacking_impersonation(self):
        q = "An unknown person hacked into my computer account and impersonated me online."
        facts = self.extractor.extract(q)

        self.assertIn("unknown_person", facts.actors)
        self.assertIn("cyber_access", facts.actions)
        self.assertIn("impersonation", facts.actions)
        self.assertIn("computer_resource", facts.objects)

    def test_police_arrest_powers(self):
        q = "What are the powers of police to arrest without warrant under BNSS?"
        facts = self.extractor.extract(q)

        self.assertIn("police", facts.actors)
        self.assertIn("arrest", facts.actions)
        self.assertIn("BNSS", facts.statutory_references)
        self.assertIn("legal_document", facts.objects)


if __name__ == "__main__":
    unittest.main()
