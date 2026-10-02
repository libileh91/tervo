"""
Tervo — Dashboard API router.

Endpoints:
- GET /dashboard/summary     → today's summary for the connected technician
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import User
from app.modules.dashboard.schemas import DashboardSummaryResponse
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get today's dashboard summary for the connected technician."""
    service = DashboardService(db)
    return await service.get_dashboard_summary(current_user)
