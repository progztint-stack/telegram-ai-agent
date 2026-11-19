"""Screenshot capture."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from playwright.async_api import Page


async def capture_screenshot(page: Page, output_dir: str = "artifacts/screenshots") -> str:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{uuid4().hex}.png"
    await page.screenshot(path=str(path), full_page=True)
    return str(path)
