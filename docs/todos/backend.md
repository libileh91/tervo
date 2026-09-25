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

---

## TD-B011 — Tests contre PostgreSQL dans la CI

| Champ         | Valeur                                                          |
| ------------- | --------------------------------------------------------------- |
| **Créé dans** | INT-70 (Sprint 6.1 — CI/CD)                                     |
| **Dépend de** | Aucune (évolution identifiée, non bloquante)                    |
| **Fichiers**  | `.github/workflows/ci.yml`, `backend/tests/`                    |
| **Action**    | Les tests utilisent SQLite (`sqlite+aiosqlite:///./test_tervo.db`). Envisager un service PostgreSQL dans la CI pour détecter les écarts de dialecte (enums, contraintes `CHECK`, colonnes générées, index). |
|               | Piste : ajouter un service `postgres` au job `backend-tests` et surcharger `DATABASE_URL`. |
| **Statut**    | ⏳ Évolution — à planifier si des bugs spécifiques PostgreSQL apparaissent |


---

## TD-B012 — Relation Product → Equipment et test multi-instances

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-96 |
| **Dépend de** | INT-97 — entité Equipment |
| **Fichiers** | `app/models/product.py`, futur `app/models/equipment.py`, migrations, `tests/test_products.py` |
| **Action attendue** | Ajouter Equipment.product_id (FK non unique), relations ORM bidirectionnelles ; tester deux équipements distincts du même produit puis la conservation des liens après désactivation. Valider les deux critères INT-96 restants. |
| **Statut** | ✅ Fait dans INT-97 — relations ORM et test de deux appareils conservés après désactivation |

## TD-B013 — Droits catalogue MANAGER / COMMERCIAL

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-96 |
| **Dépend de** | Introduction des rôles MANAGER et COMMERCIAL prévus par la DAT |
| **Fichiers** | `app/models/user.py`, `app/api/v1/products.py`, migrations, tests |
| **Action attendue** | Étendre le contrôle catalogue_editor à ces rôles et tester leurs droits. Actuellement ADMIN écrit, TECHNICIAN consulte. |
| **Statut** | ⏳ Rôles absents du modèle actuel |


---

## TD-B014 — Raccorder Equipment à Installation

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-97 |
| **Dépend de** | INT-103 — entité Installation |
| **Fichiers** | `app/models/equipment.py`, futur `app/models/installation.py`, migration, services et tests |
| **Action attendue** | Ajouter la FK Equipment.installation_id, son unicité (Installation 1 → 0..1 Equipment) et les relations ORM. Alimenter ce champ uniquement lors de la réalisation d’une installation, en vérifiant site et produit. La colonne reste nullable pour les imports historiques. |
| **Statut** | ⏳ En attente d’INT-103 ; aucun identifiant libre accepté par l’API actuelle |

---

## TD-B015 — Consommer les candidats et arbitrages INT-98

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-98 |
| **Dépend de** | INT-99 (matching), INT-100 (persistance), INT-101 (API et décisions) |
| **Fichiers** | `app/importers/validators.py`, `matcher.py`, `app/services/import_service.py`, futurs modèles ImportRecord/ImportError et API admin |
| **Action attendue** | Résoudre les références dans leur namespace ; prouver toute association client avant de rendre MISSING_PHONE non bloquant ; appliquer les décisions validées (site/titre, statut historique, doublons et remplacement), puis enregistrer provenance/actions. Ne jamais écrire directement les dictionnaires normalized contenant des valeurs absentes sur un client existant. Vérifier les doublons d’interventions inter-fichiers et les orphelins C999. |
| **Statut** | ⏳ INT-99 et INT-100 faits : rapprochement, décisions et persistance testés ; reste l’exposition API INT-101 |


---

## TD-B016 — Mesurer l’import sur un volume représentatif

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-100 |
| **Dépend de** | Échantillon anonymisé représentatif avant migration réelle |
| **Fichiers** | `app/importers/excel_reader.py`, `app/services/import_planner.py`, `app/services/import_service.py` |
| **Action attendue** | Mesurer mémoire, durée, coût du rapprochement et attente des verrous PostgreSQL ; définir le découpage des archives. Selon les mesures, ajouter index de candidats, lecture en flux ou worker asynchrone. Le lecteur et le référentiel sont actuellement chargés en mémoire ; les transactions de 500 lignes ne garantissent pas le passage à l’échelle. |
| **Statut** | ⏳ À mesurer avant import réel ; pack fictif et scénario de 502 lignes validés |
