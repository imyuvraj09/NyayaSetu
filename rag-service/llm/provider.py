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
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _sanitize_log(text: str) -> str:
    """Scrub sensitive API tokens or keys from log messages."""
    if not text:
        return ""
    # Redact common Gemini / OpenAI API key patterns
    text = re.sub(r"AQ\.[A-Za-z0-9_\-]{20,}", "[REDACTED_GEMINI_KEY]", text)
    text = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_GOOGLE_KEY]", text)
    text = re.sub(r"sk-[a-zA-Z0-9_\-]{20,}", "[REDACTED_OPENAI_KEY]", text)
    text = re.sub(r"key=[A-Za-z0-9_\-]+", "key=[REDACTED]", text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9_\.\-]+", "Bearer [REDACTED]", text)
    return text


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
            return LLMAuthenticationError(
                message="OpenAI authentication failed. Please verify your OPENAI_API_KEY.",
                status_code=401,
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
    """Production Google Gemini LLM provider using Google's official google-genai Python SDK.
    Enforces a single authoritative model configuration with controlled single retry for transient faults.
    """

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
        self._model = model or settings.LLM_MODEL or "gemini-3.6-flash"
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

    def check_health(self) -> dict:
        """Perform a lightweight diagnostic check without making billable generation calls.
        Never exposes API keys.
        """
        configured = self.is_configured()
        available = False
        if configured and GEMINI_AVAILABLE:
            try:
                # Lightweight initialization check
                _ = genai.Client(api_key=self._api_key)
                available = True
            except Exception as exc:
                logger.warning("Gemini diagnostic health check failed: %s", _sanitize_log(str(exc)))
                available = False

        return {
            "provider": "google_gemini",
            "model": self._model,
            "configured": configured,
            "available": available,
        }

    def _classify_gemini_error(self, exc: Exception) -> LLMError:
        """Classify Gemini API and HTTP exceptions into typed LLMError subclasses with safe logging."""
        err_str = _sanitize_log(str(exc)).lower()
        status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)

        # 1. Model not found / invalid model (HTTP 404)
        if (
            status_code == 404
            or "not found" in err_str
            or "is not found for api version" in err_str
            or "invalid model" in err_str
            or "models/" in err_str and "not found" in err_str
        ):
            return LLMInvalidModelError(
                message=f"Configured Gemini model '{self._model}' is invalid or not found on Google AI.",
                status_code=404,
            )

        # 2. Authentication / Permission errors (HTTP 401/403)
        if (
            status_code in (400, 401, 403)
            or any(
                k in err_str
                for k in (
                    "api_key_invalid",
                    "unauthenticated",
                    "permission_denied",
                    "permission",
                    "invalid api key",
                    "api key not valid",
                    "api key is invalid",
                )
            )
        ):
            return LLMAuthenticationError(
                message="Google Gemini authentication failed. Please verify your GEMINI_API_KEY.",
                status_code=status_code or 401,
            )

        # 3. Rate Limit vs Quota Exceeded (HTTP 429 or ResourceExhausted)
        is_429 = (
            status_code == 429
            or "429" in err_str
            or "resource_exhausted" in err_str
            or "resourceexhausted" in err_str
            or "quota" in err_str
            or "rate limit" in err_str
        )

        if is_429:
            if "quota" in err_str or "exhausted" in err_str or "billing" in err_str or "plan" in err_str:
                return LLMQuotaExceededError(
                    message="Google Gemini API quota or request limit reached. Please check your Google AI project quota.",
                    status_code=429,
                )
            return LLMRateLimitError(
                message="Google Gemini API rate limit reached. Please try again shortly.",
                status_code=429,
            )

        # 4. Timeout errors (HTTP 408 / 504 / client timeout)
        if (
            isinstance(exc, httpx.TimeoutException)
            or status_code in (408, 504)
            or "timeout" in err_str
            or "timed out" in err_str
            or "deadline exceeded" in err_str
        ):
            return LLMTimeoutError(
                message=f"Google Gemini API request timed out after {self._timeout} seconds.",
                status_code=504,
            )

        # 5. Network / Connection errors
        if (
            isinstance(exc, (httpx.ConnectError, httpx.NetworkError))
            or "connection refused" in err_str
            or "failed to connect" in err_str
            or "dns" in err_str
        ):
            return LLMNetworkError(
                message="Network connection error communicating with Google Gemini API.",
                status_code=503,
            )

        # 6. Server-side 5xx errors
        if (
            (status_code and 500 <= status_code <= 599)
            or "internal" in err_str
            or "unavailable" in err_str
            or "service unavailable" in err_str
        ):
            return LLMProviderError(
                message=f"Google Gemini API temporary server error (HTTP {status_code or 503}).",
                status_code=status_code or 503,
            )

        # 7. Malformed / Empty responses
        if "empty" in err_str and "response" in err_str:
            return LLMEmptyResponseError(
                message="Google Gemini API returned an empty response.",
                status_code=502,
            )

        # Fallback to generic classified LLMError
        return LLMError(
            message=f"Google Gemini API error: {_sanitize_log(str(exc))}",
            category="UNKNOWN_ERROR",
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
        """Generate legal response via Google Gemini API using authoritative model with controlled single retry."""
        if not self.is_configured():
            raise RuntimeError(
                "Google Gemini provider is not configured. "
                "Please set GEMINI_API_KEY in your environment or .env file."
            )

        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

        logger.info(
            "Sending request to Google Gemini API (authoritative model: %s, temp: %.2f, max_tokens: %d, timeout: %.1fs)",
            self._model,
            temp,
            max_t,
            self._timeout,
        )

        # Controlled retry: exactly 1 retry (max 2 total attempts) for transient failures only
        max_attempts = 2

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
                        model=self._model,
                        contents=prompt,
                        config=config,
                    )

                    content = response.text or ""
                    if not content or not content.strip():
                        raise LLMEmptyResponseError("Google Gemini API returned an empty text completion.")

                    prompt_tokens = None
                    completion_tokens = None
                    finish_reason = None

                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                        completion_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

                    if hasattr(response, "candidates") and response.candidates:
                        finish_reason = getattr(response.candidates[0], "finish_reason", None)

                    logger.info(
                        "Google Gemini API response received successfully on attempt %d (model: %s, length: %d chars)",
                        attempt,
                        self._model,
                        len(content),
                    )

                    return LLMResponse(
                        content=content.strip(),
                        model=self._model,
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
                if isinstance(raw_exc, LLMError):
                    classified_err = raw_exc
                else:
                    classified_err = self._classify_gemini_error(raw_exc)

                safe_msg = _sanitize_log(classified_err.message)
                logger.warning(
                    "Google Gemini generation attempt %d/%d failed [category=%s, status=%s]: %s",
                    attempt,
                    max_attempts,
                    classified_err.category,
                    classified_err.status_code,
                    safe_msg,
                )

                # Non-retryable errors (auth, quota, invalid model, etc.) fail immediately without retrying
                if not classified_err.retryable or attempt >= max_attempts:
                    logger.error(
                        "Google Gemini request failed [category=%s, status=%s, retryable=%s, attempts=%d]",
                        classified_err.category,
                        classified_err.status_code,
                        classified_err.retryable,
                        attempt,
                    )
                    raise classified_err from raw_exc

                # Transient retryable error (1 retry allowed)
                logger.info(
                    "Retrying Gemini generation in 1.0s (attempt %d of %d) for transient %s...",
                    attempt + 1,
                    max_attempts,
                    classified_err.category,
                )
                time.sleep(1.0)

    def _generate_via_rest(
        self,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Direct REST fallback for Gemini API via httpx using authoritative model."""
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
            raise LLMEmptyResponseError("Google Gemini API returned an empty candidate list.")

        content_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not content_part or not content_part.strip():
            raise LLMEmptyResponseError("Google Gemini API returned empty content.")

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
