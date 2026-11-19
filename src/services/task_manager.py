"""Persistent task lifecycle manager."""

from __future__ import annotations

from uuid import uuid4

from ..database.models import TaskRecord, TaskStatus, utc_now
from ..database.repository import TaskRepository


class TaskManager:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository
        self._cancelled: set[str] = set()

    def create(self, user_id: int, title: str) -> TaskRecord:
        now = utc_now()
        task = TaskRecord(
            id=uuid4().hex,
            user_id=user_id,
            title=title,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        return self.repository.create(task)

    def start(self, task_id: str) -> TaskRecord | None:
        return self.repository.update(task_id, status=TaskStatus.RUNNING, progress=0)

    def progress(self, task_id: str, progress: int) -> TaskRecord | None:
        if task_id in self._cancelled:
            return self.cancel(task_id)
        return self.repository.update(task_id, progress=progress)

    def waiting(self, task_id: str) -> TaskRecord | None:
        return self.repository.update(task_id, status=TaskStatus.WAITING_FOR_USER)

    def complete(self, task_id: str, result: dict) -> TaskRecord | None:
        return self.repository.update(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            result=result,
        )

    def fail(self, task_id: str, error: str) -> TaskRecord | None:
        return self.repository.update(
            task_id,
            status=TaskStatus.FAILED,
            error=error,
        )

    def cancel(self, task_id: str) -> TaskRecord | None:
        self._cancelled.add(task_id)
        task = self.repository.update(task_id, status=TaskStatus.CANCELLED)
        self._cancelled.discard(task_id)
        return task

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self._cancelled

    def get(self, task_id: str) -> TaskRecord | None:
        return self.repository.get(task_id)

    def list(self, user_id: int) -> list[TaskRecord]:
        return self.repository.list_for_user(user_id)
