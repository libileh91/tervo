 # Migration `pip` → `uv` (Astral)

## Contexte

Remplacement de l'outillage Python classique (`pip` + `venv` + `requirements.txt`)
par `uv`, le gestionnaire de paquets ultra-rapide d'Astral (la boîte derrière Ruff).

## Pourquoi `uv` ?

- **Vitesse** : 10-100× plus rapide que `pip` (Rust vs Python)
- **Lockfile** : `uv.lock` généré automatiquement (comme `bun.lock` côté frontend)
- **Unifié** : remplace `pip` + `venv` + `pip-tools` en un seul binaire
- **pyproject.toml** : standard PEP 621, plus besoin de `requirements.txt`

---

## Étapes réalisées

### 1. Installation de `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# → ~/.local/bin/uv (v0.11.24)
```

### 2. Création de `pyproject.toml`

Le fichier `backend/requirements.txt` a été converti en `backend/pyproject.toml`
avec séparation propre des dépendances :

```toml
[project]
name = "tervo-backend"
version = "0.1.0"
description = "Tervo — Backend API (FastAPI + SQLAlchemy)"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    # ... 15 dépendances prod
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]
```

### 3. Création du venv + installation

```bash
cd backend/
rm -rf .venv                     # ancien venv pip
uv venv                          # nouveau venv (ultra-rapide)
uv sync                          # installe tout depuis pyproject.toml
```

### 4. Test

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# ✅ Application startup complete.
```

### 5. Suppression de `requirements.txt`

Plus besoin — `pyproject.toml` + `uv.lock` font le même travail proprement.

---

## Nouvelles commandes de référence

| Avant (pip) | Après (uv) |
|---|---|
| `python -m venv .venv` | `uv venv` |
| `.venv/bin/pip install -r requirements.txt` | `uv sync` |
| `.venv/bin/python -m uvicorn app.main:app` | `uv run uvicorn main:app` |
| `.venv/bin/pip list` | `uv pip list` |
| `.venv/bin/pip install <pkg>` | `uv add <pkg>` |
| `.venv/bin/pip freeze` | `uv lock` |
| `source .venv/bin/activate` | `source .venv/bin/activate` (identique) |
| `deactivate` | `deactivate` (identique) |

---

### 6. Mise à jour des docs — `INT-00-initialiser-alembic.md`

- Arborescence : `requirements.txt` → `pyproject.toml` + `uv.lock`
- Setup : `python -m venv` + `pip install` → `uv venv` + `uv sync`

### 7. Mise à jour des docs — `rename-siteflow-to-tervo-venv.md`

- Solution A : `python -m venv` + `pip install` → `uv venv` + `uv sync`
- Solution B : ajout de `uv run uvicorn` comme alternative
- Check dépendances : `.venv/bin/pip list` → `uv pip list`

### 8. Mise à jour des docs — `guide-de-test.md` (frontend)

- Lancement : `.venv/bin/uvicorn` → `uv run uvicorn`
- Tests : `.venv/bin/python -m pytest` → `uv run pytest`
- Inline test : `.venv/bin/python -c` → `uv run python -c`
- Troubleshooting : `pip install -r requirements.txt` → `uv sync`

### 9. Mise à jour des docs — `02-spec-technique.md` (CI/CD)

- `actions/setup-python@v5` → `astral-sh/setup-uv@v5`
- `pip install -r requirements.txt` → `uv sync --frozen`
- `pytest` → `uv run pytest`

### 10. Guide complet créé

- `notes/backend/extras/guide-uv-usage.md` — workflow complet dev → test → deploy
  avec Docker, CI/CD, aide-mémoire.

---

*Note mise à jour au fur et à mesure de la migration — Juin 2026*
