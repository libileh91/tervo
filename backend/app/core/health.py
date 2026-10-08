"""Database readiness probe, independent of application startup and auth."""

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core import database


router = APIRouter()
READINESS_TIMEOUT_SECONDS = 2.0


@router.get("/health/ready", include_in_schema=False)
async def readiness() -> JSONResponse:
    """Check the existing engine without migrations or application data access."""
    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception:
        # Some drivers emit native errors before SQLAlchemy wraps them.
        # Any failed probe is not ready; never expose errors or credentials.
        return JSONResponse(status_code=503, content={"status": "not_ready"})

    # CancelledError intentionally propagates instead of becoming a 503.
    return JSONResponse(status_code=200, content={"status": "ready"})
