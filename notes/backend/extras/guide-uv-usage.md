# Guide d'utilisation `uv` — Workflow complet

> **`uv`** est le gestionnaire de paquets Python d'Astral (Rust).
> Remplace `pip` + `venv` + `pip-tools` en un seul binaire.

---

## Table des matières

1. [Rappel — Installer uv](#1-rappel--installer-uv)
2. [Dev — Setup initial](#2-dev--setup-initial)
3. [Dev — Quotidien](#3-dev--quotidien)
4. [Dev — Gestion des dépendances](#4-dev--gestion-des-dépendances)
5. [Dev — Environnements et Python](#5-dev--environnements-et-python)
6. [Test — Lancer les tests](#6-test--lancer-les-tests)
7. [Test — Intégration continue (CI)](#7-test--intégration-continue-ci)
8. [Deploy — Production](#8-deploy--production)
9. [Deploy — Docker](#9-deploy--docker)
10. [Dépannage](#10-dépannage)
11. [Aide-mémoire](#11-aide-mémoire)

---

## 1. Rappel — Installer uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# → ~/.local/bin/uv (ajoute-le au PATH si pas déjà)
```

Vérifier :

```bash
uv --version
# → uv 0.11.24
```

---

## 2. Dev — Setup initial

```bash
cd backend/

# 1. Créer le venv (une fois)
uv venv
# → .venv/ créé avec Python 3.12.0

# 2. Installer les dépendances
uv sync
# → lit pyproject.toml → installe tout → génère uv.lock

# 3. Lancer le serveur
uv run uvicorn main:app --reload
```

### À la place de l'ancien pip

| Avant | Après |
|---|---|
| `python -m venv .venv` | `uv venv` |
| `.venv/bin/pip install -r requirements.txt` | `uv sync` |
| `.venv/bin/python -m uvicorn main:app` | `uv run uvicorn main:app` |
| `source .venv/bin/activate` + `uvicorn ...` | `uv run uvicorn ...` (ou `source .venv/bin/activate`) |

**Astuce** : `uv run <cmd>` exécute n'importe quelle commande **dans** le venv sans avoir à l'activer.

---

## 3. Dev — Quotidien

```bash
# Lancer le serveur
uv run uvicorn main:app --reload

# Lancer un script Python one-shot
uv run python scripts/seed.py

# Lancer une commande interactive dans le venv
uv run --with bash
# ou active le venv classiquement :
source .venv/bin/activate

# Exécuter un fichier Python directement
uv run python -c "from app.config import settings; print(settings.APP_NAME)"
# → ResQ

# Lancer Alembic (migrations)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "ma migration"

# Lancer les seeds
uv run python app/seed.py
```


### `uv run` vs `source .venv/bin/activate`

#### `uv run` est **indépendant de l'activation du venv**

Tu as remarqué que `uv run uvicorn main:app` fonctionne **avec ou sans** `source .venv/bin/activate`. Pourquoi ?

#### Comment `uv run` trouve le venv

`uv run` n'a pas besoin que le venv soit activé. Il cherche automatiquement :

```mermaid
flowchart LR
    A[uv run uvicorn] --> B{Cherche .venv/}
    B --> C[Dossier courant]
    B --> D[Dossiers parents]
    B --> E[Variable VIRTUAL_ENV]
    C ou D ou E --> F[.venv trouvé ?]
    F -->|Oui| G[Utilise python de .venv/bin/]
    F -->|Non| H[Utilise python système]
```

1. **Dossier courant** : `./.venv/`
2. **Dossier parents** : `../.venv/`, `../../.venv/`, etc.
3. **Variable `VIRTUAL_ENV`** : positionnée par `source .venv/bin/activate`

Dès qu'il trouve un `.venv/`, il monte son PATH et exécute la commande dedans.

#### Ça veut dire quoi concrètement ?

```bash
# Sans activation — uv run trouve .venv/ tout seul
cd backend/
uv run uvicorn main:app --reload   # ✅  utilise .venv/bin/python

# Avec activation — .venv est dans le PATH en premier
echo "$PATH"
# → .../backend/.venv/bin:/home/lob/.pyenv/shims:...
uv run uvicorn main:app --reload    # ✅  utilise VIRTUAL_ENV
uvicorn main:app --reload           # ✅  utilise le PATH modifié
```

#### Mais pourquoi `uvicorn` seul (sans activation) ne marche pas ?

```bash
uvicorn main:app --reload
# → ModuleNotFoundError: No module named 'aiosqlite'
```

Parce que sans activation et sans `uv run`, ton shell utilise le Python **système** (pyenv global) qui n'a pas les dépendances. `uv run` est le pont qui connecte automatiquement la commande au bon venv.

| Commande | Venv activé ? | Résultat |
|---|---|---|
| `uv run uvicorn` | Peu importe | ✅ utilise `.venv/` |
| `uvicorn` | ✅ Oui | ✅ utilise `.venv/bin/` (PATH modifié) |
| `uvicorn` | ❌ Non | ❌ utilise Python global |

#### Résumé

- **`uv run <cmd>`** : trouve et utilise le venv **automatiquement** — pas besoin d'activation
- **`source .venv/bin/activate`** : modifie le PATH du shell courant — utile pour plusieurs commandes
- **`uv run` + activation** : les deux méthodes coexistent sans conflit — `uv run` utilise `VIRTUAL_ENV` s'il est positionné

#### Best practice — laquelle utiliser ?

| Contexte | Méthode recommandée | Pourquoi ? |
|---|---|---|
| **Lancer le serveur** une fois | `uv run uvicorn main:app --reload` | Une commande, pas d'activation, zéro risque d'utiliser le mauvais Python |
| **Plusieurs commandes** à la suite | `source .venv/bin/activate` puis `uvicorn`, `alembic`, `pytest`... | Évite de préfixer chaque ligne avec `uv run` |
| **Script one-shot** (seed, test, debug) | `uv run python script.py` | Indépendant du shell courant, reproductible |
| **CI / Docker** | `uv run uvicorn ...` | Pas d'interactivité, tout est automatisé |
| **Nouveau contributeur** qui découvre le projet | `uv run` | Pas besoin de savoir ce qu'est `source activate` |

**Ma recommandation : privilégie `uv run`.**

- Plus fiable : même si t'oublies d'activer le venv, ça marche
- Plus explicite : on voit tout de suite que la commande utilise le venv
- Plus portable : un `uv run` fonctionne pareil en dev, en CI, en Docker

L'activation (`source .venv/bin/activate`) reste utile quand tu vas enchaîner 10 commandes dans le même terminal — mais dans ce cas, pense à taper `which python` ou `which uvicorn` pour vérifier que le PATH est bien celui du `.venv/` (surtout avec pyenv qui peut interférer).

---

## 4. Dev — Gestion des dépendances

### `pyproject.toml` — la source de vérité

```toml
[project]
name = "resq-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "sqlalchemy>=2.0.0",
    # ...
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]
```

### Commandes

```bash
# Ajouter une dépendance (production)
uv add httpx

# Ajouter une dépendance (dev)
uv add --dev pytest-cov

# Ajouter avec une version spécifique
uv add "fastapi>=0.115.0"

# Retirer une dépendance
uv remove weasyprint

# Mettre à jour toutes les dépendances
uv sync --upgrade

# Mettre à jour une seule dépendance
uv lock --upgrade-package pydantic

# Voir l'arbre des dépendances
uv tree

# Voir ce qui est installé
uv pip list

# Chercher si un paquet est installé
uv pip list | grep aiosqlite

# Voir les dépendances obsolètes
uv outdated
```

### `uv.lock` — le lockfile

```bash
# Générer / mettre à jour le lockfile
uv lock

# Installer depuis le lockfile (sans le modifier)
uv sync --frozen
```

À **commiter** dans git (comme `bun.lock`). Il garantit que tout le monde
a exactement les mêmes versions en dev et en CI.

---

## 5. Dev — Environnements et Python

```bash
# Lister les versions Python disponibles
uv python list

# Installer une version Python
uv python install 3.10 3.11 3.12

# Voir la version utilisée
uv python version

# Créer le venv avec une version spécifique
uv venv --python 3.11

# Recréer le venv depuis zéro
rm -rf .venv && uv venv && uv sync
```

---

## 6. Test — Lancer les tests

```bash
# Tous les tests
uv run pytest

# Avec sortie verbose
uv run pytest tests/ -v

# Avec couverture
uv run pytest --cov=app

# Un fichier spécifique
uv run pytest tests/test_auth.py -v

# Un test spécifique (par nom)
uv run pytest tests/test_auth.py -v -k "test_login"
```

### Test rapide sans pytest (one-shot)

```bash
uv run python -c "
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        r = await client.post('/api/v1/auth/login',
            json={'username':'tech1','password':'password123'})
        print(f'{r.status_code} - {r.json()}')

asyncio.run(test())
"
```

---

## 7. Test — Intégration continue (CI)

### GitHub Actions — workflow recommandé

```yaml
jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.11"
      - run: uv sync --frozen
      - run: uv run pytest tests/ --cov=app
```

**Pourquoi `astral-sh/setup-uv` ?**
- Installe `uv` dans le runner GitHub
- Configure automatiquement le PATH
- Supporte le cache des dépendances (plus rapide)

**Pourquoi `--frozen` ?**
- Installe depuis `uv.lock` sans le modifier
- Garantit la reproductibilité exacte
- Échoue si `uv.lock` est périmé

---

## 8. Deploy — Production

```bash
# Build du package (sdist + wheel)
uv build
# → dist/resq_backend-0.1.0.tar.gz
# → dist/resq_backend-0.1.0-py3-none-any.whl

# Installer depuis le package buildé
uv pip install dist/resq_backend-0.1.0-py3-none-any.whl

# Exporter les dépendances pour déploiement sans uv
uv export --frozen --no-dev > requirements-prod.txt
```

### Export des dépendances pour un environnement sans uv

```bash
uv export --frozen --no-dev > requirements-prod.txt
```

Utile si le serveur de production n'a pas `uv` (mais l'idéal est d'avoir `uv` partout).

---

## 9. Deploy — Docker

### Avec `uv` dans l'image (recommandé)

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copier les fichiers de dépendances
COPY pyproject.toml uv.lock ./

# Installer uniquement les dépendances de production
RUN uv sync --frozen --no-dev

# Copier le code
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker multi-stage (optimisé)

```dockerfile
# Stage 1 : installation des dépendances
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2 : image finale
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY . .

EXPOSE 8000
CMD [".venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 10. Dépannage

| Problème | Solution |
|---|---|
| `uv: command not found` | `export PATH="$HOME/.local/bin:$PATH"` ou ajouter à `~/.zshrc` |
| Le venv est corrompu | `rm -rf .venv && uv venv && uv sync` |
| `uv.lock` est périmé | `uv lock` pour le regénérer |
| Conflit de version Python | `uv venv --python 3.12` pour forcer une version |
| `uv sync` échoue | Vérifier la syntaxe de `pyproject.toml` (JSON valide dans les listes) |
| Ajouter un paquet sans `uv add` | Le faire manuellement dans `pyproject.toml` puis `uv lock` + `uv sync` |
| `uv run` trop lent | `uv sync` au préalable pour pré-installer |

---

## 11. Aide-mémoire

```bash
# ── Setup ──
uv venv                          # créer le venv
uv sync                          # installer les dépendances
uv sync --frozen                 # installer depuis uv.lock (CI)
uv sync --no-dev                 # installer seulement la prod

# ── Dépendances ──
uv add <pkg>                     # ajouter une dépendance prod
uv add --dev <pkg>               # ajouter une dépendance dev
uv remove <pkg>                  # retirer une dépendance
uv lock                          # mettre à jour uv.lock
uv tree                          # arbre des dépendances
uv outdated                      # dépendances obsolètes

# ── Exécution ──
uv run <cmd>                     # exécuter une commande dans le venv
uv run python script.py          # exécuter un script
uv run uvicorn main:app          # lancer le serveur
uv run pytest tests/ -v          # lancer les tests
uv run alembic upgrade head      # lancer les migrations

# ── Info ──
uv pip list                      # lister les paquets installés
uv python version                # version Python utilisée
uv python list                   # versions Python disponibles

# ── Build / Deploy ──
uv build                         # builder le package
uv export --frozen --no-dev      # exporter en requirements.txt
```

---

*Documentation générée suite à la migration pip → uv — Juin 2026*
