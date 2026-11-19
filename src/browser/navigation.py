"""Safe page navigation."""

from __future__ import annotations

from playwright.async_api import Page

from .security import BrowserSecurity


class NavigationService:
    def __init__(self, security: BrowserSecurity, timeout_ms: int = 30_000) -> None:
        self.security = security
        self.timeout_ms = timeout_ms

    async def navigate(self, page: Page, url: str) -> dict:
        safe_url = self.security.validate_url(url)
        response = await page.goto(safe_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        return {
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None,
        }

    async def fill(self, page: Page, selector: str, value: str) -> None:
        await page.locator(selector).fill(value, timeout=self.timeout_ms)

    async def click(self, page: Page, selector: str) -> dict:
        await page.locator(selector).click(timeout=self.timeout_ms)
        return {
            "url": page.url,
            "title": await page.title(),
        }

    async def confirmed_destructive_click(
        self,
        page: Page,
        selector: str,
        *,
        confirmed: bool,
    ) -> dict:
        if not confirmed:
            raise PermissionError("يتطلب الإجراء التدميري تأكيدًا صريحًا")
        return await self.click(page, selector)
