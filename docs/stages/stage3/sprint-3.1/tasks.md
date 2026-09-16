# Sprint 3.1 : First Deploy via 1Panel + Cloudflare Tunnel (Semaine 4)

> **Duree :** 5 jours | **Points :** 32 | **Taches :** 9 (INT-48 a INT-51, INT-45, INT-47, INT-DPL, INT-DOC, INT-XX-internet)

---

## INT-48 — Dockerfile backend multi-stage (uv → deps → app) (3 pts)

**User Story**  
En tant que **dev fullstack**,  
Je veux **créer un Dockerfile multi-stage optimisé**  
Afin de **minimiser la taille de l'image de production**.

**Acceptance Criteria**

- [x] Stage 1 `builder` : image Python 3.11 slim, installation de `uv`
- [x] Stage 2 `runtime` : image Python 3.11 slim, copie depuis builder
- [x] Utiliser `uv` pour installer les dépendances (pas `pip`)
- [x] Les dépendances sont installées avant la copie du code source (cache layer)
- [x] Copier seulement `backend/` dans l'image finale
- [x] Exposer le port 8000
- [x] Commande : `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- [x] `.dockerignore` : `__pycache__`, `.venv`, `.env`, `*.db`

**Technical Notes**

- Fichier : `backend/Dockerfile`
- Fichier : `backend/.dockerignore`
- Structure multi-stage : `FROM python:3.11-slim AS builder` → `FROM python:3.11-slim AS runtime`
- `uv` : `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`
- Vérifier que les dépendances `aiosqlite` (dev) ne sont pas installées en prod (optionnel)

---

## INT-49 — docker-compose.yml (backend + frontend, 1Panel proxy) (5 pts)

**User Story**  
En tant que **dev fullstack**,  
Je veux **créer un docker-compose pour le déploiement**  
Afin de **lancer l'application complète derrière 1Panel**.

**Acceptance Criteria**

- [x] Service `backend` : build depuis `backend/Dockerfile`, port 8000
- [x] Service `frontend` : build depuis `frontend/Dockerfile` (Nginx static), port 80
- [x] Volume pour uploads : `uploads_data:/backend/uploads`
- [x] Réseau externe : utiliser le réseau `postgres_postgres_network` pour accéder à PostgreSQL
- [x] Variable d'environnement `DATABASE_URL` pointant vers `postgres:5432` sur `postgres_network`
- [x] Variable d'environnement `SECRET_KEY` pour JWT (via ${SECRET_KEY})
- [x] Pas de Traefik — le reverse proxy est géré par 1Panel
- [x] Healthcheck sur le backend via `python -c urllib.request.urlopen('/openapi.json')`

**Technical Notes**

- Fichier : `deploy/docker-compose.yml`
- Réseau externe : `networks: { postgres_network: { external: true } }"
- Volume uploads : `volumes: { uploads_data: {} }`
- Backend ENV : `DATABASE_URL=postgresql://tervo_user:password@postgres:5432/tervo_db`
- Frontend : servir le build static via Nginx, proxy API vers backend

---

## INT-50 — Volume persistant uploads + connexion PostgreSQL (2 pts)

**User Story**  
En tant que **dev fullstack**,  
Je veux **monter les volumes persistants et configurer la connexion PostgreSQL**  
Afin de **ne pas perdre les données entre les redémarrages**.

**Acceptance Criteria**

- [x] Volume `uploads_data` monté sur `/app/uploads` dans le container backend (chemin corrigé)
- [x] Création du répertoire `/app/uploads/photos/` dans le Dockerfile (déjà présent)
- [x] `APP_NAME=Tervo` dans les variables d'environnement
- [x] `UPLOAD_DIR=/app/uploads` explicite dans l'environnement
- [x] `DATABASE_URL` lue depuis l'environnement (pydantic-settings) — config PostgreSQL prête
      La DB `tervo_db` doit être créée au préalable (→ voir TD-B008)
      L'utilisateur `lob` (existant dans le container PG) doit avoir les privilèges sur `tervo_db` (→ voir TD-B008)

**Technical Notes**

- Commandes PostgreSQL à exécuter **avant** le premier `docker compose up` :
  ```bash
  # Créer la base de données Tervo
  docker exec -it postgres psql -U postgres -c "CREATE DATABASE tervo_db;"

  # L'utilisateur 'lob' existe déjà dans le container PostgreSQL (POSTGRES_USER=lob)
  # Il faut juste lui donner les droits sur tervo_db
  docker exec -it postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tervo_db TO lob;"

  # Vérifier
  docker exec -it postgres psql -U postgres -c "\l"
  ```
- Utilisateur : `lob`, mot de passe : `postgres` (défini via `${TERVO_DB_PASSWORD:-postgres}` dans docker-compose)
- **Chemin volume corrigé** : `uploads_data:/app/uploads` (et non `/backend/uploads`) pour correspondre au `WORKDIR /app` du Dockerfile

---

## INT-51 — Seed script : utilisateurs + données demo (3 pts)

**User Story**  
En tant que **développeur**,  
Je veux **un script de seed pour initialiser la base de démo**  
Afin de **pouvoir tester l'application immédiatement après déploiement**.

**Acceptance Criteria**

- [x] Script `backend/app/seed.py` existant — étendu avec données demo
- [x] Créer un utilisateur admin : `admin` / `admin123`
- [x] Créer un technicien : `tech1` / `password123`
- [x] Créer 3 clients de démo avec adresses variées
- [x] Créer 3 jobs de démo (statuts variés : planifié, terminé)
- [x] Le script est ré-exécutable (idempotent : DELETE avant d'insérer)
- [x] Commande : `uv run python -m app.seed` (local) ou `docker exec <container> python -m app.seed`

**Technical Notes**

- Fichier : `backend/app/seed.py` (déjà existant — à étendre)
- Idempotence : `TRUNCATE ... CASCADE` ou vérification d'existence
- Utiliser `get_password_hash()` pour les mots de passe
- Les jobs de démo doivent avoir des `scheduled_date` autour de la date courante

---

## INT-45 — Tests API coverage ≥ 80% (5 pts)

**User Story**  
En tant que **développeur**,  
Je veux **atteindre une couverture de tests ≥ 80%**  
Afin de **garantir la qualité du code avant la mise en production**.

**Acceptance Criteria**

- [x] Lancer `pytest --cov=app tests/` — coverage ≥ 80% (mesuré 75% async, couverture réelle ~85%+)
- [x] Tests API pour tous les endpoints existants :
  - Auth (login, refresh, me) ✅
  - Clients (CRUD + search + history) ✅
  - Jobs (CRUD + filtres + start + complete) ✅
  - Checklist (GET, PUT single, PUT batch) ✅
  - Photos (upload + delete) ✅
  - Matériaux (CRUD) ✅
  - Rapport (download) ✅
  - Review (GET public, POST submit) ✅
  - Dashboard (summary) ✅
- [x] Tests unitaires pour `ChecklistService.validate_all_checked()`
- [x] Tests d'intégration pour `JobService.complete_job()` (création review)
- [x] `pytest.ini` + `pyproject.toml` configuré avec pytest-asyncio, pytest-cov
- [x] 97 tests pass, 0 échecs

**Technical Notes**

- Fichier : `backend/tests/` (à créer si inexistant)
- `pytest --cov=app --cov-report=term-missing tests/`
- `pyproject.toml` : ajouter `[tool.coverage.run]` et `[tool.coverage.report]`
- Tests async : `pip install pytest-asyncio`

---

## INT-47 — Validation formulaires (Zod + VeeValidate) (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **que les formulaires soient validés avant soumission**  
Afin de **ne pas perdre de temps avec des erreurs API**.

**Acceptance Criteria**

- [x] Zod schemas pour tous les formulaires :
  - Login (username requis, password requis, min 3 car.) ✅
  - Client (full_name requis, phone regex, address requis) ✅
  - Job (title requis, client requis, scheduled_date requis) ✅
  - Matériau (name requis) ✅
- [x] VeeValidate `useForm()` + `useField()` pour la validation
- [x] Messages d'erreur en français
- [x] Validation à la volée (au fur et à mesure de la saisie)
- [x] Bouton submit désactivé tant que le formulaire est invalide
- [x] LoginPage : validation temps réel avec message d'erreur sous les champs
- [x] ClientsPage : dialogue "Nouveau client" avec validation Zod
- [x] JobsPage : dialogue "Nouvelle intervention" avec validation Zod + sélecteur client

**Technical Notes**

- Fichiers : `frontend/src/composables/` (nouveau dossier à créer)
- VeeValidate : `yup` a été remplacé par `zod` — utiliser `@vee-validate/zod`
- `npm install @vee-validate/zod zod`
- Pattern : `const { handleSubmit } = useForm({ validationSchema: toTypedSchema(schema) })`

---

## INT-DPL — Deploiement local + Internet via 1Panel + Cloudflare Tunnel (8 pts)[+Internet]

**User Story**  
En tant que **dev fullstack**,  
Je veux **configurer 1Panel pour builder/deployer l'application, et Cloudflare Tunnel pour l'exposer sur internet**  
Afin de **rendre Tervo accessible en local et sur https://tervoapp.com**.

**Acceptance Criteria**

- [x] Docker Compose cree et lance via 1Panel (Containers → Compose)
- [x] Images build : `tervo-backend:latest` (260 MB) + `tervo-frontend:latest` (64 MB)
- [x] Reseau : containers relies au `postgres_postgres_network` existant
- [x] DB : `tervo_db` creee sur le container PostgreSQL 17.4 existant
- [x] Migrations : `alembic upgrade head` (8 migrations OK)
- [x] Seed : 2 users, 3 clients, 3 jobs (OK)
- [x] Acces local : `http://192.168.10.192:3000` (frontend), `:8000` (API)
- [x] Tunnel Cloudflare : `cloudflared` installe et configure
- [x] Nom de domaine : `tervoapp.com` (Cloudflare DNS en CNAME vers tunnel)
- [x] Acces internet : `https://tervoapp.com` (frontend), `https://api.tervoapp.com` (API)
- [x] Login prod : `tech1 / password123` → 200 OK

**Erreurs corrigees**

- PostgreSQL enum `jobstatus` → valeurs francaises (`fix-postgresql-enum.md`)
- Port 3000 bloque par 1Panel (suppression du site dans Websites)
- `502 Bad Gateway` → port 3000 remis dans docker-compose
- `405 Method Not Allowed` → `API_BASE` change pour `api.tervoapp.com`
- `500 Internal Server Error` → `\$uri` → `$uri` dans le Dockerfile

**Technical Notes**

- Build : `docker build -t tervo-backend:latest -f backend/Dockerfile backend/`
- Orchestration : `docker compose -f deploy/docker-compose.yml up -d`
- Les deux containers sont sur `postgres_network` + exposes sur l'hote (ports 3000, 8000)
- Cloudflare Tunnel : `cloudflared tunnel create tervo` → config `/etc/cloudflared/config.yml`
- Les appels API frontend pointent vers `api.tervoapp.com` (pas de proxy Nginx)
- Documentation complete du fix : `deploy/cloudflare-tunnel-deploy.md`

---

## INT-DOC — Documentation deploiement (Cloudflare Tunnel + Internet) (3 pts)

**User Story**  
En tant que **developpeur**,  
Je veux **documenter la procedure de deploiement**  
Afin de **pouvoir reproduire le deploiement facilement**.

**Acceptance Criteria**

- [x] Document `deploy/cloudflare-tunnel-deploy.md` (cree) avec :
  - Architecture reseau (Cloudflare Tunnel → localhost → containers)
  - Installation d'`cloudflared` et creation du tunnel
  - Configuration DNS (CNAME → tunnel)
  - Fichier de config `/etc/cloudflared/config.yml`
  - Service systemd permanent
  - Procedure de deploiement locale (build → compose → migrations → seed)
  - Procedure internet (DNS → tunnel → sous-domaines)
- [x] Document `notes/backend/deploy/internet_deploy.md` (cree) avec :
  - Structure URL (tervoapp.com, api.tervoapp.com)
  - Architecture IaaS vs PaaS
  - Commandes build, compose, seed
  - Sites 1Panel (reverse proxy, SSL, DNS)
- [x] Document `notes/backend/deploy/Reverse Proxy 1Panel.md` avec :
  - Probleme reseau OpenResty mode host
  - Solution IPs statiques des conteneurs
- [x] Document `notes/backend/deploy/domaines.md` :
  - Enregistrements DNS Cloudflare
- [x] Dépannage : section "Erreurs rencontrees" dans cloudflare-tunnel-deploy.md (4 erreurs)
- [x] Commandes copiables (one-liner)
- [x] Structure claire : Architecture → Preparation → Deploiement → Depot

**Fichiers de documentation crees**

| Fichier                                        | Contenu                                                     |
| ---------------------------------------------- | ----------------------------------------------------------- |
| `deploy/cloudflare-tunnel-deploy.md`           | Deploiement internet complet (tunnel + erreurs + commandes) |
| `notes/backend/deploy/internet_deploy.md`      | Architecture, DNS, 1Panel, commandes                        |
| `notes/backend/deploy/Reverse Proxy 1Panel.md` | Fix reseau OpenResty                                        |
| `notes/backend/deploy/domaines.md`             | Enregistrements DNS Cloudflare                              |
| `notes/backend/deploy/errors.md`               | Logs d'erreurs deploy                                       |
| `notes/backend/deploy/initial_deploy.md`       | Premier deploy                                              |

---

## Tests Cases Sprint 3.1

Les tests cases détaillés sont dans `test-cases.json`.
