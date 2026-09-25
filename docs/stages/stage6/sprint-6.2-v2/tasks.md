# Sprint 6.2-v2 : Tervo v2 — cœur métier + migration Excel

> **Réfonte du DAT** (`docs/DAT/new/`) : le domaine passe de `clients + jobs` à une chaîne
> complète `Client → Site → Equipment → Intervention` + `Product → Sale → SaleLine →
> Installation → Equipment` + `Showroom`.
>
> **Principe directeur (verdict) :** remonter la **migration Excel** (le différenciateur
> entretien) et cibler le **cœur** en priorité. Les lots non terminés sont assumés et
> documentés comme « backlog » — c'est une force, pas une faiblesse.

---

## Décisions verrouillées (rappel)

- Identifiants **entiers auto-incrémentés** (pas d'UUID)
- `job` → **`Intervention`** (rename, + `under_warranty`)
- `Equipment` **sans** `PLANNED` — `ACTIVE / OUT_OF_SERVICE / REPLACED / RETIRED`
- `SaleLine 1 → N Installation` · `Installation 1 → 0..1 Equipment`
- `Installation.status` : `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`
- `Report` versionné V1 · `ShowroomVisit.client_id` nullable · `Quote` hors V1
- `replaced_by_id` (ancien → nouveau) · `under_warranty` sur `Intervention`

---

## Dépendances

```text
Lot 1 — Socle physique (Client, Site, Product, Equipment, Intervention)
        │
        ├──────────────►  Lot 2 — Migration Excel   (remontée, différenciateur)
        │                 (ne dépend QUE du Lot 1)
        │
        └──────────────►  Lot 3 — Chaîne commerciale (Sale → Installation)
```

> **Lot 2 ne dépend pas du Lot 3** : les équipements historiques ont `installation_id`
> nullable (pas de vente/installation enregistrée pour 20 ans d'historique). La migration
> cible donc `Client → Site → Equipment → Intervention` + `Product`, sans exiger la chaîne
> commerciale.

---

## Lot 1 — Socle physique v2 (16 pts)

---

## INT-94 — Renommer `job` → `intervention` (5 pts)

**User Story**
En tant que **dev backend**,
Je veux **aligner le nom de l'entité terrain sur le vocabulaire métier**,
Afin de **rendre le code cohérent avec le DAT v2 et défendable en entretien**.

**Acceptance Criteria**
- [x] Modèle `Job` → `Intervention` ; `JobStatus` → `InterventionStatus` ; table `job` → `intervention`
- [x] Enum `InterventionStatus` en anglais (`PLANNED / IN_PROGRESS / COMPLETED / CANCELLED`)
- [x] Ajout `under_warranty: boolean` (défaut `false`)
- [x] Renommage propagé : schemas, service, repository, API (`/interventions`), seed, frontend, tests
- [x] Migration Alembic idempotente (rename table + colonnes FK + enum)
- [x] Tous les tests existants passent (114 adaptés)
- [x] `site_id` (requis) → **ajouté dans INT-95** (chaîne `Client → Site → Intervention`, `client_id` direct retiré)
- [x] `equipment_id` (nullable) → **ajouté dans INT-97**, avec contrôle du site

**Technical Notes**
- Renommage mécanique **une fois, tôt** — le plus tard serait plus cher
- `equipment_id` nullable + règle `Equipment.site_id == Intervention.site_id`
- Fichiers : `app/models/`, `app/schemas/`, `app/services/job.py`, `app/api/v1/`, `app/seed.py`, `frontend/src/`

---

## INT-95 — Entité `Site` (3 pts)

**User Story**
En tant que **gérant**,
Je veux **rattacher plusieurs lieux physiques à un client**,
Afin de **savoir où se trouvent les équipements et où intervenir**.

**Acceptance Criteria**
- [x] Modèle `Site` : `client_id` (FK requis), `name`, `address`, `postal_code`, `city`, `notes`
- [x] `Client 1 → N Site` ; un site ne peut exister sans client
- [x] CRUD API : `GET/POST /sites`, `GET/PATCH/DELETE /sites/{id}`
- [x] `GET /clients/{id}/sites`
- [x] Test : créer 2 sites pour un client → les 2 listés

**Technical Notes**
- Fichiers : `app/models/site.py`, `app/schemas/site.py`, `app/services/site.py`, `app/repositories/site.py`, `app/api/v1/sites.py`
- Migration Alembic

---

## INT-96 — Entité `Product` (catalogue) (3 pts)

**User Story**
En tant que **vendeur**,
Je veux **gérer un catalogue de références commerciales**,
Afin de **distinguer la référence vendue de l'équipement physique installé**.

**Acceptance Criteria**
- [x] Modèle `Product` : `brand`, `model`, `reference`, `category`, `characteristics`, `active`
- [x] CRUD API + désactivation (soft, pas de suppression)
- [x] `Product 1 → N Equipment` (un produit peut être installé plusieurs fois)
- [x] Test : créer un produit → l'utiliser sur 2 équipements distincts

**Avancement** : terminé ; relation Product → Equipment et test multi-instances validés dans INT-97 (TD-B012 résolu).

**Technical Notes**
- Remplace l'ancien sprint 6.3 « catalogue » (INT-81→84 gelé)
- Fichiers : `app/models/product.py`, `app/schemas/product.py`, `app/services/product.py`, `app/api/v1/products.py`

---

## INT-97 — Entité `Equipment` (5 pts)

**User Story**
En tant que **technicien**,
Je veux **identifier chaque appareil physique installé**,
Afin de **suivre son historique et ses interventions sur la durée**.

**Acceptance Criteria**
- [x] Modèle `Equipment` : `site_id` (requis), `product_id` (nullable), `installation_id` (nullable), `serial_number`, `installed_at`, `commissioned_at`, `warranty_start/end`, `lifecycle_status`, `replaced_by_id`, `notes`
- [x] `lifecycle_status` ∈ `ACTIVE / OUT_OF_SERVICE / REPLACED / RETIRED` (pas de `PLANNED`)
- [x] `replaced_by_id` = self-FK (ancien → nouveau), l'ancien est conservé
- [x] API : `GET /equipment`, `GET /equipment/{id}`, `GET /sites/{id}/equipment`, `POST /equipment/{id}/replace`
- [x] Test : remplacer un équipement → l'ancien garde son historique, pointe vers le nouveau

**Technical Notes**
- `installation_id` nullable : les équipements importés (20 ans) n'ont pas de vente/installation. FK et alimentation reportées à INT-103 (TD-B014).
- Fichiers : `app/models/equipment.py`, `app/schemas/equipment.py`, `app/services/equipment.py`, `app/api/v1/equipment.py`

---

## Lot 2 — Migration Excel (remontée) (18 pts)

> **C'est le différenciateur entretien.** Le package `app/importers/` (INT-71) est réutilisé :
> la *structure* du pipeline reste, mais ses méthodes sont encore des squelettes : le Lot 2 implémente la lecture, la normalisation, la validation, le rapprochement et la persistance.

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
- [ ] `POST /api/v1/admin/import/preview` → 10 lignes + mapping détecté, feuille/en-tête/encodage, provenance, transformations et propositions à confirmer
- [ ] `POST /api/v1/admin/import/validate` → statistiques (prêts / doublons / erreurs)
- [ ] `POST /api/v1/admin/import/execute` → import + rapport ; exécuter uniquement le fichier, mapping et décisions validés, sans recalcul silencieux
- [ ] Décisions humaines tracées : doublons, noms de sites proposés, remplacement documenté ; données obligatoires manquantes corrigées ou laissées en attente
- [ ] `GET /api/v1/admin/import/batches` + `GET .../batches/{id}/errors`
- [ ] Auth `role=admin` requise
- [ ] Tests API pour chaque endpoint

**Technical Notes**
- Upload multipart ; réponse typée Pydantic

---

## Lot 3 — Chaîne commerciale (10 pts)

---

## INT-102 — `Sale` + `SaleLine` (5 pts)

**User Story**
En tant que **commercial**,
Je veux **enregistrer une vente avec ses lignes de produits**,
Afin de **distinguer l'événement commercial de l'installation future**.

**Acceptance Criteria**
- [ ] `Sale` : `client_id`, `site_id`, `sale_date`, `status` (`DRAFT / CONFIRMED / CANCELLED`)
- [ ] `SaleLine` : `sale_id`, `product_id`, `quantity`, `unit_price`
- [ ] `Sale 1 → N SaleLine` ; une vente confirmée a ≥ 1 ligne
- [ ] API : `POST /sales`, `POST /sales/{id}/confirm`, `POST /sales/{id}/cancel`
- [ ] Test : `quantity = 3` → 3 lignes possibles → 3 installations ultérieures

**Technical Notes**
- `quantity` > 1 est la clé du `SaleLine 1 → N Installation`

---

## INT-103 — `Installation` (5 pts)

**User Story**
En tant que **technicien**,
Je veux **suivre l'installation d'un équipement vendu**,
Afin de **créer l'équipement physique au moment où il est réellement installé**.

**Acceptance Criteria**
- [ ] `Installation` : `sale_line_id`, `site_id`, `scheduled_start/end`, `started_at`, `completed_at`, `installation_date`, `commissioning_date`, `status`
- [ ] `status` ∈ `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`
- [ ] `POST /installations/{id}/start`, `/complete`, `/cancel`
- [ ] `complete` (même transaction) : `Installation → COMPLETED` + `Equipment` créé/rattaché
- [ ] Test : installation complétée → 1 équipement créé, `installation_id` renseigné

**Technical Notes**
- `complete` est une **transaction métier** (installation + équipement atomiques)

---

## Lot 4 — Cycle terrain (17 pts)

> Réutilise et reshape l'existant (`checklist_item`, `job_photo`, `material`, `review`, `report`)
> sur le nouveau modèle. Dépend du Lot 1.

---

## INT-104 — Checklist modèle + snapshot (5 pts)

**User Story**
En tant que **gérant**,
Je veux **définir des modèles de checklist par type d'intervention**,
Afin de **standardiser les contrôles sans réécrire l'historique des interventions passées**.

**Acceptance Criteria**
- [ ] `ChecklistTemplate` : `intervention_type`, `name` (+ items modifiables)
- [ ] `InterventionChecklist` : snapshot généré à la création de l'intervention
- [ ] `ChecklistItem` : historique (`result`, `comment`)
- [ ] Règle : modifier un modèle ne modifie **pas** les checklists passées
- [ ] API : `GET/POST /checklist-templates`, `GET /interventions/{id}/checklist`, `PATCH /checklist-items/{id}`

**Technical Notes**
- Remplace `checklist_item` (plat) → 2 niveaux (modèle / snapshot)
- Fichiers : `app/models/checklist.py`, `app/services/checklist.py`, `app/api/v1/checklists.py`

---

## INT-105 — Photos + Matériel (3 pts)

**User Story**
En tant que **technicien**,
Je veux **documenter l'intervention (photos avant/après, matériel posé)**,
Afin de **garder la traçabilité de ce qui a été fait**.

**Acceptance Criteria**
- [ ] `Photo` : `intervention_id`, `usage` (avant/après/équipement/anomalie/pièce)
- [ ] `MaterialUsage` : `intervention_id`, `designation`, `quantity`, `unit`
- [ ] Reshape `job_photo` → `Photo`, `material` → `MaterialUsage` (FK intervention)
- [ ] API upload/suppression photos + CRUD matériel conservés

**Technical Notes**
- Réutilise l'upload existant (`UPLOAD_DIR`) + thumbnails
- Fichiers : `app/models/photo.py`, `app/models/material.py`, services/API existants

---

## INT-106 — Résultat + clôture (3 pts)

**User Story**
En tant que **technicien**,
Je veux **qualifier le résultat et clôturer l'intervention**,
Afin de **distinguer « terminée » de « résolue »**.

**Acceptance Criteria**
- [ ] `result` ∈ `RESOLVED / PARTIALLY_RESOLVED / UNRESOLVED / PART_NEEDED / QUOTE_NEEDED / RESCHEDULE`
- [ ] `complete` : résultat requis, observations optionnelles
- [ ] `status` (avancement) ≠ `result` (issue métier) — deux champs distincts
- [ ] Test : intervention `COMPLETED` + `result=PART_NEEDED` → en base

**Technical Notes**
- Fichiers : `app/models/intervention.py`, `app/services/intervention.py`

---

## INT-107 — Rapport versionné (4 pts)

**User Story**
En tant que **gérant**,
Je veux **générer et transmettre un rapport historisé**,
Afin de **ne pas réécrire un document déjà envoyé au client**.

**Acceptance Criteria**
- [ ] `Report` (document logique) + `ReportVersion` (version physique)
- [ ] Un rapport transmis reste stable ; une correction → nouvelle version
- [ ] API : `POST /interventions/{id}/reports`, `GET /reports/{id}`, `GET /reports/{id}/versions/{v}`
- [ ] PDF réutilisé (WeasyPrint)

**Technical Notes**
- Reshape `ReportExporter` existant → versionnement
- Fichiers : `app/models/report.py`, `app/services/report.py`, `app/exporters/`

---

## INT-108 — Avis client (2 pts)

**User Story**
En tant que **client**,
Je veux **laisser un avis après intervention**,
Afin de **donner un retour sur l'expérience**.

**Acceptance Criteria**
- [ ] `Review` : `intervention_id` (UNIQUE), `rating`, `comment`
- [ ] `Intervention 1 → 0..1 Review`
- [ ] API publique `POST /reviews` (share_token) conservée

**Technical Notes**
- Reshape l'existant `Review` → FK `intervention` (aujourd'hui `job`)
- Fichiers : `app/models/review.py`, `app/services/review.py`, `app/api/v1/reviews.py`

---

## Lot 5 — Showroom + remplacement (7 pts)

> Dépend du Lot 1 (et du Lot 3 pour le lien showroom → vente).

---

## INT-109 — ShowroomVisit (4 pts)

**User Story**
En tant que **commercial**,
Je veux **enregistrer une visite showroom avec les produits présentés**,
Afin de **suivre le parcours prospect → vente**.

**Acceptance Criteria**
- [ ] `ShowroomVisit` : `client_id` (nullable), `visitor_name`, `visited_at`, `salesperson_id`, `follow_up_status`, `notes`
- [ ] `ShowroomVisitProduct` : `visit_id`, `product_id` (N↔N)
- [ ] `follow_up_status` ∈ `TO_FOLLOW_UP / CONSIDERING / QUOTE_REQUESTED / QUOTE_SENT / SOLD / LOST / NO_FURTHER_ACTION`
- [ ] API : `GET/POST /showroom/visits`, `POST /showroom/visits/{id}/products`

**Technical Notes**
- `client_id` nullable : prospect pas encore client (`visitor_name` requis en secours)
- Fichiers : `app/models/showroom.py`, `app/services/showroom.py`, `app/api/v1/showroom.py`

---

## INT-110 — Remplacement d'équipement (3 pts)

**User Story**
En tant que **technicien**,
Je veux **remplacer un équipement défaillant**,
Afin de **conserver l'historique de l'ancien et ouvrir un nouveau cycle**.

**Acceptance Criteria**
- [ ] `POST /equipment/{id}/replace` : ancien → `REPLACED` + `replaced_by_id` → nouveau
- [ ] Nouvel équipement : nouveau `serial_number`, `installed_at`, `warranty_*`
- [ ] L'ancien conserve ses interventions, rapports, photos
- [ ] Test : remplacer → ancien pointe vers nouveau, historique intact

**Technical Notes**
- Transaction métier (état ancien + création nouveau atomiques)
- Fichiers : `app/services/equipment.py`, `app/api/v1/equipment.py`

---

## Lot 6 — Déploiement + doc entretien (8 pts)

> Reprend et finalise l'ancien sprint 6.4/6.5, sur le modèle v2.

---

## INT-111 — Déploiement VPS (5 pts)

**User Story**
En tant que **gérant**,
Je veux **déployer Tervo v2 sur un VPS en production**,
Afin de **disposer d'une instance publique avec HTTPS**.

**Acceptance Criteria**
- [ ] VPS : Ubuntu 24.04, SSH clé, ufw (22/80/443), fail2ban
- [ ] Docker + 1Panel + Let's Encrypt
- [ ] CI/CD : GitHub Actions → tests → SSH → `git pull` → `docker compose up -d` (un seul build)
- [ ] PostgreSQL sans port publié ; services bind `127.0.0.1`
- [ ] `curl` frontend + API → 200

**Technical Notes**
- Réutilise `notes/backend/deploy/` + `.github/workflows/ci.yml` (déjà prêts)

---

## INT-112 — Doc entretien (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **une fiche d'architecture et un Q/R entretien**,
Afin de **présenter le projet avec crédibilité (profil backend Java/Go)**.

**Acceptance Criteria**
- [ ] Fiche archi : chaîne Client→Site→Equipment→Intervention + migration
- [ ] Q/R : pourquoi la migration est transverse, pourquoi 3 zones, pourquoi transactions par batch
- [ ] Périmètre crédibilité : ne pas survendre Vue/TS, GH Actions, VPS, 1Panel
- [ ] Fichiers : `notes/interview/`

**Technical Notes**
- Le différenciateur = la migration Excel (pandas, fuzzy, 2 passes, transactions)

---

## Tests Cases Sprint 6.2-v2

Les tests cases détaillés sont dans `test-cases.json`.
