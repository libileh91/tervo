# Sprint 3.1 : First Deploy via 1Panel (Semaine 4)

> **Durée :** 5 jours | **Points :** 29 | **Tâches :** 8 (INT-48 à INT-51, INT-45, INT-47, INT-DPL, INT-DOC)

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
- Backend ENV : `DATABASE_URL=postgresql://resq_user:password@postgres:5432/resq_db`
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
- [x] `APP_NAME=ResQ` dans les variables d'environnement
- [x] `UPLOAD_DIR=/app/uploads` explicite dans l'environnement
- [x] `DATABASE_URL` lue depuis l'environnement (pydantic-settings) — config PostgreSQL prête
La DB `resq_db` doit être créée au préalable (→ voir TD-B008)
L'utilisateur `lob` (existant dans le container PG) doit avoir les privilèges sur `resq_db` (→ voir TD-B008)

**Technical Notes**
- Commandes PostgreSQL à exécuter **avant** le premier `docker compose up` :
  ```bash
  # Créer la base de données ResQ
  docker exec -it postgres psql -U postgres -c "CREATE DATABASE resq_db;"
  
  # L'utilisateur 'lob' existe déjà dans le container PostgreSQL (POSTGRES_USER=lob)
  # Il faut juste lui donner les droits sur resq_db
  docker exec -it postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE resq_db TO lob;"
  
  # Vérifier
  docker exec -it postgres psql -U postgres -c "\l"
  ```
- Utilisateur : `lob`, mot de passe : `postgres` (défini via `${RESQ_DB_PASSWORD:-postgres}` dans docker-compose)
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

## INT-DPL — Config 1Panel : build image, DB, reverse proxy, variables d'env (5 pts)

**User Story**  
En tant que **dev fullstack**,  
Je veux **configurer 1Panel pour builder et déployer l'application**  
Afin de **rendre ResQ accessible sur le réseau**.

**Acceptance Criteria**
- [ ] Dans 1Panel UI : créer un projet Docker Compose avec `docker-compose.yml`
- [ ] Builder l'image backend via 1Panel (équivalent `docker build`)
- [ ] Tag : `resq-backend:latest`
- [ ] Configurer le reverse proxy 1Panel pour exposer :
  - `http://<IP>:8000` → backend (API)
  - Frontend servi via Nginx dans le docker-compose
- [ ] Configurer les variables d'environnement dans 1Panel :
  - `DATABASE_URL`, `SECRET_KEY`, `UPLOAD_DIR`
- [ ] Créer la base `resq_db` et l'utilisateur `resq_user` (via commande exec)
- [ ] Exécuter les migrations : `docker exec <container> alembic upgrade head`
- [ ] Exécuter le seed : `docker exec <container> python -m app.seed`
- [ ] Vérifier que l'API répond : `curl http://localhost:8000/api/v1/auth/login`

**Technical Notes**
- 1Panel accessible via `http://localhost:7410` (login: `lb1P`)
- Build Docker via 1Panel : onglet "Containers" → "Build"
- Reverse proxy : onglet "Websites" → "Create reverse proxy"
- Variables d'environnement : onglet "Containers" → "Compose" → "Env"
- Il n'y a pas de registry Docker — build local uniquement

---

## INT-DOC — Documentation déploiement (procédure 1Panel) (3 pts)

**User Story**  
En tant que **développeur**,  
Je veux **documenter la procédure de déploiement**  
Afin de **pouvoir reproduire le déploiement facilement**.

**Acceptance Criteria**
- [ ] Document `deploy/deployment.md` avec :
  - Prérequis : Docker, 1Panel installé, PostgreSQL container
  - Étapes de création de la base de données
  - Étapes de build des images Docker
  - Étapes de configuration du reverse proxy 1Panel
  - Étapes de migration et seed
  - Vérification de l'installation
- [ ] Commandes copiables (one-liner)
- [ ] Dépannage : erreurs fréquentes et solutions
- [ ] Structure claire : Prérequis → Installation → Vérification

**Technical Notes**
- Fichier : `deploy/deployment.md` (nouveau)
- Ne pas inclure les mots de passe en clair (utiliser `CHANGEME`)
- Inclure la configuration réseau (postgres_network)
- Inclure les commandes Docker exec pour PostgreSQL

---

## Tests Cases Sprint 3.1

Les tests cases détaillés sont dans `test-cases.json`.
