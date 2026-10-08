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
| **Statut**    | ⏳ Différé — Phase 2 ; INT-105 livre les usages BEFORE/AFTER mais ne valide pas cette règle supplémentaire de clôture |

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
| **Dépend de** | INT-125 (configuration), INT-127 (cible/décision SQL) |
| **Fichiers**  | `deploy/docker-compose.yml`, `deploy/.env.example`, procédure INT-127 |
| **Action**    | Préparer la DB cible avec les noms/rôles réellement choisis. INT-125 ne crée que des DB de recette jetables ; ne pas supposer le rôle `postgres`/`lob` ou un conteneur issu du mini-s1. Les anciennes commandes CREATE/GRANT sont des exemples historiques, pas une procédure VPS autorisée. |
| **Statut**    | ⏳ Ouvert, reprise INT-127 ; aucune DB réelle créée par INT-125 |

---

## TD-B009 — Vérifier les privilèges PostgreSQL après création

| Champ         | Valeur                                                          |
| ------------- | --------------------------------------------------------------- |
| **Créé dans** | INT-50 (Sprint 3.1)                                             |
| **Dépend de** | TD-B008, INT-127 ; constat enrichi dans INT-125 |
| **Fichiers**  | `deploy/docker-compose.yml`, `backend/app/config.py`, procédure SQL INT-127 |
| **Action**    | Cadrer les rôles bootstrap/migration/application et tester leurs privilèges avant release réelle. `POSTGRES_USER` de l'image officielle crée un superuser ; le rôle partagé de la recette INT-125 ne prouve pas un moindre privilège. Vérifier le rôle courant et les accès réels, sans présumer `lob`/`postgres`, ni modifier une DB existante pour rendre la recette verte. |
| **Statut**    | ⏳ Ouvert, dépendance INT-127 non débloquée ; ne pas clôturer sur la seule santé de la stack |

---

## TD-B010 — PostgreSQL embarqué : migration des données existantes

| Champ         | Valeur                                                          |
| ------------- | --------------------------------------------------------------- |
| **Créé dans** | INT-67 (Sprint 6.1 — consolidation du compose)                  |
| **Dépend de** | Sprint 7.6 : INT-127 (cible/décision), INT-128 (backup/restore), INT-111 (application réelle du plan) |
| **Fichiers**  | `deploy/docker-compose.yml`, `deploy/postgres.docker-compose.yml` |
| **Action**    | Inventorier la source réelle mini-s1 ou confirmer le démarrage vide ; préparer une seule DB Compose sur le VPS. L'ancien PG partagé documenté ne prouve pas quelles données doivent être transférées aujourd'hui. |
|               | **Décider** la reprise en INT-127, vérifier backup/restore en INT-128, appliquer le choix en INT-111. Ne présumer ni conteneur, rôle, volume physique ni version. |
|               | Exemples historiques mini-s1 uniquement, à ne pas exécuter sans inventaire et procédure adaptée : |
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
| **Fichiers** | `app/modules/identity/models.py` (déplacé dans INT-122), `app/modules/catalog/api.py` (déplacé dans INT-115), migrations, tests |
| **Action attendue** | Étendre le contrôle catalogue_editor à ces rôles et tester leurs droits. Dans INT-109, cadrer aussi leurs droits showroom et l'attribution d'un commercial actif ; actuellement ADMIN seul accède au showroom, TECHNICIAN reste exclu des visites. |
| **Statut** | ⏳ Rôles absents du modèle actuel ; INT-109 n'introduit pas de faux rôle COMMERCIAL/MANAGER |


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
| **Fichiers** | `app/modules/imports/pipeline/{validators,matcher,multi_matcher}.py`, `app/modules/imports/{service,models,api}.py` (chemins actualisés par INT-121) |
| **Action attendue** | Résoudre les références dans leur namespace ; prouver toute association client avant de rendre MISSING_PHONE non bloquant ; appliquer les décisions validées (site/titre, statut historique, doublons et remplacement), puis enregistrer provenance/actions. Ne jamais écrire directement les dictionnaires normalized contenant des valeurs absentes sur un client existant. Vérifier les doublons d’interventions inter-fichiers et les orphelins C999. |
| **Statut** | ✅ Fait (INT-99 à INT-101) — décisions explicites, sources conservées, reprise, arbitrage inter-fichiers et API admin testés |


---

## TD-B016 — Mesurer l’import sur un volume représentatif

| Champ | Valeur |
| --- | --- |
| **Créé dans** | INT-100 |
| **Dépend de** | Échantillon anonymisé représentatif avant migration réelle |
| **Fichiers** | `app/modules/imports/pipeline/excel_reader.py`, `app/modules/imports/planner.py`, `app/modules/imports/service.py` (déplacés dans INT-121) |
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
| **Dépend de** | Cutovers terrain/reports acceptés ; mise à jour documentaire distincte autorisée avant les features 7.4 |
| **Fichiers** | `docs/stages/stage7/sprint7.4/tasks.md`, `test-cases.json`, DAT si autorisé dans son propre scope ; `app/modules/interventions/`, `app/modules/reports/{api,renderer}.py`, `app/modules/reports/templates/report_template.html` |
| **Action attendue** | Remplacer les anciens chemins horizontaux par les sources terrain actuelles, sans cocher ni implémenter INT-104 à INT-108. Reprendre le mapping de la note INT-119. Les nouveaux modèles/fichiers éventuels restent à cadrer par feature ; les cas détaillés INT-105/108 restent à compléter avant implémentation. |
| **Statut** | ✅ Chemins du planning 7.4 repris au démarrage d'INT-104 : sources terrain/rapports modulaires et distinction des fichiers futurs ; aucun critère INT-105 à INT-108 coché, aucun changement du DAT ni réalisation métier déduit de cette reprise |

---

## TD-B019 — Cadrer l'usage sûr du seed de démonstration

| Champ | Valeur |
|---|---|
| **Créé dans** | INT-122 / R10, vérification réelle du bootstrap démo |
| **Dépend de** | INT-126 (bootstrap production sûr), INT-111 (usage réel) ; aucun seed sur base persistante sans cadrage dédié |
| **Fichiers** | `app/seed.py`, procédures de déploiement, futurs tests de protection si autorisés |
| **Action attendue** | Séparer/cadrer l'usage démo de la migration/production, définir la protection contre un seed destructif accidentel et documenter les préconditions. Le script actuel effectue des DELETE et ne nettoie pas toute la chaîne V2 ; la répétition testée sur sa propre SQLite démo ne garantit pas la sûreté sur une base peuplée. Ne pas modifier ou vider une base existante pour valider ce todo. |
| **Statut** | ⏳ À cadrer avant tout usage du seed avec des données existantes ; aucun changement de CLI/comportement dans R10 |

---

## TD-B020 — Compléter la traçabilité et la maintenance du stockage photo

| Champ | Valeur |
|---|---|
| **Créé dans** | INT-105, sprint7.4 |
| **Dépend de** | Cadrage dédié des métadonnées/audits prévus au DAT ; INT-107 pour les règles après transmission d'un rapport |
| **Fichiers** | `app/modules/interventions/models/photo.py`, `services/photo.py`, `app/modules/reports/`, migrations et procédures de maintenance |
| **Action attendue** | Cadrer la persistance du nom original, MIME, taille et l'audit/contrôle des suppressions historiques. Définir une réconciliation sûre DB/filesystem : les compensations d'upload contrôlé existent, mais un crash ou une erreur filesystem après commit peut laisser un orphelin. Ne jamais supprimer arbitrairement des fichiers d'un répertoire réel pour tester ce sujet. |
| **Statut** | ⏳ Différé ; INT-107 archive les octets PDF séparément des photos et garde ses versions stables, mais ne livre ni audit/suppression contrôlée des originaux photo, ni réconciliation du filesystem. Politique métier restante à cadrer. |

---

## TD-B021 — Arbitrer les issues historiques confirmées

| Champ | Valeur |
|---|---|
| **Créé dans** | INT-106, sprint7.4 |
| **Dépend de** | Mapping historique et arbitrages métier explicitement validés avant import réel |
| **Fichiers** | `app/modules/imports/{planner,service}.py`, sources archivées, tests et éventuelles migrations de données |
| **Action attendue** | Cadrer l'utilisation des issues présentes dans les archives sans inférer RESOLVED d'un statut COMPLETED ou d'une note client. Conserver provenance et décisions, tester les valeurs inconnues et l'invalidation des approbations quand un résultat réel change. |
| **Statut** | ⏳ À cadrer ; INT-106 conserve result null dans l'historique, n'effectue aucun backfill fictif et protège les empreintes d'import |

---

## TD-B022 — Mesurer et sauvegarder les PDF versionnés en base

| Champ | Valeur |
|---|---|
| **Créé dans** | INT-107, sprint7.4 |
| **Dépend de** | Volumétrie représentative, INT-128 (backup/restore BYTEA), INT-111 (déploiement réel) |
| **Fichiers** | `app/modules/reports/{models,service}.py`, `deploy/`, procédure PostgreSQL INT-111 |
| **Action attendue** | Mesurer taille cumulée des versions PDF `BYTEA`, temps de génération/lecture et volume des sauvegardes. Vérifier une restauration qui conserve PDF, empreinte et date de confirmation. Selon les mesures, décider si un stockage privé externe avec réconciliation transactionnelle est requis ; ne pas exposer les fichiers dans `/uploads`. |
| **Statut** | ⏳ Ouvert ; les tests jetables INT-107 ne prouvent ni tenue au volume ni restauration/déploiement VPS |

---

## TD-B023 — Attribuer explicitement une vente à une visite showroom

| Champ | Valeur |
|---|---|
| **Créé dans** | INT-109, sprint7.5 |
| **Dépend de** | Arbitrage métier du lien visite → vente (cardinalité et attribution) et rôles commerciaux TD-B013 |
| **Fichiers** | `app/modules/showroom/`, `app/modules/sales/`, migration et contrats API |
| **Action attendue** | Définir comment enregistrer une vente provenant réellement d'une visite, sans inférer sa provenance d'un simple `client_id` ou du statut `SOLD` : un même client peut avoir plusieurs visites et plusieurs ventes. Choisir cardinalité, responsabilité de l'attribution et comportement d'un prospect non encore client avant implémentation. Ne pas inventer d'entité Quote V1. |
| **Statut** | ⏳ Cadrage métier requis ; INT-109 conserve événements, clients, produits et suivi sans créer de lien vente non prouvé |
