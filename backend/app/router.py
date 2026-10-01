"""API composition; legacy routers are replaced wave by wave."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.checklist import router as checklist_router
from app.modules.customers.api import clients_router, sites_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.equipment import router as equipment_router
from app.api.v1.imports import router as imports_router
from app.api.v1.installations import router as installations_router
from app.api.v1.interventions import router as interventions_router
from app.api.v1.materials import router as materials_router
from app.api.v1.photos import router as photos_router
from app.modules.catalog.api import router as products_router
from app.api.v1.reports import router as reports_router
from app.api.v1.reviews import router as reviews_router
from app.modules.sales.api import router as sales_router


api_router = APIRouter()
api_router.include_router(imports_router)
api_router.include_router(auth_router)
api_router.include_router(clients_router)
api_router.include_router(interventions_router)
api_router.include_router(dashboard_router)
api_router.include_router(checklist_router)
api_router.include_router(photos_router)
api_router.include_router(materials_router)
api_router.include_router(reports_router)
api_router.include_router(reviews_router)
api_router.include_router(sites_router)
api_router.include_router(products_router)
api_router.include_router(equipment_router)
api_router.include_router(installations_router)
api_router.include_router(sales_router)
