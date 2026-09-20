# Sprint 6.1 : Corrections architecture + Docker + CI/CD (2 jours)

> **Durée :** 2 jours (7h/j) | **Points :** 10 | **Tâches :** INT-66 à INT-70
>
> **Référence :** `docs/DAT/annexes/revue-architecture.md` §2 à §6, §16, §19, §20

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
- [x] Décision figée : ports publics = **22, 80, 443**
- [x] `7410` (1Panel) **non exposé publiquement**
- [x] Procédure documentée : accès 1Panel via tunnel SSH (`ssh -L 7410:localhost:7410`)
- [x] Alternative documentée : restriction firewall à une IP admin connue
- [x] Suppression des mentions contradictoires dans le DAT (`7410` exposé vs non exposé)

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
- [x] DAT : `Python 3.11+`, `FastAPI`, `SQLAlchemy 2.x`, `PostgreSQL` (sans `0.111+`, `17`, etc.)
- [x] Versions exactes conservées dans : `pyproject.toml`, `package.json` (`vue ^3.5.40`, `vite ^6.0.0`), `docker-compose.yml` (`postgres:17.4`)
- [x] Principe documenté : « Le DAT décrit l'architecture ; le lockfile décrit l'état exact des dépendances. » (`00-sommaire.md`, `specs/02` §1)
- [x] Audit des fichiers DAT pour retirer les versions figées (fusion DAT du 17/09)

**Technical Notes**
- Fichiers : `docs/DAT/04-architecture.md`, `specs/02-spec-technique.md`
- **Rappel entretien :** c'est un excellent point de maturité — séparer la doc d'architecture de l'état des dépendances.

---

## INT-70 — CI/CD sans double build (2 pts)

**User Story**
En tant que **dev backend**,
Je veux **un pipeline CI/CD cohérent**,
Afin de **ne pas builder les images deux fois inutilement**.

**Acceptance Criteria**
- [x] Diagnostic documenté : le pipeline décrit buildait dans GitHub Actions **puis** sur le VPS (double build inutile, sans registry intermédiaire)
- [x] Correction implémentée : GitHub Actions fait les **tests**, puis SSH → `git pull` → `docker compose up -d --build` → `alembic upgrade head`
- [x] Aucun build d'image dans GitHub Actions (le dossier `.github/` était vide — le workflow créé ne contient pas ce build redondant)
- [x] Évolution documentée (non implémentée) : build → push **GHCR** → `docker compose pull` sur le VPS
- [x] Note pédagogique : `notes/backend/deploy/ci-cd.md`
- [x] Validation : YAML parsé, 97 tests backend OK, `bun run build` OK

**Technical Notes**
- Fichier : `.github/workflows/ci.yml`
- **Rappel entretien :** « Pour la première version, j'ai privilégié un déploiement simple par SSH et Docker Compose. Une évolution naturelle serait de publier les images dans un registry puis de faire un `docker compose pull` sur le VPS. »
- Ne **pas** prétendre maîtriser GHCR — le présenter comme évolution.

---

## Tests Cases Sprint 6.1

Les tests cases détaillés sont dans `test-cases.json`.
