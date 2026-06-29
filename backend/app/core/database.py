"""
ResQ — Async database engine and session.

Uses aiosqlite for dev (SQLite async), PostgreSQL + asyncpg for prod.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _get_async_database_url() -> str:
    """Convert sync DATABASE_URL to async by injecting the async driver."""
    if settings.DATABASE_URL.startswith("sqlite"):
        return settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if settings.DATABASE_URL.startswith("postgresql"):
        return settings.DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    return settings.DATABASE_URL


engine = create_async_engine(_get_async_database_url(), echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency that yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
