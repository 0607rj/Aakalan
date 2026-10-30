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

    # Sign-up and emailed one-time codes (services/auth.py). Email goes out by SMTP when
    # smtp_host is set; otherwise (not in production) it is written to the server log.
    signup_enabled: bool = True
    otp_minutes: int = 10  # a code's lifetime
    otp_max_attempts: int = 5  # wrong tries before a code stops working
    otp_resend_seconds: int = 60  # wait before another code
    otp_max_per_hour: int = 5  # codes per user and purpose in an hour
    # Wrong passwords at sign-in (services/auth.py): after this many for one email, or from one
    # address, sign-in waits until the oldest falls out of the window (no lock-out for ever).
    login_max_failures: int = 5
    login_ip_max_failures: int = 30
    login_window_minutes: int = 15
    password_min_length: int = 8
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "Aakalan <no-reply@aakalan.local>"
    smtp_starttls: bool = True

    # Sign-in emails of the product owner (OWNER_EMAILS, a JSON list). Only they see how close
    # the estimates are to real results and record bid results (OPEN_QUESTIONS 169); empty = nobody.
    owner_emails: list[str] = []

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    seeds_dir: Path = BACKEND_DIR / "seeds"
    seed_user_password: str = "admin123"
    # The shared library of researched features (services/research/library.py); empty = the
    # file under seeds_dir. Tests point it at a temporary file.
    research_library_path: Path | None = None

    llm_provider: str = "anthropic"  # "anthropic" or "fake" (tests / offline demos)
    llm_model: str = "claude-sonnet-5-5"
    llm_effort: str = "medium"
    llm_max_output_tokens: int = 16000
    anthropic_api_key: str = ""
    # Server-side web search tool for researching missing features (services/research).
    llm_web_search_tool: str = "web_search_20250305"

    upload_max_mb: int = 25
    # Tries of the AI call that counts what the system contains (the independent check); a
    # document left uncounted needs a person to confirm its price before export.
    inventory_tries: int = 2
    document_max_chars: int = 2_500_000  # ~600k tokens; larger documents are refused, not cut

    @model_validator(mode="after")
    def _no_dev_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret.startswith("dev-only"):
            raise ValueError("JWT_SECRET must be set in production")
        return self

    @property
    def resolved_research_library(self) -> Path:
        return self.research_library_path or self.seeds_dir / "research" / "library.yaml"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
