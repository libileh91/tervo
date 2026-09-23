"""
Tervo — Reports API router.

Endpoints:
- GET /interventions/{intervention_id}/report/download → PDF report
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.exporters.report import ReportExporter
from app.models.intervention import InterventionStatus
from app.models.user import User
from app.repositories.intervention import InterventionRepository

router = APIRouter(prefix="/interventions", tags=["reports"])


@router.get("/{intervention_id}/report/download")
async def download_report(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the PDF report for a completed intervention."""
    repo = InterventionRepository(db)
    intervention = await repo.get_by_id(intervention_id)

    if intervention is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intervention non trouvée",
        )

    if intervention.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à cette intervention",
        )

    if intervention.status != InterventionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'intervention doit être terminée pour générer le rapport.",
        )

    exporter = ReportExporter()
    pdf_bytes = exporter.generate_pdf(intervention)

    filename = f"rapport-intervention-{intervention_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
