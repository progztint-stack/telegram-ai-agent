from types import SimpleNamespace

import pytest

from src.bot.handlers import BotHandlers
from src.config.settings import Settings
from src.database.repository import TaskRepository
from src.providers.manager import ProviderManager
from src.providers.mock import MockProvider
from src.services.context_manager import ContextManager
from src.services.task_manager import TaskManager


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


@pytest.mark.asyncio
async def test_status_handler(tmp_path):
    settings = Settings(_env_file=None, authorized_telegram_users="123")
    repository = TaskRepository(f"sqlite:///{tmp_path / 'tasks.db'}")
    handlers = BotHandlers(
        settings,
        ProviderManager([MockProvider()]),
        ContextManager(),
        TaskManager(repository),
    )
    message = FakeMessage()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        effective_message=message,
    )
    await handlers.status(update, SimpleNamespace())
    assert message.replies
    assert "الحالة" in message.replies[0]


@pytest.mark.asyncio
async def test_unauthorized_handler():
    settings = Settings(_env_file=None, authorized_telegram_users="123")
    handlers = BotHandlers(settings, ProviderManager([MockProvider()]), ContextManager(), None)
    message = FakeMessage()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=999),
        effective_message=message,
    )
    await handlers.help(update, SimpleNamespace())
    assert "غير مفوض" in message.replies[0]
