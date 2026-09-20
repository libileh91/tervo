"""
Tervo — Structure du package `importers` (INT-71).

Ce fichier verrouille le **contrat structurel** du pipeline d'import :

- le package s'importe seul — ni FastAPI, ni SQLAlchemy, ni modèles ;
- les objets de valeur (mapping, aperçu, rapport) sont sérialisables ;
- les seuils de décision et la taille de batch sont des constantes nommées.

Les tests **métier** (normalisation, matching, validation) relèvent d'INT-80.

Run:
    cd backend/
    uv run pytest tests/test_importers_structure.py -v
"""

from __future__ import annotations

import ast
import json
import pkgutil
from pathlib import Path
from typing import Any, cast

from app import importers
from app.importers import (
    AUTO_MATCH_THRESHOLD,
    DEFAULT_BATCH_SIZE,
    HUMAN_REVIEW_THRESHOLD,
    BatchResult,
    ColumnMapping,
    ErrorStatus,
    ImportReport,
    ImportStatus,
    InternalField,
    MatchCandidate,
    MatchDecision,
    MatchWeights,
    MatchZone,
    RowError,
    SheetPreview,
    ValidationResult,
)
from app.services.import_service import ImportService

# ── Helpers ────────────────────────────────────────────────

#: Racines de modules interdites dans `app/importers` : le pipeline doit
#: rester testable sans application web ni base de données.
FORBIDDEN_ROOTS: frozenset[str] = frozenset({"fastapi", "sqlalchemy", "alembic"})

#: Sous-packages de `app` interdits : le pipeline ne connaît que lui-même.
FORBIDDEN_APP_PREFIXES: tuple[str, ...] = (
    "app.api",
    "app.core",
    "app.models",
    "app.repositories",
    "app.services",
    "app.schemas",
)


def _package_dir() -> Path:
    """Répertoire du package `app.importers`."""
    return Path(cast(str, importers.__file__)).parent


def _importer_modules() -> list[tuple[str, Path]]:
    """Liste `(nom, chemin)` des modules du package `importers`."""
    package_dir = _package_dir()
    modules = [("__init__", package_dir / "__init__.py")]
    modules += [
        (info.name, package_dir / f"{info.name}.py")
        for info in pkgutil.iter_modules([str(package_dir)])
    ]
    return modules


def _imported_modules(source_path: Path) -> set[str]:
    """Modules importés par un fichier, via l'AST (ignore les docstrings)."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _json(payload: dict[str, object]) -> Any:
    """Sérialise puis relit un payload : prouve qu'il passe réellement en JSON."""
    return json.loads(json.dumps(payload))


# ── Contrat du package ─────────────────────────────────────


class TestPackageContract:
    """Le package expose son API et reste indépendant du framework."""

    def test_package_exposes_its_public_api(self):
        """Tout le vocabulaire du pipeline est exporté par `__all__`."""
        expected = {
            # Lecture
            "ExcelReader",
            "SheetPreview",
            # Détection de format
            "FormatDetector",
            "ColumnMapping",
            "InternalField",
            "ImportKind",
            # Normalisation
            "Normalizer",
            # Validation
            "Validator",
            "ValidationResult",
            "RowError",
            "ErrorStatus",
            # Rapprochement
            "ClientMatcher",
            "MatchDecision",
            "MatchCandidate",
            "MatchZone",
            "MatchWeights",
            "AUTO_MATCH_THRESHOLD",
            "HUMAN_REVIEW_THRESHOLD",
            # Rapport
            "ImportReport",
            "ImportStatus",
            "BatchResult",
            "DEFAULT_BATCH_SIZE",
        }
        assert expected <= set(importers.__all__)

    def test_importers_ignore_framework_and_database(self):
        """Aucun module n'importe FastAPI, SQLAlchemy ni Alembic."""
        offenders = {
            name: sorted(_imported_modules(path) & FORBIDDEN_ROOTS)
            for name, path in _importer_modules()
        }
        assert {name: found for name, found in offenders.items() if found} == {}

    def test_importers_ignore_app_layers(self):
        """Le pipeline ne dépend ni des modèles, ni des repositories, ni de l'API."""
        offenders: dict[str, list[str]] = {}
        for name, path in _importer_modules():
            forbidden = [
                module
                for module in _imported_modules(path)
                if module.startswith(FORBIDDEN_APP_PREFIXES)
            ]
            if forbidden:
                offenders[name] = sorted(forbidden)
        assert offenders == {}

    def test_importers_only_depend_on_their_own_layers(self):
        """Les imports `app.*` se limitent au package `importers`."""
        for name, path in _importer_modules():
            for module in _imported_modules(path):
                if module.startswith("app."):
                    assert module.startswith("app.importers."), (
                        f"{name} importe {module} hors du package importers"
                    )


# ── Objets de valeur ───────────────────────────────────────


class TestValueObjects:
    """Les objets échangés entre étapes sont des types explicites et sérialisables."""

    def test_column_mapping_lookup(self):
        mapping = ColumnMapping(
            fields={InternalField.FULL_NAME.value: "Nom Client"},
            confidence={InternalField.FULL_NAME.value: 0.92},
        )

        assert mapping.source_column(InternalField.FULL_NAME) == "Nom Client"
        assert mapping.source_column(InternalField.PHONE) is None
        assert mapping.is_mapped(InternalField.FULL_NAME) is True
        assert mapping.is_mapped(InternalField.PHONE) is False
        assert mapping.mapped_fields() == [InternalField.FULL_NAME]
        assert _json(mapping.to_dict())["overridden"] is False

    def test_sheet_preview_is_serialisable(self):
        preview = SheetPreview(
            columns=["Nom Client", "Tel"],
            rows=[{"Nom Client": "DUPONT Jean", "Tel": "0612345678"}],
            total_rows=1204,
        )

        payload = _json(preview.to_dict())
        assert payload["total_rows"] == 1204
        assert payload["columns"] == ["Nom Client", "Tel"]

    def test_row_error_keeps_the_original_value(self):
        error = RowError(
            row=42,
            status=ErrorStatus.ORPHAN,
            error="Client introuvable",
            original_value="DUPONT Jean",
        )

        payload = _json(error.to_dict())
        assert payload["status"] == "ORPHAN"
        assert payload["original_value"] == "DUPONT Jean"

    def test_validation_result_counts_distinct_error_rows(self):
        """Deux anomalies sur la même ligne = une seule ligne en erreur."""
        result = ValidationResult(
            valid=[{"full_name": f"client {i}"} for i in range(10)],
            errors=[
                RowError(row=11, status=ErrorStatus.VALIDATION_ERROR, error="nom manquant"),
                RowError(row=11, status=ErrorStatus.VALIDATION_ERROR, error="téléphone manquant"),
                RowError(row=12, status=ErrorStatus.VALIDATION_ERROR, error="email invalide"),
            ],
        )

        assert result.total == 12
        assert result.error_count == 2
        assert result.is_clean is False

    def test_match_decision_carries_its_zone(self):
        auto = MatchDecision(
            zone=MatchZone.AUTO,
            score=97.4,
            matched_client_id=12,
            reason="Nom et téléphone identiques",
        )
        review = MatchDecision(
            zone=MatchZone.HUMAN_REVIEW,
            score=86.0,
            reason="Nom proche, téléphone absent",
            candidates=[MatchCandidate(client_id=7, score=86.0, name="DUPONT Jean")],
        )
        new = MatchDecision(zone=MatchZone.NEW_CLIENT, score=41.2)

        assert auto.is_auto is True
        assert auto.matched_client_id == 12
        assert review.is_ambiguous is True
        assert review.matched_client_id is None
        assert _json(review.to_dict())["candidates"][0]["client_id"] == 7
        assert new.is_new is True

    def test_match_weights_prioritise_name_over_city(self):
        weights = MatchWeights()

        assert round(weights.total, 10) == 1.0
        assert weights.to_dict()["name"] > weights.to_dict()["city"]


# ── Rapport d'import ───────────────────────────────────────


class TestImportReport:
    """Le rapport agrège ce qui s'est réellement passé, batch par batch."""

    @staticmethod
    def _report() -> ImportReport:
        report = ImportReport(filename="historique_2010.xlsx", file_hash="a" * 64)
        report.add_batch_result(
            BatchResult(index=0, total=500, created=480, duplicates=15, errors=5, duration_ms=812.4)
        )
        report.add_batch_result(
            BatchResult(index=1, total=200, created=195, duplicates=5, duration_ms=310.0)
        )
        return report

    def test_aggregates_batches(self):
        report = self._report()

        assert report.batch_count == 2
        assert report.total == 700
        assert report.created == 675
        assert report.duplicates == 20
        assert report.skipped == 0

    def test_error_count_deduplicates_rows(self):
        report = self._report()
        report.add_errors(
            [
                RowError(row=42, status=ErrorStatus.ORPHAN, error="Client introuvable"),
                RowError(row=42, status=ErrorStatus.ORPHAN, error="Client introuvable"),
                RowError(row=77, status=ErrorStatus.DUPLICATE_AMBIGUOUS, error="Score 86 — ambigu"),
            ]
        )

        assert len(report.errors) == 3
        assert report.error_count == 2

    def test_running_report_has_no_duration(self):
        report = self._report()

        assert report.status is ImportStatus.RUNNING
        assert report.is_finished is False
        assert report.duration_seconds is None

    def test_finalize_closes_the_report(self):
        report = self._report()
        report.finalize(ImportStatus.PARTIAL)

        assert report.status is ImportStatus.PARTIAL
        assert report.is_finished is True
        assert report.completed_at is not None
        assert report.duration_seconds is not None
        assert report.duration_seconds >= 0

    def test_to_dict_is_json_serialisable(self):
        report = self._report()
        report.finalize(ImportStatus.PARTIAL)

        payload = _json(report.to_dict())
        assert payload["created"] == 675
        assert payload["status"] == "partial"
        assert payload["batch_count"] == 2
        assert payload["errors"] == []


# ── Configuration ──────────────────────────────────────────


class TestConfiguration:
    """Les seuils sont des constantes nommées, pas des magic numbers."""

    def test_decision_thresholds_are_named_constants(self):
        assert AUTO_MATCH_THRESHOLD == 95.0
        assert HUMAN_REVIEW_THRESHOLD == 80.0
        assert HUMAN_REVIEW_THRESHOLD < AUTO_MATCH_THRESHOLD

    def test_batch_size_default_is_shared_with_the_service(self):
        assert DEFAULT_BATCH_SIZE == 500
        assert ImportService.BATCH_SIZE == DEFAULT_BATCH_SIZE
