# Fix : `PUT /jobs/{id}/start` 500 — Timezone aware vs naive datetime

> **Date :** 13/07/2026
> **Backend :** `backend/app/services/job.py`

---

## 1. Le bug

```
PUT http://localhost:3001/api/v1/jobs/1/start → 500 Internal Server Error
```

Console frontend :
```
client.ts:24 PUT http://localhost:3001/api/v1/jobs/1/start 500 (Internal Server Error)
```

---

## 2. La cause

### Code qui plante
```python
# backend/app/services/job.py
from datetime import datetime, timezone

job.started_at = datetime.now(timezone.utc)  # ← timezone-aware
```

### Pourquoi ça plante
En Python, il existe deux types de datetime :
- **Naive** : `datetime.utcnow()` → `2026-07-13T15:17:42.668543` (sans fuseau)
- **Aware** : `datetime.now(timezone.utc)` → `2026-07-13T15:17:42.668543+00:00` (avec fuseau)

Le modèle SQLAlchemy a :
```python
started_at = Column(DateTime, nullable=True)  # ← pas de timezone=True
```

Sans `timezone=True`, SQLAlchemy crée une colonne PostgreSQL `TIMESTAMP` (sans timezone). Quand on essaie d'insérer un datetime **aware** dans une colonne **sans timezone**, PostgreSQL lève une erreur.

### Pourquoi ça ne plante pas en SQLite
SQLite n'a pas de concept de timezone pour les dates — il stocke tout comme texte. Donc le bug n'apparaissait qu'en PostgreSQL.

---

## 3. La solution

```python
# ✅ Naive — compatible avec la colonne DateTime sans timezone
job.started_at = datetime.utcnow()
```

Deux autres endroits avaient le même problème :
```python
# Dans start_job
job.started_at = datetime.now(timezone.utc)    # → datetime.utcnow()

# Dans complete_job
job.completed_at = datetime.now(timezone.utc)  # → datetime.utcnow()
```

---

## 4. Recommandation long-terme

Pour une meilleure gestion des timezone, il faudrait :
1. Changer la colonne : `Column(DateTime(timezone=True), nullable=True)`
2. Utiliser `datetime.now(timezone.utc)` partout
3. Adapter les calculs (comme `elapsed_minutes`) pour gérer les timezone

Mais ce changement nécessite une migration Alembic et des ajustements dans tous
les schémas Pydantic. Pour le sprint 4.1, `datetime.utcnow()` suffit.

---

## 5. Vérification

```bash
# Avant
curl -s -X PUT http://localhost:8000/api/v1/jobs/5/start
# → 500

# Après
curl -s -X PUT http://localhost:8000/api/v1/jobs/5/start
# → 200 { "id": 5, "status": "en_cours", "started_at": "2026-07-13T15:17:42.668543" }
```

---

## 6. Résumé

| Concept | Naive | Aware |
|---------|-------|-------|
| Exemple | `2026-07-13T15:17:42` | `2026-07-13T15:17:42+00:00` |
| Fonction | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| Compatible TIMESTAMP | ✅ | ❌ |
| Compatible TIMESTAMPTZ | ✅ | ✅ |
| PostgreSQL sans timezone | ✅ | ❌ |
