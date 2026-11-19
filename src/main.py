"""Application entry point."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from .bot.handlers import BotHandlers
from .browser.manager import BrowserManager
from .browser.security import BrowserSecurity
from .config.logging import configure_logging
from .config.settings import Settings
from .database.repository import TaskRepository
from .providers.base import AIProvider
from .providers.failover import FailoverPolicy
from .providers.gemini import GeminiProvider
from .providers.groq import GroqProvider
from .providers.manager import ProviderManager
from .services.context_manager import ContextManager
from .services.task_manager import TaskManager


async def _shutdown(application: Application) -> None:
    providers: ProviderManager = application.bot_data["provider_manager"]
    browser: BrowserManager = application.bot_data["browser_manager"]
    try:
        await providers.close()
    finally:
        await browser.close()


async def _handle_telegram_error(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    logging.getLogger(__name__).error(
        "Unhandled Telegram update error (%s)",
        type(context.error).__name__ if context.error else "unknown",
    )


def build_application(settings: Settings | None = None) -> Application | None:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    missing = settings.missing_runtime_config()
    if missing:
        logging.getLogger(__name__).error(
            "Bot startup blocked; configure environment variables: %s",
            ", ".join(missing),
        )
        return None

    repository = TaskRepository(settings.database_url)
    tasks = TaskManager(repository)
    conversation = ContextManager(repository=repository)

    provider_by_name: dict[str, AIProvider] = {
        "gemini": GeminiProvider(settings.gemini_api_key, model=settings.gemini_model),
        "groq": GroqProvider(
            settings.groq_api_key,
            model=settings.groq_model,
            timeout_seconds=settings.ai_timeout_seconds,
        ),
    }
    providers = [provider_by_name[name] for name in settings.configured_providers]
    provider_manager = ProviderManager(
        providers,
        policy=FailoverPolicy(
            max_retries=settings.ai_max_retries,
            initial_delay_seconds=settings.ai_retry_initial_delay_seconds,
            max_delay_seconds=settings.ai_retry_max_delay_seconds,
        ),
        timeout_seconds=settings.ai_timeout_seconds,
    )
    browser = BrowserManager(
        headless=settings.browser_headless,
        launch_timeout_ms=settings.browser_launch_timeout_ms,
        security=BrowserSecurity(settings.allowed_domains),
    )
    handlers = BotHandlers(settings, provider_manager, conversation, tasks, browser)

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .concurrent_updates(4)
        .post_shutdown(_shutdown)
        .build()
    )
    application.bot_data["provider_manager"] = provider_manager
    application.bot_data["browser_manager"] = browser
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("status", handlers.status))
    application.add_handler(CommandHandler("provider", handlers.providers))
    application.add_handler(CommandHandler("providers", handlers.providers))
    application.add_handler(CommandHandler("test_ai", handlers.test_ai))
    application.add_handler(CommandHandler("browser_status", handlers.browser_status))
    application.add_handler(CommandHandler("cancel", handlers.cancel))
    application.add_handler(CommandHandler("tasks", handlers.tasks))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.message)
    )
    application.add_error_handler(_handle_telegram_error)
    return application


def main() -> None:
    application = build_application()
    if application is None:
        raise SystemExit(1)
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
