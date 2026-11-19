"""Groq provider adapter."""

from __future__ import annotations

from .base import AIProvider, AIResponse, InvalidRequestError, RateLimitError, TransientProviderError


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self.api_key = api_key
        self.model = model

    def _ensure_client(self):
        if not self.api_key:
            raise InvalidRequestError("Groq API key is not configured")
        try:
            from groq import AsyncGroq
            return AsyncGroq(api_key=self.api_key)
        except ImportError as exc:
            raise TransientProviderError("Groq SDK is unavailable") from exc

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
            return AIResponse(
                text=text,
                provider=self.name,
                model=self.model,
                metadata={"context_messages": len(context or [])},
            )
        except Exception as exc:
            message = str(exc).lower()
            if "429" in message or "rate" in message:
                raise RateLimitError(str(exc)) from exc
            if "400" in message or "invalid" in message:
                raise InvalidRequestError(str(exc)) from exc
            raise TransientProviderError(str(exc)) from exc

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        self._ensure_client()
        return True

