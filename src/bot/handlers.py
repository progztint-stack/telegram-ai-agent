"""Telegram command and message handlers."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import structlog
from telegram import Update
from telegram.error import RetryAfter
from telegram.ext import ContextTypes

from ..browser.manager import BrowserManager
from ..config.settings import Settings
from ..providers.manager import ProviderManager
from ..services.context_manager import ContextManager
from ..services.task_manager import TaskManager
from .keyboards import main_keyboard
from .messages import AR_MESSAGES

TELEGRAM_MESSAGE_LIMIT = 4000


def _split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    chunks: list[str] = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


class BotHandlers:
    def __init__(
        self,
        settings: Settings,
        providers: ProviderManager,
        context: ContextManager,
        tasks: TaskManager,
        browser: BrowserManager | None = None,
    ) -> None:
        self.settings = settings
        self.provider_manager = providers
        self.context = context
        self.task_manager = tasks
        self.browser = browser
        self.active_tasks: dict[int, tuple[str, asyncio.Task]] = {}
        self.log = structlog.get_logger(__name__)

    def _authorized(self, update: Update) -> bool:
        user_id = update.effective_user.id if update.effective_user else 0
        return user_id in self.settings.authorized_users

    async def _reply(self, update: Update, text: str, **kwargs) -> None:
        if not update.effective_message:
            return
        for index, chunk in enumerate(_split_message(text)):
            reply_kwargs = kwargs if index == 0 else {}
            for attempt in range(2):
                try:
                    await update.effective_message.reply_text(chunk, **reply_kwargs)
                    break
                except RetryAfter as exc:
                    if attempt:
                        raise
                    retry_after = exc.retry_after
                    delay = (
                        retry_after.total_seconds()
                        if isinstance(retry_after, timedelta)
                        else float(retry_after)
                    )
                    await asyncio.sleep(min(delay, 30.0))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        await self._reply(update, AR_MESSAGES["start"], reply_markup=main_keyboard())

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        await self._reply(update, AR_MESSAGES["help"])

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        database_healthy = self.task_manager.repository.health_check()
        provider_status = await self.provider_manager.status()
        configured = [name for name, healthy in provider_status.items() if healthy]
        text = (
            "الحالة: "
            + ("سليم ✅" if database_healthy else "يوجد خلل ⚠️")
            + "\nقاعدة البيانات: "
            + ("متصلة" if database_healthy else "غير متاحة")
            + "\nالمزود النشط: "
            + (self.provider_manager.active_provider or "غير مهيأ")
            + "\nالمزودون المهيؤون: "
            + (", ".join(configured) if configured else "لا يوجد")
        )
        await self._reply(update, text)

    async def providers(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        statuses = await self.provider_manager.status()
        active = self.provider_manager.active_provider or "غير مهيأ"
        lines = [
            f"{name}: {'مهيأ' if configured else 'غير مهيأ'}"
            for name, configured in statuses.items()
        ]
        await self._reply(
            update,
            f"المزود النشط: {active}\n" + ("\n".join(lines) or "لا يوجد مزود مهيأ"),
        )

    async def _handle_prompt(self, update: Update, prompt: str) -> None:
        if not prompt.strip() or not update.effective_user:
            return
        user_id = update.effective_user.id
        if user_id in self.active_tasks:
            await self._reply(update, "لديك طلب قيد التنفيذ. ألغِه أو انتظر اكتماله.")
            return
        current_task = asyncio.current_task()
        if current_task is None:
            raise RuntimeError("AI request must run inside an asyncio task")
        task_id: str | None = None
        try:
            task = self.task_manager.create(user_id, "طلب ذكاء اصطناعي")
            task_id = task.id
            self.active_tasks[user_id] = (task_id, current_task)
            self.task_manager.start(task_id)
            history = self.context.get(user_id)
            self.context.add(user_id, "user", prompt)
            response = await self.provider_manager.generate(prompt, history)
            self.context.add(user_id, "assistant", response.text)
            self.task_manager.complete(task_id, {
                "provider": response.provider,
                "model": response.model,
            })
            await self._reply(update, f"{response.text}\n\nالمزود: {response.provider}")
        except asyncio.CancelledError:
            if task_id:
                self.task_manager.cancel(task_id)
            raise
        except Exception as exc:
            if task_id:
                self.task_manager.fail(task_id, type(exc).__name__)
            self.log.error("telegram_request_failed", error_type=type(exc).__name__)
            await self._reply(update, "تعذر تنفيذ الطلب حاليًا. تحقق من حالة المزود وحاول لاحقًا.")
        finally:
            active = self.active_tasks.get(user_id)
            if active and active[1] is current_task:
                self.active_tasks.pop(user_id, None)

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        message = update.effective_message
        if message and message.text:
            await self._handle_prompt(update, message.text)

    async def test_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        prompt = " ".join(context.args) if context.args else "أعطني شرحًا مختصرًا"
        await self._handle_prompt(update, prompt)

    async def browser_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        if self.browser is None:
            await self._reply(update, "إدارة المتصفح غير مهيأة.")
            return
        try:
            await self.browser.start()
        except Exception as exc:
            self.log.error("browser_start_failed", error_type=type(exc).__name__)
            await self._reply(update, "تعذر تشغيل Chromium. تحقق من تثبيت المتصفح ومتطلباته.")
            return
        await self._reply(update, "Chromium يعمل بنجاح في الوضع headless.")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        user_id = update.effective_user.id
        active = self.active_tasks.get(user_id)
        if not active:
            await self._reply(update, AR_MESSAGES["no_task"])
            return
        task_id, running_task = active
        self.task_manager.cancel(task_id)
        running_task.cancel()
        await self._reply(update, AR_MESSAGES["cancelled"])

    async def tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        user_id = update.effective_user.id
        records = self.task_manager.list(user_id)
        if not records:
            await self._reply(update, "لا توجد مهام مسجلة.")
            return
        lines = [
            f"{item.id[:8]} — {item.status.value} — {item.progress}% — {item.title}"
            for item in records
        ]
        await self._reply(update, "\n".join(lines))
