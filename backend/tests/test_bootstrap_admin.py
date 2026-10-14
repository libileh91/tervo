"""INT-126: only disposable SQLite databases, never the demo seed or VPS."""

import os
import subprocess
import sys
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import bootstrap_admin
from app.bootstrap_admin import BootstrapError, create_admin
from app.core.database import get_db
from app.core.security import verify_password
from app.modules.identity.api import router as auth_router
from app.modules.identity.models import Role, User


@pytest.fixture
async def database(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'bootstrap.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    yield sessions
    await engine.dispose()


async def test_bootstrap_login_replay_and_conflicts(database):
    async with database() as session:
        async with session.begin():
            assert await create_admin(session, "admin1", "admin@example.test", "long-test-secret-1")
        original = (await session.execute(select(User))).scalar_one()
        original_hash = original.hashed_password
        assert original.role == Role.ADMIN and original.is_active
        assert original_hash != "long-test-secret-1"
        assert verify_password("long-test-secret-1", original_hash)
        await session.rollback()

        async with session.begin():
            assert not await create_admin(session, "admin1", "admin@example.test", "different-secret-2")

        for username, email in (
            ("admin1", "other@example.test"),  # username conflict
            ("another", "admin@example.test"),  # email conflict
            ("another", "other@example.test"),  # another admin already present
        ):
            with pytest.raises(BootstrapError, match="conflicting identity"):
                async with session.begin():
                    await create_admin(session, username, email, "different-secret-2")
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 1 and users[0].hashed_password == original_hash

    api = FastAPI()
    api.include_router(auth_router, prefix="/api/v1")

    async def get_test_db():
        async with database() as session:
            yield session

    api.dependency_overrides[get_db] = get_test_db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin1", "password": "long-test-secret-1"},
        )
        assert response.status_code == 200
        assert response.json()["access_token"]


async def test_invalid_input_and_disabled_admin_are_not_repaired(database):
    async with database() as session:
        for username, email, secret in (
            ("x", "valid@example.test", "long-test-secret-1"),
            ("valid", "invalid", "long-test-secret-1"),
            ("valid", "valid@example.test", "short"),
            ("valid", "valid@example.test", "x" * 73),
        ):
            with pytest.raises(BootstrapError):
                async with session.begin():
                    await create_admin(session, username, email, secret)
        assert (await session.execute(select(User))).scalars().all() == []
        await session.rollback()
        async with session.begin():
            assert await create_admin(session, "admin1", "admin@example.test", "long-test-secret-1")
        admin = (await session.execute(select(User))).scalar_one()
        admin.is_active = False
        await session.commit()
        with pytest.raises(BootstrapError, match="unchanged"):
            async with session.begin():
                await create_admin(session, "admin1", "admin@example.test", "different-secret-2")
        assert not (await session.execute(select(User))).scalar_one().is_active


async def test_interactive_command_creates_once_without_echoing_secret(
    database, monkeypatch, capsys
):
    from app.core import database as db_module

    monkeypatch.setattr(db_module, "async_session", database)
    monkeypatch.setattr(bootstrap_admin, "check_database", lambda _: None)
    monkeypatch.setattr(bootstrap_admin.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    prompts = iter(("admin1", "admin@example.test", "admin1", "admin@example.test"))
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))
    secrets = iter(("long-test-secret-1", "long-test-secret-1"))
    monkeypatch.setattr(bootstrap_admin.getpass, "getpass", lambda _: next(secrets))

    assert await bootstrap_admin.run("bootstrap.db") == "Administrator created."
    assert await bootstrap_admin.run("bootstrap.db") == "Administrator already exists; no changes made."
    assert "long-test-secret-1" not in capsys.readouterr().out
    async with database() as session:
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 1 and users[0].role == Role.ADMIN


def test_cli_refuses_default_db_and_noninteractive_secret(tmp_path):
    env = {
        key: value for key, value in os.environ.items()
        if key not in {"DATABASE_URL", "TERVO_DB_NAME", "TERVO_DB_USER", "TERVO_DB_PASSWORD"}
    }
    env["APP_ENV"] = "development"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    database = tmp_path / "untouched.db"
    for explicit in (False, True):
        if explicit:
            env["DATABASE_URL"] = f"sqlite:///{database}"
        result = subprocess.run(
            [sys.executable, "-B", "-m", "app.bootstrap_admin",
             "--confirm-db-name", str(database)],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 1
        assert "Bootstrap refused" in result.stderr
        if not explicit:
            assert "Configure the database explicitly" in result.stderr
        else:
            assert "interactive terminal" in result.stderr
        assert not database.exists()
    mismatch = subprocess.run(
        [sys.executable, "-B", "-m", "app.bootstrap_admin",
         "--confirm-db-name", "different.db"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert mismatch.returncode == 1
    assert "Database name does not match" in mismatch.stderr
    assert not database.exists()


def test_seed_refuses_non_development_before_sql(monkeypatch):
    from app import seed

    monkeypatch.setattr(seed.settings, "APP_ENV", "test")
    with pytest.raises(RuntimeError, match="restricted"):
        import asyncio

        asyncio.run(seed.seed())
