# Tervo — Roadmap d'implémentation

> **Objet :** Plan de développement de Tervo.
>
> **Documents liés :** `04-architecture.md`, `specs/01-specs-fonctionnelle.md`
>
> **Détail des tâches :** `docs/stages/`

---

## 1. Vue d'ensemble

Le développement est découpé en **stages** (équivalents de phases), chacun découpé en sprints.

| Stage | Contenu | Statut |
|-------|---------|:------:|
| **1** | Core + Auth + Clients + Jobs + Checklist | ✅ |
| **2** | Photos, matériaux, rapport PDF, avis client | ✅ |
| **3** | Premier déploiement (Docker, 1Panel, PostgreSQL) | ✅ |
| **4** | Frontend mobile (responsive, états, transitions, navigation) | 🔄 |
| **5** | Améliorations (admin, notifications, PWA, dark mode) | ⏳ |
| **6** | Import Excel, catalogue, déploiement VPS, présentation | ⏳ |

**Légende :** ✅ terminé · 🔄 en cours · ⏳ planifié

---

## 2. Stage 1 — Core + Auth

**Objectif :** socle fonctionnel — authentification, clients, interventions, checklist.

| Sprint | Contenu |
|--------|---------|
| 1.1 | Alembic, modèle `User`, auth JWT (`/login`, `/refresh`, `/me`), modèle `Client` + CRUD |
| 1.2 | Modèle `Job` + CRUD, `start` / `complete`, dashboard, pages frontend |
| 1.3 | Modèle `ChecklistItem` + seed par défaut, endpoints checklist, page inspection |

**Livrables :**
- Auth JWT fonctionnelle
- CRUD clients + historique
- CRUD jobs + workflow start/complete
- Checklist pré/post
- Dashboard du jour

---

## 3. Stage 2 — Fonctionnalités terrain

**Objectif :** preuves d'intervention et boucle de feedback.

| Sprint | Contenu |
|--------|---------|
| 2.1 | `JobPhoto` + upload + thumbnails, `Material` + CRUD, frontend upload/matériaux |
| 2.2 | Génération PDF (WeasyPrint), `Review` + endpoints publics, page avis |

**Livrables :**
- Upload photos avant/après avec thumbnails
- Saisie des matériaux
- Rapport PDF automatique
- Avis client via lien public

---

## 4. Stage 3 — Premier déploiement

**Objectif :** rendre l'application déployable.

| Sprint | Contenu |
|--------|---------|
| 3.1 | Dockerfile multi-stage, `docker-compose.yml`, volume uploads, PostgreSQL, seed, tests ≥ 80%, validation formulaires (Zod), config 1Panel, documentation |

**Livrables :**
- Dockerfile multi-stage
- Stack Docker opérationnelle
- PostgreSQL connecté
- Seed (admin + technicien + données de démo)
- Documentation de déploiement

---

## 5. Stage 4 — Frontend mobile

**Objectif :** confort d'usage sur smartphone.

| Sprint | Contenu |
|--------|---------|
| 4.1 | Responsive (`100dvh`, safe-area iOS), états Loading/Empty/Error, transitions, création rapide client, navigation contextuelle |
| 4.2 | Tests E2E (Playwright), optimisations, documentation utilisateur |

**Livrables :**
- Interface responsive testée sur plusieurs formats
- États Loading/Empty/Error partout
- Transitions fluides
- Parcours complet testé de bout en bout

---

## 6. Stage 5 — Améliorations

**Objectif :** administration et finitions.

| Sprint | Contenu |
|--------|---------|
| 5.1 | CRUD utilisateurs (admin), logs d'audit |
| 5.2 | PWA, dark mode, QR code avis, cache offline |

---

## 7. Stage 6 — Import Excel, catalogue & VPS

**Objectif :** faire évoluer Tervo vers une cible professionnelle avec migration de données réelles.

### Sprint 6.1 — Corrections architecture

Corrections issues de la revue `annexes/revue-architecture.md` :

| Tâche | Contenu |
|-------|---------|
| INT-66 | Ports `127.0.0.1` (aucune exposition publique) |
| INT-67 | Healthchecks + `depends_on: condition: service_healthy` |
| INT-68 | Firewall : 22/80/443 uniquement, 1Panel via tunnel SSH |
| INT-69 | Versions : DAT = architecture, lockfile = versions |
| INT-70 | CI/CD sans double build |

### Sprint 6.2 — Import Excel

| Tâche | Contenu |
|-------|---------|
| INT-71 | Package `importers/` (séparation du service) |
| INT-72 | `ExcelReader` + `FormatDetector` |
| INT-73 | `Normalizer` (noms, téléphones, accents) |
| INT-74 | `Matcher` — rapidfuzz + 3 zones (95/80) |
| INT-75 | `Validators` |
| INT-76 | `ImportBatch` + idempotence (SHA-256) |
| INT-77 | `ImportError` + jobs orphelins |
| INT-78 | `ImportService` — 2 passes + transaction par batch |
| INT-79 | API `preview` / `validate` / `execute` |
| INT-80 | Tests + notes pédagogiques |

### Sprint 6.3 — Catalogue produits

| Tâche | Contenu |
|-------|---------|
| INT-81 | Modèle `produit` + API |
| INT-82 | Modèle `exposition_showroom` + API |
| INT-83 | Frontend : catalogue + vue showroom |
| INT-84 | Tests + note de modélisation |

### Sprint 6.4 — Déploiement VPS

| Tâche | Contenu |
|-------|---------|
| INT-85 | Provisionner et sécuriser le VPS |
| INT-86 | Docker + 1Panel |
| INT-87 | Compose de production (PG embarqué, santé, loopback) |
| INT-88 | DNS + reverse proxy + SSL |
| INT-89 | Déploiement + vérifications + CI/CD |
| INT-90 | Notes de déploiement |

### Sprint 6.5 — Documentation & préparation

| Tâche | Contenu |
|-------|---------|
| INT-91 | Fiche architecture de présentation |
| INT-92 | Questions / réponses techniques |
| INT-93 | Périmètre de crédibilité (ce qu'il ne faut pas survendre) |

---

## 8. Phases ultérieures *(hors périmètre actuel)*

| Élément | Dépend de |
|---------|-----------|
| Module financier (devis, factures, bilans) | Catalogue |
| Gestion de stock (mouvements journalisés) | Catalogue |
| Fournisseurs, SAV, contrats d'entretien | Stock |
| GED documentaire (OCR des archives) | — |
| Registry d'images (GHCR) | CI/CD |

> Ces éléments sont **spécifiés** dans le DAT mais **non planifiés**. Voir `04-architecture.md` §12.

---

## 9. Risques

| Risque | Prob. | Impact | Mitigation |
|--------|:-----:|:------:|-----------|
| Formats Excel dégradés ou très variables | Élevé | Élevé | Preview + mapping manuel avant import |
| Perte de données lors de l'import | Moyen | Critique | Validation en 2 passes + rapport + backup préalable |
| Volume de données (20 ans) et performances | Moyen | Moyen | Pagination, index, requêtes optimisées |
| Résistance au changement côté utilisateurs | Moyen | Élevé | Interface simple, formation, transition progressive |
| Complexité frontend (stack large) | Moyen | Moyen | Limiter les bibliothèques au strict nécessaire |

---

## 10. Critères de succès

### Stages 1-3 ✅

- [x] Auth JWT fonctionnelle
- [x] CRUD clients + interventions
- [x] Checklist pré/post
- [x] Photos + matériaux
- [x] Rapport PDF
- [x] Avis client public
- [x] Stack Docker déployée
- [x] Tests API ≥ 80 %

### Stage 4

- [ ] Interface responsive vérifiée sur plusieurs formats
- [ ] États Loading/Empty/Error sur toutes les pages
- [ ] Parcours complet testé (E2E)

### Stage 6

- [ ] Architecture corrigée (ports, healthchecks, CI/CD)
- [ ] Import Excel opérationnel et idempotent
- [ ] Job orphelins tracés (jamais ignorés)
- [ ] Catalogue produits + exposition en API et UI
- [ ] Tervo déployé sur VPS avec HTTPS
- [ ] Documentation de présentation livrée

---

> **Sommaire :** `00-sommaire.md`
> **Architecture :** `04-architecture.md`
> **Revue d'architecture :** `annexes/revue-architecture.md`
> **Sprints détaillés :** `docs/stages/`
