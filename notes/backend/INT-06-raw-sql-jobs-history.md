# INT-06 — Raw SQL dans le Repository (historique jobs)

> **Objectif** : Implémenter `GET /clients/{id}/jobs` avec du **raw SQL** pour comparer avec l'ORM
> **Stack** : SQLAlchemy `text()` + raw SQL + mapping manuel

---

## 1. L'endpoint

```
GET /api/v1/clients/{client_id}/jobs?page=1&page_size=50
```

Retourne l'historique des interventions d'un client :

```json
{
  "items": [
    {
      "id": 1,
      "title": "Maintenance climatisation",
      "status": "planifié",
      "completed_at": null,
      "technician_name": "Guuleed Liban"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

---

## 2. Le Repository en RAW SQL

Fichier : `app/repositories/job.py`

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_client(self, client_id, page=1, page_size=50) -> list[dict]:
        offset = (page - 1) * page_size
        sql = text("""
            SELECT
                j.id,
                j.title,
                j.status,
                j.completed_at,
                u.full_name AS technician_name
            FROM job j
            LEFT JOIN "user" u ON j.technician_id = u.id
            WHERE j.client_id = :client_id
            ORDER BY j.created_at DESC
            LIMIT :limit_val OFFSET :offset_val
        """)
        result = await self.db.execute(sql, {
            "client_id": client_id,
            "limit_val": page_size,
            "offset_val": offset,
        })
        rows = result.fetchall()

        # Mapping manuel des rows → dicts
        return [
            {
                "id": row.id,
                "title": row.title,
                "status": row.status,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "technician_name": row.technician_name,
            }
            for row in rows
        ]
```

---

## 3. ORM vs Raw SQL : comparaison côte à côte

### ORM (SQLAlchemy) — comme dans ClientRepository

```python
# ➕ Avantages
query = select(Job)
query = query.where(Job.client_id == client_id)
query = query.order_by(Job.created_at.desc())
query = query.offset(...).limit(...)

result = await self.db.execute(query)
jobs = result.scalars().all()

# ✅ Type-safe : jobs[0].title → str
# ✅ Auto-mapping : pas besoin de convertir
# ✅ Relations : jobs[0].technician.full_name
# ✅ Réutilisable : on peut composer des filtres dynamiquement
```

### Raw SQL — comme dans JobRepository

```python
# ➕ Avantages
sql = text("""
    SELECT j.id, j.title, j.status, j.completed_at, u.full_name AS technician_name
    FROM job j
    LEFT JOIN "user" u ON j.technician_id = u.id
    WHERE j.client_id = :client_id
    ORDER BY j.created_at DESC
    LIMIT :limit_val OFFSET :offset_val
""")

result = await self.db.execute(sql, {...})
rows = result.fetchall()

# ❌ Mapping manuel : row → dict
# ❌ row.title vs row["title"] (dépend du driver)
# ❌ Pas de typage : "status" est un str, pas un JobStatus
# ❌ Fragile : si on ajoute une colonne, faut modifier le SQL ET le mapping
```

### Tableau comparatif

| Critère                | ORM (SQLAlchemy)                     | Raw SQL                                         |
| ---------------------- | ------------------------------------ | ----------------------------------------------- |
| **Lisibilité**         | `Job.client_id == id`                | `WHERE j.client_id = :client_id`                |
| **Type safety**        | ✅ `jobs[0].title` → `str`           | ❌ `row.title` → `Any`                          |
| **Mapping**            | Automatique (ORM → objet)            | Manuel (row → dict)                             |
| **Requêtes complexes** | Fastidieux (plusieurs `join()`)      | Naturel (SQL pur)                               |
| **Migrations**         | Couplé (Alembic détecte les modèles) | Déconnecté (faut suivre le schéma manuellement) |
| **Perf**               | Léger overhead                       | Brut (ce que la DB reçoit)                      |

---

## 4. `text()` et les paramètres nommés

```sql
SELECT * FROM job WHERE client_id = :client_id
```

```python
await db.execute(sql, {"client_id": 5})
```

**Pourquoi les `:` au lieu des `?` ?**

- `:client_id` = paramètre **nommé** (SQLAlchemy style)
- `?` = paramètre **positionnel** (sqlite3 natif)
- Avec `text()`, on utilise les `:` qui sont **plus lisibles** et **réutilisables**

**Sécurité :** Les paramètres sont **toujours** passés via `:params`, jamais interpolés dans la chaîne SQL. Ça protège des injections SQL.

---

## 5. Le `LEFT JOIN` expliqué

```sql
FROM job j
LEFT JOIN "user" u ON j.technician_id = u.id
```

| Type de JOIN       | Comportement                                              |
| ------------------ | --------------------------------------------------------- |
| `INNER JOIN`       | Exclut les jobs sans technicien assigné                   |
| **`LEFT JOIN`** ✅ | Garde **tous** les jobs, même si `technician_id` est NULL |

Si un job n'a pas de technicien, `technician_name` sera `null` dans la réponse.

---

## 6. `ORDER BY created_at DESC` — pourquoi pas `scheduled_date` ?

```sql
ORDER BY j.created_at DESC
```

**Pourquoi `created_at` et pas `scheduled_date` ?**

- `scheduled_date` est la **date planifiée** (peut être dans le futur)
- `created_at` est la **date de création** (toujours dans le passé)
- L'historique doit montrer les jobs du plus **récemment créé** au plus **ancien**

---

## 7. Test raw SQL pur

```bash
cd backend/
.venv/bin/python -c "
import asyncio
from app.core.database import async_session
from sqlalchemy import text

async def test_raw_sql():
    async with async_session() as session:
        sql = text('''
            SELECT j.id, j.title, j.status, u.full_name AS tech
            FROM job j
            LEFT JOIN \"user\" u ON j.technician_id = u.id
            WHERE j.client_id = :cid
            ORDER BY j.created_at DESC
        ''')
        result = await session.execute(sql, {'cid': 1})
        rows = result.fetchall()
        for row in rows:
            print(f'{row.id}: {row.title} ({row.status}) - {row.tech}')

asyncio.run(test_raw_sql())
"
```

---

## 8. Quand utiliser l'ORM vs Raw SQL ?

### ✅ ORM pour :

- CRUD standard (98% des cas)
- Requêtes avec filtres dynamiques
- Relations (client.jobs, job.technician)
- Tests et refactoring (le typage aide)
- **Ce qu'on fait dans ResQ pour la prod**

### 🔬 Raw SQL pour :

- Requêtes avec JOINs complexes + agrégations
- Rapports et statistiques (dashboard)
- Migration ponctuelle (one-shot)
- **Ce qu'on vient de faire pour apprendre**

---

INT-06 — GET /clients/{id}/jobs (2 pts) — ✅ Terminé\*\*

## 9. Tests validés (2/2)

| #            | Test                                                       | Résultat |
| ------------ | ---------------------------------------------------------- | -------- |
| TC-INT-06-01 | GET /clients/{id}/jobs — historique paginé avec technicien | ✅       |
| TC-INT-06-02 | GET /clients/999/jobs — client inexistant (404)            | ✅       |

### Ce qui a été fait

| Fichier                                | Rôle                                                   |
| -------------------------------------- | ------------------------------------------------------ |
| `app/models/job.py`                    | Modèle Job créé (nécessaire pour la table)             |
| `app/models/__init__.py`               | `Job` importé                                          |
| `app/repositories/job.py`              | **Raw SQL** — `text()` + `LEFT JOIN` + mapping manuel  |
| `app/services/job.py`                  | Service avec `_check_client_exists()` en raw SQL aussi |
| `app/schemas/job.py`                   | Schemas `JobHistoryItem`, `JobHistoryResponse`         |
| `app/api/v1/clients.py`                | Endpoint `GET /{client_id}/jobs` ajouté                |
| `notes/INT-06-raw-sql-jobs-history.md` | Note pédagogique : ORM vs Raw SQL                      |

---

## 10. Verdict : ORM vs Raw SQL

Après avoir testé les deux approches dans le projet :

- **ORM** (ClientRepository) → plus rapide à écrire, typé, résilient aux changements de schéma
- **Raw SQL** (JobRepository) → plus lisible pour les JOINs, mais mapping manuel fragile

On reste sur **SQLAlchemy ORM pour la prod**, et on garde le raw SQL pour les cas spécifiques (rapports, dashboard, uniques).
