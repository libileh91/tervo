# INT-37 : Tests API — Photos, Matériaux, Rapport, Avis

## Contexte

Tests d'intégration API pour les endpoints du Sprint 2.2. Utilise `pytest` +
`httpx.AsyncClient` avec une base de données SQLite isolée.

---

## Stack technique

| Outil | Rôle |
|---|---|
| `pytest` | Runner de tests |
| `pytest-asyncio` | Support async (`asyncio_mode = auto`) |
| `pytest-cov` | Couverture de code |
| `httpx.AsyncClient` + `ASGITransport` | Appels HTTP sans serveur |
| `SQLite` (test_resq.db) | Base de test isolée, tables créées/drop à chaque test |

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `backend/tests/test_api.py` | 28 tests répartis en 5 classes |
| `backend/tests/test_photo.jpg` | Image JPEG valide (825 bytes) pour les tests upload |
| `backend/pytest.ini` | Config : `asyncio_mode = auto` |

---

## Structure des tests

```
TestPhotos          (7 tests)  — upload success/format/auth/assignation, delete x3
TestMaterials       (5 tests)  — CRUD + auth
TestReport          (4 tests)  — download terminé/non/not_found/no_auth
TestReview          (9 tests)  — GET valide/invalide/expiré, POST success/double/etc
TestIntegration     (3 tests)  — complete_job → review créé
```

## Points clés

### Test database isolée

```python
TEST_DB_URL = "sqlite+aiosqlite:///./test_resq.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)

# Dans la fixture client():
await _create_tables()       # Base.metadata.create_all
# ... tests ...
await _drop_tables()          # Base.metadata.drop_all
```

Chaque test repart d'une base vierge → pas de dépendance entre tests.

### ASGITransport au lieu de app=app

```python
# ❌ Cette syntaxe nécessite httpx ≥ 0.28
async with httpx.AsyncClient(app=app, base_url="http://test") as ac:

# ✅ Compatible avec httpx ≤ 0.27
transport = ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
```

### Image JPEG valide pour les tests upload

`PIL.Image.open()` échoue sur du texte brut → il faut une vraie image :

```python
from PIL import Image
img = Image.new('RGB', (100, 100), color='red')
img.save('tests/test_photo.jpg', 'JPEG')
```

### Fixture other_tech_user pour les tests 403

Un token JWT d'un user qui n'existe pas en DB → 401 (auth reject).
Un token JWT d'un user qui existe mais pas assigné au job → 403 (assignation reject).

```python
@pytest.fixture
async def other_tech_user(db: AsyncSession) -> User:
    user = User(username="other_tech", ...)
    db.add(user)
    await db.commit()
    return user
```

---

## Résultats

```
28 passed in 8.17s
Coverage: 65% (target: ≥ 60%)
```

## Commandes

```bash
cd backend/

# Lancer les tests
.venv/bin/python -m pytest tests/test_api.py -v

# Avec couverture
.venv/bin/python -m pytest tests/test_api.py --cov=app --cov-report=term-missing

# Un seul test
.venv/bin/python -m pytest tests/test_api.py::TestPhotos::test_upload_photo_success -v
```
