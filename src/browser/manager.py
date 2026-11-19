"""Chromium lifecycle and browser session management."""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Route,
    async_playwright,
)

from .security import BrowserSecurity, NavigationDeniedError


class BrowserManager:
    def __init__(
        self,
        headless: bool = True,
        session_dir: str = "browser_sessions",
        launch_timeout_ms: int = 30_000,
        security: BrowserSecurity | None = None,
    ) -> None:
        if launch_timeout_ms <= 0:
            raise ValueError("launch_timeout_ms must be positive")
        self.headless = headless
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.launch_timeout_ms = launch_timeout_ms
        self.security = security or BrowserSecurity(set())
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        if self._browser and self._browser.is_connected():
            return
        await self.close()
        playwright = await async_playwright().start()
        browser: Browser | None = None
        try:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                timeout=self.launch_timeout_ms,
            )
            context = await browser.new_context(service_workers="block")
        except BaseException:
            if browser:
                await browser.close()
            await playwright.stop()
            raise
        self._playwright = playwright
        self._browser = browser
        self._context = context

    async def new_page(self) -> Page:
        await self.start()
        assert self._context is not None
        page = await self._context.new_page()
        await page.route("**/*", self._guard_route)
        return page

    async def _guard_route(self, route: Route) -> None:
        try:
            await asyncio.to_thread(self.security.validate_url, route.request.url)
        except NavigationDeniedError:
            await route.abort()
            return
        await route.continue_()

    async def close(self) -> None:
        context, self._context = self._context, None
        browser, self._browser = self._browser, None
        playwright, self._playwright = self._playwright, None
        try:
            if context:
                await context.close()
        finally:
            try:
                if browser:
                    await browser.close()
            finally:
                if playwright:
                    await playwright.stop()

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._browser.is_connected()
