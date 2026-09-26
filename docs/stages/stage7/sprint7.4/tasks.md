# Sprint 7.4 — Cycle terrain

> **Tervo V2** · INT-104 à INT-108 · **Statut :** À traiter
> **Dépendances :** Sprint 7.1 ; réutiliser les modules terrain existants.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.4/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

> Réutilise et reshape l'existant (`checklist_item`, `job_photo`, `material`, `review`, `report`)
> sur le nouveau modèle. Dépend du Sprint 7.1.

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

## Cas de test

Voir [test-cases.json](test-cases.json).

**À compléter avant implémentation :** cas détaillés pour INT-105, INT-108. Ils étaient absents du fichier de tests initial ; les critères d’acceptation ci-dessus restent la référence.
