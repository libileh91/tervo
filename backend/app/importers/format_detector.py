"""
Tervo — Format detector.

Détection du mapping entre les colonnes d'un fichier Excel et les champs
internes de Tervo.

Les fichiers historiques (20 ans) ont des formats variables : colonnes
renommées, déplacées, accentuées différemment. Cette étape produit un
mapping explicite, **surchargeable manuellement** par l'administrateur
avant l'import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

# ── Vocabulaire interne ────────────────────────────────────


class ImportKind(str, Enum):
    """Nature des données importées."""

    CLIENTS = "clients"
    JOBS = "jobs"
    MIXED = "mixed"


class InternalField(str, Enum):
    """Champs internes cibles d'un import.

    Ces valeurs sont indépendantes du vocabulaire des fichiers Excel.
    """

    # ── Client ─────────────────────────────────────────────
    FULL_NAME = "full_name"
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"
    POSTAL_CODE = "postal_code"
    CITY = "city"
    NOTES = "notes"

    # ── Intervention ───────────────────────────────────────
    TITLE = "title"
    DESCRIPTION = "description"
    SCHEDULED_DATE = "scheduled_date"
    OBSERVATIONS = "observations"

    # ── Lien ───────────────────────────────────────────────
    # Les fichiers historiques référencent le client par son NOM, pas par
    # un identifiant : ce champ porte ce nom, résolu en `client_id` lors
    # de la PASS 2 (cf. `ImportService`).
    CLIENT_NAME = "client_name"


# ── Mapping ────────────────────────────────────────────────


@dataclass(frozen=True)
class ColumnMapping:
    """Correspondance champs internes ↔ colonnes du fichier source.

    Attributes:
        fields: `InternalField` (valeur) → nom de colonne source.
        confidence: `InternalField` (valeur) → score de confiance [0, 1].
        unmapped: Colonnes source qui n'ont été associées à aucun champ.
        overridden: `True` si le mapping a été corrigé manuellement.
    """

    fields: dict[str, str] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    unmapped: list[str] = field(default_factory=list)
    overridden: bool = False

    def source_column(self, internal: InternalField) -> str | None:
        """Retourne la colonne source associée à un champ interne."""
        return self.fields.get(internal.value)

    def is_mapped(self, internal: InternalField) -> bool:
        """Indique si un champ interne est présent dans le mapping."""
        return internal.value in self.fields

    def mapped_fields(self) -> list[InternalField]:
        """Liste des champs internes effectivement mappés."""
        return [f for f in InternalField if f.value in self.fields]

    def to_dict(self) -> dict[str, object]:
        return {
            "fields": dict(self.fields),
            "confidence": dict(self.confidence),
            "unmapped": list(self.unmapped),
            "overridden": self.overridden,
        }


# ── Detector ───────────────────────────────────────────────


class FormatDetector:
    """Détecte le mapping colonnes source → champs internes.

    La détection combine deux stratégies :
      1. Un dictionnaire de synonymes connus (ex. « Nom Client », « client »,
         « NOM » → `FULL_NAME`).
      2. Une similarité de chaînes (rapidfuzz) pour les variantes non listées.

    Un score de confiance est associé à chaque correspondance : en dessous de
    `MIN_CONFIDENCE`, la colonne est laissée de côté plutôt que mal mappée.
    """

    #: Seuil sous lequel une correspondance n'est pas retenue.
    MIN_CONFIDENCE: float = 0.75

    #: Synonymes connus, par champ interne.
    HEADER_SYNONYMS: ClassVar[dict[InternalField, tuple[str, ...]]] = {
        InternalField.FULL_NAME: ("nom client", "client", "nom", "full name", "raison sociale"),
        InternalField.PHONE: ("tel", "telephone", "numero", "portable", "mobile"),
        InternalField.EMAIL: ("email", "mail", "courriel"),
        InternalField.ADDRESS: ("adresse", "address", "rue"),
        InternalField.POSTAL_CODE: ("code postal", "cp", "zip"),
        InternalField.CITY: ("ville", "city", "commune"),
        InternalField.NOTES: ("notes", "remarque", "commentaire"),
        InternalField.TITLE: ("titre", "objet", "libelle", "intervention"),
        InternalField.DESCRIPTION: ("description", "detail"),
        InternalField.SCHEDULED_DATE: ("date", "date intervention", "date prevue"),
        InternalField.OBSERVATIONS: ("observations", "compte rendu"),
        InternalField.CLIENT_NAME: ("nom client", "client", "nom"),
    }

    #: Champs recherchés selon la nature de l'import.
    EXPECTED_FIELDS: ClassVar[dict[ImportKind, tuple[InternalField, ...]]] = {
        ImportKind.CLIENTS: (
            InternalField.FULL_NAME,
            InternalField.PHONE,
            InternalField.EMAIL,
            InternalField.ADDRESS,
            InternalField.POSTAL_CODE,
            InternalField.CITY,
            InternalField.NOTES,
        ),
        ImportKind.JOBS: (
            InternalField.CLIENT_NAME,
            InternalField.TITLE,
            InternalField.DESCRIPTION,
            InternalField.SCHEDULED_DATE,
            InternalField.OBSERVATIONS,
        ),
        ImportKind.MIXED: tuple(InternalField),
    }

    def detect(
        self,
        columns: list[str],
        kind: ImportKind = ImportKind.MIXED,
    ) -> ColumnMapping:
        """Détecte le mapping à partir des en-têtes du fichier.

        Args:
            columns: Noms de colonnes bruts, tels que lus dans le fichier.
            kind: Champs attendus selon la nature de l'import.

        Todo:
            INT-72 — implémentation.
        """
        raise NotImplementedError("INT-72 — FormatDetector.detect()")
