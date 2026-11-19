"""Check production configuration, SQLite, and headless Chromium."""

from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.async_api import Error as PlaywrightError

from src.browser.manager import BrowserManager
from src.browser.security import BrowserSecurity
from src.config.settings import Settings
from src.database.repository import TaskRepository


async def check_browser(settings: Settings) -> None:
    browser = BrowserManager(
        headless=settings.browser_headless,
        launch_timeout_ms=settings.browser_launch_timeout_ms,
        security=BrowserSecurity(settings.allowed_domains),
    )
    try:
        await browser.start()
    finally:
        await browser.close()


def main() -> int:
    settings = Settings()
    missing = settings.missing_runtime_config()
    if missing:
        print("configuration=not_ready missing=" + ",".join(missing))
        return 1

    try:
        repository = TaskRepository(settings.database_url)
        if not repository.health_check():
            print("database=failed")
            return 1
        print("database=healthy")
        asyncio.run(check_browser(settings))
        print("chromium=healthy")
    except (OSError, sqlite3.Error, ValueError, PlaywrightError) as exc:
        print(f"health=failed error_type={type(exc).__name__}")
        return 1
    print("configuration=ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
