# INT-04 — Modèle Client + migration

> **Objectif** : Créer le modèle `Client` (fiche client) avec sa migration automatique
> **Stack** : SQLAlchemy 2.0 ORM + Alembic autogenerate + indexation

---

## 1. Le modèle `Client`

Fichier : `backend/app/models/client.py`

```python
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.models.base import Base


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)  # NOT NULL + INDEX
    phone = Column(String(50), nullable=False, index=True)       # NOT NULL + INDEX
    email = Column(String(255), nullable=True)                    # NULLABLE
    address = Column(String(500), nullable=False)                 # NOT NULL
    postal_code = Column(String(20), nullable=True)               # NULLABLE
    city = Column(String(255), nullable=True, index=True)         # NULLABLE + INDEX
    notes = Column(Text, nullable=True)                           # NULLABLE
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

---

## 2. Colonnes obligatoires vs optionnelles

| Colonne | Type | Obligatoire | Pourquoi |
|---------|------|-------------|----------|
| `id` | Integer | ✅ Auto (PK) | Identifiant unique |
| `full_name` | String(255) | ✅ | Nom du client ou de l'entreprise |
| `phone` | String(50) | ✅ | Contact téléphonique principal |
| `address` | String(500) | ✅ | Adresse d'intervention |
| `email` | String(255) | ❌ | Pas toujours connu |
| `postal_code` | String(20) | ❌ | Optionnel en fonction du pays |
| `city` | String(255) | ❌ | Peut être déduit du code postal |
| `notes` | Text | ❌ | Info complémentaire (code porte, étage...) |

**En SQL :** `nullable=False` → `NOT NULL` / `nullable=True` → pas de contrainte.

---

## 3. Les index

```python
full_name = Column(String(255), nullable=False, index=True)  # idx_client_full_name
phone     = Column(String(50),  nullable=False, index=True)  # idx_client_phone
city      = Column(String(255), nullable=True,  index=True)  # idx_client_city
```

**Pourquoi ces index ?** Les techniciens chercheront des clients par :
- **Nom** → `SELECT * FROM client WHERE full_name LIKE '%dupont%'`
- **Téléphone** → `SELECT * FROM client WHERE phone = '0612345678'`
- **Ville** → `SELECT * FROM client WHERE city = 'Paris'`

Sans index, chaque recherche fait un **scan complet de la table** (lent avec des milliers de clients).

### SQL généré

```sql
CREATE INDEX ix_client_full_name ON client (full_name);
CREATE INDEX ix_client_phone ON client (phone);
CREATE INDEX ix_client_city ON client (city);
```

---

## 4. Migration générée

```bash
cd backend/
.venv/bin/alembic revision --autogenerate -m "add client table"
```

Détection automatique par Alembic :
```
Detected added table 'client'
Detected added index 'ix_client_city'
Detected added index 'ix_client_full_name'
Detected added index 'ix_client_phone'
```

**Fichier généré :** `alembic/versions/a341de379a02_add_client_table.py`

```python
def upgrade() -> None:
    op.create_table('client',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.VARCHAR(length=255), nullable=False),
        sa.Column('phone', sa.VARCHAR(length=50), nullable=False),
        sa.Column('email', sa.VARCHAR(length=255), nullable=True),
        sa.Column('address', sa.VARCHAR(length=500), nullable=False),
        sa.Column('postal_code', sa.VARCHAR(length=20), nullable=True),
        sa.Column('city', sa.VARCHAR(length=255), nullable=True),
        sa.Column('notes', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_client_city'), 'client', ['city'], unique=False)
    op.create_index(op.f('ix_client_full_name'), 'client', ['full_name'], unique=False)
    op.create_index(op.f('ix_client_id'), 'client', ['id'], unique=False)
    op.create_index(op.f('ix_client_phone'), 'client', ['phone'], unique=False)
```

**À noter :** Alembic nomme automatiquement les index avec le préfixe `ix_` + `nom_table` + `nom_colonne`.

---

## 5. Chaîne des migrations

```bash
.venv/bin/alembic history
```

```
9b55bf942f2a -> 24b96d6f9dfa (head)  # add client table  ← NOUVEAU
9b55bf942f2a -> 24b96d6f9dfa         # add user table
9b55bf942f2a (base)                  # initial empty schema
```

```mermaid
flowchart LR
    A["9b55bf942f2a<br/>(initial empty)"] --> B["24b96d6f9dfa<br/>(add user table)"]
    B --> C["a341de379a02<br/>(add client table) <-- HEAD"]
```

---

## 6. Vérification en base

```sql
SELECT sql FROM sqlite_master WHERE type='table' AND name='client';
```

```sql
CREATE TABLE client (
    id INTEGER NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    address VARCHAR(500) NOT NULL,
    postal_code VARCHAR(20),
    city VARCHAR(255),
    notes TEXT,
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id)
)
```

---

## 7. Résumé : le pattern pour chaque nouveau modèle

```bash
# 1. Créer app/models/ma_table.py
# 2. L'importer dans app/models/__init__.py
# 3. Générer la migration
.venv/bin/alembic revision --autogenerate -m "add ma_table"
# 4. Appliquer
.venv/bin/alembic upgrade head
# 5. Vérifier
.venv/bin/alembic current
```
