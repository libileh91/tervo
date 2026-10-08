"""
Tervo — Application configuration.

Uses pydantic-settings to load configuration from environment variables
with sensible defaults for development (SQLite).
"""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    APP_ENV: Literal["development", "production", "test"] = "development"

    # ── Database ──────────────────────────────────────────
    # Default: SQLite stored in the backend directory for dev
    # NOTE: sync scheme for Alembic; async engine adds +aiosqlite at runtime
    DATABASE_URL: str = Field(default="sqlite:///./tervo.db", repr=False)
    # Production Compose passes components, never an interpolated URI.
    TERVO_DB_HOST: str = "postgres"
    TERVO_DB_PORT: int = Field(default=5432, ge=1, le=65535)
    TERVO_DB_NAME: str | None = None
    TERVO_DB_USER: str | None = None
    TERVO_DB_PASSWORD: SecretStr | None = None

    # ── Auth / JWT ────────────────────────────────────────
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", repr=False)
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

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "hide_input_in_errors": True,
    }

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        normalized = []
        for origin in origins:
            parts = urlsplit(origin)
            port = parts.port  # Reject malformed ports as well as URL paths.
            if (
                parts.scheme not in {"http", "https"}
                or not parts.hostname
                or any(character.isspace() for character in origin)
                or parts.username is not None
                or parts.password is not None
                or parts.path not in {"", "/"}
                or parts.query
                or parts.fragment
            ):
                raise ValueError("CORS_ORIGINS must contain HTTP(S) origins only")
            host = parts.hostname.lower()
            authority = f"[{host}]" if ":" in host else host
            if port is not None and (parts.scheme, port) not in {("https", 443), ("http", 80)}:
                authority += f":{port}"
            normalized.append(f"{parts.scheme}://{authority}")
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_production(self):
        if self.APP_ENV != "production":
            return self
        if (
            len(self.SECRET_KEY) < 32
            or self.SECRET_KEY in {
                "dev-secret-key-change-in-production",
                "change-me-in-production",
            }
        ):
            raise ValueError("Production requires an explicit strong SECRET_KEY")
        if "CORS_ORIGINS" not in self.model_fields_set or not self.CORS_ORIGINS:
            raise ValueError("Production requires explicit CORS_ORIGINS")
        if any(urlsplit(origin).scheme != "https" for origin in self.CORS_ORIGINS):
            raise ValueError("Production CORS origins must use HTTPS")

        components = (self.TERVO_DB_NAME, self.TERVO_DB_USER, self.TERVO_DB_PASSWORD)
        if any(value is not None for value in components):
            if "DATABASE_URL" in self.model_fields_set:
                raise ValueError("Choose DB components or DATABASE_URL, not both")
            if not all(components) or len(self.TERVO_DB_PASSWORD.get_secret_value()) < 16:
                raise ValueError("Production requires DB name/user and a password of at least 16 characters")
            url = URL.create(
                "postgresql",
                username=self.TERVO_DB_USER,
                password=self.TERVO_DB_PASSWORD.get_secret_value(),
                host=self.TERVO_DB_HOST,
                port=self.TERVO_DB_PORT,
                database=self.TERVO_DB_NAME,
            )
            # Derived value is not an explicitly supplied second DB source.
            object.__setattr__(self, "DATABASE_URL", url.render_as_string(hide_password=False))
        else:
            if "DATABASE_URL" not in self.model_fields_set:
                raise ValueError("Production requires explicit PostgreSQL configuration")
            try:
                url = make_url(self.DATABASE_URL)
            except Exception:
                raise ValueError("Invalid production DATABASE_URL") from None
            if (
                url.get_backend_name() != "postgresql"
                or not url.username
                or not url.password
                or len(url.password) < 16
                or not url.host
                or not url.database
            ):
                raise ValueError("Production requires authenticated PostgreSQL")
        return self


settings = Settings()
