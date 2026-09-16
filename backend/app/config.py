"""
Tervo — Application configuration.

Uses pydantic-settings to load configuration from environment variables
with sensible defaults for development (SQLite).
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────
    # Default: SQLite stored in the backend directory for dev
    # NOTE: sync scheme for Alembic; async engine adds +aiosqlite at runtime
    DATABASE_URL: str = "sqlite:///./tervo.db"

    # ── Auth / JWT ────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── App metadata ──────────────────────────────────────
    APP_NAME: str = "Tervo"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # ── Uploads (photos) ──────────────────────────────────
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent / "uploads")
    UPLOAD_URL: str = "/uploads"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
