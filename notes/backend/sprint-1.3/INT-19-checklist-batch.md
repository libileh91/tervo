# INT-19 — PUT /jobs/{id}/checklist/batch

> **Objectif** : Mettre à jour plusieurs items de checklist en un seul appel
> **Stack** : FastAPI + transaction SQLAlchemy

---

## 1. L'endpoint

```
PUT /api/v1/jobs/{job_id}/checklist/batch
Authorization: Bearer <token>
```

**Requête :**

```json
{
  "items": [
    { "id": 1, "checked": true, "note": "EPI OK" },
    { "id": 2, "checked": true, "note": "Accès sécurisé" }
  ]
}
```

**Réponse 200 :**

```json
{ "updated": 2 }
```

---

## 2. Pourquoi un endpoint batch ?

| Approche                           | Nb d'appels API           |
| ---------------------------------- | ------------------------- |
| Individuel (`PUT /checklist/{id}`) | **5 appels** pour 5 items |
| Batch (`PUT /checklist/batch`)     | **1 appel**               |

Sur le terrain (réseau mobile parfois lent), le batch est beaucoup plus efficace.

---

## 3. Fonctionnement

```python
async def batch_update(self, job_id: int, items_data: list[dict]) -> int:
    count = 0
    for item_data in items_data:
        # Vérifie que l'item appartient bien au job
        item = await self.db.execute(
            select(ChecklistItem).where(
                ChecklistItem.id == item_data["id"],
                ChecklistItem.job_id == job_id,
            )
        ).scalar_one_or_none()
        if item is None:
            raise ValueError(f"Item {item_data['id']} not found for job {job_id}")

        # Mise à jour
        if "checked" in item_data: item.checked = item_data["checked"]
        if "note" in item_data:    item.note = item_data["note"]
        count += 1

    await self.db.commit()   # ← 1 commit pour N updates
    return count
```

**Atomicité :** si un item échoue (mauvais id), une exception est levée → le commit n'est pas fait → rien n'est modifié.

---

## 4. Fichiers

| Fichier                         | Action                                      |
| ------------------------------- | ------------------------------------------- |
| `app/repositories/checklist.py` | `batch_update()`                            |
| `app/services/checklist.py`     | `batch_update()` avec gestion d'erreur      |
| `app/api/v1/checklist.py`       | Endpoint `PUT /batch`                       |
| `app/schemas/job.py`            | `BatchUpdateRequest`, `BatchUpdateResponse` |
