# Fix — Bug#1 : Completion d'un job (statut "en_cours" persistant)

> **Date :** 26/06/2026
> **Cause racine :** 3 problèmes cumulatifs empêchaient de terminer un job.

---

## Problème 1 — Bouton "Terminer" toujours désactivé

```typescript
// InspectionPage.vue — AVANT
const allChecked = computed(() => {
    if (!items.value || items.value.length === 0) return false; // ← BLOQUE si checklist vide
    return items.value.every((i) => localChecked.value[i.id] ?? i.checked);
});
```

Les jobs du seed n'ont pas de checklist → `items` est vide → `allChecked = false` → bouton grisé.

```typescript
// APRES
const allChecked = computed(() => {
    if (!items.value || items.value.length === 0) return true;  // pas d'items = ok
    return items.value.every((i) => localChecked.value[i.id] ?? i.checked);
});
```

---

## Problème 2 — Statut non mis à jour après completion

Le cache TanStack Query ne se mettait pas à jour après l'appel API. Solutions tentées et échouées :
- `setQueryData` → merge incorrect (écrasait les champs manquants)
- `invalidateQueries` → async, le composant remontait avant refetch
- `removeQueries` → ne vidait pas le cache à temps
- `window.location.href` → rechargement complet mais pas fiable

**Solution finale — Mutation directe sur JobDetailPage :**

```typescript
// JobDetailPage.vue — bouton "Terminer" ajouté directement
<Button v-if="job.status === 'en_cours'" label="Terminer" @click="handleComplete" />

async function handleComplete() {
    await api.put(`/jobs/${jobId}/complete`, { observations: null }, auth.token);
    // Mutation directe — pas de cache
    job.value = { ...job.value!, status: "terminé", completed_at: new Date().toISOString() };
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
}
```

---

## Problème 3 — Timer qui tournait à l'infini

Le composant `ElapsedTimer` comptait le temps écoulé depuis `started_at` dans la carte "Job en cours" du dashboard. Tant que le dashboard n'était pas rafraîchi après completion, le timer continuait à tourner → illusion que le job est toujours en cours.

**Solution :** Supprimé. Le timer n'est pas une feature critique.

---

## Checklist auto-création backend

```python
# ChecklistService — get_items()
async def get_items(self, job_id: int) -> list:
    items = await self.repo.get_items(job_id)
    if not items:
        await self.create_default_items(job_id)  # auto-create si aucun
        items = await self.repo.get_items(job_id)
    return items
```

Les vieux jobs (seed) qui n'avaient pas de checklist en ont maintenant une automatiquement.

---

## Leçon

- **Mutation directe** > manipulation de cache pour les actions critiques
- Toujours vérifier les cas `vide` dans les conditions de validation
- Les composants visuels (timer) créent une perception faussée s'ils ne sont pas synchronisés

---

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `InspectionPage.vue` | `allChecked` → `true` sur checklist vide |
| `JobDetailPage.vue` | Ajout bouton "Terminer" + `handleComplete` |
| `DashboardPage.vue` | Retrait du `ElapsedTimer` |
| `checklist.py` | Auto-création si items vides |
