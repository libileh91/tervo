"""
Tervo — Matcher clients.

Rapprochement fuzzy des clients de l'historique avec les clients déjà en base.

Un fichier de 20 ans contient `"Jean DUPONT"`, `"J. Dupont"` et
`"Dupont Jean"` pour une même personne. L'égalité stricte ne suffit pas :
la similarité est calculée avec `rapidfuzz` (jamais `difflib`), puis classée
en trois zones.

Trois zones, parce que les deux erreurs possibles n'ont pas le même coût :

    score >= 95   → AUTO          rapprochement automatique
    80 <= s < 95  → HUMAN_REVIEW  arbitrage humain avant fusion
    score < 80    → NEW_CLIENT    création d'un nouveau client

Fusionner deux clients distincts est **irréversible** (des interventions
basculent sur le mauvais dossier) ; créer un doublon est corrigeable.
La zone grise est donc volontairement large : une erreur de rapprochement
coûte plus cher qu'un doublon temporaire.

Le score est composite — nom (fort) + téléphone (fort) + ville (faible) —
et seuls les signaux réellement présents sont pondérés (cf. `MatchWeights`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# ── Seuils de décision ─────────────────────────────────────

#: Au-dessus, le rapprochement est appliqué sans intervention humaine.
AUTO_MATCH_THRESHOLD: float = 95.0

#: En dessous, la ligne est considérée comme un nouveau client.
HUMAN_REVIEW_THRESHOLD: float = 80.0

#: Nombre de candidats remontés pour l'arbitrage humain.
DEFAULT_MAX_CANDIDATES: int = 5

# ── Types ──────────────────────────────────────────────────


class MatchZone(str, Enum):
    """Zone de décision issue du score de similarité.

    Les valeurs sont volontairement explicites : elles alimentent
    `import_error.status` (via `DUPLICATE_AMBIGUOUS`) et le rapport d'import.
    """

    AUTO = "auto"
    HUMAN_REVIEW = "human_review"
    NEW_CLIENT = "new_client"


@dataclass(frozen=True)
class MatchWeights:
    """Pondération des signaux comparés.

    Le nom et le téléphone sont des signaux **forts** : ils identifient une
    personne. La ville est un signal **faible** : elle ne discrimine que
    marginalement (« Dupont à Lyon »).

    Lorsqu'un signal est absent (téléphone vide, ville non renseignée), son
    poids est retiré du calcul plutôt que compté comme un zéro — sinon une
    ligne incomplète obtiendrait systématiquement un score bas.
    """

    name: float = 0.60
    phone: float = 0.30
    city: float = 0.10

    @property
    def total(self) -> float:
        """Somme des poids (base de renormalisation)."""
        return self.name + self.phone + self.city

    def to_dict(self) -> dict[str, float]:
        return {"name": self.name, "phone": self.phone, "city": self.city}


@dataclass(frozen=True)
class MatchCandidate:
    """Client existant proposé comme candidat au rapprochement.

    Attributes:
        client_id: Identifiant du client déjà en base.
        score: Score composite [0, 100] entre la ligne et ce client.
        name: Nom du client candidat (forme originale, pour affichage).
        phone: Téléphone du client candidat.
        city: Ville du client candidat.
    """

    client_id: int
    score: float
    name: str | None = None
    phone: str | None = None
    city: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "score": round(self.score, 2),
            "name": self.name,
            "phone": self.phone,
            "city": self.city,
        }


@dataclass(frozen=True)
class MatchDecision:
    """Décision de rapprochement pour une ligne.

    Attributes:
        zone: Zone de décision (`AUTO`, `HUMAN_REVIEW`, `NEW_CLIENT`).
        score: Meilleur score obtenu [0, 100].
        matched_client_id: Client retenu (`AUTO` uniquement, sinon `None`).
        reason: Justification lisible, tracée dans le rapport.
        candidates: Meilleurs candidats, du plus proche au plus lointain —
            fournis pour l'arbitrage humain de la zone `HUMAN_REVIEW`.
    """

    zone: MatchZone
    score: float
    matched_client_id: int | None = None
    reason: str = ""
    candidates: list[MatchCandidate] = field(default_factory=list)

    @property
    def is_auto(self) -> bool:
        """`True` si le rapprochement est appliqué automatiquement."""
        return self.zone is MatchZone.AUTO

    @property
    def is_ambiguous(self) -> bool:
        """`True` si la ligne attend un arbitrage humain."""
        return self.zone is MatchZone.HUMAN_REVIEW

    @property
    def is_new(self) -> bool:
        """`True` si la ligne doit créer un nouveau client."""
        return self.zone is MatchZone.NEW_CLIENT

    def to_dict(self) -> dict[str, object]:
        return {
            "zone": self.zone.value,
            "score": round(self.score, 2),
            "matched_client_id": self.matched_client_id,
            "reason": self.reason,
            "candidates": [c.to_dict() for c in self.candidates],
        }


# ── Matcher ────────────────────────────────────────────────


class ClientMatcher:
    """Rapproche une ligne d'import d'un client existant.

    Les seuils et la pondération sont injectables pour que les tests puissent
    forcer une zone sans dépendre d'un score réel — les constantes du module
    servent de valeurs par défaut.
    """

    def __init__(
        self,
        weights: MatchWeights | None = None,
        auto_threshold: float = AUTO_MATCH_THRESHOLD,
        review_threshold: float = HUMAN_REVIEW_THRESHOLD,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
    ) -> None:
        self.weights = weights or MatchWeights()
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold
        self.max_candidates = max_candidates

    def match(
        self,
        candidate: dict[str, object],
        existing: list[dict[str, object]],
    ) -> MatchDecision:
        """Classe une ligne face à l'ensemble des clients existants.

        Args:
            candidate: Ligne normalisée (`full_name`, `phone`, `city`…).
            existing: Clients déjà en base (mêmes clés que `candidate`).

        Returns:
            La décision retenue, avec les meilleurs candidats pour les zones
            non automatiques.

        Todo:
            INT-99 — implémentation.
        """
        raise NotImplementedError("INT-99 — ClientMatcher.match()")

    def score(
        self,
        candidate: dict[str, object],
        client: dict[str, object],
    ) -> float:
        """Calcule le score composite [0, 100] entre deux enregistrements.

        Utilise `rapidfuzz.fuzz.token_sort_ratio` sur les noms — insensible à
        l'ordre des mots (`"Dupont Jean"` ≈ `"Jean Dupont"`).

        Todo:
            INT-99 — implémentation.
        """
        raise NotImplementedError("INT-99 — ClientMatcher.score()")

    def classify(self, score: float) -> MatchZone:
        """Traduit un score en zone de décision.

        Todo:
            INT-99 — implémentation.
        """
        raise NotImplementedError("INT-99 — ClientMatcher.classify()")
