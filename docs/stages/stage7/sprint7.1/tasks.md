# Sprint 7.1 — Socle physique

> **Tervo V2** · INT-94 à INT-97 · **Statut :** Terminé
> **Dépendances :** Socle existant des stages précédents.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes :** [notes/backend/sprint7.1](../../../../notes/backend/sprint7.1/)

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

## Cas de test

Voir [test-cases.json](test-cases.json).
