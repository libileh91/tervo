"""
Tervo — Async database engine and session.

Uses aiosqlite for dev (SQLite async), PostgreSQL + asyncpg for prod.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.database_urls import database_url


def _get_async_database_url() -> str:
    """Retain the historical string interface with structurally selected drivers."""
    return database_url(settings.DATABASE_URL, asynchronous=True).render_as_string(
        hide_password=False
    )


engine = create_async_engine(_get_async_database_url(), echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency that yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
