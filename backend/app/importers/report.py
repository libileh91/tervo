"""
Tervo — Import report.

Agrégation du résultat d'un import : synthèse globale + détail par batch.

Le rapport est construit **au fil de l'eau** : chaque batch commité ajoute un
`BatchResult`, chaque anomalie ajoute un `RowError`. Il ne recalcule rien à
partir de la base : il reflète ce que l'orchestrateur (`ImportService`) a
réellement fait. C'est ce qui le rend exploitable même lorsque l'import se
termine en `partial` ou `failed`.

Correspondance avec la table `import_batch` (`docs/DAT/05-data-model.md`) :

    total      → lignes_traitees
    created    → lignes_creees
    skipped    → lignes_ignorees
    error_count→ lignes_erreurs
    duplicates → pas de colonne dédiée (détail du rapport JSON)
    to_dict()  → colonne `rapport` (TEXT)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from app.importers.format_detector import ImportKind
from app.importers.validators import RowError

# ── Paramètres ─────────────────────────────────────────────

#: Taille de batch par défaut : compromis entre mémoire et granularité du
#: rollback. Un batch = une transaction.
DEFAULT_BATCH_SIZE: int = 500

# ── Types ──────────────────────────────────────────────────


class ImportStatus(str, Enum):
    """Statut d'un import — aligné sur `import_batch.status`."""

    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class BatchResult:
    """Résultat d'un batch, c'est-à-dire d'une transaction.

    Un batch est l'unité de commit : si le batch échoue, il est rollbacké
    seul et les précédents restent valides.

    Attributes:
        index: Position du batch (0-indexée) dans la séquence d'import.
        total: Lignes examinées dans ce batch.
        created: Entités créées.
        duplicates: Lignes rapprochées d'une entité existante (doublon évité).
        skipped: Lignes déjà importées (traçabilité `source_hash`).
        errors: Lignes rejetées, tracées dans `import_error`.
        duration_ms: Durée du batch, en millisecondes.
    """

    index: int
    total: int
    created: int = 0
    duplicates: int = 0
    skipped: int = 0
    errors: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "total": self.total,
            "created": self.created,
            "duplicates": self.duplicates,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration_ms": round(self.duration_ms, 2),
        }


# ── Report ─────────────────────────────────────────────────


@dataclass
class ImportReport:
    """Rapport d'import, sérialisable pour l'API admin.

    Attributes:
        filename: Nom du fichier d'origine.
        file_hash: SHA-256 du fichier — clé de l'idempotence.
        kind: Nature de l'import (`clients`, `sites`, `equipment`, `interventions`, `products`, `mixed`).
        batch_size: Taille de batch utilisée.
        status: Statut courant, mis à jour par `finalize()`.
        started_at: Début de l'import.
        completed_at: Fin de l'import (`None` tant qu'il tourne).
        batches: Détail par batch, dans l'ordre d'exécution.
        errors: Anomalies collectées (validation, orphelins, ambigus).
    """

    filename: str
    file_hash: str
    kind: ImportKind = ImportKind.MIXED
    batch_size: int = DEFAULT_BATCH_SIZE
    status: ImportStatus = ImportStatus.RUNNING
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    batches: list[BatchResult] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)

    # ── Agrégats ───────────────────────────────────────────

    @property
    def batch_count(self) -> int:
        """Nombre de batches exécutés."""
        return len(self.batches)

    @property
    def total(self) -> int:
        """Nombre total de lignes examinées."""
        return sum(b.total for b in self.batches)

    @property
    def created(self) -> int:
        """Nombre total d'entités créées."""
        return sum(b.created for b in self.batches)

    @property
    def duplicates(self) -> int:
        """Nombre total de doublons évités."""
        return sum(b.duplicates for b in self.batches)

    @property
    def skipped(self) -> int:
        """Nombre total de lignes déjà importées."""
        return sum(b.skipped for b in self.batches)

    @property
    def error_count(self) -> int:
        """Nombre de lignes en anomalie (dédupliquées par ligne)."""
        return len({(e.source_file, e.source_sheet, e.row) for e in self.errors
                    if e.severity != "warning"})

    @property
    def is_finished(self) -> bool:
        """`True` si l'import n'est plus en cours."""
        return self.status is not ImportStatus.RUNNING

    @property
    def duration_seconds(self) -> float | None:
        """Durée de l'import, ou `None` s'il n'est pas terminé."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    # ── Construction ───────────────────────────────────────

    def add_batch_result(self, result: BatchResult) -> None:
        """Enregistre le résultat d'un batch commité."""
        self.batches.append(result)

    def add_errors(self, errors: list[RowError]) -> None:
        """Enregistre les anomalies d'un batch (y compris ses rollbacks)."""
        self.errors.extend(errors)

    def finalize(self, status: ImportStatus) -> None:
        """Clôture le rapport : statut final + horodatage de fin."""
        self.status = status
        self.completed_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, object]:
        """Représentation sérialisable (réponse API / colonne `rapport`)."""
        return {
            "filename": self.filename,
            "file_hash": self.file_hash,
            "kind": self.kind.value,
            "batch_size": self.batch_size,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "batch_count": self.batch_count,
            "total": self.total,
            "created": self.created,
            "duplicates": self.duplicates,
            "skipped": self.skipped,
            "error_count": self.error_count,
            "batches": [b.to_dict() for b in self.batches],
            "errors": [e.to_dict() for e in self.errors],
        }
