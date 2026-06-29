Bonne question. Voici pourquoi j'ai choisi SQLAlchemy (ORM) plutôt que du **raw SQL** dans le Repository :

## ORM (mon choix) vs Raw SQL

| Critère          | SQLAlchemy ORM ✅                                       | Raw SQL                                             |
| ---------------- | ------------------------------------------------------- | --------------------------------------------------- |
| **Productivité** | 3 lignes pour un `SELECT` complexe                      | ~15 lignes avec `cursor.execute()` + mapping manuel |
| **Type safety**  | `result.scalar_one_or_none()` retourne `Client \| None` | `fetchone()` retourne `Row \| None` → faut mapper   |
| **Relations**    | `client.jobs` directement accessible                    | `JOIN` manuel + mapping                             |
| **Async**        | `await db.execute()` natif                              | `aiosqlite` fonctionne aussi, mais plus verbeux     |
| **Migrations**   | Couplé avec Alembic (mêmes modèles)                     | Décalage risque : modèle ORM ≠ SQL réel             |

### Exemple de ce que donnerait du raw SQL

```python
# RAW SQL — Repository
class ClientRepository:
    async def list(self, page, page_size, search=None):
        query = "SELECT id, full_name, phone, email, address, postal_code, city, notes, created_at, updated_at FROM client"
        params = []
        if search:
            query += " WHERE full_name LIKE ? OR phone LIKE ?"
            params = [f"%{search}%", f"%{search}%"]
        query += " ORDER BY full_name ASC LIMIT ? OFFSET ?"
        params += [page_size, (page - 1) * page_size]

        result = await self.db.execute(query, params)
        rows = result.fetchall()
        return [Client(**dict(row)) for row in rows]  # ← mapping manuel
```

À chaque nouvelle entité ou nouveau champ, **tout le mapping est à faire à la main**.

### Mais tu as raison sur un point

Le **raw SQL est plus lisible** pour des requilles complexes avec plusieurs `JOIN`, des sous-requêtes, ou du full-text search. Et en termes de perf, il n'y a pas d'overhead ORM.

Si tu préfères, on peut basculer en **raw SQL** pour la couche Repository. C'est un choix d'équipe — l'architecture (Router → Service → Repository) reste la même, seule l'implémentation du Repository change.
