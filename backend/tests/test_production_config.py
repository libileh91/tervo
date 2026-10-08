"""Small production configuration contract; no persistent DB access."""

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.config import Settings
from app.core.database_urls import database_url


def production(**overrides):
    values = {
        "APP_ENV": "production",
        "SECRET_KEY": "test-only-not-a-real-key-" + "x" * 40,
        "CORS_ORIGINS": ["https://tervoapp.com/"],
        "TERVO_DB_NAME": "test_db",
        "TERVO_DB_USER": "test_user",
        "TERVO_DB_PASSWORD": "test-only-p@ss#$/%:word",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_components_and_sync_async_drivers_preserve_password():
    settings = production()
    parsed = make_url(settings.DATABASE_URL)
    assert parsed.password == "test-only-p@ss#$/%:word"
    assert settings.CORS_ORIGINS == ["https://tervoapp.com"]
    for asynchronous, driver in (
        (True, "postgresql+asyncpg"),
        (False, "postgresql+psycopg2"),
    ):
        url = database_url(settings.DATABASE_URL, asynchronous=asynchronous)
        assert url.drivername == driver
        assert url.password == parsed.password
        assert make_url(url.render_as_string(hide_password=False)).password == parsed.password
    assert Settings.model_validate(settings).DATABASE_URL == settings.DATABASE_URL


def test_production_rejects_unsafe_or_ambiguous_configuration_without_values():
    cases = [
        {"SECRET_KEY": "private-test-value"},
        {"TERVO_DB_PASSWORD": ""},
        {"TERVO_DB_PASSWORD": "weak"},
        {"CORS_ORIGINS": ["*"]},
        {"CORS_ORIGINS": ["http://tervoapp.com"]},
        {"CORS_ORIGINS": ["https://tervoapp.com/path"]},
        {"DATABASE_URL": "postgresql://test_user:private-test-value@postgres/test_db"},
    ]
    for overrides in cases:
        with pytest.raises(ValidationError) as error:
            production(**overrides)
        assert "private-test-value" not in str(error.value)
        assert "test-only-p@ss" not in str(error.value)


def test_production_explicit_url_requires_postgres_and_cors(monkeypatch):
    for name in ("TERVO_DB_NAME", "TERVO_DB_USER", "TERVO_DB_PASSWORD", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    values = {
        "APP_ENV": "production",
        "SECRET_KEY": "test-only-not-a-real-key-" + "x" * 40,
        "CORS_ORIGINS": ["https://tervoapp.com"],
        "DATABASE_URL": "postgresql+asyncpg://test_user:test-only-not-real@postgres/test_db",
    }
    settings = Settings(_env_file=None, **values)
    assert database_url(settings.DATABASE_URL, asynchronous=False).drivername == "postgresql+psycopg2"
    values["DATABASE_URL"] = "sqlite:///must-not-be-opened.db"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
    values["DATABASE_URL"] = "postgresql://test_user:test-only-not-real@postgres/test_db"
    values.pop("CORS_ORIGINS")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_shared_dotenv_can_load_quoted_reserved_password(tmp_path, monkeypatch):
    for name in (
        "APP_ENV", "DATABASE_URL", "SECRET_KEY", "TERVO_DB_NAME",
        "TERVO_DB_USER", "TERVO_DB_PASSWORD", "CORS_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "private.env"
    path.write_text(
        "APP_ENV=production\n"
        "TERVO_DB_NAME=test_db\n"
        "TERVO_DB_USER=test_user\n"
        "TERVO_DB_PASSWORD='test-only-p@ss#$/%:word'\n"
        f"SECRET_KEY={'x' * 64}\n"
        "CORS_ORIGINS='[\"https://tervoapp.com\"]'\n"
        "VITE_API_BASE_URL=https://api.tervoapp.com/api/v1\n"
    )
    path.chmod(0o600)
    settings = Settings(_env_file=path)
    assert make_url(settings.DATABASE_URL).password == "test-only-p@ss#$/%:word"
