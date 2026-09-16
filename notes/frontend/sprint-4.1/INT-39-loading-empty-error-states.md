# INT-39 — Gestion états Loading/Empty/Error toutes pages

> **Date :** 13/07/2026
> **Fichiers modifiés :** `JobDetailPage.vue`, `ClientDetailPage.vue`, `InspectionPage.vue`, `ProfilePage.vue`, `ReviewPage.vue`, `ClientsPage.vue`
> **Fichiers vérifiés (inchangés) :** `DashboardPage.vue`, `JobsPage.vue`

---

## 1. Le pattern `v-if` à 3 états

Chaque page qui charge des données suit ce pattern :

```vue
<!-- Loading -->
<div v-if="isLoading" class="loading-state">
    <Skeleton height="80px" class="mb-2" />
    <Skeleton height="80px" />
</div>

<!-- Error -->
<div v-else-if="isError" class="error-state">
    <Message severity="error">
        Message d'erreur compréhensible
    </Message>
    <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch" class="mt-2" />
</div>

<!-- Empty (cas particulier : data chargée mais vide) -->
<div v-else-if="data && data.items.length === 0" class="empty-state">
    <i class="pi pi-inbox empty-icon" />
    <p class="empty-text">Aucune donnée</p>
    <Button label="Nouveau" icon="pi pi-plus" fluid @click="openDialog" />
</div>

<!-- Data -->
<template v-else>
    <!-- Contenu normal -->
</template>
```

### Ordre des conditions
1. `v-if="isLoading"` — Affiché **pendant** le chargement
2. `v-else-if="isError"` — Affiché **si** le chargement a échoué
3. `v-else-if="data vides"` — Affiché si les données sont vides (distinct de l'erreur)
4. `v-else` — Le contenu normal

### Pourquoi `v-else-if` et pas `v-if` partout ?
- `v-else-if` garanti qu'un seul bloc est affiché à la fois
- Si on utilisait `v-if` partout, plusieurs blocs pourraient s'afficher simultanément

---

## 2. `refetch()` — Le bouton "Réessayer"

### Destructuring
Pour utiliser `refetch`, il faut le déstructurer dans `useQuery` :

```ts
// ❌ Avant — pas de refetch
const { data, isLoading, isError, error } = useQuery({...});

// ✅ Après — avec refetch
const { data, isLoading, isError, error, refetch } = useQuery({...});
```

### Utilisation dans le template
```vue
<Button label="Réessayer" @click="refetch" />
```

**Note :** TypeScript se plaint que `refetch` attend `RefetchOptions` mais reçoit un `PointerEvent`. C'est un faux positif — Vue appelle juste la fonction, l'event MouseEvent est ignoré par `refetch()`.

### Pages où `refetch` a été ajouté

| Page | Query | Fonction `refetch` |
|------|-------|-------------------|
| `JobDetailPage` | `["job", jobId]` | `refetch` |
| `ClientDetailPage` | `["client", clientId]` | `refetchClient` |
| `ClientDetailPage` | `["client-jobs", clientId]` | `refetchJobs` |
| `InspectionPage` | `["checklist", jobId]` | `refetch` |
| `ReviewPage` | Fetch manuel | `loadReviewData()` |
| `ProfilePage` | Auth store | `auth.fetchUser()` |

---

## 3. Audits et corrections par page

### JobDetailPage
```vue
<!-- ❌ Avant : juste un Message -->
<Message v-else-if="isError" severity="error">...</Message>

<!-- ✅ Après : div.error-state + Message + Button -->
<div v-else-if="isError" class="error-state">
    <Message severity="error">...</Message>
    <Button label="Réessayer" fluid @click="refetch" />
</div>
```

### ClientDetailPage
Deux queries → deux états d'erreur :
- **Client** (`useQuery(["client", clientId])`) → erreur globale avec `refetchClient`
- **Jobs historiques** (`useQuery(["client-jobs", clientId])`) → erreur dans la carte "Historique" avec `refetchJobs`

```ts
// Avant : pas de refetch, pas d'isError pour les jobs
const { data: client, isLoading, isError, error } = useQuery({...});
const { data: jobsData, isLoading: jobsLoading } = useQuery({...});

// Après
const { data: client, isLoading, isError, error, refetch: refetchClient } = useQuery({...});
const { data: jobsData, isLoading: jobsLoading, isError: jobsError, error: jobsErrorObj, refetch: refetchJobs } = useQuery({...});
```

### InspectionPage
Même pattern que JobDetailPage : ajout de `refetch` + bouton "Réessayer".

### ProfilePage
Création complète des 3 états :
- **Loading** : `auth.loading` (propriété du store Pinia, true pendant `login()`)
- **Empty/Error** : `!auth.user` + bouton `auth.fetchUser()`
- **Data** : `auth.user` avec les infos

```vue
<div v-if="auth.loading" class="loading-state">
    <Skeleton height="40px" class="mb-2" />
    <Skeleton height="40px" class="mb-2" />
    <Skeleton height="40px" />
</div>

<div v-else-if="!auth.user" class="empty-state">
    <i class="pi pi-user" style="font-size: 3rem; color: #d1d5db" />
    <p class="empty-text">Impossible de charger le profil</p>
    <Button label="Réessayer" icon="pi pi-refresh" fluid @click="auth.fetchUser()" />
</div>

<div v-else class="profile-info">
    <!-- Contenu -->
</div>
```

### ReviewPage
Extraction de la logique de fetch dans une fonction réutilisable :

```ts
// ❌ Avant : logique inline dans onMounted, pas de retry possible
onMounted(async () => {
    try {
        const res = await fetch(`/api/v1/review/${token}`);
        // ...
    } catch {
        isError.value = true;
    }
});

// ✅ Après : fonction nommée + bouton Réessayer
async function loadReviewData() {
    isLoading.value = true;
    isError.value = false;
    try {
        const res = await fetch(`/api/v1/review/${token}`);
        // ...
    } catch {
        isError.value = true;
    } finally {
        isLoading.value = false;
    }
}

onMounted(loadReviewData);
```

### ClientsPage
Ajout d'un bouton "Nouveau client" dans l'empty state :

```vue
<div v-if="data.items.length === 0" class="empty-state">
    <i class="pi pi-users empty-icon" />
    <p class="empty-text">{{ search ? "Aucun client trouvé" : "Aucun client" }}</p>
    <Button label="Nouveau client" icon="pi pi-plus" fluid @click="showNewDialog = true" />
</div>
```

---

## 4. Résumé des fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `pages/JobDetailPage.vue` | Ajout `refetch` + bouton "Réessayer" |
| `pages/ClientDetailPage.vue` | Ajout `refetchClient` + `refetchJobs` + erreur jobs historiques |
| `pages/InspectionPage.vue` | Ajout `refetch` + bouton "Réessayer" |
| `pages/ProfilePage.vue` | Création complète Loading/Empty/Error |
| `pages/ReviewPage.vue` | Extraction `loadReviewData()` + bouton "Réessayer" |
| `pages/ClientsPage.vue` | Ajout bouton "Nouveau client" dans empty state |

---

## 5. PrimeVue components utilisés pour les états

| Composant | Usage |
|-----------|-------|
| `<Skeleton>` | Loading — `height`, `class="mb-2"` |
| `<Message>` | Error/Empty — `severity="error"` ou `"warn"` |
| `<Button icon="pi pi-refresh">` | "Réessayer" — `fluid` pour mobile |
| `<Button icon="pi pi-plus">` | Action empty state — `fluid` |
| `<i class="pi pi-...">` | Icône empty state — `style="font-size: 3rem"` |
