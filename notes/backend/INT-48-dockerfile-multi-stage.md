# INT-48 — Dockerfile backend multi-stage (uv → deps → app)

> **Objectif :** Créer un Dockerfile multi-stage optimisé pour le backend ResQ, utilisant `uv` au lieu de `pip`.
> **Date :** 25/06/2026

---

## Pourquoi multi-stage ?

Le multi-stage permet de séparer **l'environnement de build** (avec compilateurs, outils) de **l'environnement runtime** (minimal). Résultat : image finale plus petite et plus sécurisée.

```
Stage builder  → python:3.11-slim + uv + dépendances + source
     ↓ copie .venv + app code uniquement
Stage runtime  → python:3.11-slim (250 MB au lieu de ~1GB)
```

---

## Le Dockerfile

```dockerfile
# ── Stage 1: Builder ──────────────────────────────────────
FROM python:3.11-slim AS builder

# Install uv (pas de pull ghcr.io — pip suffit)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Layer 1: dépendances seules (cache Docker : inchangé = pas rebuild)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-group dev --frozen --no-install-project

# Layer 2: code source
COPY . .
RUN uv sync --no-group dev --frozen

# ── Stage 2: Runtime ──────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copie UNIQUEMENT .venv + code depuis builder
COPY --from=builder /app/.venv          /app/.venv
COPY --from=builder /app/app            /app/app
COPY --from=builder /app/alembic        /app/alembic
COPY --from=builder /app/alembic.ini    /app/
COPY --from=builder /app/main.py        /app/

ENV PATH="/app/.venv/bin:$PATH"
RUN mkdir -p /app/uploads/photos

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Points clés

| Concept | Explication |
|---------|------------|
| `COPY pyproject.toml uv.lock ./` avant le code source | **Layer caching** : si les dépendances n'ont pas changé, Docker réutilise le layer. Le build passe de 1min → < 1s. |
| `--no-group dev` | N'installe **pas** les dépendances de dev (`pytest`, `httpx`) dans l'image de production. |
| `--frozen` | Utilise `uv.lock` tel quel — pas de résolution, juste installation. Plus rapide et reproductible. |
| `--no-install-project` | 1er `uv sync` : installe **uniquement** les dépendances, pas le projet. 2nd `uv sync` : installe le projet dans le .venv existant. |
| `COPY --from=builder` | Copie entre stages. On ne copie que `.venv/` (dépendances) et `app/`, `alembic/` (code). |

---

## Le .dockerignore

```dockerignore
__pycache__/  .venv/  .pytest_cache/  .coverage  *.db
.env
.git/  .gitignore
.agents/  docs/  notes/
frontend/
uploads/
Dockerfile  .dockerignore
```

Évite d'envoyer au contexte Docker des fichiers inutiles (docs, frontend, git, etc.) → build plus rapide.

---

## Commandes de build et test

```bash
# Build
cd backend/
docker build -t resq-backend:test -f Dockerfile .

# Voir la taille
docker images resq-backend:test

# Lancer
docker run -d --name resq-test -p 8000:8000 resq-backend:test

# Vérifier les logs
docker logs resq-test

# Tester l'API
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
# → 200 = OK

# Tester le routing
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/auth/login
# → 405 = OK (POST attendu, pas GET, mais le routing fonctionne)

# Nettoyer
docker stop resq-test && docker rm resq-test
```

---

## Résultat

| Métrique | Valeur | Seuil accepté |
|----------|--------|--------------|
| Taille image | **250 MB** | < 300 MB ✅ |
| Build time (1er) | ~30s | — |
| Build time (cache, 2ème) | ~1s | — |
| Uvicorn répond | ✅ 200 sur /docs | — |
| Routing API | ✅ 405 (endpoint trouvé) | — |

---

## À noter pour la suite

- **asyncpg** manquant : `pyproject.toml` a `aiosqlite` mais pas `asyncpg`. Pour PostgreSQL, il faudra ajouter `asyncpg` aux dépendances (INT-49 ou INT-50).
- L'image est taguée `resq-backend:latest` pour le déploiement final via 1Panel.

---

> **Prochaine tâche :** INT-49 — docker-compose.yml backend + frontend


## Deploy Structure

Voici la structure finale :

```
resQ/
├── backend/
│   ├── Dockerfile          ← INT-48 ✅ (reste ici, lié au build context)
│   ├── .dockerignore       ← INT-48 ✅ (reste ici)
│   └── ...
├── deploy/                 ← NOUVEAU
│   ├── docker-compose.yml  ← INT-49 (à créer)
│   ├── deployment.md       ← INT-DOC (à créer)
│   └── postgres.docker-compose.yml  ← ref copiée depuis notes/
├── docs/
│   └── stages/stage3/sprint-3.1/tasks.md  ← chemins mis à jour ✅
└── notes/
```

**Ce qui a changé :**
- `deploy/` créé à la racine ✓
- `postgres.docker-compose.yml` copié dans `deploy/` (référence pratique)
- Tasks.md mis à jour : chemins `docker-compose.yml` → `deploy/docker-compose.yml` et `docs/deployment.md` → `deploy/deployment.md`
- `backend/Dockerfile` et `.dockerignore` inchangés (bonne pratique : proches du code)

**Prêt pour INT-49 ?** Le `deploy/docker-compose.yml` sera créé dedans.