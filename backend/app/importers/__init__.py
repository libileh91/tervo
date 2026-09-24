"""
Tervo — Importers package.

Pipeline d'import de l'historique Excel vers PostgreSQL.

Le pipeline est découpé en étapes à responsabilité unique :

    ExcelReader      → lit le fichier (pandas + openpyxl)
    FormatDetector   → détecte le mapping colonnes Excel → champs internes
    Normalizer       → normalise les valeurs (accents, casse, téléphone…)
    Validator        → valide chaque ligne (champs requis, formats)
    ClientMatcher    → rapproche les clients (rapidfuzz, 3 zones)
    ImportReport     → agrège le résultat d'un import

L'orchestration est assurée par `app.services.import_service.ImportService`,
qui ne contient aucune logique bas niveau : il enchaîne les étapes ci-dessus
et gère la persistance (repositories + transactions).

Ce package est volontairement indépendant de FastAPI et de SQLAlchemy :
chaque étape est testable isolément, sans base de données.

Flux complet :

    Excel
      │
      ▼
    ExcelReader.read()
      │
      ▼
    FormatDetector.detect()
      │
      ▼
    Normalizer (nom, téléphone, texte)
      │
      ▼
    Validator.validate()
      │
      ▼
    ClientMatcher.match()      (3 zones : ≥95 auto / 80-95 humain / <80 nouveau)
      │
      ▼
    ImportService              (PASS 1 clients/sites/équipements → PASS 2 interventions, transaction par batch)
      │
      ▼
    PostgreSQL + ImportReport
"""

from app.importers.excel_reader import ExcelReader, SheetPreview
from app.importers.format_detector import (
    ColumnMapping,
    FormatDetector,
    ImportKind,
    InternalField,
)
from app.importers.matcher import (
    AUTO_MATCH_THRESHOLD,
    HUMAN_REVIEW_THRESHOLD,
    ClientMatcher,
    MatchCandidate,
    MatchDecision,
    MatchWeights,
    MatchZone,
)
from app.importers.normalizer import Normalizer
from app.importers.report import (
    DEFAULT_BATCH_SIZE,
    BatchResult,
    ImportReport,
    ImportStatus,
)
from app.importers.validators import (
    ErrorStatus,
    RowError,
    ValidationResult,
    Validator,
)

# Groupé par étape du pipeline (lecture → rapport) plutôt que trié
# alphabétiquement : l'ordre reflète le déroulé d'un import.
__all__ = [  # noqa: RUF022
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
]
