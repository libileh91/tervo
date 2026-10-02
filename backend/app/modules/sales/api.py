"""Commercial sales API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.sales.models import SaleStatus
from app.modules.identity.models import User
from app.modules.sales.schemas import SaleCreate, SaleResponse
from app.modules.sales.service import SaleService

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleResponse, status_code=201)
async def create_sale(body: SaleCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await SaleService(db).create(body)


@router.post("/{sale_id}/confirm", response_model=SaleResponse)
async def confirm_sale(sale_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await SaleService(db).transition(sale_id, SaleStatus.CONFIRMED)


@router.post("/{sale_id}/cancel", response_model=SaleResponse)
async def cancel_sale(sale_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await SaleService(db).transition(sale_id, SaleStatus.CANCELLED)
