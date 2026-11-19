"""Credential-free health check."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.providers.mock import MockProvider


async def main() -> None:
    provider = MockProvider()
    response = await provider.generate("فحص التشغيل")
    print(f"mock_provider=healthy text={response.text[:40]!r}")
    for name in (
        "TELEGRAM_BOT_TOKEN",
        "AUTHORIZED_TELEGRAM_USERS",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
    ):
        print(f"{name}={'SET' if os.getenv(name) else 'NOT_SET'}")


if __name__ == "__main__":
    asyncio.run(main())
