Challenge accepted ! Après avoir analysé la matrice comparative de DeepSeek, j'ai identifié mes lacunes : ma première version était trop **linéaire et modulaire** (approche "silos"). Pour un technicien sur le terrain, ça n'a pas de sens de coder 100% des clients avant de coder 1% des jobs.

Pour me dépasser, j'adopte l'approche architecturale de DeepSeek (**arbitrages stratégiques**) mais je la pousse plus loin avec une **découpe verticale en "Thin Slices"** (tranches de bout en bout). L'objectif : livrer du valeur métier à chaque phase, et intégrer la contrainte majeure du spécification (le mode hors-ligne) dès le cœur du projet.

Voici la **Roadmap 08 corrigée et optimisée**.

---

# 🗺️ 08-roadmap-v2.md — Tervo (MVP "Thin-Slice" & Offline-Ready)

> **Stratégie :** Découpage vertical (End-to-End Workflow). Chaque phase livre un flux complet utilisable par le technicien, plutôt qu'un module figé. Intégration de l'architecture hors-ligne dès la Phase 3.

---

## 📌 Phase 1 : Fondations & Setup (Jour 1)

**Focus :** Squelette, CI/CD, Migrations DB (Alembic obligatoire dès l'init) et Auth.

### 🛠 Backend

- Init FastAPI + SQLAlchemy 2.0 + Pydantic V2 + **Alembic** (config `env.py` + `Base.metadata`)
- Modèles `User` + 1ère migration `alembic revision --autogenerate`
- Auth JWT (`/login`, `/refresh`, `/me`)

### 🖥 Frontend

- Init Vue 3 + Vite + **Bun** + TypeScript
- Setup PrimeVue 4, PrimeFlex, Vue Router, Pinia, Vue Query
- Page `LoginPage` + Store `authStore`

### 🚀 Déploiement & DevOps

- Git init + Docker Compose (FastAPI + PostgreSQL + 1Panel)
- Pipeline GitHub Actions (Lint, Test, Build)

### 🧪 Cas de tests (Phase 1)

| ID   | Test                                                     | Type    |
| ---- | -------------------------------------------------------- | ------- |
| T1.1 | `alembic upgrade head` s'exécute sans erreur sur DB vide | Backend |
| T1.2 | `/me` retourne 401 sans JWT valide                       | API     |
| T1.3 | Le pipeline CI bloque si `pytest` échoue                 | DevOps  |

---

## 📌 Phase 2 : Flux "Arrivée sur site" (Client + Job + Start)

**Focus :** Le technicien peut chercher un client, créer un job urgent et le démarrer (déclenche le timer).

### 🛠 Backend

- Modèles `Client`, `Job` (Status/Priority Enums)
- CRUD Clients + Jobs
- Endpoint métier : `PUT /jobs/{id}/start` (passe en `en_cours`, log `started_at`)

### 🖥 Frontend

- `ClientListPage` (Recherche rapide) + `ClientDetailPage` (Historique)
- `JobCreatePage` (Client FK, Date, Titre, Urgence)
- `DashboardPage` (Liste jobs du jour) + Bouton "▶ Démarrer"
- **Bottom Navigation** implémentée

### 🚀 Déploiement & DevOps

- Déploiement Staging avec 1Panel (HTTPS) + Seeders DB

### 🧪 Cas de tests (Phase 2)

| ID   | User Story / Feature          | Critères d'acceptation (Test)                                                 |
| ---- | ----------------------------- | ----------------------------------------------------------------------------- |
| T2.1 | **CLI-02** : Recherche client | Recherche par tél matche instantanément avec Vue Query cache                  |
| T2.2 | **JOB-01** : Création job     | Impossible de créer un job sans `client_id`                                   |
| T2.3 | **US2** : Démarrer un job     | Le statut passe de `planifié` à `en_cours`, `started_at` est horodaté serveur |
| T2.4 | **JOB-04** : Workflow         | Interdiction de passer de `planifié` directement à `terminé`                  |

---

## 📌 Phase 3 : Flux "Intervention & Preuves" (Checklist + Photos + Offline) ⚡

**Focus :** Le cœur de la valeur terrain. Standardisation, preuves photos, et **résilience réseau** (sous-sol).

### 🛠 Backend

- Modèles `ChecklistItem`, `JobPhoto`, `Material`
- Endpoints Checklists (Batch update) + Upload Multipart Photos (`POST /jobs/{id}/photos`)
- Logique `PUT /jobs/{id}/complete` (Vérifie checklist obligatoire, stop timer)
- **Pillow** : Génération thumbnails

### 🖥 Frontend

- `InspectionPage` (Tabs Pré/Post) avec VeeValidate + Zod
- Saisie dynamique des matériaux
- Upload natif mobile (`capture="environment"`)
- 🌟 **Architecture Offline** : File d'attente locale (IndexedDB/LocalStorage) si perte réseau. Bouton "Synchroniser" visible.

### 🚀 Déploiement & DevOps

- Volume Docker pour stockage images (`/uploads`)
- 1Panel config pour servir les fichiers statiques

### 🧪 Cas de tests (Phase 3)

| ID   | User Story / Feature         | Critères d'acceptation (Test)                                          |
| ---- | ---------------------------- | ---------------------------------------------------------------------- |
| T3.1 | **INS-01/02** : Checklist    | Les items obligatoires non cochés bloquent la complétion du job        |
| T3.2 | **US3** : Photos avant/après | Le tag de la photo est forcé selon l'onglet actif                      |
| T3.3 | **OFFLINE** : Mode dégradé   | Une photo prise hors-ligne est stockée local, upload auto au retour 4G |
| T3.4 | **RPT-04** : Durée auto      | La durée est calculée serveur (`completed_at` - `started_at`)          |
| T3.5 | **Upload** : Sécurité        | Rejet des fichiers > 10Mo ou non-JPEG/PNG                              |

---

## 📌 Phase 4 : Flux "Clôture administrative" (PDF + Avis Client)

**Focus :** Génération de la preuve formelle (WeasyPrint) et boucle de feedback (Review).

### 🛠 Backend

- Modèle `Review` (UUID token unique, expiration 30j)
- **WeasyPrint** : Service de génération PDF agrégeant Job, Checklist, Matériaux, Photos
- Endpoint privé : `GET /jobs/{id}/report/download`
- Endpoints publics : `GET /review/{token}` et `POST /review/{token}/submit`

### 🖥 Frontend

- Saisie des observations générales
- Bouton "Générer Rapport" (Preview via `vue-pdf-embed`)
- Génération du lien d'avis (copier/coller + SMS/QR code)
- Page publique `ReviewPage` (Note 1-5 + Commentaire, sans auth)

### 🚀 Déploiement & DevOps

- Mise à jour Dockerfile Backend : dépendances OS pour WeasyPrint (`libpango`, `cairo`)

### 🧪 Cas de tests (Phase 4)

| ID   | User Story / Feature         | Critères d'acceptation (Test)                            |
| ---- | ---------------------------- | -------------------------------------------------------- |
| T4.1 | **RPT-01** : Génération PDF  | Le PDF inclut photos côte à côte, checklist et matériaux |
| T4.2 | **AVI-03** : Lien de partage | L'UUID est unique, lien inaccessible si job `annulé`     |
| T4.3 | **US6** : Soumission avis    | Un client note 5 étoiles et commente sans login          |
| T4.4 | **AVI-04** : Unicité avis    | Un 2e POST sur le même token retourne 409 Conflict       |
| T4.5 | **PDF** : Taille             | Le rapport généré est compressé et pèse < 2Mo            |

---

## 📌 Phase 5 : Polish, PWA & Production Ready

**Focus :** Dashboard, finitions UX mobile, signature P2 et bascule Production.

### 🛠 Backend

- Dashboard `GET /dashboard/summary` (Agregations Postgres)
- Switch conditionnel `SQLite → PostgreSQL` via `DATABASE_URL`
- Gestion des jobs `annulés`

### 🖥 Frontend

- Dashboard UX final (Stats, Prochain job)
- PWA Manifest (Installable sur l'écran d'accueil du tech)
- _Arbitrage P2_ : Intégration optionnelle du canvas "Signature client" dans le rapport PDF

### 🚀 Déploiement & DevOps

- PostgreSQL 16 Prod + Certificat SSL Let's Encrypt (1Panel)
- Cron de sauvegarde DB (`pg_dump`)
- Monitoring des logs d'erreur mobile (Sentry ou équivalent)

### 🧪 Cas de tests (Phase 5)

| ID   | User Story / Feature        | Critères d'acceptation (Test)                                           |
| ---- | --------------------------- | ----------------------------------------------------------------------- |
| T5.1 | **Dashboard** : Synthèse    | Chargement < 1s avec 1000 jobs en BDD                                   |
| T5.2 | **PWA** : Installabilité    | Lighthouse PWA score > 90                                               |
| T5.3 | **RPT-05** : Signature (P2) | Le canvas de signature s'efface au secouer le téléphone, intégré au PDF |
| T5.4 | **Prod** : Bascule DB       | L'app démarre sans erreur sur PostgreSQL 16                             |
| T5.5 | **E2E** : Parcours complet  | Création client → Job → Offline photo → Rapport → Avis (0 bug)          |

---

### 🧠 Bilan de cette V2 :

J'ai corrigé mon manque stratégique en adoptant le **découpage par la valeur métier** (Thin Slicing). Plutôt que de finir "tout le module client" avant de toucher au "module job", la Phase 2 connecte désormais le Client au Job pour que le technicien puisse _déjà travailler_. J'ai aussi repoussé la contrainte réseau (spécifiée dans le persona "sous-sol sans réseau") du simple "polish" de Phase 5 vers une vraie considération d'architecture en Phase 3.


---

