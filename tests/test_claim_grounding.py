"""Comprehensive unit test suite for Phase 5 Answer Claim Grounding & Citation Verification.

Tests all 17 required aspects:
1. Atomic claim extraction
2. Source span preservation
3. Claim classification
4. Claim weighting
5. Evidence matching
6. Supported claims
7. Partially supported claims
8. Unsupported claims
9. Contradicted claims
10. Missing citations
11. Invalid citations
12. Misaligned citations
13. Temporal claims
14. Multi-statute evidence
15. High-risk unsupported claims
16. Answer qualification
17. Backward compatibility and pipeline switches
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
RAG_SERVICE_DIR = REPO_ROOT / "rag-service"
if str(RAG_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_SERVICE_DIR))

from research.claim_grounding.answer_validator import AnswerValidator
from research.claim_grounding.citation_verifier import CitationVerifier
from research.claim_grounding.claim_classifier import ClaimClassifier
from research.claim_grounding.claim_extractor import ClaimExtractor
from research.claim_grounding.engine import ClaimGroundingEngine, get_claim_grounding_engine
from research.claim_grounding.entailment_checker import EntailmentChecker
from research.claim_grounding.evidence_matcher import EvidenceMatcher
from research.claim_grounding.models import (
    AtomicClaim,
    CitationStatus,
    ClaimEvidenceMatch,
    ClaimGroundingDecision,
    ClaimHandlingAction,
    ClaimStatus,
    ClaimType,
    GenerationMetadata,
    RiskLevel,
)


class TestClaimGrounding(unittest.TestCase):
    """Unit tests for atomic claim extraction, classification, matching, entailment, and validation."""

    def setUp(self):
        self.extractor = ClaimExtractor()
        self.classifier = ClaimClassifier()
        self.matcher = EvidenceMatcher()
        self.entailment_checker = EntailmentChecker()
        self.citation_verifier = CitationVerifier()
        self.validator = AnswerValidator()
        self.engine = ClaimGroundingEngine()

    def test_01_atomic_claim_extraction(self):
        """Test extraction of atomic claims from compound answer text."""
        text = (
            "The offense of theft is defined under Section 303. "
            "Whoever commits theft shall be punished with imprisonment up to three years; "
            "electronic evidence is admissible under Section 63."
        )
        claims = self.extractor.extract_claims(text)
        self.assertGreaterEqual(len(claims), 2)
        for c in claims:
            self.assertIsInstance(c, AtomicClaim)
            self.assertTrue(len(c.claim_text) >= 15)

    def test_02_source_span_preservation(self):
        """Test exact character span preservation from the original text."""
        text = "Under Section 303 of BNS, theft is punishable with imprisonment."
        claims = self.extractor.extract_claims(text)
        self.assertEqual(len(claims), 1)
        claim = claims[0]
        # Extracted span must match original text exactly
        extracted_slice = text[claim.source_span_start:claim.source_span_end]
        self.assertEqual(extracted_slice, claim.claim_text)

    def test_03_claim_classification(self):
        """Test classification into legal roles (punishment, procedural, evidentiary, etc.)."""
        c1 = AtomicClaim("C1", "Whoever commits theft shall be punished with imprisonment.", ClaimType.GENERAL_INFORMATION, 0, 10)
        self.classifier.classify_claim(c1)
        self.assertEqual(c1.claim_type, ClaimType.PUNISHMENT)
        self.assertEqual(c1.risk_level, RiskLevel.HIGH)

        c2 = AtomicClaim("C2", "Police officers may arrest the suspect without a warrant.", ClaimType.GENERAL_INFORMATION, 0, 10)
        self.classifier.classify_claim(c2)
        self.assertEqual(c2.claim_type, ClaimType.PROCEDURAL_REQUIREMENT)

        c3 = AtomicClaim("C3", "Electronic evidence certificate is mandatory for printouts.", ClaimType.GENERAL_INFORMATION, 0, 10)
        self.classifier.classify_claim(c3)
        self.assertEqual(c3.claim_type, ClaimType.EVIDENTIARY_REQUIREMENT)

    def test_04_claim_weighting(self):
        """Test risk level importance weights assigned to claims."""
        c_punish = AtomicClaim("C1", "Punishable with imprisonment.", ClaimType.PUNISHMENT, 0, 10)
        self.classifier.classify_claim(c_punish)
        self.assertEqual(c_punish.importance_weight, 1.00)

        c_general = AtomicClaim("C2", "This information is intended for general guidance.", ClaimType.GENERAL_INFORMATION, 0, 10)
        self.classifier.classify_claim(c_general)
        self.assertEqual(c_general.importance_weight, 0.50)

    def test_05_evidence_matching(self):
        """Test matching claim to retrieved chunks."""
        claim = AtomicClaim("C1", "Theft is punished under Section 303 of BNS.", ClaimType.PUNISHMENT, 0, 10)
        evidence = [
            {
                "chunk_id": "chunk_bns_303",
                "statute": "Bharatiya Nyaya Sanhita, 2023",
                "section": "Section 303",
                "text": "Section 303. Whoever commits theft shall be punished with imprisonment up to three years.",
            },
            {
                "chunk_id": "chunk_it_43",
                "statute": "Information Technology Act, 2000",
                "section": "Section 43",
                "text": "Section 43. Penalty and compensation for damage to computer.",
            },
        ]
        matches = self.matcher.match_claim_to_evidence(claim, evidence)
        self.assertTrue(len(matches) >= 1)
        self.assertEqual(matches[0].chunk_id, "chunk_bns_303")
        self.assertGreater(matches[0].match_score, 0.50)

    def test_06_supported_claims(self):
        """Test entailment verification for fully supported claim."""
        claim = AtomicClaim(
            "C1",
            "Under Section 303 of BNS, theft is punishable with imprisonment up to three years.",
            ClaimType.PUNISHMENT,
            0,
            50,
        )
        match = ClaimEvidenceMatch(
            claim_id="C1",
            chunk_id="bns_303",
            statute="Bharatiya Nyaya Sanhita, 2023",
            section="Section 303",
            source_identifier="BNS",
            match_score=0.90,
            evidence_text="Section 303. Whoever commits theft shall be punished with imprisonment for a term which may extend to three years, or with fine.",
            support_status=ClaimStatus.INSUFFICIENT_EVIDENCE,
        )
        status, score, best, reason = self.entailment_checker.evaluate_support(claim, [match])
        self.assertEqual(status, ClaimStatus.SUPPORTED)
        self.assertEqual(score, 1.0)

    def test_07_partially_supported_claims(self):
        """Test claim that overstates or partially captures statutory conditions."""
        claim = AtomicClaim(
            "C1",
            "Under Section 420 of BNS, cheating is punished with lifetime freezing of all bank assets.",
            ClaimType.PUNISHMENT,
            0,
            50,
        )
        match = ClaimEvidenceMatch(
            claim_id="C1",
            chunk_id="bns_318",
            statute="Bharatiya Nyaya Sanhita, 2023",
            section="Section 318",
            source_identifier="BNS",
            match_score=0.45,
            evidence_text="Section 318. Cheating. Whoever cheats shall be punished with imprisonment up to three years.",
            support_status=ClaimStatus.INSUFFICIENT_EVIDENCE,
        )
        status, score, best, reason = self.entailment_checker.evaluate_support(claim, [match])
        self.assertIn(status, [ClaimStatus.PARTIALLY_SUPPORTED, ClaimStatus.UNSUPPORTED])

    def test_08_unsupported_claims(self):
        """Test claim with zero supporting evidence in retrieved context."""
        claim = AtomicClaim(
            "C1",
            "Under Section 999 of Space Law, lunar rovers must obtain state licensing.",
            ClaimType.STATUTORY_PROVISION,
            0,
            50,
        )
        status, score, best, reason = self.entailment_checker.evaluate_support(claim, [])
        self.assertEqual(status, ClaimStatus.UNSUPPORTED)
        self.assertEqual(score, 0.0)

    def test_09_contradicted_claims(self):
        """Test claim that directly contradicts retrieved statutory text."""
        claim = AtomicClaim(
            "C1",
            "Under Section 303 of BNS, theft is punishable with imprisonment up to 10 years.",
            ClaimType.PUNISHMENT,
            0,
            50,
        )
        match = ClaimEvidenceMatch(
            claim_id="C1",
            chunk_id="bns_303",
            statute="Bharatiya Nyaya Sanhita, 2023",
            section="Section 303",
            source_identifier="BNS",
            match_score=0.85,
            evidence_text="Section 303. (2) Whoever commits theft shall be punished with imprisonment for a term which may extend to 3 years, or with fine.",
            support_status=ClaimStatus.INSUFFICIENT_EVIDENCE,
        )
        status, score, best, reason = self.entailment_checker.evaluate_support(claim, [match])
        self.assertEqual(status, ClaimStatus.CONTRADICTED)

    def test_10_missing_citations(self):
        """Test detection of missing citations on high-risk statutory claims."""
        claim = AtomicClaim(
            "C1",
            "Theft of property is punishable with imprisonment up to three years.",
            ClaimType.PUNISHMENT,
            0,
            50,
            attached_citations=[],
        )
        cit_results = self.citation_verifier.verify_citations(claim, [], [], ClaimStatus.SUPPORTED)
        self.assertEqual(len(cit_results), 1)
        self.assertEqual(cit_results[0].status, CitationStatus.MISSING_CITATION)

    def test_11_invalid_citations(self):
        """Test detection of non-existent or fabricated source references."""
        claim = self.extractor.extract_claims("According to [Source 99], copyright infringement requires execution.")[0]
        cit_results = self.citation_verifier.verify_citations(
            claim,
            [{"chunk_id": "c1", "statute": "BNS"}], # only 1 source exists
            [],
            ClaimStatus.UNSUPPORTED,
        )
        self.assertEqual(len(cit_results), 1)
        self.assertEqual(cit_results[0].status, CitationStatus.INVALID_SOURCE)

    def test_12_misaligned_citations(self):
        """Test citation attributed to wrong statute (e.g. Section 66C of CPA)."""
        claim = self.extractor.extract_claims("Section 66C of Consumer Protection Act covers hacking.")[0]
        evidence = [
            {"chunk_id": "it_66c", "document_name": "Information Technology Act, 2000", "section": "Section 66C", "statute": "IT Act"}
        ]
        matches = self.matcher.match_claim_to_evidence(claim, evidence)
        cit_results = self.citation_verifier.verify_citations(claim, evidence, matches, ClaimStatus.PARTIALLY_SUPPORTED)
        self.assertTrue(any(c.status == CitationStatus.MISALIGNED_CITATION for c in cit_results))

    def test_13_temporal_claims(self):
        """Test temporal applicability verification."""
        claim = self.extractor.extract_claims("Bharatiya Nyaya Sanhita came into effect on 1st July 2024.")[0]
        self.classifier.classify_claim(claim)
        self.assertEqual(claim.claim_type, ClaimType.TEMPORAL_CLAIM)

    def test_14_multi_statute_evidence(self):
        """Test answer with multiple complementary statutes."""
        answer = (
            "Under Section 303 of Bharatiya Nyaya Sanhita, theft carries imprisonment. "
            "Under Section 35 of Bharatiya Nagarik Suraksha Sanhita, warrantless arrest is permitted for cognizable theft."
        )
        evidence = [
            {"chunk_id": "bns_303", "statute": "Bharatiya Nyaya Sanhita, 2023", "section": "Section 303", "text": "Section 303. Whoever commits theft shall be punished..."},
            {"chunk_id": "bnss_35", "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023", "section": "Section 35", "text": "Section 35. When police may arrest without warrant..."},
        ]
        res = self.engine.verify_and_qualify_answer(answer, evidence)
        self.assertEqual(len(res.claims), 2)
        self.assertGreaterEqual(res.grounding_score, 0.90)

    def test_15_high_risk_unsupported_claims(self):
        """Test that high-risk unsupported claims are flagged and qualified."""
        answer = "Corporate directors face mandatory hanging under Section 999 for copyright infringement."
        evidence = [
            {"chunk_id": "bns_303", "statute": "Bharatiya Nyaya Sanhita, 2023", "section": "Section 303", "text": "Section 303. Theft definition."}
        ]
        res = self.engine.verify_and_qualify_answer(answer, evidence)
        self.assertGreater(res.high_risk_error_count, 0)
        self.assertTrue(res.modifications_made)
        self.assertIn("Note: This specific proposition could not be verified", res.validated_answer)

    def test_16_answer_qualification(self):
        """Test that answer validator qualifies ungrounded propositions while keeping text intact."""
        decision = ClaimGroundingDecision(
            claim=AtomicClaim("C1", "The accused must surrender passport.", ClaimType.PROCEDURAL_REQUIREMENT, 0, 36, risk_level=RiskLevel.HIGH),
            status=ClaimStatus.UNSUPPORTED,
            support_score=0.0,
        )
        val_text, mods = self.validator.validate_and_qualify("The accused must surrender passport.", [decision])
        self.assertTrue(mods)
        self.assertIn("The accused must surrender passport.", val_text)
        self.assertIn("could not be verified", val_text)

    def test_17_backward_compatibility_switches(self):
        """Test that default initialization produces backward-compatible structures."""
        res = self.engine.verify_and_qualify_answer(
            answer="",
            evidence_chunks=[],
            generation_metadata=GenerationMetadata(generation_provider="test_llm"),
        )
        self.assertEqual(res.grounding_score, 1.0)
        self.assertEqual(len(res.claims), 0)
        self.assertFalse(res.modifications_made)


if __name__ == "__main__":
    unittest.main()
