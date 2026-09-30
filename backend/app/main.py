"""
Tervo — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.database import engine
from app.model_registry import load_models


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

# ── Models and routers ────────────────────────────────────
load_models()

from app.router import api_router

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# ── Static files (uploaded photos) ────────────────────────
# Le dossier est gitignoré : il est donc absent d'un checkout neuf (CI,
# conteneur). On le crée explicitement — sinon StaticFiles lève une
# RuntimeError au chargement du module, avant même le démarrage de l'app.
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

app.mount(
    settings.UPLOAD_URL,
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)
