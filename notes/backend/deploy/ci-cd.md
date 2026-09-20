# INT-70 — CI/CD : un seul build

> **Stage 6 / Sprint 6.1** | Points : 2 | Statut : ✅
> **Référence :** `docs/DAT/annexes/revue-architecture.md` §5
> **Fichier :** `.github/workflows/ci.yml`

---

## Le problème : le double build

Le pipeline décrit initialement faisait :

```
GitHub Actions
   ├── tests
   ├── docker build          ← 1er build
   └── SSH vers le VPS
          ├── git pull
          ├── docker build   ← 2e build (le même !)
          └── docker compose up
```

**Les images construites dans GitHub Actions ne servaient à rien.**

Pourquoi ? Parce qu'il n'y a **aucun registry intermédiaire**. La CI construit des images… puis les jette. Le VPS reconstruit tout de zéro.

| Conséquence | Impact |
|-------------|--------|
| Temps de pipeline doublé | CI plus lente, minutes consommées inutilement |
| Ressources gaspillées | CPU/bande passante sur les runners GitHub **et** sur le VPS |
| Incohérence possible | Les deux builds pourraient diverger (env, cache, ordre) |

---

## Deux architectures, deux niveaux de maturité

### Niveau 1 — La CI vérifie, le serveur construit (retenu)

```
push main
    │
    ▼
GitHub Actions
    ├── tests backend (pytest)
    └── build frontend (vérification)
         │
         ▼ (si OK)
      SSH → VPS
         ├── git pull
         ├── docker compose up -d --build   ← UN SEUL build
         └── alembic upgrade head
```

**Avantages :** simple, un seul point de construction, pas de registry à gérer.
**Limite :** la CI ne teste pas les *images* (elle teste le code).

### Niveau 2 — Registry d'images (évolution)

```
push main
    │
    ▼
GitHub Actions
    ├── tests
    ├── docker build
    └── docker push → GHCR (registry)
         │
         ▼
      SSH → VPS
         └── docker compose pull && up -d   ← aucun build sur le serveur
```

**Avantages :** le VPS ne build jamais (moins de charge), l'artefact testé est exactement celui déployé, rollback immédiat (retag).
**Coût :** gestion d'un registry + authentification + stratégie de tags.

> **Position à tenir :** le niveau 1 est **implémenté** ; le niveau 2 est une **évolution identifiée**, pas une réalisation. Ne pas présenter le niveau 2 comme acquis.
>
> **Déploiement désactivé par défaut** : tant que `DEPLOY_ENABLED ≠ 'true'`, le job `deploy` est ignoré. Les jobs de **vérification** (tests + build) tournent toujours — c'est le vrai intérêt du pipeline à ce stade.

---

## Le workflow implémenté

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:      # uv sync + pytest
  frontend-build:     # bun install + bun run build
  deploy:             # needs: [backend-tests, frontend-build]
    if: >
      github.ref == 'refs/heads/main' &&
      github.event_name == 'push' &&
      vars.DEPLOY_ENABLED == 'true'
```

### Points de conception

| Choix | Raison |
|-------|--------|
| `needs: [backend-tests, frontend-build]` | On ne déploie pas du code non testé |
| `if: ref == main && event == push` | Pas de déploiement depuis une PR |
| **`vars.DEPLOY_ENABLED == 'true'`** | Déploiement **désactivé par défaut** — le VPS n'existe pas encore et les secrets ne sont pas configurés. À activer en Stage 6.4 |
| `uv sync --frozen` | Respecte le lockfile `uv.lock` |
| `bun install --frozen-lockfile` | Respecte `bun.lock` |
| `set -e` dans le script SSH | Le pipeline échoue au premier problème |
| `alembic upgrade head` après `up -d` | Migrations appliquées automatiquement |
| `docker image prune -f` | Évite l'accumulation d'images orphelines |

> **Pourquoi une variable et pas un secret ?** Les `secrets.*` ne sont pas lisibles dans un `if:` d'étape au niveau job. Les `vars.*` (repository variables) le sont — ce qui permet de garder le pipeline vert tant que le VPS n'est pas prêt.

### Secrets requis

| Secret | Contenu |
|--------|---------|
| `VPS_HOST` | IP ou nom d'hôte du serveur |
| `VPS_USER` | Utilisateur SSH |
| `VPS_SSH_KEY` | Clé privée SSH (déploiement) |

### Variable de dépôt requise

| Variable | Valeur |
|----------|--------|
| `DEPLOY_ENABLED` | `true` pour activer le déploiement (absent ou ≠ `true` → job `deploy` ignoré) |

---

## Tests backend : SQLite

Les tests utilisent une base **SQLite** (`sqlite+aiosqlite:///./test_tervo.db`), pas PostgreSQL.

→ Le workflow CI n'a donc **pas besoin d'un service PostgreSQL**. C'est volontaire et cohérent avec l'état actuel.

> **Évolution possible :** exécuter les tests contre PostgreSQL (service container) pour détecter les différences de dialecte (types, contraintes, `GENERATED ALWAYS AS`, etc.). À planifier si des bugs spécifiques PostgreSQL apparaissent.

---

## À retenir pour l'entretien

**Question type :** « Comment déployez-vous ? »

> « Un push sur `main` déclenche GitHub Actions : les tests backend passent, le frontend se build. Si tout est vert, la CI se connecte en SSH au VPS, fait un `git pull` et un `docker compose up -d --build`, puis applique les migrations Alembic. »

**Question type :** « Où construisez-vous les images ? »

> « Uniquement sur le serveur. Ma première version construisait aussi dans la CI, mais sans registry intermédiaire ce build était jeté — donc inutile. Évolution logique : pousser les images dans GHCR et ne faire qu'un `docker compose pull` sur le serveur. »

**Ce qu'il faut éviter de dire :** « j'utilise GHCR » — ce n'est pas implémenté.

---

## Pièges

| Piège | Conséquence |
|-------|-------------|
| Builder dans la CI sans registry | Travail jeté, pipeline deux fois plus long |
| Déployer sans `needs` | Code non testé en production |
| Déployer depuis une PR | Déploiements non maîtrisés |
| Oublier `--frozen` / `--frozen-lockfile` | Dépendances non déterministes |
| Oublier les migrations | L'application tourne sur un schéma obsolète |

---

> **Fichier lié :** `.github/workflows/ci.yml`
> **Précédent :** INT-69 (versions)
> **Suite :** Sprint 6.2 (Import Excel)
