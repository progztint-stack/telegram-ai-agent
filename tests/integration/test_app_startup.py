from src.main import build_application


def test_mock_mode_starts_without_real_credentials(monkeypatch):
    for name in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "AUTHORIZED_TELEGRAM_USERS",
    ):
        monkeypatch.delenv(name, raising=False)
    application = build_application()
    assert application is None


def test_bot_does_not_start_with_token_but_no_authorized_users(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.delenv("AUTHORIZED_TELEGRAM_USERS", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    application = build_application()
    assert application is None
