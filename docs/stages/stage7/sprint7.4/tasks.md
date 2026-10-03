# Sprint 7.4 — Cycle terrain

> **Tervo V2** · INT-104 à INT-108 · **Statut :** INT-104 implémentée et vérifiée localement ; INT-105 à INT-108 à traiter
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
- [ ] `Photo` : `intervention_id`, `usage` (avant/après/équipement/anomalie/pièce)
- [ ] `MaterialUsage` : `intervention_id`, `designation`, `quantity`, `unit`
- [ ] Reshape `job_photo` → `Photo`, `material` → `MaterialUsage` (FK intervention)
- [ ] API upload/suppression photos + CRUD matériel conservés

**Technical Notes**
- Réutilise l'upload existant (`UPLOAD_DIR`) + thumbnails
- Sources actuelles : `app/modules/interventions/models/{intervention_photo,material}.py`,
  `services/{photo,material}.py`, `repositories/{photo,material}.py`,
  `api/{photos,materials}.py`. Les nouveaux noms éventuels sont à cadrer dans INT-105.

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
- Sources : `app/modules/interventions/models/intervention.py`,
  `schemas/intervention.py`, `services/intervention.py`, `api/interventions.py`.

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
- Sources actuelles : `app/modules/reports/{api,renderer}.py`,
  `templates/report_template.html`. Les modèles/migrations de versionnement
  restent à créer et à cadrer dans INT-107, pas livrés par le refactor.

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

**À compléter avant implémentation :** cas détaillés pour INT-105, INT-108. Ils étaient absents du fichier de tests initial ; les critères d’acceptation ci-dessus restent la référence.
