# INT-32 : Endpoint public `GET /review/{share_token}`

## Contexte

Endpoint **public** (sans authentification) permettant au client de consulter les
infos d'un job via un lien unique partagé par le technicien.

Le lien est généré automatiquement à la complétion du job (INT-34) sous la forme :
`https://tervo.app/review/{share_token}`.

---

## Architecture en couches

```
Router (api/v1/reviews.py)
  └── Service (services/review.py)
       └── Repository (repositories/review.py)
            └── Model ORM (models/review.py)
                 └── SQLite / PostgreSQL
```

Chaque couche a un rôle précis et isolé :

| Couche         | Rôle                                                   | Dépend de       |
| -------------- | ------------------------------------------------------ | --------------- |
| **Router**     | Définir la route HTTP + validation de base             | Service         |
| **Service**    | Règles métier (expiration, validation token)           | Repository      |
| **Repository** | Accès DB (requêtes SQLAlchemy)                         | Model ORM       |
| **Model**      | Mapping ORM table `review`                             | SQLAlchemy Base |
| **Schema**     | Sérialisation/désérialisation Pydantic pour la réponse | —               |

---

## 1. Schema — `schemas/review.py`

Définit les modèles Pydantic pour la réponse publique.

```python
class ReviewJobInfo(BaseModel):
    """Infos job exposées publiquement."""
    title: str
    completed_at: str | None = None


class ReviewTechnicianInfo(BaseModel):
    """Infos technicien exposées publiquement."""
    full_name: str | None = None


class ReviewPublicResponse(BaseModel):
    """Réponse complète pour GET /review/{share_token}."""
    job: ReviewJobInfo
    technician: ReviewTechnicianInfo
    already_reviewed: bool
```

**Points clés :**

- 3 sous-objets imbriqués pour une réponse structurée
- `already_reviewed: bool` = `review.submitted_at is not None`
- Schema validé automatiquement par FastAPI comme `response_model`

---

## 2. Repository — `repositories/review.py`

Accès DB avec **eager-loading** des relations.

```python
class ReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_token(self, token: str) -> Review | None:
        result = await self.db.execute(
            select(Review)
            .options(
                selectinload(Review.job).selectinload(Job.technician),
            )
            .where(Review.share_token == token)
        )
        return result.scalar_one_or_none()
```

### Pourquoi `selectinload` chaîné ?

```python
selectinload(Review.job).selectinload(Job.technician)
```

Sans ce chaînage, `review.job` serait chargé mais `job.technician` serait un proxy SQLAlchemy non résolu. Le chaînage force le chargement des **deux niveaux** en une seule requête (2x SELECT IN).

**Alternative** : accéder à `job.technician` en-dehors de la session → `DetachedInstanceError`.

---

## 3. Service — `services/review.py`

Règles métier : token invalide, expiration, format réponse.

```python
class ReviewService:
    def __init__(self, db: AsyncSession):
        self.repo = ReviewRepository(db)

    async def get_review_by_token(self, token: str) -> dict:
        review = await self.repo.get_by_token(token)

        if review is None:
            raise HTTPException(404, detail="Lien invalide ou expiré")

        # Vérification expiration
        now = datetime.now(timezone.utc)
        expires = review.share_token_expires_at
        if expires.tzinfo is None:          # SQLite stocke des datetime naive
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            raise HTTPException(404, detail="Lien invalide ou expiré")

        return {
            "job": {
                "title": review.job.title,
                "completed_at": ...,  # isoformat
            },
            "technician": {
                "full_name": review.job.technician.full_name if review.job.technician else None,
            },
            "already_reviewed": review.submitted_at is not None,
        }
```

### Le piège du timezone aware vs naive

| Base de données | Type stocké            | Récupéré par SQLAlchemy |
| --------------- | ---------------------- | ----------------------- |
| SQLite          | `DATETIME` (pas de tz) | `datetime` **naive**    |
| PostgreSQL      | `TIMESTAMPTZ`          | `datetime` **aware**    |

→ `datetime.now(timezone.utc)` donne un datetime **aware**.
→ SQLAlchemy lit `share_token_expires_at` depuis SQLite → **naive**.
→ Comparer un aware avec un naive → `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Fix** : détecter et convertir :

```python
if expires.tzinfo is None:
    expires = expires.replace(tzinfo=timezone.utc)
```

---

## 4. Router — `api/v1/reviews.py`

Route **publique** : pas de `Depends(get_current_user)`.

```python
router = APIRouter(prefix="/review", tags=["reviews"])

@router.get(
    "/{share_token}",
    response_model=ReviewPublicResponse,
    summary="Get review info by share token (public)",
)
async def get_review_by_token(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Aucune authentification requise."""
    service = ReviewService(db)
    return await service.get_review_by_token(share_token)
```

### Différence clé avec les endpoints auth

```python
# Endpoint privé (avec auth)
def get_job(current_user: User = Depends(get_current_user), ...):

# Endpoint public (sans auth)
def get_review_by_token(...):
```

Si on met `Depends(get_current_user)` sur un endpoint public, le navigateur enverra `Authorization: Bearer null` → 401.

---

## 5. Enregistrement dans `main.py`

```python
from app.api.v1.reviews import router as reviews_router

app.include_router(reviews_router, prefix=settings.API_V1_PREFIX)
# → Le préfixe /api/v1 s'applique → route finale = /api/v1/review/{share_token}
```

---

## Tests curl

```bash
# 1. Token valide → 200 + infos job/technicien
TOKEN="0240ade082cb423b8e46a47435c64854"
curl -s "http://localhost:8000/api/v1/review/${TOKEN}" | python3 -m json.tool
# {
#     "job": {
#         "title": "Test refactor checklist",
#         "completed_at": "2026-06-07T15:20:20.692988"
#     },
#     "technician": {
#         "full_name": "Jean Martin"
#     },
#     "already_reviewed": false
# }

# 2. Token invalide → 404
curl -s "http://localhost:8000/api/v1/review/invalid_token_xxx"
# → {"detail":"Lien invalide ou expiré"}

# 3. Sans auth → 200 (public OK)
curl -s -w "\nHTTP %{http_code}" "http://localhost:8000/api/v1/review/${TOKEN}" | tail -1
# → HTTP 200

# 4. Token expiré → 404
# Modifier share_token_expires_at dans le passé
curl -s "http://localhost:8000/api/v1/review/${TOKEN}"
# → {"detail":"Lien invalide ou expiré"}
```

---

## Fichiers créés

| Fichier                              | Rôle                                      |
| ------------------------------------ | ----------------------------------------- |
| `backend/app/repositories/review.py` | Accès DB : get_by_token() avec eager-load |
| `backend/app/services/review.py`     | Règles métier : expiration, format        |
| `backend/app/schemas/review.py`      | Schémas Pydantic pour réponse publique    |
| `backend/app/api/v1/reviews.py`      | Router GET + (futur POST)                 |

## Fichiers modifiés

| Fichier               | Changement                                  |
| --------------------- | ------------------------------------------- |
| `backend/app/main.py` | Import + include_router du `reviews_router` |

---

## Commandes utiles

```bash
# Créer un review de test manuellement
cd backend/
.venv/bin/python -c "
import asyncio, uuid
from datetime import datetime, timedelta, timezone
from app.core.database import async_session
from app.models.review import Review

async def main():
    async with async_session() as db:
        token = uuid.uuid4().hex
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).replace(tzinfo=None)
        review = Review(job_id=12, rating=5, share_token=token, share_token_expires_at=expires)
        db.add(review)
        await db.commit()
        print(f'Token: {token}')

asyncio.run(main())
"

# Forcer un token expiré (UPDATE direct)
.venv/bin/python -c "
import asyncio
from datetime import datetime
from app.core.database import async_session
from app.models.review import Review
from sqlalchemy import select

async def main():
    async with async_session() as db:
        r = (await db.execute(select(Review).where(Review.id == 1))).scalar_one()
        r.share_token_expires_at = datetime(2020, 1, 1)
        await db.commit()

asyncio.run(main())
"
```

## Récapitulatif INT-32 ✅

### Ce qui a été fait

| Fichier                                         | Action      | Rôle                                                                                 |
| ----------------------------------------------- | ----------- | ------------------------------------------------------------------------------------ |
| `backend/app/repositories/review.py`            | **Créé**    | Accès DB avec `get_by_token()` + `selectinload` chaîné (Review → Job → User)         |
| `backend/app/services/review.py`                | **Créé**    | Règles métier : validation token, expiration (timezone aware/naive), format réponse  |
| `backend/app/schemas/review.py`                 | **Créé**    | 3 schémas Pydantic : `ReviewJobInfo`, `ReviewTechnicianInfo`, `ReviewPublicResponse` |
| `backend/app/api/v1/reviews.py`                 | **Créé**    | Router avec `GET /review/{share_token}` (public, no auth)                            |
| `backend/app/main.py`                           | **Modifié** | Import + `include_router` du reviews_router                                          |
| `docs/stages/stage2/sprint-2.2/tasks.md`        | **Modifié** | 5 critères INT-32 cochés ✅                                                          |
| `docs/stages/stage2/sprint-2.2/test-cases.json` | **Modifié** | `actual_result` remplis pour TC-32-01/02/03                                          |
| `notes/backend/INT-32-review-get.md`            | **Créé**    | Note pédagogique détaillée avec mermaid, tableaux, pièges (timezone), tests curl     |

### Tests validés

| Test                                           | Résultat |
| ---------------------------------------------- | -------- |
| Token valide → 200 + job/technician/info       | ✅       |
| Token invalide → 404 "Lien invalide ou expiré" | ✅       |
| Token expiré → 404 "Lien invalide ou expiré"   | ✅       |
| Sans auth → 200 (public)                       | ✅       |

### Piège évité 🔥

**Timezone aware vs naive** avec SQLite. `datetime.now(timezone.utc)` donne un datetime **aware**, SQLAlchemy lit `share_token_expires_at` depuis SQLite comme **naive**. Comparer les deux → `TypeError`. Fix : `if expires.tzinfo is None: expires = expires.replace(tzinfo=timezone.utc)`.
