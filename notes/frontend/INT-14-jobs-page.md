# INT-14 — Frontend JobsPage (filtre statut/date)

> **Objectif** : Afficher la liste des interventions avec pagination, filtres et navigation
> **Stack** : Vue 3 + PrimeVue DataTable + Vue Query + filtres URL

---

## 1. Structure de la page

```mermaid
flowchart LR
    subgraph JobsPage
        A[Header + Bouton + Nouveau job]
        B[Filtres: Select statut + DatePicker]
        C[DataTable paginée]
        D[Row click → JobDetailPage]
    end
    subgraph API
        E[GET /api/v1/jobs?status=&date=&page=]
    end
    B --> C
    C --> E
    D --> F[/jobs/:id]
```

---

## 2. Filtres synchronisés avec l'URL

```ts
const filterStatus = ref<string | null>(route.query.status as string);
const filterDate = ref<Date | null>(route.query.date ? new Date(route.query.date as string) : null);

function applyFilters() {
  router.replace({ query: { status: filterStatus.value, date: dateString.value } });
}
```

**Avantage :** L'URL est partageable. `?status=planifié&date=2026-06-15` → bookmarkable.

---

## 2b. Piège évité : `optionLabel` / `optionValue` sur Select

```vue
<Select
    v-model="filterStatus"
    :options="statusOptions"
    optionLabel="label"       <!-- obligatoire : affiche "Planifié" dans le dropdown -->
    optionValue="value"        <!-- obligatoire : stocke "planifié" dans filterStatus -->
    @change="applyFilters"
/>
```

**Bug rencontré :** Sans `optionLabel` et `optionValue`, PrimeVue utilise **l'objet entier** comme valeur → `?status=[object+Object]` dans l'URL → filtre cassé.

```diff
+ optionLabel="label"
+ optionValue="value"
```

**Rappel :** `statusOptions` est un tableau d'objets :
```ts
const statusOptions = [
  { label: "Planifié", value: "planifié" },
  { label: "En cours",  value: "en_cours" },
  { label: "Terminé",   value: "terminé" },
  { label: "Annulé",    value: "annulé" },
]
```
Sans `optionValue`, `v-model` reçoit `{label, value}` au lieu de `"planifié"`.

## 3. DataTable PrimeVue

```vue
<DataTable
  :value="data.items"
  paginator
  :rows="pageSize"
  :totalRecords="data.total"
  @page="onPage"
  @row-click="goToDetail"
  stripedRows
  size="small"
>
  <Column field="title" header="Titre" sortable />
  <Column header="Client">
    <template #body="{ data: row }">{{ row.client?.full_name }}</template>
  </Column>
  <Column header="Statut">
    <template #body="{ data: row }">
      <Chip :label="row.status" :severity="statusSeverity(row.status)" />
    </template>
  </Column>
</DataTable>
```

**Points clés :**

- `@row-click` → navigation vers `JobDetailPage`
- `paginator` → pagination intégrée PrimeVue
- `stripedRows` → lignes alternées pour la lisibilité
- `Chip` → couleur par statut : vert (terminé), bleu (en cours), orange (planifié), rouge (annulé)

---

## 4. API Client — Jobs list

```ts
export const jobsApi = {
  list: (token, params) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.date) query.set("date", params.date);
    if (params?.page) query.set("page", String(params.page));
    return api.get<JobListResponse>(`/jobs?${query}`, token);
  },
};
```

---

## 5. Chip colors helpers

```ts
// Priorité
export function prioritySeverity(p: string) {
  switch (p) {
    case "urgente":
      return "danger"; // 🔴
    case "haute":
      return "warn"; // 🟠
    case "normale":
      return "info"; // 🟡
    case "basse":
      return "success"; // 🟢
  }
}

// Statut
export function statusSeverity(s: string) {
  switch (s) {
    case "terminé":
      return "success";
    case "en_cours":
      return "info";
    case "planifié":
      return "warn";
    case "annulé":
      return "danger";
  }
}
```

---

## 6. Fichiers modifiés

| Fichier                  | Action                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| `src/api/client.ts`      | Ajout types `JobListItem`, `JobListResponse` + `jobsApi` + `statusSeverity` |
| `src/pages/JobsPage.vue` | **Réécrit** placeholder → DataTable + filtres                               |

### Todo débloqué

- **TD-F002** (JobListPage) : ✅ Fait

---

## Récap

INT-14 — Frontend JobsPage (5 pts) — ✅ Terminé\*\*

### Fichiers modifiés

| Fichier                  | Action                                                                       |
| ------------------------ | ---------------------------------------------------------------------------- |
| `src/api/client.ts`      | Types `JobListItem`, `JobListResponse` + `jobsApi` + `statusSeverity` helper |
| `src/pages/JobsPage.vue` | **Réécrit** — placeholder → DataTable PrimeVue paginée                       |

### Fonctionnalités

- ✅ DataTable paginée (titre, client, statut chip, priorité chip, date)
- ✅ Filtre statut (Select dropdown) + filtre date (DatePicker)
- ✅ Filtres synchronisés avec URL (`?status=planifié&date=2026-06-15`)
- ✅ Clic sur une ligne → navigation vers `JobDetailPage`
- ✅ Bouton "+ Nouveau job"
- ✅ États loading (Skeleton), error (Message + Réessayer), empty
- ✅ Rafraîchissement manuel via bouton "Actualiser"

### Todo débloqué

- **TD-F002** (JobListPage) : ✅ Fait

---

Il reste **INT-15 — JobDetailPage** et **INT-16 — ClientListPage + ClientDetailPage** pour finir le sprint 1.2. Prêt quand tu veux.
