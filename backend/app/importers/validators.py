"""
Tervo — Validators.

Validation ligne à ligne des données avant insertion.

Principe : une ligne invalide est **rejetée et tracée**, elle ne bloque pas
tout le fichier. Un fichier de 20 ans contient inévitablement des lignes
incomplètes — les refuser en bloc rendrait l'import inutilisable.

Chaque anomalie est conservée dans `RowError`, avec son statut :

    VALIDATION_ERROR      champ requis manquant, format invalide
    ORPHAN                intervention sans client identifiable
    DUPLICATE_AMBIGUOUS   rapprochement client ambigu (zone 80-95)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

import pandas as pd

from app.importers.format_detector import ColumnMapping, ImportKind, InternalField

# ── Types ──────────────────────────────────────────────────


class ErrorStatus(str, Enum):
    """Statut d'une anomalie d'import.

    Aligné sur la colonne `status` de la table `import_error`.
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"
    ORPHAN = "ORPHAN"
    DUPLICATE_AMBIGUOUS = "DUPLICATE_AMBIGUOUS"


@dataclass(frozen=True)
class RowError:
    """Anomalie rencontrée sur une ligne.

    Attributes:
        row: Numéro de ligne dans le fichier source (1-indexé, en-tête exclu).
        status: Nature de l'anomalie.
        error: Message lisible.
        column: Colonne concernée, si applicable.
        value: Valeur fautive, si applicable.
        original_value: Valeur d'origine conservée (ex. nom de client
            introuvable pour une intervention orpheline) — permet une
            résolution manuelle ultérieure.
    """

    row: int
    status: ErrorStatus
    error: str
    column: str | None = None
    value: str | None = None
    original_value: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "row": self.row,
            "status": self.status.value,
            "error": self.error,
            "column": self.column,
            "value": self.value,
            "original_value": self.original_value,
        }


@dataclass
class ValidationResult:
    """Résultat d'une passe de validation.

    Attributes:
        valid: Lignes valides, converties en dictionnaires `InternalField` → valeur.
        errors: Anomalies collectées (une ligne peut en produire plusieurs).
    """

    valid: list[dict[str, object]] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Nombre total de lignes examinées."""
        return len(self.valid) + len({e.row for e in self.errors})

    @property
    def error_count(self) -> int:
        """Nombre de lignes en anomalie (dédupliquées par ligne)."""
        return len({e.row for e in self.errors})

    @property
    def is_clean(self) -> bool:
        """`True` si aucune anomalie n'a été détectée."""
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "valid_count": len(self.valid),
            "error_count": self.error_count,
            "errors": [e.to_dict() for e in self.errors],
        }


# ── Validator ──────────────────────────────────────────────


class Validator:
    """Valide les lignes d'un DataFrame selon la nature de l'import.

    La validation s'appuie sur le mapping détecté : un champ absent du
    mapping est traité comme « non fourni », pas comme une erreur si le
    fichier ne le contenait pas.
    """

    #: Champs dont la présence est obligatoire, par nature d'import.
    REQUIRED_FIELDS: ClassVar[dict[ImportKind, tuple[InternalField, ...]]] = {
        ImportKind.CLIENTS: (InternalField.FULL_NAME, InternalField.PHONE),
        ImportKind.JOBS: (InternalField.CLIENT_NAME, InternalField.TITLE),
        ImportKind.MIXED: (InternalField.FULL_NAME,),
    }

    #: Versions maximales acceptées pour les photos / pièces jointes (non utilisé ici).
    MAX_FIELD_LENGTH: int = 500

    def validate(
        self,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        kind: ImportKind,
    ) -> ValidationResult:
        """Valide chaque ligne et sépare les valides des anomalies.

        Args:
            df: DataFrame brut issu de `ExcelReader`.
            mapping: Mapping détecté (ou corrigé) colonnes → champs internes.
            kind: Nature de l'import (détermine les champs requis).

        Todo:
            INT-75 — implémentation.
        """
        raise NotImplementedError("INT-75 — Validator.validate()")
