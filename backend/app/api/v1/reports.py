"""
ResQ — Reports API router.

Endpoints:
- GET /jobs/{job_id}/report/download → PDF report
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.exporters.report import ReportExporter
from app.models.user import User
from app.repositories.job import JobRepository

router = APIRouter(prefix="/jobs", tags=["reports"])


@router.get("/{job_id}/report/download")
async def download_report(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the PDF report for a completed job."""
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trouvé",
        )

    if job.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce job",
        )

    if job.status != "terminé":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le job doit être terminé pour générer le rapport.",
        )

    exporter = ReportExporter()
    pdf_bytes = exporter.generate_pdf(job)

    filename = f"rapport-intervention-{job_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
