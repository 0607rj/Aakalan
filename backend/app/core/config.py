"""Application settings, read from environment variables / `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Aakalan"
    app_version: str = "0.1.0"
    environment: str = "development"

    data_dir: Path = REPO_ROOT / "data"
    database_url: str = ""
    sqlite_vec_enabled: bool = True

    jwt_secret: str = Field(default="dev-only-change-me-0123456789abcdef", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    seeds_dir: Path = BACKEND_DIR / "seeds"
    seed_user_password: str = "aakalan-dev"

    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-5-5"

    @model_validator(mode="after")
    def _no_dev_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret.startswith("dev-only"):
            raise ValueError("JWT_SECRET must be set in production")
        return self

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
