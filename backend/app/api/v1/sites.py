"""
Tervo — Sites API router.

Endpoints:
- GET    /sites           → list (paginated, optional client_id filter)
- POST   /sites           → create
- GET    /sites/{id}      → detail
- PATCH  /sites/{id}      → update (partial)
- DELETE /sites/{id}      → delete
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.intervention import InterventionHistoryResponse
from app.schemas.site import (
    SiteCreate,
    SiteListResponse,
    SiteResponse,
    SiteUpdate,
)
from app.services.intervention import InterventionService
from app.services.site import SiteService
from app.schemas.equipment import EquipmentListResponse
from app.services.equipment import EquipmentService

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=SiteListResponse)
async def list_sites(
    page: int = 1,
    page_size: int = 25,
    client_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List sites with pagination and optional client filter."""
    service = SiteService(db)
    return await service.list_sites(page, page_size, client_id)


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new site."""
    service = SiteService(db)
    return await service.create_site(body)


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single site by ID."""
    service = SiteService(db)
    return await service.get_site(site_id)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    body: SiteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing site (partial update)."""
    service = SiteService(db)
    return await service.update_site(site_id, body)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a site."""
    service = SiteService(db)
    await service.delete_site(site_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{site_id}/interventions", response_model=InterventionHistoryResponse)
async def get_site_interventions(
    site_id: int,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated intervention history for a site (404 if the site doesn't exist)."""
    service = InterventionService(db)
    return await service.get_site_interventions(site_id, page, page_size)



@router.get("/{site_id}/equipment", response_model=EquipmentListResponse)
async def get_site_equipment(site_id: int, page: int = Query(1, ge=1),
                             page_size: int = Query(25, ge=1, le=100),
                             current_user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    service = EquipmentService(db)
    await service.check_site(site_id)
    return await service.list_equipment(page, page_size, site_id=site_id)
