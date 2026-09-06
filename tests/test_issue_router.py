"""Unit tests for FactFirstRouter and confidence-aware routing modes."""

import unittest
from research.issue_router import FactFirstRouter
from research.schemas import RoutingMode


class TestIssueRouter(unittest.TestCase):
    def setUp(self):
        self.router = FactFirstRouter()

    def test_empty_query_fallback(self):
        decision = self.router.route_query("")
        self.assertEqual(decision.routing_mode, RoutingMode.AMBIGUOUS_FALLBACK)
        self.assertTrue(decision.fallback_used)
        self.assertIn("GENERAL", decision.selected_regimes)

    def test_cyber_identity_theft_high_confidence(self):
        q = "What is the punishment for identity theft and cheating by personation using computer resource under the IT Act?"
        decision = self.router.route_query(q)

        self.assertIn(decision.routing_mode, [RoutingMode.HIGH_CONFIDENCE, RoutingMode.MEDIUM_CONFIDENCE_SOFT_BOOST])
        self.assertFalse(decision.fallback_used)
        self.assertIn("IT_ACT", decision.selected_regimes)
        self.assertGreaterEqual(decision.confidence, 0.70)

    def test_bns_substantive_theft_routing(self):
        q = "What is the punishment for committing theft under Section 303 of the Bharatiya Nyaya Sanhita?"
        decision = self.router.route_query(q)

        self.assertEqual(decision.routing_mode, RoutingMode.HIGH_CONFIDENCE)
        self.assertIn("BNS_SUBSTANTIVE", decision.selected_regimes)
        self.assertFalse(decision.fallback_used)

    def test_bnss_procedural_arrest_routing(self):
        q = "When can police arrest an accused without warrant under Bharatiya Nagarik Suraksha Sanhita?"
        decision = self.router.route_query(q)

        self.assertEqual(decision.routing_mode, RoutingMode.HIGH_CONFIDENCE)
        self.assertIn("BNSS_PROCEDURAL", decision.selected_regimes)

    def test_bsa_evidence_admissibility_routing(self):
        q = "How are electronic records certified for admissibility under Bharatiya Sakshya Adhiniyam?"
        decision = self.router.route_query(q)

        self.assertIn("BSA_EVIDENCE", decision.selected_regimes)
        self.assertFalse(decision.fallback_used)

    def test_low_confidence_fallback(self):
        q = "Tell me about rights and laws in some context."
        decision = self.router.route_query(q)

        self.assertIn(decision.routing_mode, [RoutingMode.LOW_CONFIDENCE_FALLBACK, RoutingMode.MEDIUM_CONFIDENCE_SOFT_BOOST])
        if decision.routing_mode == RoutingMode.LOW_CONFIDENCE_FALLBACK:
            self.assertTrue(decision.fallback_used)


if __name__ == "__main__":
    unittest.main()
