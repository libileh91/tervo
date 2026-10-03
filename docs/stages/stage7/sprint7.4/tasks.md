# Sprint 7.4 — Cycle terrain

> **Tervo V2** · INT-104 à INT-108 · **Statut :** INT-104 à INT-106 implémentées et vérifiées localement ; INT-107 et INT-108 à traiter
> **Dépendances :** Sprint 7.1 ; réutiliser les modules terrain existants.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.4/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

> Réutilise les modules terrain et rapports actuels : `app/modules/interventions/`
> et `app/modules/reports/`. Les noms historiques (`job_photo`, etc.) ne désignent
> pas de nouveaux fichiers à recréer. Dépend du Sprint 7.1.

---

## INT-104 — Checklist modèle + snapshot (5 pts)

**User Story**
En tant que **gérant**,
Je veux **définir des modèles de checklist par type d'intervention**,
Afin de **standardiser les contrôles sans réécrire l'historique des interventions passées**.

**Acceptance Criteria**
- [x] `ChecklistTemplate` : `intervention_type`, `name` (+ items modifiables)
- [x] `InterventionChecklist` : snapshot généré à la création de l'intervention
- [x] `ChecklistItem` : historique (`result`, `comment`)
- [x] Règle : modifier un modèle ne modifie **pas** les checklists passées
- [x] API : `GET/POST /checklist-templates`, `GET /interventions/{id}/checklist`, `PATCH /checklist-items/{id}`

**Validation locale**
- Suite backend : 450 réussis, 6 cas PostgreSQL ignorés dans ce run, 7 warnings.
- Run PostgreSQL 17.4 dédié : 132 réussis, incluant les cas ignorés ci-dessus,
  les migrations et les courses PATCH/clôture/annulation.
- Frontend : 4 tests de brouillons, typecheck et build réussis.
- Smoke navigateur réel : login, snapshot, sauvegarde partiellement échouée,
  saisies conservées, réessai, clôture et téléchargement PDF réussis.
- `alembic check` reste à 255 uniquement pour la FK technicien historique ;
  comparaison structurée sans nouvel écart INT-104.
- Preuves et limites : [note pédagogique](../../../../notes/backend/sprint7.4/INT-104-checklist-modeles-snapshots.md).
- Aucun run CI distant INT-104 ni déploiement revendiqué par cette validation.

**Technical Notes**
- Remplace `checklist_item` (plat) → modèle réutilisable / snapshot historique / items.
- Choix validé : sélection explicite par `InterventionCreate.checklist_template_id`
  (optionnel, positif), sans inventer de classification des interventions. Sans
  sélection, snapshot des cinq contrôles par défaut ; aucune sélection automatique
  fondée sur `intervention_type`.
- Création intervention + snapshot + items dans une transaction unique. Copie du
  nom, de la version, des libellés, catégories et positions ; changer le modèle
  n'affecte aucune instance existante.
- Contrat V2 unique : `result` / `comment` ; retrait de `checked` / `note` et des
  anciennes routes checklist `PUT` (item et batch) et `POST` (item personnalisé).
  Les consommateurs frontend, rapports, seed et tests doivent suivre ce contrat.
- `result` est un texte non vide ou `null` (contrôle non réalisé), sans enum métier
  arbitraire. Le serveur gère `completed_at`. La structure du snapshot n'est pas
  modifiable par les routes d'exécution.
- Modèles consultables par les utilisateurs authentifiés, modifiables par ADMIN
  (MANAGER n'existe pas encore, TD-B013 non clôturé). Résultats modifiables par le
  technicien assigné sur une intervention PLANNED ou IN_PROGRESS.
- Sources : `app/modules/interventions/models/{checklist,checklist_item,intervention}.py`,
  `schemas/{checklist,intervention}.py`, `services/{checklist,intervention}.py`,
  `repositories/{checklist,intervention}.py`, `api/checklist.py`, registre ORM et router.
- Migration Alembic dédiée ; les données de démonstration peuvent être adaptées,
  mais aucune base existante n'est réinitialisée implicitement. Les preuves R0–R11
  et fixtures historiques restent immuables ; les gardes du contrat courant
  contrôlent séparément le delta INT-104.
- Compléter les cas INT-104 avant implémentation et produire la note dans
  `notes/backend/sprint7.4/`. Ne pas déduire la livraison d'une interface
  d'administration des modèles de la seule API.

---

## INT-105 — Photos + Matériel (3 pts)

**User Story**
En tant que **technicien**,
Je veux **documenter l'intervention (photos avant/après, matériel posé)**,
Afin de **garder la traçabilité de ce qui a été fait**.

**Acceptance Criteria**
- [x] `Photo` : `intervention_id`, `usage` (avant/après/équipement/anomalie/pièce)
- [x] `MaterialUsage` : `intervention_id`, `designation`, `quantity`, `unit`
- [x] Reshape `job_photo` → `Photo`, `material` → `MaterialUsage` (FK intervention)
- [x] API upload/suppression photos + CRUD matériel conservés

**Validation locale**
- Backend : 539 tests réussis, 7 cas PostgreSQL ignorés dans ce run, 7 warnings.
- PostgreSQL dédié : 200 tests réussis, incluant migrations et cas ignorés ci-dessus.
- Frontend : 10 tests Bun (36 assertions), typecheck et build réussis.
- Migrations `head → -1 → head` réussies ; `alembic check` reste à 255 pour
  la seule FK technicien historique, comparaison structurée sans nouvel écart.
- Note : [INT-105 — Photos et matériel V2](../../../../notes/backend/sprint7.4/INT-105-photos-materiel-v2.md).
- La configuration CI n'est pas présentée comme un run distant réussi.

**Technical Notes**
- Réutilise l'upload existant (`UPLOAD_DIR`) + thumbnails
- Contrat canonique : `Photo.usage` prend `BEFORE / AFTER / EQUIPMENT / ANOMALY / PART / OTHER`.
  Le champ `usage` du planning remplace `category` ; `OTHER` est conservé comme
  prévu dans le DAT. Pas d'alias legacy dans le nouveau multipart ou les réponses.
- `MaterialUsage` : désignation non blanche (255 caractères), quantité positive
  numérique (12 chiffres, 3 décimales), unité libre non blanche (50 caractères).
  La création exige quantité/unité ; l'historique peut conserver `null` pour les
  valeurs inconnues, sans inventer d'unité.
- Les routes photos et matériel restent utilisables ; adapter leurs consommateurs
  frontend/rapport/seed. Vérifier le parent réel des IDs enfants avant toute
  modification/suppression ; un ID d'une autre intervention donne 404.
- Migration dédiée après `g104e0010001`, préflight des usages/quantités avant DDL,
  conservation des IDs et chemins de fichiers, refus d'un downgrade destructif.
- TD-B004 (minimum une photo BEFORE et AFTER pour clôturer) reste différé :
  INT-105 ne transforme pas cette règle de phase 2 en critère de clôture.
- Sources initiales : `app/modules/interventions/models/{intervention_photo,material}.py`,
  `services/{photo,material}.py`, `repositories/{photo,material}.py`,
  `api/{photos,materials}.py`. Cibles ORM : `models/{photo,material_usage}.py`.
- Tests détaillés INT-105 dans `test-cases.json`, note à produire dans
  `notes/backend/sprint7.4/`. Ne pas déduire le stockage des métadonnées étendues
  du DAT ni un audit de suppression de la seule adaptation de ces endpoints.

---

## INT-106 — Résultat + clôture (3 pts)

**User Story**
En tant que **technicien**,
Je veux **qualifier le résultat et clôturer l'intervention**,
Afin de **distinguer « terminée » de « résolue »**.

**Acceptance Criteria**
- [x] `result` ∈ `RESOLVED / PARTIALLY_RESOLVED / UNRESOLVED / PART_NEEDED / QUOTE_NEEDED / RESCHEDULE`
- [x] `complete` : résultat requis, observations optionnelles
- [x] `status` (avancement) ≠ `result` (issue métier) — deux champs distincts
- [x] Test : intervention `COMPLETED` + `result=PART_NEEDED` → en base

**Validation locale**
- Backend complet : 617 réussis, 9 skips PostgreSQL, 23 warnings.
- PostgreSQL canonique : 238 réussis ; revalidation finale clôture/migration/empreinte
  de 39 cas réussis, dont l'échec au commit et la concurrence.
- Frontend : 14 tests (74 assertions), typecheck/build réussis.
- Smoke réel parent : choix obligatoire, erreur injectée/réessai, PART_NEEDED,
  historique inconnu/pagination et extraction PDF vérifiés.
- [Note pédagogique](../../../../notes/backend/sprint7.4/INT-106-resultat-cloture.md).
- Aucun push ni validation CI distante/déploiement déduit de ces runs.

**Technical Notes**
- Sources : `app/modules/interventions/models/intervention.py`,
  `schemas/intervention.py`, `services/intervention.py`, `api/interventions.py`.
- Résultat global distinct du texte libre `ChecklistItem.result` ; les six valeurs
  sont canoniques et la sélection doit être explicite, sans défaut RESOLVED.
- `PUT /interventions/{id}/complete` exige `result` non null ; les observations
  sont optionnelles. Absence/null conserve les observations existantes ; texte
  fourni les remplace. Les schémas create/update ne permettent pas de fixer
  ce résultat hors de la clôture.
- Le résultat est exposé dans détail/liste/historique et réponse de clôture.
  `COMPLETED + PART_NEEDED` reste une combinaison métier valide ; aucune vente,
  devis ou intervention de suivi n'est créé automatiquement.
- Statut, résultat, date et avis auto créé dans une transaction unique. Conserver
  le verrou parent commun avec les PATCH checklist ; rejeter les clôtures répétées
  sans modifier l'issue ni dupliquer l'avis.
- Migration après `h105e0010001` : résultat nullable pour l'historique, aucun
  résultat inféré d'un ancien statut COMPLETED. Downgrade refusé si un résultat
  renseigné serait perdu ; base jetable uniquement pour la validation.
- La clôture ne rend pas obligatoire une photo BEFORE/AFTER (TD-B004 différé).
- Cas détaillés ci-dessous dans `test-cases.json` ; note à produire dans
  `notes/backend/sprint7.4/` avec code, transactions, migration et preuves réelles.

---

## INT-107 — Rapport versionné (4 pts)

**User Story**
En tant que **gérant**,
Je veux **générer et transmettre un rapport historisé**,
Afin de **ne pas réécrire un document déjà envoyé au client**.

**Acceptance Criteria**
- [x] `Report` (document logique) + `ReportVersion` (version physique)
- [x] Un rapport transmis reste stable ; une correction → nouvelle version
- [x] API : `POST /interventions/{id}/reports`, `GET /reports/{id}`, `GET /reports/{id}/versions/{v}`
- [x] PDF réutilisé (WeasyPrint)

**Validation locale**
- Scénario API direct sur SQLite et PostgreSQL jetables : génération, relecture
  binaire/empreinte, approbation manuelle, correction v2, droits et rollback ;
  une seule recette d'intégration automatisée, sans nouvelle batterie unitaire.
- Migration PostgreSQL `upgrade head → downgrade -1 → upgrade head` réussie.
  Avec archive présente, downgrade SQLite refusé avant DDL. Comparaison de
  metadata sans nouvel écart ; `alembic check` demeure non nul pour la seule
  FK technicien historique.
- Typecheck/build frontend réussis. Pas de smoke navigateur, de CI distante
  ni de déploiement revendiqué.
- [Note pédagogique et limites](../../../../notes/backend/sprint7.4/INT-107-rapports-versionnes.md).

**Technical Notes**
- Reshape `ReportExporter` existant → versionnement
- Sources actuelles : `app/modules/reports/{api,renderer}.py`,
  `templates/report_template.html`. Cibles INT-107 :
  `app/modules/reports/{models,schemas,service,api}.py`, registre ORM
  et migration `j107e0010001`.
- Décision validée : une **confirmation manuelle** d'une transmission hors
  Tervo marque une version précise et son auteur/date. Pas d'envoi email/SMTP,
  ni de notification réelle déguisée en `send`. La confirmation réitérée
  conserve la première date et le premier auteur.
- `Report` logique unique par intervention, `ReportVersion` physique numérotée
  et jamais écrasée. PDF binaire archivé dans la DB (accès privé par API,
  aucune URL statique `/uploads`), empreinte SHA-256 vérifiée avant téléchargement
  ou confirmation. Ce choix transactionnel évite le coût caché DB/fichiers
  sans prétendre valider un volume de production représentatif.
- Génération POST explicite après clôture. GET metadata/download n'écrit rien ;
  l'ancienne URL PDF ne fait que lire la dernière version existante. Une
  correction crée une nouvelle version sans changer l'ancienne, transmise
  ou non. Clé `Idempotency-Key` facultative pour rejouer une génération ;
  numérotation et clé protégées par unicité DB/verrou parent.
- ADMIN ou technicien assigné ; pas de rôle MANAGER inventé (TD-B013).
  Le frontend expose génération, historique de versions, aperçu/téléchargement
  et confirmation externe explicite. Adapter tests/guards historiques sans
  réécrire leurs fixtures et actualiser les notes dépendantes.

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
- Sources actuelles : `app/modules/interventions/models/review.py`,
  `services/review.py`, `repositories/review.py`, `api/reviews.py`.
- La FK actuelle cible déjà `intervention` ; INT-108 doit vérifier les critères
  restants et compléter ses tests, pas refaire un renommage livré.

---

## Cas de test

Voir [test-cases.json](test-cases.json).

**À compléter avant implémentation :** cas détaillés pour INT-108. Les cas INT-105 sont désormais cadrés ; leurs résultats restent à renseigner après exécution.
