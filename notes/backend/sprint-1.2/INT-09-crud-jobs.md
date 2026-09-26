# INT-09 — CRUD Jobs API + seed checklist

> **Objectif** : CRUD complet des jobs avec seed automatique de checklist + filtres
> **Stack** : FastAPI + SQLAlchemy ORM + `selectinload` (eager loading)

---

## 1. Les endpoints

| Méthode  | Route                                       | Description                                          |
| -------- | ------------------------------------------- | ---------------------------------------------------- |
| `GET`    | `/api/v1/jobs?status=&date=&technician_id=` | Liste paginée + filtres                              |
| `POST`   | `/api/v1/jobs`                              | Création + **seed automatique de 5 items checklist** |
| `GET`    | `/api/v1/jobs/{id}`                         | Détail complet avec client, technicien, checklist    |
| `PUT`    | `/api/v1/jobs/{id}`                         | Mise à jour partielle                                |
| `DELETE` | `/api/v1/jobs/{id}`                         | Suppression (204)                                    |

---

## 2. Seed automatique de la checklist

À la création d'un job, 5 items sont créés automatiquement :

```python
DEFAULT_PRE_ITEMS = [
    "Vérifier équipement de protection individuelle (EPI)",
    "Vérifier les accès et sécuriser la zone de travail",
    "Couper l'alimentation électrique de l'équipement",
]

DEFAULT_POST_ITEMS = [
    "Nettoyer la zone de travail et remettre en état",
    "Rétablir l'alimentation et tester le fonctionnement",
]
```

**Mécanisme :** Dans `JobRepository.create()` :

```python
async def create(self, data: dict) -> Job:
    job = Job(**data)
    self.db.add(job)
    await self.db.commit()
    await self.db.refresh(job)

    await self._seed_checklist(job.id)  # ← 5 items créés ici
    return await self.get_by_id(job.id)  # ← re-fetch avec relations
```

---

## 3. `selectinload` — Eager loading

```python
from sqlalchemy.orm import selectinload

result = await self.db.execute(
    select(Job)
    .options(
        selectinload(Job.client),         # charge client en 1 requête
        selectinload(Job.technician),     # charge technicien
        selectinload(Job.checklist_items), # charge checklist
    )
    .where(Job.id == job_id)
)
```

**Pourquoi `selectinload` ?** Sans ça, SQLAlchemy ferait une requête supplémentaire à chaque accès à `job.client` (N+1 problem). `selectinload` pré-charge les relations en une seule requête.

### Piège évité : MissingGreenlet dans `list_all`

```diff
# ❌ Oubli de checklist_items dans list_all → MissingGreenlet
query = select(Job).options(
    selectinload(Job.client),
    selectinload(Job.technician),
+   selectinload(Job.checklist_items),  # ← OBLIGATOIRE si JobResponse inclut checklist_items
)
```

**Erreur :** `MissingGreenlet: greenlet_spawn has not been called` → Pydantic `model_validate()` tente d'accéder à `job.checklist_items` en lazy load, mais c'est interdit en mode async.

### N+1 problem expliqué

```python
# SANS selectinload (N+1) :
jobs = await db.execute(select(Job))  # 1 requête
for job in jobs:
    print(job.client.name)  # 1 requête PAR job → N requêtes

# AVEC selectinload (1 seule requête) :
jobs = await db.execute(select(Job).options(selectinload(Job.client)))
# → 1 requête pour les jobs + 1 requête pour tous les clients
```

---

## 4. Les filtres GET /jobs

```python
@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None),
    date: str | None = Query(None),
    technician_id: int | None = Query(None),
    ...
):
```

**Filtres disponibles :**

- `?status=planifié` → WHERE status = 'planifié'
- `?date=2026-06-15` → WHERE scheduled_date = '2026-06-15'
- `?technician_id=1` → WHERE technician_id = 1
- **Combinables** : `?status=en_cours&technician_id=1`

---

## 5. ChecklistItem model

```python
class ChecklistItem(Base):
    __tablename__ = "checklist_item"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(20), nullable=False)  # 'pre_intervention' | 'post_intervention'
    label = Column(String(255), nullable=False)
    checked = Column(Boolean, default=False)
    note = Column(Text, nullable=True)
    position = Column(Integer, default=0)

    job = relationship("Job", back_populates="checklist_items")
```

---

## 6. Tests

```bash
cd backend/
.venv/bin/uvicorn app.main:app --reload

# Créer un job
curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "title": "Test", "scheduled_date": "2026-06-15"}'

# Lister avec filtre
curl -s "http://localhost:8000/api/v1/jobs?status=planifié" \
  -H "Authorization: Bearer <token>"

# Détail (vérifier que client + checklist sont inclus)
curl -s http://localhost:8000/api/v1/jobs/1 \
  -H "Authorization: Bearer <token>" | python -m json.tool
```

---

## 7. Résumé des fichiers

INT-09 — CRUD Jobs API (5 pts) — ✅ Terminé**

| Fichier                        | Nouveau/modifié                          |
| ------------------------------ | ---------------------------------------- |
| `app/models/checklist_item.py` | **Nouveau**                              |
| `app/models/__init__.py`       | Modifié (import ChecklistItem)           |
| `app/schemas/job.py`           | **Réécrit** (CRUD schemas + history)     |
| `app/repositories/job.py`      | **Réécrit** (ORM CRUD + raw SQL history) |
| `app/services/job.py`          | **Réécrit** (CRUD + history)             |
| `app/api/v1/jobs.py`           | **Nouveau**                              |
| `app/main.py`                  | Modifié (jobs router)                    |


### Tests validés (6 tests)

| # | Test | Résultat |
|---|------|----------|
| TC-09-01 | POST /jobs — création 201 + seed checklist | ✅ |
| TC-09-02 | GET /jobs — filtres status + date | ✅ |
| TC-09-03 | GET /jobs/{id} — détail complet avec client | ✅ |
| TC-09-04 | PUT /jobs/{id} — mise à jour partielle | ✅ |
| TC-09-05 | DELETE /jobs/{id} — 204 + 404 confirmé | ✅ |
| TC-09-06 | GET /jobs/999 — 404 inexistant | ✅ |

### Fichiers

| Fichier | Action |
|---------|--------|
| `app/models/checklist_item.py` | **Nouveau** (modèle avec relation `job`) |
| `app/models/job.py` | Modifié (ondelete + relation checklist_items active) |
| `app/schemas/job.py` | **Réécrit** (JobCreate, JobUpdate, JobResponse, JobListResponse) |
| `app/repositories/job.py` | **Réécrit** (ORM CRUD + seed checklist + raw SQL history) |
| `app/services/job.py` | **Réécrit** (CRUD + history) |
| `app/api/v1/jobs.py` | **Nouveau** (5 endpoints) |
| `app/main.py` | Modifié (jobs router) |
| `alembic/versions/...` | Migration `checklist_item` |
| `notes/backend/sprint-1.2/INT-09-crud-jobs.md` | Note pédagogique |

Prêt pour **INT-10 — PUT /jobs/{id}/start** quand tu veux.
