import pytest
from pydantic import ValidationError

from src.config.settings import Settings


def test_missing_api_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("AUTHORIZED_TELEGRAM_USERS", raising=False)
    settings = Settings(_env_file=None)
    missing = settings.missing_external_config()
    assert "GEMINI_API_KEY" in missing
    assert "GROQ_API_KEY" in missing
    assert "TELEGRAM_BOT_TOKEN" in missing


def test_authorized_users():
    settings = Settings(_env_file=None, authorized_telegram_users="123, 456")
    assert settings.authorized_users == {123, 456}


def test_missing_bot_config_does_not_require_ai_keys():
    settings = Settings(
        _env_file=None,
        telegram_bot_token="test-token",
        authorized_telegram_users="123",
    )
    assert settings.missing_bot_config() == []


def test_configured_providers_respect_primary_order():
    settings = Settings(
        _env_file=None,
        gemini_api_key="gemini-test",
        groq_api_key="groq-test",
        ai_primary_provider="groq",
    )
    assert settings.configured_providers == ["groq", "gemini"]


def test_runtime_requires_one_ai_provider():
    settings = Settings(
        _env_file=None,
        telegram_bot_token="telegram-test",
        authorized_telegram_users="123",
    )
    assert settings.missing_runtime_config() == ["GEMINI_API_KEY or GROQ_API_KEY"]


def test_invalid_authorized_user_id_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, authorized_telegram_users="123,not-an-id")
