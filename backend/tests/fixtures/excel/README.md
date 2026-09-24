# Fixtures INT-98

Copies du jeu fictif fourni dans `docs/DAT/others/migration strategy/resources/`.
Toutes les personnes et coordonnées sont fictives. Ne pas substituer de données réelles.

Trois classeurs : référentiel multi-feuilles, interventions historiques et ancien export.
Un CSV Latin-1 séparé par des points-virgules complète les cas.

`test_importers_v2.py` construit des variantes temporaires (titre avant l’en-tête,
lignes vides, CSV multiligne, formules, produits) sans modifier ces sources.

`anomalies_attendues.json` est conservé comme inventaire du pack. INT-98 couvre la
lecture/validation ; résolution de C999, rapprochements inter-fichiers et décisions
persistées relèvent d’INT-99–101. Les PDF ne sont pas nécessaires à ces tests.
