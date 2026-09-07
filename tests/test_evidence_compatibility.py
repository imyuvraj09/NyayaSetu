"""Unit Tests for Phase 4 Evidence Compatibility Filtering in NyayaSetu.

Covers all 14 test requirements:
1. Compatible evidence
2. Incompatible regime
3. Substantive vs procedural mismatch
4. IT Act vs generic criminal law
5. Multi-statute compatibility
6. Temporal compatibility
7. Unknown temporal information
8. Special law vs general law
9. Soft penalties
10. No catastrophic document removal
11. Hard exclusion configuration
12. Backward compatibility
13. Configuration validation
14. Evidence relationship analysis
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = REPO_ROOT / "rag-service"
for p in [REPO_ROOT, RAG_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from research.evidence_compatibility.engine import EvidenceCompatibilityEngine, get_evidence_compatibility_engine
from research.evidence_compatibility.models import (
    CompatibilityScore,
    CompatibilityStatus,
    EvidenceRelationshipType,
    LegalRole,
    TemporalStatus,
)
from research.evidence_compatibility.regime_checker import RegimeCompatibilityChecker
from research.evidence_compatibility.issue_checker import IssueCompatibilityChecker
from research.evidence_compatibility.legal_role_checker import LegalRoleCompatibilityChecker
from research.evidence_compatibility.temporal_checker import TemporalCompatibilityChecker
from research.evidence_compatibility.special_general_checker import SpecialGeneralCompatibilityChecker
from research.evidence_compatibility.relationship_analyzer import EvidenceRelationshipAnalyzer
from research.evidence_compatibility.scoring import CompatibilityScorer
from research.evidence_compatibility.rules import STATUTE_REGISTRY, validate_configuration
from research.schemas import ExtractedFacts, NormalizedFacts, RoutingDecision, RoutingMode
from schemas.retrieval import RetrievedChunk


class TestEvidenceCompatibility(unittest.TestCase):
    """Test suite for Phase 4 Evidence Compatibility components and end-to-end engine."""

    def setUp(self):
        self.engine = get_evidence_compatibility_engine()

    def test_01_compatible_evidence(self):
        """1. Compatible evidence: Valid BNS theft chunk matched to BNS theft query."""
        chunk = RetrievedChunk(
            chunk_id="chunk_bns_303",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            document_type="statute",
            source_filename="bns.pdf",
            page_numbers=[100],
            text="Section 303. Whoever commits theft shall be punished with imprisonment up to three years or fine.",
            relevance_score=0.90,
        )
        routing = RoutingDecision(
            selected_regimes=["BNS_SUBSTANTIVE"],
            routing_mode=RoutingMode.HIGH_CONFIDENCE,
            confidence=0.95,
            fallback_used=False,
        )
        ranked, result = self.engine.filter_and_rank_candidates(
            query="What is the punishment for theft under BNS?",
            candidates=[chunk],
            routing_decision=routing,
        )
        self.assertEqual(len(ranked), 1)
        dec = result.decisions[0]
        self.assertIn(dec.compatibility_status, [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.PARTIALLY_COMPATIBLE])
        self.assertGreaterEqual(dec.compatibility_score, 0.75)
        self.assertFalse(dec.hard_excluded)

    def test_02_incompatible_regime(self):
        """2. Incompatible regime: Unrelated CPA evidence chunk retrieved for substantive BNS theft."""
        chunk = RetrievedChunk(
            chunk_id="chunk_cpa_2",
            document_name="Consumer Protection Act, 2019",
            document_type="statute",
            source_filename="cpa.pdf",
            page_numbers=[5],
            text="Section 2. Definition of consumer, defect, and unfair trade practice.",
            relevance_score=0.85,
        )
        routing = RoutingDecision(
            selected_regimes=["BNS_SUBSTANTIVE"],
            routing_mode=RoutingMode.HIGH_CONFIDENCE,
            confidence=0.90,
            fallback_used=False,
        )
        checker = RegimeCompatibilityChecker()
        score, status, violations, sup, rej = checker.check_regime_compatibility(
            document_name=chunk.document_name,
            source_filename=chunk.source_filename,
            routing_decision=routing,
        )
        self.assertLess(score, 0.80)
        self.assertTrue(any(v.dimension == "regime" for v in violations))

    def test_03_substantive_vs_procedural_mismatch(self):
        """3. Substantive vs procedural mismatch: substantive inquiry matched with BNSS procedural chunk."""
        checker = LegalRoleCompatibilityChecker()
        role = checker.determine_evidence_role(
            document_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            source_filename="bnss.pdf",
            section="35",
            chunk_text="Section 35. When police may arrest without warrant any person concerned in cognizable offence.",
        )
        score, status, violations, sup, rej = checker.check_role_compatibility(
            query="What is the definition and punishment of theft?",
            evidence_role=role,
            document_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            section="35",
        )
        self.assertEqual(role, LegalRole.PROCEDURAL)
        self.assertTrue(any("PROCEDURAL_PROVISION_FOR_SUBSTANTIVE_PUNISHMENT_QUERY" in v.rule_name for v in violations))
        self.assertLess(score, 1.0)

    def test_04_it_act_vs_generic_criminal_law(self):
        """4. IT Act vs generic criminal law: Cyber hacking query prioritizes IT Act over generic trespass."""
        checker = SpecialGeneralCompatibilityChecker()
        routing = RoutingDecision(
            selected_regimes=["IT_ACT"],
            routing_mode=RoutingMode.HIGH_CONFIDENCE,
            confidence=0.95,
            fallback_used=False,
        )
        # Check general statute penalty when special applies
        score_bns, status_bns, viols, _, _ = checker.check_special_general_compatibility(
            document_name="Bharatiya Nyaya Sanhita, 2023",
            source_filename="bns.pdf",
            routing_decision=routing,
        )
        self.assertLess(score_bns, 1.0)
        self.assertTrue(any("SPECIAL_LAW_PRECEDENCE" in v.rule_name for v in viols))

        # Check special statute compatibility
        score_it, status_it, viols_it, _, _ = checker.check_special_general_compatibility(
            document_name="Information Technology Act, 2000",
            source_filename="it_act.pdf",
            routing_decision=routing,
        )
        self.assertEqual(score_it, 1.0)
        self.assertEqual(len(viols_it), 0)

    def test_05_multi_statute_compatibility(self):
        """5. Multi-statute compatibility: Retaining both substantive and procedural evidence."""
        chunk_bns = RetrievedChunk(
            chunk_id="c_bns",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            document_type="statute",
            source_filename="bns.pdf",
            page_numbers=[1],
            text="Section 303. Theft definition and punishment.",
            relevance_score=0.88,
        )
        chunk_bnss = RetrievedChunk(
            chunk_id="c_bnss",
            document_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            document_type="statute",
            source_filename="bnss.pdf",
            page_numbers=[2],
            text="Section 35. When police may arrest without warrant.",
            relevance_score=0.86,
        )
        routing = RoutingDecision(
            selected_regimes=["BNS_SUBSTANTIVE", "BNSS_PROCEDURAL"],
            routing_mode=RoutingMode.MEDIUM_CONFIDENCE_SOFT_BOOST,
            confidence=0.92,
            fallback_used=False,
        )
        ranked, result = self.engine.filter_and_rank_candidates(
            query="Can police arrest someone for theft without warrant and what is the punishment?",
            candidates=[chunk_bns, chunk_bnss],
            routing_decision=routing,
            top_k=2,
        )
        # Both retained in top-2
        retained_ids = [c.chunk_id for c in ranked]
        self.assertIn("c_bns", retained_ids)
        self.assertIn("c_bnss", retained_ids)
        self.assertGreaterEqual(result.regime_coherence_score, 0.5)

    def test_06_temporal_compatibility(self):
        """6. Temporal compatibility: Post-2024 query penalizes repealed IPC enactment."""
        checker = TemporalCompatibilityChecker()
        score, status, violations, sup, rej = checker.check_temporal_compatibility(
            query="An incident of theft took place in 2025 post-2024. What law applies?",
            document_name="Indian Penal Code, 1860",
            source_filename="ipc.pdf",
        )
        self.assertEqual(status, TemporalStatus.REPEALED)
        self.assertTrue(any(v.rule_name == "SUPERSEDED_STATUTE_POST_2024" for v in violations))
        self.assertLess(score, 0.60)

    def test_07_unknown_temporal_information(self):
        """7. Unknown temporal information: Zero hallucination, evaluated neutrally."""
        checker = TemporalCompatibilityChecker()
        score, status, violations, sup, rej = checker.check_temporal_compatibility(
            query="What is the punishment for theft under section 303?",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            source_filename="bns.pdf",
        )
        self.assertEqual(status, TemporalStatus.UNKNOWN)
        self.assertEqual(score, 1.0)
        self.assertEqual(len(violations), 0)

    def test_08_special_law_vs_general_law(self):
        """8. Special law vs general law: POSH workplace sexual harassment inquiry."""
        checker = SpecialGeneralCompatibilityChecker()
        routing = RoutingDecision(
            selected_regimes=["POSH_LABOUR"],
            routing_mode=RoutingMode.HIGH_CONFIDENCE,
            confidence=0.90,
            fallback_used=False,
        )
        score_gen, status, viols, _, _ = checker.check_special_general_compatibility(
            document_name="Bharatiya Nyaya Sanhita, 2023",
            source_filename="bns.pdf",
            routing_decision=routing,
        )
        self.assertLess(score_gen, 1.0)
        self.assertTrue(any(v.dimension == "special_general" for v in viols))

    def test_09_soft_penalties(self):
        """9. Soft penalties: Incompatible evidence receives a positive non-zero multiplier."""
        scorer = CompatibilityScorer()
        score_obj, status = scorer.calculate_score(
            regime_score=0.20,
            issue_score=0.30,
            legal_role_score=0.30,
            temporal_score=0.40,
            special_general_score=0.50,
            relationship_score=0.50,
            violations=[],
        )
        self.assertGreater(score_obj.soft_multiplier, 0.0)
        self.assertGreaterEqual(score_obj.soft_multiplier, 0.35)

    def test_10_no_catastrophic_document_removal(self):
        """10. No catastrophic document removal: Under default allow_hard_exclusion=False, candidates are kept."""
        chunk = RetrievedChunk(
            chunk_id="chunk_weak",
            document_name="Indian Evidence Act, 1872",
            document_type="statute",
            source_filename="iea.pdf",
            page_numbers=[10],
            text="Definitions of document and proof.",
            relevance_score=0.40,
        )
        routing = RoutingDecision(
            selected_regimes=["BNS_SUBSTANTIVE"],
            routing_mode=RoutingMode.HIGH_CONFIDENCE,
            confidence=0.90,
            fallback_used=False,
        )
        ranked, result = self.engine.filter_and_rank_candidates(
            query="What is theft under BNS?",
            candidates=[chunk],
            routing_decision=routing,
        )
        self.assertEqual(len(ranked), 1)
        self.assertFalse(result.decisions[0].hard_excluded)

    def test_11_hard_exclusion_configuration(self):
        """11. Hard exclusion configuration: Only excludes when explicitly configured."""
        strict_engine = EvidenceCompatibilityEngine(
            config={
                "allow_hard_exclusion": True,
                "scoring": {
                    "thresholds": {"hard_exclusion": 0.85},
                },
            }
        )
        chunk = RetrievedChunk(
            chunk_id="chunk_unrelated",
            document_name="Indian Penal Code, 1860",
            document_type="statute",
            source_filename="ipc.pdf",
            page_numbers=[1],
            text="Unrelated archaic section.",
            relevance_score=0.10,
        )
        routing = RoutingDecision(
            selected_regimes=["IT_ACT"],
            routing_mode=RoutingMode.HIGH_CONFIDENCE,
            confidence=0.95,
            fallback_used=False,
        )
        facts = ExtractedFacts(temporal_context="post-2024")
        ranked, result = strict_engine.filter_and_rank_candidates(
            query="Cyber hacking offense in 2025 post-2024",
            candidates=[chunk],
            routing_decision=routing,
            facts=facts,
        )
        # Should be excluded due to allow_hard_exclusion=True and low score
        self.assertTrue(result.decisions[0].hard_excluded)
        self.assertEqual(len(ranked), 0)

    def test_12_backward_compatibility(self):
        """12. Backward compatibility: Works smoothly without routing_decision or facts."""
        chunk = RetrievedChunk(
            chunk_id="chunk_bns",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            document_type="statute",
            source_filename="bns.pdf",
            page_numbers=[1],
            text="Section 303. Theft definition.",
            relevance_score=0.85,
        )
        ranked, result = self.engine.filter_and_rank_candidates(
            query="What is theft?",
            candidates=[chunk],
            routing_decision=None,
            facts=None,
        )
        self.assertEqual(len(ranked), 1)
        self.assertEqual(result.total_candidates, 1)

    def test_13_configuration_validation(self):
        """13. Configuration validation: Validate weights and threshold integrity."""
        valid_cfg = {
            "scoring": {
                "weights": {
                    "regime": 0.25,
                    "issue": 0.25,
                    "legal_role": 0.20,
                    "temporal": 0.15,
                    "special_general": 0.10,
                    "relationship": 0.05,
                }
            }
        }
        self.assertTrue(validate_configuration(valid_cfg))

    def test_14_evidence_relationship_analysis(self):
        """14. Evidence relationship analysis: Bridge and temporal conflict detection."""
        analyzer = EvidenceRelationshipAnalyzer()
        c_bns = {
            "chunk_id": "c1",
            "document_name": "Bharatiya Nyaya Sanhita, 2023",
            "section": "303",
            "text": "Theft",
            "legal_role": LegalRole.SUBSTANTIVE,
            "temporal_status": TemporalStatus.APPLICABLE,
        }
        c_bnss = {
            "chunk_id": "c2",
            "document_name": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "section": "35",
            "text": "Arrest",
            "legal_role": LegalRole.PROCEDURAL,
            "temporal_status": TemporalStatus.APPLICABLE,
        }
        c_ipc = {
            "chunk_id": "c3",
            "document_name": "Indian Penal Code, 1860",
            "section": "378",
            "text": "Repealed theft",
            "legal_role": LegalRole.SUBSTANTIVE,
            "temporal_status": TemporalStatus.REPEALED,
        }

        # Substantive + Procedural -> PROCEDURALLY_SUPPORTS bridge
        rels, scores, coherence = analyzer.analyze_relationships([c_bns, c_bnss])
        self.assertTrue(any(r.relationship_type == EvidenceRelationshipType.PROCEDURALLY_SUPPORTS for r in rels))
        self.assertGreater(coherence, 0.0)

        # BNS + IPC -> TEMPORALLY_CONFLICTS
        rels_conflict, scores_c, _ = analyzer.analyze_relationships([c_bns, c_ipc])
        self.assertTrue(any(r.relationship_type == EvidenceRelationshipType.TEMPORALLY_CONFLICTS for r in rels_conflict))


if __name__ == "__main__":
    unittest.main()
