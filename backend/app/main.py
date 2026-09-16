"""
Tervo — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup/shutdown."""
    # Startup: database engine is created on import
    yield
    # Shutdown: dispose of the engine
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────
from app.api.v1.auth import router as auth_router  # noqa: E402
from app.api.v1.checklist import router as checklist_router  # noqa: E402
from app.api.v1.clients import router as clients_router  # noqa: E402
from app.api.v1.dashboard import router as dashboard_router  # noqa: E402
from app.api.v1.jobs import router as jobs_router  # noqa: E402
from app.api.v1.materials import router as materials_router  # noqa: E402
from app.api.v1.photos import router as photos_router  # noqa: E402
from app.api.v1.reports import router as reports_router  # noqa: E402
from app.api.v1.reviews import router as reviews_router  # noqa: E402

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(clients_router, prefix=settings.API_V1_PREFIX)
app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(checklist_router, prefix=settings.API_V1_PREFIX)
app.include_router(photos_router, prefix=settings.API_V1_PREFIX)
app.include_router(materials_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
app.include_router(reviews_router, prefix=settings.API_V1_PREFIX)

# ── Static files (uploaded photos) ────────────────────────
app.mount(
    settings.UPLOAD_URL,
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)
