# INT-55 — Backend : section `overdue_jobs` dans le dashboard

> **Date :** 13/07/2026
> **Sprint :** 4.3

---

## 1. Ce qui a été fait

Ajout d'une section `overdue_jobs` dans la réponse de `GET /dashboard/summary`. Elle liste les jobs `planifiés` dont la `scheduled_date` est **avant aujourd'hui**, pour le technicien connecté.

### 3 fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `schemas/job.py` | Ajout de `OverdueJobRef` + champ `overdue_jobs` dans `DashboardSummaryResponse` |
| `repositories/job.py` | Ajout de `list_overdue(technician_id)` |
| `services/job.py` | Requête des jobs en retard + transformation en `OverdueJobRef` |

---

## 2. Ce qui a été ajouté

### Schema `OverdueJobRef`

```python
class OverdueJobRef(BaseModel):
    id: int
    title: str
    priority: str
    scheduled_date: str          # ISO YYYY-MM-DD
    days_overdue: int            # (today - scheduled_date).days
    client_full_name: str
    client_address: str
```

### `DashboardSummaryResponse` étendu

```python
class DashboardSummaryResponse(BaseModel):
    today: TodaySummary
    next_job: NextJobRef | None = None
    in_progress_job: InProgressJobRef | None = None
    overdue_jobs: list[OverdueJobRef] = []   # ← nouveau, par défaut []
```

### Repository : `list_overdue()`

```python
async def list_overdue(self, technician_id: int) -> list[Job]:
    today = func.current_date()
    query = (
        select(Job)
        .options(selectinload(Job.client))
        .where(
            Job.technician_id == technician_id,
            Job.status == "planifié",
            Job.scheduled_date < today,       # ← comparaison date < aujourd'hui
        )
        .order_by(Job.scheduled_date.asc())   # ← le plus vieux en premier
    )
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

**Points clés :**
- `func.current_date()` → compile en `CURRENT_DATE` en PostgreSQL (date du jour sans timezone)
- `selectinload(Job.client)` → évite le N+1 (charge le client en une seule query)
- `.order_by(Job.scheduled_date.asc())` → tri croissant (le + vieux d'abord)

### Service : intégration dans `get_dashboard_summary()`

```python
# Après le calcul de next_job et in_progress_job...
overdue_jobs_raw = await self.repo.list_overdue(current_user.id)
overdue_jobs = [
    OverdueJobRef(
        id=j.id,
        title=j.title,
        priority=j.priority.value,
        scheduled_date=j.scheduled_date.isoformat(),
        days_overdue=(today - j.scheduled_date).days,
        client_full_name=j.client.full_name,
        client_address=j.client.address,
    )
    for j in overdue_jobs_raw
]

return DashboardSummaryResponse(
    today=...,
    next_job=...,
    in_progress_job=...,
    overdue_jobs=overdue_jobs,    # ← intégré
)
```

---

## 3. Test

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"tech1","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Créer un job avec date passée
curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"client_id":21,"title":"En retard","scheduled_date":"2026-07-10","priority":"haute"}'

# Vérifier le dashboard
curl -s http://localhost:8000/api/v1/dashboard/summary \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"today: {d['today']}\")
print(f\"overdue_jobs: {len(d['overdue_jobs'])} jobs\")
for j in d['overdue_jobs']:
    print(f\"  - {j['title']} (retard: {j['days_overdue']}j, date: {j['scheduled_date']})\")
"
```
