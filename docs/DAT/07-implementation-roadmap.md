# Tervo — Roadmap d'implémentation

> **Objet :** Plan de développement de Tervo.
>
> **Documents liés :** `specs/02-spec-technique.md`, `specs/01-specs-fonctionnelle.md`

---

## 1. Overview

Développement sur **10 semaines**, en **5 phases**. Stack : FastAPI + Vue.js + PostgreSQL + 1Panel.

```
Phase 1             Phase 2              Phase 3             Phase 4               Phase 5
Core + Auth         Fonctionnalités      First Deploy        Frontend + Tests      Améliorations
Sem 1-2 ✅          Sem 3 ✅             Sem 4               Sem 5                 Sem 6-7
├─ Auth JWT         ├─ Photos            ├─ Dockerfile       ├─ Responsive         ├─ Admin users
├─ Clients CRUD     ├─ Matériaux         ├─ docker-compose   ├─ States/Error       ├─ Notifications
├─ Jobs CRUD        ├─ Rapport PDF       ├─ PostgreSQL       ├─ Transitions        ├─ PWA
├─ Dashboard        ├─ Avis client       ├─ 1Panel config    ├─ E2E Tests          ├─ Dark mode
└─ Start/Complete   └─ 1Panel ready      └─ Coverage ≥80%   └─ Performance        └─ QR codes
```

---

## 2. Phase 1 : Core + Auth (Semaines 1-2) ✅

**Objectif :** Auth JWT + CRUD Clients + CRUD Jobs + workflow start/complete + checklist + dashboard.

### Sprint 1.1 : Base (Semaine 1, Lun-Mer)

| ID     | Tâche                                                               | Points |
| ------ | ------------------------------------------------------------------- | ------ |
| INT-00 | Initialiser Alembic (`alembic init` + config `env.py`)              | 1      |
| INT-01 | Modèle `User` + 1ère migration (`autogenerate` puis `upgrade head`) | 3      |
| INT-02 | `POST /auth/login` + `POST /auth/refresh` (JWT)                     | 3      |
| INT-03 | `GET /auth/me` + `PUT /auth/me`                                     | 2      |
| INT-04 | Modèle `Client` + migration                                         | 2      |
| INT-05 | `GET/POST /clients` + `GET/PUT/DELETE /clients/{id}`                | 5      |
| INT-06 | `GET /clients/{id}/jobs` (historique)                               | 2      |
| INT-07 | Frontend : `LoginPage` + `App.vue` + BottomNav                      | 5      |

### Sprint 1.2 : Jobs (Semaine 1, Jeu-Ven)

| ID     | Tâche                                                | Points |
| ------ | ---------------------------------------------------- | ------ |
| INT-08 | Modèle `Job` + migration                             | 3      |
| INT-09 | `GET/POST /jobs` + `GET/PUT/DELETE /jobs/{id}`       | 5      |
| INT-10 | `PUT /jobs/{id}/start` (démarrer → en_cours + timer) | 3      |
| INT-11 | `PUT /jobs/{id}/complete` (terminer → validations)   | 5      |
| INT-12 | `GET /dashboard/summary` (jobs du jour, timer)       | 3      |
| INT-13 | Frontend : `DashboardPage` (jobs du jour + boutons)  | 5      |
| INT-14 | Frontend : `JobListPage` (filtre statut/date)        | 5      |
| INT-15 | Frontend : `JobDetailPage` (fiche avec onglets)      | 5      |
| INT-16 | Frontend : `ClientListPage` + `ClientDetailPage`     | 5      |

### Sprint 1.3 : Checklist (Semaine 2, Lun-Mer)

| ID     | Tâche                                                        | Points |
| ------ | ------------------------------------------------------------ | ------ |
| INT-17 | Modèle `ChecklistItem` + migration + seed items par défaut   | 3      |
| INT-18 | `GET /jobs/{id}/checklist` + `PUT /jobs/{id}/checklist/{id}` | 3      |
| INT-19 | `PUT /jobs/{id}/checklist/batch`                             | 3      |
| INT-20 | Frontend : `InspectionPage` (checklist pré/post)             | 8      |
| INT-21 | Validation : checklist requise pour terminer                 | 3      |

**Livrables Phase 1 :**

- ✅ Auth JWT
- ✅ CRUD Clients + historique
- ✅ CRUD Jobs + workflow start/complete
- ✅ Checklist inspection pré/post
- ✅ Dashboard du jour (jobs, timer)
- ✅ Frontend : Login, BottomNav, Dashboard, Clients, Jobs, Inspection

---

## 3. Phase 2 : Fonctionnalités (Semaine 3) ✅

**Objectif :** Upload photos, matériaux, génération PDF rapport, avis client public.

### Sprint 2.1 : Photos & Matériaux (Semaine 3, Lun-Mer)

| ID     | Tâche                                                    | Points |
| ------ | -------------------------------------------------------- | ------ |
| INT-22 | Modèle `JobPhoto` + migration + stockage fichiers        | 3      |
| INT-23 | `POST /jobs/{id}/photos` (multipart + thumbnail)         | 5      |
| INT-24 | `DELETE /jobs/{id}/photos/{id}`                          | 2      |
| INT-25 | Modèle `Material` + migration                            | 2      |
| INT-26 | `GET/POST /jobs/{id}/materials` + `PUT/DELETE`           | 3      |
| INT-27 | Frontend : Upload photo (appareil natif + galerie)       | 5      |
| INT-28 | Frontend : `MaterialsForm` (ajout/suppression dynamique) | 3      |

### Sprint 2.2 : Rapport PDF + Avis (Semaine 3, Jeu-Ven)

| ID     | Tâche                                                        | Points |
| ------ | ------------------------------------------------------------ | ------ |
| INT-29 | Génération PDF rapport (WeasyPrint + template HTML)          | 8      |
| INT-30 | `GET /jobs/{id}/report/download`                             | 3      |
| INT-31 | Modèle `Review` + migration                                  | 2      |
| INT-32 | `GET /review/{share_token}` (public, no auth)                | 2      |
| INT-33 | `POST /review/{share_token}/submit` (public)                 | 3      |
| INT-34 | Génération `share_token` automatique à la complétion         | 2      |
| INT-35 | Frontend : `ReportPreviewPage`                               | 3      |
| INT-36 | Frontend : `ReviewPage` publique (star rating + commentaire) | 5      |
| INT-37 | Tests API : photos, matériaux, rapport, avis                 | 5      |

**Livrables Phase 2 :**

- ✅ Upload photos avant/après avec thumbnails
- ✅ Saisie matériaux
- ✅ Rapport PDF généré automatiquement
- ✅ Avis client via lien public sans auth
- ✅ Première itération Helloworld 1Panel (tests de déploiement avec 1Panel)

---

## 4. Phase 3 : First Deploy (Semaine 4)

**Objectif :** Mise en production via 1Panel. Docker multi-stage, PostgreSQL dédié, premier déploiement.

### Sprint 3.1 : First Deploy via 1Panel (Semaine 4, Lun-Ven)

| ID      | Tâche                                                      | Points |
| ------- | ---------------------------------------------------------- | ------ |
| INT-48  | Dockerfile backend multi-stage (uv → deps → app)           | 3      |
| INT-49  | docker-compose.yml (backend + frontend, reverse proxy 1Panel) | 5   |
| INT-50  | Volume persistant uploads + connexion PostgreSQL existant   | 2      |
| INT-51  | Seed script : utilisateurs + données demo                  | 3      |
| INT-45  | Tests API coverage ≥ 80%                                   | 5      |
| INT-47  | Validation formulaires (Zod + VeeValidate)                 | 3      |
| INT-DPL | Config 1Panel : build image, DB, reverse proxy, var env    | 5      |
| INT-DOC | Documentation déploiement (procédure 1Panel)               | 3      |

**Livrables Phase 3 :**

- [ ] Application déployée via 1Panel accessible en IP:port
- [ ] PostgreSQL `tervo_db` créée et connectée
- [ ] Uploads volume persistant monté
- [ ] Seed données : admin + technicien + données demo
- [ ] Dockerfile multi-stage opérationnel
- [ ] Coverage ≥ 80%
- [ ] Validation formulaires (Zod) active
- [ ] Documentation déploiement livrée

---

## 5. Phase 4 : Frontend + Tests (Semaine 5)

**Objectif :** Finitions frontend mobile, E2E Playwright, performance, documentation.

### Sprint 4.1 : Frontend mobile (Semaine 5, Lun-Mer)

| ID     | Tâche                                                       | Points |
| ------ | ----------------------------------------------------------- | ------ |
| INT-38 | Responsive mobile (layout bottom nav, plein écran)          | 5      |
| INT-39 | Gestion états Loading/Empty/Error toutes pages              | 5      |
| INT-40 | Animations transitions pages                                | 2      |
| INT-41 | Création rapide client depuis formulaire job                | 3      |
| INT-42 | Navigation contextuelle (clic dashboard → job → inspection) | 3      |

### Sprint 4.2 : Tests & Perf (Semaine 5, Jeu-Ven)

| ID     | Tâche                                                                                                     | Points |
| ------ | --------------------------------------------------------------------------------------------------------- | ------ |
| INT-43 | Tests E2E Playwright : login → créer client → créer job → start → checklist → photos → complete → rapport | 8      |
| INT-44 | Tests E2E : avis client (lien public → note → submit)                                                     | 3      |
| INT-46 | Performance : N+1 queries, index manquants                                                                | 3      |
| INT-52 | Documentation utilisateur (guide + captures)                                                              | 5      |
| INT-53 | Documentation API (Swagger/OpenAPI enrichi)                                                               | 2      |

**Livrables Phase 4 :**

- [ ] Application responsive mobile (testée iPhone SE → Galaxy S22)
- [ ] États Loading/Empty/Error sur toutes les pages
- [ ] Transitions fluides entre pages
- [ ] Création rapide client + job en un clic
- [ ] Navigation contextuelle (Dashboard → Job → Inspection)
- [ ] Tests E2E Playwright couvrant les workflows principaux
- [ ] Performance : N+1 queries résolues, index optimisés
- [ ] Documentation utilisateur + API livrées

---

## 6. Phase 5 : Améliorations (Semaines 6-7)

**Objectif :** Admin utilisateurs, notifications, logs d'audit, PWA, dark mode, QR codes.

### Sprint 5.1 : Admin & Notifications (Semaine 6)

| ID     | Tâche                                        | Points |
| ------ | -------------------------------------------- | ------ |
| INT-56 | `GET/POST/PUT /admin/users`                  | 5      |
| INT-57 | `DELETE /admin/users/{id}` (soft-delete)     | 2      |
| INT-58 | `POST /admin/register` (création technicien) | 3      |
| INT-59 | Frontend : `UserManagementPage`              | 5      |
| INT-60 | Logs d'audit (qui a fait quoi, quand)        | 3      |

### Sprint 5.2 : Polish & PWA (Semaine 7)

| ID     | Tâche                                             | Points |
| ------ | ------------------------------------------------- | ------ |
| INT-61 | PWA : service worker + manifest + offline basique | 5      |
| INT-62 | Dark mode                                         | 3      |
| INT-63 | QR code pour lien avis                            | 3      |
| INT-64 | Cache offline : derniers jobs téléchargés         | 5      |
| INT-65 | Revue de sécurité + nettoyage                     | 3      |

**Livrables Phase 5 :**

- [ ] CRUD utilisateurs (admin)
- [ ] Logs d'audit
- [ ] PWA basique (service worker)
- [ ] Dark mode
- [ ] QR code pour avis client

---

## 7. Dépendances

```
Phase 1 (Core + Auth) ✅
    ↓
Phase 2 (Fonctionnalités) ✅  ← dépend de Phase 1
    ↓
Phase 3 (First Deploy)         ← dépend de Phase 1 + 2
    ↓
Phase 4 (Frontend + Tests)     ← dépend de Phase 3 (déploiement requis pour E2E)
    ↓
Phase 5 (Améliorations)        ← dépend de Phase 1 + 2 + 3 + 4
```

---

## 8. Équipe

| Rôle              | Allocation | Responsabilités                                     |
| ----------------- | ---------- | --------------------------------------------------- |
| **Dev Backend**   | 100%       | FastAPI, API, services, modèles, génération PDF     |
| **Dev Frontend**  | 100%       | Vue.js, composants, Pinia, Vue Query, upload photos |
| **Dev Fullstack** | 50%        | Docker, 1Panel, déploiement, tests E2E              |
| **QA/Doc**        | 50%        | Tests, documentation utilisateur, recette           |

| Phase | Durée | ETP |
|-------|-------|-----|
| Phase 1 | 2 semaines | 2.5 |
| Phase 2 | 1 semaine | 2.5 |
| Phase 3 | 1 semaine | 2.0 |
| Phase 4 | 1 semaine | 2.0 |
| Phase 5 | 2 semaines | 1.5 |
| **Total** | **7 semaines** | **2.1 avg** |

---

## 9. Risques

| Risque                                | Prob. | Impact | Mitigation                                 |
| ------------------------------------- | ----- | ------ | ------------------------------------------ |
| Upload photos volumineuses (4G lente) | Moyen | Moyen  | Compression côté client avant upload       |
| Génération PDF avec photos            | Moyen | Moyen  | WeasyPrint OK (testé en Phase 2)           |
| Mode hors-ligne complexe              | Moyen | Élevé  | Scope offline en P5, cache basique d'abord |
| Retard planning                       | Moyen | Élevé  | Buffer 20%, scope P4/P5 ajustable          |
| 1Panel build complexe                 | Faible | Moyen | POC 1Panel déjà validé en Phase 2          |
| Connexion PostgreSQL existant         | Faible | Moyen | Container dédié séparé, réseau bridge      |

---

## 10. Critères de succès

### Phase 1 (Semaine 2) ✅

- [x] Auth JWT fonctionnelle
- [x] CRUD Clients API opérationnel
- [x] CRUD Jobs + start/complete opérationnel
- [x] Checklist pré/post fonctionnelle
- [x] Dashboard du jour (jobs, timer)

### Phase 2 (Semaine 3) ✅

- [x] Upload photos avant/après fonctionnel
- [x] Saisie matériaux fonctionnelle
- [x] Rapport PDF téléchargeable
- [x] Avis client via lien public
- [x] Tests API ≥ 60%

### Phase 3 (Semaine 4)

- [ ] Déploiement 1Panel opérationnel
- [ ] Coverage ≥ 80%
- [ ] Docker multi-stage prêt
- [ ] Documentation déploiement livrée

### Phase 4 (Semaine 5)

- [ ] Application responsive mobile
- [ ] Tests E2E passent
- [ ] États Loading/Empty/Error partout
- [ ] Documentation utilisateur livrée

### Phase 5 (Semaine 7)

- [ ] Admin utilisateurs
- [ ] PWA basique (offline)
- [ ] Dark mode
- [ ] QR codes avis

---

> **Document mis à jour le 25/06/2026**
> **Version :** 4.0 (Restructuration 5 phases + 1Panel)
> **Documents liés :** `specs/02-spec-technique.md`, `specs/01-specs-fonctionnelle.md`
