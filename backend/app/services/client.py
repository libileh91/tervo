"""
Tervo — Client service.

Business logic layer for client operations.
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention import Intervention
from app.repositories.client import ClientRepository
from app.schemas.client import (
    ClientCreate,
    ClientDetailResponse,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)


class ClientService:
    """Encapsulates business rules for client management."""

    def __init__(self, db: AsyncSession):
        self.repo = ClientRepository(db)

    async def list_clients(
        self, page: int = 1, page_size: int = 25, search: str | None = None
    ) -> ClientListResponse:
        """Get a paginated list of clients."""
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 25
        if page_size > 100:
            page_size = 100

        total = await self.repo.count(search)
        clients = await self.repo.list(page, page_size, search)
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return ClientListResponse(
            items=[ClientResponse.model_validate(c) for c in clients],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_client(self, client_id: int) -> ClientDetailResponse:
        """Get a single client by ID with intervention stats (real DB queries)."""
        client = await self._find_or_404(client_id)

        # Query real intervention stats via ORM
        stats_query = select(
            func.count(Intervention.id),
            func.max(Intervention.created_at),
        ).where(Intervention.client_id == client_id)
        result = await self.repo.db.execute(stats_query)
        row = result.fetchone()
        interventions_count = row[0] if row else 0
        last_intervention_date = row[1].date() if row and row[1] else None

        return ClientDetailResponse(
            **{  # type: ignore
                **client.__dict__,
                "interventions_count": interventions_count,
                "last_intervention_date": last_intervention_date,
            }
        )

    async def create_client(self, data: ClientCreate) -> ClientResponse:
        """Create a new client."""
        client = await self.repo.create(data.model_dump())
        return ClientResponse.model_validate(client)

    async def update_client(self, client_id: int, data: ClientUpdate) -> ClientResponse:
        """Update an existing client."""
        client = await self._find_or_404(client_id)
        # Filter out None values (partial update)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        client = await self.repo.update(client, update_data)
        return ClientResponse.model_validate(client)

    async def delete_client(self, client_id: int) -> None:
        """Delete a client."""
        client = await self._find_or_404(client_id)
        await self.repo.delete(client)

    async def _find_or_404(self, client_id: int):
        """Find a client by ID or raise 404."""
        client = await self.repo.get_by_id(client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
        return client
