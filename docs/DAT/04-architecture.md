# ResQ — Architecture Technique (DAT)

> Document d'Architecture Technique — vue complète du système.

---

## 1. Objectif

Application Web **mobile-first** pour techniciens CVC :

- Gérer les fiches clients et leur historique d'interventions
- Créer et suivre des jobs de A à Z (planifié → en cours → terminé)
- Remplir des checklists d'inspection pré/post-intervention
- Capturer des photos avant/après
- Générer des rapports PDF automatiques
- Recueillir les avis clients via lien de partage

---

## 2. Stack technique

| Domaine      | Technologie       | Version   | Rôle                       |
| ------------ | ----------------- | --------- | -------------------------- |
| **Backend**  | Python            | 3.11+     | Langage                    |
|              | FastAPI           | 0.111+    | Framework API REST         |
|              | SQLAlchemy        | 2.0+      | ORM                        |
|              | Pydantic          | 2.x       | Validation / sérialisation |
|              | **Alembic**       | **1.13+** | **Migrations DB (dès J1)** |
|              | SQLite            | intégré   | Dev                        |
|              | PostgreSQL        | 16        | Production                 |
|              | Uvicorn           | 0.30+     | Serveur ASGI               |
|              | python-jose       | 3.3+      | JWT                        |
|              | passlib           | 1.7+      | Hashage bcrypt             |
|              | WeasyPrint        | —         | Génération PDF             |
|              | Pillow            | 10.x      | Thumbnails photos          |
|              | Pytest            | 8.x       | Tests                      |
| **Frontend** | Vue.js            | 3.x       | Framework UI               |
|              | **Bun**           | **1.2+**  | **Runtime JS (remplace Node.js)** |
|              | TypeScript        | 5.x       | Typage                     |
|              | Vue Router        | 4.x       | Routing                    |
|              | Pinia             | 2.x       | Gestion d'état             |
|              | Vue Query         | 5.x       | Cache serveur              |
|              | PrimeVue          | 4.x       | Composants UI              |
|              | PrimeFlex         | 3.x       | Styling                    |
|              | VeeValidate + Zod | 4.x / 3.x | Formulaires                |
|              | date-fns          | 3.x       | Dates                      |
|              | Vite              | 6.x       | Bundler                    |
| **DevOps**   | Docker + Compose  | —         | Conteneurisation           |
|              | GitHub Actions    | —         | CI/CD                      |
|              | Traefik           | —         | Reverse proxy + TLS        |

---

## 3. Architecture générale

```
Navigateur mobile (Vue.js SPA)
    │ multipart (photos) + JSON (API)
    ▼
FastAPI Routers (api/v1/)
    │
    ▼
Services → Repositories → SQLAlchemy → DB
    │
    ▼
Exporters → Génération PDF (WeasyPrint)
```

---

## 4. Migrations DB (Alembic — day 1)

Alembic est setup **dès la première migration** du projet, pas ajouté après coup. Cela permet de versionner le schéma de données et de déployer sur n'importe quelle base (SQLite → PostgreSQL).

### Workflow quotidien

```bash
# 1. Créer / modifier un modèle SQLAlchemy
# 2. Générer la migration automatiquement
alembic revision --autogenerate -m "add material table"

# 3. Vérifier le fichier généré dans alembic/versions/
# 4. Appliquer
alembic upgrade head
```

### Initialisation (Sprint 1.1)

```bash
# Réalisé une seule fois au début du projet (tâche INT-00)
alembic init backend/alembic

# Configurer backend/alembic/env.py :
#   - DATABASE_URL (depuis settings)
#   - target_metadata = Base.metadata (import des modèles)
```

Le fichier `env.py` référence `Base.metadata` pour que `--autogenerate` détecte les changements :

```python
# backend/alembic/env.py
from app.models.base import Base   # ← importe TOUS les modèles (via __init__)
from app.config import settings

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

### À chaque nouveau modèle

```bash
# 1. Créer le fichier models/ma_table.py (extends Base)
# 2. L'importer dans models/__init__.py
# 3. alembic revision --autogenerate -m "add ma_table"
# 4. alembic upgrade head
```

---

## 5. Structure du projet

```text
hvac/
├── docs/DAT/
│   ├── 04-architecture.md            ← ce document (DAT)
│   ├── 05-data-model.md
│   ├── 06-workflows.md
│   ├── 07-implementation-roadmap.md
│   └── specs/
│       ├── 01-specs-fonctionnelle.md
│       ├── 02-spec-technique.md
│       └── 03-api-spec.md
├── backend/
│   ├── alembic/                      # Migrations DB
│   │   ├── env.py                    # target_metadata = Base.metadata
│   │   ├── versions/                 # Fichiers de migration générés
│   │   └── script.py.mako
│   ├── alembic.ini
│   └── app/
│       ├── main.py, config.py
│       ├── core/           # database, security, deps, exceptions
│       ├── models/         # client, user, job, checklist_item...
│       ├── schemas/        # Pydantic
│       ├── repositories/   # accès DB
│       ├── services/       # logique métier
│       ├── api/v1/         # routes REST
│       └── exporters/      # PDF
├── frontend/
│   └── src/
│       ├── main.ts, App.vue, router/
│       ├── stores/, composables/, api/
│       ├── pages/
│       └── components/
├── docker-compose.yml
└── README.md
```

---

## 6. Responsabilités des couches

| Couche                    | Responsabilité                                    |
| ------------------------- | ------------------------------------------------- |
| **API** (FastAPI routers) | Endpoints REST, validation Pydantic, auth JWT     |
| **Services**              | Logique métier (statuts, timers, checklists, PDF) |
| **Repositories**          | Accès DB, requêtes SQLAlchemy                     |
| **Models**                | Mapping ORM, relations                            |
| **Schemas**               | Validation entrée/sortie API                      |
| **Frontend** (Vue.js)     | UI mobile-first, formulaires, photos, navigation  |

---

## 7. Flux de données

### Démarrage d'un job

```
Bouton ▶ Démarrer (Vue.js)
    → PUT /api/v1/jobs/{id}/start
    → started_at = now(), status = 'en_cours'
    → Timer lancé → checklist pré affichée
```

### Terminaison + rapport

```
Bouton Terminer (Vue.js)
    → PUT /api/v1/jobs/{id}/complete
    → Validation : photos + checklist OK
    → completed_at = now(), duration calculée
    → PDF généré (WeasyPrint)
    → share_token créé pour l'avis client
    → 200 OK (download_url + share_url)
```

---

## 8. Sous-système : génération PDF

```python
# services/report_service.py
from weasyprint import HTML
from jinja2 import Template

class ReportService:
    def generate_pdf(self, job: Job) -> bytes:
        template = Template(REPORT_HTML_TEMPLATE)
        html = template.render(
            client=job.client, job=job,
            checklist=job.checklist_items,
            photos=job.photos, materials=job.materials,
        )
        return HTML(string=html).write_pdf()
```

Le PDF inclut : client, dates/durée, checklist, photos avant/après, matériaux, observations.

---

## 9. Sous-système : upload photos

```
Client (Vue.js)
    │ multipart/form-data
    ▼
POST /api/v1/jobs/{id}/photos
    │
    ▼
FastAPI → Pillow thumbnail → stockage disque
    │
    ▼
/backend/uploads/photos/{uuid}.jpg
/backend/uploads/photos/thumb_{uuid}.jpg
```

- Format : JPEG, PNG, max 10 Mo
- Thumbnail : 300×300, généré côté serveur
- Servi via Traefik (file server middleware)

---

## 10. Sécurité

- **Auth** : JWT (access token 30 min, refresh token 7 jours), hash bcrypt
- **Photos** : upload réservé aux techniciens authentifiés
- **Avis client** : endpoint public protégé par token unique (UUID), sans auth
- **CORS** : whitelist explicite
- **XSS** : échappement automatique des templates Vue.js
- **SQL injection** : SQLAlchemy paramétré

---

## 11. Principes d'architecture

- **Mobile-first** : interface pensée pour le smartphone, bottom nav
- **API REST versionnée** : `/api/v1/`
- **Auth JWT** : rôles `technician` / `admin`
- **Migrations DB dès J1** : Alembic + `--autogenerate` + `upgrade`
- **Validation bi-couche** : Pydantic serveur + Zod client
- **Cache** : Vue Query, invalidation après mutations
- **Photos** : upload multipart, thumbnails, stockage fichier ou S3
- **PDF** : généré côté serveur (WeasyPrint)
- **Avis client** : endpoint public sans auth, token unique

---

> **Endpoints API :** `specs/03-api-spec.md`
> **Modèle de données :** `05-data-model.md`
> **Spécification technique :** `specs/02-spec-technique.md`
