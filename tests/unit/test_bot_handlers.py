import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from telegram.error import RetryAfter

from src.bot.handlers import BotHandlers
from src.config.settings import Settings
from src.database.models import TaskStatus
from src.database.repository import TaskRepository
from src.providers.manager import ProviderManager
from src.providers.mock import MockProvider
from src.services.context_manager import ContextManager
from src.services.task_manager import TaskManager


class FakeMessage:
    def __init__(self):
        self.replies = []
        self.reply_options = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.reply_options.append(kwargs)


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


@pytest.mark.asyncio
async def test_text_message_is_processed_and_persisted(tmp_path):
    settings = Settings(_env_file=None, authorized_telegram_users="123")
    repository = TaskRepository(f"sqlite:///{tmp_path / 'tasks.db'}")
    context = ContextManager(repository=repository)
    handlers = BotHandlers(
        settings,
        ProviderManager([MockProvider()]),
        context,
        TaskManager(repository),
    )
    message = FakeMessage()
    message.text = "سؤال جديد"
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        effective_message=message,
    )

    await handlers.message(update, SimpleNamespace())

    assert "سؤال جديد" in message.replies[0]
    assert [item["role"] for item in context.get(123)] == ["user", "assistant"]
    assert repository.get_conversation(123)[0]["content"] == "سؤال جديد"
    assert callable(handlers.tasks)


@pytest.mark.asyncio
async def test_replies_are_split_under_telegram_limit():
    settings = Settings(_env_file=None, authorized_telegram_users="123")
    handlers = BotHandlers(settings, ProviderManager([MockProvider()]), ContextManager(), None)
    message = FakeMessage()
    update = SimpleNamespace(effective_message=message)

    await handlers._reply(update, "x" * 8500)

    assert len(message.replies) == 3
    assert all(len(reply) <= 4000 for reply in message.replies)


@pytest.mark.asyncio
async def test_reply_splitting_respects_telegram_utf16_character_limit():
    handlers = BotHandlers(
        Settings(_env_file=None, authorized_telegram_users="123"),
        ProviderManager([MockProvider()]),
        ContextManager(),
        None,
    )
    message = FakeMessage()

    await handlers._reply(SimpleNamespace(effective_message=message), "\U0001f600" * 2500)

    assert len(message.replies) == 2
    assert all(len(reply.encode("utf-16-le")) // 2 <= 4000 for reply in message.replies)


@pytest.mark.asyncio
async def test_telegram_rate_limit_is_retried_once(monkeypatch):
    class RateLimitedMessage(FakeMessage):
        def __init__(self):
            super().__init__()
            self.rate_limited = True

        async def reply_text(self, text, **kwargs):
            if self.rate_limited:
                self.rate_limited = False
                raise RetryAfter(1)
            await super().reply_text(text, **kwargs)

    async def no_wait(_):
        return None

    monkeypatch.setattr("src.bot.handlers.asyncio.sleep", no_wait)
    monkeypatch.setattr(
        RetryAfter,
        "retry_after",
        property(lambda self: timedelta(seconds=1)),
    )
    handlers = BotHandlers(
        Settings(_env_file=None, authorized_telegram_users="123"),
        ProviderManager([MockProvider()]),
        ContextManager(),
        None,
    )
    message = RateLimitedMessage()

    await handlers._reply(SimpleNamespace(effective_message=message), "رد")

    assert message.replies == ["رد"]


@pytest.mark.asyncio
async def test_cancel_command_cancels_active_provider_request(tmp_path):
    started = asyncio.Event()

    class SlowProvider:
        name = "slow"

        async def generate(self, prompt, context=None):
            started.set()
            await asyncio.Event().wait()

        async def health_check(self):
            return True

    repository = TaskRepository(f"sqlite:///{tmp_path / 'tasks.db'}")
    handlers = BotHandlers(
        Settings(_env_file=None, authorized_telegram_users="123"),
        ProviderManager([SlowProvider()]),
        ContextManager(repository=repository),
        TaskManager(repository),
    )
    request_update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        effective_message=FakeMessage(),
    )
    request = asyncio.create_task(handlers._handle_prompt(request_update, "انتظر"))
    await started.wait()
    cancel_message = FakeMessage()
    cancel_update = SimpleNamespace(
        effective_user=SimpleNamespace(id=123),
        effective_message=cancel_message,
    )

    await handlers.cancel(cancel_update, SimpleNamespace())
    with pytest.raises(asyncio.CancelledError):
        await request

    assert cancel_message.replies == ["تم إلغاء المهمة."]
    assert repository.list_for_user(123)[0].status == TaskStatus.CANCELLED
