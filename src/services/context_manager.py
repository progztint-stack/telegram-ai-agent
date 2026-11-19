"""In-memory conversation context with bounded history."""

from __future__ import annotations

from collections import defaultdict

from ..database.repository import TaskRepository


class ContextManager:
    def __init__(
        self,
        max_messages: int = 30,
        repository: TaskRepository | None = None,
    ) -> None:
        if max_messages < 1:
            raise ValueError("max_messages must be positive")
        self.max_messages = max_messages
        self.repository = repository
        self._messages: dict[int, list[dict[str, str]]] = defaultdict(list)

    def add(self, user_id: int, role: str, content: str) -> None:
        history = self._messages[user_id]
        history.append({"role": role, "content": content})
        if len(history) > self.max_messages:
            del history[: len(history) - self.max_messages]
        if self.repository:
            self.repository.save_conversation(user_id, history)

    def get(self, user_id: int) -> list[dict[str, str]]:
        if user_id not in self._messages and self.repository:
            self._messages[user_id] = self.repository.get_conversation(
                user_id,
                limit=self.max_messages,
            )
        return list(self._messages[user_id])

    def clear(self, user_id: int) -> None:
        self._messages.pop(user_id, None)
        if self.repository:
            self.repository.clear_conversation(user_id)
