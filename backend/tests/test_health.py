"""Readiness tests isolated from the application bootstrap and persistent DBs."""

import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest
from asyncpg.exceptions import InvalidPasswordError
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import health


@pytest.fixture
async def client():
    app = FastAPI()
    app.include_router(health.router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_readiness_sqlite_success_and_hidden_schema(tmp_path, monkeypatch, client):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ready.db'}")
    monkeypatch.setattr(health.database, "engine", engine)
    try:
        response = await client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
        schema = (await client.get("/openapi.json")).json()
        assert "/health/ready" not in schema["paths"]
        async with engine.connect() as connection:
            tables = await connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            assert tables.all() == []
    finally:
        await engine.dispose()


async def test_readiness_failed_connection_is_static(monkeypatch, client):
    class FailingEngine:
        @asynccontextmanager
        async def connect(self):
            # Drivers can fail before SQLAlchemy wraps their exception.
            raise InvalidPasswordError("private-test-value")
            yield  # Preserve the async context manager interface.

    monkeypatch.setattr(health.database, "engine", FailingEngine())
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert response.text == '{"status":"not_ready"}'


@pytest.mark.parametrize("phase", ["connect", "execute"])
async def test_readiness_timeout_is_static(monkeypatch, client, phase):
    cancelled = asyncio.Event()

    async def block():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    class SlowConnection:
        async def execute(self, statement):
            assert str(statement) == "SELECT 1"
            await block()

    class SlowEngine:
        @asynccontextmanager
        async def connect(self):
            if phase == "connect":
                await block()
            yield SlowConnection()

    monkeypatch.setattr(health.database, "engine", SlowEngine())
    monkeypatch.setattr(health, "READINESS_TIMEOUT_SECONDS", 0.02)
    response = await asyncio.wait_for(client.get("/health/ready"), timeout=1)
    assert response.status_code == 503
    assert response.text == '{"status":"not_ready"}'
    assert cancelled.is_set()


async def test_readiness_preserves_request_cancellation(monkeypatch, client):
    started = asyncio.Event()
    cleaned_up = asyncio.Event()

    class WaitingEngine:
        @asynccontextmanager
        async def connect(self):
            started.set()
            try:
                await asyncio.Event().wait()
                yield
            finally:
                cleaned_up.set()

    monkeypatch.setattr(health.database, "engine", WaitingEngine())
    task = asyncio.create_task(client.get("/health/ready"))
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cleaned_up.is_set()
    finally:
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
