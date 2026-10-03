"""Report generation owns the transaction; reads never regenerate a document."""
from datetime import datetime, timezone
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload, undefer

from app.modules.identity.models import Role
from app.modules.interventions.models.intervention import InterventionStatus
from app.modules.interventions.repositories.intervention import InterventionRepository
from app.modules.reports.models import Report, ReportVersion
from app.modules.reports.renderer import ReportExporter
from app.modules.reports.schemas import ReportResponse, ReportVersionResponse


class ReportService:
    def __init__(self, db):
        self.db = db

    async def _intervention(self, intervention_id, user, *, lock=False):
        intervention = await InterventionRepository(self.db).get_by_id(intervention_id, for_update=lock)
        if intervention is None:
            raise HTTPException(404, "Intervention non trouvée")
        if user.role != Role.ADMIN and intervention.technician_id != user.id:
            raise HTTPException(403, "Rapport réservé à l'administrateur ou au technicien assigné")
        return intervention

    async def _report(self, report_id, user, *, lock=False):
        report = await self.db.get(Report, report_id)
        if report is None:
            raise HTTPException(404, "Rapport non trouvé")
        await self._intervention(report.intervention_id, user, lock=lock)
        return report

    async def _loaded(self, report_id):
        return (await self.db.execute(
            select(Report).where(Report.id == report_id).options(selectinload(Report.versions))
            .execution_options(populate_existing=True)
        )).scalar_one()

    async def generate(self, intervention_id, user, request_key=None):
        if request_key is not None and (not request_key.strip() or len(request_key) > 100):
            raise HTTPException(422, "Idempotency-Key doit être non vide et limité à 100 caractères")
        try:
            intervention = await self._intervention(intervention_id, user, lock=True)
            if intervention.status != InterventionStatus.COMPLETED:
                raise HTTPException(400, "L'intervention doit être terminée")
            report = (await self.db.execute(select(Report).where(
                Report.intervention_id == intervention_id
            ))).scalar_one_or_none()
            if report is None:
                report = Report(intervention_id=intervention_id)
                self.db.add(report)
                await self.db.flush()
            if request_key is not None:
                existing = (await self.db.execute(select(ReportVersion).where(
                    ReportVersion.report_id == report.id, ReportVersion.request_key == request_key
                ))).scalar_one_or_none()
                if existing is not None:
                    response = ReportVersionResponse.model_validate(existing)
                    await self.db.commit()
                    return response
            previous = (await self.db.execute(select(ReportVersion.version).where(
                ReportVersion.report_id == report.id
            ).order_by(ReportVersion.version.desc()).limit(1))).scalar_one_or_none()
            pdf = ReportExporter().generate_pdf(intervention)
            if not pdf.startswith(b"%PDF-"):
                raise RuntimeError("Le renderer n'a pas produit un PDF valide")
            version = ReportVersion(
                report_id=report.id, version=(previous or 0) + 1, request_key=request_key,
                pdf=pdf, sha256=sha256(pdf).hexdigest(), size=len(pdf),
                generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                generated_by_id=user.id,
            )
            self.db.add(version)
            await self.db.flush()
            response = ReportVersionResponse.model_validate(version)
            await self.db.commit()
            return response
        except Exception:
            await self.db.rollback()
            raise

    async def get(self, report_id, user):
        await self._report(report_id, user)
        return ReportResponse.model_validate(await self._loaded(report_id))

    async def for_intervention(self, intervention_id, user):
        await self._intervention(intervention_id, user)
        report_id = await self.db.scalar(select(Report.id).where(Report.intervention_id == intervention_id))
        if report_id is None:
            raise HTTPException(404, "Aucun rapport généré ; créer une version explicitement")
        return ReportResponse.model_validate(await self._loaded(report_id))

    async def _version(self, report_id, number):
        version = (await self.db.execute(select(ReportVersion).where(
            ReportVersion.report_id == report_id, ReportVersion.version == number
        ).options(undefer(ReportVersion.pdf)).execution_options(populate_existing=True))).scalar_one_or_none()
        if version is None:
            raise HTTPException(404, "Version non trouvée")
        return version

    @staticmethod
    def _verified_pdf(version):
        if len(version.pdf) != version.size or sha256(version.pdf).hexdigest() != version.sha256:
            raise HTTPException(500, "Intégrité du PDF archivé invalide ; aucun recalcul automatique")
        return version.pdf

    async def file(self, report_id, number, user):
        await self._report(report_id, user)
        version = await self._version(report_id, number)
        return self._verified_pdf(version)

    async def transmit(self, report_id, number, user):
        try:
            await self._report(report_id, user, lock=True)
            version = await self._version(report_id, number)
            self._verified_pdf(version)
            if version.transmitted_at is None:
                version.transmitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
                version.transmitted_by_id = user.id
                await self.db.flush()
            response = ReportVersionResponse.model_validate(version)
            await self.db.commit()
            return response
        except Exception:
            await self.db.rollback()
            raise
