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
        category: str = "LLM_ERROR",
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
        message: str = "OpenAI API rate limit reached. Please try again later.",
        status_code: Optional[int] = 429,
    ) -> None:
        super().__init__(
            message=message,
            category="RATE_LIMIT_EXCEEDED",
            status_code=status_code,
            retryable=True,
        )


class LLMQuotaExceededError(LLMError):
    """API quota or billing limit exceeded (insufficient_quota). Permanent until funded."""

    def __init__(
        self,
        message: str = "OpenAI API quota exceeded. Please check your account plan or billing details.",
        status_code: Optional[int] = 429,
    ) -> None:
        super().__init__(
            message=message,
            category="QUOTA_EXCEEDED",
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
            category="LLM_TIMEOUT",
            status_code=status_code,
            retryable=True,
        )


class LLMServiceUnavailableError(LLMError):
    """LLM service temporarily unavailable or connection failure. Temporary and retryable."""

    def __init__(
        self,
        message: str = "LLM inference service is temporarily unavailable.",
        status_code: Optional[int] = 503,
    ) -> None:
        super().__init__(
            message=message,
            category="LLM_SERVICE_UNAVAILABLE",
            status_code=status_code,
            retryable=True,
        )


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

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate text completion from the language model.

        Args:
            prompt: User prompt content containing query and grounded context.
            system_instruction: Guiding instructions and legal safety constraints.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in generated completion.

        Returns:
            LLMResponse object containing the generated text and execution metadata.

        Raises:
            RuntimeError: If provider is unconfigured or returns an error.
        """
        pass
