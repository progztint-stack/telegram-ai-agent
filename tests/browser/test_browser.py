import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from src.browser.manager import BrowserManager
from src.browser.navigation import NavigationService
from src.browser.screenshots import capture_screenshot
from src.browser.security import BrowserSecurity


@pytest.mark.asyncio
async def test_browser_navigation_and_screenshot(tmp_path):
    pytest.importorskip("playwright")
    fixtures = Path(__file__).parents[2] / "fixtures"
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(fixtures))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    manager = BrowserManager(headless=True)
    try:
        await manager.start()
        page = await manager.new_page()
        security = BrowserSecurity({"localhost", "127.0.0.1"}, allow_local=True)
        service = NavigationService(security)
        result = await service.navigate(page, f"http://127.0.0.1:{port}/test_store.html")
        assert result["title"] == "متجر تجريبي"
        screenshot = await capture_screenshot(page, str(tmp_path))
        assert Path(screenshot).exists()
    finally:
        await manager.close()
        server.shutdown()
        thread.join(timeout=5)
