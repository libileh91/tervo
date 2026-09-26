# INT-51 — Seed script : utilisateurs + données demo

> **Objectif :** Étendre le seed script avec des données démo réalistes (admin, technicien, clients, jobs).
> **Date :** 25/06/2026

---

## Données seedées

```
┌─ Users ───────────────┐
│ admin     / admin123   │  → ADMIN
│ tech1     / password123│  → TECHNICIAN
└────────────────────────┘
         │
         ▼
┌─ Clients ─────────────────────────────────────┐
│ Monsieur Hamdi Hassan    — Paris 75001        │
│ Madame Khadija Ahmed     — Paris 75008        │
│ Société MediaPro SARL    — Lyon 69002         │
└───────────────────────────────────────────────┘
         │
         ▼
┌─ Jobs ───────────────────────────────────────────────────────┐
│ [planifié] Install. climatisation   → Hamdi Hassan   (auj.)  │
│ [terminé]  Dépannage chaudière      → Khadija Ahmed  (hier)  │
│ [planifié] Maintenance chaudière    → MediaPro SARL  (J+3)   │
└──────────────────────────────────────────────────────────────┘
```

---

## Code clé du seed

### Idempotence — DELETE avant INSERT

```python
# Ordre inverse des dépendances (enfant → parent)
for table in ["review", "material", "job_photo",
              "checklist_item", "job", "client", "user"]:
    await session.execute(text(f"DELETE FROM {table}"))
```

`DELETE FROM` au lieu de `TRUNCATE` pour compatibilité SQLite (dev) et PostgreSQL (prod).

### Création avec `session.flush()`

```python
session.add(tech1)
await session.flush()  # ← get tech1.id AVANT d'utiliser dans les jobs
```

`flush()` envoie les INSERT en base sans `commit()`. Permet de récupérer les IDs générés pour les utiliser comme clés étrangères.

### Datetimes réalistes

```python
today = date.today()

Job(
    scheduled_date=today,                          # aujourd'hui
    scheduled_start_time=time(9, 0),
    scheduled_end_time=time(12, 0),
    status=JobStatus.PLANIFIE,
)

Job(
    scheduled_date=today - timedelta(days=1),       # hier
    started_at=datetime.combine(today - timedelta(days=1), time(14, 5)),
    completed_at=datetime.combine(today - timedelta(days=1), time(16, 15)),
    status=JobStatus.TERMINE,
)
```

---

## Commandes

```bash
# Local (SQLite)
cd backend/
uv run python -m app.seed

# Docker (PostgreSQL)
docker exec <container-name> python -m app.seed

# Vérifier que les users existent
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Vérifier le dashboard
curl http://localhost:8000/api/v1/dashboard/summary \
  -H "Authorization: Bearer <token>"
```

---

## Résultats de validation

| Test | Résultat |
|------|----------|
| `uv run python -m app.seed` (1er run) | ✅ 3 users, 3 clients, 3 jobs |
| 2ème run (idempotence) | ✅ Aucune erreur, mêmes données |
| `POST /auth/login` admin | ✅ 200 OK + JWT |
| `POST /auth/login` tech1 | ✅ 200 OK + JWT |
| `GET /dashboard/summary` | ✅ 1 job aujourd'hui, priorité haute |

---

> **Prochaine tâche :** INT-45 — Coverage ≥ 80%
