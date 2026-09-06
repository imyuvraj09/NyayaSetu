"""Unit tests for FactNormalizer."""

import unittest
from research.fact_extraction import ConservativeFactExtractor
from research.fact_normalization import FactNormalizer


class TestFactNormalization(unittest.TestCase):
    def setUp(self):
        self.extractor = ConservativeFactExtractor()
        self.normalizer = FactNormalizer()

    def test_canonical_action_mapping(self):
        q = "Someone stole my mobile phone."
        facts = self.extractor.extract(q)
        normalized = self.normalizer.normalize(facts, q)

        self.assertIn("action:theft", normalized.canonical_actions)
        self.assertIn("object:movable_electronic_device", normalized.canonical_objects)

        # Check provenance
        action_item = next(i for i in normalized.items if i.category == "action")
        self.assertEqual(action_item.original_value, "theft")
        self.assertEqual(action_item.canonical_value, "action:theft")
        self.assertEqual(action_item.normalization_source, "action_canonical_map")

    def test_canonical_statute_mapping(self):
        q = "Punishment under BNS and procedure under BNSS."
        facts = self.extractor.extract(q)
        normalized = self.normalizer.normalize(facts, q)

        self.assertIn("statute:bharatiya_nyaya_sanhita_2023", normalized.canonical_statutes)
        self.assertIn("statute:bharatiya_nagarik_suraksha_sanhita_2023", normalized.canonical_statutes)


if __name__ == "__main__":
    unittest.main()
