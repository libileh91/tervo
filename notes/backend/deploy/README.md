# Déploiement Tervo — Index & Vue d'ensemble

> **Objet :** point d'entrée de toute la documentation de déploiement. Chaque note détaillée est référencée ici.
> **Dernière mise à jour :** 20/09/2026

---

## 1. Les deux cibles

Le projet a **deux environnements de déploiement**, avec des contraintes différentes.

|                    | **mini-s1** (dev / démo)               | **VPS** (production)                |
| ------------------ | -------------------------------------- | ----------------------------------- |
| **Serveur**        | Machine locale, `192.168.10.192`       | Hetzner CX22 (ou équivalent)        |
| **IP**             | Privée, derrière un routeur            | Publique fixe                       |
| **Exposition**     | Cloudflare Tunnel (connexion sortante) | Reverse proxy 1Panel (ports 80/443) |
| **SSL**            | Cloudflare Edge (automatique)          | Let's Encrypt (1Panel)              |
| **DNS**            | Cloudflare (`tervoapp.com`)            | Enregistrements A                   |
| **Ports services** | Historiquement `0.0.0.0`               | **`127.0.0.1`** (Stage 6.1)         |
| **PostgreSQL**     | Conteneur partagé préexistant          | Embarqué dans le compose            |
| **Statut**         | ✅ opérationnel                        | ⏳ Sprint 7.6 (INT-111)                        |

> **Pourquoi deux cibles ?** Le mini-s1 a servi à valider l'application et la chaîne de déploiement sans exposer la machine. Le VPS est la cible professionnelle (Sprint 7.6 (INT-111)).

---

## 2. Chronologie

| Date           | Sprint  | Événement                                                                                    |
| -------------- | ------- | -------------------------------------------------------------------------------------------- |
| Sprint 3.1     | —       | Premier déploiement : Dockerfile multi-stage, `docker-compose.yml`, PostgreSQL, 1Panel, seed |
| Sprint 4.1     | —       | Déploiement du frontend mobile (responsive, états, transitions)                              |
| 11/07/2026     | —       | **Déploiement Internet** via Cloudflare Tunnel (`tervoapp.com`)                              |
| 11/07/2026     | —       | Décision : **ni 1Panel ni Traefik** comme reverse proxy (le tunnel suffit)                   |
| 13/07/2026     | 4.1     | Fix timezone-aware datetime (`PUT /jobs/{id}/start` → 500)                                   |
| 17/08/2026     | —       | Incident **502** : OpenResty ne résout plus le nom du conteneur                              |
| **17/09/2026** | **6.1** | **Corrections d'architecture** : ports `127.0.0.1`, healthchecks, firewall, CI/CD            |
| 20/09/2026     | 6.1     | CI GitHub Actions verte (26s) + fix `UPLOAD_DIR` révélé par la CI                            |
| ⏳             | 6.4     | **Déploiement VPS** (provisioning, DNS, Let's Encrypt, CI/CD)                                |

---

## 3. Architecture cible

```
                        INTERNET
                           │
                     HTTPS 80/443
                           │
                   ┌───────▼────────┐
                   │     1Panel     │
                   │   OpenResty    │
                   │  SSL / Routing │
                   └───────┬────────┘
                           │ 127.0.0.1 (aucun service applicatif exposé)
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    Frontend (Vue.js)  Backend (FastAPI)  [services annexes]
    127.0.0.1:3000     127.0.0.1:8000
          │                │
          │         Router → Service → Repository
          │                │
          │           PostgreSQL
          │          (aucun port publié)
          │
          └────────── API REST

  1Panel (7410) : écoute en loopback → accès par tunnel SSH uniquement
```

**Ports publics : 22, 80, 443.** Tout le reste est interne.

---

## 4. Inventaire des notes

### 4.1 Fondations (déploiement initial)

| Fichier                   | Contenu                                               |
| ------------------------- | ----------------------------------------------------- |
| `initial_deploy.md`       | Première mise en route du serveur (étapes pas à pas)  |
| `internet_deploy.md`      | Stratégie IaaS : mini-s1 + Docker + Cloudflare Tunnel |
| `Reverse Proxy 1Panel.md` | Configuration du reverse proxy 1Panel pour Tervo      |
| `domaines.md`             | Enregistrements DNS (`tervoapp.com`, `api.*`)         |
| `errors.md`               | Registre chronologique des erreurs de déploiement     |

### 4.2 Cloudflare Tunnel

| Fichier                       | Contenu                                                                                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `cloudflare-tunnel-deploy.md` | **Documentation complète** : installation `cloudflared`, création du tunnel, DNS, `config.yml`, service systemd, erreurs (502, 405), usages de `cloudflared` |
| `why-not-1panel-traefik.md`   | Pourquoi 1Panel/Traefik ne sont pas nécessaires quand le tunnel assure proxy + SSL + ingress                                                                 |

### 4.3 Incidents & fixes

| Fichier                              | Contenu                                                                               |
| ------------------------------------ | ------------------------------------------------------------------------------------- |
| `incident-502-nginx-upstream.md`     | **502 Bad Gateway** — OpenResty ne résout plus `tervo-backend-1` (IP statique vs nom) |
| `fix-timezone-aware-datetime-500.md` | **500 sur `PUT /jobs/{id}/start`** — datetime naïf vs timezone-aware                  |
| `../sprint-4.1/sprint-4.1-deploy.md` | Déploiement du frontend mobile (Sprint 4.1)                                           |

### 4.4 Corrections d'architecture (Stage 6.1)

| Fichier                            | Tâche  | Contenu                                                                                                 |
| ---------------------------------- | :----: | ------------------------------------------------------------------------------------------------------- |
| `../sprint-6.1/ports-securises.md` | INT-66 | Bind `127.0.0.1`, anatomie d'une ligne `ports:`, piège `localhost` vs `127.0.0.1`, PostgreSQL sans port |
| `../sprint-6.1/healthchecks.md`    | INT-67 | `depends_on` ≠ readiness, `pg_isready`, `condition: service_healthy`, démonstration réelle              |
| `../sprint-6.1/firewall.md`        | INT-68 | ufw (22/80/443), fail2ban, 1Panel par tunnel SSH, piège « activer ufw avant SSH »                       |
| `../sprint-6.1/ci-cd.md`           | INT-70 | Double build expliqué, 2 niveaux de maturité (CI-vérifie vs registry GHCR), garde-fou `DEPLOY_ENABLED`  |

### 4.5 Évolutions documentées (hors périmètre actuel)

| Fichier            | Contenu                                                                            |
| ------------------ | ---------------------------------------------------------------------------------- |
| `paperless-ngx.md` | GED documentaire (OCR des archives) — installation Docker Classic, intégration API |

---

## 5. Stage 6.1 en détail

Objectif : rendre le déploiement **défendable** — chaque choix justifiable.

### INT-66 — Ports sécurisés

| Avant                        | Après                                  |
| ---------------------------- | -------------------------------------- |
| `${BACKEND_PORT:-8000}:8000` | `127.0.0.1:${BACKEND_PORT:-8000}:8000` |
| `${FRONTEND_PORT:-3000}:80`  | `127.0.0.1:${FRONTEND_PORT:-3000}:80`  |
| postgres `5432:5432`         | _(aucun port)_                         |

**Vérification :** `docker compose config` → `host_ip: 127.0.0.1` sur les deux services, 0 port pour postgres.

**Pourquoi :** sans préfixe, Docker publie sur `0.0.0.0` → le service est joignable depuis Internet **en contournant le reverse proxy** (donc sans TLS ni filtrage).

### INT-67 — Healthchecks

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${TERVO_DB_USER:-lob} -d ${TERVO_DB_NAME:-tervo_db}"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s

backend:
  depends_on:
    postgres:
      condition: service_healthy
```

**Consolidation nécessaire :** `condition: service_healthy` ne fonctionne **que dans un même fichier Compose**. PostgreSQL était dans `postgres.docker-compose.yml` → il a été intégré au compose principal.

**Démonstration réelle** (test isolé) :

```
Container hctest-db-1 Started
Container hctest-db-1 Waiting      ← attend le healthcheck
Container hctest-db-1 Healthy
Container hctest-app-1 Starting    ← démarre seulement là
```

### INT-68 — Firewall

| Port | Service                |    Public     |
| ---- | ---------------------- | :-----------: |
| 22   | SSH (clé uniquement)   |      ✅       |
| 80   | HTTP (redirect + ACME) |      ✅       |
| 443  | HTTPS                  |      ✅       |
| 7410 | 1Panel                 | ❌ tunnel SSH |

Cohérence rétablie dans le DAT (deux politiques contradictoires existaient).

### INT-69 — Versions

Le DAT décrit l'**architecture** (`Python 3.11+`, `PostgreSQL`) ; les versions exactes vivent dans `pyproject.toml`, `package.json`, `docker-compose.yml`.

### INT-70 — CI/CD

```
push main
   ├── backend-tests   (uv sync --frozen + pytest)
   ├── frontend-build  (bun install --frozen-lockfile + build)
   └── deploy          (needs: les deux, si vars.DEPLOY_ENABLED == 'true')
          └── SSH → git pull → docker compose up -d --build → alembic upgrade head
```

**Un seul build**, sur le VPS. Détail complet : `../sprint-6.1/ci-cd.md`.

---

## 6. Erreurs rencontrées → corrections

| #   | Erreur                                        | Cause racine                                                            | Correction                                                    |
| --- | --------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| 1   | Port déjà occupé                              | Conteneur + 1Panel voulaient le même port                               | Retirer `ports:` quand le proxy gère                          |
| 2   | 502 Bad Gateway                               | OpenResty (mode host) ne résout pas les noms Docker                     | Utiliser l'IP statique du conteneur                           |
| 3   | 405 + « Identifiants invalides »              | Mauvais routage `/api/`                                                 | Corriger la configuration du reverse proxy                    |
| 4   | 500 Internal Server Error                     | Rebuild frontend incomplet                                              | Rebuild complet de l'image                                    |
| 5   | 502 après redémarrage                         | L'IP du conteneur change                                                | Nom de service + réseau partagé                               |
| 6   | **500 sur `/jobs/{id}/start`**                | `datetime.utcnow()` naïf vs colonne timezone-aware                      | `datetime.now(timezone.utc)`                                  |
| 7   | **`invalid input value for enum`**            | Enum PostgreSQL créé avec les valeurs Python (`planifié` vs `PLANIFIE`) | Migration d'enum corrigée                                     |
| 8   | **CI rouge : `Directory ... does not exist`** | `StaticFiles(directory=...)` validé à l'import ; `uploads/` gitignoré   | `Path(...).mkdir(parents=True, exist_ok=True)` dans `main.py` |

> Les erreurs 1-5 sont documentées dans `cloudflare-tunnel-deploy.md` et `errors.md` ; l'erreur 7 dans `notes/backend/extras/` ; l'erreur 8 est récente (Stage 6.1).

---

## 7. Checklist de déploiement

### 7.1 Premier déploiement (mini-s1)

- [ ] Docker + Docker Compose installés
- [ ] Conteneur PostgreSQL opérationnel + base `tervo_db` créée
- [ ] `deploy/docker-compose.yml` configuré (`.env` avec `SECRET_KEY`, `TERVO_DB_*`)
- [ ] `docker compose up -d`
- [ ] `alembic upgrade head`
- [ ] `python -m app.seed`
- [ ] Reverse proxy 1Panel → sites configurés
- [ ] Vérifications : `curl` frontend + API, login

### 7.2 Déploiement VPS (Sprint 7.6 (INT-111))

- [ ] VPS provisionné, Ubuntu 24.04, SSH par clé
- [ ] `ufw` (22/80/443) + `fail2ban` + `unattended-upgrades`
- [ ] Docker + 1Panel installés ; `1panel-network` créé
- [ ] `.env` de production (secrets forts)
- [ ] DNS : `tervo.com`, `api.tervo.com` → IP du VPS
- [ ] Sites 1Panel + Let's Encrypt activé
- [ ] `docker compose up -d --build` + migrations + seed
- [ ] Backups planifiés (quotidien + test mensuel)
- [ ] Secrets GitHub (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`) + variable `DEPLOY_ENABLED=true`
- [ ] CI/CD testée de bout en bout

---

## 8. GitHub Actions — limites et stratégie

### 8.1 Limites du plan gratuit

| Type de dépôt           | Minutes incluses                   | Stockage artefacts |
| ----------------------- | ---------------------------------- | ------------------ |
| **Public**              | **Illimitées** (runners standards) | Illimité           |
| **Privé** (compte Free) | **2 000 min/mois**                 | 500 Mo             |

**Ce dépôt est public** (`github.com/libileh91/tervo`) → **aucune limite de minutes**.

Facteurs de consommation : Linux ×1, Windows ×2, macOS ×10.

**Consommation mesurée de ce projet :** 3 runs, ~20-27 s chacun → **~1 minute au total**. Négligeable même sur un plan privé.

### 8.2 Faut-il construire en local pour économiser la CI ?

**Réponse courte : non — et c'est une mauvaise idée de contourner la CI.**

| Idée                                              | Verdict | Pourquoi                                                                                                                                   |
| ------------------------------------------------- | :-----: | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Skip la CI pour les changements « mineurs »       |   ❌    | La CI perd sa fonction de **garantie**. Un « mineur » casse souvent en prod (ex. le fix `UPLOAD_DIR` a été révélé par la CI, pas en local) |
| Builder en local au lieu de la CI                 |   ❌    | L'environnement local n'est pas reproductible (OS, versions, caches). Retour du « ça marche chez moi »                                     |
| **Checks locaux _en plus_ de la CI**              |   ✅    | Retour rapide avant push, évite de brûler des runs sur des erreurs évidentes                                                               |
| **Optimiser la CI** (filtres, concurrence, cache) |   ✅    | Vrai levier d'économie, sans perte de garantie                                                                                             |

### 8.3 Ce qui est réellement utile

1. **`concurrency`** — annule les runs obsolètes quand on pousse plusieurs fois d'affilée
2. **`paths-ignore`** — ne pas lancer la CI pour une modification de docs/notes uniquement
3. **Cache** — déjà en place via `setup-uv` et `setup-bun`
4. **Déploiement conditionnel** — déjà en place (`DEPLOY_ENABLED`)

> **Principe :** la CI est la **source de vérité**. Les checks locaux sont un **complément de confort**, jamais un remplacement.

---

## 9. Leçons retenues

| Leçon                                             | Détail                                                                      |
| ------------------------------------------------- | --------------------------------------------------------------------------- |
| **`depends_on` ≠ readiness**                      | Le healthcheck matérialise la frontière entre « démarré » et « disponible » |
| **`0.0.0.0` contourne le proxy**                  | Un service publié sans `host_ip` est joignable depuis Internet              |
| **La CI trouve ce que le local cache**            | Le fix `UPLOAD_DIR` est passé inaperçu en local (dossier existant)          |
| **Une action composite peut cacher des versions** | Vérifier `runs.using` via l'API GitHub avant de conclure                    |
| **`localhost` ≠ `127.0.0.1` en Docker**           | Le premier n'est pas une IP d'écoute valide pour `ports:`                   |
| **Backup ≠ synchronisation**                      | Versionner, ne pas refléter — sinon propagation des suppressions            |

---

> **Documentation d'architecture :** `docs/DAT/04-architecture.md`
> **Revue des corrections :** `docs/DAT/annexes/revue-architecture.md`
> **Workflow CI/CD :** `.github/workflows/ci.yml`
