# Contexte — MB Chauffage DAT (13/07/2026)

> Session de création du DAT MB Chauffage, projet client CVC avec 20+ ans de données.
> **Fin de session** : retour au projet Tervo Sprint 4.1

---

## Décisions d'architecture retenues

### Stack hybride : Swarm + 1Panel

| Composant | Technologie | Rôle |
|-----------|------------|------|
| **Backend** | FastAPI, Python 3.11, SQLAlchemy async | API REST |
| **Frontend** | Vue.js 3, Bun, PrimeVue 4, Zod | SPA mobile-first |
| **Database** | PostgreSQL 17 | Stockage principal |
| **Orchestration** | **Docker Swarm** | Rolling updates, replicas: 2, auto-restart |
| **Reverse proxy** | **1Panel OpenResty** | Routage sous-domaines, Let's Encrypt one-click |
| **Backups** | 1Panel Cron + pg_dump + Hetzner Object Storage | Quotidiens + restore test mensuel |
| **Dev** | Docker Compose | Environnement local |

### Pourquoi 1Panel plutôt que Traefik

1. **Couteau suisse** : Reverse proxy + SSL + File Manager + DB GUI + Backups + Monitoring dans un seul outil
2. **Pas besoin d'apprendre** : déjà maîtrisé sur mini-s1
3. **GUI** : le gérant peut télécharger un PDF, vérifier la DB, voir l'état
4. **Traefik** nécessite Portainer/phpPgAdmin/scripts cron en plus

### Pourquoi Swarm plutôt que Compose

1. **Rolling updates** : zero-downtime (`order: start-first`, `parallelism: 1`)
2. **Self-healing** : Swarm recrée automatiquement les conteneurs morts
3. **Multi-node futur** : un `docker swarm join-token worker` suffit pour scale
4. 1Panel UI ne gère pas Swarm → les services sont déployés en CLI (`docker stack deploy`)

### Architecture réseau

```
internaute → 1Panel OpenResty (ports 80/443)
    ├── mbchauffage.com → localhost:3000 (frontend Swarm)
    ├── api.mbchauffage.com → localhost:8000 (backend Swarm, replicas: 2)
    ├── [futur] pay.mbchauffage.com → localhost:5000
    └── [futur] iq.mbchauffage.com → localhost:5100
```

### Data Model — Nouveautés vs Tervo

- Tables financières : `devis`, `ligne_devis`, `facture`, `ligne_facture`, `bilan`
- Tables d'import : `import_log`, `import_error`
- Extended : `client` (siret, tva_intra, type), `user` (role: comptable), `job` (devis_id, facture_id)

### Roadmap 6 phases

1. **Core + Auth** (Sem 1-2) — Reprise Tervo + rôles
2. **Data Migration** (Sem 3-4) — Import 20 ans d'Excels (pandas + openpyxl + fuzzy matching)
3. **Fonctionnalités** (Sem 5) — Photos, matériaux, PDF, avis
4. **Module Financier** (Sem 6-7) — Devis, Factures, Bilans
5. **Déploiement Prod** (Sem 8) — VPS, 1Panel, Swarm, SSL, Backups
6. **Polish & PWA** (Sem 9-10) — PWA, dark mode, signatures, QR codes

---

## Fichiers créés

```
docs/DAT/MBchauffage-DAT/
├── 04-architecture.md
├── 05-data-model.md
├── 06-workflows.md
├── 07-implementation-roadmap.md
└── specs/
    ├── 01-specs-fonctionnelle.md
    ├── 02-spec-technique.md
    └── 03-api-spec.md
```

---

## Prochaines étapes quand on reviendra dessus

- Phase 1 : Reprendre le code Tervo, adapter les modèles MB Chauffage
- Phase 2 : Récupérer les vrais fichiers Excel, construire le pipeline d'import
- Phase 3 : Déploiement VPS Hetzner CX22
