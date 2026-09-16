# INT-42 — Navigation contextuelle (clic dashboard → job → inspection)

> **Date :** 13/07/2026
> **Fichiers modifiés :** `DashboardPage.vue`, `InspectionPage.vue`, `LoginPage.vue`, `ProfilePage.vue`

---

## 1. Audit complet des navigations

Avant de coder, j'ai audité tous les `router.push()` et `router.replace()` dans toutes les pages :

| Page | Navigation | Avant | Après |
|------|-----------|-------|-------|
| Dashboard → next-job card | Clic sur la carte | ❌ Aucune navigation | ✅ `{ name: 'JobDetail', params: { id } }` |
| Dashboard → in-progress card | Clic sur la carte | ❌ Aucune navigation | ✅ `{ name: 'JobDetail', params: { id } }` |
| Dashboard → "▶ Démarrer" | Bouton dans next-job | ✅ `startJob(id)` (API) | ✅ `@click.stop` (pas de propagation vers la carte) |
| Dashboard → "Terminer" | Bouton in-progress | ✅ `{ name: 'JobDetail', ... }` | ✅ Inchangé |
| JobDetail → "← Retour" | Bouton header | ✅ `{ name: 'Jobs' }` | ✅ Inchangé |
| JobDetail → "📋 Checklist" | Bouton actions | ✅ `{ name: 'Inspection', ... }` | ✅ Inchangé |
| Inspection → "← Retour" | Bouton header | ❌ `router.back()` | ✅ `{ name: 'JobDetail', params: { id: jobId } }` |
| Login → après connexion | Redirect | ❌ `router.push("/")` | ✅ `{ name: 'Dashboard' }` |
| Profile → "Se déconnecter" | Redirect | ❌ `router.push('/login')` | ✅ `{ name: 'Login' }` |

---

## 2. Cards cliquables sur le Dashboard

### Problème
Les cartes "Prochain job" et "Job en cours" n'étaient pas cliquables. Le technicien ne pouvait pas accéder au détail du job depuis le dashboard.

### Solution

```vue
<!-- Carte cliquable avec @click.stop sur le bouton enfant -->
<div
    v-if="dashboard.next_job"
    class="card next-job-card clickable-card"
    @click="router.push({ name: 'JobDetail', params: { id: dashboard.next_job!.id } })"
>
    ...
    <Button
        label="▶ Démarrer"
        @click.stop="startJob(dashboard.next_job!.id)"
        ...
    />
</div>
```

### `@click.stop` — Pourquoi c'est nécessaire
- Sans `@click.stop`, cliquer sur "▶ Démarrer" déclencherait **deux** événements :
  1. Le `@click` du bouton → `startJob()`
  2. Le `@click` de la carte → navigation vers JobDetailPage
- `@click.stop` appelle `event.stopPropagation()` → l'événement ne remonte pas au parent

### CSS des cartes cliquables
```css
.clickable-card {
    cursor: pointer;
    transition: box-shadow 0.2s, transform 0.15s;
}

.clickable-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.clickable-card:active {
    transform: scale(0.99);  /* Feedback tactile subtil */
}
```

---

## 3. `router.back()` → `router.push({ name })`

### Problème avec `router.back()`
```ts
// ❌ Fragile : dépend de l'historique du navigateur
router.back()
```
Si l'utilisateur arrive sur InspectionPage directement (URL copiée), `router.back()` peut le ramener n'importe où, voire le quitter de l'application.

### Solution
```ts
// ✅ Robuste : nom de route + paramètre explicite
router.push({ name: 'JobDetail', params: { id: jobId } })
```

---

## 4. Noms de route vs paths en dur

### Principe
Toujours utiliser les `name` des routes, jamais les paths en dur :

```ts
// ❌ Path en dur — casse si l'URL change
router.push("/")
router.push('/login')
router.push('/jobs/' + id)

// ✅ Nom de route — indépendant de l'URL
router.push({ name: 'Dashboard' })
router.push({ name: 'Login' })
router.push({ name: 'JobDetail', params: { id } })
```

### Routes disponibles
D'après `router/index.ts` :

| Name | Path | Page |
|------|------|------|
| `Login` | `/login` | LoginPage |
| `Dashboard` | `/` | DashboardPage |
| `Jobs` | `/jobs` | JobsPage |
| `JobDetail` | `/jobs/:id` | JobDetailPage |
| `Inspection` | `/jobs/:id/inspection` | InspectionPage |
| `Clients` | `/clients` | ClientsPage |
| `ClientDetail` | `/clients/:id` | ClientDetailPage |
| `Profile` | `/profile` | ProfilePage |
| `Review` | `/review/:token` | ReviewPage |

---

## 5. Résumé

| Fichier | Changement |
|---------|-----------|
| `DashboardPage.vue` | Cartes next-job + in-progress cliquables ; `@click.stop` sur "▶ Démarrer" ; CSS `.clickable-card` |
| `InspectionPage.vue` | `router.back()` → `{ name: 'JobDetail', params: { id: jobId } }` |
| `LoginPage.vue` | `router.push("/")` → `{ name: 'Dashboard' }` |
| `ProfilePage.vue` | `router.push('/login')` → `{ name: 'Login' }` |
