# INT-23 — POST /jobs/{id}/photos (multipart + thumbnail)

> **Objectif** : Uploader une photo avant/après avec miniature automatique
> **Stack** : FastAPI + Pillow + stockage UUID

---

## 1. L'endpoint

```
POST /api/v1/jobs/{job_id}/photos
Authorization: Bearer <token>
Content-Type: multipart/form-data

file:     (JPEG/PNG, max 10 Mo)
category: "avant" | "après"
```

**Réponse 201 :**
```json
{
  "id": 1,
  "category": "avant",
  "file_url": "/uploads/photos/0166de308c9d424987bd057ff1ec3071.jpg",
  "thumbnail_url": "/uploads/photos/thumb_0166de308c9d424987bd057ff1ec3071.jpg",
  "taken_at": "2026-06-07T17:24:45"
}
```

---

## 2. Service — upload_photo()

```python
async def upload_photo(self, job_id, file, category):
    # 1. Valider le type (JPEG/PNG)
    # 2. Valider la taille (max 10 Mo)
    # 3. Générer un UUID unique
    # 4. Sauvegarder le fichier original
    # 5. Générer la thumbnail 300×300 avec Pillow
    # 6. Sauvegarder en DB
    # 7. Retourner les URLs
```

**Génération de thumbnail :**
```python
from PIL import Image

img = Image.open(file_path)
img.thumbnail((300, 300))
img.save(thumb_path, "JPEG", quality=85)
```

---

## 3. Stockage

```
backend/uploads/photos/
├── 0166de308c9d424987bd057ff1ec3071.jpg        # original
├── thumb_0166de308c9d424987bd057ff1ec3071.jpg  # miniature 300×300
├── d515597a136a401d99a6f42a6764bdb2.jpg
└── thumb_d515597a136a401d99a6f42a6764bdb2.jpg
```

**UUID** : `uuid.uuid4().hex` → 32 caractères hexadécimaux, garantie d'unicité.

---

## 4. Fichiers

| Fichier | Action |
|---------|--------|
| `app/repositories/photo.py` | **Nouveau** — create, get_by_id, delete |
| `app/services/photo.py` | **Nouveau** — upload + thumbnail |
| `app/api/v1/photos.py` | **Nouveau** — endpoint POST |
| `app/main.py` | `photos_router` enregistré |

---

## 5. Test

```bash
cd backend/
.venv/bin/uvicorn app.main:app --reload

# Upload (créer une image test)
.venv/bin/python -c "
from PIL import Image
img = Image.new('RGB', (400,300), 'red')
img.save('test.jpg')

curl -s -X POST http://localhost:8000/api/v1/jobs/1/photos \
  -H 'Authorization: Bearer <token>' \
  -F 'file=@test.jpg' \
  -F 'category=avant'
"
```
