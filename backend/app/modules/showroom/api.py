"""Authenticated showroom history and presented-product endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import Role, User
from app.modules.showroom.models import FollowUpStatus
from app.modules.showroom.schemas import PresentedProductCreate, VisitCreate, VisitListResponse, VisitResponse, VisitUpdate, utc_naive
from app.modules.showroom.service import ShowroomService

router = APIRouter(prefix="/showroom/visits", tags=["showroom"])


async def showroom_user(user: User = Depends(get_current_user)):
    # Todo later (TD-B013): grant COMMERCIAL/MANAGER appropriate access once these roles exist.
    if user.role != Role.ADMIN:
        raise HTTPException(403, "Showroom réservé aux administrateurs")
    return user


@router.get("", response_model=VisitListResponse)
async def list_visits(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    client_id: int | None = Query(None, gt=0),
    salesperson_id: int | None = Query(None, gt=0),
    visited_from: datetime | None = None,
    visited_to: datetime | None = None,
    follow_up_status: FollowUpStatus | None = None,
    product_id: int | None = Query(None, gt=0),
    user: User = Depends(showroom_user), db: AsyncSession = Depends(get_db),
):
    visited_from = utc_naive(visited_from) if visited_from else None
    visited_to = utc_naive(visited_to) if visited_to else None
    if visited_from and visited_to and visited_from > visited_to:
        raise HTTPException(422, "Intervalle de visite invalide")
    return await ShowroomService(db).list(
        page, page_size, client_id=client_id, salesperson_id=salesperson_id,
        visited_from=visited_from, visited_to=visited_to,
        follow_up_status=follow_up_status, product_id=product_id,
    )


@router.post("", response_model=VisitResponse, status_code=201)
async def create_visit(
    body: VisitCreate, user: User = Depends(showroom_user), db: AsyncSession = Depends(get_db),
):
    return await ShowroomService(db).create(body, user)


@router.get("/{visit_id}", response_model=VisitResponse)
async def get_visit(
    visit_id: int, user: User = Depends(showroom_user), db: AsyncSession = Depends(get_db),
):
    return await ShowroomService(db).get(visit_id)


@router.patch("/{visit_id}", response_model=VisitResponse)
async def update_visit(
    visit_id: int, body: VisitUpdate,
    user: User = Depends(showroom_user), db: AsyncSession = Depends(get_db),
):
    return await ShowroomService(db).update(visit_id, body)


@router.post("/{visit_id}/products", response_model=VisitResponse, status_code=201)
async def add_presented_product(
    visit_id: int, body: PresentedProductCreate,
    user: User = Depends(showroom_user), db: AsyncSession = Depends(get_db),
):
    return await ShowroomService(db).add_product(visit_id, body.product_id)


@router.delete("/{visit_id}/products/{product_id}", status_code=204)
async def remove_presented_product(
    visit_id: int, product_id: int,
    user: User = Depends(showroom_user), db: AsyncSession = Depends(get_db),
):
    await ShowroomService(db).remove_product(visit_id, product_id)
    return Response(status_code=204)
