# Sprint 6.1 : Corrections architecture + Docker + CI/CD (2 jours)

> **Durée :** 2 jours (7h/j) | **Points :** 10 | **Tâches :** INT-66 à INT-70
>
> **Référence :** `docs/DAT/MBchauffage-DAT/Todo_Fix.md` §2 à §6, §16, §19, §20

---

## INT-66 — Ports sécurisés (127.0.0.1) + reverse proxy (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **que les services applicatifs ne soient pas exposés publiquement**,
Afin de **forcer tout le trafic à passer par le reverse proxy HTTPS**.

**Acceptance Criteria**
- [x] Backend bind : `127.0.0.1:8000:8000` (pas `0.0.0.0`)
- [x] Frontend bind : `127.0.0.1:3000:80` (pas `0.0.0.0`)
- [x] PostgreSQL : **aucun port publié** (accessible uniquement dans le réseau Docker)
- [x] Documentation du flux : `Internet → 1Panel (80/443) → localhost:PORT → service`
- [x] Test : `docker compose config` → `host_ip: 127.0.0.1` confirmé sur backend + frontend, 0 port pour postgres

**Technical Notes**
- Fichier : `deploy/docker-compose.yml`
- `127.0.0.1:8000:8000` = bind uniquement sur la loopback de l'hôte
- Le reverse proxy 1Panel route `api.tervo.com → http://127.0.0.1:8000`
- **Rappel entretien :** « Les services applicatifs ne sont pas directement exposés à Internet. Le reverse proxy est le seul point d'entrée HTTPS. »

---

## INT-67 — Healthchecks + `depends_on: condition` (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **que le backend ne démarre qu'une fois PostgreSQL réellement prêt**,
Afin d'**éviter les erreurs de connexion au démarrage**.

**Acceptance Criteria**
- [x] `postgres` : `healthcheck.test: pg_isready -U <user> -d <db>`
- [x] `healthcheck.interval: 10s`, `timeout: 5s`, `retries: 5`
- [x] `backend.depends_on.postgres.condition: service_healthy`
- [x] Test : `docker compose up` → le backend attend que PG soit healthy (démo isolée : `Waiting` → `Healthy` → `Starting`)
- [x] Test : `docker compose ps` → colonne STATUS montre `(healthy)`
- [x] Consolidation : `postgres` déplacé dans `docker-compose.yml` (requis pour `condition: service_healthy`)

**Technical Notes**
- Fichier : `deploy/docker-compose.yml`
- `depends_on` simple = **ordre de démarrage**, pas **disponibilité**
- `pg_isready` : retourne 0 si PostgreSQL accepte les connexions
- **Rappel entretien :** « Le démarrage du conteneur ne garantit pas que la base soit prête à accepter des connexions. Le healthcheck distingue un conteneur démarré d'un service réellement disponible. »

---

## INT-68 — Firewall : ports 22/80/443 uniquement (1 pt)

**User Story**
En tant que **dev backend**,
Je veux **une politique de ports cohérente et documentée**,
Afin de **ne pas exposer l'administration (1Panel) publiquement**.

**Acceptance Criteria**
- [ ] Décision figée : ports publics = **22, 80, 443**
- [ ] `7410` (1Panel) **non exposé publiquement**
- [ ] Procédure documentée : accès 1Panel via tunnel SSH (`ssh -L 7410:localhost:7410`)
- [ ] Alternative documentée : restriction firewall à une IP admin connue
- [ ] Suppression des mentions contradictoires dans le DAT (`7410` exposé vs non exposé)

**Technical Notes**
- Fichier : `notes/backend/deploy/firewall.md` (nouveau)
- `ufw allow 22,80,443/tcp`
- **Rappel entretien :** « L'interface d'administration n'est jamais exposée publiquement — elle est accessible via tunnel SSH ou restriction d'IP. »

---

## INT-69 — Versions : DAT = archi, lockfile = versions (1 pt)

**User Story**
En tant que **dev backend**,
Je veux **que le DAT décrive l'architecture sans figer des versions précises**,
Afin d'**éviter que la doc vieillisse**.

**Acceptance Criteria**
- [ ] DAT : `Python 3.11+`, `FastAPI`, `SQLAlchemy 2.x`, `PostgreSQL` (sans `0.111+`, `17`, etc.)
- [ ] Versions exactes conservées dans : `pyproject.toml`, `package.json`, `docker-compose.yml`
- [ ] Principe documenté : « Le DAT décrit l'architecture ; le lockfile décrit l'état exact des dépendances. »
- [ ] Audit des fichiers DAT pour retirer les versions figées

**Technical Notes**
- Fichiers : `docs/DAT/MBchauffage-DAT/04-architecture.md`, `specs/02-spec-technique.md`
- **Rappel entretien :** c'est un excellent point de maturité — séparer la doc d'architecture de l'état des dépendances.

---

## INT-70 — CI/CD sans double build (2 pts)

**User Story**
En tant que **dev backend**,
Je veux **un pipeline CI/CD cohérent**,
Afin de **ne pas builder les images deux fois inutilement**.

**Acceptance Criteria**
- [ ] Diagnostic documenté : le pipeline actuel build dans GitHub Actions **puis** sur le VPS
- [ ] Correction : GitHub Actions fait les **tests**, puis SSH → `git pull` → `docker compose build` → `up -d`
- [ ] Le build GitHub Actions redondant est supprimé
- [ ] Évolution documentée (non implémentée) : build → push **GHCR** → `docker compose pull` sur le VPS
- [ ] Note pédagogique : pourquoi le double build est incohérent

**Technical Notes**
- Fichier : `.github/workflows/ci.yml`
- **Rappel entretien :** « Pour la première version, j'ai privilégié un déploiement simple par SSH et Docker Compose. Une évolution naturelle serait de publier les images dans un registry puis de faire un `docker compose pull` sur le VPS. »
- Ne **pas** prétendre maîtriser GHCR — le présenter comme évolution.

---

## Tests Cases Sprint 6.1

Les tests cases détaillés sont dans `test-cases.json`.
