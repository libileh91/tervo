# Fix — PostgreSQL : enum jobstatus & priority (Sprint 3.1 / INT-DPL)

> **Date :** 29/06/2026
> **Cause :** Décalage SQLite ↔ PostgreSQL — les enums PostgreSQL utilisaient les noms Python (`PLANIFIE`) au lieu des valeurs françaises (`planifié`).

---

## Erreur initiale

```
sqlalchemy.exc.DBAPIError: invalid input value for enum jobstatus: "planifié"
```

Le seed envoyait `planifié`, `terminé` (valeurs françaises du modèle Python) mais l'enum PostgreSQL avait été créé avec `PLANIFIE`, `TERMINE`, `ANNULE` (noms Python).

---

## Causes cumulatives

### 1. Migration incohérente

```python
# 5cc5d1686947_add_job_table.py — AVANT
sa.Column('status', sa.Enum('PLANIFIE', 'EN_COURS', 'TERMINE', 'ANNULE', name='jobstatus'))
sa.Column('priority', sa.Enum('BASSE', 'NORMALE', 'HAUTE', 'URGENTE', name='priority'))
```

L'enum était créé avec les **noms Python** plutôt que les **valeurs françaises**.

### 2. `values_callable` manquant dans le modèle

```python
# models/job.py — AVANT (values_callable perdu)
status = Column(Enum(JobStatus, ), ...)      # sans values_callable
priority = Column(Enum(Priority, ), ...)      # sans values_callable
```

`values_callable` avait été supprimé accidentellement par un `sed`. Sans lui, l'ORM envoie `.name` (`PLANIFIE`) au lieu de `.value` (`planifié`).

---

## Corrections

### 1. Migration

```python
# 5cc5d1686947_add_job_table.py — APRÈS
sa.Column('status', sa.Enum('planifié', 'en_cours', 'terminé', 'annulé', name='jobstatus'))
sa.Column('priority', sa.Enum('basse', 'normale', 'haute', 'urgente', name='priority'))
```

### 2. Modèle

```python
# models/job.py — APRÈS
status = Column(
    Enum(JobStatus, values_callable=lambda x: [e.value for e in x]),
    ...
)
priority = Column(
    Enum(Priority, values_callable=lambda x: [e.value for e in x]),
    ...
)
```

`values_callable` garantit que l'ORM envoie les **valeurs françaises** (`planifié`, `terminé`, etc.).

---

## Procédure de reset DB

```bash
# 1. Nettoyer
docker exec postgres psql -U lob -d resq_db -c "
DROP TABLE IF EXISTS review, material, job_photo, checklist_item,
                     job, client, \"user\", alembic_version CASCADE;
DROP TYPE IF EXISTS role, jobstatus, priority CASCADE;
"

# 2. Rebuild image
docker build -t resq-backend:latest -f backend/Dockerfile backend/

# 3. Relancer compose
docker compose -f deploy/docker-compose.yml down
docker compose -f deploy/docker-compose.yml up -d

# 4. Migrations + seed
docker exec resq-backend-1 alembic upgrade head
docker exec resq-backend-1 python -m app.seed
```

---

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `alembic/versions/5cc5d1686947_add_job_table.py` | Enums en français |
| `app/models/job.py` | `values_callable` restauré |
| `app/seed.py` | `"user"` quoté (mot réservé PG) |
| `pyproject.toml` | Ajout `psycopg2-binary` (driver sync Alembic) |
| `deploy/docker-compose.yml` | `name: resq` |
