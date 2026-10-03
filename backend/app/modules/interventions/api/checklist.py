"""Checklist definitions, immutable snapshots and technician completion."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import Role, User
from app.modules.interventions.models.checklist import InterventionChecklist
from app.modules.interventions.models.intervention import InterventionStatus
from app.modules.interventions.repositories.intervention import InterventionRepository
from app.modules.interventions.schemas.checklist import (
    ChecklistTemplateCreate, ChecklistTemplateUpdate, ChecklistTemplateResponse,
    InterventionChecklistResponse,
)
from app.modules.interventions.schemas.intervention import ChecklistItemRef, ChecklistItemUpdate
from app.modules.interventions.services.checklist import ChecklistService

router = APIRouter(tags=["checklist"])


async def require_admin(user: User = Depends(get_current_user)):
    if user.role != Role.ADMIN:
        raise HTTPException(403, "Accès administrateur requis")
    return user


@router.get("/checklist-templates", response_model=list[ChecklistTemplateResponse])
async def list_templates(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ChecklistService(db).list_templates()


@router.post("/checklist-templates", response_model=ChecklistTemplateResponse, status_code=201)
async def create_template(body: ChecklistTemplateCreate, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await ChecklistService(db).create_template(body)


@router.patch("/checklist-templates/{template_id}", response_model=ChecklistTemplateResponse)
async def update_template(template_id: int, body: ChecklistTemplateUpdate, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await ChecklistService(db).update_template(template_id, body)


@router.get("/interventions/{intervention_id}/checklist", response_model=InterventionChecklistResponse)
async def get_checklist(intervention_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if await InterventionRepository(db).get_by_id(intervention_id) is None:
        raise HTTPException(404, "Intervention non trouvée")
    return await ChecklistService(db).get_snapshot(intervention_id)


@router.patch("/checklist-items/{item_id}", response_model=ChecklistItemRef)
async def update_item(item_id: int, body: ChecklistItemUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ChecklistService(db)
    item = await service.repo.get_item(item_id)
    if item is None:
        raise HTTPException(404, "Item de checklist non trouvé")
    snapshot = await db.get(InterventionChecklist, item.intervention_checklist_id)
    intervention = await InterventionRepository(db).get_by_id(snapshot.intervention_id, for_update=True)
    # The item may have been read before waiting for the intervention lock.
    await db.refresh(item)
    if intervention.technician_id != user.id:
        raise HTTPException(403, "Vous n'êtes pas assigné à cette intervention")
    if intervention.status not in (InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS):
        raise HTTPException(422, "La checklist est verrouillée pour ce statut")
    return await service.update_item(item_id, body.model_dump(exclude_unset=True))
