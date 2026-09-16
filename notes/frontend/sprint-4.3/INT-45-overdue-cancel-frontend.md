# INT-45 — Frontend : section "En retard" + bouton "Annuler"

> **Date :** 13/07/2026
> **Sprint :** 4.3

---

## 1. Ce qui a été fait

### DashboardPage.vue
- Nouvelle carte "En retard" quand `dashboard.overdue_jobs.length > 0`
- Chaque job affiche : titre, client, adresse, date, jours de retard (chip `J-3`)
- Deux boutons par job : "▶ Démarrer" et "❌ Annuler"
- `@click.stop` sur les boutons pour éviter la propagation vers la carte

### JobDetailPage.vue
- Nouveau bouton "❌ Annuler" visible quand `job.status === 'planifié'`
- Dialog de confirmation avant annulation
- Invalidation du cache job + dashboard après succès

### client.ts
- Extension du type `DashboardSummary` avec `overdue_jobs`

---

## 2. Template : Carte "En retard" dans le Dashboard

```vue
<div v-if="dashboard.overdue_jobs && dashboard.overdue_jobs.length > 0"
     class="card overdue-card">
    <div class="card-header">
        <h2><i class="pi pi-exclamation-triangle" /> En retard</h2>
    </div>
    <div class="overdue-list">
        <div v-for="job in dashboard.overdue_jobs" :key="job.id"
             class="overdue-item">
            <div class="overdue-item-header">
                <h3 class="job-title">{{ job.title }}</h3>
                <Chip :label="'J-' + job.days_overdue" severity="warn"
                      size="small" />
            </div>
            <div class="job-details">
                <p><i class="pi pi-user" /> {{ job.client_full_name }}</p>
                <p><i class="pi pi-map-marker" /> {{ job.client_address }}</p>
                <p><i class="pi pi-calendar" /> {{ job.scheduled_date }}</p>
            </div>
            <div class="overdue-item-actions">
                <Button label="▶ Démarrer" severity="success" size="small"
                        fluid @click.stop="startJob(job.id)" />
                <Button label="❌ Annuler" severity="warn" size="small"
                        fluid @click.stop="cancelJob(job.id)" />
            </div>
        </div>
    </div>
</div>
```

### Pourquoi `@click.stop` ?
La carte overdue n'est pas clickable (contrairement aux cartes "Prochain job" et "Job en cours"), mais c'est une bonne pratique de mettre `@click.stop` sur les boutons au cas où la carte deviendrait clickable plus tard.

---

## 3. Fonction `cancelJob()` dans le Dashboard

```ts
const cancellingJobId = ref<number | null>(null);

async function cancelJob(jobId: number) {
    cancellingJobId.value = jobId;
    try {
        await api.put(`/jobs/${jobId}/cancel`, {}, auth.token);
        toast.add({ severity: "success", summary: "Job annulé", life: 3000 });
        refetch();  // ← rafraîchit le dashboard
    } catch (err: any) {
        toast.add({ severity: "error", summary: "Erreur", ... });
    } finally {
        cancellingJobId.value = null;
    }
}
```

---

## 4. Bouton "Annuler" dans JobDetailPage

### Dialog de confirmation
```vue
<Dialog v-model:visible="showCancelDialog" header="Confirmer l'annulation" modal>
    <p>Annuler cette intervention ?</p>
    <div class="dialog-actions">
        <Button label="Non" severity="secondary" fluid
                @click="showCancelDialog = false" />
        <Button label="Oui, annuler" severity="warn" fluid
                :loading="cancelLoading" @click="handleCancel" />
    </div>
</Dialog>
```

### Fonction avec invalidation de cache
```ts
async function handleCancel() {
    cancelLoading.value = true;
    try {
        await api.put(`/jobs/${jobId}/cancel`, {}, auth.token);
        toast.add({ severity: "success", summary: "Job annulé", life: 3000 });
        showCancelDialog.value = false;
        queryClient.invalidateQueries({ queryKey: ["job", jobId] });
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (err: any) { ... }
    finally { cancelLoading.value = false; }
}
```

**Dashboard → `refetch()` vs JobDetailPage → `queryClient.invalidateQueries()`**
- Le Dashboard utilise `refetch()` car c'est la fonction retournée par `useQuery()`
- JobDetailPage utilise `queryClient.invalidateQueries()` pour invalider proprement le cache sans re-fetcher immédiatement

---

## 5. CSS : Carte "En retard" orangée

```css
.overdue-card {
    border-left: 4px solid #f59e0b;   /* Barre orange */
    background: #fffbeb;               /* Fond crème */
}
.overdue-card .card-header h2 {
    color: #d97706;                    /* Texte orange */
    display: flex; align-items: center; gap: 0.4rem;
}
.overdue-item-actions {
    display: flex; gap: 0.5rem; margin-top: 0.75rem;
}
```

---

## 6. Résumé

| Fichier | Changement |
|---------|-----------|
| `pages/DashboardPage.vue` | Carte "En retard" + `cancelJob()` + CSS overdue |
| `pages/JobDetailPage.vue` | Bouton "❌ Annuler" + Dialog + `handleCancel()` |
| `api/client.ts` | Type TS `DashboardSummary.overdue_jobs` |
