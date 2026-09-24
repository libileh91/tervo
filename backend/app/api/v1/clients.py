"""
Tervo — Clients API router.

Endpoints:
- GET    /clients        → list (paginated, searchable)
- POST   /clients        → create
- GET    /clients/{id}   → detail (with interventions_count, last_intervention_date)
- PUT    /clients/{id}   → update
- DELETE /clients/{id}   → delete
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientDetailResponse,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.schemas.site import SiteListResponse
from app.services.client import ClientService
from app.services.site import SiteService

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
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


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new client."""
    service = ClientService(db)
    return await service.create_client(body)


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single client by ID with intervention statistics."""
    service = ClientService(db)
    return await service.get_client(client_id)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    body: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing client."""
    service = ClientService(db)
    return await service.update_client(client_id, body)


@router.get("/{client_id}/sites", response_model=SiteListResponse)
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


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a client."""
    service = ClientService(db)
    await service.delete_client(client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
