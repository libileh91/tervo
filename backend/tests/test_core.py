"""
Tests for core database configuration.

Run:
    cd backend/
    uv run pytest tests/test_core.py -v --cov=app --cov-report=term-missing
"""

import pytest


class TestDatabase:
    """Targets uncovered lines in core/database.py."""

    def test_sqlite_url_conversion(self):
        """SQLite sync → async URL conversion."""
        # Monkey-patch settings
        import app.config
        from app.core.database import _get_async_database_url

        original_url = app.config.settings.DATABASE_URL

        app.config.settings.DATABASE_URL = "sqlite:///./resq.db"
        result = _get_async_database_url()
        assert result == "sqlite+aiosqlite:///./resq.db"

        app.config.settings.DATABASE_URL = "sqlite:///./test.db"
        result = _get_async_database_url()
        assert result == "sqlite+aiosqlite:///./test.db"

        # Restore
        app.config.settings.DATABASE_URL = original_url

    def test_postgresql_url_conversion(self):
        """PostgreSQL sync → async URL conversion."""
        import app.config
        from app.core.database import _get_async_database_url

        original_url = app.config.settings.DATABASE_URL

        app.config.settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
        result = _get_async_database_url()
        assert result == "postgresql+asyncpg://user:pass@localhost:5432/db"

        app.config.settings.DATABASE_URL = original_url

    def test_unknown_url_passthrough(self):
        """Unknown scheme → no conversion."""
        import app.config
        from app.core.database import _get_async_database_url

        original_url = app.config.settings.DATABASE_URL

        app.config.settings.DATABASE_URL = "mysql://user:pass@localhost/db"
        result = _get_async_database_url()
        assert result == "mysql://user:pass@localhost/db"

        app.config.settings.DATABASE_URL = original_url


class TestSecurity:
    """Targets uncovered lines in core/security.py."""

    def test_verify_password_wrong(self):
        """Wrong password → False."""
        from app.core.security import get_password_hash, verify_password

        hashed = get_password_hash("correct")
        assert verify_password("wrong", hashed) is False

    def test_verify_password_correct(self):
        """Correct password → True."""
        from app.core.security import get_password_hash, verify_password

        hashed = get_password_hash("correct")
        assert verify_password("correct", hashed) is True

    def test_create_access_token_with_expiry(self):
        """Access token with custom expiry."""
        from jose import jwt

        from app.core.security import create_access_token

        token = create_access_token(user_id=123)
        payload = jwt.decode(
            token, "dev-secret-key-change-in-production", algorithms=["HS256"]
        )
        assert payload["sub"] == "123"
        assert "exp" in payload
        assert "iat" in payload
        assert payload["type"] == "access"
