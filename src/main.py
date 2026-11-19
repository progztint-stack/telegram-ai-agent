"""Application entry point."""

from __future__ import annotations

import asyncio

from telegram.ext import Application, CommandHandler

from .bot.handlers import BotHandlers
from .config.logging import configure_logging
from .config.settings import Settings
from .database.repository import TaskRepository
from .providers.gemini import GeminiProvider
from .providers.groq import GroqProvider
from .providers.mock import MockProvider
from .providers.manager import ProviderManager
from .services.context_manager import ContextManager
from .services.task_manager import TaskManager


def build_application() -> Application | None:
    settings = Settings()
    configure_logging()

    if settings.missing_bot_config():
        return None

    repository = TaskRepository(settings.database_url)
    tasks = TaskManager(repository)
    context = ContextManager()

    providers = []
    if settings.gemini_api_key:
        providers.append(GeminiProvider(settings.gemini_api_key))
    if settings.groq_api_key:
        providers.append(GroqProvider(settings.groq_api_key))
    if not providers:
        providers.append(MockProvider())

    provider_manager = ProviderManager(providers)
    handlers = BotHandlers(settings, provider_manager, context, tasks)

    if not settings.telegram_bot_token:
        return None

    application = Application.builder().token(settings.telegram_bot_token).build()
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("status", handlers.status))
    application.add_handler(CommandHandler("providers", handlers.providers))
    application.add_handler(CommandHandler("test_ai", handlers.test_ai))
    application.add_handler(CommandHandler("browser_status", handlers.browser_status))
    application.add_handler(CommandHandler("cancel", handlers.cancel))
    application.add_handler(CommandHandler("tasks", handlers.tasks))
    return application


def main() -> None:
    application = build_application()
    if application is None:
        print("التطبيق يحتاج إلى TELEGRAM_BOT_TOKEN وبيانات المستخدم المصرح به.")
        print("اختبر الوحدات عبر pytest دون مفاتيح حقيقية.")
        return
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
