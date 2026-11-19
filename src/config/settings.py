"""Validated application settings."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    groq_api_key: str = ""
    telegram_bot_token: str = ""
    authorized_telegram_users: str = ""
    browser_headless: bool = True
    browser_allowed_domains: str = "localhost,127.0.0.1"
    database_url: str = "sqlite:///./data/tasks.db"

    @property
    def authorized_users(self) -> set[int]:
        if not self.authorized_telegram_users.strip():
            return set()
        return {
            int(value.strip())
            for value in self.authorized_telegram_users.split(",")
            if value.strip().isdigit()
        }

    @property
    def allowed_domains(self) -> set[str]:
        values = {value.strip().lower() for value in self.browser_allowed_domains.split(",")}
        return {value for value in values if value}

    @property
    def sqlite_path(self) -> str:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("DATABASE_URL must use sqlite:/// for this application")
        return self.database_url[len(prefix):]

    def missing_external_config(self) -> list[str]:
        missing: list[str] = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.groq_api_key:
            missing.append("GROQ_API_KEY")
        if not self.authorized_users:
            missing.append("AUTHORIZED_TELEGRAM_USERS")
        return missing

    def missing_bot_config(self) -> list[str]:
        missing: list[str] = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.authorized_users:
            missing.append("AUTHORIZED_TELEGRAM_USERS")
        return missing

