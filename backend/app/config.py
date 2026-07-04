"""Application settings loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider selection: "gemini" | "anthropic" | "mock" | "auto"
    llm_provider: str = "anthropic"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"

    github_token: str = ""
    database_url: str = "sqlite:///./ai_interviewer.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Admin auth (dashboard). Change these in production.
    admin_password: str = "changeme"
    admin_secret: str = "dev-admin-secret-change-me"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
