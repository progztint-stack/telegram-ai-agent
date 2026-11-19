"""Google Gemini provider adapter."""

from __future__ import annotations

from .base import AIProvider, AIResponse, InvalidRequestError, ProviderError, RateLimitError, TransientProviderError


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self._client = None

    def _ensure_client(self) -> None:
        if not self.api_key:
            raise InvalidRequestError("Gemini API key is not configured")
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        except ImportError as exc:
            raise TransientProviderError("Gemini SDK is unavailable") from exc

    async def generate(self, prompt: str, context: list[dict[str, str]] | None = None) -> AIResponse:
        self._ensure_client()
        assert self._client is not None
        history = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}" for item in (context or [])
        )
        full_prompt = f"{history}\n\nuser: {prompt}" if history else prompt
        try:
            response = await self._client.generate_content_async(full_prompt)
            return AIResponse(
                text=response.text,
                provider=self.name,
                model=self.model,
                metadata={"context_messages": len(context or [])},
            )
        except Exception as exc:
            message = str(exc).lower()
            if "quota" in message or "rate" in message or "429" in message:
                raise RateLimitError(str(exc)) from exc
            if "400" in message or "invalid" in message:
                raise InvalidRequestError(str(exc)) from exc
            raise TransientProviderError(str(exc)) from exc

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        self._ensure_client()
        return True

