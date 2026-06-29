# INT-20 — Frontend InspectionPage

> **Objectif** : Page d'inspection mobile avec checklist pré/post-intervention
> **Stack** : Vue 3 + PrimeVue Checkbox/Textarea + Vue Query + batch update

---

## 1. Route

```
/jobs/:id/inspection  →  InspectionPage.vue
```

Ajoutée dans `router/index.ts` après `/jobs/:id` :

```ts
{
  path: "/jobs/:id/inspection",
  name: "Inspection",
  component: () => import("@/pages/InspectionPage.vue"),
  meta: { requiresAuth: true, title: "Inspection" },
}
```

---

## 2. Architecture

```mermaid
flowchart TD
    A[InspectionPage] -->|GET /checklist| B[Items API]
    A -->|GET /jobs/{id}| C[Job status]
    C -->|pas en_cours| D[Message warning]
    C -->|en_cours| E[Afficher sections]
    E --> F[Pré-intervention 3 items]
    E --> G[Post-intervention 2 items]
    F --> H[Checkbox toggle → local state]
    G --> H
    H --> I[Bouton Sauvegarder → PUT /batch]
    I --> J[invalidateQueries checklist + job]
```

---

## 3. État local vs API

```ts
// État local (optimistic) — changement instantané
const localChecked = ref<Record<number, boolean>>({})
const localNotes = ref<Record<number, string | null>>({})
const dirtyItems = ref<Set<number>>(new Set())

// Watch : initialise l'état local depuis l'API
watch(items, (newItems) => {
  for (const item of newItems) {
    localChecked.value[item.id] = item.checked
    localNotes.value[item.id] = item.note
  }
}, { immediate: true })
```

**Pourquoi un état local ?** L'utilisateur coche/décoche instantanément, sans attendre l'API. La sauvegarde se fait en batch au clic sur "Sauvegarder".

---

## 4. Sauvegarde en batch

```ts
async function handleSave() {
  // Ne sauvegarder que les items modifiés
  const batch = items
    .filter(item => dirtyItems.value.has(item.id))
    .map(item => ({
      id: item.id,
      checked: localChecked.value[item.id] ?? item.checked,
      note: localNotes.value[item.id] ?? item.note,
    }))

  await checklistApi.batchUpdate(auth.token!, jobId, batch)

  // Invalider le cache pour synchro avec JobDetailPage
  queryClient.invalidateQueries({ queryKey: ["checklist", jobId] })
  queryClient.invalidateQueries({ queryKey: ["job", jobId] })
}
```

---

## 5. Vérification du statut

```vue
<Message v-if="job && job.status !== 'en_cours'" severity="warn">
  Démarrez le job d'abord pour accéder à la checklist.
</Message>
```

Le job est chargé en parallèle de la checklist. Si le statut n'est pas `en_cours`, on bloque l'affichage des items.

---

## 6. Fichiers

| Fichier | Action |
|---------|--------|
| `src/api/client.ts` | `checklistApi` (getItems, batchUpdate) |
| `src/pages/InspectionPage.vue` | **Nouveau** — page complète |
| `src/router/index.ts` | Route `/jobs/:id/inspection` |
| `notes/frontend/INT-20-inspection-page.md` | Note pédagogique |
