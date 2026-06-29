# INT-13 — Frontend DashboardPage

> **Objectif** : Afficher le tableau de bord du technicien avec compteurs, prochain job, job en cours
> **Stack** : Vue 3 + PrimeVue + Vue Query + ElapsedTimer

---

## 1. Architecture du Dashboard

```mermaid
flowchart TD
    subgraph Frontend [DashboardPage.vue]
        A[useQuery refetchInterval=10s] -->|GET /dashboard/summary| B[Dashboard Data]
        B --> C[Compteurs 3 cartes]
        B --> D[Carte Prochain job]
        B --> E[Carte Job en cours]
        F[Bouton ▶ Démarrer] -->|PUT /jobs/{id}/start| G[refetch]
        H[ElapsedTimer.vue] -->|interval 1s| I[HH:MM:SS]
    end
    subgraph Backend [FastAPI]
        J[GET /api/v1/dashboard/summary]
        K[PUT /api/v1/jobs/{id}/start]
    end
    A --> J
    F --> K
```

---

## 2. Vue Query — Auto-refresh 10s

```ts
const {
  data: dashboard,
  isLoading,
  isError,
  error,
  refetch,
} = useQuery({
  queryKey: ['dashboard'],
  queryFn: () => dashboardApi.summary(auth.token!),
  refetchInterval: 10000,        // ← rafraîchissement auto toutes les 10s
  enabled: !!auth.token,          // ← ne tourne que si connecté
})
```

**Pourquoi Vue Query ?** Il gère automatiquement :
- Le cache (pas de re-fetch si les données n'ont pas changé)
- Le refetch interval (rafraîchissement auto)
- Les états `isLoading`, `isError`, `data`
- Le re-fetch manuel via `refetch()` après mutation (start)

---

## 3. ElapsedTimer — Chronomètre HH:MM:SS

```vue
<template>
  <span class="elapsed-timer">{{ display }}</span>
</template>

<script setup lang="ts">
const props = defineProps<{ startedAt: string }>()
const now = ref(Date.now())

onMounted(() => {
  setInterval(() => { now.value = Date.now() }, 1000)
})

const display = computed(() => {
  const diff = Math.floor((now.value - new Date(props.startedAt).getTime()) / 1000)
  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  const s = diff % 60
  return `${pad(h)}:${pad(m)}:${pad(s)}`
})
</script>
```

**Points clés :**
- `setInterval(1000)` → mise à jour chaque seconde
- `computed` → réactif : le template se met à jour automatiquement
- `tabular-nums` → les chiffres ne bougent pas quand ils changent (pas de sautillement)

---

## 4. Les états du dashboard

### Loading
```vue
<Skeleton height="80px" />  <!-- 3 squelettes gris animés -->
```

### Error
```vue
<Message severity="error">Impossible de charger...</Message>
<Button label="Réessayer" @click="refetch" />
```

### Empty (aucun job)
```vue
<i class="pi pi-calendar-plus" />
<p>Aucun job aujourd'hui</p>
<Button label="Nouveau job" />
```

### Data
```vue
<div class="counters">
  <div class="counter-card">          <!-- Total -->
  <div class="counter-card in-progress"> <!-- En cours -->
  <div class="counter-card completed">  <!-- Terminés -->
</div>

<div class="card" v-if="dashboard.next_job">          <!-- Prochain -->
<div class="card" v-if="dashboard.in_progress_job">   <!-- En cours -->
```

---

## 5. API Client — Dashboard types

```ts
export interface DashboardSummary {
  today: {
    date: string
    jobs_total: number
    jobs_in_progress: number
    jobs_completed: number
  }
  next_job: { id, title, priority, client_full_name, client_address, scheduled_start_time } | null
  in_progress_job: { id, title, started_at, elapsed_minutes } | null
}

export const dashboardApi = {
  summary: (token: string) => api.get<DashboardSummary>('/dashboard/summary', token),
}
```

---

## 6. Couleurs de priorité

```ts
export function prioritySeverity(p: string) {
  switch (p) {
    case 'urgente': return 'danger'    // 🔴
    case 'haute':   return 'warn'      // 🟠
    case 'normale': return 'info'      // 🟡
    case 'basse':   return 'success'   // 🟢
  }
}
```

---

## 7. Todo débloqué

- **TD-F001** (DashboardPage) : ✅ Fait
