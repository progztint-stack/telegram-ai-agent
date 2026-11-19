"""Google Gemini provider adapter."""

from __future__ import annotations

from .base import (
    AIProvider,
    AIResponse,
    InvalidRequestError,
    ProviderConfigurationError,
    RateLimitError,
    TransientProviderError,
)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self._client = None

    def _ensure_client(self) -> None:
        if not self.api_key:
            raise ProviderConfigurationError("Gemini API key is not configured")
        try:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        except ImportError as exc:
            raise ProviderConfigurationError("Gemini SDK is unavailable") from exc

    async def generate(self, prompt: str, context: list[dict[str, str]] | None = None) -> AIResponse:
        if self._client is None:
            self._ensure_client()
        history = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}" for item in (context or [])
        )
        full_prompt = f"{history}\n\nuser: {prompt}" if history else prompt
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            if not response.text:
                raise TransientProviderError("Gemini returned an empty response")
            return AIResponse(
                text=response.text,
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
            await self._client.aio.aclose()
            self._client = None


def _classify_provider_error(exc: Exception):
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    message = str(exc).lower()
    if status_code == 429 or any(marker in message for marker in ("quota", "rate limit", "resource_exhausted")):
        return RateLimitError("Gemini rate limit or quota was reached")
    if status_code in {401, 403, 404}:
        return ProviderConfigurationError("Gemini credentials or model configuration were rejected")
    if status_code == 400 or "invalid argument" in message:
        return InvalidRequestError("Gemini rejected the request")
    return TransientProviderError("Gemini request failed")

