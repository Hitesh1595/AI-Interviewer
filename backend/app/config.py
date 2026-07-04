"""Application settings loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider: "openai" | "mock" | "auto"
    llm_provider: str = "openai"

    # OpenAI — text model for evaluation + Realtime model/voice for the interview.
    openai_api_key: str = ""
    openai_text_model: str = "gpt-4o-mini"
    openai_realtime_model: str = "gpt-realtime-2"
    openai_voice: str = "alloy"

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
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
