"""Sequential provider orchestration."""

from __future__ import annotations

import asyncio
from typing import Sequence

import structlog

from .base import (
    AIProvider,
    AIResponse,
    InvalidRequestError,
    ProviderError,
    RateLimitError,
    TransientProviderError,
)
from .failover import FailoverPolicy


class ProviderManager:
    def __init__(
        self,
        providers: Sequence[AIProvider],
        policy: FailoverPolicy | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.providers = tuple(providers)
        self.policy = policy or FailoverPolicy()
        self.timeout_seconds = timeout_seconds
        self.log = structlog.get_logger(__name__)
        self._active_provider: str | None = None

    async def generate(self, prompt: str, context: list[dict[str, str]] | None = None) -> AIResponse:
        if not prompt.strip():
            raise InvalidRequestError("Prompt cannot be empty")

        last_error: ProviderError | None = None
        for index, provider in enumerate(self.providers):
            for retry_attempt in range(self.policy.max_retries + 1):
                try:
                    response = await asyncio.wait_for(
                        provider.generate(prompt, context),
                        timeout=self.timeout_seconds,
                    )
                    self._active_provider = provider.name
                    if index > 0:
                        self.log.warning("provider_failover_complete", provider=provider.name)
                    return response
                except InvalidRequestError:
                    raise
                except TimeoutError:
                    last_error = TransientProviderError("Provider request timed out")
                    self.log.warning(
                        "provider_request_failed",
                        provider=provider.name,
                        error_type="timeout",
                    )
                except ProviderError as exc:
                    last_error = exc
                    self.log.warning(
                        "provider_request_failed",
                        provider=provider.name,
                        error_type=type(exc).__name__,
                    )
                except Exception as exc:
                    last_error = TransientProviderError(
                        f"{provider.name} failed with {type(exc).__name__}"
                    )
                    self.log.error(
                        "provider_request_failed",
                        provider=provider.name,
                        error_type=type(exc).__name__,
                    )

                retryable = isinstance(last_error, (TransientProviderError, RateLimitError))
                if retryable and retry_attempt < self.policy.max_retries:
                    delay = self.policy.retry_delay(retry_attempt)
                    self.log.warning(
                        "provider_retry",
                        provider=provider.name,
                        attempt=retry_attempt + 1,
                        delay_seconds=delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                break

            if index + 1 < len(self.providers):
                self.log.warning(
                    "provider_switch",
                    from_provider=provider.name,
                    to_provider=self.providers[index + 1].name,
                )

        if last_error:
            raise ProviderError(
                "تعذر الحصول على رد من مزودي الذكاء الاصطناعي. حاول مرة أخرى لاحقًا."
            ) from last_error
        raise ProviderError("No AI providers are configured")

    @property
    def active_provider(self) -> str | None:
        return self._active_provider or (self.providers[0].name if self.providers else None)

    async def status(self) -> dict[str, bool]:
        return {provider.name: await provider.health_check() for provider in self.providers}

    async def close(self) -> None:
        for provider in self.providers:
            await provider.close()
