# Spécification Technique — ResQ

> **Objet :** Complément technique au DAT. Stack, frontend, pipelines.
>
> **Document principal :** `04-architecture.md` (DAT complet : archi, flux, PDF, photos, sécurité, déploiement).
>
> **Document fonctionnel associé :** `01-specs-fonctionnelle.md`

---

## 1. Stack technique

### Backend

| Technologie                | Version   | Rôle                       |
| -------------------------- | --------- | -------------------------- |
| **Python**                 | 3.11+     | Langage principal          |
| **FastAPI**                | 0.111+    | Framework API REST         |
| **SQLAlchemy**             | 2.0+      | ORM                        |
| **Pydantic**               | 2.x       | Validation / sérialisation |
| **Alembic**                | 1.13+     | Migrations DB              |
| **SQLite**                 | (intégré) | Phase 1 dev                |
| **PostgreSQL**             | 16        | Phase 2 prod               |
| **Uvicorn**                | 0.30+     | Serveur ASGI               |
| **python-jose**            | 3.3+      | JWT                        |
| **passlib**                | 1.7+      | Hashage bcrypt             |
| **ReportLab / WeasyPrint** | —         | Génération PDF             |
| **Pillow**                 | 10.x      | Thumbnails photos          |
| **Pytest**                 | 8.x       | Tests                      |

### Frontend

| Technologie              | Version   | Rôle                           |
| ------------------------ | --------- | ------------------------------ |
| **Bun**                  | 1.2+      | Runtime JS (remplace Node.js)  |
| **Vue.js**               | 3.x       | Framework UI (Composition API) |
| **TypeScript**           | 5.x       | Typage                         |
| **Vue Router**           | 4.x       | Routing SPA                    |
| **Pinia**                | 2.x       | Gestion d'état                 |
| **Vue Query (TanStack)** | 5.x       | Cache serveur                  |
| **PrimeVue**             | 4.x       | Composants UI                  |
| **PrimeFlex**            | 3.x       | Styling utilitaire             |
| **VeeValidate + Zod**    | 4.x / 3.x | Formulaires + validation       |
| **date-fns**             | 3.x       | Manipulation dates             |
| **Vite**                 | 6.x       | Bundler / dev server           |

### DevOps

| Technologie        | Rôle                 |
| ------------------ | -------------------- |
| **Docker**         | Conteneurisation     |
| **Docker Compose** | Orchestration locale |
| **GitHub Actions** | CI/CD                |
| **traefik**        | Reverse proxy        |

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

/review/:token              → ReviewPage (public)
```

### Gestion d'état

| Store (Pinia) | Usage                                 |
| ------------- | ------------------------------------- |
| `authStore`   | Connexion, token, utilisateur courant |
| `jobStore`    | Jobs du jour, job courant             |

Cache serveur via **Vue Query** (`@tanstack/vue-query`) : staleTime 10s pour les jobs du jour, 30s pour les clients.

### Composants graphiques

| Composant                      | Bibliothèque                  |
| ------------------------------ | ----------------------------- |
| DataTable, Form, Input, Button | PrimeVue                      |
| Dialog (confirmation)          | PrimeVue                      |
| Toast (notifications)          | PrimeVue Toast                |
| FileUpload (photos)            | PrimeVue                      |
| Rating (étoiles)               | PrimeVue                      |
| Bottom navigation              | Composant custom              |
| PDF preview                    | `<iframe>` ou `vue-pdf-embed` |

### Navigation mobile

Bottom navbar fixe avec 4 onglets : Accueil, Jobs, Clients, Profil.

---

## 3. CI/CD (GitHub Actions)

```yaml
name: CI

on: [push, pull_request]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: hvac_test
          POSTGRES_USER: hvac_user
          POSTGRES_PASSWORD: password
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { python-version: "3.11" }
      - run: uv sync --frozen
      - run: uv run pytest backend/tests/ --cov=app

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
        working-directory: frontend
      - run: npm run test
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
```

---

## 4. Modèle de données

Cf. `05-data-model.md` pour le schéma complet.

### Modèle SQLAlchemy (exemple)

```python
# models/job.py
from sqlalchemy import Column, Integer, String, Text, Date, Time, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base
import enum

class JobStatus(str, enum.Enum):
    PLANIFIE = "planifié"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ANNULE = "annulé"

class Priority(str, enum.Enum):
    BASSE = "basse"
    NORMALE = "normale"
    HAUTE = "haute"
    URGENTE = "urgente"

class Job(Base):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("client.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("user.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(JobStatus), default=JobStatus.PLANIFIE)
    priority = Column(Enum(Priority), default=Priority.NORMALE)
    scheduled_date = Column(Date, nullable=False)
    scheduled_start_time = Column(Time)
    scheduled_end_time = Column(Time)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    observations = Column(Text)

    client = relationship("Client", back_populates="jobs")
    technician = relationship("User", back_populates="jobs")
    checklist_items = relationship("ChecklistItem", back_populates="job", cascade="all, delete-orphan")
    photos = relationship("JobPhoto", back_populates="job", cascade="all, delete-orphan")
    materials = relationship("Material", back_populates="job", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="job", uselist=False, cascade="all, delete-orphan")
```

Rappel des entités : `client`, `user`, `job`, `checklist_item`, `job_photo`, `material`, `review`.

---

## 5. API REST

Base URL : `/api/v1/`

| Groupe    | Endpoints                                                                                        |
| --------- | ------------------------------------------------------------------------------------------------ |
| Auth      | `POST /login`, `POST /refresh`, `GET /me`, `PUT /me`                                             |
| Clients   | `GET/POST /clients`, `GET/PUT/DELETE /clients/{id}`, `GET /clients/{id}/jobs`                    |
| Jobs      | `GET/POST /jobs`, `GET/PUT/DELETE /jobs/{id}`, `PUT /jobs/{id}/start`, `PUT /jobs/{id}/complete` |
| Checklist | `GET /jobs/{id}/checklist`, `PUT /jobs/{id}/checklist/{id}`, `PUT /jobs/{id}/checklist/batch`    |
| Photos    | `POST /jobs/{id}/photos`, `DELETE /jobs/{id}/photos/{id}`                                        |
| Matériaux | `GET/POST /jobs/{id}/materials`, `PUT/DELETE /jobs/{id}/materials/{id}`                          |
| Rapports  | `GET /jobs/{id}/report/download`                                                                 |
| Reviews   | `GET /review/{token}` (public), `POST /review/{token}/submit` (public)                           |
| Dashboard | `GET /dashboard/summary`                                                                         |

Spécification détaillée : `03-api-spec.md`

> **Document mis à jour le 03/06/2026**
> **Version :** 3.0 (Refonte MVP)
> **DAT :** `04-architecture.md`
