"""
Tervo — Excel reader.

Lecture des fichiers Excel de l'historique via pandas + openpyxl.

Responsabilité unique : produire un `pandas.DataFrame` **brut**. Aucune
interprétation, aucune normalisation, aucune validation — ces étapes sont
assurées par `format_detector`, `normalizer` et `validators`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# ── Types ──────────────────────────────────────────────────


@dataclass(frozen=True)
class SheetPreview:
    """Aperçu d'une feuille avant import.

    Attributes:
        columns: Noms de colonnes tels qu'ils apparaissent dans le fichier.
        rows: Les `limit` premières lignes, sérialisables en JSON.
        total_rows: Nombre total de lignes de données (hors en-tête).
    """

    columns: list[str]
    rows: list[dict[str, object]]
    total_rows: int

    def to_dict(self) -> dict[str, object]:
        """Représentation sérialisable (réponse API)."""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "total_rows": self.total_rows,
        }


# ── Reader ─────────────────────────────────────────────────


class ExcelReader:
    """Lit un fichier Excel et le convertit en `pandas.DataFrame`.

    Le choix de `openpyxl` est explicite (`engine=`) pour éviter que pandas
    devine le moteur selon l'extension — les fichiers historiques peuvent
    avoir des extensions trompeuses.
    """

    SUPPORTED_SUFFIXES: tuple[str, ...] = (".xlsx", ".xlsm", ".xls")
    DEFAULT_SHEET: int | str = 0

    def read(
        self,
        path: str | Path,
        sheet: int | str = DEFAULT_SHEET,
    ) -> pd.DataFrame:
        """Lit la feuille demandée et retourne un DataFrame brut.

        Raises:
            ValueError: extension non supportée, ou feuille introuvable.

        Todo:
            INT-72 — implémentation.
        """
        raise NotImplementedError("INT-72 — ExcelReader.read()")

    def preview(self, df: pd.DataFrame, limit: int = 10) -> SheetPreview:
        """Construit un aperçu : colonnes + `limit` premières lignes.

        Les valeurs non sérialisables (NaN, Timestamp) sont converties en
        types JSON-compatibles.

        Todo:
            INT-72 — implémentation.
        """
        raise NotImplementedError("INT-72 — ExcelReader.preview()")
