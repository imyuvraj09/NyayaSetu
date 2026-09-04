"""
Base LLM provider abstraction for NyayaSetu Legal Knowledge Assistant.

Defines the contract for LLM integrations, enabling seamless swapping between
Google Gemini, OpenAI, self-hosted vLLM/Ollama, or mock testing providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class LLMError(RuntimeError):
    """Base exception for LLM errors with category classification and retryability flag."""

    def __init__(
        self,
        message: str,
        category: str = "UNKNOWN_ERROR",
        status_code: Optional[int] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code
        self.retryable = retryable


class LLMRateLimitError(LLMError):
    """HTTP 429 rate limit reached (requests or tokens per minute). Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM API rate limit reached. Please try again shortly.",
        status_code: Optional[int] = 429,
    ) -> None:
        super().__init__(
            message=message,
            category="RATE_LIMIT",
            status_code=status_code,
            retryable=True,
        )


class LLMQuotaExceededError(LLMError):
    """API quota or billing limit exceeded. Permanent until funded / quota refreshed."""

    def __init__(
        self,
        message: str = "LLM API quota exceeded. Please check your account plan or billing limits.",
        status_code: Optional[int] = 429,
    ) -> None:
        super().__init__(
            message=message,
            category="QUOTA_EXCEEDED",
            status_code=status_code,
            retryable=False,
        )


class LLMAuthenticationError(LLMError):
    """API key invalid or permission denied (HTTP 401/403). Non-retryable."""

    def __init__(
        self,
        message: str = "LLM authentication failed. Please verify your API key.",
        status_code: Optional[int] = 401,
    ) -> None:
        super().__init__(
            message=message,
            category="AUTHENTICATION_ERROR",
            status_code=status_code,
            retryable=False,
        )


class LLMInvalidModelError(LLMError):
    """Requested model not found or unsupported by provider (HTTP 404). Non-retryable."""

    def __init__(
        self,
        message: str = "Configured LLM model is invalid or unavailable.",
        status_code: Optional[int] = 404,
    ) -> None:
        super().__init__(
            message=message,
            category="INVALID_MODEL",
            status_code=status_code,
            retryable=False,
        )


class LLMTimeoutError(LLMError):
    """Request timeout communicating with LLM API. Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM inference request timed out.",
        status_code: Optional[int] = 504,
    ) -> None:
        super().__init__(
            message=message,
            category="TIMEOUT",
            status_code=status_code,
            retryable=True,
        )


class LLMNetworkError(LLMError):
    """Network connection or DNS resolution failure. Temporary and retryable."""

    def __init__(
        self,
        message: str = "Network connection error communicating with LLM provider.",
        status_code: Optional[int] = 503,
    ) -> None:
        super().__init__(
            message=message,
            category="NETWORK_ERROR",
            status_code=status_code,
            retryable=True,
        )


class LLMMalformedResponseError(LLMError):
    """Provider returned response that cannot be parsed as valid content/JSON. Non-retryable."""

    def __init__(
        self,
        message: str = "LLM provider returned a malformed response.",
        status_code: Optional[int] = 502,
    ) -> None:
        super().__init__(
            message=message,
            category="MALFORMED_RESPONSE",
            status_code=status_code,
            retryable=False,
        )


class LLMEmptyResponseError(LLMError):
    """Provider returned empty completion content. Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM provider returned an empty response.",
        status_code: Optional[int] = 502,
    ) -> None:
        super().__init__(
            message=message,
            category="EMPTY_RESPONSE",
            status_code=status_code,
            retryable=True,
        )


class LLMProviderError(LLMError):
    """Provider server-side 5xx error or internal failure. Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM provider encountered an internal service error.",
        status_code: Optional[int] = 503,
    ) -> None:
        super().__init__(
            message=message,
            category="PROVIDER_ERROR",
            status_code=status_code,
            retryable=True,
        )


# Backward-compatible alias
LLMServiceUnavailableError = LLMProviderError


@dataclass
class LLMResponse:
    """Standardized response from an LLM provider."""

    content: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract interface for LLM inference providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'google', 'openai', 'custom')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier being used."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether valid credentials and configuration exist for this provider."""
        pass

    def check_health(self) -> Dict[str, Any]:
        """Perform a lightweight diagnostic check without sending generation requests.
        Never exposes API keys.
        """
        configured = self.is_configured()
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "configured": configured,
            "available": configured,
        }

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate text completion from the language model."""
        pass
