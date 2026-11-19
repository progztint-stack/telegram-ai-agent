"""Provider used for tests and credential-free local mode."""

from __future__ import annotations

from .base import AIProvider, AIResponse


class MockProvider(AIProvider):
    name = "mock"

    def __init__(self, response: str = "وضع المحاكاة يعمل بنجاح.") -> None:
        self.response = response

    async def generate(self, prompt: str, context: list[dict[str, str]] | None = None) -> AIResponse:
        return AIResponse(
            text=f"{self.response}\n\nسؤالك: {prompt}",
            provider=self.name,
            model="mock-v1",
            metadata={"context_messages": len(context or [])},
        )

    async def health_check(self) -> bool:
        return True

