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
