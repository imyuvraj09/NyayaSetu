"""
NyayaSetu RAG Service — Google Gemini Integration Verification Suite.

Tests:
1. GoogleGeminiProvider instantiation, defaults (gemini-2.5-flash), and model name stripping.
2. Configuration check via is_configured().
3. Factory function get_llm_provider resolution for 'gemini' and 'google'.
4. Error classification:
   - 429 Rate limit -> LLMRateLimitError
   - 429 Quota / ResourceExhausted -> LLMQuotaExceededError
   - Request timeout -> LLMTimeoutError
   - Network connection / 5xx -> LLMServiceUnavailableError
   - 401 Auth error -> LLMError (AUTH_ERROR)
5. 3-attempt exponential backoff retry loop on retryable errors.
6. Immediate exit for non-retryable errors without sleep loop.
7. LegalRAGPipeline integration and fallback source preservation.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from llm.base import (
    LLMError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResponse,
    LLMServiceUnavailableError,
    LLMTimeoutError,
)
from llm.provider import (
    GeminiProvider,
    GoogleGeminiProvider,
    get_llm_provider,
)
from rag.rag_pipeline import LegalRAGPipeline
from schemas.retrieval import AdvancedRetrievalResult, RerankedChunk


class MockGeminiAPIError(Exception):
    def __init__(self, message, code=429):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = code


def test_gemini_provider_initialization():
    provider = GoogleGeminiProvider(api_key="mock-key-12345", model="gemini-2.5-flash")
    assert provider.provider_name == "gemini", f"Expected 'gemini', got {provider.provider_name}"
    assert provider.model_name == "gemini-2.5-flash", f"Expected 'gemini-2.5-flash', got {provider.model_name}"
    assert provider.is_configured() is True, "Expected is_configured to be True"

    # Test stripping 'models/' prefix
    provider_prefixed = GoogleGeminiProvider(api_key="mock-key-12345", model="models/gemini-2.5-flash")
    assert provider_prefixed.model_name == "gemini-2.5-flash", "Should strip 'models/' prefix"

    # Test unconfigured
    provider_empty = GoogleGeminiProvider(api_key="")
    assert provider_empty.is_configured() is False, "Expected is_configured to be False when key is empty"

    print("  [PASS] 1. GoogleGeminiProvider initialization, model normalization, and configuration check")


def test_factory_resolution():
    gemini_prov = get_llm_provider("gemini")
    assert isinstance(gemini_prov, GoogleGeminiProvider), "get_llm_provider('gemini') should return GoogleGeminiProvider"

    google_prov = get_llm_provider("google")
    assert isinstance(google_prov, GoogleGeminiProvider), "get_llm_provider('google') should return GoogleGeminiProvider"

    assert GeminiProvider is GoogleGeminiProvider, "GeminiProvider alias should match GoogleGeminiProvider"

    print("  [PASS] 2. get_llm_provider('gemini') and get_llm_provider('google') resolve correctly")


def test_error_classification():
    provider = GoogleGeminiProvider(api_key="mock-key")

    # 1. Rate limit
    rate_err = MockGeminiAPIError("Rate limit exceeded for requests per minute (RPM)", code=429)
    classified = provider._classify_gemini_error(rate_err)
    assert isinstance(classified, LLMRateLimitError)
    assert classified.retryable is True

    # 2. ResourceExhausted / Quota
    quota_err = MockGeminiAPIError("ResourceExhausted: Quota exceeded for project", code=429)
    classified_quota = provider._classify_gemini_error(quota_err)
    assert isinstance(classified_quota, LLMQuotaExceededError)
    assert classified_quota.retryable is False

    # 3. Timeout
    timeout_err = MockGeminiAPIError("Request timed out", code=504)
    classified_timeout = provider._classify_gemini_error(timeout_err)
    assert isinstance(classified_timeout, LLMTimeoutError)
    assert classified_timeout.retryable is True

    # 4. Service unavailable / 503
    server_err = MockGeminiAPIError("Internal server error", code=503)
    classified_server = provider._classify_gemini_error(server_err)
    assert isinstance(classified_server, LLMServiceUnavailableError)
    assert classified_server.retryable is True

    # 5. Auth error
    auth_err = MockGeminiAPIError("API_KEY_INVALID: User not found", code=400)
    classified_auth = provider._classify_gemini_error(auth_err)
    assert classified_auth.category == "AUTH_ERROR"
    assert classified_auth.retryable is False

    print("  [PASS] 3. Error classification (rate limit, quota, timeout, 503, auth) verified")


def test_retry_behavior():
    provider = GoogleGeminiProvider(api_key="mock-key")
    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise MockGeminiAPIError("Rate limit reached for requests per minute (RPM)", code=429)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = mock_generate

    with patch("google.genai.Client", return_value=mock_client), patch("time.sleep") as mock_sleep:
        try:
            provider.generate("Summarize Section 303 BNS")
            assert False, "Expected LLMRateLimitError"
        except LLMRateLimitError:
            pass

    assert call_count == 3, f"Expected 3 retry attempts, got {call_count}"
    assert mock_sleep.call_count == 2, f"Expected 2 sleep calls between 3 attempts, got {mock_sleep.call_count}"
    print("  [PASS] 4. Automatic 3-attempt exponential retry executed before raising rate limit error")


def test_non_retryable_quota_behavior():
    provider = GoogleGeminiProvider(api_key="mock-key")
    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise MockGeminiAPIError("ResourceExhausted: Quota exceeded for project", code=429)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = mock_generate

    with patch("google.genai.Client", return_value=mock_client), patch("time.sleep") as mock_sleep:
        try:
            provider.generate("Summarize Section 303 BNS")
            assert False, "Expected LLMQuotaExceededError"
        except LLMQuotaExceededError:
            pass

    assert call_count == 1, f"Expected 1 immediate attempt for non-retryable quota error, got {call_count}"
    assert mock_sleep.call_count == 0, "Non-retryable quota error should not sleep"
    print("  [PASS] 5. Non-retryable quota error exits immediately without redundant retry loops")


def test_successful_gemini_generation():
    provider = GoogleGeminiProvider(api_key="mock-key")

    mock_response = MagicMock()
    mock_response.text = "## Answer\n\nUnder Section 303 of Bharatiya Nyaya Sanhita, theft is defined as..."
    mock_response.usage_metadata.prompt_token_count = 142
    mock_response.usage_metadata.candidates_token_count = 85
    mock_candidate = MagicMock()
    mock_candidate.finish_reason = "STOP"
    mock_response.candidates = [mock_candidate]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        res = provider.generate("What is theft under BNS?")

    assert isinstance(res, LLMResponse)
    assert "Section 303" in res.content
    assert res.prompt_tokens == 142
    assert res.completion_tokens == 85
    assert res.metadata["provider"] == "gemini"
    print("  [PASS] 6. Successful Gemini generation returns formatted LLMResponse with token counts")


def test_pipeline_fallback_preserves_sources():
    mock_retriever = MagicMock()
    mock_chunks = [
        RerankedChunk(
            rank=1,
            chunk_id="bns_c0385",
            document_name="Bharatiya Nyaya Sanhita, 2023",
            document_type="criminal_code",
            source_filename="bns_2023.pdf",
            page_numbers=[81, 82],
            text="Section 303: Theft. Whoever, intending to take dishonestly any movable property...",
            similarity_score=0.75,
            reranker_score=0.91,
        ),
        RerankedChunk(
            rank=2,
            chunk_id="bnss_c0409",
            document_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            document_type="procedure_code",
            source_filename="bnss_2023.pdf",
            page_numbers=[89],
            text="Section 173: Information in cognizable cases...",
            similarity_score=0.72,
            reranker_score=0.88,
        ),
    ]
    mock_retriever.retrieve.return_value = AdvancedRetrievalResult(
        original_query="What is theft under BNS?",
        normalized_query="What is theft under BNS?",
        initial_k=20,
        final_k=5,
        initial_candidates_count=20,
        filtered_candidates_count=7,
        final_results_count=2,
        results=mock_chunks,
        document_distribution={"Bharatiya Nyaya Sanhita, 2023": 1, "Bharatiya Nagarik Suraksha Sanhita, 2023": 1},
    )

    mock_llm = MagicMock()
    mock_llm.provider_name = "gemini"
    mock_llm.model_name = "gemini-2.5-flash"
    mock_llm.generate.side_effect = LLMQuotaExceededError(
        "Google Gemini API quota reached.",
        status_code=429,
    )

    pipeline = LegalRAGPipeline(retriever=mock_retriever, llm_provider=mock_llm)
    response = pipeline.query("What is theft under BNS?")

    assert response.status == "rate_limited"
    assert len(response.sources) == 2, f"Expected 2 preserved sources, got {len(response.sources)}"
    assert response.sources[0].document_name == "Bharatiya Nyaya Sanhita, 2023"
    assert "## Answer" in response.answer
    assert "## Legal Sources" in response.answer
    assert "## Note" in response.answer
    assert "Bharatiya Nyaya Sanhita, 2023 (Page 81, 82" in response.answer
    print("  [PASS] 7. Pipeline fallback preserves 100% of retrieved statutory sources with disclaimer")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("NYAYASETU: GOOGLE GEMINI PROVIDER VERIFICATION SUITE")
    print("=" * 80 + "\n")

    test_gemini_provider_initialization()
    test_factory_resolution()
    test_error_classification()
    test_retry_behavior()
    test_non_retryable_quota_behavior()
    test_successful_gemini_generation()
    test_pipeline_fallback_preserves_sources()

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED (7/7) - 100% SUCCESS")
    print("=" * 80 + "\n")
