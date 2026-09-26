# Sprint 6.2 : Import Excel — pandas + fuzzy + pipeline (6 jours)

> ⚠️ **GELÉ — remplacé par [`sprint-6.2-v2/`](../sprint-6.2-v2/tasks.md).**
> Ce sprint décrivait l'import sur l'ancien modèle `clients + jobs`. Suite à la refonte du
> DAT (Tervo v2 : `Client → Site → Equipment → Intervention` + `Product → Sale →
> Installation`), il est remplacé par le sprint v2.
>
> **Seul INT-71 est conservé** : le package `app/importers/` (structure du pipeline) est
> réutilisé tel quel — seuls le vocabulaire et les cibles changent. INT-72 → INT-80 sont
> **obsolètes** (ciblage `clients + jobs`).

> **Durée :** 6 jours (7h/j) | **Points :** 39 | **Tâches :** INT-71 à INT-80
>
> **Référence :** `docs/DAT/annexes/revue-architecture.md` §6 à §12, §23
>
> **C'est le cœur du projet.** Tout l'argumentaire d'entretien repose sur ce sprint.

---

## INT-71 — Structure `importers/` séparée (2 pts)

**User Story**
En tant que **dev backend**,
Je veux **isoler la logique d'import dans un package dédié**,
Afin de **rendre l'architecture lisible et défendable**.

**Acceptance Criteria**
- [x] Package `backend/app/importers/` créé avec :
  - `excel_reader.py` — lecture pandas/openpyxl
  - `format_detector.py` — détection du format et mapping des colonnes
  - `normalizer.py` — normalisation des valeurs
  - `validators.py` — validation des lignes
  - `matcher.py` — fuzzy matching clients
  - `report.py` — génération du rapport d'import
- [x] `services/import_service.py` **orchestre** le pipeline (ne contient pas la logique bas niveau)
- [x] Flux documenté : `ExcelReader → FormatDetector → Normalizer → Validator → Matcher → ImportService → Repository`

**Technical Notes**
- Fichier : `backend/app/importers/` (nouveau package)
- **Rappel entretien :** « J'ai séparé le pipeline d'import du service métier — chaque étape a une responsabilité unique, ce qui la rend testable indépendamment. »
- **Implémenté à ce stade :** la structure, les interfaces et les objets de valeur. Les algorithmes (INT-72 → INT-78) sont des squelettes marqués `Todo: INT-XX`.
- **Contrat testé :** `tests/test_importers_structure.py` vérifie par AST que `app/importers` n'importe ni FastAPI, ni SQLAlchemy, ni les modèles/repositories/API.
- **Dépendances ajoutées :** `pandas`, `openpyxl`, `rapidfuzz` (`uv add` → `pyproject.toml` + `uv.lock`).
- **Note :** `notes/backend/sprint-6.2/architecture-pipeline.md`

---

## INT-72 — ExcelReader + FormatDetector (4 pts)

**User Story**
En tant que **dev backend**,
Je veux **lire un Excel et détecter automatiquement ses colonnes**,
Afin de **gérer des fichiers aux formats variables sur 20 ans**.

**Acceptance Criteria**
- [ ] `ExcelReader.read(path)` → `pandas.DataFrame` (engine `openpyxl`)
- [ ] Gestion des `.xls` et `.xlsx`
- [ ] `FormatDetector.detect(df)` → mapping colonnes → champs internes
- [ ] Normalisation des en-têtes (accents, casse, espaces, `\n`)
- [ ] Score de confiance par colonne détectée
- [ ] Mapping manuellement surchargeable (l'admin peut corriger)
- [ ] Test : 3 fichiers Excel aux formats différents → mapping correct

**Technical Notes**
- `pandas.read_excel(path, engine="openpyxl")`
- Détection par similarité d'en-têtes (rapidfuzz) + dictionnaire de synonymes
- Exemples : `"Nom Client"` / `"client"` / `"NOM"` → `full_name`
- Fichiers de test : `backend/tests/fixtures/excel/`

---

## INT-73 — Normalizer (nom, téléphone, texte) (4 pts)

**User Story**
En tant que **dev backend**,
Je veux **normaliser les valeurs avant comparaison**,
Afin de **comparer `" Élodie  DUPONT "` et `"elodie dupont"` correctement**.

**Acceptance Criteria**
- [ ] `normalize_name(" Élodie  DUPONT ")` → `"elodie dupont"`
- [ ] Suppression des accents (`unicodedata.normalize` + `NFKD`)
- [ ] Casse unifiée + espaces multiples compressés + trim
- [ ] `normalize_phone("06 12 34 56 78")` → `"0612345678"`
- [ ] Gestion `+33`, `0033`, tirets, points, parenthèses
- [ ] `normalize_text()` pour adresses/villes
- [ ] Tests unitaires sur 20+ cas (dont cas limites)

**Technical Notes**
- `unicodedata.normalize("NFKD", s)` + filtre `unicodedata.combining`
- Téléphone : `re.sub(r"[^\d+]", "", s)` puis règle de préfixe
- **Rappel entretien :** « Comparer des chaînes brutes est une erreur — je normalise d'abord pour éviter les faux négatifs. »

---

## INT-74 — Matcher rapidfuzz + 3 zones de décision (5 pts)

**User Story**
En tant que **dev backend**,
Je veux **détecter les doublons clients avec une zone d'incertitude**,
Afin de **ne pas fusionner aveuglément deux clients distincts**.

**Acceptance Criteria**
- [ ] Utilisation de **`rapidfuzz`** partout (pas `difflib`)
- [ ] Trois zones :
  - `score >= 95` → **match automatique**
  - `80 <= score < 95` → **validation humaine**
  - `score < 80` → **nouveau client**
- [ ] Score composite : nom (poids fort) + téléphone (poids fort) + ville (poids faible)
- [ ] Seuils configurables (constantes nommées, pas de magic numbers)
- [ ] Retourne : `{decision, score, matched_client_id, reason}`
- [ ] Tests : cas exact, cas proche (ambigu), cas distinct

**Technical Notes**
- `rapidfuzz.fuzz.token_sort_ratio` (insensible à l'ordre des mots)
- Seuils en constantes : `AUTO_MATCH_THRESHOLD = 95`, `HUMAN_REVIEW_THRESHOLD = 80`
- **Rappel entretien :** « Je ne veux pas automatiser aveuglément la fusion. Une erreur de rapprochement est plus grave qu'un doublon temporaire. D'où trois zones : auto, ambigu, non-match. »

---

## INT-75 — Validators (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **valider chaque ligne avant insertion**,
Afin de **rejeter les données incomplètes avec un message clair**.

**Acceptance Criteria**
- [ ] Champs obligatoires vérifiés (nom, téléphone)
- [ ] Formats vérifiés (email, code postal, date)
- [ ] Chaque erreur collectée : `{row, column, value, error}`
- [ ] Une erreur **ne bloque pas** tout le fichier → ligne rejetée + loggée
- [ ] Test : fichier avec 10% de lignes invalides → 90% importées, 10% en erreurs

**Technical Notes**
- Retourne `ValidationResult(valid_rows, errors)`
- Pas de validation Pydantic ici (données brutes) — validators dédiés
- Alimente `import_errors` (INT-77)

---

## INT-76 — ImportBatch + idempotence (SHA-256) (5 pts)

**User Story**
En tant que **dev backend**,
Je veux **qu'un fichier déjà importé ne soit pas réimporté**,
Afin de **garantir l'idempotence de façon prouvable**.

**Acceptance Criteria**
- [ ] Modèle `ImportBatch` : `id`, `filename`, `file_hash`, `started_at`, `completed_at`, `status`
- [ ] `file_hash` = SHA-256 du fichier
- [ ] Avant import : si `file_hash` existe et `status=success` → **skip**
- [ ] Modèle `ImportRecord` : `source_file`, `source_row`, `source_hash`, `entity_type`, `entity_id`
- [ ] Test : importer 2× le même fichier → 2e fois = 0 création
- [ ] Migration Alembic

**Technical Notes**
- `hashlib.sha256(path.read_bytes()).hexdigest()`
- **Rappel entretien :** « L'idempotence n'est pas un slogan — elle repose sur un hash de fichier et une table de traçabilité ligne par ligne. »

---

## INT-77 — `import_errors` + jobs orphelins (4 pts)

**User Story**
En tant que **dev backend**,
Je veux **tracer les jobs non rattachables au lieu de les ignorer**,
Afin de **ne jamais perdre une donnée historique**.

**Acceptance Criteria**
- [ ] Modèle `ImportError` : `import_batch_id`, `row`, `reason`, `status`, `original_value`
- [ ] Statuts : `VALIDATION_ERROR`, `ORPHAN`, `DUPLICATE_AMBIGUOUS`
- [ ] Un job sans client identifiable → **`import_errors` avec `ORPHAN`** (pas inséré comme job)
- [ ] Le `original_client_name` est conservé pour résolution manuelle
- [ ] Endpoint pour lister les anomalies d'un batch
- [ ] Test : job avec client inconnu → présent dans `import_errors`, absent de `jobs`

**Technical Notes**
- **Rappel entretien :** « Ignorer définitivement une donnée historique est dangereux. Les jobs non rattachables vont en anomalie d'import et ne sont insérés qu'après résolution. »

---

## INT-78 — ImportService : 2 passes + transactions par batch (5 pts)

**User Story**
En tant que **dev backend**,
Je veux **importer clients puis jobs, avec transaction par batch**,
Afin de **garantir la cohérence sans bloquer sur 20 ans de données**.

**Acceptance Criteria**
- [ ] **Passe 1 — Clients** : import + résolution doublons → IDs canoniques
- [ ] **Passe 2 — Jobs** : matching client (via IDs de la passe 1) → insertion
- [ ] **Transaction par batch** (ex: 500 lignes), **pas** une transaction géante
- [ ] Rollback du batch courant en cas d'erreur, les batches précédents restent commités
- [ ] `ImportBatch.status` : `running` → `success` / `partial` / `failed`
- [ ] Test : erreur simulée en passe 2 → batch 1 commité, batch 2 rollback

**Technical Notes**
- `async with session.begin():` par batch
- Ordonnancement : `clients` (dépendances) → `jobs` (FK)
- **Rappel entretien :** « Je ne fais pas une transaction sur 20 ans de données — c'est inutilement lourd. Je fais une transaction par batch : si le batch 3 échoue, les batches 1 et 2 restent valides. »

---

## INT-79 — API import : preview / validate / execute (4 pts)

**User Story**
En tant qu'**admin**,
Je veux **prévisualiser, valider puis exécuter un import**,
Afin de **contrôler ce qui sera inséré avant de le faire**.

**Acceptance Criteria**
- [ ] `POST /api/v1/admin/import/preview` → 10 premières lignes + mapping détecté
- [ ] `POST /api/v1/admin/import/validate` → statistiques (prêts / doublons / erreurs)
- [ ] `POST /api/v1/admin/import/execute` → import réel + rapport
- [ ] `GET /api/v1/admin/import/batches` → historique
- [ ] `GET /api/v1/admin/import/batches/{id}/errors` → anomalies
- [ ] Auth admin requise (`role = admin`)
- [ ] Tests API pour chaque endpoint

**Technical Notes**
- Upload multipart pour preview/validate/execute
- Réponse typée Pydantic
- **Rappel entretien :** le flux preview → validate → execute évite d'insérer à l'aveugle.

---

## INT-80 — Tests import + notes pédagogiques (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **des tests et des notes sur le pipeline**,
Afin de **pouvoir expliquer chaque étape en entretien**.

**Acceptance Criteria**
- [ ] Fixtures Excel de test : 3 formats, 100 / 1 000 lignes
- [ ] Tests unitaires : normalizer, matcher, validators
- [ ] Tests d'intégration : pipeline complet preview → execute
- [ ] Tests idempotence : double import
- [ ] Notes pédagogiques créées :
  - `notes/backend/sprint-6.2/pandas-openpyxl.md`
  - `notes/backend/sprint-6.2/normalisation-unicode.md`
  - `notes/backend/sprint-6.2/fuzzy-matching-rapidfuzz.md`
  - `notes/backend/sprint-6.2/transactions-batch.md`
  - `notes/backend/sprint-6.2/idempotence-sha256.md`

**Technical Notes**
- Fixtures : `backend/tests/fixtures/excel/`
- Objectif des notes : pouvoir expliquer **pourquoi**, pas seulement **comment**

---

## Tests Cases Sprint 6.2

Les tests cases détaillés sont dans `test-cases.json`.
