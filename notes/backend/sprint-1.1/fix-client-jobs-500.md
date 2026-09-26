# Fix : 500 Internal Server Error sur GET /clients/{id}/jobs

> **Date :** 25/06/2026
> **Contexte :** Consultation de l'historique des jobs d'un client → 500 Internal Server Error. Aucun log backend, juste une erreur 500 dans la console frontend.

---

## Cause

```python
# repositories/job.py — ligne 133
"completed_at": row.completed_at.isoformat() if row.completed_at else None,
```

Le endpoint utilise du **raw SQL** (pas SQLAlchemy ORM) :

```python
sql = text("""
    SELECT j.id, j.title, j.status, j.completed_at, u.full_name AS technician_name
    FROM job j
    LEFT JOIN "user" u ON j.technician_id = u.id
    WHERE j.client_id = :client_id
    ORDER BY j.created_at DESC
    ...
""")
```

Avec raw SQL + SQLite, les colonnes `datetime` sont retournées comme des **strings déjà formatées** en ISO (SQLite n'a pas de type datetime natif). Mais le code tente d'appeler `.isoformat()` (une méthode de `datetime.datetime`) sur ces strings → `AttributeError`.

```
AttributeError: 'str' object has no attribute 'isoformat'
```

## Pourquoi ça marche en dev mais plante en recette ?

En développement, les tests utilisent SQLAlchemy ORM (pas raw SQL), donc ce code n'est pas exécuté. Le raw SQL est un cas particulier.

## Correction

```python
# ✅ APRÈS : compatible SQLite (str) ET PostgreSQL (datetime)
"completed_at": row.completed_at.isoformat()
if hasattr(row.completed_at, "isoformat")
else row.completed_at,
```

- `str` n'a pas `.isoformat()` → `hasattr` retourne `False` → on passe la valeur brute (déjà en ISO string)
- `datetime.datetime` a `.isoformat()` → `hasattr` retourne `True` → on formate
- `None` → on passe `None` (`hasattr` sur `None` retourne `False`)

## Leçon

Quand on fait du raw SQL avec SQLAlchemy, les types retournés diffèrent selon le moteur de base de données :

| Moteur | Type de `datetime` | `.isoformat()` compatible ? |
|--------|-------------------|----------------------------|
| SQLite | `str` (ISO) | ❌ Non |
| PostgreSQL | `datetime` | ✅ Oui |
| MySQL | `datetime` | ✅ Oui |

Toujours prévoir les deux cas avec `hasattr()` ou convertir explicitement.

---

## Fichier modifié

- `backend/app/repositories/job.py` → ligne 133 : `if row.completed_at` → `if hasattr(row.completed_at, "isoformat")`
