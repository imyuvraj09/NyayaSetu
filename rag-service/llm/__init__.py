"""LLM Provider abstraction package for NyayaSetu RAG Service."""

from llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMEmptyResponseError,
    LLMError,
    LLMInvalidModelError,
    LLMMalformedResponseError,
    LLMNetworkError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResponse,
    LLMServiceUnavailableError,
    LLMTimeoutError,
)
from llm.provider import (
    GeminiProvider,
    GoogleGeminiProvider,
    MockLLMProvider,
    OpenAICompatibleProvider,
    OpenAIProvider,
    get_llm_provider,
)

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "LLMError",
    "LLMRateLimitError",
    "LLMQuotaExceededError",
    "LLMAuthenticationError",
    "LLMInvalidModelError",
    "LLMTimeoutError",
    "LLMNetworkError",
    "LLMMalformedResponseError",
    "LLMEmptyResponseError",
    "LLMProviderError",
    "LLMServiceUnavailableError",
    "OpenAIProvider",
    "OpenAICompatibleProvider",
    "GoogleGeminiProvider",
    "GeminiProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
