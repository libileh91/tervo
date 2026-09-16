# INT-08 — Modèle Job + migration

> **Objectif** : Créer le modèle `Job` (intervention terrain) avec ses relations et contraintes
> **Stack** : SQLAlchemy 2.0 ORM + ForeignKey + Relationships

---

## 1. Le modèle `Job`

Fichier : `backend/app/models/job.py`

```python
class JobStatus(str, enum.Enum):
    PLANIFIE = "planifié"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ANNULE = "annulé"

class Priority(str, enum.Enum):
    BASSE = "basse"
    NORMALE = "normale"
    HAUTE = "haute"
    URGENTE = "urgente"


class Job(Base):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True)
    technician_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.PLANIFIE, nullable=False, index=True)
    priority = Column(Enum(Priority), default=Priority.NORMALE, nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False, index=True)
    scheduled_start_time = Column(Time, nullable=True)
    scheduled_end_time = Column(Time, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

---

## 2. Les Foreign Keys

```python
ForeignKey("client.id", ondelete="CASCADE")   # si client supprimé → ses jobs aussi
ForeignKey("user.id", ondelete="SET NULL")    # si user supprimé → technician_id = NULL
```

| `ondelete` | Comportement                                                                     |
| ---------- | -------------------------------------------------------------------------------- |
| `CASCADE`  | Supprime le job si le client est supprimé                                        |
| `SET NULL` | Met `technician_id = NULL` si le technicien est supprimé (conserve l'historique) |

**Piège SQLite :** SQLite ne supporte pas `ALTER CONSTRAINT`. Les `ondelete` sont définis dans le modèle et fonctionneront en PostgreSQL, mais en SQLite dev ils sont ignorés.

### Piège évité : Enum `values_callable`

```python
# ❌ Problème : SQLAlchemy stocke les NOMS (PLANIFIE) par défaut
status = Column(Enum(JobStatus), default=JobStatus.PLANIFIE)

# ✅ Solution : stocker les VALEURS françaises
status = Column(
    Enum(JobStatus, values_callable=lambda x: [e.value for e in x]),
    default=JobStatus.PLANIFIE,
)
```

**Bug rencontré :** Les jobs insérés via `raw SQL` stockaient `"planifié"` (la valeur), mais SQLAlchemy attendait `"PLANIFIE"` (le nom de l'enum). Résultat : `LookupError: 'planifié' is not among the defined enum values`.

**Solution :** `values_callable=lambda x: [e.value for e in x]` → SQLAlchemy stocke/charge les valeurs (`"planifié"`) au lieu des noms (`"PLANIFIE"`).

> **Correction aussi dans** `app/models/job.py` lignes 52-55 et 57-60 (priority).

---

## 3. Les Index

```python
# Tous avec index=True pour les performances
client_id      → ix_job_client_id
technician_id  → ix_job_technician_id
status         → ix_job_status
scheduled_date → ix_job_scheduled_date
priority       → ix_job_priority
```

**Pourquoi autant d'index ?** Les jobs sont souvent filtrés par :

- `WHERE client_id = ?` → détail client
- `WHERE technician_id = ? AND status = ?` → tableau de bord
- `WHERE scheduled_date = ?` → planning du jour

---

## 4. Les Relationships

```python
# Relations existantes
client = relationship("Client", backref="jobs")
technician = relationship("User", backref="jobs")

# Forward relationships (modèles créés plus tard)
checklist_items = relationship("ChecklistItem", back_populates="job", cascade="all, delete-orphan")
photos = relationship("JobPhoto", back_populates="job", cascade="all, delete-orphan")
materials = relationship("Material", back_populates="job", cascade="all, delete-orphan")
review = relationship("Review", back_populates="job", uselist=False, cascade="all, delete-orphan")
```

**`cascade="all, delete-orphan"`** : si un job est supprimé, tous ses items (checklist, photos, matériaux, review) sont automatiquement supprimés aussi.

**`uselist=False`** : review est une relation 1-1 (un seul avis par job).

---

## 5. Chaîne des migrations

```bash
.venv/bin/alembic history
```

```
7e7c3408ecfb (head) ← update job model (ondelete + forward relations)
5cc5d1686947        ← add job table
a341de379a02        ← add client table
24b96d6f9dfa        ← add user table
9b55bf942f2a        ← initial empty schema
```

---

## 6. Vérification en base

```bash
cd backend/
.venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('tervo.db')
cur = conn.execute(\"SELECT sql FROM sqlite_master WHERE type='table' AND name='job';\")
print(cur.fetchone()[0])
conn.close()
"
```

```sql
CREATE TABLE job (
    id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    technician_id INTEGER,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(10) NOT NULL,
    priority VARCHAR(7) NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_start_time TIME,
    scheduled_end_time TIME,
    started_at DATETIME,
    completed_at DATETIME,
    observations TEXT,
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(client_id) REFERENCES client(id),
    FOREIGN KEY(technician_id) REFERENCES "user"(id)
)
```

---

## 7. Le modèle a été créé dans INT-06

Petite particularité : le modèle `Job` a été créé **en avance** lors de INT-06 (nécessaire pour l'historique des jobs en raw SQL). INT-08 a donc consisté à :

1. **Ajouter `ondelete`** sur les ForeignKey (`CASCADE`, `SET NULL`)
2. **Ajouter les forward relationships** pour les modèles futurs (ChecklistItem, JobPhoto, Material, Review)
3. **Générer migration 7e7c3408ecfb** (no-op sur SQLite, effective sur PostgreSQL)

---

## 8. Done Tasks

INT-08 — Modèle Job + migration (3 pts) — ✅ Terminé\*\*

### Ce qui a été fait

| Action                                                                           | Fichier             |
| -------------------------------------------------------------------------------- | ------------------- |
| Modèle Job déjà existant (INT-06)                                                | `app/models/job.py` |
| Ajout `ondelete="CASCADE"` sur FK `client_id`                                    | ✅                  |
| Ajout `ondelete="SET NULL"` sur FK `technician_id`                               | ✅                  |
| Ajout forward relationships (`checklist_items`, `photos`, `materials`, `review`) | ✅                  |
| Migration `7e7c3408ecfb` générée + appliquée                                     | ✅                  |
| Test case TC-INT-08-01 mis à jour                                                | ✅                  |
| Note `INT-08-modele-job.md` créée                                                | ✅                  |

### Chaîne des migrations

```
initial → user → client → job → update_job (HEAD)
```

### Note importante

SQLite ne supporte pas `ALTER CONSTRAINT`, donc la migration de mise à jour des FK est **no-op** en dev SQLite. Les `ondelete` seront effectifs en PostgreSQL. C'est un compromis classique SQLite vs PostgreSQL — le modèle les définit, la prod les appliquera.

---

Prêt pour **INT-09 — CRUD Jobs API** quand tu veux.
