"""Autonomous installations, authenticated like the existing field endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.installations.models import InstallationStatus
from app.modules.installations.schemas import (
    InstallationCreate, InstallationComplete, InstallationResponse, InstallationListResponse,
)
from app.modules.installations.service import InstallationService

router = APIRouter(prefix="/installations", tags=["installations"],
                   dependencies=[Depends(get_current_user)])


@router.get("", response_model=InstallationListResponse)
async def list_installations(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
        site_id: int | None = Query(None, gt=0), status: InstallationStatus | None = None,
        db: AsyncSession = Depends(get_db)):
    return await InstallationService(db).list_installations(page, page_size, site_id=site_id, status=status)


@router.post("", response_model=InstallationResponse, status_code=201)
async def create_installation(body: InstallationCreate, db: AsyncSession = Depends(get_db)):
    return await InstallationService(db).create_installation(body)


@router.get("/{installation_id}", response_model=InstallationResponse)
async def get_installation(installation_id: int, db: AsyncSession = Depends(get_db)):
    return await InstallationService(db).get_installation(installation_id)


@router.post("/{installation_id}/start", response_model=InstallationResponse)
async def start_installation(installation_id: int, db: AsyncSession = Depends(get_db)):
    return await InstallationService(db).transition(installation_id, "start")


@router.post("/{installation_id}/cancel", response_model=InstallationResponse)
async def cancel_installation(installation_id: int, db: AsyncSession = Depends(get_db)):
    return await InstallationService(db).transition(installation_id, "cancel")


@router.post("/{installation_id}/complete", response_model=InstallationResponse)
async def complete_installation(installation_id: int, body: InstallationComplete,
                                db: AsyncSession = Depends(get_db)):
    return await InstallationService(db).complete(installation_id, body)
