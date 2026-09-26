# INT-49 — docker-compose.yml (backend + frontend, 1Panel proxy)

> **Objectif :** Créer le docker-compose de production orchestrant le backend (FastAPI) et le frontend (Nginx static), connecté au PostgreSQL existant.
> **Date :** 25/06/2026

---

## Architecture cible

```
                      ┌───────────────────┐
                      │   1Panel Admin    │
                      │  http://IP:7410   │ ← UI de gestion
                      │  (login: lb1P)    │
                      └────────┬──────────┘
                               │ configure
                               ▼
                      ┌───────────────────┐
                      │ 1Panel Reverse    │
                      │ Proxy (nginx)     │ ← proxy géré par 1Panel
                      │  :80 (HTTP)       │
                      │  :443 (HTTPS)     │
                      └──────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │ Backend  │   │ Frontend │   │PostgreSQL│ ← existant
       │ :8000    │   │ :80      │   │ :5432    │
       └──────────┘   └──────────┘   └──────────┘
             │                              │
             └───────── postgres_network ───┘
                          (externe)
```

**Points clés :**
- **1Panel Admin** (port `7410`) : interface web pour tout configurer — accessible uniquement en local
- **1Panel Reverse Proxy** (ports `80` HTTP / `443` HTTPS) : expose les services Tervo publiquement
- **Pas de Traefik** — 1Panel fait office de reverse proxy via son UI
- Le backend expose son port `8000` **en interne** (dans docker-compose) ; 1Panel le relie à son proxy
- Le frontend Nginx expose le port `80` **en interne** ; idem, 1Panel le relie
- Le réseau `postgres_postgres_network` est **externe** (créé par le docker-compose PostgreSQL existant)
- Le backend accède à PostgreSQL via le hostname `postgres:5432`

#### TODO 1Panel: config Reverse 
Les ports `8000` (backend) et `80` (frontend Nginx) sont les ports **internes** des containers docker-compose. C'est via l'UI 1Panel (port 7410) que tu diras : *"traite-moi les requêtes qui arrivent sur le domaine X et envoie-les sur le backend:8000"*.

Concrètement, dans 1Panel UI → onglet **"Websites"** → **"Create reverse proxy"**, tu créeras une règle du type :

| Depuis (entrée 1Panel) | Vers (container) |
|------------------------|------------------|
| `http://IP_SERVER:8000` ou domaine → `/api/*` | `backend:8000` |
| `http://IP_SERVER:80` ou domaine → `/*` | `frontend:80` |

C'est ce qu'on verra en détail dans **INT-DPL** (Config 1Panel).

---

## Les fichiers créés

### `deploy/docker-compose.yml`

```yaml
services:
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - uploads_data:/backend/uploads
    environment:
      - DATABASE_URL=postgresql://${TERVO_DB_USER:-tervo_user}:${TERVO_DB_PASSWORD:-changeme}@postgres:5432/${TERVO_DB_NAME:-tervo_db}
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
    networks:
      - postgres_network
    healthcheck:
      test: ["CMD", "python", "-c",
        "import urllib.request;
         urllib.request.urlopen(
           'http://localhost:8000/openapi.json'
         )"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    ports:
      - "${FRONTEND_PORT:-80}:80"
    networks:
      - postgres_network
    restart: unless-stopped

volumes:
  uploads_data:

networks:
  postgres_network:
    external: true
    name: postgres_postgres_network
```

### `frontend/Dockerfile`

```dockerfile
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html
# SPA fallback : toutes les routes → index.html
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Concepts clés

| Concept | Explication |
|---------|-------------|
| `context: ../backend` | Le contexte de build est relatif au dossier du docker-compose (`deploy/`). On remonte d'un niveau pour pointer vers `backend/`. |
| `external: true` + `name:` | On utilise un réseau Docker créé **en dehors** de ce compose (celui du PostgreSQL). `name:` permet de spécifier le nom exact. |
| `$${VAR:-default}` | Variable d'environnement avec valeur par défaut. `$$` échappe le `$` pour le shell du docker-compose (vs shell host). |
| `healthcheck` | Test périodique via Python (déjà présent dans l'image). Vérifie que `/openapi.json` répond. |
| SPA fallback | `try_files $uri $uri/ /index.html` : pour une SPA Vue, toutes les routes doivent renvoyer `index.html` (le JS router s'occupe du reste). |

---

## Commandes

```bash
# Build + lancement
docker compose -f deploy/docker-compose.yml up -d

# Voir les logs
docker compose -f deploy/docker-compose.yml logs -f

# Arrêt
docker compose -f deploy/docker-compose.yml down

# Voir la config résolue (variables substituées)
docker compose -f deploy/docker-compose.yml config

# Rebuild sans cache
docker compose -f deploy/docker-compose.yml build --no-cache

# Taille des images
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep tervo
```

---

## Rétrospective INT-48 corrigée

Pendant INT-49, j'ai identifié et corrigé un problème de INT-48 :

| Problème | Correction |
|----------|-----------|
| `asyncpg` manquant dans `pyproject.toml` | Ajouté : `"asyncpg>=0.29.0"` + `uv lock` |
| Le `database.py` utilise `asyncpg` pour PostgreSQL | Sans cette dépendance, le backend plantait au démarrage en prod |

---

## Résultats

| Image | Taille | Statut |
|-------|--------|--------|
| `tervo-backend:test` | 260 MB | ✅ Build OK |
| `tervo-frontend:test` | 63.9 MB | ✅ Build OK |
| docker-compose config | — | ✅ Syntaxe valide |

---

## Recap

✅ INT-49 terminé

**Fichiers créés / modifiés :**

| Fichier | Action | Description |
|---------|--------|-------------|
| `deploy/docker-compose.yml` | **Nouveau** | Backend (port 8000) + Frontend Nginx (port 80), réseau PostgreSQL externe |
| `frontend/Dockerfile` | **Nouveau** | Nginx alpine, SPA fallback, 63.9 MB |
| `deploy/postgres.docker-compose.yml` | Copié depuis notes/ | Référence locale du PostgreSQL |

**Rétrospective corrigée :**
- `backend/pyproject.toml` : ajout `asyncpg>=0.29.0` → `uv lock` ✅
- Rebuild backend image : **260 MB** (toujours < 300 MB)
- Docker-compose : syntaxe validée ✅

**Fichiers mis à jour :**
- `docs/stages/stage3/sprint-3.1/tasks.md` → critères INT-49 cochés ✅
- `docs/stages/stage3/sprint-3.1/test-cases.json` → chemins corrigés `deploy/`, healthcheck `/openapi.json`

---

**Feu-vert pour INT-50 — Volume persistant uploads + connexion PostgreSQL ?