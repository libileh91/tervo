# Sprint 1.2 : Jobs (Semaine 1, Jeu-Ven)

> **Durée :** 2 jours | **Points :** 39 | **Tâches :** 9 (INT-08 à INT-16)

---

## INT-08 — Modèle Job + migration (3 pts)

**User Story**  
En tant que **développeur backend**,  
Je veux **créer le modèle `Job` avec ses relations et sa migration**  
kAfin de **pouvoir gérer les interventions terrain**.

**Acceptance Criteria**
- [x] Modèle `Job` créé : id, client_id (FK), technician_id (FK), title, description, status, priority, scheduled_date, scheduled_start_time, scheduled_end_time, started_at, completed_at, observations, created_at, updated_at
- [x] Enums : `JobStatus` (planifié, en_cours, terminé, annulé), `Priority` (basse, normale, haute, urgente)
- [x] FK `client_id` → client.id (ON DELETE CASCADE)
- [x] FK `technician_id` → user.id (ON DELETE SET NULL)
- [x] Index sur : client_id, technician_id, status, scheduled_date, priority
- [x] Migration générée et appliquée
- [x] Relations ORM : `job.client`, `job.technician`, `job.checklist_items`, ~~`job.photos`, `job.materials`, `job.review`~~ (reporté Phase 2)

**Technical Notes**
- `scheduled_date` est NOT NULL (date obligatoire)
- `status` par défaut = `planifié`
- `priority` par défaut = `normale`
- Créer le fichier `backend/app/models/job.py`

--- 

## INT-09 — GET/POST /jobs + GET/PUT/DELETE /jobs/{id} (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **créer, lister, modifier, supprimer et consulter les jobs**  
Afin de **gérer mon planning d'interventions**.

**Acceptance Criteria**
- [x] `GET /api/v1/jobs` : liste paginée avec filtres (`?status=planifié&date=2026-05-15&technician_id=1`)
- [x] `POST /api/v1/jobs` : création → retourne 201 + job créé **avec checklist items par défaut (seed)**
- [x] `GET /api/v1/jobs/{id}` : détail complet incluant client, technician, checklist_items, ~~photos, materials~~ (Phase 2)
- [x] `PUT /api/v1/jobs/{id}` : modification des champs (sauf statut via workflow spécifique)
- [x] `DELETE /api/v1/jobs/{id}` : suppression → 204
- [x] Authentification requise
- [x] 404 si job inexistant
- [x] La création initialise automatiquement les checklist items (pré + post)
- [x] Auto-assign `technician_id` = `current_user.id` à la création

**Technical Notes**
- À la création d'un job, seed automatique de 3 items pré + 2 items post
- Schémas Pydantic : `JobCreate`, `JobUpdate`, `JobResponse`, `JobListResponse`
- Inclure les noms dans les relations (client full_name, technician full_name)

---

## INT-10 — PUT /jobs/{id}/start (démarrer → en_cours + timer) (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **démarrer un job d'un simple clic**  
Afin de **déclencher le chronomètre et passer en statut "en cours"**.

**Acceptance Criteria**
- [x] `PUT /api/v1/jobs/{id}/start` → status passe à `en_cours`
- [x] `started_at` enregistré automatiquement (timestamp serveur)
- [x] Validation : le job doit être `planifié` (sinon erreur 400)
- [x] Retourne `{ id, status, started_at }`
- [x] Authentification requise
- [x] Seul le technicien assigné peut démarrer (sinon 403)

**Technical Notes**
- Vérifier `job.status == JobStatus.PLANIFIE` avant mise à jour
- Vérifier que `job.technician_id == current_user.id` (sauf admin)
- Utiliser `datetime.utcnow()` pour `started_at`

```mermaid
flowchart LR
    A["POST /jobs"] -->|status: planifié| B["Job planifié"]
    B -->|PUT /jobs/{id}/start<br/>status: en_cours| C["Job en cours"]
    C -->|PUT /jobs/{id}/complete<br/>status: terminé| D["Job terminé"]
```

---

## INT-11 — PUT /jobs/{id}/complete (terminer → validations) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **terminer un job**  
Afin de **clôturer l'intervention, calculer la durée et générer le rapport**.

**Acceptance Criteria**
- [x] `PUT /api/v1/jobs/{id}/complete` accepte `{ observations }` optionnel
- [x] Le job doit être `en_cours` (sinon erreur 400)
- [x] Validation : tous les items checklist doivent être `checked`
- [ ] Validation : min. 1 photo avant + 1 photo après (Phase 2)
- [x] `completed_at` enregistré automatiquement
- [x] `duration_minutes` calculé (completed_at - started_at)
- [x] Retourne `{ id, status, completed_at, duration_minutes }`
- [x] Authentification requise, vérification d'assignation

**Technical Notes**
- Vérifications dans le service avant mise à jour
- `completed_at` = timestamp serveur
- `duration_minutes` = (completed_at - started_at) en minutes entières

---

## INT-12 — GET /dashboard/summary (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **voir mon résumé du jour sur le tableau de bord**  
Afin de **savoir combien de jobs m'attendent et où j'en suis**.

**Acceptance Criteria**
- [x] `GET /api/v1/dashboard/summary` retourne les infos du jour pour le technicien connecté
- [x] Champs : `today.date`, `today.jobs_total`, `today.jobs_in_progress`, `today.jobs_completed`
- [x] `next_job` : prochain job planifié (avec `client.full_name`, `client.address`, `priority`, `scheduled_start_time`)
- [x] `in_progress_job` : job en cours (avec `elapsed_minutes`)
- [x] Si aucun job en cours, `in_progress_job` = null
- [x] Si aucun prochain job, `next_job` = null
- [x] Authentification requise
- [x] Créer le schema Pydantic `DashboardSummaryResponse` dans `schemas/job.py`

**Technical Notes**
- Fichier : `backend/app/api/v1/dashboard.py` (nouveau router)
- Schémas : ajouter `DashboardSummaryResponse`, `TodaySummary`, `NextJobRef`, `InProgressJobRef` dans `schemas/job.py`
- Utiliser `selectinload(Job.client)` pour charger le client (pattern INT-09)
- Utiliser `datetime.now(timezone.utc)` pour `elapsed_minutes` (pattern INT-10)
- Filtrer par `scheduled_date == today` ET `technician_id == current_user.id`
- `next_job` = premier job `planifié` ordonné par `scheduled_start_time ASC`
- `elapsed_minutes` = (now - started_at) // 60 en minutes entières

---

## INT-13 — Frontend : DashboardPage (jobs du jour + boutons) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **voir mon tableau de bord en arrivant le matin**  
Afin de **consulter ma journée en un coup d'œil et démarrer mes jobs**.

**Acceptance Criteria**
- [x] Appel API `GET /api/v1/dashboard/summary` via `api.get()` (depuis `@/api/client`)
- [x] Affichage des compteurs : jobs_total, en_cours, terminés
- [x] Carte "Prochain job" : titre, priorité (couleur), client, adresse, heure
- [x] Bouton "▶ Démarrer" sur le prochain job → appelle `api.put('/jobs/{id}/start', {}, token)`
- [x] Carte "Job en cours" : titre, chronomètre (temps écoulé), bouton "Terminer"
- [x] Si aucun job : message "Aucun job aujourd'hui" + illustration
- [x] État loading : Skeleton PrimeVue
- [x] État error : message + bouton "Réessayer"
- [x] Rafraîchissement automatique toutes les 10s avec Vue Query

**Technical Notes**
- Fichier : `frontend/src/pages/DashboardPage.vue` (existe déjà en placeholder — à remplacer)
- Route : `name: 'Dashboard'` path: `/` (déjà dans `router/index.ts`)
- Appel API : `api.get<DashboardSummaryResponse>('/dashboard/summary', authStore.token)`
- Token : récupéré depuis `useAuthStore().token`
- Vue Query : `useQuery({ queryKey: ['dashboard'], queryFn: fetchDashboard, refetchInterval: 10000 })`
- Timer custom : nouveau composant `frontend/src/components/ElapsedTimer.vue` (props: started_at, affiche HH:MM:SS)
- Couleurs de priorité : 🔴 urgente, 🟠 haute, 🟡 normale, 🟢 basse (via PrimeVue Severity)
- Navigation contextuelle : `router.push({ name: 'JobDetail', params: { id: job.id } })`

---

## INT-14 — Frontend : JobsPage (filtre statut/date) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **voir la liste de tous mes jobs avec des filtres**  
Afin de **retrouver facilement une intervention passée ou à venir**.

**Acceptance Criteria**
- [x] Appel API `GET /api/v1/jobs?status=&date=` via `api.get()`
- [x] Liste paginée des jobs (DataTable PrimeVue)
- [x] Filtres : par statut (dropdown), par date (date picker)
- [x] Chaque ligne : titre, client, statut (chip coloré), priorité, date
- [x] Clic sur un job → navigation vers JobDetailPage
- [x] Bouton "+ Nouveau job" (en haut ou FAB)
- [x] États loading/empty/error gérés
- [x] Rafraîchissement manuel (bouton "Actualiser")

**Technical Notes**
- Fichier : `frontend/src/pages/JobsPage.vue` (existe déjà en placeholder — à remplacer)
- Route : `name: 'Jobs'` path: `/jobs` (déjà dans `router/index.ts`)
- Appel API : `api.get<JobListResponse>('/jobs?status=' + status + '&date=' + date, authStore.token)`
- Filtres synchronisés avec URL query params : `$route.query.status`, `$router.push({ query: { status } })`
- DataTable PrimeVue : `<DataTable :value="items">`, `<Column>`, `<Chip :severity="chipSeverity(status)">`
- Le filtre `technician_id` n'est pas nécessaire en frontend — le backend filtre automatiquement par `current_user`
- Navigation : `router.push({ name: 'JobDetail', params: { id: row.id } })`

---

## INT-15 — Frontend : JobDetailPage (fiche avec onglets) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **voir le détail complet d'un job**  
Afin de **consulter toutes les informations et actions disponibles**.

**Acceptance Criteria**
- [x] Appel API `GET /api/v1/jobs/{id}` via `api.get()`
- [x] En-tête : titre, statut (chip), priorité (chip couleur), nom client
- [x] Onglets (TabView PrimeVue) : Infos, Checklist, Photos, Matériaux, Rapport
- [x] Onglet Infos : description, dates (`scheduled_date`, `started_at`, `completed_at`), technicien assigné, observations
- [x] Onglets Checklist/Photos/Matériaux/Rapport : placeholder "Disponible dans une prochaine version" (Sprint 1.3 / Phase 2)
- [x] Boutons d'action : "▶ Démarrer" (si `planifié`) → `api.put('/jobs/{id}/start')`, "Terminer" (si `en_cours`)
- [x] Bouton "Supprimer" (si `planifié` ou `annulé`) avec confirmation Dialog
- [x] États loading/error

**Technical Notes**
- Fichier : `frontend/src/pages/JobDetailPage.vue` (nouveau fichier)
- Route : **ajouter** `{ path: '/jobs/:id', name: 'JobDetail', component: () => import('@/pages/JobDetailPage.vue'), meta: { requiresAuth: true, title: 'Intervention' } }` dans `router/index.ts`
- Appel API : `api.get<JobResponse>('/jobs/' + id, authStore.token)`
- TabView PrimeVue : `<TabView><TabPanel header="Infos">...</TabPanel><TabPanel header="Checklist" :disabled="true">...</TabPanel></TabView>`
- Dialog confirmation : `<Dialog header="Confirmer"><p>Supprimer ce job ?</p><Button label="Confirmer" severity="danger" @click="deleteJob" /></Dialog>`
- Navigation retour : `router.push({ name: 'Jobs' })` après suppression

---

## INT-16 — Frontend : ClientListPage + ClientDetailPage (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **consulter la liste des clients et leur fiche détaillée**  
Afin de **trouver un client et voir son historique**.

**Acceptance Criteria**
- [x] `ClientListPage` : liste paginée, champ de recherche (nom/téléphone)
- [x] `ClientDetailPage` : affiche toutes les infos client
- [x] `ClientDetailPage` : historique des jobs (tableau chronologique)
- [x] Bouton "Modifier" sur la fiche client
- [x] Bouton "Supprimer" avec confirmation
- [x] Bouton "+ Nouveau client"
- [x] Bouton "+ Nouveau job" depuis la fiche client
- [x] États loading/empty/error

**Technical Notes**
- `ClientListPage.vue` dans `pages/clients/`
- `ClientDetailPage.vue` dans `pages/clients/`
- Route params : `/clients`, `/clients/:id`
- Utiliser `GET /clients?search=` pour la recherche en temps réel (debounce 300ms)
- L'historique client réutilise le même format que `GET /clients/{id}/jobs`

---

## Tests Cases Sprint 1.2

Les tests cases détaillés sont dans `test-cases.json`.
