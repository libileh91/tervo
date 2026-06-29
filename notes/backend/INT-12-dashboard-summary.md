# INT-12 — GET /dashboard/summary

> **Objectif** : Retourner le résumé du jour pour le technicien connecté
> **Stack** : FastAPI + SQLAlchemy ORM + `selectinload`

---

## 1. L'endpoint

```
GET /api/v1/dashboard/summary
Authorization: Bearer <token>
```

**Réponse 200 :**

```json
{
  "today": {
    "date": "2026-06-06",
    "jobs_total": 4,
    "jobs_in_progress": 2,
    "jobs_completed": 0
  },
  "next_job": {
    "id": 8,
    "title": "Maintenance clim",
    "priority": "haute",
    "client_full_name": "Client Dash",
    "client_address": "12 rue Test",
    "scheduled_start_time": "10:00"
  },
  "in_progress_job": {
    "id": 9,
    "title": "Urgence fuite",
    "started_at": "2026-06-06T15:29:51",
    "elapsed_minutes": 5
  }
}
```

---

## 2. Le service

```python
async def get_dashboard_summary(self, current_user: User) -> DashboardSummaryResponse:
    today = date.today()

    # 1 requête : tous les jobs du jour pour ce technicien
    today_jobs = await self.repo.db.execute(
        select(Job)
        .options(selectinload(Job.client))      # ← eager loading client
        .where(
            Job.scheduled_date == today,
            Job.technician_id == current_user.id,
        )
        .order_by(Job.scheduled_start_time.asc())
    )
    jobs = list(today_jobs.scalars().all())

    # Compteurs
    jobs_in_progress = sum(1 for j in jobs if j.status == JobStatus.EN_COURS)
    jobs_completed   = sum(1 for j in jobs if j.status == JobStatus.TERMINE)

    # Premier job planifié (next)
    next_job = next((j for j in jobs if j.status == JobStatus.PLANIFIE), None)

    # Job en cours
    in_progress = next((j for j in jobs if j.status == JobStatus.EN_COURS), None)
    elapsed = int((datetime.utcnow() - in_progress.started_at).total_seconds() // 60)
```

**Point clé :** Une seule requête SQL grâce à `selectinload(Job.client)` — pas de N+1.

---

## 3. Le router dédié

Nouveau fichier `app/api/v1/dashboard.py` :

```python
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)
    return await service.get_dashboard_summary(current_user)
```

**Pourquoi un router séparé ?** Pour suivre le pattern REST et garder `/api/v1/dashboard/` distinct de `/api/v1/jobs/`.

---

## 4. Cas possibles

| Scénario                       | `next_job` | `in_progress_job` |
| ------------------------------ | ---------- | ----------------- |
| Aucun job aujourd'hui          | `null`     | `null`            |
| Un job planifié, rien en cours | `{ ... }`  | `null`            |
| Un job en cours, rien planifié | `null`     | `{ ... }`         |
| Les deux                       | `{ ... }`  | `{ ... }`         |

---

## 5. Piège évité : timezone naive vs aware

**Problème :** `datetime.now(timezone.utc)` retourne un objet **aware**, mais SQLite stocke `started_at` comme **naive**. La soustraction échoue :

```
TypeError: can't subtract offset-naive and offset-aware datetimes
```

**Solution :** Utiliser `datetime.utcnow()` (naive) pour le calcul et `.replace(tzinfo=None)` sur la valeur chargée.

---

## 6. Todos débloqués

- **TD-F001** (DashboardPage frontend) : ✅ Backend prêt — `GET /api/v1/dashboard/summary` disponible

---

## Récap

INT-12 — GET /dashboard/summary (3 pts) — ✅ Terminé\*\*

### Tests validés

| #            | Test                                                             | Résultat |
| ------------ | ---------------------------------------------------------------- | -------- |
| TC-INT-12-01 | Dashboard avec jobs (200, champs today/next_job/in_progress_job) | ✅       |
| TC-INT-12-02 | Dashboard sans jobs (today avec 0, next/in_progress = null)      | ✅       |

### Fichiers créés

| Fichier                   | Action                                                                       |
| ------------------------- | ---------------------------------------------------------------------------- |
| `app/schemas/job.py`      | `TodaySummary`, `NextJobRef`, `InProgressJobRef`, `DashboardSummaryResponse` |
| `app/services/job.py`     | `get_dashboard_summary()` avec selectinload                                  |
| `app/api/v1/dashboard.py` | **Nouveau** router dédié                                                     |
| `app/api/v1/jobs.py`      | Fix : `time.fromisoformat()` pour `scheduled_start_time`                     |
| `app/main.py`             | Dashboard router enregistré                                                  |
| `docs/todos/frontend.md`  | TD-F001 : INT-12 marqué ✅                                                   |

### Todo débloqué

| Todo                                 | Statut                                                |
| ------------------------------------ | ----------------------------------------------------- |
| **TD-F001** — DashboardPage frontend | ✅ Backend prêt (`GET /dashboard/summary` disponible) |

---

Prêt pour **INT-13 — Frontend DashboardPage** quand tu veux.
