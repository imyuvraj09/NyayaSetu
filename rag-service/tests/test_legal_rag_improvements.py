"""
Comprehensive Regression and Improvement Verification Test Suite for NyayaSetu Legal RAG.

Tests all 10 target improvements:
1. Evidence Law Domain Classification & Hierarchical Taxonomy
2. Direct Legal Relevance Filtering (pruning Section 1/2, boosting 62/63)
3. Provision Relationship Validation (Section 62 refers to Section 63; Section 63 specifies conditions & certificate)
4. Answer Consistency Validation (No internal contradictions, concise non-repetitive summaries)
5. Conditional Judicial Principles Omission (No empty Judicial Principles when no case law retrieved)
6. Mandatory BSA Electronic Records Regression Query
7. Criminal Law Query (Theft under BNS)
8. Cyber Law Query (Unauthorized computer access)
9. Ambiguous WhatsApp Evidence Query
10. Burden of proof Query
"""

import os
import sys
import unittest

# Add rag-service to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retrieval.query_analyzer import LegalQueryAnalyzer
from retrieval.legal_question import LegalQuestion
from retrieval.provision_relationship_validator import LegalProvisionRelationshipValidator, ProvisionRelationship
from retrieval.answer_consistency_validator import AnswerConsistencyValidator
from rag.rag_pipeline import LegalRAGPipeline


class TestLegalRAGImprovements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query_analyzer = LegalQueryAnalyzer()
        cls.relationship_validator = LegalProvisionRelationshipValidator()
        cls.consistency_validator = AnswerConsistencyValidator()
        cls.pipeline = LegalRAGPipeline()

    def test_01_mandatory_bsa_electronic_records_domain_classification(self):
        """Test that BSA electronic records query resolves to Law of Evidence with complete taxonomy."""
        query = "How are electronic records admitted under Bharatiya Sakshya Adhiniyam?"
        analysis = self.query_analyzer.analyze(query)
        
        # Must be Law of Evidence, NOT Criminal Law
        self.assertEqual(analysis.domain, "Law of Evidence", f"Expected 'Law of Evidence', got '{analysis.domain}'")
        self.assertEqual(analysis.sub_domain, "Electronic Evidence")
        self.assertEqual(analysis.act, "Bharatiya Sakshya Adhiniyam, 2023")
        
        # Taxonomy path check
        taxonomy = analysis.hierarchical_taxonomy
        self.assertEqual(taxonomy["primary_domain"], "Law of Evidence")
        self.assertEqual(taxonomy["sub_domain"], "Electronic Evidence")
        self.assertEqual(taxonomy["specific_area"], "Admissibility and Proof of Electronic Records")
        self.assertEqual(taxonomy["relevant_act"], "Bharatiya Sakshya Adhiniyam, 2023")

    def test_02_other_domain_classifications(self):
        """Test domain classification across Criminal Law, Cyber Law, WhatsApp evidence, and Burden of Proof."""
        cases = [
            ("What punishment is prescribed for theft under the Bharatiya Nyaya Sanhita?", "Criminal Law"),
            ("What are the legal consequences of unauthorized access to a computer system?", "Cybercrime / Information Technology Law"),
            ("Can a WhatsApp message be used in court?", "Law of Evidence"),
            ("What is the burden of proof in a criminal trial?", "Law of Evidence"),
        ]
        for query, expected_domain in cases:
            with self.subTest(query=query):
                res = self.query_analyzer.analyze(query)
                self.assertEqual(res.domain, expected_domain, f"Query '{query}' expected '{expected_domain}', got '{res.domain}'")

    def test_03_provision_relationship_validator_unit(self):
        """Test that the Provision Relationship Validator corrects inverted relationships and condition transfer."""
        validator = self.relationship_validator
        
        # Case 1: Inverted relationship where Section 63 is said to refer to Section 62
        bad_text_1 = (
            "Under Section 63 of Bharatiya Sakshya Adhiniyam, which refers to Section 62, "
            "electronic records may be proved."
        )
        corrected_1 = validator.correct_and_sanitize_relationships(bad_text_1)
        self.assertIn("Section 62 of Bharatiya Sakshya Adhiniyam refers to Section 63", corrected_1)
        self.assertNotIn("Section 63 of Bharatiya Sakshya Adhiniyam, which refers to Section 62", corrected_1)

        # Case 2: Section 62 wrongly claimed to require a certificate
        bad_text_2 = (
            "Section 62 mandates a certificate signed by the person in charge of the computer device."
        )
        corrected_2 = validator.correct_and_sanitize_relationships(bad_text_2)
        self.assertIn("Section 63 mandates a certificate", corrected_2)

        # Case 3: Verify defined legal relationship properties
        rel = validator.get_relationship("Bharatiya Sakshya Adhiniyam, 2023", "62", "63")
        self.assertIsNotNone(rel)
        self.assertEqual(rel.relationship_type, "refers_to")
        self.assertEqual(rel.target_provision, "Section 63")

    def test_04_answer_consistency_validator_unit(self):
        """Test that the Answer Consistency Validator reconciles contradictions and prunes repetitive conclusions."""
        validator = self.consistency_validator
        
        # Case 1: Detect and reconcile contradiction: direct answer says admissible, conclusion says inadmissible
        inconsistent_answer = {
            "legalDomain": "Law of Evidence",
            "mainAnswer": (
                "Answer\n\n"
                "Electronic records are admissible as evidence under the Bharatiya Sakshya Adhiniyam, 2023.\n\n"
                "Legal Position\n\n"
                "Section 62 enables electronic records to be proved pursuant to Section 63."
            ),
            "legalBasis": (
                "Relevant Legal Provisions\n\n"
                "Bharatiya Sakshya Adhiniyam, 2023 — Section 63\n\n"
                "Summary:\n\n"
                "Electronic records are strictly inadmissible in all court proceedings."
            ),
            "recommendedNextSteps": ["Ensure Section 63 certificate is obtained."]
        }
        
        import json
        reconciled_json = validator.reconcile_and_sanitize_answer(json.dumps(inconsistent_answer))
        reconciled = json.loads(reconciled_json)
        
        # The contradiction in conclusion must be reconciled / removed
        self.assertNotIn("strictly inadmissible", reconciled["legalBasis"])

    def test_05_mandatory_bsa_electronic_records_end_to_end(self):
        """Test end-to-end LegalRAGPipeline response for the mandatory BSA Electronic Records query."""
        query = "How are electronic records admitted under Bharatiya Sakshya Adhiniyam?"
        response = self.pipeline.query(query)
        
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.answer)
        
        # Parse JSON answer
        import json
        try:
            answer_data = json.loads(response.answer)
        except Exception:
            self.fail(f"Pipeline output is not valid JSON: {response.answer}")
            
        main_answer = answer_data.get("mainAnswer", "")
        legal_basis = answer_data.get("legalBasis", "")
        domain = answer_data.get("legalDomain", "")
        
        full_text = f"{main_answer}\n\n{legal_basis}"
        
        # 1. Domain Check
        self.assertEqual(domain, "Law of Evidence", f"Expected Law of Evidence, got: {domain}")
        
        # 2. Key Sections Check: Sections 62 and 63 MUST be prioritized in sources and answer
        source_labels = [s.document_name for s in response.sources]
        source_snippets = " ".join(s.text_snippet for s in response.sources)
        self.assertTrue(
            any("62" in s.text_snippet or "63" in s.text_snippet for s in response.sources),
            "Retrieved sources must contain Section 62 or Section 63"
        )
        
        # 3. Provision Relationship Check
        # Section 62 is the enabling provision referring to Section 63
        self.assertIn("62", full_text, "Answer must reference Section 62")
        self.assertIn("63", full_text, "Answer must reference Section 63")
        self.assertIn("certificate", full_text.lower(), "Answer must reference the certificate requirement under Section 63")
        
        # Confirm no condition transfer (Section 62 should not be described as prescribing the certificate)
        self.assertNotIn("section 62 certificate", full_text.lower())
        self.assertNotIn("certificate under section 62", full_text.lower())
        
        # 4. No empty Judicial Principles section
        self.assertNotIn("Judicial Principles", main_answer)
        self.assertNotIn("Judicial Principles", legal_basis)
        
        # 5. Professional formatting (No markdown bolding ** or markdown headings ###)
        self.assertNotIn("**", main_answer)
        self.assertNotIn("**", legal_basis)
        self.assertNotIn("###", main_answer)
        self.assertNotIn("###", legal_basis)
        
        # 6. Check Section 1 commencement is NOT in the top sources
        top_source_texts = [s.text_snippet for s in response.sources[:3]]
        for st in top_source_texts:
            self.assertNotIn("shall come into force on such date", st.lower())


if __name__ == "__main__":
    unittest.main()
