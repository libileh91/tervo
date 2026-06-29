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

- [ ] `App.vue` utilise `min-height: 100dvh` (dynamique viewport height pour mobile)
- [ ] BottomNav fixe avec `padding-bottom: env(safe-area-inset-bottom)` (iPhone X+)
- [ ] Toutes les pages ont un padding qui évite la superposition avec BottomNav
- [ ] Tailles de police : minimum 16px (pour éviter le zoom automatique iOS)
- [ ] Champs de formulaire : `width: 100%` avec `box-sizing: border-box`
- [ ] PrimeVue `fluid` sur tous les boutons (full width sur mobile)
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

- [ ] **Loading** : Skeleton PrimeVue sur toutes les pages qui chargent des données
- [ ] **Empty** : Message + icône + action possible (ex: "Aucun job aujourd'hui" + "Nouveau job")
- [ ] **Error** : Message d'erreur compréhensible + bouton "Réessayer" qui appelle `refetch()`
- [ ] Audit des pages existantes pour vérifier les 3 états :
  - DashboardPage ✅ (déjà fait)
  - JobsPage ✅ (déjà fait)
  - JobDetailPage ✅ (déjà fait)
  - ClientsPage ✅ (déjà fait)
  - ClientDetailPage ✅ (déjà fait)
  - InspectionPage ⏳ (à vérifier)
  - ProfilePage ⏳ (à ajouter)
  - ReviewPage ⏳ (à vérifier)

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

- [ ] Transition slide horizontale entre les pages (gauche/droite)
- [ ] Transition fade sur les états loading → data
- [ ] Durée : 200-300ms
- [ ] Pas d'animation pour la page Login

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

- [ ] Dans le formulaire "Nouveau job", ajouter un champ de recherche client
- [ ] Si client existant : le sélectionner → champ désactivé
- [ ] Si client inconnu : bouton "➕ Nouveau client" → affiche les champs inline (nom, téléphone, adresse)
- [ ] À la soumission : créer le client + le job en un seul clic
- [ ] Workflow : `POST /clients` (si nouveau) → `POST /jobs` avec le `client_id` retourné

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

- [ ] Dashboard : clic sur "Prochain job" → `JobDetailPage`
- [ ] Dashboard : clic sur "Job en cours" → `JobDetailPage`
- [ ] Dashboard : clic sur "Terminer" → `JobDetailPage` (déjà fait)
- [ ] JobDetailPage : bouton "📋 Checklist" → `InspectionPage` (déjà fait)
- [ ] InspectionPage : bouton "← Retour" → `JobDetailPage`
- [ ] JobDetailPage : bouton "← Retour" → `JobsPage`
- [ ] Vérifier que toutes les navigations utilisent les `name` des routes, pas les paths en dur

**Technical Notes**

- Audit des navigations existantes — corriger les `router.push('/jobs/' + id)` en `router.push({ name: 'JobDetail', params: { id } })`
- Utiliser `router.back()` pour les retours simples
- Déjà partiellement fait dans Sprint 1.2

---

## Tests Cases Sprint 4.1

Les tests cases détaillés sont dans `test-cases.json`.
