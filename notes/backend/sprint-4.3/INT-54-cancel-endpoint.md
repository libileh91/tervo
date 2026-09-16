# INT-54 — Backend : endpoint `PUT /jobs/{id}/cancel`

> **Date :** 13/07/2026
> **Sprint :** 4.3

---

## 1. Ce qui a été fait

Ajout d'un endpoint `PUT /api/v1/jobs/{id}/cancel` qui permet d'annuler un job au statut `planifié`.

### 3 fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `schemas/job.py` | Ajout de `JobCancelResponse(id: int, status: str)` |
| `services/job.py` | Ajout de `cancel_job()` — logique métier |
| `api/v1/jobs.py` | Ajout du routeur `PUT /{job_id}/cancel` |

---

## 2. Pattern : ajouter un endpoint workflow

Chaque endpoint de workflow (start, cancel, complete) suit exactement le même pattern. Voici la recette :

### Étape 1 : Schema de réponse

```python
# schemas/job.py
class JobCancelResponse(BaseModel):
    id: int
    status: str
```

### Étape 2 : Service method

```python
# services/job.py
async def cancel_job(self, job_id: int, current_user: User) -> JobCancelResponse:
    job = await self._find_or_404(job_id)

    # Validation 1 : statut autorisé
    if job.status != JobStatus.PLANIFIE:
        raise HTTPException(status_code=400, detail="Le job doit être au statut 'planifié' pour être annulé")

    # Validation 2 : technicien assigné
    if job.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas assigné à ce job")

    # Mutation
    job.status = JobStatus.ANNULE       # ← l'énumération existe déjà
    await self.repo.db.commit()
    await self.repo.db.refresh(job)

    return JobCancelResponse(id=job.id, status=job.status.value)
```

### Étape 3 : Routeur

```python
@router.put("/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(job_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    service = JobService(db)
    return await service.cancel_job(job_id, current_user)
```

---

## 3. Points à retenir

### `JobStatus.ANNULE` existait déjà

```python
class JobStatus(str, enum.Enum):
    PLANIFIE = "planifié"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ANNULE = "annulé"    # ← déjà là, inutilisé avant INT-54
```

L'énumération était définie mais aucun endpoint ne l'utilisait. On a simplement branché le statut existant.

### `job.status.value`

Comme `JobStatus` est un `Enum` (pas une string directe), pour obtenir la valeur string on utilise `.value` :
```python
status=job.status.value  # → "annulé"
```

### Pas de timestamp

Contrairement à `start_job()` (started_at) et `complete_job()` (completed_at), l'annulation n'enregistre pas de timestamp. À ajouter plus tard si besoin (`canceled_at`).

---

## 4. Tests

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"tech1","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X PUT http://localhost:8000/api/v1/jobs/12/cancel -H "Authorization: Bearer $TOKEN"
# → {"id":12,"status":"annulé"}

curl -s -X PUT http://localhost:8000/api/v1/jobs/14/cancel -H "Authorization: Bearer $TOKEN"
# → {"detail":"Le job doit être au statut 'planifié' pour être annulé"}

curl -s -X PUT http://localhost:8000/api/v1/jobs/99999/cancel -H "Authorization: Bearer $TOKEN"
# → {"detail":"Job non trouvé"}
```
