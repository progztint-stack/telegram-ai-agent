"""Groq provider adapter."""

from __future__ import annotations

from .base import (
    AIProvider,
    AIResponse,
    InvalidRequestError,
    ProviderConfigurationError,
    RateLimitError,
    TransientProviderError,
)


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ProviderConfigurationError("Groq API key is not configured")
        try:
            from groq import AsyncGroq

            self._client = AsyncGroq(
                api_key=self.api_key,
                timeout=self.timeout_seconds,
                max_retries=0,
            )
            return self._client
        except ImportError as exc:
            raise ProviderConfigurationError("Groq SDK is unavailable") from exc

    async def generate(self, prompt: str, context: list[dict[str, str]] | None = None) -> AIResponse:
        client = self._ensure_client()
        messages = list(context or [])
        messages.append({"role": "user", "content": prompt})
        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            text = completion.choices[0].message.content or ""
            if not text:
                raise TransientProviderError("Groq returned an empty response")
            return AIResponse(
                text=text,
                provider=self.name,
                model=self.model,
                metadata={"context_messages": len(context or [])},
            )
        except Exception as exc:
            if isinstance(exc, (InvalidRequestError, ProviderConfigurationError, RateLimitError, TransientProviderError)):
                raise
            raise _classify_provider_error(exc) from exc

    async def health_check(self) -> bool:
        return bool(self.api_key.strip())

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


def _classify_provider_error(exc: Exception):
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    message = str(exc).lower()
    if status_code == 429 or any(marker in message for marker in ("rate limit", "too many requests")):
        return RateLimitError("Groq rate limit or quota was reached")
    if status_code in {401, 403, 404}:
        return ProviderConfigurationError("Groq credentials or model configuration were rejected")
    if status_code == 400 or "invalid request" in message:
        return InvalidRequestError("Groq rejected the request")
    return TransientProviderError("Groq request failed")

