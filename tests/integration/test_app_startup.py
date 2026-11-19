from src.main import build_application
from src.config.settings import Settings


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


def test_application_registers_commands_and_uses_configured_provider_order(tmp_path):
    settings = Settings(
        _env_file=None,
        telegram_bot_token="123456:test-token",
        authorized_telegram_users="123",
        gemini_api_key="gemini-test",
        groq_api_key="groq-test",
        ai_primary_provider="groq",
        database_url=f"sqlite:///{tmp_path / 'tasks.db'}",
    )

    application = build_application(settings)

    assert application is not None
    assert [
        provider.name
        for provider in application.bot_data["provider_manager"].providers
    ] == ["groq", "gemini"]
    command_names = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        for command in getattr(handler, "commands", set())
    }
    assert {"start", "help", "status", "provider", "providers"}.issubset(command_names)
