# INT-16 — Frontend ClientListPage + ClientDetailPage

> **Objectif** : Liste paginée des clients + fiche détaillée avec historique des jobs
> **Stack** : Vue 3 + PrimeVue DataTable + debounce recherche 300ms

---

## 1. Pages

| Route          | Page                   | API                                            |
| -------------- | ---------------------- | ---------------------------------------------- |
| `/clients`     | `ClientsPage.vue`      | `GET /api/v1/clients?search=&page=`            |
| `/clients/:id` | `ClientDetailPage.vue` | `GET /clients/{id}` + `GET /clients/{id}/jobs` |

---

## 2. ClientListPage — Recherche avec debounce

```vue
<InputText v-model="search" placeholder="Rechercher..." @input="onSearchInput" />

<script setup>
let debounceTimer = null;

function onSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    page.value = 1;
    refetch(); // ← appel API avec le nouveau search
  }, 300); // ← 300ms d'attente après la dernière frappe
}
</script>
```

**Pourquoi 300ms ?** Évite de bombarder l'API à chaque frappe clavier. On attend que l'utilisateur ait fini de taper.

---

## 3. ClientDetailPage — Deux requêtes parallèles

```ts
// Client info
const { data: client } = useQuery({
  queryKey: ["client", clientId],
  queryFn: () => clientsApi.getById(auth.token!, clientId),
});

// Job history (parallèle, indépendant)
const { data: jobsData } = useQuery({
  queryKey: ["client-jobs", clientId],
  queryFn: () => clientsApi.getJobs(auth.token!, clientId),
});
```

**Avantage :** Les deux appels partent en parallèle. Si la liste des jobs est longue, elle n'empêche pas l'affichage du client.

---

## 4. Suppression avec cascade

```ts
async function handleDelete() {
  await clientsApi.delete(auth.token!, clientId);
  // Le backend a `ON DELETE CASCADE` → tous les jobs supprimés aussi
  router.push({ name: "Clients" });
}
```

**Attention :** Le Dialog prévient : "Toutes ses interventions seront supprimées."

---

## 5. Fichiers

| Fichier                          | Action                                                                          |
| -------------------------------- | ------------------------------------------------------------------------------- |
| `src/api/client.ts`              | Types `ClientListItem`, `ClientDetailResponse`, `JobHistoryItem` + `clientsApi` |
| `src/pages/ClientsPage.vue`      | **Réécrit** — DataTable + recherche debounce                                    |
| `src/pages/ClientDetailPage.vue` | **Nouveau** — info client + historique jobs                                     |
| `src/router/index.ts`            | Route `/clients/:id` ajoutée                                                    |

### Todo débloqué

- **TD-F004** (ClientListPage + ClientDetailPage) : ✅ Fait

---

## Récap

INT-16 — Frontend ClientListPage + ClientDetailPage (5 pts) — ✅ Terminé\*\*

### Fichiers

| Fichier                                  | Action                                                        |
| ---------------------------------------- | ------------------------------------------------------------- |
| `src/api/client.ts`                      | Types clients + `clientsApi` (list, getById, delete, getJobs) |
| `src/pages/ClientsPage.vue`              | **Réécrit** — DataTable paginée + recherche debounce 300ms    |
| `src/pages/ClientDetailPage.vue`         | **Nouveau** — infos client + historique jobs                  |
| `src/router/index.ts`                    | Route `/clients/:id`                                          |
| `notes/frontend/INT-16-clients-pages.md` | Note pédagogique                                              |

### Todo débloqué

- **TD-F004** : ✅ Fait

---

### 🎉 Sprint 1.2 terminé !

| Tâche  | Description             | Status |
| ------ | ----------------------- | ------ |
| INT-08 | Modèle Job + migration  | ✅     |
| INT-09 | CRUD Jobs API           | ✅     |
| INT-10 | PUT /jobs/{id}/start    | ✅     |
| INT-11 | PUT /jobs/{id}/complete | ✅     |
| INT-12 | GET /dashboard/summary  | ✅     |
| INT-13 | Frontend DashboardPage  | ✅     |
| INT-14 | Frontend JobsPage       | ✅     |
| INT-15 | Frontend JobDetailPage  | ✅     |
| INT-16 | Frontend ClientsPages   | ✅     |

Prêt pour le **sprint 1.3** (Checklist & Validation) quand tu veux.
