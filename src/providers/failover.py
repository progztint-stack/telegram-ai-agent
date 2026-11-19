"""Failover policy."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FailoverPolicy:
    max_retries: int = 2
    initial_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0

    def retry_delay(self, attempt: int) -> float:
        delay = self.initial_delay_seconds * (2 ** max(0, attempt))
        return min(delay, self.max_delay_seconds)

