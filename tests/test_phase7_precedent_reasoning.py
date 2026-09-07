"""Unit and Regression Test Suite for Phase 7 — Judicial Precedent Retrieval & Authority-Aware Reasoning.

Covers all 10 Phase 7 components:
1. Data models & schemas (JudicialPrecedent, assessments, relationships, conflicts)
2. CourtHierarchyEngine (Constitutional tier, bench weighting, court classification)
3. PrecedentAuthorityClassifier (Article 141 binding, territorial limits, passage type)
4. JurisdictionChecker (Territorial scope, interstate persuasiveness)
5. PrecedentTemporalValidator (Overruling detection, age decay)
6. PrecedentRelationshipAnalyzer (Overruled, Distinguished, Followed, Cited)
7. PrecedentCitationGraph (Topological authority propagation, citation network)
8. PrecedentConflictDetector (Conflict detection, hierarchical resolution, harmonization)
9. StatutePrecedentChecker (IPC-BNS transition compatibility, statutory concordance)
10. AuthorityAwareRanker & PrecedentSynthesizer (Multi-factor ranking and synthesis)
11. PrecedentReasoningEngine (End-to-end integration and execution)
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAG_SERVICE_DIR = os.path.join(REPO_ROOT, "rag-service")
for p in [REPO_ROOT, RAG_SERVICE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from research.precedent_reasoning.models import (
    CourtLevel,
    AuthorityStatus,
    JurisdictionRelevance,
    PrecedentRelationshipType,
    PrecedentTemporalStatus,
    ConflictStatus,
    BenchStrength,
    JudicialPrecedent,
    PrecedentMetadata,
    AuthorityAssessment,
    JurisdictionAssessment,
    PrecedentRelationship,
    PrecedentConflict,
    PrecedentReasoningResult,
)
from research.precedent_reasoning.court_hierarchy import CourtHierarchyEngine
from research.precedent_reasoning.authority_classifier import PrecedentAuthorityClassifier
from research.precedent_reasoning.jurisdiction_checker import JurisdictionChecker
from research.precedent_reasoning.temporal_validator import PrecedentTemporalValidator
from research.precedent_reasoning.precedent_relationship_analyzer import PrecedentRelationshipAnalyzer
from research.precedent_reasoning.citation_graph import PrecedentCitationGraph
from research.precedent_reasoning.conflict_detector import PrecedentConflictDetector
from research.precedent_reasoning.statute_precedent_checker import StatutePrecedentChecker
from research.precedent_reasoning.authority_ranker import AuthorityAwareRanker
from research.precedent_reasoning.precedent_synthesizer import PrecedentSynthesizer
from research.precedent_reasoning.engine import PrecedentReasoningEngine


class TestPrecedentModels(unittest.TestCase):
    """Test Phase 7 data models, enums, and serialization."""

    def test_judicial_precedent_instantiation(self):
        meta = PrecedentMetadata(
            case_name="Kesavananda Bharati v. State of Kerala",
            court="Supreme Court of India",
            court_level=CourtLevel.SUPREME_COURT,
            citation="(1973) 4 SCC 225",
            judgment_date="1973-04-24",
            jurisdiction="India",
            bench=["Sikri C.J.", "Shelat J.", "Hegde J."],
            bench_strength="13",
            statutes_referred=["Constitution of India"],
            sections_referred=["Article 368"],
            topics=["basic structure", "constitutional amendment"],
        )
        jp = JudicialPrecedent(
            chunk_id="kb_1973_01",
            document_id="kb_1973",
            case_name=meta.case_name,
            citation=meta.citation,
            court=meta.court,
            court_level=meta.court_level,
            judgment_date=meta.judgment_date,
            passage_type="HOLDING",
            text="Parliament cannot alter the basic structure or essential framework of the Constitution.",
            is_holding_or_ratio=True,
            retrieval_score=0.92,
            metadata=meta,
            statutes_referred=meta.statutes_referred,
            sections_referred=meta.sections_referred,
            topics=meta.topics,
        )
        self.assertEqual(jp.case_name, "Kesavananda Bharati v. State of Kerala")
        self.assertEqual(jp.court_level, CourtLevel.SUPREME_COURT)
        self.assertTrue(jp.is_holding_or_ratio)
        d = jp.to_dict()
        self.assertIn("chunk_id", d)
        self.assertIn("case_name", d)
        self.assertIn("metadata", d)
        self.assertEqual(d["metadata"]["bench_strength"], "13")

    def test_relationship_and_conflict_serialization(self):
        rel = PrecedentRelationship(
            source_case="Navtej Singh Johar v. Union of India",
            target_case="Suresh Kumar Koushal v. Naz Foundation",
            relationship_type=PrecedentRelationshipType.OVERRULED,
            evidence_text="Suresh Koushal is hereby overruled.",
            confidence=0.95,
            is_explicit_in_corpus=True,
        )
        rel_dict = rel.to_dict()
        self.assertEqual(rel_dict["relationship_type"], "OVERRULED")
        self.assertEqual(rel_dict["target_case"], "Suresh Kumar Koushal v. Naz Foundation")

        conflict = PrecedentConflict(
            case_a="Navtej Singh Johar v. Union of India",
            case_b="Suresh Kumar Koushal v. Naz Foundation",
            legal_issue="Constitutionality of IPC Section 377",
            position_a="Unconstitutional between consenting adults",
            position_b="Constitutional and within legislative wisdom",
            conflict_status=ConflictStatus.RESOLVED_BY_AUTHORITY,
            controlling_case="Navtej Singh Johar v. Union of India",
            resolution_basis="Overruled by Constitution Bench of Supreme Court",
        )
        c_dict = conflict.to_dict()
        self.assertEqual(c_dict["conflict_status"], "RESOLVED_BY_AUTHORITY")
        self.assertEqual(c_dict["controlling_case"], "Navtej Singh Johar v. Union of India")


class TestCourtHierarchyEngine(unittest.TestCase):
    """Test Indian court hierarchy classification and bench weighting."""

    def test_classify_supreme_court(self):
        names = [
            "Supreme Court of India",
            "Supreme Court",
            "Hon'ble Supreme Court of India",
            "SC of India",
        ]
        for n in names:
            self.assertEqual(
                CourtHierarchyEngine.classify_court_level(n),
                CourtLevel.SUPREME_COURT,
                f"Failed for {n}",
            )

    def test_classify_high_courts(self):
        names = [
            "High Court of Judicature at Bombay",
            "Delhi High Court",
            "High Court of Karnataka",
            "Allahabad HC",
            "High Court of Madras",
        ]
        for n in names:
            self.assertEqual(
                CourtHierarchyEngine.classify_court_level(n),
                CourtLevel.HIGH_COURT,
                f"Failed for {n}",
            )

    def test_classify_subordinate_and_tribunal(self):
        self.assertEqual(
            CourtHierarchyEngine.classify_court_level("Sessions Court at Pune"),
            CourtLevel.DISTRICT_COURT,
        )
        self.assertEqual(
            CourtHierarchyEngine.classify_court_level("National Company Law Appellate Tribunal"),
            CourtLevel.TRIBUNAL,
        )

    def test_bench_weighting(self):
        # 5+ judges => 1.25 multiplier
        w_5 = CourtHierarchyEngine.compute_bench_weight("5")
        self.assertAlmostEqual(w_5, 1.25)

        # 3 judges => 1.15 multiplier
        w_3 = CourtHierarchyEngine.compute_bench_weight("3")
        self.assertAlmostEqual(w_3, 1.15)

        # 1 judge => 1.0 multiplier
        w_1 = CourtHierarchyEngine.compute_bench_weight("1")
        self.assertAlmostEqual(w_1, 1.0)


class TestPrecedentAuthorityClassifier(unittest.TestCase):
    """Test PrecedentAuthorityClassifier under Article 141 of Indian Constitution."""

    def test_supreme_court_is_article_141_binding(self):
        jp = JudicialPrecedent(
            chunk_id="sc_01",
            document_id="sc_doc",
            case_name="Navtej Singh Johar v. Union of India",
            citation="(2018) 10 SCC 1",
            court="Supreme Court of India",
            court_level=CourtLevel.SUPREME_COURT,
            judgment_date="2018-09-06",
            passage_type="HOLDING",
            text="Section 377 is unconstitutional in private consensual relations.",
            is_holding_or_ratio=True,
            retrieval_score=0.85,
        )
        assessment = PrecedentAuthorityClassifier.evaluate_authority(jp, target_jurisdiction="Maharashtra")
        self.assertEqual(assessment.authority_status, AuthorityStatus.BINDING)
        self.assertTrue(assessment.article_141_binding)
        self.assertGreater(assessment.authority_score, 1.0)
        self.assertIn("Article 141", assessment.reasoning)

    def test_high_court_intra_state_binding_vs_interstate_persuasive(self):
        jp = JudicialPrecedent(
            chunk_id="hc_bom_01",
            document_id="hc_bom",
            case_name="State of Maharashtra v. ABC",
            citation="2020 Bom CR 12",
            court="High Court of Judicature at Bombay",
            court_level=CourtLevel.HIGH_COURT,
            judgment_date="2020-05-10",
            passage_type="RATIO",
            text="Interpretation of Maharashtra Police Act.",
            is_holding_or_ratio=True,
            retrieval_score=0.80,
            metadata=PrecedentMetadata(
                case_name="State of Maharashtra v. ABC",
                court="High Court of Judicature at Bombay",
                court_level=CourtLevel.HIGH_COURT,
                citation="2020 Bom CR 12",
                judgment_date="2020-05-10",
                jurisdiction="Maharashtra",
            ),
        )
        # Inside Maharashtra => BINDING
        assess_intra = PrecedentAuthorityClassifier.evaluate_authority(jp, target_jurisdiction="Maharashtra")
        self.assertEqual(assess_intra.authority_status, AuthorityStatus.BINDING)
        self.assertFalse(assess_intra.article_141_binding)

        # In Delhi => PERSUASIVE
        assess_inter = PrecedentAuthorityClassifier.evaluate_authority(jp, target_jurisdiction="Delhi")
        self.assertEqual(assess_inter.authority_status, AuthorityStatus.PERSUASIVE)


class TestPrecedentRelationshipAndConflicts(unittest.TestCase):
    """Test relationship extraction, citation graph, and conflict detection."""

    def setUp(self):
        self.p_navtej = JudicialPrecedent(
            chunk_id="sc_navtej",
            document_id="sc_navtej",
            case_name="Navtej Singh Johar v. Union of India",
            citation="(2018) 10 SCC 1",
            court="Supreme Court of India",
            court_level=CourtLevel.SUPREME_COURT,
            judgment_date="2018-09-06",
            passage_type="HOLDING",
            text="The declaration of law in Suresh Kumar Koushal v. Naz Foundation is hereby overruled.",
            is_holding_or_ratio=True,
            retrieval_score=0.90,
            sections_referred=["377"],
            topics=["section 377", "constitutionality"],
        )
        self.p_koushal = JudicialPrecedent(
            chunk_id="sc_koushal",
            document_id="sc_koushal",
            case_name="Suresh Kumar Koushal v. Naz Foundation",
            citation="(2014) 1 SCC 1",
            court="Supreme Court of India",
            court_level=CourtLevel.SUPREME_COURT,
            judgment_date="2014-01-15",
            passage_type="HOLDING",
            text="Section 377 IPC is constitutionally valid.",
            is_holding_or_ratio=True,
            retrieval_score=0.75,
            sections_referred=["377"],
            topics=["section 377", "constitutionality"],
            metadata=PrecedentMetadata(
                case_name="Suresh Kumar Koushal v. Naz Foundation",
                court="Supreme Court of India",
                court_level=CourtLevel.SUPREME_COURT,
                citation="(2014) 1 SCC 1",
                judgment_date="2014-01-15",
                sections_referred=["377"],
                topics=["section 377", "constitutionality"],
                overruled_by="Navtej Singh Johar v. Union of India",
            ),
        )

    def test_relationship_analyzer_detects_overruling(self):
        rels = PrecedentRelationshipAnalyzer.analyze_all_relationships([self.p_navtej, self.p_koushal])
        self.assertTrue(len(rels) >= 1)
        overruled_rel = [r for r in rels if r.relationship_type == PrecedentRelationshipType.OVERRULED]
        self.assertTrue(len(overruled_rel) >= 1)
        self.assertEqual(overruled_rel[0].source_case, "Navtej Singh Johar v. Union of India")
        self.assertEqual(overruled_rel[0].target_case, "Suresh Kumar Koushal v. Naz Foundation")

    def test_citation_graph_propagation(self):
        graph = PrecedentCitationGraph()
        graph.add_precedent(self.p_navtej)
        graph.add_precedent(self.p_koushal)
        rel = PrecedentRelationship(
            source_case=self.p_navtej.case_name,
            target_case=self.p_koushal.case_name,
            relationship_type=PrecedentRelationshipType.OVERRULED,
            evidence_text="Overruled",
        )
        graph.add_relationship(rel)
        overrulers = graph.find_overruling_precedents("Suresh Kumar Koushal v. Naz Foundation")
        self.assertIn("Navtej Singh Johar v. Union of India", overrulers)

    def test_conflict_detector_resolves_overruled_precedent(self):
        rels = PrecedentRelationshipAnalyzer.analyze_all_relationships([self.p_navtej, self.p_koushal])
        conflicts = PrecedentConflictDetector.detect_conflicts([self.p_navtej, self.p_koushal], rels)
        self.assertTrue(len(conflicts) >= 1)
        res_conflict = conflicts[0]
        self.assertEqual(res_conflict.conflict_status, ConflictStatus.RESOLVED_BY_AUTHORITY)
        self.assertEqual(res_conflict.controlling_case, "Navtej Singh Johar v. Union of India")


class TestStatutePrecedentChecker(unittest.TestCase):
    """Test IPC to BNS statutory transition concordance."""

    def test_statute_compatibility_direct_and_transition(self):
        jp = JudicialPrecedent(
            chunk_id="chhotey_lal",
            document_id="doc_chhotey",
            case_name="State of UP v. Chhotey Lal",
            citation="(2011) 2 SCC 550",
            court="Supreme Court of India",
            court_level=CourtLevel.SUPREME_COURT,
            judgment_date="2011-01-05",
            passage_type="HOLDING",
            text="Consent under Section 375 IPC.",
            is_holding_or_ratio=True,
            retrieval_score=0.88,
            statutes_referred=["Indian Penal Code, 1860"],
            sections_referred=["375"],
        )
        # Querying BNS Section 63 (equivalent to IPC 375)
        mult, reason = StatutePrecedentChecker.evaluate_compatibility(
            jp,
            target_statutes=["Bharatiya Nyaya Sanhita, 2023"],
            target_sections=["63"],
            routed_regime="BNS",
        )
        self.assertGreaterEqual(mult, 1.0)
        self.assertIn("375", reason)
        self.assertIn("63", reason)


class TestAuthorityAwareRankerAndEngine(unittest.TestCase):
    """Test end-to-end PrecedentReasoningEngine and AuthorityAwareRanker."""

    def setUp(self):
        self.engine = PrecedentReasoningEngine()

    def test_reason_over_precedents_privacy_query(self):
        res: PrecedentReasoningResult = self.engine.reason_over_precedents(
            query="Is right to privacy a fundamental right in India under Article 21?",
            target_sections=["Article 21"],
            top_k=5,
        )
        self.assertIsInstance(res, PrecedentReasoningResult)
        self.assertGreaterEqual(len(res.ranked_precedents), 1)
        self.assertGreaterEqual(len(res.controlling_precedents), 1)
        self.assertIn("execution_time_ms", res.to_dict())
        self.assertIn("audit_log", res.to_dict())

        # Check ranking decisions exist and contain proper adjustments
        self.assertGreaterEqual(len(res.ranking_decisions), 1)
        d0 = res.ranking_decisions[0]
        self.assertIn("final_score", d0.to_dict())
        self.assertIn("authority_multiplier", d0.to_dict())

    def test_reason_over_precedents_consent_query(self):
        res: PrecedentReasoningResult = self.engine.reason_over_precedents(
            query="What constitutes consent in sexual offences under Section 375 IPC and Pramod Suryabhan Pawar?",
            target_sections=["375", "63"],
            top_k=5,
        )
        self.assertIsInstance(res, PrecedentReasoningResult)
        # Check top case is Pramod Suryabhan Pawar
        top_case = res.ranked_precedents[0]
        self.assertEqual(top_case.case_name, "Pramod Suryabhan Pawar v. State of Maharashtra")
        self.assertEqual(top_case.court_level, CourtLevel.SUPREME_COURT)


if __name__ == "__main__":
    unittest.main()
