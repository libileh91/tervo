# Sprint 4.1 : Frontend mobile (Semaine 5, Lun-Mer)

> **Durée :** 3 jours | **Points :** 18 | **Tâches :** 5 (INT-38 à INT-42)
>
> Sprint déplacé depuis l'ancien Sprint 2.3.

---

## INT-38 — Responsive mobile (layout bottom nav, plein écran) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **que l'application s'adapte parfaitement à mon écran de smartphone**  
Afin de **travailler confortablement sur le terrain**.

**Acceptance Criteria**

- [x] `App.vue` utilise `min-height: 100dvh` (dynamique viewport height pour mobile)
- [x] BottomNav fixe avec `padding-bottom: env(safe-area-inset-bottom)` (iPhone X+)
- [x] Toutes les pages ont un padding qui évite la superposition avec BottomNav
- [x] Tailles de police : minimum 16px (pour éviter le zoom automatique iOS)
- [x] Champs de formulaire : `width: 100%` avec `box-sizing: border-box`
- [x] PrimeVue `fluid` sur tous les boutons (full width sur mobile)
- [ ] Testé sur : iPhone SE, iPhone 14, Android Galaxy S22 (viewport 375px - 430px)

**Technical Notes**

- Fichier : `frontend/src/App.vue` (layout principal)
- Utiliser `dvh` unit : `min-height: 100dvh` (meilleur que `100vh` sur mobile)
- Safe area : `env(safe-area-inset-bottom)` pour les notchs iOS
- Meta viewport déjà dans `index.html` : `<meta name="viewport" content="width=device-width, initial-scale=1.0">`

---

## INT-39 — Gestion états Loading/Empty/Error toutes pages (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **savoir clairement ce qui se passe dans l'application**  
Afin de **ne pas rester bloqué sur un écran vide ou une erreur silencieuse**.

**Acceptance Criteria**

- [x] **Loading** : Skeleton PrimeVue sur toutes les pages qui chargent des données
- [x] **Empty** : Message + icône + action possible (ex: "Aucun job aujourd'hui" + "Nouveau job")
- [x] **Error** : Message d'erreur compréhensible + bouton "Réessayer" qui appelle `refetch()`
- [x] Audit des pages existantes pour vérifier les 3 états :
  - DashboardPage ✅ (déjà fait)
  - JobsPage ✅ (déjà fait)
  - JobDetailPage ✅ (ajouté bouton Réessayer)
  - ClientsPage ✅ (ajouté bouton action empty state)
  - ClientDetailPage ✅ (ajouté Réessayer + jobs error)
  - InspectionPage ✅ (ajouté Réessayer)
  - ProfilePage ✅ (ajouté Loading/Empty/Error)
  - ReviewPage ✅ (ajouté Réessayer)

**Technical Notes**

- Utiliser `v-if="isLoading" / v-else-if="isError" / v-else` pattern (déjà utilisé sur JobDetailPage)
- Componentiser si redondant : créer `PageState.vue` avec props `loading`, `error`, `empty`
- `refetch()` vient de `useQuery()`

---

## INT-40 — Animations transitions pages (2 pts)

**User Story**  
En tant que **technicien**,  
Je veux **des transitions fluides entre les pages**  
Afin de **me sentir dans une application native**.

**Acceptance Criteria**

- [x] Transition slide horizontale entre les pages (gauche/droite)
- [x] Transition fade sur les états loading → data
- [x] Durée : 200-300ms
- [x] Pas d'animation pour la page Login

**Technical Notes**

- Fichier : `frontend/src/App.vue` — wrapper `<router-view>` avec `<Transition>`
- `<Transition name="slide-fade" mode="out-in">`
- CSS : `.slide-fade-enter-active { transition: all 0.3s ease; }`
- Désactiver pour `/login` avec `$route.meta.noTransition`

---

## INT-41 — Création rapide client depuis formulaire job (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **créer un client directement depuis le formulaire de nouveau job**  
Afin de **gagner du temps lors d'une intervention urgente**.

**Acceptance Criteria**

- [x] Dans le formulaire "Nouveau job", ajouter un champ de recherche client
- [x] Si client existant : le sélectionner → champ désactivé
- [x] Si client inconnu : bouton "➕ Nouveau client" → affiche les champs inline (nom, téléphone, adresse)
- [x] À la soumission : créer le client + le job en un seul clic
- [x] Workflow : `POST /clients` (si nouveau) → `POST /jobs` avec le `client_id` retourné

**Technical Notes**

- Fichier : `frontend/src/pages/JobsPage.vue` — formulaire "Nouveau job" à créer si pas déjà fait
- Ou créer `JobCreatePage.vue` avec route `/jobs/new`
- Pattern : recherche client (debounce 300ms) → sélection ou création inline
- Deux appels API : `clientsApi.create()` puis `jobsApi.create()`

---

## INT-42 — Navigation contextuelle (clic dashboard → job → inspection) (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **naviguer rapidement du dashboard au détail du job puis à l'inspection**  
Afin de **réduire le nombre de clics pour les actions fréquentes**.

**Acceptance Criteria**

- [x] Dashboard : clic sur "Prochain job" → `JobDetailPage`
- [x] Dashboard : clic sur "Job en cours" → `JobDetailPage`
- [x] Dashboard : clic sur "Terminer" → `JobDetailPage` (déjà fait)
- [x] JobDetailPage : bouton "📋 Checklist" → `InspectionPage` (déjà fait)
- [x] InspectionPage : bouton "← Retour" → `JobDetailPage`
- [x] JobDetailPage : bouton "← Retour" → `JobsPage`
- [x] Vérifier que toutes les navigations utilisent les `name` des routes, pas les paths en dur

**Technical Notes**

- Audit des navigations existantes — corriger les `router.push('/jobs/' + id)` en `router.push({ name: 'JobDetail', params: { id } })`
- Utiliser `router.back()` pour les retours simples
- Déjà partiellement fait dans Sprint 1.2

---

## Tests Cases Sprint 4.1

Les tests cases détaillés sont dans `test-cases.json`.
