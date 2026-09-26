# INT-22 — Modèle JobPhoto + Material + migration

> **Objectif** : Créer les modèles `JobPhoto` (photos avant/après) et `Material` (matériaux utilisés)
> **Stack** : SQLAlchemy + Alembic + Pillow + stockage fichiers UUID

---

## 1. Modèle JobPhoto

```python
class JobPhoto(Base):
    __tablename__ = "job_photo"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("job.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(20), nullable=False)  # 'avant', 'après'
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    taken_at = Column(DateTime, server_default=func.now(), nullable=False)

    job = relationship("Job", back_populates="photos")
```

**Particularités :**

- `category` : stocke `'avant'` ou `'après'` — pas d'enum pour simplifier
- `file_path` : chemin complet vers le fichier stocké (UUID)
- `thumbnail_path` : chemin vers la miniature 300×300

---

## 2. Modèle Material

```python
class Material(Base):
    __tablename__ = "material"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("job.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    quantity = Column(String(50), nullable=True)  # texte libre : "1", "0.5 kg", "2 m"
    position = Column(Integer, default=0)

    job = relationship("Job", back_populates="materials")
```

**`quantity` en VARCHAR :** une quantité peut être "1", "0.5 kg", "2 m" — pas un simple entier.

---

## 3. Configuration uploads

```python
# config.py
UPLOAD_DIR: str = "backend/uploads"
UPLOAD_URL: str = "/uploads"
```

Dossier créé à la racine du backend :

```
backend/uploads/photos/
```

Les fichiers seront stockés avec un UUID :

```
backend/uploads/photos/a1b2c3d4.jpg
backend/uploads/photos/thumb_a1b2c3d4.jpg
```

---

## 4. Relations Job → JobPhoto / Material

```python
# models/job.py
photos = relationship("JobPhoto", back_populates="job", cascade="all, delete-orphan")
materials = relationship("Material", back_populates="job", cascade="all, delete-orphan")
```

**`cascade="all, delete-orphan"`** : si un job est supprimé, toutes ses photos et matériaux sont supprimés aussi.

---

## 5. Migration

```bash
cd backend/
.venv/bin/alembic revision --autogenerate -m "add job_photo and material tables"
.venv/bin/alembic upgrade head
```

Tables créées :

- `job_photo` : id, job_id (FK), category, file_path, thumbnail_path, taken_at
- `material` : id, job_id (FK), name, quantity, position

---

## 6. Troubleshooting

**Problème :** `ModuleNotFoundError: No module named 'pydantic_settings'`
**Solution :** `pip install -r requirements.txt` (reinstaller les dépendances après avoir cassé le venv)

---

## 7. Fichiers

| Fichier                   | Action                                     |
| ------------------------- | ------------------------------------------ |
| `app/models/job_photo.py` | **Nouveau**                                |
| `app/models/material.py`  | **Nouveau**                                |
| `app/models/job.py`       | Relations `photos` et `materials` activées |
| `app/models/__init__.py`  | Imports `JobPhoto`, `Material`             |
| `app/config.py`           | `UPLOAD_DIR`, `UPLOAD_URL`                 |
| `alembic/versions/...`    | Migration `170af5c7827f`                   |
| `docs/todos/backend.md`   | TD-B003 mis à jour (photos + materials ✅) |

## Récap

INT-22 — Modèle JobPhoto + Material + migration (3 pts) — ✅ Terminé\*\*

### Fait

| Action                                   | Fichier                                      |
| ---------------------------------------- | -------------------------------------------- |
| Modèle `JobPhoto`                        | `app/models/job_photo.py`                    |
| Modèle `Material`                        | `app/models/material.py`                     |
| Config uploads                           | `app/config.py` : `UPLOAD_DIR`, `UPLOAD_URL` |
| Dossier uploads                          | `backend/uploads/photos/` créé               |
| Relations `job.photos` + `job.materials` | `app/models/job.py` (débloque TD-B003)       |
| Pillow installé                          | `requirements.txt` (thumbnail 300×300)       |
| Migration `170af5c7827f`                 | 2 tables créées : `job_photo`, `material`    |
| Note                                     | `notes/backend/sprint-2.1/INT-22-jobphoto-material.md`  |

### Todos débloqués

| Todo                                      | Statut                                              |
| ----------------------------------------- | --------------------------------------------------- |
| TD-B003 (`job.photos`, `job.materials`)   | ✅ `photos` et `materials` activés (reste `review`) |
| TD-B004 (validation photos dans complete) | ⏳ Bloqué — attend upload endpoint                  |

### Chaîne migrations

```
initial → user → client → job → checklist_item → job_photo + material (HEAD)
```

Prêt pour **INT-23 — POST /jobs/{id}/photos** quand tu veux.
