"""Administrative migration workflow: capture, approve, execute and audit."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import Role, User
from app.schemas.imports import (
    ExecuteImport, ImportBatchListResponse, ImportBatchResponse,
    ImportErrorListResponse, SheetSelection, ValidateImport,
)
from app.services.import_service import ImportService

router = APIRouter(prefix='/admin/import', tags=['admin-import'])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SELECTIONS = TypeAdapter(list[SheetSelection])


async def import_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(403, 'Import réservé aux administrateurs')
    return user


@router.post('/preview', response_model=ImportBatchResponse)
async def preview_import(
    file: UploadFile = File(...),
    source_namespace: str = Form(..., min_length=1, max_length=100),
    selections: str = Form(..., description='Liste JSON des feuilles, natures et options de lecture'),
    user: User = Depends(import_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        manifest = SELECTIONS.validate_json(selections)
    except ValidationError as exc:
        raise HTTPException(422, 'Sélections invalides : liste JSON de feuilles attendue') from exc
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, 'Fichier supérieur à 10 Mio')
    if not file.filename:
        raise HTTPException(422, 'Nom de fichier requis')
    return await ImportService(db).stage(
        content, file.filename, source_namespace,
        [selection.model_dump(mode='json', exclude_none=True) for selection in manifest],
        imported_by=user.id,
    )


@router.post('/validate', response_model=ImportBatchResponse)
async def validate_import(
    body: ValidateImport,
    user: User = Depends(import_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ImportService(db).validate(
        body.batch_id,
        decisions={key:choice.model_dump(mode='json') for key,choice in body.decisions.items()},
        selections=([s.model_dump(mode='json', exclude_none=True) for s in body.selections]
                    if body.selections is not None else None),
        imported_by=user.id,
    )


@router.post('/execute', response_model=ImportBatchResponse)
async def execute_import(
    body: ExecuteImport,
    user: User = Depends(import_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ImportService(db).execute(body.batch_id, body.plan_token)


@router.get('/batches', response_model=ImportBatchListResponse)
async def list_imports(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(import_admin), db: AsyncSession = Depends(get_db),
):
    return await ImportService(db).list_batches(page, page_size)


@router.get('/batches/{batch_id}', response_model=ImportBatchResponse)
async def get_import(
    batch_id: int,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=100),
    user: User = Depends(import_admin), db: AsyncSession = Depends(get_db),
):
    return await ImportService(db).detail(batch_id, page, page_size)


@router.get('/batches/{batch_id}/errors', response_model=ImportErrorListResponse)
async def get_import_errors(
    batch_id: int,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=100),
    user: User = Depends(import_admin), db: AsyncSession = Depends(get_db),
):
    return await ImportService(db).error_page(batch_id, page, page_size)
