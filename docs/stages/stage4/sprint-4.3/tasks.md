# Sprint 4.3 : Jobs en retard & annulation (Semaine 5, Ven)

> **Durée :** 1 jour | **Points :** 8 | **Tâches :** 3 (INT-54, INT-55, INT-45)
>
> Sprint ajouté après Sprint 4.1 pour gérer les jobs dont la date est passée.

---

## INT-54 — Backend : endpoint `PUT /jobs/{id}/cancel` (2 pts)

**User Story**
En tant que **technicien**,
Je veux **annuler une intervention qui n'aura pas lieu**,
Afin de **ne pas garder des jobs planifiés obsolètes dans la liste**.

**Acceptance Criteria**

- [x] `PUT /api/v1/jobs/{id}/cancel` — passe le statut à `annulé`
- [x] Vérifie que le job est au statut `planifié` (pas déjà en cours/terminé/annulé)
- [x] Vérifie que le technicien connecté est bien assigné au job
- [x] Retourne `{ id, status: "annulé" }`
- [x] 400 si le job n'est pas `planifié`
- [x] 403 si le technicien n'est pas assigné
- [x] 404 si le job n'existe pas

**Technical Notes**

- Fichier : `backend/app/api/v1/jobs.py` — ajouter le routeur
- Fichier : `backend/app/services/job.py` — ajouter `cancel_job()`
- Modèle : `JobStatus.ANNULE` existe déjà dans `app/models/job.py`
- Schema : créer `JobCancelResponse(id: int, status: str)` dans `schemas/job.py`
- Calqué sur le pattern de `start_job()` / `complete_job()`

---

## INT-55 — Backend : section "En retard" dans le dashboard (3 pts)

**User Story**
En tant que **technicien**,
Je veux **voir les interventions dont la date est dépassée**,
Afin de **pouvoir les traiter (démarrer, replanifier ou annuler)**.

**Acceptance Criteria**

- [x] `GET /dashboard/summary` inclut un nouveau champ `overdue_jobs: [...]`
- [x] `overdue_jobs` liste les jobs `planifiés` avec `scheduled_date < today`
- [x] Filtré par `technician_id == current_user`
- [x] Trié par `scheduled_date ASC` (le plus vieux en premier)
- [x] Chaque élément contient : `id, title, priority, scheduled_date, client_full_name, client_address, days_overdue`
- [x] `days_overdue` = nombre de jours de retard (entier, aujourd'hui - scheduled_date)
- [x] `scheduled_date` en string ISO `YYYY-MM-DD`
- [x] Ne casse pas les endpoints existants (next_job, in_progress_job, today)

**Technical Notes**

- Fichier : `backend/app/services/job.py` — modifier `get_dashboard_summary()`
- Fichier : `backend/app/schemas/job.py` — ajouter `OverdueJobRef` et étendre `DashboardSummaryResponse`
- Fichier : `backend/app/repositories/job.py` — ajouter méthode `list_overdue(technician_id)`
- Le frontend reçoit déjà les données via le même endpoint — pas de nouvelle route

---

## INT-45 — Frontend : section "En retard" + bouton "Annuler" (3 pts)

**User Story**
En tant que **technicien**,
Je veux **voir les jobs en retard sur mon dashboard et pouvoir les annuler**,
Afin de **garder mon planning propre et réagir rapidement**.

**Acceptance Criteria**

- [x] Dashboard : nouvelle carte "En retard" si `dashboard.overdue_jobs.length > 0`
- [x] Affiche pour chaque job : titre, client, jours de retard, priorité, date dépassée
- [x] Chaque job retardé a : bouton "▶ Démarrer" (start_job) et "❌ Annuler" (cancel_job)
- [x] JobDetailPage : bouton "Annuler" visible quand `job.status === 'planifié'`
- [x] Bouton "Annuler" → confirmation Dialog → `PUT /jobs/{id}/cancel` → toast + refetch
- [x] Rafraîchissement du dashboard après chaque action (start/cancel)
- [x] Appel API via `api.put(/jobs/{id}/cancel, {}, token)` — pattern existant

**Technical Notes**

- Fichier : `frontend/src/pages/DashboardPage.vue` — carte overdue + actions
- Fichier : `frontend/src/pages/JobDetailPage.vue` — bouton annuler dans les actions
- UI : carte similaire à "Prochain job" avec fond légèrement orangé pour signifier le retard
- Icône : `pi pi-exclamation-triangle` pour le warning
- `days_overdue` : affiché comme `"J-3"` ou `"En retard de 3 jours"`
- Ne pas oublier `@click.stop` sur les boutons pour éviter la propagation vers la carte

---

## Tests Cases Sprint 4.3

Les tests cases détaillés sont dans `test-cases.json`.
