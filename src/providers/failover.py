"""Failover policy."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FailoverPolicy:
    max_retries: int = 2
    initial_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.initial_delay_seconds < 0 or self.max_delay_seconds <= 0:
            raise ValueError("retry delays must be positive")
        if self.initial_delay_seconds > self.max_delay_seconds:
            raise ValueError("initial delay cannot exceed maximum delay")

    def retry_delay(self, attempt: int) -> float:
        delay = self.initial_delay_seconds * (2 ** max(0, attempt))
        return min(delay, self.max_delay_seconds)

