"""
Regression tests for Issue 12:
Prevent Query-Answer Mismatch, Stale Context Leakage, and Enforce Workplace Sexual Harassment Handling.

Covers:
1. LegalQuestionAnalyzer: Domain, primary task, and issue resolution for workplace sexual harassment.
2. QueryAnalyzer: Act detection, domain routing to POSH Act, and sub-query generation.
3. UniversalEvidenceFilter: POSH chunk elevation (DIRECT) and BSA electronic chunk rejection (IRRELEVANT).
4. DeterministicAnswerBuilder: Dedicated POSH response generation with protections, complaint mechanisms, and evidence.
5. Sequential Query Execution: Query 1 (BSA Electronic Evidence) followed by Query 2 (Sexual Harassment)
   confirming ZERO stale context leakage or cross-query contamination.
6. QueryAnswerRelevanceValidator: Detecting topic mismatch and validating multi-intent coverage.
7. Request ID Propagation: Request ID correctly preserved throughout pipeline execution.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.legal_question import LegalQuestionAnalyzer, QuestionType, PrimaryTask
from retrieval.query_analyzer import LegalQueryAnalyzer, KNOWN_ACT_REGISTRY
from retrieval.evidence_relevance_filter import UniversalEvidenceFilter, EvidenceCompatibility
from rag.deterministic_answer_builder import DeterministicAnswerBuilder
from rag.query_answer_validator import QueryAnswerRelevanceValidator
from schemas.generation import SourceReference


SEXUAL_HARASSMENT_QUERY = (
    "A woman alleges sexual harassment at her workplace by a senior employee whose name is RAJU. "
    "What legal protections, complaint mechanisms, and evidence are relevant?"
)

BSA_ELECTRONIC_QUERY = (
    "How are electronic records admitted as evidence under the Bharatiya Sakshya Adhiniyam, 2023?"
)


class TestIssue12Regression(unittest.TestCase):
    """Comprehensive test suite for Issue 12 fixes."""

    def test_01_legal_question_analyzer_workplace_harassment(self):
        """Verify that LegalQuestionAnalyzer correctly models workplace sexual harassment."""
        analyzer = LegalQuestionAnalyzer()
        lq = analyzer.analyze(SEXUAL_HARASSMENT_QUERY)

        # Domain must be Labour Law / Workplace Sexual Harassment (POSH)
        assert "posh" in lq.primary_domain.lower() or "sexual harassment" in lq.primary_domain.lower()
        assert "Employment and Workplace Law" in lq.secondary_domains

        # Primary issue must not be substantive_law_governing_woman or substantive_law_governing_raju
        assert "substantive_law_governing_woman" not in lq.primary_issue
        assert "raju" not in lq.primary_issue.lower()
        assert "workplace_sexual_harassment" in lq.primary_issue

        # Candidate acts must contain the POSH Act
        act_names = [a.lower() for a in lq.acts]
        assert any("sexual harassment" in a or "posh" in a for a in act_names)

        # Operative legal concepts must focus on sexual harassment, not person names
        concepts = [c.lower() for c in lq.operative_legal_concepts]
        assert "raju" not in concepts
        assert any("sexual harassment" in c or "harassment" in c for c in concepts)

    def test_02_query_analyzer_routing_to_posh_act(self):
        """Verify that LegalQueryAnalyzer routes the sexual harassment query to the POSH Act."""
        analyzer = LegalQueryAnalyzer()
        analysis = analyzer.analyze(SEXUAL_HARASSMENT_QUERY)

        # Document ID must be sexual_harassment_workplace_act_2013
        assert analysis.document_id == "sexual_harassment_workplace_act_2013"
        assert analysis.act_short_name == "POSH"

        # Excluded topics must include BSA electronic records
        assert any("bsa" in t.lower() or "electronic" in t.lower() for t in analysis.excluded_topics)

        # Sub-queries must target POSH Act facets
        assert len(analysis.sub_queries) >= 2
        for sq in analysis.sub_queries:
            assert "sexual harassment" in (sq.target_act or "").lower() or "posh" in (sq.target_act or "").lower()

    def test_03_universal_evidence_filter_posh_vs_bsa(self):
        """Verify UniversalEvidenceFilter marks POSH chunks DIRECT and BSA chunks IRRELEVANT."""
        lq = LegalQuestionAnalyzer().analyze(SEXUAL_HARASSMENT_QUERY)

        # 1. POSH Section 9 (Complaint) chunk
        posh_chunk = {
            "text": "Any aggrieved woman may make, in writing, a complaint of sexual harassment at workplace to the Internal Committee within three months.",
            "metadata": {
                "document_id": "sexual_harassment_workplace_act_2013",
                "act": "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
                "section_number": "9",
                "section_title": "Complaint of sexual harassment",
            },
        }
        res_posh = UniversalEvidenceFilter.evaluate_chunk(posh_chunk, legal_question=lq)
        assert res_posh.compatibility == EvidenceCompatibility.DIRECT
        assert res_posh.affinity_score >= 0.9

        # 2. BSA Section 63 (Electronic Records) chunk
        bsa_chunk = {
            "text": "Admissibility of electronic records. Any information contained in an electronic record produced by a computer shall be deemed to be a document.",
            "metadata": {
                "document_id": "bsa_2023",
                "act": "Bharatiya Sakshya Adhiniyam, 2023",
                "section_number": "63",
                "section_title": "Admissibility of electronic records",
            },
        }
        res_bsa = UniversalEvidenceFilter.evaluate_chunk(bsa_chunk, legal_question=lq)
        assert res_bsa.compatibility == EvidenceCompatibility.IRRELEVANT
        assert res_bsa.affinity_score == 0.0

    def test_04_deterministic_answer_builder_posh_response(self):
        """Verify DeterministicAnswerBuilder generates comprehensive POSH answer covering all required intents."""
        posh_sources = [
            SourceReference(
                source_label="[SOURCE 1]",
                chunk_id="sexual_harassment_workplace_act_2013_c0011",
                document_name="The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
                act_short_name="POSH",
                section_number="3",
                section_title="Prevention of sexual harassment",
                text_snippet="No woman shall be subjected to sexual harassment at any workplace. The following circumstances may amount to sexual harassment...",
                similarity_score=0.92,
                reranker_score=0.95,
            ),
            SourceReference(
                source_label="[SOURCE 2]",
                chunk_id="sexual_harassment_workplace_act_2013_c0021",
                document_name="The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
                act_short_name="POSH",
                section_number="9",
                section_title="Complaint of sexual harassment",
                text_snippet="Any aggrieved woman may make, in writing, a complaint of sexual harassment at workplace to the Internal Committee within three months...",
                similarity_score=0.90,
                reranker_score=0.94,
            ),
            SourceReference(
                source_label="[SOURCE 3]",
                chunk_id="sexual_harassment_workplace_act_2013_c0023",
                document_name="The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013",
                act_short_name="POSH",
                section_number="11",
                section_title="Inquiry into complaint",
                text_snippet="The Internal Committee shall proceed to make inquiry into the complaint in accordance with service rules...",
                similarity_score=0.88,
                reranker_score=0.91,
            ),
        ]

        raw_answer = DeterministicAnswerBuilder.build_answer(
            query=SEXUAL_HARASSMENT_QUERY,
            sources=posh_sources,
        )

        import json
        parsed = json.loads(raw_answer)
        main_answer = parsed["mainAnswer"]

        # 1. Must NOT discuss BSA electronic records admissibility as the answer
        assert "Admissibility of electronic records under the Bharatiya Sakshya Adhiniyam, 2023" not in main_answer
        assert "Section 63 deeming computer output" not in main_answer

        # 2. Must cover all 3 intents
        # Intent 1: Legal protections
        assert "Legal Protections" in main_answer
        assert "Section 3" in main_answer or "Section 12" in main_answer or "protections" in main_answer.lower()

        # Intent 2: Complaint mechanisms
        assert "Complaint Mechanisms" in main_answer
        assert "Internal Complaints Committee" in main_answer or "ICC" in main_answer
        assert "Section 9" in main_answer or "three months" in main_answer

        # Intent 3: Relevant evidence
        assert "Relevant Evidence" in main_answer
        assert any(w in main_answer.lower() for w in ["communications", "messages", "records", "witness", "chats"])

        # 3. Must address respondent named RAJU
        assert "RAJU" in main_answer

    def test_05_sequential_query_isolation_no_stale_leakage(self):
        """Verify sequential execution of BSA Query followed by Sexual Harassment Query has zero stale leakage."""
        from rag.rag_pipeline import LegalRAGPipeline

        pipeline = LegalRAGPipeline()

        # Query 1: BSA Electronic Evidence inquiry
        resp1 = pipeline.query(BSA_ELECTRONIC_QUERY, request_id="req-test-bsa-001")
        assert resp1.request_id == "req-test-bsa-001"
        assert any("sakshya" in s.document_name.lower() or "bsa" in s.document_name.lower() for s in resp1.sources)

        # Query 2: Workplace Sexual Harassment inquiry (Executed immediately on same pipeline instance)
        resp2 = pipeline.query(SEXUAL_HARASSMENT_QUERY, request_id="req-test-posh-002")
        assert resp2.request_id == "req-test-posh-002"

        # Assert zero leakage: resp2 must not be about BSA electronic records
        resp2_answer = resp2.answer
        assert "Admissibility of electronic records" not in resp2_answer
        assert "Section 63 deeming computer output" not in resp2_answer

        # Assert resp2 addresses workplace sexual harassment
        assert "sexual harassment" in resp2_answer.lower()
        assert any("posh" in s.document_name.lower() or "sexual harassment" in s.document_name.lower() for s in resp2.sources)

        # Assert intent coverage report is present and complete
        assert resp2.intent_coverage is not None
        assert resp2.intent_coverage.get("legal_protections") is True
        assert resp2.intent_coverage.get("complaint_mechanisms") is True
        assert resp2.intent_coverage.get("relevant_evidence") is True

    def test_06_query_answer_relevance_validator_detects_mismatch(self):
        """Verify QueryAnswerRelevanceValidator catches topic mismatches and passes aligned answers."""
        # 1. Invalid case: Sexual harassment query answered with BSA Section 63
        mismatched_answer = (
            "Under the Bharatiya Sakshya Adhiniyam, 2023 (BSA), electronic records are admitted through a distinct "
            "statutory mechanism established under Sections 62 and 63. Section 63 deeming computer output to be a document."
        )
        res_bad = QueryAnswerRelevanceValidator.validate(
            query=SEXUAL_HARASSMENT_QUERY,
            answer=mismatched_answer,
        )
        assert res_bad.is_valid is False
        assert res_bad.contamination_detected is True
        assert res_bad.relevance_score == 0.0

        # 2. Valid case: Sexual harassment query answered with POSH Act provisions
        aligned_answer = (
            "Under the POSH Act, 2013, legal protections against workplace sexual harassment are established under Section 3. "
            "Complaint mechanisms include the Internal Complaints Committee (ICC) under Section 4 and Section 9. "
            "Relevant evidence includes contemporaneous messages, emails, witness statements, and workplace records."
        )
        res_good = QueryAnswerRelevanceValidator.validate(
            query=SEXUAL_HARASSMENT_QUERY,
            answer=aligned_answer,
        )
        assert res_good.is_valid is True
        assert res_good.contamination_detected is False
        assert res_good.intent_coverage.get("legal_protections") is True
        assert res_good.intent_coverage.get("complaint_mechanisms") is True
        assert res_good.intent_coverage.get("relevant_evidence") is True


if __name__ == "__main__":
    unittest.main()
