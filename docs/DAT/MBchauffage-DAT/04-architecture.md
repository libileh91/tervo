# MB Chauffage — Architecture Technique (DAT)

> Document d'Architecture Technique — vue complète du système.
> Projet client réel : **MB Chauffage**, entreprise CVC avec 20+ ans de données historiques (Excel).

---

## 1. Objectif

Application Web **mobile-first** pour techniciens CVC d'une entreprise établie :

- Gérer les fiches clients et leur historique d'interventions (20 ans de données)
- Créer et suivre des jobs de A à Z (planifié → en cours → terminé)
- Remplir des checklists d'inspection pré/post-intervention
- Capturer des photos avant/après
- Générer des rapports PDF automatiques
- Recueillir les avis clients via lien de partage
- **Générer des devis et factures** (module financier)
- **Consulter les bilans mensuels/annuels** (tableau de bord financier)
- **Importer l'historique Excel existant** (data migration)

---

## 2. Stack technique

| Domaine           | Technologie                | Version    | Rôle                                                                                  |
| ----------------- | -------------------------- | ---------- | ------------------------------------------------------------------------------------- |
| **Backend**       | Python                     | 3.11+      | Langage                                                                               |
|                   | FastAPI                    | 0.111+     | Framework API REST                                                                    |
|                   | SQLAlchemy                 | 2.0+       | ORM (async)                                                                           |
|                   | Pydantic                   | 2.x        | Validation / sérialisation                                                            |
|                   | **Alembic**                | **1.13+**  | **Migrations DB (dès J1)**                                                            |
|                   | PostgreSQL                 | 17         | Base de données (unique, pas de SQLite)                                               |
|                   | Uvicorn                    | 0.30+      | Serveur ASGI                                                                          |
|                   | python-jose                | 3.3+       | JWT                                                                                   |
|                   | passlib                    | 1.7+       | Hashage bcrypt                                                                        |
|                   | WeasyPrint                 | —          | Génération PDF (rapports, devis, factures)                                            |
|                   | Pillow                     | 10.x       | Thumbnails photos                                                                     |
|                   | **pandas**                 | **2.x**    | **Import données Excel**                                                              |
|                   | **openpyxl**               | **3.x**    | **Lecture fichiers .xlsx**                                                            |
|                   | Pytest                     | 8.x        | Tests                                                                                 |
| **Frontend**      | Vue.js                     | 3.x        | Framework UI                                                                          |
|                   | **Bun**                    | **1.2+**   | **Runtime JS**                                                                        |
|                   | TypeScript                 | 5.x        | Typage                                                                                |
|                   | Vue Router                 | 4.x        | Routing                                                                               |
|                   | Pinia                      | 2.x        | Gestion d'état                                                                        |
|                   | Vue Query                  | 5.x        | Cache serveur                                                                         |
|                   | PrimeVue                   | 4.x        | Composants UI                                                                         |
|                   | PrimeFlex                  | 3.x        | Styling                                                                               |
|                   | VeeValidate + Zod          | 4.x / 3.x  | Formulaires                                                                           |
|                   | date-fns                   | 3.x        | Dates                                                                                 |
|                   | Vite                       | 6.x        | Bundler                                                                               |
| **DevOps**        | Docker + Compose           | —          | Conteneurisation (dev **et** production, service unique)                             |
|                   | **1Panel**                 | **2.x**    | **Reverse proxy (OpenResty) + SSL (Let's Encrypt) + File Manager + DB GUI + Backups** |
|                   | GitHub Actions             | —          | CI/CD                                                                                 |
|                   | **pg_dump**                | —          | **Backups quotidiens**                                                                |
|                   | **Hetzner Object Storage** | —          | **Stockage backups + photos**                                                         |
| **Documentation** | **Paperless-ngx**          | **latest** | **GED : OCR, classification auto, archivage devis/factures/rapports**                 |

---

## 3. Architecture générale

```
Navigateur mobile (Vue.js SPA)
    │ multipart (photos) + JSON (API)
    ▼
1Panel OpenResty (reverse proxy, Let's Encrypt SSL)
    │
    ├── mbchauffage.com → frontend (Nginx, port 3000) [Docker Compose]
    ├── api.mbchauffage.com → backend (FastAPI, port 8000) [Docker Compose]
    ├── docs.mbchauffage.com → Paperless-ngx (port 8000) [Docker Compose]
    ├── [futur] pay.mbchauffage.com → module paiement [Docker Compose]
    └── [futur] iq.mbchauffage.com → analytics [Docker Compose]
    │
    ▼
Docker Compose — stack applicatif          Docker Compose — Paperless (annexe)
    ├── mb-backend (port 8000)             ├── paperless-ngx (port 8000)
    ├── mb-frontend (port 3000)            ├── paperless-db (postgres:17)
    ├── mb-postgres (port 5432)            └── paperless-broker (redis:7)
    ├── [futur] mb-pay
    └── [futur] mb-iq
    │
    ▼
FastAPI Routers (api/v1/)       Services → Repositories → SQLAlchemy → PostgreSQL
    │
    ▼
Exporters → Génération PDF (WeasyPrint) — rapports, devis, factures

Exporters → Auto-archivage → Paperless API → documents OCRisés
```

---

## 4. Pourquoi 1Panel et pas Cloudflare Tunnel (ni Traefik) ?

### 4.1 Tunnel vs VPS direct

| Critère             | Cloudflare Tunnel (Tervo)                  | 1Panel (MB Chauffage)                           |
| ------------------- | ------------------------------------------ | ----------------------------------------------- |
| **Type de serveur** | Serveur domestique (mini-s1), IP dynamique | VPS avec IP publique fixe, ports 80/443 directs |
| **SSL**             | Automatique via Cloudflare Edge            | Let's Encrypt one-click dans l'UI 1Panel        |
| **Routage**         | Sous-domaines → `config.yml` tunnel + DNS  | UI Websites 1Panel (formulaire, pas de YAML)    |
| **Exposition**      | Connexion sortante uniquement (sécurisé)   | Ports 80/443 ouverts (ufw + fail2ban)           |
| **Adapté pour**     | Serveur domestique sans IP fixe            | VPS pro avec IP publique                        |

Sur un VPS, les ports 80/443 sont directement accessibles → pas besoin de tunnel.

### 4.2 Pourquoi 1Panel plutôt que Traefik

| Critère                | Traefik                                                   | 1Panel                                                     |
| ---------------------- | --------------------------------------------------------- | ---------------------------------------------------------- |
| **Reverse proxy**      | Labels Docker dans `docker-compose.yml`                   | UI graphique : Websites → Create → Reverse Proxy           |
| **SSL**                | Let's Encrypt (YAML config)                               | Let's Encrypt (one-click UI)                               |
| **Multi-domaine**      | Labels `traefik.http.routers.*` par service               | Un site par sous-domaine dans l'UI                         |
| **Apprentissage**      | Syntaxe YAML Traefik + middleware + certificate resolvers | Interface graphique qu'on maîtrise déjà                    |
| **File manager**       | ❌ Besoin d'un outil séparé                               | ✅ Navigateur de fichiers intégré (accès aux uploads, PDF) |
| **DB GUI**             | ❌ Besoin de phpPgAdmin/Adminer en plus                   | ✅ Console PostgreSQL intégrée                             |
| **Backups**            | ❌ Besoin de scripts cron manuels                         | ✅ Planificateur de backups intégré                        |
| **Monitoring**         | ❌ Besoin de Portainer/Dockge en plus                     | ✅ CPU, RAM, logs des conteneurs en direct                 |
| **Cron jobs**          | ❌ Besoin de crontab + scripts                            | ✅ Interface de planification intégrée                     |
| **Ajout d'un service** | Ajouter 5 labels Traefik dans le yaml, redéployer         | UI 1Panel : formulaire en 2 minutes                        |

**1Panel est un couteau suisse.** Traefik ne fait que le reverse proxy + SSL. Pour un projet client réel, 1Panel couvre tous les besoins opérationnels dans un seul outil :

1. **Reverse proxy** (OpenResty/Nginx) pour tous les sous-domaines
2. **SSL** Let's Encrypt en un clic (pas de YAML, pas de labels Docker)
3. **File manager** : le gérant peut télécharger un rapport PDF directement depuis le navigateur
4. **DB GUI** : vérifier une facture dans PostgreSQL sans ligne de commande
5. **Backups** : planifier les dumps PostgreSQL sans écrire de cron à la main
6. **Monitoring** : voir l'état des conteneurs, la RAM, les logs en un coup d'oeil

**Note :** 1Panel a été testé ponctuellement sur Tervo mais retiré depuis (remplacé par Cloudflare Tunnel, plus adapté à un serveur domestique sans IP fixe). Ce n'est donc pas un outil déjà maîtrisé en production — une phase de prise en main est à prévoir sur MB Chauffage, mais l'interface graphique reste nettement moins complexe à apprendre que la syntaxe Traefik (labels, middleware, certificate resolvers).

---

## 5. Infrastructure de production

### 5.1 VPS

| Spécification   | Valeur           |
| --------------- | ---------------- |
| **Fournisseur** | Hetzner CX22     |
| **vCPU**        | 2                |
| **RAM**         | 4 Go             |
| **Stockage**    | 40 Go NVMe       |
| **OS**          | Ubuntu 24.04 LTS |
| **Coût estimé** | ~8 €/mois        |

### 5.2 Topologie — Docker Compose + 1Panel

```
VPS (Hetzner CX22)
  │
  ├── 1Panel (port 7410) — UI d'administration
  │   ├── OpenResty (ports 80/443, mode bridge)
  │   │   ├── mbchauffage.com → localhost:3000 (frontend)
  │   │   ├── api.mbchauffage.com → localhost:8000 (backend)
  │   │   ├── docs.mbchauffage.com → localhost:8000 (Paperless-ngx)
  │   │   ├── [futur] pay.mbchauffage.com → localhost:5000 (pay)
  │   │   └── [futur] iq.mbchauffage.com → localhost:5100 (iq)
  │   ├── Let's Encrypt SSL (one-click par site)
  │   ├── File Manager → accès aux uploads, PDFs
  │   ├── Database GUI → exploration PostgreSQL
  │   └── Cron Jobs → backups planifiés
  │
  ├── Docker Compose — stack applicatif (docker-compose.prod.yml)
  │   ├── mb-frontend (Nginx static, port 3000 publié)
  │   ├── mb-backend (uvicorn, port 8000 publié, restart: unless-stopped)
  │   ├── mb-postgres (PostgreSQL 17, port 5432 interne)
  │   ├── [futur] mb-pay (port 5000 publié)
  │   └── [futur] mb-iq (port 5100 publié)
  │
  ├── Volumes Docker (bind mounts / volumes nommés)
  │   ├── postgres_data → /var/lib/docker/volumes/postgres_data
  │   ├── uploads_data → /var/lib/docker/volumes/uploads_data
  │   └── backup_data → /var/lib/docker/volumes/backup_data
  │
  ├── Paperless-ngx (Docker Compose, géré séparément)
  │   ├── paperless-ngx (port 8000 publié)
  │   ├── paperless-db (PostgreSQL 15)
  │   └── paperless-broker (Redis 7)
  │
  └── Backups (via 1Panel Cron)
      ├── pg_dump quotidien → Hetzner Object Storage
      ├── uploads sync → Hetzner Object Storage
      └── Restore test (1er du mois)
```

> **Docker Compose + 1Panel :** Compose orchestre les conteneurs (`restart: unless-stopped` pour l'auto-restart, `docker compose up -d` pour les mises à jour), 1Panel gère tout le reste (reverse proxy, SSL, file manager, DB GUI, backups, monitoring). Les services exposent leurs ports sur l'hôte, et 1Panel route via `localhost:PORT` — ce pattern est identique qu'il y ait ou non un orchestrateur multi-nœud derrière, donc le retrait de Swarm ne change rien côté 1Panel.
>
> **Swarm écarté :** pas de contrainte de charge, de SLA, ni de date fixée pour un multi-node (cf. section 4 du DAT technique). Réévaluation possible si l'un de ces signaux apparaît concrètement.

### 5.3 Backups quotidiens

```bash
# /etc/cron.d/mbchauffage-backup
0 3 * * * root pg_dump -U mbchauffage -h localhost mbchauffage_db | gzip > /var/backups/mbchauffage_$(date +\%Y\%m\%d).sql.gz
0 4 * * * root s3cmd put /var/backups/mbchauffage_$(date +\%Y\%m\%d).sql.gz s3://mbchauffage-backups/
0 5 1 * * root /usr/local/bin/restore-test.sh  # Test mensuel de restauration
```

**Règle d'or :** les backups sont **non-négociables**. Ce sont 20 ans de données réelles. On fait un backup quotidien + un test de restauration mensuel.

---

## 6. Data Migration — 20 ans d'Excels → PostgreSQL

C'est le défi technique majeur du projet. L'entreprise a 20 ans de données dans des fichiers Excel aux formats variables.

### 6.1 Problèmes identifiés

| Problème                                 | Impact                                               | Stratégie                                                  |
| ---------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| Formats Excel variables selon les années | Colonnes renommées, déplacées                        | Mapping par lot (un fichier de config par "année-type")    |
| Données manquantes                       | Champs vides, clients sans téléphone                 | Valeurs par défaut + logs d'avertissement                  |
| Doublons clients                         | Même client avec orthographe différente              | Fuzzy matching (`diffblib`) + validation manuelle          |
| Accents / encoding                       | É, È, À mal encodés dans vieux fichiers              | Normalisation unicode via `unicodedata`                    |
| Pas de FK relationnelle                  | Les jobs référencent les clients par nom, pas par ID | Résolution en deux passes : clients d'abord → jobs ensuite |

### 6.2 Pipeline d'import

```python
# backend/app/services/import_service.py (pseudo-code)
class ImportService:
    def import_excel(self, file_path: Path, import_config: dict) -> ImportResult:
        # 1. Détection du format (headers, colonnes)
        df = pd.read_excel(file_path, engine="openpyxl")
        mapping = self.detect_format(df, import_config)

        # 2. Passe 1 : Clients
        clients_df = df[mapping["client_columns"]].drop_duplicates()
        for _, row in clients_df.iterrows():
            client = self.find_or_create_client(row, mapping)

        # 3. Passe 2 : Jobs
        jobs_df = df[mapping["job_columns"]]
        for _, row in jobs_df.iterrows():
            client = self.match_client(row["client_name"])  # fuzzy
            job = self.create_job(client, row, mapping)

        # 4. Logs + rapport
        return ImportResult(created=..., skipped=..., errors=...)
```

### 6.3 Validation avant import

```bash
# L'admin uploade le fichier → preview → validation → import
POST /api/v1/admin/import/preview   # Aperçu des 10 premières lignes parsées
POST /api/v1/admin/import/validate  # Validation complète (doublons, erreurs)
POST /api/v1/admin/import/execute   # Import réel
```

---

## 7. Sécurité

- **Auth** : JWT (access token 30 min, refresh token 7 jours), hash bcrypt
- **Photos** : upload réservé aux techniciens authentifiés
- **Avis client** : endpoint public protégé par token unique (UUID), sans auth
- **CORS** : whitelist explicite (mbchauffage.com)
- **XSS** : échappement automatique des templates Vue.js
- **SQL injection** : SQLAlchemy paramétré
- **Firewall** : `ufw` sur le VPS (ports 22, 80, 443 uniquement)
- **Fail2Ban** : protection SSH
- **Backups chiffrés** : `gpg` avant envoi vers Object Storage (optionnel P2)

---

## 8. Structure du projet

```text
mbchauffage/
├── docs/
│   └── DAT/
│       └── MBchauffage-DAT/
│           ├── 04-architecture.md        ← ce document
│           ├── 05-data-model.md
│           ├── 06-workflows.md
│           ├── 07-implementation-roadmap.md
│           └── specs/
│               ├── 01-specs-fonctionnelle.md
│               ├── 02-spec-technique.md
│               └── 03-api-spec.md
├── backend/
│   ├── alembic/                          # Migrations DB
│   ├── alembic.ini
│   └── app/
│       ├── main.py, config.py
│       ├── core/           # database, security, deps, exceptions
│       ├── models/         # client, user, job, devis, facture, bilan...
│       ├── schemas/        # Pydantic
│       ├── repositories/   # accès DB
│       ├── services/       # logique métier + import_service
│       ├── api/v1/         # routes REST
│       │   ├── admin/      # import, users management
│       │   └── ...
│       ├── exporters/      # PDF (rapports, devis, factures)
│       └── importers/      # Import Excel
├── frontend/
│   └── src/
│       ├── main.ts, App.vue, router/
│       ├── stores/, composables/, api/
│       ├── pages/
│       │   ├── admin/      # Import, users, dashboard financier
│       │   └── ...
│       └── components/
├── deploy/
│   ├── docker-compose.yml          # Dev local
│   ├── docker-compose.prod.yml     # Production
│   └── backup/
├── paperless/
│   ├── docker-compose.yml          # Paperless-ngx
│   └── .env                        # Mots de passe (ne pas commiter)
│       ├── backup.sh               # Script pg_dump
│       └── restore-test.sh         # Test de restauration mensuel
├── data/
│   └── imports/                    # Fichiers Excel à importer
│       └── README.md               # Procédure d'import
└── README.md
```

---

## 9. Responsabilités des couches

| Couche                    | Responsabilité                                            |
| ------------------------- | --------------------------------------------------------- |
| **API** (FastAPI routers) | Endpoints REST, validation Pydantic, auth JWT             |
| **Services**              | Logique métier (statuts, timers, checklists, PDF, import) |
| **Repositories**          | Accès DB, requêtes SQLAlchemy                             |
| **Models**                | Mapping ORM, relations                                    |
| **Schemas**               | Validation entrée/sortie API                              |
| **Importers**             | Pipeline import Excel → PostgreSQL (pandas)               |
| **Frontend** (Vue.js)     | UI mobile-first, formulaires, photos, navigation          |

---

## 10. Principes d'architecture

- **Mobile-first** : interface pensée pour le smartphone, bottom nav
- **API REST versionnée** : `/api/v1/`
- **Auth JWT** : rôles `technician` / `admin` / `comptable`
- **Migrations DB dès J1** : Alembic + `--autogenerate` + `upgrade`
- **PostgreSQL uniquement** : pas de SQLite (les données sont réelles, pas de "dev db" simplifiée)
- **Validation bi-couche** : Pydantic serveur + Zod client
- **Cache** : Vue Query, invalidation après mutations
- **Photos** : upload multipart, thumbnails, stockage volume Docker + sync Object Storage
- **PDF** : généré côté serveur (WeasyPrint) — rapports, devis, factures
- **Avis client** : endpoint public sans auth, token unique
- **Backups** : quotidiens automatisés, test de restauration mensuel obligatoire
- **Idempotence** : le seed et l'import sont ré-exécutables sans effet de bord
- **1Panel + Docker Compose** : 1Panel pour le proxy/SSL/backups/files/DB/monitoring, Compose pour l'orchestration (`restart: unless-stopped`, recreate au déploiement) — pas de Swarm, aucun besoin multi-nœud identifié à ce stade

---

## 11. Comparaison Tervo vs MB Chauffage

| Dimension            | Tervo (perso)                   | MB Chauffage (client pro)                                          |
| -------------------- | ------------------------------- | ------------------------------------------------------------------ |
| **Serveur**          | mini-s1 (domestique)            | VPS Hetzner CX22                                                   |
| **Orchestration**    | Docker Compose                  | Docker Compose (identique — pas de Swarm, aucun besoin multi-nœud identifié) |
| **Reverse Proxy**    | Cloudflare Tunnel               | **1Panel OpenResty** (reverse proxy) +                             |
|                      |                                 | **1Panel Let's Encrypt** (SSL one-click)                           |
| **SSL**              | Cloudflare Edge                 | Let's Encrypt via 1Panel                                           |
| **DB**               | PostgreSQL (container existant) | PostgreSQL dédié (service Compose)                                 |
| **Backups**          | Aucun                           | Quotidiens + test mensuel                                          |
| **Data Migration**   | Aucune (seed demo)              | Import 20 ans d'Excels                                             |
| **Module financier** | Non                             | Devis, Factures, Bilans                                            |
| **Domaine**          | tervoapp.com                    | mbchauffage.com                                                    |
| **Sous-domaines**    | 2 (api, www)                    | 4+ (api, pay, iq, www) — gérés via UI 1Panel Websites              |
| **CI/CD**            | GitHub Actions                  | GitHub Actions → `docker compose up -d`                             |
| **Monitoring**       | Aucun                           | 1Panel dashboard + UptimeRobot                                     |
| **Firewall**         | Routeur NAT                     | ufw + fail2ban                                                     |
                                                  |

---

> **Endpoints API :** `specs/03-api-spec.md`
> **Modèle de données :** `05-data-model.md`
> **Spécification technique :** `specs/02-spec-technique.md`
> **Projet source :** Tervo (`docs/DAT/04-architecture.md`)
