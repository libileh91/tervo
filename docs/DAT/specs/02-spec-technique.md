# Tervo — Spécification Technique

> **Objet :** Complément technique au DAT. Stack détaillée, frontend, infrastructure, CI/CD.
>
> **Document principal :** `04-architecture.md` (archi, décisions, flux, sécurité).
>
> **Document fonctionnel :** `specs/01-specs-fonctionnelle.md`

---

## 1. Stack technique

> Les versions exactes vivent dans `pyproject.toml`, `package.json` et `docker-compose.yml` — pas dans le DAT.

### Backend

| Technologie | Rôle |
|-------------|------|
| Python 3.11+ | Langage |
| FastAPI | Framework API REST |
| SQLAlchemy 2.x | ORM (async) |
| Pydantic | Validation / sérialisation |
| Alembic | Migrations DB |
| PostgreSQL | Base de données |
| Uvicorn | Serveur ASGI |
| python-jose | JWT |
| passlib | Hashage bcrypt |
| WeasyPrint | Génération PDF |
| Pillow | Thumbnails photos |
| pandas + openpyxl | Lecture Excel |
| rapidfuzz | Fuzzy matching |
| Pytest | Tests |

### Frontend

| Technologie | Rôle |
|-------------|------|
| Vue.js 3 | Framework UI (Composition API) |
| TypeScript | Typage |
| Vite | Bundler / dev server |
| Vue Router | Routing SPA |
| Pinia | État client |
| Vue Query (TanStack) | État serveur (cache, refetch) |
| PrimeVue | Composants UI |
| VeeValidate + Zod | Formulaires + validation |
| date-fns | Manipulation des dates |

### DevOps

| Technologie | Rôle |
|-------------|------|
| Docker + Compose | Conteneurisation + orchestration |
| 1Panel | Reverse proxy (OpenResty), SSL, admin |
| GitHub Actions | CI/CD |
| pg_dump | Backups PostgreSQL |

---

## 2. Frontend (Vue.js)

### 2.1 Arbre de routes

```
/login                       → LoginPage              (public, sans nav)
/                            → DashboardPage

/clients                     → ClientListPage
/clients/:id                 → ClientDetailPage

/jobs                        → JobListPage
/jobs/:id                    → JobDetailPage
/jobs/:id/inspection         → InspectionPage
/jobs/:id/report             → ReportPreviewPage

/produits                    → ProduitsPage           (catalogue)
/produits/:id                → ProduitDetailPage
/showroom                    → ShowroomPage           (exposition en salle)

/profile                     → ProfilePage

/review/:token               → ReviewPage             (public, sans auth)
```

**Routes *phase 2* (non implémentées) :** `/devis`, `/factures`, `/bilans`,
`/admin/import`, `/admin/users`.

### 2.2 Gestion d'état

| Store (Pinia) | Usage |
|---------------|-------|
| `authStore` | Connexion, token, utilisateur courant, rôle |

**Cache serveur** via Vue Query : `staleTime` court pour les données du jour, plus long pour les référentiels.

> **Distinction à connaître :** Pinia = état **client** (session, préférences). Vue Query = état **serveur** (données de l'API, cache, invalidation). Ne pas mélanger les deux.

### 2.3 Composants

| Composant | Bibliothèque |
|-----------|--------------|
| DataTable, Form, Input, Button, Dialog | PrimeVue |
| Toast (notifications) | PrimeVue |
| FileUpload (photos) | PrimeVue |
| Rating (étoiles) | PrimeVue |
| Skeleton (chargement) | PrimeVue |
| Bottom navigation | Composant custom |

### 2.4 Navigation mobile

Bottom navbar fixe, 4 onglets : Accueil, Interventions, Clients, Profil
(+ Catalogue selon la version).

### 2.5 États d'écran

Toute page qui charge des données implémente **3 états** :

| État | Affichage |
|------|-----------|
| **Loading** | Skeleton |
| **Empty** | Message + icône + action |
| **Error** | Message clair + bouton « Réessayer » (`refetch()`) |

---

## 3. Infrastructure technique

### 3.1 `deploy/docker-compose.yml`

> Les tags d'image (`postgres:17.4`) sont **illustratifs** : la source de vérité reste le fichier `deploy/docker-compose.yml` du dépôt.

```yaml
name: tervo

services:
  postgres:
    image: postgres:17.4
    environment:
      POSTGRES_DB: ${TERVO_DB_NAME:-tervo_db}
      POSTGRES_USER: ${TERVO_DB_USER:-lob}
      POSTGRES_PASSWORD: ${TERVO_DB_PASSWORD:-password}
    volumes:
      - postgres_data:/var/lib/postgresql/data/pgdata
    networks: [tervo_network]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${TERVO_DB_USER:-lob} -d ${TERVO_DB_NAME:-tervo_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    # Aucun port publié

  backend:
    build: { context: ../backend, dockerfile: Dockerfile }
    ports: ["127.0.0.1:${BACKEND_PORT:-8000}:8000"]
    volumes: [uploads_data:/app/uploads]
    environment:
      - DATABASE_URL=postgresql://${TERVO_DB_USER:-lob}:${TERVO_DB_PASSWORD:-password}@postgres:5432/${TERVO_DB_NAME:-tervo_db}
      - SECRET_KEY=${SECRET_KEY}
    networks: [tervo_network, 1panel-network]
    depends_on:
      postgres: { condition: service_healthy }

  frontend:
    build: { context: ../frontend, dockerfile: Dockerfile }
    ports: ["127.0.0.1:${FRONTEND_PORT:-3000}:80"]
    networks: [tervo_network, 1panel-network]

volumes:
  postgres_data:
  uploads_data:

networks:
  tervo_network: { driver: bridge }
  1panel-network: { external: true, name: 1panel-network }
```

**Trois points non négociables :**

1. `127.0.0.1:PORT` — jamais `0.0.0.0`
2. `postgres` sans `ports:` — accessible seulement dans le réseau Docker
3. `condition: service_healthy` — le backend attend une base **réellement** prête

### 3.2 Logique de déploiement

```bash
# Build + déploiement (sur le VPS)
git pull
docker compose -f deploy/docker-compose.yml up -d --build

# Migrations + seed
docker exec tervo-backend-1 alembic upgrade head
docker exec tervo-backend-1 python -m app.seed
```

### 3.3 Configuration 1Panel

```
Websites → Create Website → Reverse Proxy

Site 1 : tervo.com
  Proxy Address : http://127.0.0.1:3000
  HTTPS → Let's Encrypt → Enable

Site 2 : api.tervo.com
  Proxy Address : http://127.0.0.1:8000
  HTTPS → Let's Encrypt → Enable
```

---

## 4. CI/CD (GitHub Actions)

### 4.1 Principe : un seul build

```
push main
   │
   ▼
GitHub Actions
   ├── tests (pytest + postgres service)
   └── SSH vers le VPS
          └── git pull → docker compose up -d --build
```

> ⚠️ **Ne pas builder dans GitHub Actions puis à nouveau sur le VPS.** Le premier build serait inutilisé. Voir `annexes/revue-architecture.md` §5.

### 4.2 Workflow

```yaml
name: CI/CD

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_DB: tervo_test
          POSTGRES_USER: tervo
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { python-version: "3.11" }
      - run: uv sync --frozen
      - run: uv run pytest backend/tests/ --cov=app

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/tervo
            git pull
            docker compose -f deploy/docker-compose.yml up -d --build
```

### 4.3 Évolution possible (non implémentée)

```
GitHub Actions → build → push GHCR → VPS → docker compose pull → up -d
```

À présenter comme **évolution**, pas comme acquis.

---

## 5. Backups

### 5.1 Script quotidien

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/var/backups/tervo
BUCKET=s3://tervo-backups/daily/$(date +%Y/%m)

mkdir -p "$BACKUP_DIR"

# Base de données
docker exec tervo-postgres-1 pg_dump -U tervo tervo_db | gzip > "$BACKUP_DIR/tervo_${DATE}.sql.gz"

# Fichiers (versionnés, pas miroir)
tar czf "$BACKUP_DIR/uploads_${DATE}.tar.gz" -C /var/lib/docker/volumes/tervo_uploads_data _data

# Envoi distant
s3cmd put "$BACKUP_DIR/tervo_${DATE}.sql.gz" "$BUCKET/"
s3cmd put "$BACKUP_DIR/uploads_${DATE}.tar.gz" "$BUCKET/"

# Rétention : 30 jours
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
```

### 5.2 Test de restauration mensuel

Le test doit vérifier **plus que le nombre de tables** :

```
restore dans une base temporaire
   ↓
vérifier le schéma
   ↓
vérifier les tables attendues
   ↓
vérifier les volumétries (row counts)
   ↓
vérifier quelques contraintes
   ↓
exécuter une requête applicative réelle
   ↓
OK
```

> Un dump qui restaure 15 tables peut contenir des données corrompues ou incomplètes.

---

## 6. Conventions

| Sujet | Convention |
|-------|-----------|
| Préfixe API | `/api/v1/` |
| Nommage DB | `snake_case` (tables et colonnes) |
| Nommage Python | `snake_case` (fonctions), `PascalCase` (classes) |
| Structure backend | Router → Service → Repository |
| Erreurs API | Codes HTTP standards + message explicite |
| Secrets | `.env`, jamais commité |

---

> **Document principal :** `04-architecture.md`
> **API :** `specs/03-api-spec.md`
> **Revue d'architecture :** `annexes/revue-architecture.md`
