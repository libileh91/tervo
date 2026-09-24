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
    CLIENTS = "clients"
    SITES = "sites"
    EQUIPMENT = "equipment"
    INTERVENTIONS = "interventions"
    PRODUCTS = "products"
    MIXED = "mixed"


class InternalField(str, Enum):
    FULL_NAME = "full_name"
    FIRST_NAME = "first_name"
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"
    POSTAL_CODE = "postal_code"
    CITY = "city"
    NOTES = "notes"
    CLIENT_SOURCE_ID = "client_source_id"
    SITE_SOURCE_ID = "site_source_id"
    EQUIPMENT_SOURCE_ID = "equipment_source_id"
    INTERVENTION_SOURCE_ID = "intervention_source_id"
    CLIENT_NAME = "client_name"
    SITE_NAME = "site_name"
    SITE_ADDRESS = "site_address"
    SITE_TYPE = "site_type"
    SERIAL_NUMBER = "serial_number"
    INSTALLATION_DATE = "installation_date"
    COMMISSIONED_AT = "commissioned_at"
    WARRANTY_START = "warranty_start"
    WARRANTY_END = "warranty_end"
    LIFECYCLE_STATUS = "lifecycle_status"
    PRODUCT_REFERENCE = "product_reference"
    PRODUCT_NAME = "product_name"
    PRODUCT_BRAND = "product_brand"
    PRODUCT_MODEL = "product_model"
    PRODUCT_CATEGORY = "product_category"
    PRODUCT_CHARACTERISTICS = "product_characteristics"
    PRODUCT_ACTIVE = "product_active"
    TITLE = "title"
    DESCRIPTION = "description"
    SCHEDULED_DATE = "scheduled_date"
    OBSERVATIONS = "observations"
    INTERVENTION_TYPE = "intervention_type"
    INTERVENTION_RESULT = "intervention_result"
    TECHNICIAN_NAME = "technician_name"
    DOCUMENT_REFERENCE = "document_reference"


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
    """Conservative, context-specific aliases; unknown/ambiguous headers stay unmapped."""
    MIN_CONFIDENCE = 0.75
    HEADER_SYNONYMS = {
        InternalField.FULL_NAME: ('nom', 'nom client', 'full name', 'raison sociale'),
        InternalField.FIRST_NAME: ('prenom', 'first name'),
        InternalField.PHONE: ('tel', 'telephone', 'portable', 'mobile'),
        InternalField.EMAIL: ('email', 'mail', 'courriel'),
        InternalField.ADDRESS: ('adresse facturation', 'adresse', 'address'),
        InternalField.POSTAL_CODE: ('code postal', 'cp', 'zip'),
        InternalField.CITY: ('ville', 'city', 'commune'),
        InternalField.NOTES: ('notes', 'remarque', 'commentaire'),
        InternalField.CLIENT_SOURCE_ID: ('id client', 'id ancien', 'client id'),
        InternalField.SITE_SOURCE_ID: ('id site', 'site id'),
        InternalField.EQUIPMENT_SOURCE_ID: ('id equipement', 'equipment id'),
        InternalField.INTERVENTION_SOURCE_ID: ('ref intervention', 'reference intervention'),
        InternalField.CLIENT_NAME: ('nom client', 'client', 'nom'),
        InternalField.SITE_NAME: ('nom site', 'site name'),
        InternalField.SITE_ADDRESS: ('adresse chantier', 'adresse site'),
        InternalField.SITE_TYPE: ('type site',),
        InternalField.SERIAL_NUMBER: ('numero serie', 'numero de serie', 'n serie', 'serial number'),
        InternalField.INSTALLATION_DATE: ('date installation', 'installation date'),
        InternalField.COMMISSIONED_AT: ('date mise en service', 'commissioned at'),
        InternalField.WARRANTY_START: ('debut garantie', 'warranty start'),
        InternalField.WARRANTY_END: ('fin garantie', 'warranty end'),
        InternalField.LIFECYCLE_STATUS: ('statut', 'etat equipement', 'lifecycle status'),
        InternalField.PRODUCT_REFERENCE: ('reference produit', 'ref produit', 'reference'),
        InternalField.PRODUCT_NAME: ('nom produit', 'product name'),
        InternalField.PRODUCT_BRAND: ('marque', 'brand'),
        InternalField.PRODUCT_MODEL: ('modele', 'model'),
        InternalField.PRODUCT_CATEGORY: ('type', 'categorie', 'category'),
        InternalField.PRODUCT_CHARACTERISTICS: ('caracteristiques', 'characteristics'),
        InternalField.PRODUCT_ACTIVE: ('actif', 'active'),
        InternalField.TITLE: ('titre', 'objet', 'libelle'),
        InternalField.DESCRIPTION: ('description', 'travaux', 'detail'),
        InternalField.SCHEDULED_DATE: ('date', 'date passage', 'date intervention', 'date prevue'),
        InternalField.OBSERVATIONS: ('observations', 'compte rendu'),
        InternalField.INTERVENTION_TYPE: ('type', 'type intervention'),
        InternalField.INTERVENTION_RESULT: ('resultat', 'result'),
        InternalField.TECHNICIAN_NAME: ('technicien', 'intervenant'),
        InternalField.DOCUMENT_REFERENCE: ('ref document', 'reference document'),
    }

    EXPECTED_FIELDS = {
        ImportKind.CLIENTS: (InternalField.FULL_NAME,InternalField.FIRST_NAME,InternalField.PHONE,InternalField.EMAIL,InternalField.ADDRESS,InternalField.POSTAL_CODE,InternalField.CITY,InternalField.NOTES,InternalField.CLIENT_SOURCE_ID,),
        ImportKind.SITES: (InternalField.SITE_SOURCE_ID,InternalField.CLIENT_SOURCE_ID,InternalField.CLIENT_NAME,InternalField.SITE_NAME,InternalField.SITE_ADDRESS,InternalField.POSTAL_CODE,InternalField.CITY,InternalField.SITE_TYPE,InternalField.NOTES,),
        ImportKind.EQUIPMENT: (InternalField.EQUIPMENT_SOURCE_ID,InternalField.SITE_SOURCE_ID,InternalField.PRODUCT_REFERENCE,InternalField.PRODUCT_BRAND,InternalField.PRODUCT_MODEL,InternalField.PRODUCT_CATEGORY,InternalField.SERIAL_NUMBER,InternalField.INSTALLATION_DATE,InternalField.COMMISSIONED_AT,InternalField.WARRANTY_START,InternalField.WARRANTY_END,InternalField.LIFECYCLE_STATUS,InternalField.NOTES,),
        ImportKind.INTERVENTIONS: (InternalField.INTERVENTION_SOURCE_ID,InternalField.CLIENT_SOURCE_ID,InternalField.SITE_SOURCE_ID,InternalField.EQUIPMENT_SOURCE_ID,InternalField.CLIENT_NAME,InternalField.PHONE,InternalField.SITE_ADDRESS,InternalField.SCHEDULED_DATE,InternalField.TITLE,InternalField.DESCRIPTION,InternalField.INTERVENTION_TYPE,InternalField.INTERVENTION_RESULT,InternalField.TECHNICIAN_NAME,InternalField.DOCUMENT_REFERENCE,InternalField.OBSERVATIONS,),
        ImportKind.PRODUCTS: (InternalField.PRODUCT_REFERENCE,InternalField.PRODUCT_NAME,InternalField.PRODUCT_BRAND,InternalField.PRODUCT_MODEL,InternalField.PRODUCT_CATEGORY,InternalField.PRODUCT_CHARACTERISTICS,InternalField.PRODUCT_ACTIVE,InternalField.DESCRIPTION,InternalField.NOTES,),
        ImportKind.MIXED: tuple(InternalField),
    }

    @staticmethod
    def header(value: str) -> str:
        import re
        from app.importers.normalizer import Normalizer
        return " ".join(re.sub(r"[^a-z0-9]+", " ", Normalizer.name(value)).split())

    def detect(self, columns: list[str], kind: ImportKind = ImportKind.MIXED,
               overrides: dict[str, str] | None = None) -> ColumnMapping:
        allowed = self.EXPECTED_FIELDS[kind]
        if len(columns) != len(set(columns)):
            raise ValueError("En-têtes dupliqués : corriger la sélection de colonnes")
        fields, confidence = {}, {}
        for column in columns:
            matches = [f for f in allowed if self.header(column) in
                       {self.header(a) for a in (*self.HEADER_SYNONYMS[f], f.value)}]
            if len(matches) == 1:
                key = matches[0].value
                # Two source columns targeting one field require explicit arbitration.
                if key not in fields:
                    fields[key], confidence[key] = column, 1.0
                else:
                    confidence[key] = 0.0
        for key in list(fields):
            if confidence[key] == 0:
                del fields[key]
                del confidence[key]
        for key, column in (overrides or {}).items():
            if key not in {f.value for f in allowed} or column not in columns:
                raise ValueError("Mapping manuel invalide")
            fields[key], confidence[key] = column, 1.0
        if len(set(fields.values())) != len(fields):
            raise ValueError("Une colonne ne peut alimenter plusieurs champs sans règle explicite")
        return ColumnMapping(fields=fields, confidence=confidence,
                             unmapped=[c for c in columns if c not in fields.values()],
                             overridden=bool(overrides))
