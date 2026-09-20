# Tervo — Architecture Technique (DAT)

> Document d'Architecture Technique — vue complète du système.
> **Projet :** Tervo — application de gestion d'interventions CVC.
> **Dernière mise à jour :** 17/09/2026

---

## 1. Objectif

Application Web **mobile-first** pour techniciens CVC :

- Gérer les fiches clients et leur historique d'interventions
- Créer et suivre des jobs de A à Z (planifié → en cours → terminé)
- Remplir des checklists d'inspection pré/intervention
- Capturer des photos avant/après
- Générer des rapports PDF automatiques
- Recueillir les avis clients via lien de partage

**Extensions du périmètre :**

- **Catalogue produits & exposition** — fiches produits, exposition en salle, essai
- **Module financier** *(phase 2)* — devis, factures, bilans
- **Import Excel** — migration d'un historique de 20 ans vers PostgreSQL
- **Déploiement VPS** — exposition publique avec HTTPS

> Les modules marqués *(phase 2)* sont décrits dans ce DAT mais **hors périmètre du Stage 6** (cf. `07-implementation-roadmap.md`).

---

## 2. Stack technique

> **Principe :** le DAT décrit l'architecture ; les **versions exactes** vivent dans `pyproject.toml`, `package.json` et `docker-compose.yml`. Voir `annexes/revue-architecture.md` §16.

| Domaine      | Technologie       | Rôle                              |
| ------------ | ----------------- | --------------------------------- |
| **Backend**  | Python 3.11+      | Langage                           |
|              | FastAPI           | Framework API REST                |
|              | SQLAlchemy 2.x    | ORM (async)                       |
|              | Pydantic          | Validation / sérialisation        |
|              | **Alembic**       | **Migrations DB (dès J1)**        |
|              | PostgreSQL        | Base de données                   |
|              | Uvicorn           | Serveur ASGI                      |
|              | python-jose       | JWT                               |
|              | passlib           | Hashage bcrypt                    |
|              | WeasyPrint        | Génération PDF                    |
|              | Pillow            | Thumbnails photos                 |
|              | pandas / openpyxl | Import de fichiers Excel          |
|              | rapidfuzz         | Détection de doublons (fuzzy)     |
|              | Pytest            | Tests                             |
| **Frontend** | Vue.js 3          | Framework UI (Composition API)    |
|              | TypeScript        | Typage                            |
|              | Vite              | Bundler                           |
|              | Vue Router        | Routing SPA                       |
|              | Pinia             | État client (auth, session)       |
|              | Vue Query         | État serveur (cache, refetch)     |
|              | PrimeVue          | Composants UI                     |
|              | VeeValidate + Zod | Formulaires                       |
| **DevOps**   | Docker + Compose  | Conteneurisation + orchestration  |
|              | **1Panel**        | Reverse proxy (OpenResty) + SSL   |
|              | GitHub Actions    | CI/CD                             |
|              | pg_dump           | Backups PostgreSQL                |

### Frontend — principe de sobriété

La stack frontend est volontairement limitée. **Ne pas ajouter** de bibliothèque sans usage réel : chaque dépendance est une question potentielle en revue d'architecture.

---

## 3. Architecture générale

```
Navigateur mobile (Vue.js SPA)
    │ multipart (photos) + JSON (API)
    ▼
1Panel OpenResty (reverse proxy, Let's Encrypt SSL)
    │
    ├── tervo.com       → frontend (Nginx static, 127.0.0.1:3000)
    └── api.tervo.com   → backend (FastAPI, 127.0.0.1:8000)
    │
    ▼
FastAPI Routers (api/v1/)
    │
    ▼
Services → Repositories → SQLAlchemy → PostgreSQL
    │
    ▼
Exporters → Génération PDF (WeasyPrint)
```

**Aucun service applicatif n'est exposé publiquement.** Le reverse proxy est le seul point d'entrée.

---

## 4. Registre de décisions

| # | Décision | Raison | Alternative écartée |
|---|----------|--------|--------------------|
| D1 | **Docker Compose** plutôt que Swarm/Kubernetes | Périmètre : 3-5 techniciens, 1 comptable, une seule machine | Swarm (complexité injustifiée), K8s (hors échelle) |
| D2 | **1Panel** plutôt que Traefik | Un seul outil pour proxy + SSL + file manager + DB GUI + backups + monitoring | Traefik (proxy seul, nécessite 3 outils en plus) |
| D3 | **Ports en `127.0.0.1`** | Forcer le passage par le reverse proxy HTTPS | `0.0.0.0` (contournement du proxy) |
| D4 | **PostgreSQL embarqué** dans le compose | Un seul `docker compose up`, volume nommé, healthcheck possible | PG externe (pas de `depends_on` inter-fichiers) |
| D5 | **JWT** (access court + refresh) | SPA stateless, API REST | Sessions serveur (moins adapté au mobile) |
| D6 | **Alembic dès J1** | Versionner le schéma, déployer partout | Création manuelle des tables |
| D7 | **Router → Service → Repository** | Séparer HTTP / métier / accès données | Logique dans les routeurs |

### Pourquoi 1Panel plutôt que Traefik

| Critère | Traefik | 1Panel |
|---------|---------|--------|
| Reverse proxy | Labels Docker | UI graphique |
| SSL | Config YAML (ACME) | Let's Encrypt one-click |
| File manager | ✗ (outil séparé requis) | ✓ intégré |
| DB GUI | ✗ | ✓ intégré |
| Backups planifiés | ✗ | ✓ intégré |
| Monitoring conteneurs | ✗ | ✓ intégré |
| Ajout d'un service | 5 labels à écrire | Formulaire en 2 minutes |

**1Panel couvre l'administration complète ; Traefik ne fait que le routage.**

---

## 5. Infrastructure de production

### 5.1 VPS

| Spécification | Valeur |
|---------------|--------|
| Fournisseur | Hetzner CX22 (ou équivalent) |
| vCPU / RAM / Disque | 2 vCPU / 4 Go / 40 Go |
| OS | Ubuntu 24.04 LTS |
| Sécurité | ufw (22/80/443), fail2ban, SSH par clé |

### 5.2 Topologie

```
VPS
  │
  ├── 1Panel (port 7410, écoute loopback — accès via tunnel SSH uniquement)
  │   ├── OpenResty (ports 80/443)
  │   │   ├── tervo.com      → 127.0.0.1:3000 (frontend)
  │   │   └── api.tervo.com  → 127.0.0.1:8000 (backend)
  │   ├── Let's Encrypt SSL
  │   ├── File Manager → uploads, PDF
  │   ├── Database GUI → exploration PostgreSQL
  │   └── Cron Jobs → backups
  │
  ├── Docker Compose (`deploy/docker-compose.yml`)
  │   ├── postgres (aucun port publié, healthcheck pg_isready)
  │   ├── backend  (127.0.0.1:8000, depends_on postgres healthy)
  │   └── frontend (127.0.0.1:3000)
  │
  └── Volumes Docker
      ├── postgres_data
      └── uploads_data
```

**Ports publics : 22, 80, 443 uniquement.** 1Panel (7410) n'est jamais exposé.

### 5.3 Backups

| Fréquence | Action |
|-----------|--------|
| **Quotidien** | `pg_dump` → gzip → Object Storage |
| **Quotidien** | `uploads` → archive versionnée → Object Storage |
| **Mensuel** | Test de **restauration réelle** + vérifications d'intégrité |

> **Backup ≠ synchronisation.** Un backup est un *snapshot versionné*. Un miroir simple propagerait une suppression accidentelle. Voir `annexes/revue-architecture.md` §17-18.

**Un backup non testé n'est pas un backup.** Le test mensuel doit vérifier : schéma, tables, volumétrie, contraintes, puis une requête applicative réelle.

---

## 6. Data Migration — Historique Excel → PostgreSQL

### 6.1 Problèmes identifiés

| Problème | Impact | Stratégie |
|----------|--------|-----------|
| Formats variables selon les années | Colonnes renommées/déplacées | Détection automatique du mapping |
| Données manquantes | Champs vides | Valeurs par défaut + `import_errors` |
| Doublons clients | Orthographes différentes | Normalisation + fuzzy matching |
| Accents / encodage | É è À mal encodés | Normalisation unicode |
| Absence de FK historique | Jobs référencent les clients par nom | Import en 2 passes |
| Données non rattachables | Job sans client identifiable | `import_errors` (jamais ignoré) |

### 6.2 Pipeline d'import

```
Fichier Excel
     │
     ▼
ExcelReader (pandas + openpyxl)
     │
     ▼
FormatDetector (mapping des colonnes)
     │
     ▼
Normalizer (noms, téléphones, adresses)
     │
     ▼
Validators (champs obligatoires, formats)
     │
     ▼
Matcher (rapidfuzz — 3 zones : ≥95 auto / 80-95 humain / <80 nouveau)
     │
     ▼
ImportService
     ├── PASS 1 — CLIENTS  → IDs canoniques
     └── PASS 2 — JOBS     → résolution client_id
     │
     ▼
Transaction par batch (pas une transaction géante)
     │
     ▼
Rapport d'import
```

### 6.3 Idempotence

Un fichier déjà importé ne doit pas l'être deux fois :

```
Fichier Excel → SHA-256 → déjà en base ?
                              ├── oui → skip
                              └── non → import
```

Traçabilité ligne à ligne dans une table de correspondance (fichier source, ligne, entité créée).

### 6.4 Validation avant insertion

```
POST /api/v1/admin/import/preview    → 10 lignes + mapping détecté
POST /api/v1/admin/import/validate   → statistiques (prêts / doublons / erreurs)
POST /api/v1/admin/import/execute    → import réel + rapport
```

**Aucune insertion à l'aveugle.** Voir `05-data-model.md` et `06-workflows.md`.

---

## 7. Migrations DB (Alembic — dès J1)

Alembic est configuré **dès la première migration**, pas ajouté après coup.

```bash
# Générer une migration à partir des modèles
alembic revision --autogenerate -m "add material table"

# Vérifier le fichier généré dans alembic/versions/, puis appliquer
alembic upgrade head
```

`env.py` référence `Base.metadata` pour que `--autogenerate` détecte les changements :

```python
# backend/alembic/env.py
from app.models.base import Base   # importe TOUS les modèles
from app.config import settings

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

---

## 8. Structure du projet

```
Tervo/
├── backend/
│   ├── alembic/                      # Migrations DB
│   └── app/
│       ├── main.py, config.py
│       ├── core/                     # database, security, deps, exceptions
│       ├── models/                   # SQLAlchemy ORM
│       ├── schemas/                  # Pydantic
│       ├── repositories/             # accès DB
│       ├── services/                 # logique métier
│       ├── api/v1/                   # routes REST
│       ├── importers/                # pipeline Excel
│       │   ├── excel_reader.py
│       │   ├── format_detector.py
│       │   ├── normalizer.py
│       │   ├── validators.py
│       │   ├── matcher.py
│       │   └── report.py
│       └── exporters/                # PDF (WeasyPrint)
├── frontend/
│   └── src/
│       ├── main.ts, App.vue, router/
│       ├── stores/, composables/, api/
│       ├── pages/
│       └── components/
├── deploy/
│   ├── docker-compose.yml            # postgres + backend + frontend
│   └── postgres.docker-compose.yml   # PG autonome (option « PG partagé »)
├── docs/DAT/                         # ce document
└── notes/                            # notes pédagogiques
```

---

## 9. Responsabilités des couches

| Couche | Responsabilité |
|--------|----------------|
| **API** (FastAPI routers) | Endpoints REST, validation Pydantic, auth JWT |
| **Services** | Logique métier (statuts, timers, checklists, import, PDF) |
| **Repositories** | Accès DB, requêtes SQLAlchemy |
| **Models** | Mapping ORM, relations |
| **Schemas** | Validation entrée/sortie API |
| **Importers** | Pipeline d'import (lecture → normalisation → matching) |
| **Exporters** | Génération PDF |
| **Frontend** | UI mobile-first, formulaires, photos, navigation |

---

## 10. Sous-systèmes

### 10.1 Génération PDF

```python
# app/exporters/report.py
from weasyprint import HTML
from jinja2 import Template

class ReportExporter:
    def generate_pdf(self, job) -> bytes:
        template = Template(REPORT_HTML_TEMPLATE)
        html = template.render(
            client=job.client, job=job,
            checklist=job.checklist_items,
            photos=job.photos, materials=job.materials,
        )
        return HTML(string=html).write_pdf()
```

Le PDF inclut : client, dates/durée, checklist, photos avant/après, matériaux, observations.

### 10.2 Upload photos

```
Client (Vue.js) ──multipart──► POST /api/v1/jobs/{id}/photos
                                     │
                                     ▼
                          Pillow → thumbnail
                                     │
                                     ▼
                     uploads/photos/{uuid}.jpg
                     uploads/photos/thumb_{uuid}.jpg
```

- Format : JPEG, PNG — taille max contrôlée
- Thumbnail généré côté serveur
- Servi par le reverse proxy

---

## 11. Sécurité

- **Auth** : JWT (access token court, refresh token contrôlé), hash bcrypt
- **Transport** : HTTPS obligatoire (Let's Encrypt)
- **Photos** : upload réservé aux techniciens authentifiés
- **Avis client** : endpoint public protégé par token unique (UUID)
- **CORS** : whitelist explicite
- **XSS** : échappement automatique des templates Vue.js
- **SQL injection** : SQLAlchemy paramétré
- **Réseau** : ports 22/80/443 uniquement ; services applicatifs en loopback ; PostgreSQL sans port publié
- **Admin** : 1Panel accessible uniquement par tunnel SSH
- **Serveur** : ufw + fail2ban + mises à jour de sécurité automatiques
- **Secrets** : `.env` hors dépôt Git, permissions restreintes

> **JWT — point ouvert :** le DAT ne fige pas la stratégie de stockage des tokens (localStorage vs cookie httpOnly). Voir `annexes/revue-architecture.md` §21.

---

## 12. Évolution (hors périmètre actuel)

| Élément | Statut | Raison |
|---------|--------|--------|
| Module financier (devis, factures, bilans) | Phase 2 | Périmètre Stage 6 |
| Gestion de stock | Phase 2 | Dépend du catalogue |
| Fournisseurs / SAV / contrats | Phase 2 | Dépend du stock |
| GED documentaire (OCR des archives) | Phase 2 | Décision tracée dans `annexes/` |
| Registry d'images (GHCR) | Évolution | Simplification actuelle : build sur le VPS |

> **Ne pas présenter ces éléments comme réalisés.** Voir `annexes/revue-architecture.md` §25.

---

> **Sommaire :** `00-sommaire.md`
> **Modèle de données :** `05-data-model.md`
> **Workflows :** `06-workflows.md`
> **API :** `specs/03-api-spec.md`
> **Revue d'architecture :** `annexes/revue-architecture.md`
