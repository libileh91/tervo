"""R8 reports cutover: frozen R7 HTML, real PDF and SQLite/JWT contracts."""
import ast
import base64
from datetime import date, datetime, time
from decimal import Decimal
import importlib
from importlib.util import resolve_name
import os
import re
from pathlib import Path
import subprocess
import sys
import zlib
from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest
from markupsafe import escape

BACKEND = Path(__file__).resolve().parents[1]
BASELINES = Path(__file__).parent / "fixtures" / "reports"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 28, 14, 35, tzinfo=tz)


def recipe(directory, omissions=False):
    """Fixed business data; existing before/after images and missing image."""
    image = Path(__file__).parent / "test_photo.jpg"
    before, after = directory / "before.jpg", directory / "after.JPG"
    before.write_bytes(image.read_bytes())
    after.write_bytes(image.read_bytes())
    item = NS(
        id=120, title="Maintenance PAC <b>R8</b> & contrôle",
        status=NS(value="COMPLETED"), scheduled_date=date(2026, 9, 28),
        result=None,
        scheduled_start_time=time(9, 15), scheduled_end_time=time(11, 45),
        observations="Pression vérifiée & réglage effectué.\nRetour client : satisfait.",
        site=NS(name="Maison Érable", address="12 rue des Érables",
                postal_code="75012", city="Paris",
                client=NS(full_name="Élodie Martin", phone="0102030405")),
        technician=NS(full_name="Noé Durand"),
        checklist_items=[
            NS(category="pre_intervention", label="Sécurité électrique", result="OK", comment="Consignation"),
            NS(category="pre_intervention", label="Accès dégagé", result=None, comment=None),
            NS(category="post_intervention", label="Essai fonctionnement", result="OK", comment="Conforme"),
            NS(category="legacy", label="Nettoyage", result=None, comment="À revoir"),
        ],
        photos=[NS(usage="BEFORE", file_path=str(before)),
                NS(usage="AFTER", file_path=str(after)),
                NS(usage="BEFORE", file_path=str(directory / "missing.jpg")),
                NS(usage="AFTER", file_path=None)],
        materials=[NS(designation="Joint Ø 20 & raccord", quantity=Decimal("2.000"), unit="pièce"),
                   NS(designation="Fluide", quantity=Decimal("0.500"), unit="kg")],
    )
    if omissions:
        item.site = item.technician = None
        item.scheduled_date = item.scheduled_start_time = item.scheduled_end_time = None
        item.observations = None
        item.checklist_items = item.photos = item.materials = None
        item.status = NS(value="UNKNOWN")
    return item


@pytest.mark.parametrize("omissions", [False, True], ids=["complete", "fallbacks"])
def test_full_html_matches_frozen_r7_with_explicit_int104_delta(tmp_path, omissions):
    renderer = importlib.import_module("app.modules.reports.renderer")
    exporter = renderer.ReportExporter()
    with patch.object(renderer, "datetime", FrozenDatetime):
        with patch.object(exporter, "_html_to_pdf", side_effect=lambda html: html):
            actual = exporter.generate_pdf(recipe(tmp_path, omissions))
    if omissions:
        # Fixture file has a POSIX final newline; R7 Jinja render does not.
        expected = (BASELINES / "fallbacks.html").read_text(encoding="utf-8").removesuffix("\n")
    else:
        # Lossless frozen R7 HTML, including the two full image data URIs.
        expected = zlib.decompress(base64.b64decode(
            (BASELINES / "complete.html.zlib.b64").read_bytes(),
        )).decode("utf-8")
    # The R7 artifacts remain immutable. INT-104 intentionally replaces the
    # boolean/note representation and escapes data, not static report markup.
    for value in (
        "Maintenance PAC <b>R8</b> & contrôle",
        "Pression vérifiée & réglage effectué.\nRetour client : satisfait.",
        "Joint Ø 20 & raccord",
    ):
        expected = expected.replace(value, str(escape(value)))
    expected = expected.replace(
        "<tr><th>Etat</th><th>Point</th><th>Note</th></tr>",
        "<tr><th>Résultat</th><th>Point</th><th>Commentaire</th></tr>",
    ).replace(
        '<td class="check-yes">O</td>', '<td class="check-yes">OK</td>',
    ).replace(
        '<td class="check-no">X</td>', '<td class="check-no">Non réalisé</td>',
    )
    # INT-105 changes only photo grouping markup and the material unit column.
    # Project the frozen section explicitly; never regenerate a historical artifact.
    expected = expected.replace(
        '<h3 class="section-label pre">Avant</h3>',
        '<h3 class="section-label pre" data-usage="BEFORE">Avant</h3>',
    ).replace(
        '<h3 class="section-label post">Apres</h3>',
        '<h3 class="section-label post" data-usage="AFTER">Apres</h3>',
    ).replace('alt="avant"', 'alt="BEFORE"').replace('alt="apres"', 'alt="AFTER"')
    expected = expected.replace(
        '<tr><th style="width:60%;">Materiau</th><th>Quantite</th></tr>',
        '<tr><th style="width:60%;">Materiau</th><th>Quantite</th><th>Unite</th></tr>',
    ).replace(
        '<td>2</td>', '<td>2</td>\n    <td>pièce</td>',
    ).replace('<td>0.5</td>', '<td>0.5</td>\n    <td>kg</td>')
    # Replacing the two conditional groups with one loop removes one template
    # control-line newline between them; all other static markup stays frozen.
    expected = re.sub(r'(alt="BEFORE" />\n  \n</div>\n)\n(\n<h3)', r'\1\2', expected)
    # INT-106 adds exactly one issue line, without inferring historical results.
    expected = re.sub(
        r'(<span>Statut: [^\n]+</span>\n)',
        r'\1      <span>Issue: Non renseigné</span>\n',
        expected,
    )
    assert actual == expected


@pytest.mark.parametrize("result,label", [
    ("RESOLVED", "Résolu"),
    ("PARTIALLY_RESOLVED", "Partiellement résolu"),
    ("UNRESOLVED", "Non résolu"),
    ("PART_NEEDED", "Pièce nécessaire"),
    ("QUOTE_NEEDED", "Devis nécessaire"),
    ("RESCHEDULE", "À replanifier"),
    (None, "Non renseigné"),
])
def test_completion_issue_is_distinct_from_status(tmp_path, result, label):
    renderer = importlib.import_module("app.modules.reports.renderer")
    exporter = renderer.ReportExporter()
    intervention = recipe(tmp_path)
    intervention.result = result
    with patch.object(exporter, "_html_to_pdf", side_effect=lambda html: html):
        actual = exporter.generate_pdf(intervention)
    assert f"<span>Issue: {label}</span>" in actual
    assert "<span>Statut: Terminée</span>" in actual


def test_completion_issue_is_html_escaped(tmp_path):
    renderer = importlib.import_module("app.modules.reports.renderer")
    exporter = renderer.ReportExporter()
    intervention = recipe(tmp_path)
    intervention.result = "<script>issue & résultat</script>"
    with patch.object(exporter, "_html_to_pdf", side_effect=lambda html: html):
        actual = exporter.generate_pdf(intervention)
    assert str(escape(intervention.result)) in actual
    assert intervention.result not in actual


def test_checklist_result_and_comment_are_visible_but_never_html(tmp_path):
    renderer = importlib.import_module("app.modules.reports.renderer")
    exporter = renderer.ReportExporter()
    intervention = recipe(tmp_path)
    result = "<script>alert('result')</script>"
    comment = '<img src="https://invalid.example/tracker">'
    intervention.checklist_items[0].result = result
    intervention.checklist_items[0].comment = comment
    with patch.object(exporter, "_html_to_pdf", side_effect=lambda html: html):
        actual = exporter.generate_pdf(intervention)
    assert str(escape(result)) in actual
    assert str(escape(comment)) in actual
    assert result not in actual
    assert comment not in actual


def test_all_photo_usages_material_units_and_numeric_display(tmp_path):
    renderer = importlib.import_module("app.modules.reports.renderer")
    exporter = renderer.ReportExporter()
    intervention = recipe(tmp_path)
    usages = ("BEFORE", "AFTER", "EQUIPMENT", "ANOMALY", "PART", "OTHER")
    intervention.photos = [NS(usage=usage, file_path=intervention.photos[0].file_path) for usage in usages]
    intervention.materials += [
        NS(designation="<script>material</script>", quantity=None, unit=None),
        NS(designation="Précision", quantity=Decimal("0.001"), unit="<b>kg</b>"),
    ]
    with patch.object(exporter, "_html_to_pdf", side_effect=lambda html: html):
        actual = exporter.generate_pdf(intervention)
    assert actual.count('<div class="photos-grid">') == 6
    for usage in usages:
        assert actual.count(f'data-usage="{usage}"') == 1
        assert actual.count(f'alt="{usage}"') == 1
    assert "<td>2</td>" in actual and "<td>0.5</td>" in actual
    assert "<td>0.001</td>" in actual and "<td>2.000</td>" not in actual
    assert "<td>pièce</td>" in actual and "<td>kg</td>" in actual
    assert "<td>---</td>" in actual
    assert str(escape("<script>material</script>")) in actual
    assert str(escape("<b>kg</b>")) in actual
    assert "<script>material</script>" not in actual


def run_isolated(tmp_path, source):
    env = {key: value for key, value in os.environ.items() if not key.startswith("TERVO_")}
    env.update(
        PYTHONPATH=str(BACKEND),
        DATABASE_URL="sqlite:///./tervo.db",
        UPLOAD_DIR=str(tmp_path / "uploads"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run([sys.executable, "-c", source], cwd=tmp_path,
                            env=env, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


def test_real_pdf_without_legacy_cwd(tmp_path):
    run_isolated(tmp_path, """
from pathlib import Path
from tests.test_reports_module import recipe, FrozenDatetime
from unittest.mock import patch
from app.modules.reports import renderer
assert not Path("app/exporters").exists()
assert not Path("app/api/v1/reports.py").exists()
with patch.object(renderer, "datetime", FrozenDatetime):
    pdf = renderer.ReportExporter().generate_pdf(recipe(Path.cwd()))
assert pdf.startswith(b"%PDF-")
assert len(pdf) > 1000
assert b"%%EOF" in pdf[-1024:]
""")


def test_reports_init_is_pure_without_sql(tmp_path):
    run_isolated(tmp_path, """
import sys
from importlib.abc import MetaPathFinder
class NoSQL(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"sqlalchemy", "asyncpg", "aiosqlite"}:
            raise AssertionError(fullname)
sys.meta_path.insert(0, NoSQL())
import app.modules.reports
assert "app.modules.reports.renderer" not in sys.modules
assert "app.modules.reports.api" not in sys.modules
""")


def test_cutover_layout_and_ast():
    module = BACKEND / "app/modules/reports"
    assert {p.name for p in module.iterdir() if p.name != "__pycache__"} == {
        "__init__.py", "api.py", "renderer.py", "templates",
    }
    init = ast.parse((module / "__init__.py").read_text(encoding="utf-8"))
    assert len(init.body) == 1
    assert isinstance(init.body[0], ast.Expr)
    assert isinstance(init.body[0].value, ast.Constant)
    assert isinstance(init.body[0].value.value, str)
    assert {p.name for p in (module / "templates").iterdir()} == {"report_template.html"}
    for old in ("app/api/v1/reports.py", "app/exporters/report.py",
                "app/exporters/report_template.html"):
        assert not (BACKEND / old).exists()
    retired = {"app.api.v1.reports", "app.exporters.report"}
    for root in (BACKEND / "app", BACKEND / "tests"):
        for path in root.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if node.level:
                        module = resolve_name(
                            "." * node.level + module,
                            ".".join(path.parent.relative_to(BACKEND).parts),
                        )
                    imports = [module, *(module + "." + alias.name for alias in node.names)]
                elif isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                else:
                    continue
                assert not any(name == old or name.startswith(old + ".")
                               for name in imports for old in retired), path


def test_report_route_composed_once():
    from fastapi import routing
    from app.router import api_router
    from app.modules.reports.api import download_report, router
    iterator = getattr(routing, "_iter_routes_with_context", None)
    def report_routes(container):
        routes = iterator(container.routes) if iterator else ((r, None) for r in container.routes)
        return [(r, c if c is not None else r) for r, c in routes
                if getattr(r, "endpoint", None) is download_report]
    for container in (router, api_router):
        found = report_routes(container)
        assert len(found) == 1
        assert found[0][1].path == "/interventions/{intervention_id}/report/download"
        assert found[0][1].methods == {"GET"}


@pytest.fixture
async def context(tmp_path, monkeypatch):
    # Reuse the established JWT/users/schema fixture, forcibly SQLite-only.
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context
    generator = installation_context.__wrapped__(tmp_path)
    try:
        yield await anext(generator)
    finally:
        await generator.aclose()


async def test_report_api_real_jwt_and_pdf(context):
    from sqlalchemy import select
    from app.modules.identity.models import User
    from app.modules.interventions.models.intervention import Intervention, InterventionStatus
    from app.modules.reports.api import router
    assert router is not None
    ac, sessions, (_, site, _, _), tokens = context
    async with sessions() as db:
        technician = await db.scalar(select(User).where(User.username == "technician"))
        completed = Intervention(site_id=site, technician_id=technician.id,
                                 title="Rapport R8", scheduled_date=date(2026, 9, 28),
                                 status=InterventionStatus.COMPLETED)
        planned = Intervention(site_id=site, technician_id=technician.id,
                               title="Planifiée R8", scheduled_date=date(2026, 9, 28),
                               status=InterventionStatus.PLANNED)
        other = User(username="other-r8", email="other-r8@test.fr",
                     hashed_password="unused", role=technician.role)
        db.add_all([completed, planned, other])
        await db.commit()
        completed_id, planned_id, other_id = completed.id, planned.id, other.id
    url = f"/api/v1/interventions/{completed_id}/report/download"
    response = await ac.get(url)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == f'attachment; filename="rapport-intervention-{completed_id}.pdf"'
    assert response.content.startswith(b"%PDF-") and b"%%EOF" in response.content[-1024:]
    assert (await ac.get(f"/api/v1/interventions/{planned_id}/report/download")).status_code == 400
    from app.core.security import create_access_token
    for headers in (tokens["admin"], {"Authorization": "Bearer " + create_access_token(other_id)}):
        assert (await ac.get(url, headers=headers)).status_code == 403
    assert (await ac.get("/api/v1/interventions/999999/report/download")).status_code == 404
    # Override AsyncClient's technician default, rather than accidentally retaining it.
    for authorization in (None, "Bearer invalid.jwt"):
        request = ac.build_request("GET", url)
        request.headers.pop("authorization", None)
        if authorization:
            request.headers["authorization"] = authorization
        assert (await ac.send(request)).status_code in (401, 403)
