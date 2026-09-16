# INT-41 — Création rapide client depuis formulaire job

> **Date :** 13/07/2026
> **Fichier modifié :** `frontend/src/pages/JobsPage.vue`

---

## 1. Problème : sélection client dans le formulaire "Nouveau job"

**Avant :** Un simple `<Select>` dropdown avec tous les clients préchargés. Si le client n'existait pas, le technicien devait :
1. Annuler le formulaire
2. Aller dans la page Clients
3. Créer le client
4. Revenir sur Jobs
5. Rouvrir le formulaire
6. Sélectionner le client

**Après :** Recherche + sélection ou création inline en 2 étapes (POST /clients → POST /jobs).

---

## 2. Architecture du nouveau champ client

### Workflow utilisateur
```
┌─────────────────────────────────────────────┐
│  Tape le nom du client dans le champ search │
└─────────────────┬───────────────────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
   Résultats trouvés   Aucun résultat
         │                 │
    Click client       "➕ Nouveau client"
         │                 │
    Chip sélection     Champs inline
    "Jean Dupont"      nom, téléphone, adresse
         │                 │
         └───────┬─────────┘
                 ▼
           Bouton "Créer"
                 │
         ┌───────┴───────┐
         ▼               ▼
    Client existant  Nouveau client
         │          POST /clients
         │               │
         └───────┬───────┘
                 ▼
           POST /jobs
           avec client_id
```

### Code : Template du champ client

```vue
<div class="field">
    <label>Client</label>

    <!-- Mode recherche -->
    <template v-if="!selectedClient">
        <InputText
            v-model="clientSearchQuery"
            placeholder="Rechercher un client..."
            fluid
        />

        <!-- Résultats -->
        <div v-if="clientSearchResults.length > 0" class="client-results">
            <div v-for="c in clientSearchResults" :key="c.id"
                 class="client-result-item" @click="selectClient(c)">
                <span class="client-result-name">{{ c.full_name }}</span>
                <span class="client-result-phone">{{ c.phone }}</span>
            </div>
        </div>

        <!-- Nouveau client -->
        <div v-if="clientSearchQuery && clientSearchResults.length === 0"
             class="client-no-result">
            <Button label="➕ Nouveau client" severity="secondary"
                    fluid @click="showNewClientForm = true" />
        </div>
    </template>

    <!-- Client sélectionné -->
    <div v-else class="client-selected">
        <Chip :label="selectedClient.full_name" removable
              @remove="clearSelectedClient" />
    </div>
</div>
```

### Code : Filtrage client-side

On précharge tous les clients à l'ouverture du dialogue (`page_size: 100`) et on filtre côté client :

```ts
const clientsList = ref<{ id: number; full_name: string; phone: string }[]>([]);

// Charge les clients à l'ouverture du dialogue
watch(showNewDialog, async (open) => {
    if (open && clientsList.value.length === 0) {
        const res = await clientsApi.list(auth.token!, { page_size: 100 });
        clientsList.value = res.items;
    }
});

// Filtrage réactif client-side
const clientSearchResults = computed(() => {
    if (!clientSearchQuery.value.trim()) return [];
    const q = clientSearchQuery.value.toLowerCase();
    return clientsList.value.filter(
        (c) => c.full_name.toLowerCase().includes(q)
           || c.phone.toLowerCase().includes(q),
    );
});
```

**Pourquoi client-side ?** 100 clients max, pas d'appel API à chaque frappe, réponse instantanée.

### Code : Workflow 2 étapes

```ts
async function onSubmitJob() {
    let clientId: number;

    if (selectedClient.value) {
        // Étape 1a : client existant → ID direct
        clientId = selectedClient.value.id;
    } else if (showNewClientForm.value && newClientName.value.trim()) {
        // Étape 1b : nouveau client → POST /clients
        const created = await clientsApi.create(auth.token!, {
            full_name: newClientName.value.trim(),
            phone: newClientPhone.value.trim(),
            address: newClientAddress.value.trim() || newClientName.value.trim(),
        });
        clientId = created.id;
        // Rafraîchir la liste clients
        const res = await clientsApi.list(auth.token!, { page_size: 100 });
        clientsList.value = res.items;
    } else {
        toast.add({ severity: "error", summary: "Client requis", ... });
        return;
    }

    // Étape 2 : POST /jobs avec le client_id
    const newJob = await jobsApi.create(auth.token!, {
        client_id: clientId,
        title,
        description: ...,
        scheduled_date: ...,
        priority: ...,
    });
}
```

---

## 3. Nouveaux états et fonctions

| Variable | Type | Rôle |
|----------|------|------|
| `clientSearchQuery` | `ref<string>` | Texte saisi dans la recherche |
| `clientSearchResults` | `computed<ClientListItem[]>` | Résultats filtrés (nom + téléphone) |
| `selectedClient` | `ref<{id, full_name} \| null>` | Client sélectionné ou null |
| `showNewClientForm` | `ref<boolean>` | Afficher le formulaire inline |
| `newClientName` | `ref<string>` | Nom du nouveau client |
| `newClientPhone` | `ref<string>` | Téléphone du nouveau client |
| `newClientAddress` | `ref<string>` | Adresse du nouveau client |

| Fonction | Rôle |
|----------|------|
| `selectClient(client)` | Sélectionne un client → cache la recherche, affiche un Chip |
| `clearSelectedClient()` | Remet à zéro → retour à la recherche |
| `cancelNewClient()` | Cache le formulaire inline + vide les champs |

---

## 4. CSS des nouveaux éléments

```css
/* Résultats de recherche */
.client-results {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    max-height: 180px;
    overflow-y: auto;
    background: white;
}

.client-result-item {
    padding: 0.6rem 0.75rem;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #f3f4f6;
    transition: background 0.15s;
}

.client-result-item:hover { background: #eff6ff; }
.client-result-item:active { background: #dbeafe; }

.client-result-name { font-weight: 600; font-size: 0.9rem; }
.client-result-phone { font-size: 0.8rem; color: #9ca3af; }

/* Formulaire nouveau client inline */
.new-client-section {
    background: #f9fafb;
    border-radius: 8px;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
```

---

## 5. Résumé

| Fichier | Changement |
|---------|-----------|
| `frontend/src/pages/JobsPage.vue` | Champ `<Select>` client → système recherche + sélection + création inline ; `onSubmitJob()` en 2 étapes (POST /clients → POST /jobs) |
