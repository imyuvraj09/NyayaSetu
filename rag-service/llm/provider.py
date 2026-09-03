"""
Concrete LLM providers and factory for NyayaSetu Legal Assistant.

Configured with OpenAI as the primary production provider using the official OpenAI SDK,
while also preserving Google Gemini and mock providers for offline testing.
"""

import os
import re
import time
from typing import Optional

import httpx

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OpenAI = None
    OPENAI_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GEMINI_AVAILABLE = False

from llm.base import (
    BaseLLMProvider,
    LLMError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMResponse,
    LLMServiceUnavailableError,
    LLMTimeoutError,
)
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """Production OpenAI LLM provider using the official OpenAI Python SDK with resilient retry handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._api_key = (
            api_key
            or settings.effective_openai_api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("LLM_API_KEY")
        )
        self._model = model or settings.LLM_MODEL or "gpt-5.6-terra"
        self._base_url = base_url or settings.LLM_BASE_URL or None
        self._timeout = timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        """Verify API key is present and non-empty."""
        # For local models (Ollama/vLLM) via custom base_url, key might be optional
        if self._base_url and ("localhost" in self._base_url or "127.0.0.1" in self._base_url):
            return True
        return bool(self._api_key and self._api_key.strip())

    def _classify_openai_error(self, exc: Exception) -> LLMError:
        """Classify OpenAI and HTTP exceptions into typed LLMError subclasses with retryability."""
        err_str = str(exc).lower()

        # Check for HTTP 429 or SDK RateLimitError
        is_rate_limit = (
            (OPENAI_AVAILABLE and isinstance(exc, openai.RateLimitError))
            or getattr(exc, "status_code", None) == 429
            or getattr(getattr(exc, "response", None), "status_code", None) == 429
        )

        if is_rate_limit:
            # Distinguish between hard quota exhaustion and transient rate limiting
            code = getattr(exc, "code", None)
            if (
                code == "insufficient_quota"
                or "quota" in err_str
                or "billing" in err_str
                or "exceeded your current quota" in err_str
            ):
                return LLMQuotaExceededError(
                    message="OpenAI API quota exceeded. Please check your account plan and billing limits.",
                    status_code=429,
                )
            return LLMRateLimitError(
                message="OpenAI API rate limit reached. Please try again later.",
                status_code=429,
            )

        # Timeout errors
        if (
            (OPENAI_AVAILABLE and isinstance(exc, openai.APITimeoutError))
            or isinstance(exc, httpx.TimeoutException)
            or getattr(exc, "status_code", None) in (408, 504)
        ):
            return LLMTimeoutError(
                message=f"OpenAI API request timed out after {self._timeout} seconds.",
                status_code=504,
            )

        # Connection / Network errors
        if (
            (OPENAI_AVAILABLE and isinstance(exc, openai.APIConnectionError))
            or isinstance(exc, (httpx.ConnectError, httpx.NetworkError))
        ):
            return LLMServiceUnavailableError(
                message="Network connection error communicating with OpenAI API.",
                status_code=503,
            )

        # Server-side 5xx errors
        status_code = getattr(exc, "status_code", None) or getattr(
            getattr(exc, "response", None), "status_code", None
        )
        if (
            (OPENAI_AVAILABLE and hasattr(openai, "InternalServerError") and isinstance(exc, openai.InternalServerError))
            or (status_code and 500 <= status_code <= 599)
        ):
            return LLMServiceUnavailableError(
                message=f"OpenAI API temporary server error (HTTP {status_code or 503}).",
                status_code=status_code or 503,
            )

        # Authentication errors (non-retryable)
        if (OPENAI_AVAILABLE and isinstance(exc, openai.AuthenticationError)) or status_code == 401:
            return LLMError(
                message="OpenAI authentication failed. Please verify your OPENAI_API_KEY.",
                category="AUTH_ERROR",
                status_code=401,
                retryable=False,
            )

        # Generic API Error
        return LLMError(
            message=f"OpenAI API error: {getattr(exc, 'message', str(exc))}",
            category="LLM_ERROR",
            status_code=status_code or 500,
            retryable=False,
        )

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate legal response via OpenAI API with automatic retry and exponential backoff."""
        if not self.is_configured():
            raise RuntimeError(
                "OpenAI provider is not configured. "
                "Please set OPENAI_API_KEY in your environment or .env file."
            )

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        logger.info(
            "Sending request to OpenAI API (model: %s, temp: %.2f, max_tokens: %d, timeout: %.1fs)",
            self._model,
            temp,
            max_t,
            self._timeout,
        )

        max_attempts = 3
        backoff_delays = [1.5, 3.0]

        for attempt in range(1, max_attempts + 1):
            try:
                if not OPENAI_AVAILABLE:
                    return self._generate_via_httpx(messages, temp, max_t)

                client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                    timeout=self._timeout,
                )

                # Try standard completion request
                try:
                    response = client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=temp,
                        max_completion_tokens=max_t,
                    )
                except TypeError:
                    # Older SDK version fallback
                    response = client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=temp,
                        max_tokens=max_t,
                    )

                choices = response.choices
                if not choices:
                    raise RuntimeError("OpenAI API returned an empty choices list.")

                content = choices[0].message.content or ""
                usage = response.usage

                prompt_tokens = usage.prompt_tokens if usage else None
                completion_tokens = usage.completion_tokens if usage else None

                logger.info(
                    "OpenAI API response received successfully on attempt %d (length: %d chars)",
                    attempt,
                    len(content),
                )

                return LLMResponse(
                    content=content.strip(),
                    model=response.model or self._model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    metadata={
                        "provider": "openai",
                        "finish_reason": choices[0].finish_reason,
                        "attempts": attempt,
                    },
                )

            except Exception as raw_exc:
                classified_err = self._classify_openai_error(raw_exc)

                # Safe server-side logging without leaking secrets or keys
                logger.warning(
                    "OpenAI generation attempt %d/%d failed [category=%s, status=%s]: %s",
                    attempt,
                    max_attempts,
                    classified_err.category,
                    classified_err.status_code,
                    classified_err.message,
                )

                # If non-retryable (e.g. quota exceeded or auth error) or final attempt reached
                if not classified_err.retryable or attempt >= max_attempts:
                    if attempt >= max_attempts and classified_err.retryable:
                        logger.error(
                            "OpenAI generation failed after %d attempts [category=%s, status=%s]",
                            max_attempts,
                            classified_err.category,
                            classified_err.status_code,
                        )
                    raise classified_err from raw_exc

                delay = backoff_delays[attempt - 1] if attempt - 1 < len(backoff_delays) else 3.0
                logger.info(
                    "Retrying OpenAI API request in %.1fs (attempt %d of %d)...",
                    delay,
                    attempt + 1,
                    max_attempts,
                )
                time.sleep(delay)

    def _generate_via_httpx(self, messages: list, temperature: float, max_tokens: int) -> LLMResponse:
        """Direct HTTP fallback using httpx."""
        base_url = (self._base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI API returned empty choices.")
        content = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return LLMResponse(
            content=content.strip(),
            model=self._model,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            metadata={"provider": "openai", "finish_reason": choices[0].get("finish_reason")},
        )


# Alias for backward compatibility
OpenAICompatibleProvider = OpenAIProvider


class GoogleGeminiProvider(BaseLLMProvider):
    """Production Google Gemini LLM provider using Google's official google-genai Python SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        if api_key is not None:
            self._api_key = api_key.strip()
        else:
            self._api_key = (
                settings.effective_gemini_api_key
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
                or os.environ.get("LLM_API_KEY")
                or ""
            ).strip()
        self._model = model or settings.LLM_MODEL or "gemini-2.5-flash"
        if self._model.startswith("models/"):
            self._model = self._model.replace("models/", "")
        self._timeout = timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        """Verify API key is present and non-empty."""
        return bool(self._api_key and self._api_key.strip())

    def _classify_gemini_error(self, exc: Exception) -> LLMError:
        """Classify Gemini API and HTTP exceptions into typed LLMError subclasses with retryability."""
        err_str = str(exc).lower()

        # Check for HTTP 429 or ResourceExhausted
        status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        is_429 = (
            status_code == 429
            or "429" in err_str
            or "resource_exhausted" in err_str
            or "resourceexhausted" in err_str
            or "quota" in err_str
            or "rate limit" in err_str
        )

        if is_429:
            if "quota" in err_str or "exhausted" in err_str:
                return LLMQuotaExceededError(
                    message="Google Gemini API quota or request limit reached. Please check your Google AI project quota.",
                    status_code=429,
                )
            return LLMRateLimitError(
                message="Google Gemini API rate limit reached. Please try again later.",
                status_code=429,
            )

        # Timeout errors
        if (
            isinstance(exc, httpx.TimeoutException)
            or status_code in (408, 504)
            or "timeout" in err_str
            or "timed out" in err_str
        ):
            return LLMTimeoutError(
                message=f"Google Gemini API request timed out after {self._timeout} seconds.",
                status_code=504,
            )

        # Connection / Network errors
        if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)) or "connection" in err_str:
            return LLMServiceUnavailableError(
                message="Network connection error communicating with Google Gemini API.",
                status_code=503,
            )

        # Server-side 5xx errors
        if (status_code and 500 <= status_code <= 599) or "internal" in err_str or "unavailable" in err_str:
            return LLMServiceUnavailableError(
                message=f"Google Gemini API temporary server error (HTTP {status_code or 503}).",
                status_code=status_code or 503,
            )

        # Authentication errors
        if status_code in (400, 401, 403) and (
            "api_key_invalid" in err_str or "unauthenticated" in err_str or "permission" in err_str
        ):
            return LLMError(
                message="Google Gemini authentication failed. Please verify your GEMINI_API_KEY.",
                category="AUTH_ERROR",
                status_code=401,
                retryable=False,
            )

        return LLMError(
            message=f"Google Gemini API error: {str(exc)}",
            category="LLM_ERROR",
            status_code=status_code or 500,
            retryable=False,
        )

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate legal response via Google Gemini API with automatic retry and exponential backoff."""
        if not self.is_configured():
            raise RuntimeError(
                "Google Gemini provider is not configured. "
                "Please set GEMINI_API_KEY in your environment or .env file."
            )

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

        logger.info(
            "Sending request to Google Gemini API (model: %s, temp: %.2f, max_tokens: %d, timeout: %.1fs)",
            self._model,
            temp,
            max_t,
            self._timeout,
        )

        max_attempts = 3
        backoff_delays = [2.0, 4.0]
        candidate_models = [self._model] + [m for m in ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.8-flash"] if m != self._model]

        for model_to_use in candidate_models:
            for attempt in range(1, max_attempts + 1):
                try:
                    if GEMINI_AVAILABLE:
                        client = genai.Client(api_key=self._api_key)
                        effective_max_tokens = max(max_t, 3500)
                        config = types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=temp,
                            max_output_tokens=effective_max_tokens,
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(thinking_budget=256),
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        )
                        response = client.models.generate_content(
                            model=model_to_use,
                            contents=prompt,
                            config=config,
                        )

                        content = response.text or ""
                        prompt_tokens = None
                        completion_tokens = None
                        finish_reason = None

                        if hasattr(response, "usage_metadata") and response.usage_metadata:
                            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

                        if hasattr(response, "candidates") and response.candidates:
                            finish_reason = getattr(response.candidates[0], "finish_reason", None)

                        logger.info(
                            "Google Gemini API response received successfully from %s on attempt %d (length: %d chars)",
                            model_to_use,
                            attempt,
                            len(content),
                        )

                        return LLMResponse(
                            content=content.strip(),
                            model=model_to_use,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            metadata={
                                "provider": "gemini",
                                "finish_reason": str(finish_reason) if finish_reason else None,
                                "attempts": attempt,
                            },
                        )
                    else:
                        return self._generate_via_rest(prompt, system_instruction, temp, max_t)

                except Exception as raw_exc:
                    classified_err = self._classify_gemini_error(raw_exc)

                    logger.warning(
                        "Google Gemini (%s) attempt %d/%d failed [category=%s, status=%s]: %s",
                        model_to_use,
                        attempt,
                        max_attempts,
                        classified_err.category,
                        classified_err.status_code,
                        classified_err.message,
                    )

                    # If quota exhausted, immediately break attempt loop and try next candidate model
                    if classified_err.category in ("QUOTA_EXCEEDED", "RATE_LIMIT_EXCEEDED") and model_to_use != candidate_models[-1]:
                        logger.info("Switching to alternative Gemini model due to rate limit / quota...")
                        break

                    if not classified_err.retryable or attempt >= max_attempts:
                        if model_to_use == candidate_models[-1]:
                            logger.error(
                                "Google Gemini generation failed across all models [category=%s, status=%s]",
                                classified_err.category,
                                classified_err.status_code,
                            )
                            raise classified_err from raw_exc
                        break

                    delay = backoff_delays[attempt - 1] if attempt - 1 < len(backoff_delays) else 3.0
                    time.sleep(delay)

    def _generate_via_rest(
        self,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Direct REST fallback for Gemini API via httpx."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload)
        if resp.status_code != 200:
            resp.raise_for_status()

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Google Gemini API returned an empty candidate list.")

        content_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        usage = data.get("usageMetadata", {})

        return LLMResponse(
            content=content_part.strip(),
            model=self._model,
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
            metadata={"provider": "gemini", "finish_reason": candidates[0].get("finishReason")},
        )


# Aliases for convenience
GeminiProvider = GoogleGeminiProvider


class MockLLMProvider(BaseLLMProvider):
    """Deterministic offline provider for regression testing and offline demonstration."""

    def __init__(self, model_name: str = "mock-legal-assistant") -> None:
        self._model = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        found_sources = re.findall(r"\[SOURCE\s+(\d+)\]", prompt, re.IGNORECASE)
        labels = [f"[Source {num}]" for num in sorted(set(found_sources), key=int)] if found_sources else ["[Source 1]"]

        primary_cite = labels[0]
        secondary_cite = labels[1] if len(labels) > 1 else labels[0]

        mock_answer = (
            f"## Answer\n\n"
            f"Under Indian law, the statutory provisions directly governing this inquiry specify established legal "
            f"principles and statutory remedies {primary_cite}. Furthermore, specific procedures and rights "
            f"are outlined in {secondary_cite}.\n\n"
            f"## Legal Basis\n\n"
            f"According to the official statutory provisions in {primary_cite}, the enactment defines applicable "
            f"obligations, liability boundaries, and procedures. Additionally, {secondary_cite} provides the "
            f"statutory framework for legal redress and institutional adjudication.\n\n"
            f"## Sources\n\n"
            f"{primary_cite}\n"
            f"{secondary_cite}\n\n"
            f"## Important Note\n\n"
            f"This summary is provided for educational and informational purposes only based on retrieved "
            f"statutory records and does not constitute formal legal representation or legal advice. "
            f"Consult a licensed advocate for case-specific counsel."
        )

        return LLMResponse(
            content=mock_answer,
            model=self._model,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(mock_answer.split()),
            metadata={"provider": "mock", "mode": "offline_testing"},
        )


def get_llm_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """Factory helper to obtain the configured LLM provider instance.

    Defaults to GoogleGeminiProvider as primary production provider.
    """
    p_type = (provider_type or settings.LLM_PROVIDER or "gemini").lower().strip()

    if p_type in ("gemini", "google"):
        return GoogleGeminiProvider()
    elif p_type == "openai":
        return OpenAIProvider()
    elif p_type == "mock":
        return MockLLMProvider()
    elif p_type in ("custom", "groq"):
        return OpenAIProvider()
    else:
        logger.warning(
            "Unrecognized LLM_PROVIDER '%s'. Defaulting to GoogleGeminiProvider.", p_type
        )
        return GoogleGeminiProvider()
