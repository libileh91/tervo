"""Private reports and manual confirmation of external transmission."""
from fastapi import APIRouter, Depends, Header, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import User
from app.modules.reports.schemas import ReportResponse, ReportVersionResponse, TransmissionConfirmation
from app.modules.reports.service import ReportService

router = APIRouter(tags=["reports"])
PDF_RESPONSE = {200: {"description": "PDF privé archivé", "content": {
    "application/pdf": {"schema": {"type": "string", "format": "binary"}}
}}}


@router.post("/interventions/{intervention_id}/reports", response_model=ReportVersionResponse, status_code=201)
async def generate_report(intervention_id: int, user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db),
                          request_key: str | None = Header(None, alias="Idempotency-Key")):
    return await ReportService(db).generate(intervention_id, user, request_key)


@router.get("/interventions/{intervention_id}/reports", response_model=ReportResponse)
async def intervention_report(intervention_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReportService(db).for_intervention(intervention_id, user)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReportService(db).get(report_id, user)


@router.get("/reports/{report_id}/versions/{v}", response_class=Response, responses=PDF_RESPONSE)
async def version_file(report_id: int, v: int = Path(gt=0), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    content = await ReportService(db).file(report_id, v, user)
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="rapport-{report_id}-v{v}.pdf"',
        "Cache-Control": "private, no-store",
    })


@router.post("/reports/{report_id}/versions/{v}/transmit", response_model=ReportVersionResponse)
async def confirm_transmission(report_id: int, body: TransmissionConfirmation, v: int = Path(gt=0),
                               user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ReportService(db).transmit(report_id, v, user)


@router.get("/interventions/{intervention_id}/report/download", response_class=Response, responses=PDF_RESPONSE)
async def download_report(intervention_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ReportService(db)
    report = await service.for_intervention(intervention_id, current_user)
    content = await service.file(report.id, report.versions[-1].version, current_user)
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="rapport-intervention-{intervention_id}.pdf"',
        "Cache-Control": "private, no-store",
    })
