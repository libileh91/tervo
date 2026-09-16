# MB Chauffage — Roadmap d'implémentation

> **Objet :** Plan de développement de MB Chauffage.
>
> **Documents liés :** `specs/02-spec-technique.md`, `specs/01-specs-fonctionnelle.md`

---

## 1. Overview

Développement sur **10 semaines** (estimation), en **6 phases**. Stack : FastAPI + Vue.js + PostgreSQL + 1Panel + Docker Swarm.

L'ordre des phases est **repensé pour MB Chauffage** : l'import des données Excel est prioritaire car c'est le prérequis bloquant — inutile de développer des features si les données historiques ne sont pas dans le système.

```
Phase 1             Phase 2               Phase 3              Phase 4               Phase 5              Phase 6
Core + Auth         Data Migration        Fonctionnalités       Module Financier      Deploy Prod          Polish & PWA
Sem 1-2             Sem 3-4               Sem 5                Sem 6-7               Sem 8                Sem 9-10
├─ Auth JWT         ├─ Import Excel       ├─ Photos             ├─ Devis              ├─ VPS setup          ├─ PWA
├─ Clients CRUD     ├─ Mapping colonnes   ├─ Matériaux          ├─ Factures           ├─ 1Panel proxy/SSL  ├─ Dashboard financier
├─ Jobs CRUD        ├─ Fuzzy matching     ├─ Rapport PDF        ├─ Bilans             ├─ Swarm orchestre    ├─ Notifications
├─ Checklist        ├─ Validation         ├─ Avis client        ├─ Génération PDF     ├─ Backups (1Panel)  ├─ QR codes
├─ Dashboard        └─ Rapport import     └─ Seed real data     └─ Workflow devis→    └─ Rolling updates    └─ Dark mode
└─ Seed demo
```

---

## 2. Phase 1 : Core + Auth (Semaines 1-2)

**Objectif :** Reprendre le socle Tervo existant, adapter les modèles pour MB Chauffage, seed avec données demo.

### Sprint 1.1 : Setup & Auth (Semaine 1)

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-01 | Initialiser Alembic + config env.py (PostgreSQL) | 1 | Pas de SQLite — direct PostgreSQL |
| MB-02 | Modèle `User` + migration (rôles : technician, admin, comptable) | 3 | Ajout rôle `comptable` |
| MB-03 | `POST /auth/login` + `POST /auth/refresh` (JWT) | 3 | Reprise Tervo |
| MB-04 | `GET /auth/me` + `PUT /auth/me` | 2 | Reprise Tervo |
| MB-05 | Frontend : `LoginPage` + `App.vue` + BottomNav | 5 | Reprise Tervo, adapter branding MB Chauffage |

### Sprint 1.2 : Clients & Jobs (Semaine 2)

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-06 | Modèle `Client` + migration (ajout siret, tva_intra, type) | 2 | Extension du modèle Tervo |
| MB-07 | CRUD Clients + historique | 5 | Reprise Tervo |
| MB-08 | Modèle `Job` + migration (ajout devis_id, facture_id FK) | 3 | Extension |
| MB-09 | CRUD Jobs + workflow start/complete | 8 | Reprise Tervo |
| MB-10 | Checklist + Dashboard | 5 | Reprise Tervo |
| MB-11 | Frontend : Clients, Jobs, Dashboard, Inspection | 13 | Reprise Tervo, adapter |
| MB-12 | Seed script : utilisateurs + 5 clients + 5 jobs demo | 3 | Utiliser données réalistes CVC |

**Livrables Phase 1 :**

- [ ] Auth JWT avec rôle `comptable`
- [ ] CRUD Clients (avec SIRET/TVA) + CRUD Jobs
- [ ] Checklist pré/post + Dashboard
- [ ] Frontend complet (Login, BottomNav, Dashboard, Clients, Jobs, Inspection)
- [ ] Seed demo avec données CVC réalistes

---

## 3. Phase 2 : Data Migration (Semaines 3-4) ⚡ PRIORITAIRE

**Objectif :** Importer 20 ans de données Excel dans PostgreSQL. C'est le cœur de la valeur pour MB Chauffage.

### Sprint 2.1 : Pipeline import (Semaine 3)

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-13 | Modèles `ImportLog` + `ImportError` + migration | 2 | Tables de logging |
| MB-14 | Service `ImportService` : parse Excel → pandas DataFrame | 5 | openpyxl + pandas |
| MB-15 | Détection automatique du mapping des colonnes | 5 | Algorithme de matching |
| MB-16 | Fuzzy matching clients (dédoublonnage) | 5 | `difflib` ou `rapidfuzz` |
| MB-17 | `POST /admin/import/preview` (aperçu 10 lignes) | 3 | |
| MB-18 | `POST /admin/import/validate` (validation complète) | 5 | Analyse sans insertion |
| MB-19 | `POST /admin/import/execute` (import réel en 2 passes) | 8 | Clients → Jobs → Devis |

### Sprint 2.2 : Import UI + Tests (Semaine 4)

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-20 | Frontend : Page `AdminImportPage` (upload, preview, mapping) | 8 | Interface drag & drop |
| MB-21 | Frontend : Résolution manuelle des doublons | 5 | UI pour valider/rejeter les matchs |
| MB-22 | Frontend : Rapport d'import (succès, erreurs, stats) | 5 | |
| MB-23 | Tests import : fichiers Excel de test (10/100/1000 lignes) | 5 | Valider l'idempotence |
| MB-24 | **Import réel : exécuter sur les vrais fichiers MB Chauffage** | 3 | **Livrable clé** |

**Livrables Phase 2 :**

- [ ] Pipeline import Excel opérationnel (pandas + openpyxl)
- [ ] Détection automatique du mapping
- [ ] Fuzzy matching pour dédoublonnage clients
- [ ] Interface admin d'import (upload → preview → validate → execute)
- [ ] Rapport d'import détaillé
- [ ] **Données historiques MB Chauffage importées dans PostgreSQL** ✅

---

## 4. Phase 3 : Fonctionnalités terrain (Semaine 5)

**Objectif :** Upload photos, matériaux, génération PDF rapport, avis client.

Identique à la Phase 2 de Tervo (`Tervo/docs/DAT/07-implementation-roadmap.md`, section 3).

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-25 | Modèle `JobPhoto` + upload multipart + thumbnails | 5 | Reprise Tervo |
| MB-26 | Modèle `Material` + CRUD | 3 | Reprise Tervo |
| MB-27 | Génération PDF rapport (WeasyPrint) | 8 | Reprise Tervo |
| MB-28 | Modèle `Review` + endpoints publics | 5 | Reprise Tervo |
| MB-29 | Frontend : Upload photos, matériaux, inspection | 8 | Reprise Tervo |
| MB-30 | Frontend : ReportPreview, ReviewPage | 5 | Reprise Tervo |
| MB-31 | Tests API : photos, matériaux, rapport, avis | 5 | |

**Livrables Phase 3 :**

- [ ] Upload photos avant/après avec thumbnails
- [ ] Saisie matériaux
- [ ] Rapport PDF généré automatiquement
- [ ] Avis client via lien public

---

## 5. Phase 4 : Module Financier (Semaines 6-7)

**Objectif :** Devis, Factures, Bilans mensuels. Le vrai "plus" par rapport à Tervo.

### Sprint 4.1 : Devis (Semaine 6)

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-32 | Modèles `Devis` + `LigneDevis` + migration | 3 | |
| MB-33 | CRUD Devis + lignes | 5 | |
| MB-34 | Génération PDF devis (WeasyPrint, template pro) | 5 | En-tête MB Chauffage, logo |
| MB-35 | Workflow statuts devis (brouillon → envoyé → accepté/refusé) | 3 | |
| MB-36 | Frontend : `DevisListPage` + `DevisCreatePage` | 8 | Lignes dynamiques |

### Sprint 4.2 : Factures & Bilans (Semaine 7)

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-37 | Modèles `Facture` + `LigneFacture` + migration | 3 | |
| MB-38 | CRUD Factures + lignes | 5 | |
| MB-39 | Transformation devis → facture (auto) | 3 | |
| MB-40 | Génération PDF facture | 5 | |
| MB-41 | Suivi paiements (statuts, dates, relances) | 5 | |
| MB-42 | Modèle `Bilan` + CRON mensuel (calcul automatique) | 5 | Agrégation SQL |
| MB-43 | Frontend : `FactureListPage`, `BilanDashboard` | 8 | Graphiques, KPIs |
| MB-44 | Tests module financier | 5 | |

**Livrables Phase 4 :**

- [ ] CRUD Devis avec génération PDF
- [ ] CRUD Factures avec workflow devis → facture
- [ ] Bilans mensuels automatisés (agrégation CRON)
- [ ] Dashboard financier (KPIs, graphiques)
- [ ] Suivi des paiements et relances

---

## 6. Phase 5 : Déploiement Production (Semaine 8)

**Objectif :** Mise en production sur VPS avec stack hybride : Swarm orchestre les conteneurs, 1Panel gère le reverse proxy + SSL + backups.

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-45 | Provisionner VPS Hetzner CX22 (Ubuntu 24.04) | 2 | Commande, SSH, sécurité de base |
| MB-46 | Installer Docker + Swarm init (`docker swarm init`) | 2 | |
| MB-47 | Installer et configurer 1Panel | 2 | curl install, config UI initiale |
| MB-48 | Dockerfiles multi-stage (backend, frontend) | 3 | Reprise Tervo |
| MB-49 | docker-stack.yml production (Swarm, replicas: 2, rolling updates) | 5 | Services + overlay network |
| MB-50 | Configurer les sites reverse proxy dans 1Panel | 2 | mbchauffage.com → localhost:3000, api.→ :8000 |
| MB-51 | SSL Let's Encrypt via 1Panel (one-click par site) | 1 | 1Panel → Websites → HTTPS → Enable |
| MB-52 | Config DNS (mbchauffage.com → IP VPS) | 1 | Pointez mbchauffage.com, api.*, docs.* vers l'IP |
| MB-53 | Script backup quotidien (pg_dump + s3cmd) via 1Panel Cron | 2 | Interface Cron Jobs 1Panel |
| MB-54 | Script restore-test mensuel via 1Panel Cron | 2 | |
| MB-55 | Firewall (ufw) + fail2ban | 2 | Ports 22, 80, 443, 7410 |
| MB-56 | Monitoring (UptimeRobot + 1Panel dashboard) | 1 | |
| MB-57 | CI/CD : GitHub Actions → build → docker stack deploy | 3 | Rolling update automatique |
| MB-58 | Installer et configurer Paperless-ngx (Docker Compose) | 3 | OCR documents, archivage devis/factures/rapports |
| MB-59 | Intégration API Paperless (export auto des PDF depuis l'app) | 5 | Service PaperlessService + endpoint |
| MB-60 | Configurer docs.mbchauffage.com dans 1Panel | 1 | Reverse proxy + SSL Let's Encrypt |

**Livrables Phase 5 :**

- [ ] VPS provisionné et sécurisé
- [ ] Docker Swarm initialisé (1 nœud manager)
- [ ] 1Panel installé (proxy, SSL, backups, file manager, DB GUI)
- [ ] docker-stack.yml prêt avec replicas: 2 + rolling updates
- [ ] Application déployée via Swarm
- [ ] Sites 1Panel configurés (mbchauffage.com, api.mbchauffage.com)
- [ ] SSL Let's Encrypt actif (one-click 1Panel)
- [ ] Backups quotidiens + test mensuel (via 1Panel Cron)
- [ ] Paperless-ngx installé et accessible sur docs.mbchauffage.com
- [ ] CI/CD automatisée (build → stack deploy → rolling update)
- [ ] https://mbchauffage.com accessible

---

## 7. Phase 6 : Polish & PWA (Semaines 9-10)

**Objectif :** Finitions UX, PWA, dark mode, signatures, QR codes.

| ID | Tâche | Points | Notes |
|----|-------|--------|-------|
| MB-57 | PWA (service worker, manifest, installable) | 5 | |
| MB-58 | Responsive mobile (testé sur devices réels) | 5 | |
| MB-59 | Dark mode | 3 | |
| MB-60 | Signature client dans le rapport PDF | 5 | Canvas HTML → PNG → PDF |
| MB-61 | QR code pour lien avis | 3 | |
| MB-62 | États Loading/Empty/Error toutes pages | 5 | |
| MB-63 | Dashboard financier (version admin/comptable) | 8 | |
| MB-64 | Performance : N+1 queries, index | 3 | |
| MB-65 | Tests E2E Playwright (workflow complet) | 8 | |
| MB-66 | Documentation utilisateur (guide + captures) | 5 | |

**Livrables Phase 6 :**

- [ ] PWA installable
- [ ] Dark mode
- [ ] Signature client dans les rapports
- [ ] QR codes pour avis
- [ ] Tests E2E
- [ ] Documentation utilisateur livrée

---

## 8. Dépendances

```
Phase 1 (Core + Auth)
    ↓
Phase 2 (Data Migration)  ← dépend de Phase 1 (clients, jobs existent)
    ↓
Phase 3 (Fonctionnalités)  ← dépend de Phase 2 (données réelles dispo)
    ↓
Phase 4 (Module Financier)  ← dépend de Phase 1 + 2 + 3
    ↓
Phase 5 (Deploy Prod)       ← dépend de Phase 1-4 (l'app est prête)
    ↓
Phase 6 (Polish & PWA)      ← dépend de Phase 5 (prod pour tests réels)
```

---

## 9. Différences clés avec la roadmap Tervo

| Aspect | Tervo | MB Chauffage |
|--------|-------|--------------|
| **Phase Data Migration** | Aucune (seed demo uniquement) | Phase 2 entière dédiée |
| **Module Financier** | Non prévu | Phase 4 entière (devis, factures, bilans) |
| **Base de données dev** | SQLite → PostgreSQL | PostgreSQL uniquement (pas de SQLite) |
| **Orchestration** | Docker Compose | **Docker Swarm** (rolling updates, replicas: 2) |
| **Reverse Proxy** | Cloudflare Tunnel | **1Panel OpenResty** |
| **Backups** | Non | Quotidiens + test mensuel (via 1Panel Cron) |
| **Environnement** | Serveur domestique | VPS professionnel |
| **Rôles utilisateurs** | technician, admin | technician, admin, **comptable** |
| **CI/CD** | Build simple | Build + `docker stack deploy` → rolling update |

---

## 10. Risques

| Risque | Prob. | Impact | Mitigation |
|--------|-------|--------|------------|
| Formats Excel incompatibles / trop dégradés | Élevé | Élevé | Phase 2 prévoit un mapping manuel + preview avant import |
| Données perdues lors de l'import | Moyen | Critique | Validation en 2 passes + rapport détaillé + backup avant import |
| Volume de données (20 ans) impacte les perfs | Moyen | Moyen | Pagination, index PostgreSQL, requêtes optimisées |
| Résistance au changement (techniciens) | Moyen | Élevé | Interface simple, mobile-first, formation, période de transition |
| Déploiement Docker insuffisant à terme | Faible | Faible | Docker Compose suffit pour le volume prévu ; ajout de nœuds possible si croissance |
| Coût VPS + Object Storage | Faible | Faible | ~12 €/mois total, négligeable vs. gain de productivité |

---

> **Document mis à jour le 12/07/2026**
> **Version :** 1.0 (DAT MB Chauffage)
> **Projet source :** `Tervo/docs/DAT/07-implementation-roadmap.md`
> **Documents liés :** `specs/02-spec-technique.md`, `specs/01-specs-fonctionnelle.md`
