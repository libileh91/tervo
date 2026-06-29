# Sprint 1.3 : Checklist & Validation (Semaine 2, Lun-Mer)

> **Durée :** 3 jours | **Points :** 20 | **Tâches :** 5 (INT-17 à INT-21)
>
> **Ce qui existe déjà dans le code** (ne pas refaire) :
> - Modèle `ChecklistItem`, migration, seed items — créés dans INT-09
> - Relation `job.checklist_items` active dans `models/job.py`
> - Schéma `ChecklistItemRef` dans `schemas/job.py`
> - Validation brute (compte unchecked) dans `JobService.complete_job()`
> - Type frontend `ChecklistItemRef` + `jobsApi.getById()` retourne déjà `checklist_items`

---

## INT-17 — ChecklistService + ChecklistRepository (3 pts) [+Sprint 3.1]

**User Story**  
En tant que **développeur backend**,  
Je veux **extraire la logique checklist dans un service dédié**  
Afin de **séparer les responsabilités et exposer des endpoints spécifiques**.

**État actuel**
- ✅ Modèle `ChecklistItem` : `backend/app/models/checklist_item.py`
- ✅ Seed items : `backend/app/repositories/job.py` → `_seed_checklist()` (privé)
- ✅ Validation : `backend/app/services/job.py` → `complete_job()` lignes 162-172

**Acceptance Criteria**
- [x] Créer `backend/app/repositories/checklist.py` — `ChecklistRepository` avec méthodes :
  - `get_items(job_id)` — tous les items d'un job triés par `position ASC`
  - `get_item(item_id)` — un item par son id
  - `update_item(item_id, data)` — maj `checked`/`note`
  - `batch_update(job_id, items_data)` — maj multiple en transaction
  - `count_unchecked(job_id)` — nombre d'items non cochés
- [x] Créer `backend/app/services/checklist.py` — `ChecklistService` avec méthodes :
  - `create_default_items(job_id)` → seed 5 items (pré + post), extrait de `JobRepository`
  - `get_items(job_id)` → liste triée
  - `update_item(item_id, data)` → maj checked/note
  - `batch_update(job_id, items)` → maj multiple (transaction)
  - `validate_all_checked(job_id)` → `{ "is_valid": bool, "errors": [...] }`
- [x] Migrer `JobRepository._seed_checklist()` → `ChecklistService.create_default_items()`
- [x] Migrer validation dans `JobService.complete_job()` → `ChecklistService.validate_all_checked()`
- [x] Ajouter `DEFAULT_PRE_ITEMS` / `DEFAULT_POST_ITEMS` dans `services/checklist.py` (déplacer depuis `repositories/job.py`)
- [x] **[Sprint 3.1]** `get_items()` auto-crée les items par défaut si liste vide (compatibilité jobs seed)
- [x] **[Sprint 3.1]** `add_custom_item(job_id, label, category)` — permet d'ajouter des items personnalisés

**Technical Notes**
- Architecture : `services/checklist.py` → `repositories/checklist.py`
- Labels seed actuels : Pré → ("Vérifier équipement de protection individuelle (EPI)", "Vérifier les accès et sécuriser la zone de travail", "Couper l'alimentation électrique de l'équipement"), Post → ("Nettoyer la zone de travail et remettre en état", "Rétablir l'alimentation et tester le fonctionnement")
- Importer `ChecklistService` dans `JobRepository.create()` pour remplacer l'appel direct à `self._seed_checklist()`
- Supprimer `_seed_checklist()` de `JobRepository` après migration

---

## INT-18 — GET/POST/PUT /jobs/{id}/checklist (3 pts) [+Sprint 3.1]

> **🔄 Corrigé Sprint 3.1 :**
> - Ajout `POST /jobs/{id}/checklist` — création d'items checklist custom
> - `get_items()` auto-crée les items par défaut si la liste est vide (jobs du seed sans checklist)
> - Service `add_custom_item()` ajouté dans `ChecklistService`
> - Frontend InspectionPage : champ texte + bouton "Ajouter" pour items custom

**User Story**  
En tant que **technicien**,  
Je veux **consulter et cocher les items de la checklist d'un job**  
Afin de **valider chaque point d'inspection un par un**.

**Acceptance Criteria**
- [x] `GET /api/v1/jobs/{job_id}/checklist` : retourne la liste des items (triés par position)
- [x] Chaque item : id, category, label, checked, note, position (via `ChecklistItemRef` existant)
- [x] `PUT /api/v1/jobs/{job_id}/checklist/{id}` : met à jour `checked` ET `note` d'un item
- [x] Body PUT : `{ "checked": true, "note": "RAS" }`
- [x] 404 si checklist item inexistant
- [x] 404 si job inexistant
- [x] Authentification requise
- [x] Un technicien ne peut modifier que la checklist de ses propres jobs (403 si pas assigné)
- [x] **[Sprint 3.1]** `POST /api/v1/jobs/{job_id}/checklist` : ajout d'item custom (label, category) → 201

**Technical Notes**
- Router : `backend/app/api/v1/checklist.py` (nouveau fichier)
- Service : `ChecklistService.get_items()`, `ChecklistService.update_item()`
- Schema : `ChecklistItemRef` existe déjà dans `schemas/job.py` — réutiliser
- Validation d'assignation : vérifier `job.technician_id == current_user.id`
- Enregistrer dans `backend/app/main.py` : `app.include_router(checklist_router, prefix=settings.API_V1_PREFIX)`

---

## INT-19 — PUT /jobs/{id}/checklist/batch (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **cocher plusieurs items de checklist en une seule fois**  
Afin de **gagner du temps et ne pas faire d'appels API répétés**.

**Acceptance Criteria**
- [x] `PUT /api/v1/jobs/{job_id}/checklist/batch` accepte un tableau d'items
- [x] Body : `{ "items": [{ "id": 1, "checked": true, "note": "RAS" }, ...] }`
- [x] Retourne `{ "updated": 3 }` (nombre d'items mis à jour)
- [x] Transaction : tout ou rien (rollback si erreur)
- [x] 404 si un item n'appartient pas au job
- [x] Authentification requise + vérification d'assignation

**Technical Notes**
- Router : `backend/app/api/v1/checklist.py` (même fichier que INT-18)
- Service : `ChecklistService.batch_update()`
- Transaction : `async with db.begin():` pour atomicité
- Vérifier que chaque `item_id` dans le batch appartient bien au `job_id`

---

## INT-20 — Frontend : InspectionPage + JobDetailPage (8 pts) [+Sprint 3.1]

**User Story**  
En tant que **technicien**,  
Je veux **remplir la checklist d'inspection depuis mon téléphone**  
Afin de **ne rien oublier et standardiser mes interventions**.

**Acceptance Criteria**
- [x] Route : `/jobs/:id/inspection` → à ajouter dans `router/index.ts`
- [x] Appel API `GET /api/v1/jobs/{job_id}/checklist` au chargement
- [x] Vérifier que le job est `en_cours` — sinon message "Démarrez le job d'abord"
- [x] Deux sections visibles : "Pré-intervention" et "Post-intervention"
- [x] Chaque section : liste d'items avec checkbox + champ note (textarea)
- [x] Checkbox cliquable → mise à jour instantanée (optimistic update via Vue Query)
- [x] Note libre par item
- [x] Bouton "Sauvegarder" → appel batch `PUT /api/v1/jobs/{job_id}/checklist/batch`
- [x] Après sauvegarde : toast succès + invalidation cache (`queryClient.invalidateQueries`)
- [x] États loading (Skeleton), error
- [x] Navigation retour vers `JobDetailPage` (bouton "← Retour" ou `router.back()`)
- [x] **[Sprint 3.1]** Bouton "✅ Terminer" direct sur `JobDetailPage` pour les jobs `en_cours` (mutation de `job.value`)
- [x] **[Sprint 3.1]** Formulaire "Ajouter un item" avec champ texte + bouton (POST checklist)
- [x] **[Sprint 3.1]** `allChecked` corrigé : checklist vide = `true` (pas d'items à vérifier)
- [x] **[Sprint 3.1]** `InputText` import manquant corrigé

**Technical Notes**
- Fichier : `frontend/src/pages/InspectionPage.vue` (nouveau)
- Route à ajouter : `{ path: '/jobs/:id/inspection', name: 'Inspection', component: () => import('@/pages/InspectionPage.vue'), meta: { requiresAuth: true, title: 'Inspection' } }` dans `router/index.ts` (après `/jobs/:id`)
- API client : ajouter `checklistApi` dans `api/client.ts` :
  ```ts
  export const checklistApi = {
    getItems: (token, jobId) => api.get<ChecklistItemRef[]>(`/jobs/${jobId}/checklist`, token),
    batchUpdate: (token, jobId, items) => api.put(`/jobs/${jobId}/checklist/batch`, { items }, token),
  }
  ```
- Vue Query : `useQuery({ queryKey: ['checklist', jobId], queryFn: () => checklistApi.getItems(token, jobId) })`
- Optimistic update : `useMutation` avec `onMutate` pour mise à jour locale instantanée
- Sections : filtrer items par `item.category === 'pre_intervention'` / `'post_intervention'`
- Invalider aussi `['job', jobId]` pour synchro avec `JobDetailPage`
- Inspiré du pattern `DashboardPage` (Vue Query + invalidation)

---

## INT-21 — Validation checklist + Completion UI (3 pts) [+Sprint 3.1]

> **🔄 Corrigé Sprint 3.1 :**
> - `allChecked` retournait `false` sur checklist vide → bouton "Terminer" bloqué à tort
> - Corrigé : checklist vide = `true` (pas d'items à cocher)
> - Bouton "Terminer" ajouté directement sur `JobDetailPage` (mutation directe de `job.value`)
> - Timer `ElapsedTimer` retiré du dashboard (perception faussée de "job en cours")
> - Checklist auto-création backend si items vides (`get_items()` dans `ChecklistService`)

**User Story**  
En tant que **technicien**,  
Je veux **que le système m'empêche de terminer si la checklist est incomplète**  
Afin de **ne pas oublier des points d'inspection importants**.

**État actuel**
- ✅ Validation brute dans `JobService.complete_job()` : compte `func.count()` des unchecked
- ✅ Renvoie 400 si items non cochés — mais message générique

**Acceptance Criteria**
- [x] Remplacer la validation inline dans `complete_job()` par un appel à `ChecklistService.validate_all_checked()`
- [x] `validate_all_checked()` retourne `{ "is_valid": true, "errors": [] }` ou `{ "is_valid": false, "errors": [...] }`
- [x] Message d'erreur HTTP amélioré : `"3 items non cochés (2 pré, 1 post)"`
- [x] Tests unitaires pour `validate_all_checked()`
  - Tous cochés → `is_valid: true`
  - 2 non cochés (1 pré, 1 post) → `is_valid: false` avec erreurs détaillées
- [x] Frontend : désactiver le bouton "Terminer" tant que la checklist est incomplète
- [x] Frontend : tooltip "Complétez la checklist d'abord" sur le bouton désactivé
- [x] Frontend : vérification locale avant appel API (optionnel, la validation serveur reste la référence)
- [x] **[Sprint 3.1]** Bouton "Terminer" sur `JobDetailPage` (en plus d'InspectionPage) avec mutation directe du statut
- [x] **[Sprint 3.1]** `ElapsedTimer` retiré de `DashboardPage` (perception faussée)
- [x] **[Sprint 3.1]** Checklist auto-création backend (`get_items()` → `create_default_items()` si vide)
- [x] **[Sprint 3.1]** Items checklist custom via `POST /jobs/{id}/checklist` + UI

**Technical Notes**
- Backend : modifier `JobService.complete_job()` → remplacer les lignes 162-172 par `ChecklistService.validate_all_checked()`
- Le bouton "Terminer" se trouve dans `DashboardPage.vue` (carte job en cours) et `JobDetailPage.vue` (si `job.status === 'en_cours'`)
- Activation : `:disabled="!isChecklistComplete"` avec `isChecklistComplete` calculé depuis les items
- Utiliser `v-tooltip="'Complétez la checklist d'abord'"` sur le bouton désactivé (PrimeVue Tooltip)

---

## Dépendances du sprint

```
INT-17 (ChecklistService)  ← socle backend
    ↓
INT-18 (GET/PUT individuels)  ← dépend du service
INT-19 (PUT batch)             ← dépend du service
    ↓
INT-20 (InspectionPage)  ← dépend de INT-18 + INT-19
    ↓
INT-21 (Validation)  ← dépend de INT-17 + INT-20
```

## Tests Cases Sprint 1.3

Les tests cases détaillés sont dans `test-cases.json`.
