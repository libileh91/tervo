"""
Tervo — ReportExporter.

Generates a PDF report for a completed intervention using WeasyPrint + Jinja2.
"""

import base64
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from app.models.intervention import Intervention


class ReportExporter:
    """Generates a PDF report for a completed intervention."""

    def __init__(self):
        template_path = Path(__file__).resolve().parent / "report_template.html"
        with open(template_path, "r", encoding="utf-8") as f:
            self.template = Template(f.read())

    def _embed_photo(self, file_path: str | None) -> str | None:
        """Read a photo file and return a base64 data URI."""
        if not file_path:
            return None
        path = Path(file_path)
        if not path.exists():
            return None
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        ext = path.suffix.lower()
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(
            ext.lstrip("."), "jpeg"
        )
        return f"data:image/{mime};base64,{b64}"

    def generate_pdf(self, intervention: Intervention) -> bytes:
        """
        Generate a PDF report for an intervention.

        Parameters
        ----------
        intervention : Intervention
            Fully loaded ORM instance (client, technician,
            checklist_items, photos, materials must be eager-loaded).

        Returns
        -------
        bytes
            PDF content as bytes.
        """
        # Group checklist items
        pre_items = []
        post_items = []
        for item in intervention.checklist_items or []:
            entry = {"label": item.label, "checked": item.checked, "note": item.note}
            if item.category == "pre_intervention":
                pre_items.append(entry)
            else:
                post_items.append(entry)

        # Embed photos as base64
        avant_photos = []
        apres_photos = []
        for photo in intervention.photos or []:
            uri = self._embed_photo(photo.file_path)
            if uri:
                if photo.category == "avant":
                    avant_photos.append(uri)
                else:
                    apres_photos.append(uri)

        # Materials
        materials_list = []
        for mat in intervention.materials or []:
            materials_list.append({"name": mat.name, "quantity": mat.quantity})

        # Status label for display
        status_labels = {
            "PLANNED": "Planifiée",
            "IN_PROGRESS": "En cours",
            "COMPLETED": "Terminée",
            "CANCELLED": "Annulée",
        }

        # Client data
        client = intervention.client
        technician = intervention.technician

        ctx = {
            "intervention": {
                "id": intervention.id,
                "title": intervention.title,
                "status": intervention.status.value,
                "status_label": status_labels.get(
                    intervention.status.value, intervention.status.value
                ),
                "scheduled_date": str(intervention.scheduled_date)
                if intervention.scheduled_date
                else "",
                "scheduled_start_time": str(intervention.scheduled_start_time)
                if intervention.scheduled_start_time
                else "",
                "scheduled_end_time": str(intervention.scheduled_end_time)
                if intervention.scheduled_end_time
                else "",
                "observations": intervention.observations or "",
            },
            "client": {
                "full_name": client.full_name if client else "",
                "phone": client.phone if client else "",
                "address": client.address if client else "",
                "postal_code": client.postal_code if client else "",
                "city": client.city if client else "",
            },
            "technician": {
                "full_name": technician.full_name if technician else "",
            },
            "checklist_pre": pre_items,
            "checklist_post": post_items,
            "photos_avant": avant_photos,
            "photos_apres": apres_photos,
            "materials": materials_list,
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

        html = self.template.render(**ctx)
        pdf_bytes = self._html_to_pdf(html)
        return pdf_bytes

    def _html_to_pdf(self, html: str) -> bytes:
        """Convert HTML string to PDF bytes using WeasyPrint."""
        from weasyprint import HTML

        return HTML(string=html).write_pdf()
