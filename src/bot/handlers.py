"""Telegram command handlers."""

from __future__ import annotations

from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from ..config.settings import Settings
from ..providers.manager import ProviderManager
from ..services.context_manager import ContextManager
from ..services.task_manager import TaskManager
from .keyboards import main_keyboard
from .messages import AR_MESSAGES


class BotHandlers:
    def __init__(
        self,
        settings: Settings,
        providers: ProviderManager,
        context: ContextManager,
        tasks: TaskManager,
    ) -> None:
        self.settings = settings
        self.providers = providers
        self.context = context
        self.tasks = tasks
        self.active_tasks: dict[int, str] = {}

    def _authorized(self, update: Update) -> bool:
        user_id = update.effective_user.id if update.effective_user else 0
        if not self.settings.authorized_users:
            return False
        return user_id in self.settings.authorized_users

    async def _reply(self, update: Update, text: str, **kwargs) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(text, **kwargs)

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
        missing = self.settings.missing_external_config()
        text = "الحالة: جاهز ✅\nالوضع: محاكاة" if not missing else (
            "الحالة: محدود ⚠️\n"
            + "الاعتمادات الناقصـة: " + ", ".join(missing)
        )
        await self._reply(update, text)

    async def providers(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        statuses = await self.providers.status()
        lines = [f"{name}: {'متاح' if available else 'غير مفعل'}" for name, available in statuses.items()]
        await self._reply(update, "مزودو الذكاء الاصطناعي:\n" + "\n".join(lines))

    async def test_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        user_id = update.effective_user.id
        prompt = " ".join(context.args) if context.args else "أعطني شرحًا مختصرًا"
        task = self.tasks.create(user_id, "اختبار مزود الذكاء الاصطناعي")
        self.active_tasks[user_id] = task.id
        self.tasks.start(task.id)
        self.context.add(user_id, "user", prompt)
        try:
            response = await self.providers.generate(prompt, self.context.get(user_id))
            self.context.add(user_id, "assistant", response.text)
            self.tasks.complete(task.id, {
                "provider": response.provider,
                "model": response.model,
            })
            await self._reply(update, f"{response.text}\n\nالمزود: {response.provider}")
        except Exception as exc:
            self.tasks.fail(task.id, type(exc).__name__)
            await self._reply(update, "تعذر تنفيذ الطلب حاليًا. لم يتم فقدان سجل المهمة.")
        finally:
            self.active_tasks.pop(user_id, None)

    async def browser_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        await self._reply(
            update,
            "متصفح Playwright متاح للاستخدام مع روابط تجريبية المحلية فقط.",
        )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        user_id = update.effective_user.id
        task_id = self.active_tasks.pop(user_id, None)
        if not task_id:
            await self._reply(update, AR_MESSAGES["no_task"])
            return
        self.tasks.cancel(task_id)
        await self._reply(update, AR_MESSAGES["cancelled"])

    async def tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            await self._reply(update, AR_MESSAGES["unauthorized"])
            return
        user_id = update.effective_user.id
        records = self.tasks.list(user_id)
        if not records:
            await self._reply(update, "لا توجد مهام مسجلة.")
            return
        lines = [f"{item.id[:8]} — {item.status.value} — {item.progress}% — {item.title}" for item in records]
        await self._reply(update, "\n".join(lines))
