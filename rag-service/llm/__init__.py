"""LLM Provider abstraction package for NyayaSetu RAG Service."""

from llm.base import (
    BaseLLMProvider,
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
    "LLMTimeoutError",
    "LLMServiceUnavailableError",
    "OpenAIProvider",
    "OpenAICompatibleProvider",
    "GoogleGeminiProvider",
    "GeminiProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
