"""Authenticated catalogue API; writes currently reserved to administrators."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import Role, User
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["products"])


async def catalogue_editor(user: User = Depends(get_current_user)):
    # Todo later (TD-B013): allow MANAGER/COMMERCIAL when these roles exist.
    if user.role != Role.ADMIN:
        raise HTTPException(403, "Gestion du catalogue réservée aux administrateurs")
    return user


@router.get("", response_model=ProductListResponse)
async def list_products(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                        limit: int | None = Query(None, ge=1, le=100),
                        search: str | None = None, brand: str | None = None,
                        category: str | None = None, active: bool | None = None,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ProductService(db).list_products(page, limit if limit is not None else page_size,
                                                 search=search, brand=brand, category=category, active=active)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(body: ProductCreate, user: User = Depends(catalogue_editor),
                         db: AsyncSession = Depends(get_db)):
    return await ProductService(db).create_product(body)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    return await ProductService(db).get_product(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, body: ProductUpdate, user: User = Depends(catalogue_editor),
                         db: AsyncSession = Depends(get_db)):
    return await ProductService(db).update_product(product_id, body)


@router.post("/{product_id}/deactivate", response_model=ProductResponse)
async def deactivate_product(product_id: int, user: User = Depends(catalogue_editor),
                             db: AsyncSession = Depends(get_db)):
    return await ProductService(db).deactivate_product(product_id)
