# Sprint 7.2 — Migration Excel

> **Tervo V2** · INT-98 à INT-101 · **Statut :** Terminé
> **Dépendances :** Sprint 7.1 ; indépendant de la chaîne commerciale (7.3).
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes :** [notes/backend/sprint7.2](../../../../notes/backend/sprint7.2/)

> **C'est le différenciateur entretien.** Le package `app/importers/` (INT-71) est réutilisé :
> les squelettes initiaux ont été complétés dans ce sprint par la lecture, la normalisation, la validation, le rapprochement et la persistance.

---

## INT-98 — Lecture et validation du pipeline v2 (5 pts, estimation à revoir)

**User Story**
En tant que **dev backend**,
Je veux **adapter le pipeline d'import au modèle v2**,
Afin de **lire des fichiers historiques vers `Client → Site → Equipment → Intervention → Product`**.

**Acceptance Criteria**
- [x] Lire `.xlsx` multi-feuilles et `.csv` (UTF-8/Latin-1, séparateur détecté/configurable), sans modifier les sources ; `.xls` explicitement non supporté en V1
- [x] Détecter/configurer la ligne d’en-tête ; conserver fichier, feuille, ligne physique et valeurs originales
- [x] Mapping v2 pour clients/sites/équipements/interventions/produits, identifiants historiques et nom/prénom ; mapping manuel contrôlé, ambiguïtés signalées
- [x] Normaliser noms, téléphones, adresses, séries, dates et garanties sans inventer de valeurs absentes
- [x] Valider les champs par entité ; `MISSING_PHONE` bloque un nouveau client, avertit pour une association certaine fournie par l’étape de rapprochement ; absence d’adresse distincte
- [x] Aperçu sérialisable des sources, transformations, propositions et anomalies, sans écriture en base
- [x] Tests : trois formats Excel dont un avec titre avant en-têtes, CSV Latin-1, champs manquants, dates impossibles et conservation des sources

**Technical Notes**
- Implémentation des squelettes `excel_reader`, `format_detector`, `normalizer`, `validators` (INT-71).
- Fixtures autonomes dans `backend/tests/fixtures/excel/`, issues du pack fictif et variantes séparées ; sources inchangées.
- Le matching et la preuve d’association restent INT-99 ; persistance/reprise INT-100 ; API et décisions humaines INT-101.

---

## INT-99 — Matcher multi-niveaux (4 pts)

**User Story**
En tant que **dev backend**,
Je veux **rapprocher un enregistrement historique sur 3 niveaux (client → site → équipement)**,
Afin de **ne pas créer de doublons ni fusionner des entités distinctes**.

**Acceptance Criteria**
- [x] `ClientMatcher` généralisé : match client, puis site dans le client, puis équipement dans le site
- [x] 3 zones conservées (`≥95` auto / `80-95` humain / `<80` nouveau) par niveau
- [x] Score composite : nom + téléphone (client), adresse + ville (site), n° série + produit (équipement)
- [x] Références source fiables prioritaires, noms seuls insuffisants, conflits et doublons signalés → validation humaine même au-dessus de 95
- [x] Candidats doublons d’interventions inter-fichiers ; ne pas confondre diagnostic et réparation
- [x] Test : cas exact / proche (ambigu) / distinct sur chaque niveau, C001/C005, téléphone absent et export ancien recouvrant le récent

**Technical Notes**
- `rapidfuzz.fuzz.token_sort_ratio` (ordre de mots insensible)
- Seuils : `AUTO_MATCH_THRESHOLD = 95`, `HUMAN_REVIEW_THRESHOLD = 80`

---

## INT-100 — `ImportService` 2 passes + transactions par batch (5 pts)

**User Story**
En tant que **dev backend**,
Je veux **importer clients/sites/équipements puis interventions, batch par batch**,
Afin de **garantir la cohérence sans bloquer sur 20 ans de données**.

**Acceptance Criteria**
- [x] PASS 1 : `Client → Site → Equipment` (résolution + IDs canoniques)
- [x] PASS 2 : `Intervention` (résolution `site_id` + `equipment_id`)
- [x] Transaction **par batch** (500 lignes), pas une transaction géante
- [x] Idempotence : SHA-256 + `ImportBatch` (`status=success` → skip), reprise des imports partiels via lignes déjà commitées
- [x] `ImportRecord` : namespace, référence source, fichier/feuille/ligne, valeurs originales/normalisées, cible, action et décision ; correspondances réutilisables entre fichiers
- [x] Product résolu avant Equipment si référence fiable ; sinon product_id nullable et attributs sources conservés
- [x] Interventions orphelines → `import_errors` (`ORPHAN`), jamais ignorées
- [x] Test : erreur simulée au batch 2 → batch 1 commité, batch 2 rollback

**Technical Notes**
- `async with session.begin():` par batch
- Ordre : `clients → sites → equipment` (FK) puis `interventions`

---

## INT-101 — API admin import (4 pts)

**User Story**
En tant qu'**admin**,
Je veux **prévisualiser, valider puis exécuter un import**,
Afin de **contrôler ce qui sera inséré avant de le faire**.

**Acceptance Criteria**
- [x] `POST /api/v1/admin/import/preview` → 10 lignes + mapping détecté, feuille/en-tête/encodage, provenance, transformations et propositions à confirmer
- [x] `POST /api/v1/admin/import/validate` → statistiques (prêts / doublons / erreurs)
- [x] `POST /api/v1/admin/import/execute` → import + rapport ; exécuter uniquement le fichier, mapping et décisions validés, sans recalcul silencieux
- [x] Décisions humaines tracées : doublons, noms de sites proposés, remplacement documenté ; données obligatoires manquantes corrigées ou laissées en attente
- [x] `GET /api/v1/admin/import/batches` + `GET .../batches/{id}/errors`
- [x] Auth `role=admin` requise
- [x] Tests API pour chaque endpoint

**Technical Notes**
- Upload multipart ; réponse typée Pydantic

---

## Cas de test

Voir [test-cases.json](test-cases.json).
