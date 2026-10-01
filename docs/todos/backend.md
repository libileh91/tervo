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
| **Fichiers**  | Sources actuelles : `app/modules/interventions/repositories/intervention.py`, `app/modules/interventions/services/checklist.py` |
|               | `app/modules/interventions/repositories/checklist.py` (chemins actualisés par INT-119 ; réalisation historique inchangée) |
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
| **Fichiers**  | Source actuelle : `app/modules/interventions/models/intervention.py` (ancien Job ; déplacé dans INT-119) |
| **Action**    | Ajouter `job.review` quand le modèle `Review` sera créé            |
| **Statut**    | ✅ Fait — `photos` (INT-22), `materials` (INT-25), `review` (INT-31) |

---

## TD-B004 — Validation photos dans `PUT /jobs/{id}/complete`

| Champ         | Valeur                                                                     |
| ------------- | -------------------------------------------------------------------------- |
| **Créé dans** | INT-11 (spec)                                                              |
| **Dépend de** | TD-B003 + Endpoint upload photos — ✅ upload (INT-23) + delete (INT-24) OK |
| **Fichiers**  | Source actuelle : `app/modules/interventions/services/intervention.py` → `complete_intervention()` (déplacé dans INT-119) |
| **Action**    | Ajouter vérification : `min. 1 photo avant + 1 photo après`                |
| **Statut**    | ⏳ Bloqué — Phase 2                                                        |

---

## TD-B005 — Génération PDF du rapport (WeasyPrint)

| Champ         | Valeur                                                      |
| ------------- | ----------------------------------------------------------- |
| **Créé dans** | Roadmap Phase 2                                             |
| **Dépend de** | Modèle `JobPhoto`, installation WeasyPrint                  |
| **Fichiers**  | `app/modules/reports/renderer.py`, `app/modules/reports/templates/report_template.html` (déplacés dans INT-120) |
| **Action**    | Générer PDF avec client, checklist, photos, matériaux       |
| **Statut**    | ✅ Fait (INT-29 — ReportExporter + template Jinja2)          |

---

## TD-B006 — Review client (avis + share_token)

| Champ         | Valeur                                          |
| ------------- | ----------------------------------------------- |
| **Créé dans** | Data model `review`                             |
| **Dépend de** | Modèle `Review` (Phase 2)                       |
| **Fichiers**  | `app/modules/interventions/models/review.py`, `app/modules/interventions/api/reviews.py` (déplacés dans INT-119) |
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
| **Dépend de** | Sprint 7.6 (INT-111, déploiement VPS)                            |
| **Fichiers**  | `deploy/docker-compose.yml`, `deploy/postgres.docker-compose.yml` |
| **Action**    | Le compose principal embarque désormais son propre service `postgres` (conteneur `tervo-postgres-1`, volume `postgres_data`). L'ancien conteneur partagé `postgres` (compose `postgres.docker-compose.yml`) contient les données actuelles (`tervo_db`). |
|               | **Décider** : (a) migrer les données de `postgres` vers `tervo-postgres-1`, ou (b) conserver le PG partagé et retirer le service embarqué. |
|               | Migration si option (a) :                                          |
|               | `docker exec postgres pg_dump -U lob tervo_db \| gzip > tervo_db.sql.gz` |
|               | `gunzip -c tervo_db.sql.gz \| docker exec -i tervo-postgres-1 psql -U lob -d tervo_db` |
| **Statut**    | ⏳ À traiter dans INT-111 (Sprint 7.6)                            |

---

## TD-B011 — Tests contre PostgreSQL dans la CI

| Champ         | Valeur                                                          |
| ------------- | --------------------------------------------------------------- |
| **Créé dans** | INT-70 (Sprint 6.1 — CI/CD)                                     |
| **Dépend de** | Aucune (évolution identifiée, non bloquante)                    |
| **Fichiers**  | `.github/workflows/ci.yml`, `backend/tests/`                    |
| **Action**    | Les tests utilisent SQLite (`sqlite+aiosqlite:///./test_tervo.db`). Envisager un service PostgreSQL dans la CI pour détecter les écarts de dialecte (enums, contraintes `CHECK`, colonnes générées, index). |
|               | Piste : ajouter un service `postgres` au job `backend-tests` et surcharger `DATABASE_URL`. |
| **Statut**    | ✅ Fait (INT-101) — PostgreSQL 17.4 en CI : migrations aller/retour + tests du service d’import et de l’API admin ; suite générale conservée sur SQLite |


---

## TD-B012 — Relation Product → Equipment et test multi-instances

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-96 |
| **Dépend de** | INT-97 — entité Equipment |
| **Fichiers** | `app/modules/catalog/models.py` (déplacé dans INT-115), `app/modules/equipment/models.py` (déplacé dans INT-117), migrations, `tests/test_products.py` |
| **Action attendue** | Ajouter Equipment.product_id (FK non unique), relations ORM bidirectionnelles ; tester deux équipements distincts du même produit puis la conservation des liens après désactivation. Valider les deux critères INT-96 restants. |
| **Statut** | ✅ Fait dans INT-97 — relations ORM et test de deux appareils conservés après désactivation |

## TD-B013 — Droits catalogue MANAGER / COMMERCIAL

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-96 |
| **Dépend de** | Introduction des rôles MANAGER et COMMERCIAL prévus par la DAT |
| **Fichiers** | `app/models/user.py`, `app/modules/catalog/api.py` (déplacé dans INT-115), migrations, tests |
| **Action attendue** | Étendre le contrôle catalogue_editor à ces rôles et tester leurs droits. Actuellement ADMIN écrit, TECHNICIAN consulte. |
| **Statut** | ⏳ Rôles absents du modèle actuel |


---

## TD-B014 — Raccorder Equipment à Installation

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-97 |
| **Dépend de** | INT-103 — entité Installation |
| **Fichiers** | `app/modules/equipment/models.py` (déplacé dans INT-117), `app/modules/installations/models.py` (déplacé dans INT-118), migration, services et tests |
| **Action attendue** | Ajouter la FK Equipment.installation_id, son unicité (Installation 1 → 0..1 Equipment) et les relations ORM. Alimenter ce champ uniquement lors de la réalisation d’une installation, en vérifiant site et produit. La colonne reste nullable pour les imports historiques. |
| **Statut** | ✅ Fait dans INT-103 autonome (28/09/2026) — FK nullable + unicité + relations ORM ; clôture atomique créer/rattacher, site vérifié et produit catalogue validé à la création/conservé au rattachement. Tests SQLite et PostgreSQL. Cohérence avec un produit vendu reportée à TD-B017. |

---

## TD-B015 — Consommer les candidats et arbitrages INT-98

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-98 |
| **Dépend de** | INT-99 (matching), INT-100 (persistance), INT-101 (API et décisions) |
| **Fichiers** | `app/importers/validators.py`, `matcher.py`, `app/services/import_service.py`, futurs modèles ImportRecord/ImportError et API admin |
| **Action attendue** | Résoudre les références dans leur namespace ; prouver toute association client avant de rendre MISSING_PHONE non bloquant ; appliquer les décisions validées (site/titre, statut historique, doublons et remplacement), puis enregistrer provenance/actions. Ne jamais écrire directement les dictionnaires normalized contenant des valeurs absentes sur un client existant. Vérifier les doublons d’interventions inter-fichiers et les orphelins C999. |
| **Statut** | ✅ Fait (INT-99 à INT-101) — décisions explicites, sources conservées, reprise, arbitrage inter-fichiers et API admin testés |


---

## TD-B016 — Mesurer l’import sur un volume représentatif

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-100 |
| **Dépend de** | Échantillon anonymisé représentatif avant migration réelle |
| **Fichiers** | `app/importers/excel_reader.py`, `app/services/import_planner.py`, `app/services/import_service.py` |
| **Action attendue** | Mesurer mémoire, durée, coût du rapprochement et attente des verrous PostgreSQL ; définir le découpage des archives. Selon les mesures, ajouter index de candidats, lecture en flux ou worker asynchrone. Le lecteur et le référentiel sont actuellement chargés en mémoire ; les transactions de 500 lignes ne garantissent pas le passage à l’échelle. |
| **Statut** | ⏳ À mesurer avant import réel ; pack fictif et scénario de 502 lignes validés |

---

## TD-B017 — Raccorder les installations autonomes à SaleLine

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-103 partielle, sprint7.3 ; inversion INT-103 avant INT-102 explicitement validée |
| **Dépend de** | INT-102 — véritables entités Sale et SaleLine |
| **Fichiers** | `app/modules/installations/{models,schemas,service}.py` (déplacés dans INT-118), migration Alembic, `tests/test_installations.py`, `docs/stages/stage7/sprint7.3/test-cases.json` |
| **Action attendue** | Ajouter sale_line_id comme FK nullable (pas d'entier libre), sans inventer de ventes pour les installations existantes. Exposer/accepter absent ou null ; vérifier les références non nulles et leur provenance commerciale, cohérence vente/site/produit et règles de quantité/statut validées pour INT-102. Tester le parcours vendu, la ligne inconnue (404), le produit du matériel créé/rattaché et la non-régression autonome. |
| **Contrat intermédiaire historique** | Avant INT-102 : aucun champ sale_line_id en ORM, migration ou réponse API ; sa présence donnait 422. Ce contrat est remplacé par le contrat actuel ci-dessous, pas réactivé par le refactor. |
| **Contrat actuel** | Depuis INT-102 : FK nullable `Installation.sale_line_id → SaleLine.id`, parcours autonome absent/null accepté, provenance commerciale vérifiée. R4/INT-116 déplace SaleLine dans `app/modules/sales/models.py` ; R6/INT-118 déplace Installation et son orchestration dans `app/modules/installations/`, sans modifier ce contrat ni ses transactions. |
| **Statut** | ✅ Fait avec INT-102 (29/09/2026) : FK nullable et réponse `sale_line_id: null` pour le parcours autonome ; référence confirmée vérifiée, cohérence site/produit/quantité appliquée et parcours vendu testé. TD-B014 reste réalisé. |

---

## TD-B018 — Reprendre les chemins terrain du planning 7.4 après le refactor

| Champ | Valeur |
|---|---|
| **Créé dans** | INT-119 / R7, refactor monolithe modulaire |
| **Dépend de** | Cutover terrain accepté ; mise à jour documentaire distincte autorisée avant les features 7.4 ; chemins reports définis par R8, clôture R8 encore à accepter |
| **Fichiers** | `docs/stages/stage7/sprint7.4/tasks.md`, `test-cases.json`, DAT si autorisé dans son propre scope ; `app/modules/interventions/`, `app/modules/reports/{api,renderer}.py`, `app/modules/reports/templates/report_template.html` |
| **Action attendue** | Remplacer les anciens chemins horizontaux par les sources terrain actuelles, sans cocher ni implémenter INT-104 à INT-108. Reprendre le mapping de la note INT-119. Les nouveaux modèles/fichiers éventuels restent à cadrer par feature ; les cas détaillés INT-105/108 restent à compléter avant implémentation. |
| **Statut** | ⏳ À traiter dans une reprise documentaire autorisée avant 7.4 ; aucune feature terrain nouvelle livrée par R7 |
