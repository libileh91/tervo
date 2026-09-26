# INT-17 — ChecklistService + ChecklistRepository (Refactor)

> **Objectif** : Extraire la logique checklist dans un service/repository dédié
> **Stack** : FastAPI + SQLAlchemy + Repository/Service pattern

---

## 1. Pourquoi un refactor ?

Avant (monolithique) :

```
JobRepository
├── create()          ← crée le job
├── _seed_checklist() ← seed la checklist (privé !)
└── ...

JobService
├── complete_job()
│   └── count unchecked inline ← logique noyée
```

Après (séparé) :

```
ChecklistRepository          ← requêtes DB checklist
ChecklistService             ← logique métier checklist
    ├── create_default_items()
    ├── validate_all_checked()
    └── batch_update()

JobService
    └── complete_job()
        └── ChecklistService.validate_all_checked()  ← appel délégué
```

**Avantage :** chaque classe a une responsabilité unique. Plus facile à tester et à maintenir.

---

## 2. ChecklistRepository

```python
class ChecklistRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_items(self, job_id: int) -> list[ChecklistItem]:
        """Tous les items d'un job, triés par position."""
        result = await self.db.execute(
            select(ChecklistItem)
            .where(ChecklistItem.job_id == job_id)
            .order_by(ChecklistItem.position.asc())
        )
        return list(result.scalars().all())

    async def batch_update(self, job_id: int, items_data: list[dict]) -> int:
        """Update multiple items. Commit unique à la fin."""
        for item_data in items_data:
            item = await self.db.execute(
                select(ChecklistItem).where(
                    ChecklistItem.id == item_data["id"],
                    ChecklistItem.job_id == job_id,
                )
            ).scalar_one_or_none()
            if item is None:
                raise ValueError(...)
            # Mise à jour
            if "checked" in item_data: item.checked = item_data["checked"]
            if "note" in item_data:    item.note = item_data["note"]
        await self.db.commit()
        return count

    async def count_unchecked_by_category(self, job_id: int) -> dict[str, int]:
        """Compte les unchecked groupés par catégorie (pré/post)."""
        result = await self.db.execute(
            select(ChecklistItem.category, func.count(ChecklistItem.id))
            .where(ChecklistItem.job_id == job_id, ChecklistItem.checked == False)
            .group_by(ChecklistItem.category)
        )
        return {row[0]: row[1] for row in result.fetchall()}
```

**Point clé :** `count_unchecked_by_category` utilise `GROUP BY` SQL — une seule requête au lieu de deux.

---

## 3. ChecklistService

### validate_all_checked() — messages détaillés

```python
async def validate_all_checked(self, job_id: int) -> dict:
    unchecked_by_cat = await self.repo.count_unchecked_by_category(job_id)
    total = sum(unchecked_by_cat.values())

    if total == 0:
        return {"is_valid": True, "errors": []}

    errors = []
    for cat, count in unchecked_by_cat.items():
        label = "pré-intervention" if cat == "pre_intervention" else "post-intervention"
        errors.append(f"{count} item(s) {label} non cochés")

    return {
        "is_valid": False,
        "errors": errors,
        "detail": f"{total} items non cochés ({', '.join(errors)})",
    }
```

**Résultat :** `"5 items non cochés (3 item(s) pré-intervention non cochés, 2 item(s) post-intervention non cochés)"`

---

## 4. Migration des dépendances

| Avant                                              | Après                                                |
| -------------------------------------------------- | ---------------------------------------------------- |
| `DEFAULT_PRE_ITEMS` dans `repositories/job.py`     | Déplacé dans `services/checklist.py`                 |
| `_seed_checklist()` dans `JobRepository`           | Supprimé → `ChecklistService.create_default_items()` |
| Validation inline dans `JobService.complete_job()` | `ChecklistService.validate_all_checked()`            |
| `ChecklistItem` importé dans `services/job.py`     | Supprimé (plus besoin direct)                        |

---

## 5. Piège évité : `async with self.db.begin()`

```diff
- async with self.db.begin():  # ❌ Erreur : transaction déjà active
+ await self.db.commit()       # ✅ Commit unique après toutes les mises à jour
```

FastAPI + `get_db()` démarre déjà une transaction. Utiliser `begin()` à l'intérieur cause : `InvalidRequestError: A transaction is already begun on this Session`.
