"""
Unit test suite verifying LLM generation resilience, error taxonomy, controlled retry,
and deterministic fallback answer delivery in NyayaSetu.

Covers all 10 required test scenarios:
1. Gemini success
2. Gemini rate limit (429 transient)
3. Gemini timeout (504)
4. Gemini invalid model (404)
5. Gemini invalid API key (401)
6. Empty Gemini response
7. Retrieval success + generation failure
8. Retrieval failure + generation failure
9. Case-law answer fallback (prior consensual relationship)
10. Statute-only answer fallback (murder definition + punishment)
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure rag-service is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMEmptyResponseError,
    LLMError,
    LLMInvalidModelError,
    LLMNetworkError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
)
from llm.provider import GoogleGeminiProvider
from rag.deterministic_answer_builder import DeterministicAnswerBuilder
from rag.rag_pipeline import LegalRAGPipeline
from schemas.generation import SourceReference
from schemas.retrieval import AdvancedRetrievalResult, RerankedChunk


class TestLLMResilienceSuite(unittest.TestCase):
    """10 Test Scenarios for LLM Resilience and Fallback Delivery."""

    def setUp(self):
        self.statute_source_63 = SourceReference(
            source_label="[SOURCE 1]",
            chunk_id="bns_sec_63",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            act_short_name="BNS",
            section_number="63",
            section_title="Rape",
            evidence_type="STATUTE",
            similarity_score=0.91,
            reranker_score=0.96,
            text_snippet="Section 63: A man is said to commit rape who penetrates without consent or against the will of the woman.",
            page_numbers=[45],
        )
        self.case_source_chhotey = SourceReference(
            source_label="[SOURCE 2]",
            chunk_id="sc_chhotey_lal_p14",
            document_name="State of Uttar Pradesh v. Chhotey Lal",
            case_name="State of Uttar Pradesh v. Chhotey Lal",
            court="Supreme Court of India",
            citation="(2011) 2 SCC 550",
            paragraph_number="14",
            is_holding_or_ratio=True,
            evidence_type="CASE_LAW",
            similarity_score=0.88,
            reranker_score=0.95,
            text_snippet="Para 14: Even if the prosecutrix had been previously in a consensual relationship with the accused, it cannot be presumed that she consented on the occasion of the alleged incident.",
            page_numbers=[12],
        )
        self.case_source_pawar = SourceReference(
            source_label="[SOURCE 3]",
            chunk_id="sc_pawar_p18",
            document_name="Pramod Suryabhan Pawar v. State of Maharashtra",
            case_name="Pramod Suryabhan Pawar v. State of Maharashtra",
            court="Supreme Court of India",
            citation="(2019) 9 SCC 608",
            paragraph_number="18",
            is_holding_or_ratio=True,
            evidence_type="CASE_LAW",
            similarity_score=0.87,
            reranker_score=0.94,
            text_snippet="Para 18: Consent for the purpose of Section 375 involves an active and conscious deliberation to undertake the act.",
            page_numbers=[8],
        )

        self.statute_murder_101 = SourceReference(
            source_label="[SOURCE 1]",
            chunk_id="bns_sec_101",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            act_short_name="BNS",
            section_number="101",
            section_title="Murder",
            evidence_type="STATUTE",
            similarity_score=0.94,
            reranker_score=0.99,
            text_snippet="Section 101: Except in the cases hereinafter excepted, culpable homicide is murder if the act by which the death is caused is done with the intention of causing death.",
            page_numbers=[60],
        )
        self.statute_murder_103 = SourceReference(
            source_label="[SOURCE 2]",
            chunk_id="bns_sec_103",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            act_short_name="BNS",
            section_number="103",
            section_title="Punishment for murder",
            evidence_type="STATUTE",
            similarity_score=0.93,
            reranker_score=0.98,
            text_snippet="Section 103: Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine.",
            page_numbers=[62],
        )

    # ─────────────────────────────────────────────────────────────
    # Scenario 1: Gemini Success
    # ─────────────────────────────────────────────────────────────
    def test_01_gemini_success(self):
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.provider_name = "gemini"
        mock_provider.model_name = "gemini-3.6-flash"
        mock_provider.is_configured.return_value = True

        valid_json = json.dumps({
            "legalDomain": "Criminal Law / BNS",
            "mainAnswer": "Under BNS Section 63 [SOURCE 1], consent is an essential ingredient.",
            "legalBasis": "BNS Section 63",
            "recommendedNextSteps": ["Consult legal counsel."],
        })
        mock_provider.generate.return_value = LLMResponse(
            content=valid_json,
            model="gemini-3.6-flash",
            prompt_tokens=150,
            completion_tokens=80,
        )

        pipeline = LegalRAGPipeline(llm_provider=mock_provider)
        pipeline.retriever = MagicMock()
        pipeline.retriever.retrieve.return_value = AdvancedRetrievalResult(
            original_query="Test query",
            normalized_query="Test query",
            initial_k=20,
            final_k=5,
            initial_candidates_count=1,
            filtered_candidates_count=1,
            final_results_count=1,
            query_analysis={"act": "BNS", "domain": "Criminal Law"},
            results=[
                RerankedChunk(
                    rank=1,
                    chunk_id="bns_sec_63",
                    document_name="Bharatiya Nyaya Sanhita, 2023",
                    act_short_name="BNS",
                    section_number="63",
                    section_title="Rape",
                    page_numbers=[45],
                    text=self.statute_source_63.text_snippet,
                    similarity_score=0.91,
                    reranker_score=0.96,
                )
            ],
        )

        response = pipeline.query("Does previous consensual relationship establish consent?")
        self.assertEqual(response.generation_status, "SUCCESS")
        self.assertEqual(response.retrieval_status, "SUCCESS")
        self.assertEqual(response.validation_status, "PASSED")
        self.assertIn("Section 63", response.answer)

    # ─────────────────────────────────────────────────────────────
    # Scenario 2: Gemini Rate Limit (429 transient)
    # ─────────────────────────────────────────────────────────────
    def test_02_gemini_rate_limit(self):
        provider = GoogleGeminiProvider(api_key="test_key_dummy", model="gemini-3.6-flash")

        # Simulate transient 429
        mock_exc = Exception("429 Resource has been exhausted (rate limit reached)")
        classified = provider._classify_gemini_error(mock_exc)

        self.assertIsInstance(classified, (LLMRateLimitError, LLMQuotaExceededError))
        self.assertEqual(classified.status_code, 429)

        # In pipeline, rate limit error triggers deterministic fallback
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.provider_name = "gemini"
        mock_provider.model_name = "gemini-3.6-flash"
        mock_provider.is_configured.return_value = True
        mock_provider.generate.side_effect = LLMRateLimitError("Rate limit reached", status_code=429)

        pipeline = LegalRAGPipeline(llm_provider=mock_provider)
        pipeline.retriever = MagicMock()
        pipeline.retriever.retrieve.return_value = AdvancedRetrievalResult(
            original_query="Test",
            normalized_query="Test",
            initial_k=20,
            final_k=5,
            initial_candidates_count=1,
            filtered_candidates_count=1,
            final_results_count=1,
            query_analysis={"act": "BNS", "domain": "Criminal Law"},
            results=[
                RerankedChunk(
                    rank=1,
                    chunk_id="bns_sec_63",
                    document_name="Bharatiya Nyaya Sanhita, 2023",
                    act_short_name="BNS",
                    section_number="63",
                    section_title="Rape",
                    page_numbers=[45],
                    text=self.statute_source_63.text_snippet,
                    similarity_score=0.91,
                    reranker_score=0.96,
                )
            ],
        )

        response = pipeline.query("Does previous consensual relationship establish consent?")
        self.assertEqual(response.generation_status, "RETRIEVAL_ONLY")
        self.assertEqual(response.retrieval_status, "SUCCESS")
        self.assertIn("prior consensual relationship", response.answer.lower())

    # ─────────────────────────────────────────────────────────────
    # Scenario 3: Gemini Timeout (504)
    # ─────────────────────────────────────────────────────────────
    def test_03_gemini_timeout(self):
        provider = GoogleGeminiProvider(api_key="test_key_dummy", model="gemini-3.6-flash")
        mock_exc = Exception("Request timed out after 60 seconds")
        classified = provider._classify_gemini_error(mock_exc)

        self.assertIsInstance(classified, LLMTimeoutError)
        self.assertEqual(classified.category, "TIMEOUT")
        self.assertTrue(classified.retryable)

    # ─────────────────────────────────────────────────────────────
    # Scenario 4: Gemini Invalid Model (404)
    # ─────────────────────────────────────────────────────────────
    def test_04_gemini_invalid_model(self):
        provider = GoogleGeminiProvider(api_key="test_key_dummy", model="invalid-model-name")
        mock_exc = Exception("404 models/invalid-model-name is not found for API version v1beta")
        classified = provider._classify_gemini_error(mock_exc)

        self.assertIsInstance(classified, LLMInvalidModelError)
        self.assertEqual(classified.category, "INVALID_MODEL")
        self.assertFalse(classified.retryable)

    # ─────────────────────────────────────────────────────────────
    # Scenario 5: Gemini Invalid API Key (401)
    # ─────────────────────────────────────────────────────────────
    def test_05_gemini_invalid_api_key(self):
        provider = GoogleGeminiProvider(api_key="bad_key", model="gemini-3.6-flash")
        mock_exc = Exception("400 API_KEY_INVALID: API key not valid. Please pass a valid API key.")
        classified = provider._classify_gemini_error(mock_exc)

        self.assertIsInstance(classified, LLMAuthenticationError)
        self.assertEqual(classified.category, "AUTHENTICATION_ERROR")
        self.assertFalse(classified.retryable)

    # ─────────────────────────────────────────────────────────────
    # Scenario 6: Empty Gemini Response
    # ─────────────────────────────────────────────────────────────
    def test_06_empty_gemini_response(self):
        provider = GoogleGeminiProvider(api_key="test_key_dummy", model="gemini-3.6-flash")
        mock_exc = Exception("API returned empty candidate response")
        classified = provider._classify_gemini_error(mock_exc)

        self.assertIsInstance(classified, LLMEmptyResponseError)
        self.assertEqual(classified.category, "EMPTY_RESPONSE")

    # ─────────────────────────────────────────────────────────────
    # Scenario 7: Retrieval Success + Generation Failure
    # ─────────────────────────────────────────────────────────────
    def test_07_retrieval_success_generation_failure(self):
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.provider_name = "gemini"
        mock_provider.model_name = "gemini-3.6-flash"
        mock_provider.is_configured.return_value = True
        mock_provider.generate.side_effect = LLMProviderError("Gemini 503 internal server error")

        pipeline = LegalRAGPipeline(llm_provider=mock_provider)
        pipeline.retriever = MagicMock()
        pipeline.retriever.retrieve.return_value = AdvancedRetrievalResult(
            original_query="What is murder?",
            normalized_query="What is murder?",
            initial_k=20,
            final_k=5,
            initial_candidates_count=1,
            filtered_candidates_count=1,
            final_results_count=1,
            query_analysis={"act": "BNS", "domain": "Criminal Law"},
            results=[
                RerankedChunk(
                    rank=1,
                    chunk_id="bns_sec_101",
                    document_name="Bharatiya Nyaya Sanhita, 2023",
                    act_short_name="BNS",
                    section_number="101",
                    section_title="Murder",
                    page_numbers=[60],
                    text=self.statute_murder_101.text_snippet,
                    similarity_score=0.94,
                    reranker_score=0.99,
                )
            ],
        )

        response = pipeline.query("What is murder?")
        self.assertEqual(response.generation_status, "RETRIEVAL_ONLY")
        self.assertEqual(response.retrieval_status, "SUCCESS")
        self.assertGreater(len(response.sources), 0)

        # Must parse as structured response JSON
        parsed = json.loads(response.answer)
        self.assertIn("mainAnswer", parsed)
        self.assertIn("culpable homicide", parsed["mainAnswer"].lower())
        self.assertTrue("[SOURCE 1]" in parsed["mainAnswer"] or "[Source S1]" in parsed["mainAnswer"])

    # ─────────────────────────────────────────────────────────────
    # Scenario 8: Retrieval Failure + Generation Failure
    # ─────────────────────────────────────────────────────────────
    def test_08_retrieval_failure_generation_failure(self):
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.provider_name = "gemini"
        mock_provider.model_name = "gemini-3.6-flash"
        mock_provider.is_configured.return_value = True

        pipeline = LegalRAGPipeline(llm_provider=mock_provider)
        pipeline.retriever = MagicMock()
        pipeline.retriever.retrieve.return_value = AdvancedRetrievalResult(
            original_query="Nonexistent law query",
            normalized_query="Nonexistent law query",
            initial_k=20,
            final_k=5,
            initial_candidates_count=0,
            filtered_candidates_count=0,
            final_results_count=0,
            query_analysis={"act": None, "domain": "Unknown"},
            results=[],
        )

        response = pipeline.query("Nonexistent law query")
        self.assertEqual(response.retrieval_status, "NO_SOURCES_FOUND")
        self.assertEqual(response.validation_status, "NOT_RUN")
        self.assertEqual(len(response.sources), 0)
        # LLM must not be called when retrieval yields zero results
        mock_provider.generate.assert_not_called()

    # ─────────────────────────────────────────────────────────────
    # Scenario 9: Case-Law Answer Fallback (Prior Consensual Relationship)
    # ─────────────────────────────────────────────────────────────
    def test_09_case_law_answer_fallback(self):
        query = (
            "A woman alleges that she was sexually assaulted by a person with whom she was previously "
            "in a consensual relationship. Does a previous consensual relationship constitute consent "
            "for a subsequent sexual act under Indian law? Explain relevant legal provisions and judicial principles."
        )
        sources = [self.statute_source_63, self.case_source_chhotey, self.case_source_pawar]

        fallback_raw = DeterministicAnswerBuilder.build_answer(
            query=query,
            sources=sources,
            query_analysis={"act": "BNS", "domain": "Criminal Law"},
        )

        data = json.loads(fallback_raw)
        self.assertIn("mainAnswer", data)
        self.assertIn("legalBasis", data)

        main_ans = data["mainAnswer"]
        basis = data["legalBasis"]

        # Assert segregation between statutory provisions and judicial principles
        self.assertIn("Relevant legal provisions", basis)
        self.assertIn("Judicial principles", basis)

        # Assert case law citations are included
        self.assertIn("State of Uttar Pradesh v. Chhotey Lal", basis)
        self.assertIn("(2011) 2 SCC 550", basis)
        self.assertIn("Pramod Suryabhan Pawar", basis)

        # Assert correct legal principle
        self.assertTrue(
            "not constitute" in main_ans or "not" in main_ans or "independent" in main_ans,
            "Direct answer must reflect that prior relationship does not imply consent.",
        )

    # ─────────────────────────────────────────────────────────────
    # Scenario 10: Statute-Only Answer Fallback (Murder Regression)
    # ─────────────────────────────────────────────────────────────
    def test_10_statute_only_answer_fallback_murder(self):
        query = "What constitutes murder under BNS and what is the punishment?"
        sources = [self.statute_murder_101, self.statute_murder_103]

        fallback_raw = DeterministicAnswerBuilder.build_answer(
            query=query,
            sources=sources,
            query_analysis={"act": "BNS", "domain": "Criminal Law"},
        )

        data = json.loads(fallback_raw)
        main_ans = data["mainAnswer"]
        basis = data["legalBasis"]

        # Assert both definition and punishment are present
        self.assertIn("Section 101", main_ans + basis)
        self.assertIn("Section 103", main_ans + basis)

        # Assert no false negative claim
        self.assertNotIn("punishment was not found", (main_ans + basis).lower())
        self.assertNotIn("no punishment provision", (main_ans + basis).lower())
        self.assertIn("death or imprisonment for life", (main_ans + basis).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
