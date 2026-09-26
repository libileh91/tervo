# INT-18 — GET/PUT /jobs/{id}/checklist

> **Objectif** : Exposer les endpoints de consultation et mise à jour individuelle de la checklist
> **Stack** : FastAPI + ChecklistService + PrimeVue (frontend)

---

## 1. Les endpoints

| Méthode | Route                                   | Description                            |
| ------- | --------------------------------------- | -------------------------------------- |
| `GET`   | `/api/v1/jobs/{job_id}/checklist`       | Liste des items triés par position     |
| `PUT`   | `/api/v1/jobs/{job_id}/checklist/{id}`  | Mise à jour `checked`/`note` d'un item |
| `PUT`   | `/api/v1/jobs/{job_id}/checklist/batch` | Mise à jour multiple                   |

---

## 2. Piège évité : ordre des routes FastAPI

```python
# ❌ Problème si {item_id} arrive avant /batch
@router.put("/{job_id}/checklist/{item_id}", ...)  # "batch" → erreur int
@router.put("/{job_id}/checklist/batch", ...)

# ✅ Solution : /batch en premier
@router.put("/{job_id}/checklist/batch", ...)       # match exact
@router.put("/{job_id}/checklist/{item_id}", ...)   # paramétré
```

**Pourquoi ?** FastAPI match les routes dans l'ordre. `{item_id}` attrape "batch" et tente `int("batch")` → 422.

---

## 3. Vérification d'assignation

```python
async def _check_assignation(job: Job, current_user: User):
    if job.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce job",
        )
```

Même helper utilisé par les 3 endpoints — pas de duplication.

---

## 4. Schémas Pydantic

```python
class ChecklistItemUpdate(BaseModel):
    checked: bool | None = None   # tout optionnel
    note: str | None = None

class BatchItemUpdate(ChecklistItemUpdate):
    id: int                       # seul l'id est requis

class BatchUpdateRequest(BaseModel):
    items: list[BatchItemUpdate]

class BatchUpdateResponse(BaseModel):
    updated: int
```

---

## 5. Réponse GET

```json
[
  { "id": 1, "category": "pre_intervention", "label": "Vérifier EPI", "checked": false, "note": null, "position": 1 },
  { "id": 2, "category": "pre_intervention", "label": "Vérifier accès", "checked": false, "note": null, "position": 2 },
  ...
]
```

Le même schéma `ChecklistItemRef` est réutilisé côté backend ET frontend (type `ChecklistItemRef` dans `api/client.ts`).

---

## 6. Fichiers créés

| Fichier                   | Action                                                                                  |
| ------------------------- | --------------------------------------------------------------------------------------- |
| `app/api/v1/checklist.py` | **Nouveau** — 3 endpoints                                                               |
| `app/schemas/job.py`      | + `ChecklistItemUpdate`, `BatchItemUpdate`, `BatchUpdateRequest`, `BatchUpdateResponse` |
| `app/main.py`             | `checklist_router` enregistré                                                           |
