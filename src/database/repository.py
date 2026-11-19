"""SQLite task repository."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import TaskRecord, TaskStatus, utc_now


class TaskRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("Only sqlite:/// DATABASE_URL is supported")
        path = database_url.removeprefix("sqlite:///")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, task: TaskRecord) -> TaskRecord:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO tasks
                   (id,user_id,title,status,progress,result,error,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    task.id, task.user_id, task.title, task.status.value, task.progress,
                    json.dumps(task.result, ensure_ascii=False) if task.result else None,
                    task.error, task.created_at, task.updated_at,
                ),
            )
        return task

    def get(self, task_id: str) -> TaskRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_for_user(self, user_id: int, limit: int = 20) -> list[TaskRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def update(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        progress: int | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> TaskRecord | None:
        fields: list[str] = []
        values: list[object] = []
        if status is not None:
            fields.append("status=?")
            values.append(status.value)
        if progress is not None:
            fields.append("progress=?")
            values.append(max(0, min(100, progress)))
        if result is not None:
            fields.append("result=?")
            values.append(json.dumps(result, ensure_ascii=False))
        if error is not None:
            fields.append("error=?")
            values.append(error)
        fields.append("updated_at=?")
        values.append(utc_now())
        values.append(task_id)
        if not fields:
            return self.get(task_id)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE tasks SET {','.join(fields)} WHERE id=?",
                values,
            )
        return self.get(task_id)

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            status=TaskStatus(row["status"]),
            progress=row["progress"],
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
