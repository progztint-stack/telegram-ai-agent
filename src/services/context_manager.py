"""In-memory conversation context with bounded history."""

from __future__ import annotations

from collections import defaultdict


class ContextManager:
    def __init__(self, max_messages: int = 30) -> None:
        self.max_messages = max_messages
        self._messages: dict[int, list[dict[str, str]]] = defaultdict(list)

    def add(self, user_id: int, role: str, content: str) -> None:
        history = self._messages[user_id]
        history.append({"role": role, "content": content})
        if len(history) > self.max_messages:
            del history[: len(history) - self.max_messages]

    def get(self, user_id: int) -> list[dict[str, str]]:
        return list(self._messages[user_id])

    def clear(self, user_id: int) -> None:
        self._messages.pop(user_id, None)
