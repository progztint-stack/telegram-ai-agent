"""DOM and runtime inspection."""

from __future__ import annotations

from playwright.async_api import Page


async def inspect_page(page: Page, text_limit: int = 20_000) -> dict:
    text = await page.locator("body").inner_text() if await page.locator("body").count() else ""
    return {
        "url": page.url,
        "title": await page.title(),
        "text": text[:text_limit],
        "elements": await page.locator("*").count(),
    }


async def collect_runtime_errors(page: Page) -> tuple[list[str], list[str]]:
    js_errors: list[str] = []
    network_errors: list[str] = []

    page.on("console", lambda message: js_errors.append(str(message.text)) if message.type == "error" else None)
    page.on("pageerror", lambda error: js_errors.append(str(error)))
    page.on("requestfailed", lambda request: network_errors.append(f"{request.url}: {request.failure}"))
    return js_errors, network_errors
