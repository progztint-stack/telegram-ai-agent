"""Sequential provider orchestration."""

from __future__ import annotations

import asyncio
import structlog

from .base import AIProvider, AIResponse, InvalidRequestError, ProviderError, RateLimitError, TransientProviderError
from .failover import FailoverPolicy


class ProviderManager:
    def __init__(self, providers: list[AIProvider], policy: FailoverPolicy | None = None) -> None:
        self.providers = providers
        self.policy = policy or FailoverPolicy()
        self.log = structlog.get_logger(__name__)

    async def generate(self, prompt: str, context: list[dict[str, str]] | None = None) -> AIResponse:
        if not prompt.strip():
            raise InvalidRequestError("Prompt cannot be empty")

        last_error: ProviderError | None = None
        for index, provider in enumerate(self.providers):
            for retry_attempt in range(self.policy.max_retries + 1):
                try:
                    response = await provider.generate(prompt, context)
                    if index > 0:
                        self.log.warning("provider_failover_complete", provider=provider.name)
                    return response
                except InvalidRequestError:
                    raise
                except (TransientProviderError, RateLimitError) as exc:
                    last_error = exc
                    if retry_attempt < self.policy.max_retries:
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
            raise last_error
        raise ProviderError("No AI providers are configured")

    async def status(self) -> dict[str, bool]:
        return {
            provider.name: await provider.health_check()
            for provider in self.providers
        }
