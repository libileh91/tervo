"""
Tervo — Normalizer.

Normalisation des valeurs avant comparaison et insertion.

Pourquoi normaliser avant de comparer ?
    `" Élodie  DUPONT "` et `"elodie dupont"` désignent la même personne,
    mais sont deux chaînes différentes. Comparer des chaînes brutes produit
    des faux négatifs (doublons non détectés) — et donc des clients dupliqués.

Règle : **normaliser d'abord, comparer ensuite.**

La normalisation est également appliquée avant insertion, pour que les
données historiques et les données futures partagent la même forme.
"""

from __future__ import annotations

import unicodedata

# ── Normalizer ─────────────────────────────────────────────


class Normalizer:
    """Convertit des valeurs brutes en formes canoniques.

    Toutes les méthodes sont statiques : le normalizer est sans état, ce qui
    le rend directement testable et utilisable comme fonction pure.
    """

    #: Préfixes téléphoniques français ramenés à la forme locale `0X…`.
    COUNTRY_PREFIXES: tuple[str, ...] = ("+33", "0033", "33")

    @staticmethod
    def fold_accents(value: str) -> str:
        """Supprime les diacritiques (`é` → `e`, `ç` → `c`).

        Utilise la décomposition Unicode NFKD puis retire les marques
        combinantes — plus fiable qu'une table de remplacement manuelle.
        """
        decomposed = unicodedata.normalize("NFKD", value)
        return "".join(c for c in decomposed if not unicodedata.combining(c))

    @staticmethod
    def name(value: object) -> str:
        """Normalise un nom : `" Élodie  DUPONT "` → `"elodie dupont"`.

        Casse unifiée, accents retirés, espaces multiples compressés.

        Todo:
            INT-73 — implémentation.
        """
        raise NotImplementedError("INT-73 — Normalizer.name()")

    @staticmethod
    def phone(value: object) -> str:
        """Normalise un téléphone : `"06 12 34 56 78"` → `"0612345678"`.

        Retire les séparateurs (espaces, points, tirets, parenthèses) et
        ramène les préfixes internationaux (`+33`, `0033`) à la forme locale.

        Todo:
            INT-73 — implémentation.
        """
        raise NotImplementedError("INT-73 — Normalizer.phone()")

    @staticmethod
    def text(value: object) -> str:
        """Normalise un texte libre (adresse, ville) : espaces compressés.

        Ne retire pas les accents : contrairement aux noms, une adresse est
        destinée à être affichée telle quelle.

        Todo:
            INT-73 — implémentation.
        """
        raise NotImplementedError("INT-73 — Normalizer.text()")

    @staticmethod
    def email(value: object) -> str:
        """Normalise un email : trim + minuscules.

        Todo:
            INT-73 — implémentation.
        """
        raise NotImplementedError("INT-73 — Normalizer.email()")

    @staticmethod
    def postal_code(value: object) -> str:
        """Normalise un code postal (suppression des décimales parasites).

        Les fichiers Excel stockent parfois un code postal en nombre
        (`75001.0`) — il faut le ramener à `"75001"`.

        Todo:
            INT-73 — implémentation.
        """
        raise NotImplementedError("INT-73 — Normalizer.postal_code()")
