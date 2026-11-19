"""Provider abstractions and provider-specific exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


class ProviderError(Exception):
    """Base provider error."""


class InvalidRequestError(ProviderError):
    """Request is invalid and should not be retried."""


class RateLimitError(ProviderError):
    """Provider quota or rate limit was exceeded."""


class TransientProviderError(ProviderError):
    """Temporary provider or connection failure."""


@dataclass(frozen=True)
class AIResponse:
    text: str
    provider: str
    model: str
    metadata: dict[str, Any] | None = None


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, prompt: str, context: list[dict[str, str]] | None = None) -> AIResponse:
        """Generate a response."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check whether provider credentials and service are usable."""

