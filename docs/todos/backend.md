# Todos Backend — Tervo

> Fichier central des fonctionnalités backend reportées.  
> Scanné à chaque fin de tâche pour voir si des dépendances sont débloquées.  
> Ordonné par priorité (urgence décroissante).

---

## TD-B001 — Extraction seed checklist dans ChecklistService

| Champ         | Valeur                                                                  |
| ------------- | ----------------------------------------------------------------------- |
| **Créé dans** | INT-17 (Sprint 1.3)                                                     |
| **Dépend de** | Aucune (modèle et seed existent déjà dans INT-09)                       |
| **Fichiers**  | `app/repositories/job.py`, `app/services/checklist.py` (nouveau)        |
|               | `app/repositories/checklist.py` (nouveau)                               |
| **Action**    | Extraire `_seed_checklist()` de `JobRepository` vers `ChecklistService` |
|               | Extraire `validate_all_checked()` dans `ChecklistService`               |
|               | Créer `ChecklistRepository` pour les accès DB checklist                 |
| **Statut**    | ✅ Fait (INT-17 terminé — service/repo extraits)                        |

---

## TD-B002 — Endpoint `POST /api/v1/auth/register`

| Champ         | Valeur                                                 |
| ------------- | ------------------------------------------------------ |
| **Créé dans** | Spec API `03-api-spec.md`                              |
| **Dépend de** | Aucune                                                 |
| **Fichiers**  | `app/api/v1/auth.py`                                   |
| **Action**    | Ajouter un endpoint de création de compte (admin only) |
| **Statut**    | ⏳ Non prioritaire                                     |

---

## TD-B003 — Relations `job.photos`, `job.materials`, `job.review`

| Champ         | Valeur                                                             |
| ------------- | ------------------------------------------------------------------ |
| **Créé dans** | INT-08 (Modèle Job)                                                |
| **Dépend de** | Modèle `Review` (Phase 2) — `JobPhoto` ✅ et `Material` ✅ activés |
| **Fichiers**  | `app/models/job.py`                                                |
| **Action**    | Ajouter `job.review` quand le modèle `Review` sera créé            |
| **Statut**    | ✅ Fait — `photos` (INT-22), `materials` (INT-25), `review` (INT-31) |

---

## TD-B004 — Validation photos dans `PUT /jobs/{id}/complete`

| Champ         | Valeur                                                                     |
| ------------- | -------------------------------------------------------------------------- |
| **Créé dans** | INT-11 (spec)                                                              |
| **Dépend de** | TD-B003 + Endpoint upload photos — ✅ upload (INT-23) + delete (INT-24) OK |
| **Fichiers**  | `app/services/job.py` → méthode `complete_job()`                           |
| **Action**    | Ajouter vérification : `min. 1 photo avant + 1 photo après`                |
| **Statut**    | ⏳ Bloqué — Phase 2                                                        |

---

## TD-B005 — Génération PDF du rapport (WeasyPrint)

| Champ         | Valeur                                                      |
| ------------- | ----------------------------------------------------------- |
| **Créé dans** | Roadmap Phase 2                                             |
| **Dépend de** | Modèle `JobPhoto`, installation WeasyPrint                  |
| **Fichiers**  | `app/exporters/report.py`, `app/exporters/report_template.html` |
| **Action**    | Générer PDF avec client, checklist, photos, matériaux       |
| **Statut**    | ✅ Fait (INT-29 — ReportExporter + template Jinja2)          |

---

## TD-B006 — Review client (avis + share_token)

| Champ         | Valeur                                          |
| ------------- | ----------------------------------------------- |
| **Créé dans** | Data model `review`                             |
| **Dépend de** | Modèle `Review` (Phase 2)                       |
| **Fichiers**  | `app/models/review.py`, `app/api/v1/reviews.py` |
| **Action**    | Créer le modèle + endpoints publics             |
| **Statut**    | ✅ Fait — Modèle (INT-31) + GET (INT-32) + POST submit (INT-33) |

---

## TD-B008 — Créer la base PostgreSQL `tervo_db` sur le serveur

| Champ         | Valeur                                                          |
| ------------- | --------------------------------------------------------------- |
| **Créé dans** | INT-50 (Sprint 3.1)                                             |
| **Dépend de** | Container PostgreSQL running sur le serveur (`postgres:17.4`)    |
| **Fichiers**  | — (commande Docker exec)                                         |
| **Action**    | Exécuter sur le serveur :                                        |
|               | `docker exec -it postgres psql -U postgres -c "CREATE DATABASE tervo_db;"` |
|               | `docker exec -it postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tervo_db TO lob;"` |
| **Statut**    | ⏳ À faire dans INT-DPL                                          |

---

## TD-B009 — Vérifier les privilèges PostgreSQL après création

| Champ         | Valeur                                                          |
| ------------- | --------------------------------------------------------------- |
| **Créé dans** | INT-50 (Sprint 3.1)                                             |
| **Dépend de** | TD-B008                                                         |
| **Fichiers**  | — (commande Docker exec)                                         |
| **Action**    | Vérifier que `lob` a les droits sur `tervo_db` :                  |
|               | `docker exec -it postgres psql -U postgres -c "\l"`             |
|               | `docker exec -it postgres psql -U lob -d tervo_db -c "\dt"`      |
| **Statut**    | ⏳ À faire dans INT-DPL (après TD-B008)                          |

---

## TD-B010 — PostgreSQL embarqué : migration des données existantes

| Champ         | Valeur                                                          |
| ------------- | --------------------------------------------------------------- |
| **Créé dans** | INT-67 (Sprint 6.1 — consolidation du compose)                  |
| **Dépend de** | Sprint 6.4 (INT-87, déploiement VPS)                            |
| **Fichiers**  | `deploy/docker-compose.yml`, `deploy/postgres.docker-compose.yml` |
| **Action**    | Le compose principal embarque désormais son propre service `postgres` (conteneur `tervo-postgres-1`, volume `postgres_data`). L'ancien conteneur partagé `postgres` (compose `postgres.docker-compose.yml`) contient les données actuelles (`tervo_db`). |
|               | **Décider** : (a) migrer les données de `postgres` vers `tervo-postgres-1`, ou (b) conserver le PG partagé et retirer le service embarqué. |
|               | Migration si option (a) :                                          |
|               | `docker exec postgres pg_dump -U lob tervo_db \| gzip > tervo_db.sql.gz` |
|               | `gunzip -c tervo_db.sql.gz \| docker exec -i tervo-postgres-1 psql -U lob -d tervo_db` |
| **Statut**    | ⏳ À traiter dans INT-87 (Sprint 6.4)                            |
