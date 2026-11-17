"""LLM provider abstraction and implementations.

Supported providers:
- NoneProvider: offline/no-op provider, raises AIUnavailable.
- OllamaProvider: local Ollama HTTP API.
- GeminiProvider: Google Gemini REST API (x-goog-api-key header).
- OpenAIProvider: OpenAI REST API (Bearer token).

Per AGENTS.md Hard Rules:
- Rule 6: Never print, log or commit secrets.
- Rule 8: Every network or LLM call has an explicit timeout.
- Rule 10: No time.sleep: use the injectable Clock.
"""

from typing import Any, Protocol

import httpx

from t2t.clock import Clock, SystemClock
from t2t.errors import AIUnavailable


class LLMProvider(Protocol):
    """Protocol for LLM chat completion providers."""

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> str:
        """Execute completion call against the provider."""
        ...


def _execute_with_retries(
    request_func: Any,
    provider_name: str,
    clock: Clock,
    max_retries: int = 2,
    base_backoff: float = 1.0,
    secret_to_redact: str = "",
) -> httpx.Response:
    """Execute HTTP call with bounded retries and exponential backoff on 429/5xx."""
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            resp: httpx.Response = request_func()
            if resp.status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries:
                    backoff = base_backoff * (2**attempt)
                    clock.sleep(backoff)
                    continue
                resp.raise_for_status()

            resp.raise_for_status()
            return resp

        except httpx.HTTPStatusError as err:
            last_err = err
            if err.response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                backoff = base_backoff * (2**attempt)
                clock.sleep(backoff)
                continue
            err_msg = f"{provider_name} HTTP {err.response.status_code} error: {err.response.text}"
            if secret_to_redact:
                err_msg = err_msg.replace(secret_to_redact, "[REDACTED]")
            raise AIUnavailable(err_msg) from None

        except (httpx.TimeoutException, httpx.NetworkError) as err:
            last_err = err
            if attempt < max_retries:
                backoff = base_backoff * (2**attempt)
                clock.sleep(backoff)
                continue
            err_msg = f"{provider_name} request failed: {type(err).__name__}"
            if secret_to_redact:
                err_msg = err_msg.replace(secret_to_redact, "[REDACTED]")
            raise AIUnavailable(err_msg) from None

        except Exception as err:
            err_msg = f"{provider_name} call failed: {err}"
            if secret_to_redact:
                err_msg = err_msg.replace(secret_to_redact, "[REDACTED]")
            raise AIUnavailable(err_msg) from None

    final_msg = f"{provider_name} failed after {max_retries} retries: {last_err}"
    if secret_to_redact:
        final_msg = final_msg.replace(secret_to_redact, "[REDACTED]")
    raise AIUnavailable(final_msg)


class NoneProvider:
    """Offline provider that always raises AIUnavailable, triggering fallbacks."""

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> str:
        raise AIUnavailable("No AI provider configured. Set T2T_AI_PROVIDER to an active provider.")


class OllamaProvider:
    """Local Ollama HTTP completion provider."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "",
        clock: Clock | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.clock: Clock = clock if clock is not None else SystemClock()
        self.default_timeout = timeout

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> str:
        if not self.model:
            raise AIUnavailable("Ollama model name not configured. Set OLLAMA_MODEL.")

        effective_timeout = timeout if timeout is not None else self.default_timeout
        endpoint = f"{self.host}/api/chat"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        if json_schema is not None:
            payload["format"] = "json"

        with httpx.Client(timeout=effective_timeout) as client:
            resp = _execute_with_retries(
                lambda: client.post(endpoint, json=payload),
                provider_name="Ollama",
                clock=self.clock,
            )

        data = resp.json()
        return str(data.get("message", {}).get("content", ""))


class GeminiProvider:
    """Google Gemini REST API completion provider.

    Security Rule: Key MUST be passed in x-goog-api-key header, NEVER in URL.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        clock: Clock | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.clock: Clock = clock if clock is not None else SystemClock()
        self.default_timeout = timeout

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> str:
        if not self.api_key or not self.model:
            raise AIUnavailable("Gemini API key or model not configured.")

        effective_timeout = timeout if timeout is not None else self.default_timeout
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        }
        if json_schema is not None:
            payload["generationConfig"] = {
                "response_mime_type": "application/json",
                "response_schema": json_schema,
            }

        with httpx.Client(timeout=effective_timeout) as client:
            resp = _execute_with_retries(
                lambda: client.post(endpoint, headers=headers, json=payload),
                provider_name="Gemini",
                clock=self.clock,
                secret_to_redact=self.api_key,
            )

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""

        return str(parts[0].get("text", ""))


class OpenAIProvider:
    """OpenAI REST API completion provider (Bearer token in header)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        clock: Clock | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.clock: Clock = clock if clock is not None else SystemClock()
        self.default_timeout = timeout

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> str:
        if not self.api_key or not self.model:
            raise AIUnavailable("OpenAI API key or model not configured.")

        effective_timeout = timeout if timeout is not None else self.default_timeout
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=effective_timeout) as client:
            resp = _execute_with_retries(
                lambda: client.post(endpoint, headers=headers, json=payload),
                provider_name="OpenAI",
                clock=self.clock,
                secret_to_redact=self.api_key,
            )

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""

        return str(choices[0].get("message", {}).get("content", ""))
