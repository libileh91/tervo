"""
Tervo — Clients and Sites API routers.

Separate routers preserve the historical API composition order.
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.modules.customers.schemas import (
    ClientCreate,
    ClientDetailResponse,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    SiteCreate,
    SiteListResponse,
    SiteResponse,
    SiteUpdate,
)
from app.modules.customers.service import ClientService, SiteService
from app.schemas.intervention import InterventionHistoryResponse
from app.services.intervention import InterventionService
from app.schemas.equipment import EquipmentListResponse
from app.services.equipment import EquipmentService

clients_router = APIRouter(prefix="/clients", tags=["clients"])
sites_router = APIRouter(prefix="/sites", tags=["sites"])


@clients_router.get("", response_model=ClientListResponse)
async def list_clients(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List clients with pagination and optional search."""
    service = ClientService(db)
    return await service.list_clients(page, page_size, search)


@clients_router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new client."""
    service = ClientService(db)
    return await service.create_client(body)


@clients_router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single client by ID with intervention statistics."""
    service = ClientService(db)
    return await service.get_client(client_id)


@clients_router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    body: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing client."""
    service = ClientService(db)
    return await service.update_client(client_id, body)


@clients_router.get("/{client_id}/sites", response_model=SiteListResponse)
async def get_client_sites(
    client_id: int,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated sites for a client (404 if the client doesn't exist)."""
    service = SiteService(db)
    return await service.list_sites_for_client(client_id, page, page_size)


@clients_router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a client."""
    service = ClientService(db)
    await service.delete_client(client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@sites_router.get("", response_model=SiteListResponse)
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


@sites_router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new site."""
    service = SiteService(db)
    return await service.create_site(body)


@sites_router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single site by ID."""
    service = SiteService(db)
    return await service.get_site(site_id)


@sites_router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    body: SiteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing site (partial update)."""
    service = SiteService(db)
    return await service.update_site(site_id, body)


@sites_router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a site."""
    service = SiteService(db)
    await service.delete_site(site_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@sites_router.get("/{site_id}/interventions", response_model=InterventionHistoryResponse)
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



@sites_router.get("/{site_id}/equipment", response_model=EquipmentListResponse)
async def get_site_equipment(site_id: int, page: int = Query(1, ge=1),
                             page_size: int = Query(25, ge=1, le=100),
                             current_user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    service = EquipmentService(db)
    await service.check_site(site_id)
    return await service.list_equipment(page, page_size, site_id=site_id)
