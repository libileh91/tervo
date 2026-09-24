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
        row: Numéro physique dans le fichier source (1-indexé, en-tête compris).
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
    code: str = "VALIDATION_ERROR"
    severity: str = "error"
    source_file: str | None = None
    source_sheet: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "row": self.row,
            "status": self.status.value,
            "error": self.error,
            "column": self.column,
            "value": self.value,
            "original_value": self.original_value,
            "code": self.code, "severity": self.severity,
            "source_file": self.source_file, "source_sheet": self.source_sheet,
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
    records: list[dict[str, object]] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Nombre total de lignes examinées."""
        if self.records:
            return len(self.records)
        return len(self.valid) + len({e.row for e in self.errors if e.severity != "warning"})

    @property
    def error_count(self) -> int:
        """Nombre de lignes en anomalie (dédupliquées par ligne)."""
        return len({e.row for e in self.errors if e.severity != "warning"})

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
            "records": self.records,
        }


# ── Validator ──────────────────────────────────────────────


class Validator:
    """Validate creation candidates without DB writes; association proof belongs to INT-99.

    `confirmed_existing_clients` is internal trusted input from the matcher, keyed
    by physical row. Never populate it from untrusted source columns/API flags.
    """
    REQUIRED_FIELDS = {
        ImportKind.CLIENTS: (InternalField.FULL_NAME, InternalField.PHONE, InternalField.ADDRESS),
        ImportKind.SITES: (InternalField.SITE_ADDRESS,),
        ImportKind.EQUIPMENT: (),
        ImportKind.INTERVENTIONS: (InternalField.SCHEDULED_DATE,),
        ImportKind.PRODUCTS: (InternalField.PRODUCT_REFERENCE, InternalField.PRODUCT_NAME,
                              InternalField.PRODUCT_BRAND, InternalField.PRODUCT_MODEL,
                              InternalField.PRODUCT_CATEGORY),
        ImportKind.MIXED: (),
    }
    MAX_FIELD_LENGTH = 500

    def validate(self, df, mapping, kind, *, confirmed_existing_clients=None,
                 two_digit_year_base=None):
        import json
        import re
        from app.importers.normalizer import Normalizer as N
        from app.importers.excel_reader import json_value

        if any(c not in df.columns for c in mapping.fields.values()):
            raise ValueError("Mapping incompatible avec les colonnes")
        from app.importers.format_detector import FormatDetector
        if len(set(mapping.fields.values())) != len(mapping.fields):
            raise ValueError("Colonnes de mapping réutilisées")
        if any(k not in {f.value for f in FormatDetector.EXPECTED_FIELDS[kind]} for k in mapping.fields):
            raise ValueError("Champ de mapping inconnu")
        result = ValidationResult()
        source = df.attrs.get('source', {})
        numbers = df.attrs.get('source_rows', list(range(2, len(df) + 2)))
        if len(numbers) != len(df):
            raise ValueError("Provenance des lignes incohérente")
        date_fields = {'scheduled_date', 'installation_date', 'commissioned_at', 'warranty_start', 'warranty_end'}
        for number, raw in zip(numbers, df.to_dict('records')):
            original = {k: json_value(v) for k, v in raw.items()}
            values, issues, proposals = {}, [], {}
            # Todo later TD-B015 / INT-99: matcher supplies trusted association evidence.
            existing = (confirmed_existing_clients or {}).get(number)

            def issue(key, code, message, severity='error'):
                column = mapping.fields.get(key, key if key in original else None)
                value = original.get(column)
                error = RowError(row=number, status=ErrorStatus.VALIDATION_ERROR,
                    error=message, column=column or key,
                    value=None if value is None else str(value),
                    original_value=None if value is None else str(value), code=code,
                    severity=severity, source_file=source.get('file'), source_sheet=source.get('sheet'))
                issues.append(error)
                result.errors.append(error)

            for key, column in mapping.fields.items():
                value = raw[column]
                try:
                    if isinstance(value, str) and value.startswith('='):
                        raise ValueError("Formule Excel : fournir une valeur validée")
                    if key in date_fields:
                        normalized = N.date(value, two_digit_year_base=two_digit_year_base)
                    elif key == 'phone':
                        normalized = N.phone(value)
                    elif key in {'full_name', 'first_name', 'client_name'}:
                        normalized = N.name(value)
                    elif key == 'serial_number':
                        normalized = N.serial_number(value)
                    elif key == 'email':
                        normalized = N.email(value)
                        if normalized and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
                            raise ValueError("Email invalide")
                    elif key == 'product_characteristics':
                        normalized = json.loads(N.text(value)) if N.text(value) else None
                        if normalized is not None and not isinstance(normalized, dict):
                            raise ValueError("Caractéristiques : objet JSON attendu")
                    elif key == 'product_active':
                        token = N.name(value)
                        if token and token not in {'true', 'false', '1', '0', 'oui', 'non'}:
                            raise ValueError("Booléen invalide")
                        normalized = None if not token else token in {'true', '1', 'oui'}
                    else:
                        normalized = N.text(value)
                    values[key] = normalized if normalized != '' else None
                except (ValueError, TypeError) as exc:
                    values[key] = None
                    issue(key, 'INVALID_VALUE', str(exc))
            if values.get('first_name') and values.get('full_name'):
                values['full_name'] = values['first_name'] + ' ' + values['full_name']
            for field in self.REQUIRED_FIELDS[kind]:
                if not values.get(field.value) and not any(e.column == mapping.fields.get(field.value, field.value) for e in issues):
                    key = field.value
                    severity = 'warning' if kind == ImportKind.CLIENTS and existing and key in {'phone','address'} else 'error'
                    issue(key, 'MISSING_PHONE' if key == 'phone' else 'MISSING_' + key.upper(),
                          f"Champ requis absent : {key}", severity)
            if existing and kind == ImportKind.CLIENTS:
                proposals['associate_client_id'] = existing
            if kind == ImportKind.SITES:
                if not (values.get('client_source_id') or values.get('client_name')):
                    issue('client_source_id', 'MISSING_CLIENT_REFERENCE', 'Client du site non identifiable')
                if not values.get('site_name'):
                    proposals['site_name'] = values.get('site_address')
                    issue('site_name', 'SITE_NAME_REQUIRES_CONFIRMATION', 'Libellé de site à confirmer', 'review')
            if kind == ImportKind.EQUIPMENT:
                if not values.get('site_source_id'):
                    issue('site_source_id', 'MISSING_SITE_REFERENCE', 'Site requis')
                if not values.get('serial_number'):
                    issue('serial_number', 'MISSING_SERIAL_NUMBER', 'Numéro de série absent', 'warning')
                status = values.get('lifecycle_status')
                statuses = {'EN_SERVICE':'ACTIVE', 'HORS_SERVICE':'OUT_OF_SERVICE', 'REMPLACE':'REPLACED',
                            'RETIRE':'RETIRED', **{s:s for s in ('ACTIVE','OUT_OF_SERVICE','REPLACED','RETIRED')}}
                if status:
                    mapped = statuses.get(N.fold_accents(status).upper().replace(' ', '_'))
                    if mapped is None:
                        issue('lifecycle_status', 'INVALID_STATUS', 'Statut équipement inconnu')
                    else:
                        values['lifecycle_status'] = mapped
                if not values.get('product_reference'):
                    proposals['product_id'] = None
                    issue('product_reference', 'UNRESOLVED_PRODUCT', 'Référence catalogue absente : conserver product_id NULL', 'warning')
                if values.get('lifecycle_status') == 'REPLACED' or 'remplac' in N.name(values.get('notes')):
                    issue('notes', 'REPLACEMENT_REQUIRES_REVIEW', 'Lien de remplacement à confirmer', 'review')
            if kind in (ImportKind.INTERVENTIONS, ImportKind.MIXED):
                if not (values.get('site_source_id') or values.get('site_address')):
                    issue('site_source_id', 'MISSING_SITE_REFERENCE', 'Site requis pour une intervention')
                if not values.get('title'):
                    proposals['title'] = values.get('description') or values.get('intervention_type')
                    issue('title', 'TITLE_REQUIRES_CONFIRMATION', 'Titre à confirmer', 'review')
                issue('intervention_type', 'HISTORICAL_MAPPING_REQUIRES_REVIEW',
                      'Confirmer le statut historique et le mapping type/résultat/technicien', 'review')
                if kind == ImportKind.MIXED and not values.get('scheduled_date'):
                    issue('scheduled_date', 'MISSING_SCHEDULED_DATE', 'Date requise')
            if values.get('warranty_start') and values.get('warranty_end') and values['warranty_end'] < values['warranty_start']:
                issue('warranty_end', 'INVALID_WARRANTY_RANGE', 'Fin de garantie antérieure au début')
            if 'doublon' in N.name(values.get('notes')):
                issue('notes', 'DUPLICATE_REQUIRES_REVIEW', 'Doublon signalé dans la source', 'review')
            for column in (c for c in df.columns if c not in mapping.fields.values()):
                if original.get(column) is not None and N.text(original[column]):
                    issue(column, 'UNMAPPED_COLUMN', f"Colonne sans mapping : {column}", 'review')
            limits = {'full_name':255, 'phone':50, 'email':255, 'address':500,
                      'postal_code':20, 'city':255, 'site_name':255, 'site_address':500,
                      'serial_number':255, 'product_reference':100, 'product_name':255,
                      'product_brand':255, 'product_model':255, 'product_category':100, 'title':255}
            for key, limit in limits.items():
                if isinstance(values.get(key), str) and len(values[key]) > limit:
                    issue(key, 'VALUE_TOO_LONG', f"Longueur maximale : {limit}")
            blocking = any(e.severity != 'warning' for e in issues)
            result.records.append(dict(source={**source, 'row':number}, original=original,
                normalized=values, proposals=proposals, disposition='pending' if blocking else 'candidate',
                anomalies=[e.to_dict() for e in issues]))
            if not blocking:
                result.valid.append(values)
        return result
