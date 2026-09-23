# Tervo — Document d'Architecture Technique (DAT)

> **Projet :** Tervo — application de gestion d'interventions CVC (mobile-first).
> **Dernière mise à jour :** 17/09/2026

---

## Sommaire

| Document | Contenu |
|----------|---------|
| [`04-architecture.md`](04-architecture.md) | Vue d'ensemble, stack, décisions, infrastructure, migration Excel, sécurité |
| [`05-data-model.md`](05-data-model.md) | Schéma relationnel complet (SQL, colonnes, relations, règles métier) |
| [`06-workflows.md`](06-workflows.md) | Parcours utilisateurs, UX, navigation, règles métier |
| [`07-implementation-roadmap.md`](07-implementation-roadmap.md) | Stages, sprints, risques, critères de succès |
| [`08-module-catalogue.md`](08-module-catalogue.md) | Module catalogue produits & exposition en salle |
| [`specs/01-specs-fonctionnelle.md`](specs/01-specs-fonctionnelle.md) | Périmètre fonctionnel, personas, modules, user stories |
| [`specs/02-spec-technique.md`](specs/02-spec-technique.md) | Stack détaillée, frontend, infrastructure, CI/CD |
| [`specs/03-api-spec.md`](specs/03-api-spec.md) | Endpoints REST, payloads, matrice de permissions |
| [`annexes/revue-architecture.md`](annexes/revue-architecture.md) | Revue d'architecture et corrections appliquées |
| [`annexes/decision-ged.md`](annexes/decision-ged.md) | Décision GED (Paperless-ngx vs Papra) — hors périmètre actuel |

---

## Ordre de lecture conseillé

```
1. 00-sommaire.md              ← vous êtes ici
2. specs/01-specs-fonctionnelle.md   ← le quoi (fonctionnel)
3. 04-architecture.md                ← le comment (archi, décisions)
4. 05-data-model.md                  ← les données
5. 06-workflows.md                   ← les parcours
6. specs/02-spec-technique.md        ← les détails techniques
7. specs/03-api-spec.md              ← les contrats d'API
8. 08-module-catalogue.md            ← le module catalogue
9. 07-implementation-roadmap.md      ← le planning
10. annexes/revue-architecture.md    ← les corrections et questions d'architecture
11. annexes/decision-ged.md          ← décision GED (hors périmètre)
```

---

## Conventions

| Règle | Détail |
|-------|--------|
| **Versions** | Le DAT décrit l'**architecture**. Les versions exactes vivent dans `pyproject.toml`, `package.json`, `docker-compose.yml`. |
| **Périmètre** | Les éléments marqués *(phase 2)* sont spécifiés mais **non planifiés**. |
| **Codes API** | Format `XX-NN` (ex. `CLI-01`, `JOB-04`, `AVI-03`). |
| **Stages / sprints / tâches** | Le détail d'exécution est dans `docs/stages/` (`INT-NN`). |
| **Notes pédagogiques** | Dans `notes/` (backend, frontend, deploy, import, interview). |

---

## Synthèse en une page

```
INTERNET
    │
 HTTPS 80/443
    │
┌───▼─────────────┐
│     1Panel      │  reverse proxy (OpenResty) + SSL Let's Encrypt
│  SSL / Routing  │  + file manager + DB GUI + backups + monitoring
└───┬─────────────┘
    │ 127.0.0.1 (aucun service applicatif exposé)
    │
┌───▼──────────────────────────────────────────┐
│  Docker Compose                              │
│   ├── frontend  (Vue.js → Nginx)             │
│   ├── backend   (FastAPI)                    │
│   │    └── Router → Service → Repository     │
│   └── postgres  (healthcheck, aucun port)    │
└──────────────────────────────────────────────┘

PIPELINE D'IMPORT
  Excel → pandas → détection de format → normalisation
        → validation → fuzzy matching (95/80) → 2 passes → transaction/batch
```

**Points d'architecture à retenir :**

1. **Aucun service applicatif exposé** — seul le reverse proxy écoute sur Internet
2. **Healthchecks** — le backend ne démarre qu'une fois PostgreSQL réellement prêt
3. **Import idempotent** — hash SHA-256 + traçabilité ligne à ligne
4. **Fuzzy matching à 3 zones** — l'ambiguïté est validée humainement
5. **Transaction par batch** — jamais une transaction sur l'historique complet
6. **Données jamais ignorées** — les cas non rattachables deviennent des anomalies traçables

---

> **Documents liés hors DAT :**
> - Sprints : `docs/stages/`
> - Notes pédagogiques : `notes/`
> - Revue détaillée : `annexes/revue-architecture.md`
