"""Physical equipment endpoints, authenticated like the existing field API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.equipment.models import EquipmentStatus
from app.modules.equipment.schemas import EquipmentCreate, EquipmentReplace, EquipmentResponse, EquipmentListResponse
from app.modules.equipment.service import EquipmentService

router = APIRouter(prefix="/equipment", tags=["equipment"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=EquipmentListResponse)
async def list_equipment(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                         site_id: int | None = None, product_id: int | None = None,
                         lifecycle_status: EquipmentStatus | None = None, db: AsyncSession = Depends(get_db)):
    return await EquipmentService(db).list_equipment(page, page_size, site_id=site_id,
                                                      product_id=product_id, lifecycle_status=lifecycle_status)


@router.post("", response_model=EquipmentResponse, status_code=201)
async def create_equipment(body: EquipmentCreate, db: AsyncSession = Depends(get_db)):
    return await EquipmentService(db).create_equipment(body)


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(equipment_id: int, db: AsyncSession = Depends(get_db)):
    return await EquipmentService(db).get_equipment(equipment_id)


@router.post("/{equipment_id}/replace", response_model=EquipmentResponse, status_code=201)
async def replace_equipment(equipment_id: int, body: EquipmentReplace, db: AsyncSession = Depends(get_db)):
    return await EquipmentService(db).replace_equipment(equipment_id, body)
