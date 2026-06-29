# INT-24 — DELETE /jobs/{id}/photos/{id}

> **Objectif** : Supprimer une photo + thumbnail du disque et de la DB
> **Stack** : FastAPI + os.remove + graceful delete

---

## 1. L'endpoint

```
DELETE /api/v1/jobs/{job_id}/photos/{photo_id}
Authorization: Bearer <token>
```

**Réponse 204** — pas de body.

---

## 2. Service — delete_photo()

```python
async def delete_photo(self, photo_id: int) -> None:
    photo = await self.repo.get_by_id(photo_id)
    if photo is None:
        raise HTTPException(404, detail="Photo non trouvée")

    # Supprimer les fichiers du disque
    for path in [photo.file_path, photo.thumbnail_path]:
        if path and os.path.exists(path):
            os.remove(path)

    # Supprimer l'entrée DB
    await self.repo.delete(photo)
```

**Graceful delete :** `os.path.exists()` évite une erreur si le fichier a déjà été supprimé manuellement.

---

## 3. Ordre des opérations

```
1. Vérifier que la photo existe → 404 si non
2. Vérifier assignation technicien → 403 si non
3. Supprimer le fichier original du disque
4. Supprimer le thumbnail du disque
5. Supprimer l'entrée en DB
6. Retourner 204
```

**Pourquoi supprimer le fichier AVANT la DB ?** Si la suppression du fichier échoue (permission), on peut réessayer. Si on supprime la DB d'abord, on perd la référence.

---

## 4. Fichiers

| Fichier                 | Action                  |
| ----------------------- | ----------------------- |
| `app/services/photo.py` | `delete_photo()` ajouté |
| `app/api/v1/photos.py`  | Endpoint `DELETE /{id}` |

---

## 5. Test

```bash
# upload puis delete
curl -s -X DELETE http://localhost:8000/api/v1/jobs/1/photos/1 \
  -H "Authorization: Bearer <token>"
# → 204

# double delete → 404
curl -s -X DELETE http://localhost:8000/api/v1/jobs/1/photos/1 \
  -H "Authorization: Bearer <token>"
# → 404
```
