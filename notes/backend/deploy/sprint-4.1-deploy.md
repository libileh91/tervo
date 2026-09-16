# Déploiement Sprint 4.1 — Frontend mobile

> **Date :** 13/07/2026
> **Sprint :** 4.1 (INT-38 à INT-42)
> **Type :** Local (Docker Compose)

---

## Résumé du sprint

5 tâches livrées (18/18 pts) :
- **INT-38** — Responsive mobile (`100dvh`, safe-area, `font-size: 16px` iOS, `fluid` buttons)
- **INT-39** — États Loading/Empty/Error (toutes les pages, boutons "Réessayer")
- **INT-40** — Animations transitions pages (slide-fade 250ms)
- **INT-41** — Création rapide client depuis formulaire job (recherche + création inline)
- **INT-42** — Navigation contextuelle (cards Dashboard cliquables, routes nommées)

## Bugs corrigés pendant le déploiement

### Bug 1 : `PUT /jobs/{id}/start` → 500 Internal Server Error

**Cause :** `datetime.now(timezone.utc)` crée un datetime "aware" (avec fuseau horaire). Le stockage dans une colonne PostgreSQL `TIMESTAMP` (sans timezone) échoue car PostgreSQL rejette l'insertion de datetime aware dans une colonne naive.

**Fix :** Remplacer par `datetime.utcnow()` (datetime naive) dans `backend/app/services/job.py` :
```python
# Avant
job.started_at = datetime.now(timezone.utc)
job.completed_at = datetime.now(timezone.utc)

# Après
job.started_at = datetime.utcnow()
job.completed_at = datetime.utcnow()
```

**Fichiers :** `backend/app/services/job.py`

### Bug 2 : Bouton "Nouveau job" Dashboard inactif

**Cause :** Le `<Button>` dans l'empty state du Dashboard n'avait pas de `@click`.

**Fix :**
- DashboardPage → `@click="goToNewJob"` → `router.push({ name: 'Jobs', query: { newJob: '1' } })`
- JobsPage → watch sur `route.query.newJob === "1"` → ouvre le dialogue + nettoie le query param

### Bug 3 : Seed enrichi (noms somali + entreprises)

8 clients au lieu de 3, 7 jobs au lieu de 3.

---

## Procédure de déploiement

### 1. Build frontend (dist/)
```bash
cd frontend
npm install
npm run build
```

### 2. Build images Docker
```bash
cd ..
docker build -t tervo-backend:latest -f backend/Dockerfile backend/
docker build -t tervo-frontend:latest -f frontend/Dockerfile frontend/
```

### 3. Déployer
```bash
docker compose -f deploy/docker-compose.yml up -d
```

### 4. Migrations + Seed
```bash
docker exec tervo-backend-1 alembic upgrade head
docker exec tervo-backend-1 python -m app.seed
```

### 5. Vérification API
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"tech1","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Dashboard
curl -s http://localhost:8000/api/v1/dashboard/summary \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Clients
curl -s "http://localhost:8000/api/v1/clients?page_size=10" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Start job (test du fix 500)
curl -s -X PUT http://localhost:8000/api/v1/jobs/5/start \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### 6. Vérification Frontend
```bash
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:3000/
# Devrait retourner HTTP 200
```

---

## Configuration actuelle

| Service | Port | Accès |
|---------|------|-------|
| Backend API | `8000` | `http://192.168.10.192:8000/api/v1/` |
| Frontend | `3000` | `http://192.168.10.192:3000/` |
| PostgreSQL | `5432` | Container `postgres`, réseau `postgres_postgres_network` |
| Reverse Proxy | 1Panel | OpenResty, gère SSL + routage |

### Base de données
- **Hôte :** `postgres` (nom du container)
- **Port :** `5432`
- **Database :** `tervo_db`
- **User :** `lob`
- **Réseau :** `postgres_postgres_network`

### Comptes de test
| Username | Password | Rôle |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `tech1` | `password123` | Technicien |

---

## Erreurs rencontrées et corrections

| Erreur | Cause | Correction |
|--------|-------|-----------|
| `PUT /jobs/{id}/start` 500 | `datetime.now(timezone.utc)` dans colonne DateTime naive | `datetime.utcnow()` |
| `keepPreviousData` TS error | TanStack Query v5 a supprimé `keepPreviousData` | Remplacer par `placeholderData: keepPreviousData` ou supprimer |
| `refetch` type error | `@click="refetch"` passe un PointerEvent à `refetch(RefetchOptions)` | Faux positif TS — fonctionne à l'exécution |
