# Spécification Technique — MB Chauffage

> **Objet :** Complément technique au DAT. Stack, CI/CD, infrastructure.
>
> **Document principal :** `04-architecture.md` (DAT complet : archi, flux, PDF, photos, sécurité, déploiement).
>
> **Document fonctionnel associé :** `01-specs-fonctionnelle.md`

---

## 1. Stack technique

### Backend

| Technologie | Version | Rôle |
|------------|---------|------|
| **Python** | 3.11+ | Langage principal |
| **FastAPI** | 0.111+ | Framework API REST |
| **SQLAlchemy** | 2.0+ | ORM (async) |
| **Pydantic** | 2.x | Validation / sérialisation |
| **Alembic** | 1.13+ | Migrations DB |
| **PostgreSQL** | 17 | Base de données (pas de SQLite) |
| **Uvicorn** | 0.30+ | Serveur ASGI |
| **python-jose** | 3.3+ | JWT |
| **passlib** | 1.7+ | Hashage bcrypt |
| **WeasyPrint** | — | Génération PDF (rapports, devis, factures) |
| **Pillow** | 10.x | Thumbnails photos |
| **pandas** | 2.x | Import données Excel |
| **openpyxl** | 3.x | Lecture fichiers .xlsx |
| **rapidfuzz** | 3.x | Fuzzy matching (dédoublonnage clients) |
| **Pytest** | 8.x | Tests |

### Frontend

| Technologie | Version | Rôle |
|------------|---------|------|
| **Bun** | 1.2+ | Runtime JS |
| **Vue.js** | 3.x | Framework UI (Composition API) |
| **TypeScript** | 5.x | Typage |
| **Vue Router** | 4.x | Routing SPA |
| **Pinia** | 2.x | Gestion d'état |
| **Vue Query (TanStack)** | 5.x | Cache serveur |
| **PrimeVue** | 4.x | Composants UI |
| **PrimeFlex** | 3.x | Styling utilitaire |
| **VeeValidate + Zod** | 4.x / 3.x | Formulaires + validation |
| **date-fns** | 3.x | Manipulation dates |
| **Chart.js** ou **ApexCharts** | — | Graphiques bilans |
| **Vite** | 6.x | Bundler |

### DevOps

| Technologie | Rôle |
|------------|------|
| **Docker** | Conteneurisation |
| **Docker Compose** | Orchestration production (app principale + services annexes) |
| **1Panel** | Reverse proxy (OpenResty) + SSL (Let's Encrypt) + File Manager + DB GUI + Backups + Monitoring |
| **GitHub Actions** | CI/CD |
| **pg_dump** | Backups PostgreSQL |
| **s3cmd** | Sync backups → Hetzner Object Storage |
| **ufw** | Firewall VPS |
| **fail2ban** | Protection SSH |
| **UptimeRobot** | Monitoring uptime |
| **Paperless-ngx** | GED : OCR, classification auto, recherche full-text, archivage documents |

---

## 2. Frontend (Vue.js)

### Arbre de routes

```
/login                       → LoginPage
/                            → DashboardPage

/clients                     → ClientListPage
/clients/new                 → ClientCreatePage
/clients/:id                 → ClientDetailPage
/clients/:id/edit            → ClientEditPage

/jobs                        → JobListPage
/jobs/new                    → JobCreatePage
/jobs/:id                    → JobDetailPage
/jobs/:id/inspection         → InspectionPage
/jobs/:id/report             → ReportPreviewPage

/devis                       → DevisListPage
/devis/new                   → DevisCreatePage
/devis/:id                   → DevisDetailPage

/factures                    → FactureListPage
/factures/new                → FactureCreatePage
/factures/:id                → FactureDetailPage

/bilans                      → BilanDashboard (comptable/admin)

/admin/import                → AdminImportPage
/admin/users                 → AdminUsersPage (futur)

/review/:token               → ReviewPage (public)
```

### Gestion d'état

| Store (Pinia) | Usage |
|--------------|-------|
| `authStore` | Connexion, token, utilisateur courant, rôle |
| `jobStore` | Jobs du jour, job courant |
| `devisStore` | Devis courant, lignes |
| `factureStore` | Facture courante, lignes |

### Middleware de routes

- Routes `/devis`, `/factures`, `/bilans` → accessibles si `role = admin OU comptable`
- Routes `/admin/*` → accessibles si `role = admin`
- Redirection `/login` si non authentifié

---

## 3. Infrastructure — Docker Compose + 1Panel

> **Décision (révisée) :** Docker Swarm a été écarté après analyse du besoin réel. Aucun des critères qui justifieraient l'orchestration multi-nœud n'est présent à ce stade : pas de contrainte de charge identifiée (3-5 techniciens + 1 comptable), pas de SLA contractuel avec MB Chauffage, pas de date fixée pour un multi-node (modules `pay`/`iq` non scopés), et un budget serré qui pousse à éviter la RAM supplémentaire qu'un manager Swarm consommerait sur un VPS 4 Go déjà chargé (backend, frontend, Postgres, Paperless-ngx + sa propre DB/Redis). La complexité Swarm (réseaux overlay, `docker stack deploy` et ses pièges — pas de `build:` supporté, `env_file` mal géré, secrets à gérer différemment) n'est donc pas justifiée : c'est de la scalabilité anticipée pour un besoin qui n'existe pas. Migration possible vers Swarm plus tard, si un signal concret (charge mesurée, SLA, multi-node daté) apparaît.

### 3.1 docker-compose.prod.yml (production)

```yaml
version: "3.8"

services:
  backend:
    image: mbchauffage-backend:latest
    environment:
      - DATABASE_URL=postgresql://mbchauffage:${DB_PASSWORD}@postgres:5432/mbchauffage_db
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - uploads_data:/app/uploads
    ports:
      - "8000:8000"
    networks:
      - mb_network
    restart: unless-stopped
    depends_on:
      - postgres

  frontend:
    image: mbchauffage-frontend:latest
    ports:
      - "3000:80"
    networks:
      - mb_network
    restart: unless-stopped

  postgres:
    image: postgres:17
    environment:
      - POSTGRES_DB=mbchauffage_db
      - POSTGRES_USER=mbchauffage
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - mb_network
    restart: unless-stopped

volumes:
  postgres_data:
  uploads_data:

networks:
  mb_network:
    driver: bridge
```

> **1Panel n'a jamais eu besoin de gérer l'orchestrateur** (rôle inchangé, avec ou sans Swarm) : il route en reverse proxy vers `localhost:PORT`, peu importe ce qui tourne derrière. 1Panel gère : reverse proxy, SSL Let's Encrypt, File Manager, DB GUI, Backups Cron, Monitoring — tout ce qui **entoure** les conteneurs.

### 3.2 Logique de déploiement

```bash
# 1. Build
DOCKER_BUILDKIT=1 docker build -t mbchauffage-backend:latest -f backend/Dockerfile backend/
DOCKER_BUILDKIT=1 docker build -t mbchauffage-frontend:latest -f frontend/Dockerfile frontend/

# 2. Déploiement (recreate des services modifiés uniquement)
docker compose -f docker-compose.prod.yml up -d

# → Coupure de quelques secondes le temps du recreate du container backend/frontend
# → Acceptable : usage interne (3-5 techniciens), pas de trafic public continu,
#   pas de SLA contractuel nécessitant du zero-downtime
```

### 3.3 Configuration 1Panel

```
1Panel → Websites → Create Website → Reverse Proxy

Site 1: mbchauffage.com
  - Proxy Address: http://localhost:3000
  - HTTPS → Let's Encrypt → Enable (one-click)

Site 2: api.mbchauffage.com
  - Proxy Address: http://localhost:8000
  - HTTPS → Let's Encrypt → Enable (one-click)

1Panel → Cron Jobs → créer backup quotidien
1Panel → File Manager → accès aux uploads / PDF
1Panel → Database → PostgreSQL console

Site 3: docs.mbchauffage.com
  - Proxy Address: http://localhost:8000
  - HTTPS → Let's Encrypt → Enable (one-click)
```

### 3.4 Paperless-ngx — Docker Compose annexe

> Paperless-ngx tourne en Docker Compose séparé dans `/opt/paperless/`, indépendamment du stack applicatif principal. Service annexe avec ses propres dépendances (PostgreSQL 15, Redis 7).

```yaml
# /opt/paperless/docker-compose.yml
version: "3.8"

services:
  broker:
    image: redis:7
    container_name: paperless-broker
    volumes:
      - /opt/paperless/redis:/data
    restart: unless-stopped

  db:
    image: postgres:17
    container_name: paperless-db
    environment:
      POSTGRES_DB: paperless
      POSTGRES_USER: paperless
      POSTGRES_PASSWORD: ${PAPERLESS_DB_PASSWORD}
    volumes:
      - /opt/paperless/db:/var/lib/postgresql/data
    restart: unless-stopped

  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    container_name: paperless-ngx
    depends_on:
      - db
      - broker
    ports:
      - "8000:8000"
    volumes:
      - /opt/paperless/data:/usr/src/paperless/data
      - /opt/paperless/media:/usr/src/paperless/media
      - /opt/paperless/export:/usr/src/paperless/export
      - /opt/paperless/consume:/usr/src/paperless/consume
    environment:
      PAPERLESS_DBUSER: paperless
      PAPERLESS_DBPASS: ${PAPERLESS_DB_PASSWORD}
      PAPERLESS_DBHOST: db
      PAPERLESS_DBPORT: "5432"
      PAPERLESS_DBNAME: paperless
      PAPERLESS_REDIS: redis://broker:6379
      PAPERLESS_SECRET_KEY: ${PAPERLESS_SECRET_KEY}
      PAPERLESS_URL: https://docs.mbchauffage.com
      PAPERLESS_TIME_ZONE: Europe/Paris
      PAPERLESS_OCR_LANGUAGE: fra
      PAPERLESS_CONSUMER_POLLING: "60"
    restart: unless-stopped
```

**Lancement :**

```bash
cd /opt/paperless
docker compose up -d
```

**Site 1Panel :** `docs.mbchauffage.com → http://localhost:8000`

---

## 4. CI/CD (GitHub Actions)

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
          POSTGRES_DB: mbchauffage_test
          POSTGRES_USER: mbchauffage
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { python-version: "3.11" }
      - run: uv sync --frozen
      - run: uv run pytest backend/tests/ --cov=app

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build images
        run: |
          docker build -t mbchauffage-backend:latest -f backend/Dockerfile backend/
          docker build -t mbchauffage-frontend:latest -f frontend/Dockerfile frontend/
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/mbchauffage
            git pull
            docker build -t mbchauffage-backend:latest -f backend/Dockerfile backend/
            docker build -t mbchauffage-frontend:latest -f frontend/Dockerfile frontend/
            docker compose -f docker-compose.prod.yml up -d
            # Recreate des services modifiés — quelques secondes de coupure, acceptable (usage interne)
```

---

## 5. Sécurité

| Couche | Mesure |
|--------|--------|
| **Réseau** | ufw : ports 22, 80, 443, 7410 uniquement |
| **SSH** | fail2ban, clé SSH uniquement (pas de mot de passe) |
| **SSL** | Let's Encrypt via 1Panel (one-click), renouvellement automatique |
| **API** | CORS whitelist (mbchauffage.com), rate limiting |
| **Auth** | JWT, bcrypt, refresh tokens |
| **DB** | Mot de passe dans `.env` (pas en clair dans le yaml) |
| **Backups** | Chiffrement GPG avant envoi Object Storage (P2) |
| **Mises à jour** | unattended-upgrades pour les patchs de sécurité Ubuntu |
| **Secrets** | `.env` hors dépôt Git (`.gitignore`), permissions fichier restreintes (`chmod 600`) sur le VPS |

---

## 6. Backups

### Script backup quotidien (`/usr/local/bin/backup.sh`)

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/var/backups/mbchauffage
BUCKET=s3://mbchauffage-backups/daily/$(date +%Y/%m)

mkdir -p $BACKUP_DIR

# ── App DB ──────────────────────────────────────────────
docker exec mbchauffage_postgres pg_dump -U mbchauffage mbchauffage_db | gzip > $BACKUP_DIR/mbchauffage_${DATE}.sql.gz

# ── Paperless DB ─────────────────────────────────────────
docker exec paperless-db pg_dump -U paperless paperless | gzip > $BACKUP_DIR/paperless-db_${DATE}.sql.gz

# ── Paperless media ──────────────────────────────────────
tar czf $BACKUP_DIR/paperless-media_${DATE}.tar.gz -C /opt/paperless media consume

# ── Sync Object Storage ─────────────────────────────────
s3cmd put $BACKUP_DIR/mbchauffage_${DATE}.sql.gz $BUCKET/
s3cmd put $BACKUP_DIR/paperless-db_${DATE}.sql.gz $BUCKET/
s3cmd put $BACKUP_DIR/paperless-media_${DATE}.tar.gz $BUCKET/

# Rotation : garder 30 jours
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Test de restauration mensuel (`/usr/local/bin/restore-test.sh`)

```bash
#!/bin/bash
LATEST_BACKUP=$(ls -t /var/backups/mbchauffage/*.sql.gz | head -1)

# Créer une DB temporaire
docker exec mbchauffage_postgres psql -U mbchauffage -c "DROP DATABASE IF EXISTS mbchauffage_restore_test;"
docker exec mbchauffage_postgres psql -U mbchauffage -c "CREATE DATABASE mbchauffage_restore_test;"

# Restaurer
gunzip -c $LATEST_BACKUP | docker exec -i mbchauffage_postgres psql -U mbchauffage mbchauffage_restore_test

# Vérifier
TABLES=$(docker exec mbchauffage_postgres psql -U mbchauffage -d mbchauffage_restore_test -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "Tables: $TABLES"

# Nettoyer
docker exec mbchauffage_postgres psql -U mbchauffage -c "DROP DATABASE mbchauffage_restore_test;"

echo "Restore test OK"
```
---

> **Document mis à jour le 12/07/2026**
> **Version :** 1.0 (DAT MB Chauffage)
> **Projet source :** `Tervo/docs/DAT/specs/02-spec-technique.md`
> **DAT principal :** `04-architecture.md`
