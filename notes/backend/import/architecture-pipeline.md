# INT-71 — Le package `importers/` : architecture du pipeline d'import

> **Sprint :** 6.2 — Import Excel · **Tâche :** INT-71 (2 pts)
> **Fichiers créés :** `backend/app/importers/` (6 modules) + `backend/app/services/import_service.py`
> **Références :** `docs/DAT/annexes/revue-architecture.md` (séparation `importers/` vs `services/`), `docs/DAT/05-data-model.md` §5

---

## 1. Le problème que cette structure résout

Sans découpage, un import Excel finit en un service de plusieurs centaines de lignes qui :

- lit le fichier, détecte les colonnes, normalise, valide, rapproche les clients, insère, met à jour des compteurs ;
- ne se teste **qu'avec une base de données** (donc lentement, et en testant tout à la fois) ;
- devient risqué à corriger : une modification sur la normalisation peut casser la validation.

L'import est **le différenciateur du projet** (20 ans de données à migrer). Il doit donc être
lisible et démontrable. Un pipeline long mais découpé se défend en entretien ; un service
monolithique ne se défend pas.

**Principe retenu :** un module = une responsabilité = un vocabulaire.

---

## 2. Le flux, étape par étape

```
   historique.xls / .xlsx
            │
            ▼   ExcelReader.read()              # pandas + openpyxl — DataFrame BRUT
        DataFrame
            │
            ▼   FormatDetector.detect()         # colonnes source → champs internes
        ColumnMapping
            │
            ▼   Normalizer.*()                  # formes canoniques (nom, téléphone…)
            │
            ▼   Validator.validate()            # valides / anomalies, ligne à ligne
        ValidationResult
            │
            ▼   ClientMatcher.match()           # 3 zones : ≥95 auto / 80-95 humain / <80 nouveau
        MatchDecision
            │
            ▼   ImportService.execute()         # PASS 1 clients → PASS 2 jobs
            │                                   # transaction PAR BATCH (500 lignes)
            ▼
      PostgreSQL  +  ImportReport
```

Chaque flèche est **un type explicite**, pas un `dict` anonyme :

| Étape | Entrée | Sortie |
|-------|--------|--------|
| `ExcelReader.read()` | chemin de fichier | `pd.DataFrame` brut |
| `ExcelReader.preview()` | `DataFrame` | `SheetPreview` |
| `FormatDetector.detect()` | `list[str]` (en-têtes) | `ColumnMapping` |
| `Normalizer.name()/phone()/…` | `object` | `str` canonique |
| `Validator.validate()` | `DataFrame` + `ColumnMapping` + `ImportKind` | `ValidationResult` |
| `ClientMatcher.match()` | ligne normalisée + clients existants | `MatchDecision` |
| `ImportService.execute()` | chemin + mapping | `ImportReport` |

> **Pourquoi des types intermédiaires ?** Ils rendent le pipeline **inspectable** : les
> endpoints `preview` / `validate` (INT-79) réutilisent exactement ces objets, sans
> réimplémenter quoi que ce soit.

---

## 3. Les 6 modules et leur frontière

| Module | Responsabilité unique | Ne fait **pas** |
|--------|----------------------|-----------------|
| `excel_reader.py` | lire le fichier → `DataFrame` brut | aucune interprétation, aucune correction |
| `format_detector.py` | en-têtes → `ColumnMapping` (+ score de confiance) | ne lit pas le fichier, ne valide pas les valeurs |
| `normalizer.py` | valeurs brutes → formes canoniques | ne compare pas, ne décide pas |
| `validators.py` | lignes → `valid` + `RowError` | ne normalise pas, n'insère pas |
| `matcher.py` | ligne + clients existants → `MatchDecision` | n'écrit rien, ne fusionne rien |
| `report.py` | agréger batches + erreurs → `ImportReport` | ne décide rien : il **reflète** |

`report.py` mérite une précision : c'est un **agrégateur**, pas un calculateur. Il ne relit
jamais la base — il expose ce que l'orchestrateur a réellement fait. C'est ce qui permet de
produire un rapport utile **même quand l'import échoue partiellement** (statut `partial`).

Le rapport est aussi aligné sur la table `import_batch` du data model :

| `ImportReport` | Colonne `import_batch` |
|----------------|------------------------|
| `total` | `lignes_traitees` |
| `created` | `lignes_creees` |
| `skipped` | `lignes_ignorees` |
| `error_count` | `lignes_erreurs` |
| `to_dict()` | `rapport` (TEXT) |
| `duplicates` | *(pas de colonne — détail du rapport JSON)* |

---

## 4. Ce qui reste dans `ImportService` — et pourquoi

`app/services/import_service.py` **orchestre**, il ne calcule pas. Il ne contient que :

1. le **montage** des étapes (`self.reader`, `self.detector`, `self.matcher`…) ;
2. la **persistance** (repositories, sessions, transactions) ;
3. la **décision d'ordonnancement** (PASS 1 avant PASS 2) ;
4. la **politique d'erreur** (rollback du batch, statut final, orphelins).

Deux points d'entrée seulement :

| Méthode | Écrit en base ? | Usage |
|---------|:---------------:|-------|
| `analyze()` | ❌ | `POST /admin/import/preview` et `/validate` |
| `execute()` | ✅ | `POST /admin/import/execute` |

`analyze()` retourne un `ImportAnalysis` (aperçu + mapping + validation) : c'est la réponse à
« je montre ce qui **sera** fait avant de le faire ».

> **Règle d'entretien :** le service ne connaît pas les détails du fichier Excel ; les modules
> d'import ne connaissent ni FastAPI, ni SQLAlchemy. La frontière est nette dans les deux sens.

---

## 5. Le contrat d'indépendance (vérifié par un test)

Le package `app.importers` **n'importe ni FastAPI ni SQLAlchemy**. Conséquence concrète :

```python
from app.importers import Normalizer, ClientMatcher, ImportReport   # aucune base requise
```

C'est cette propriété qui rend le pipeline **testable en isolation** : on peut vérifier le
fuzzy matching sur 50 cas sans créer un client en base.

Ce contrat n'est pas une intention, il est **testé** :
`tests/test_importers_structure.py` lit le source de chaque module et échoue si un
`import fastapi` / `import sqlalchemy` apparaît dans `app/importers/`.

---

## 6. Les 4 décisions structurantes portées par cette architecture

Elles sont **décidées** ici, **implémentées** dans les tâches suivantes :

| Décision | Où c'est décidé | Où c'est implémenté |
|----------|-----------------|---------------------|
| **Idempotence** (SHA-256 + `import_batch`) | `ImportService.compute_file_hash()` / `_already_imported()` | INT-76 |
| **Trois zones de rapprochement** (95 / 80) | `matcher.AUTO_MATCH_THRESHOLD` / `HUMAN_REVIEW_THRESHOLD` | INT-74 |
| **Transaction par batch** (jamais 20 ans d'un coup) | `ImportService.BATCH_SIZE`, `_split_batches()` | INT-78 |
| **Jobs orphelins tracés, jamais ignorés** | `validators.ErrorStatus.ORPHAN` | INT-77 |

Les seuils sont des **constantes nommées** (`AUTO_MATCH_THRESHOLD = 95.0`), jamais des
« magic numbers » enfouis dans une comparaison.

---

## 7. Vérifier que la structure tient

```bash
cd backend/

# 1. Le package s'importe seul (sans app, sans base)
uv run python -c "from app.importers import *; print(ImportReport)"

# 2. Le service s'importe sans cycle
uv run python -c "from app.services.import_service import ImportService; print('ok')"

# 3. Le contrat structurel
uv run pytest tests/test_importers_structure.py -v

# 4. Non-régression complète
uv run pytest tests/ -q
```

---

## 8. Dépendances ajoutées

| Paquet | Rôle | Utilisé par |
|--------|------|-------------|
| `pandas` | lecture/manipulation tabulaire | `excel_reader`, `validators` |
| `openpyxl` | moteur de lecture `.xlsx` / `.xlsm` | `ExcelReader` (`engine="openpyxl"`) |
| `rapidfuzz` | similarité de chaînes (C++, rapide) | `matcher` (INT-74), `format_detector` (INT-72) |

Ajoutées via `uv add` → `pyproject.toml` **et** `uv.lock`. Le `Dockerfile` utilise
`uv sync --frozen` : l'image récupère les dépendances automatiquement, aucune modification
n'était nécessaire.

> **Pourquoi `rapidfuzz` et pas `difflib` (stdlib) ?** `rapidfuzz` implémente les mêmes
> algorithmes en C++ (donc nettement plus rapide sur des milliers de comparaisons) et fournit
> `token_sort_ratio`, insensible à l'ordre des mots — exactement ce qu'il faut pour
> `"Dupont Jean"` vs `"Jean Dupont"`.

---

## 9. Ce qui reste (INT-72 → INT-80)

Les 6 modules sont des **squelettes** : signatures, types, docstrings et `NotImplementedError`
avec un marqueur `Todo: INT-XX`. C'est volontaire — la structure est validée avant le code.

| Marqueur trouvé | Tâche qui l'implémente |
|-----------------|------------------------|
| `INT-72` | `ExcelReader.read()/preview()`, `FormatDetector.detect()` |
| `INT-73` | `Normalizer.name()/phone()/text()/email()/postal_code()` |
| `INT-74` | `ClientMatcher.match()/score()/classify()` |
| `INT-75` | `Validator.validate()` |
| `INT-76` | `ImportService.compute_file_hash()` / `_already_imported()` |
| `INT-77` | statuts `ORPHAN` / `DUPLICATE_AMBIGUOUS` + table `import_error` |
| `INT-78` | `ImportService.execute()` + passes + batches |
| `INT-79` | `ImportService.analyze()` + API admin |
| `INT-80` | tests métier + notes `notes/backend/import/` |

Sont **déjà implémentés** (objets de valeur, aucune logique métier) : `SheetPreview`,
`ColumnMapping`, `RowError`, `ValidationResult`, `MatchZone`, `MatchWeights`,
`MatchCandidate`, `MatchDecision`, `BatchResult`, `ImportReport`.

---

## 10. Questions d'entretien couvertes par cette structure

**« Pourquoi séparer le pipeline du service métier ? »**
> Parce que chaque étape a une responsabilité unique et un type de sortie explicite. Le
> `ImportService` ne fait qu'enchaîner et persister — il est lisible en une lecture.

**« Comment testez-vous un import sans base de données ? »**
> Le package `importers` n'importe ni FastAPI ni SQLAlchemy, et c'est vérifié par un test.
> La normalisation, la détection de mapping et le matching se testent en pur Python.

**« Comment savez-vous qu'un import a réussi partiellement ? »**
> Le rapport est construit au fil de l'eau, batch par batch, et son statut est décidé à la
> fin : `success`, `partial` ou `failed`. Il n'est pas recalculé depuis la base — il
> contient donc l'information même quand des batches ont été rollbackés.

**« Pourquoi trois zones et pas un booléen « doublon / pas doublon » ? »**
> Parce que les deux erreurs n'ont pas le même coût : fusionner deux clients distincts est
> irréversible, créer un doublon est corrigeable. La zone 80-95 est envoyée à un humain.
