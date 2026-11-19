"""Database entities and task states."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskRecord:
    id: str
    user_id: int
    title: str
    status: TaskStatus
    progress: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
