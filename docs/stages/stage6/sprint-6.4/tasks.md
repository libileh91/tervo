# Sprint 6.4 : Déploiement VPS (2 jours)

> **Durée :** 2 jours (7h/j) | **Points :** 16 | **Tâches :** INT-85 à INT-90
>
> **Référence :** `docs/DAT/MBchauffage-DAT/04-architecture.md` §5, `Todo_Fix.md` §2, §4, §5, §17, §20
>
> **Prérequis :** Sprint 6.1 terminé (ports, healthchecks, CI/CD prêts).

---

## Objectif

Déployer Tervo sur un VPS public avec :
- Reverse proxy 1Panel + SSL Let's Encrypt
- Services non exposés directement (`127.0.0.1`)
- PostgreSQL dédié
- Pipeline CI/CD opérationnel

**Ce qui change vs mini-s1 :** IP publique fixe, DNS réel, Let's Encrypt (plus de Cloudflare Tunnel).

---

## INT-85 — Provisionner et sécuriser le VPS (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **un VPS provisionné et sécurisé**,
Afin d'**héberger Tervo sur une IP publique**.

**Acceptance Criteria**
- [ ] VPS commandé (Hetzner CX22 ou équivalent : 2 vCPU, 4 Go, 40 Go)
- [ ] Ubuntu 24.04 LTS installé
- [ ] SSH par **clé uniquement** (mot de passe désactivé)
- [ ] `ufw` actif : ports **22, 80, 443** uniquement
- [ ] `fail2ban` installé et actif
- [ ] `unattended-upgrades` activé (patchs de sécurité)
- [ ] Utilisateur non-root avec sudo
- [ ] Test : `ssh` par mot de passe → refusé

**Technical Notes**
- `/etc/ssh/sshd_config` : `PasswordAuthentication no`, `PermitRootLogin no`
- `ufw default deny incoming` + `ufw allow 22,80,443/tcp`
- **Rappel entretien :** « L'accès administrateur se fait par clé SSH, le firewall n'ouvre que 22/80/443. »

---

## INT-86 — Installer Docker + 1Panel (2 pts)

**User Story**
En tant que **dev backend**,
Je veux **Docker et 1Panel installés**,
Afin de **déployer et administrer l'application**.

**Acceptance Criteria**
- [ ] Docker Engine + plugin Compose installés
- [ ] Utilisateur non-root ajouté au groupe `docker`
- [ ] 1Panel installé et accessible
- [ ] Réseau Docker `1panel-network` créé
- [ ] 1Panel accessible **uniquement via tunnel SSH** (`ssh -L 7410:localhost:7410`)
- [ ] Test : `:7410` depuis l'extérieur → refusé

**Technical Notes**
- Install Docker : script officiel `get.docker.com`
- 1Panel : script d'installation officiel
- **Ne pas exposer 7410 publiquement** (cf. INT-68)
- `ssh -L 7410:localhost:7410 user@vps` puis `http://localhost:7410`

---

## INT-87 — Adapter `docker-compose.yml` pour la production (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **un compose de production adapté au VPS**,
Afin de **déployer proprement PostgreSQL + backend + frontend**.

**Acceptance Criteria**
- [ ] **Décision PostgreSQL** : service `postgres` **dans** le compose (dédié) — pas de dépendance externe
- [ ] Backend bind : `127.0.0.1:8000:8000`
- [ ] Frontend bind : `127.0.0.1:3000:80`
- [ ] PostgreSQL : **aucun port publié**
- [ ] `healthcheck` PostgreSQL : `pg_isready`
- [ ] `depends_on: postgres: condition: service_healthy`
- [ ] `healthcheck` backend (déjà présent) conservé
- [ ] Volume `postgres_data` + `uploads_data`
- [ ] Secrets via `.env` (non commité)
- [ ] Test : `docker compose up -d` → tous les services healthy

**Technical Notes**
- Fichier : `deploy/docker-compose.yml` (production)
- **Changement vs actuel :** le compose actuel dépend d'un PG externe — en prod on embarque le PG
- **Rappel entretien :** « J'ai embarqué PostgreSQL dans le compose de production — un seul `docker compose up` suffit, et les données sont dans un volume nommé. »

---

## INT-88 — DNS + reverse proxy + SSL (2 pts)

**User Story**
En tant que **dev backend**,
Je veux **un domaine avec HTTPS**,
Afin de **rendre Tervo accessible publiquement**.

**Acceptance Criteria**
- [ ] Enregistrements DNS A : `tervo.<domaine>` et `api.tervo.<domaine>` → IP du VPS
- [ ] Site 1Panel : `tervo.<domaine>` → `http://127.0.0.1:3000`
- [ ] Site 1Panel : `api.tervo.<domaine>` → `http://127.0.0.1:8000`
- [ ] SSL Let's Encrypt activé sur les deux sites
- [ ] Renouvellement automatique vérifié
- [ ] Test : `https://api.tervo.<domaine>/docs` → Swagger accessible en HTTPS

**Technical Notes**
- 1Panel → Websites → Create → Reverse Proxy
- HTTPS → Let's Encrypt → Enable (one-click)
- **Rappel entretien :** « Le reverse proxy 1Panel est le seul point d'entrée HTTPS — il route vers les services en loopback. »

---

## INT-89 — Premier déploiement + vérification + CI/CD (4 pts)

**User Story**
En tant que **dev backend**,
Je veux **déployer et vérifier l'application**,
Afin de **valider que la stack fonctionne en production**.

**Acceptance Criteria**
- [ ] `git clone` sur le VPS
- [ ] `.env` créé (secrets de prod)
- [ ] `docker compose up -d --build`
- [ ] Migrations : `docker exec <backend> alembic upgrade head`
- [ ] Seed : `docker exec <backend> python -m app.seed`
- [ ] Frontend répond : `curl https://tervo.<domaine>` → 200
- [ ] API répond : `curl https://api.tervo.<domaine>/openapi.json` → 200
- [ ] Login test : `tech1 / password123` → 200
- [ ] Upload photo test → 201
- [ ] **CI/CD** : GitHub Actions → tests → SSH → `git pull` → `compose up -d`

**Technical Notes**
- Secrets GitHub : `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- Workflow simplifié (cf. INT-70) : un seul build
- **Rappel entretien :** déploiement par SSH + Compose ; évolution possible vers registry + `compose pull`

---

## INT-90 — Notes de déploiement (2 pts)

**User Story**
En tant que **dev backend**,
Je veux **documenter la procédure VPS**,
Afin de **pouvoir la rejouer et l'expliquer**.

**Acceptance Criteria**
- [ ] `notes/backend/deploy/vps-deploy.md` créé
- [ ] Prérequis (VPS, DNS, secrets)
- [ ] Commandes copiables (one-liners)
- [ ] Erreurs rencontrées + corrections
- [ ] Schéma final : `Internet → 1Panel (80/443) → 127.0.0.1:PORT`
- [ ] Différences avec le déploiement mini-s1 (Tunnel vs Let's Encrypt)

**Technical Notes**
- Fichier : `notes/backend/deploy/vps-deploy.md`
- Référence : `notes/backend/deploy/cloudflare-tunnel-deploy.md` (mini-s1)

---

## Tests Cases Sprint 6.4

Les tests cases détaillés sont dans `test-cases.json`.
