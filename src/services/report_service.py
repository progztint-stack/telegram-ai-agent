"""Structured execution reports."""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    title: str,
    status: str,
    progress: int,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "status": status,
        "progress": progress,
        "result": result,
        "error": error,
    }
