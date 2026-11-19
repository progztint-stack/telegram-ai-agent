"""Validated application settings."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        str_strip_whitespace=True,
    )

    gemini_api_key: str = ""
    groq_api_key: str = ""
    telegram_bot_token: str = ""
    authorized_telegram_users: str = ""
    ai_primary_provider: Literal["gemini", "groq"] = "gemini"
    gemini_model: str = "gemini-2.5-flash"
    groq_model: str = "llama-3.3-70b-versatile"
    ai_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    ai_max_retries: int = Field(default=1, ge=0, le=5)
    ai_retry_initial_delay_seconds: float = Field(default=0.5, ge=0, le=30)
    ai_retry_max_delay_seconds: float = Field(default=4.0, gt=0, le=60)
    browser_headless: bool = True
    browser_allowed_domains: str = "localhost,127.0.0.1"
    browser_launch_timeout_ms: int = Field(default=30_000, gt=0, le=120_000)
    database_url: str = "sqlite:///./data/tasks.db"
    log_level: str = "INFO"

    @field_validator("authorized_telegram_users")
    @classmethod
    def validate_authorized_users(cls, value: str) -> str:
        user_ids = [item.strip() for item in value.split(",") if item.strip()]
        if any(not user_id.isdecimal() for user_id in user_ids):
            raise ValueError("AUTHORIZED_TELEGRAM_USERS must be a comma-separated list of numeric IDs")
        return value

    @field_validator("browser_allowed_domains")
    @classmethod
    def validate_browser_domains(cls, value: str) -> str:
        domains = [item.strip() for item in value.split(",") if item.strip()]
        if any("/" in domain or "://" in domain or "@" in domain for domain in domains):
            raise ValueError("BROWSER_ALLOWED_DOMAINS must contain hostnames, not URLs")
        return value

    @property
    def authorized_users(self) -> set[int]:
        return {
            int(value.strip())
            for value in self.authorized_telegram_users.split(",")
            if value.strip().isdigit()
        }

    @property
    def allowed_domains(self) -> set[str]:
        values = {
            value.strip().lower().strip(".")
            for value in self.browser_allowed_domains.split(",")
        }
        return {value for value in values if value}

    @property
    def configured_providers(self) -> list[str]:
        configured = {
            "gemini": bool(self.gemini_api_key.strip()),
            "groq": bool(self.groq_api_key.strip()),
        }
        order = [self.ai_primary_provider, "groq" if self.ai_primary_provider == "gemini" else "gemini"]
        return [provider for provider in order if configured[provider]]

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

    def missing_runtime_config(self) -> list[str]:
        missing = self.missing_bot_config()
        if not self.configured_providers:
            missing.append("GEMINI_API_KEY or GROQ_API_KEY")
        return missing

