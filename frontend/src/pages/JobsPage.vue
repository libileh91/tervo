<template>
    <div class="jobs-page">
        <div class="page-header">
            <h1>Interventions</h1>
            <Button label="Nouveau job" icon="pi pi-plus" fluid @click="showNewDialog = true" />
        </div>

        <!-- Filtres -->
        <div class="filters">
            <Select
                v-model="filterStatus"
                :options="statusOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Tous les statuts"
                class="filter-select"
                @change="applyFilters"
            />
            <DatePicker
                v-model="filterDate"
                placeholder="Toutes les dates"
                class="filter-date"
                dateFormat="dd/mm/yy"
                @date-select="applyFilters"
            />
            <Button
                v-if="hasActiveFilters"
                icon="pi pi-times"
                severity="secondary"
                rounded
                @click="clearFilters"
                aria-label="Effacer les filtres"
            />
        </div>

        <!-- Loading -->
        <div v-if="isLoading" class="loading-state">
            <Skeleton v-for="i in 5" :key="i" height="60px" class="mb-2" />
        </div>

        <!-- Error -->
        <div v-else-if="isError" class="error-state">
            <Message severity="error">
                Impossible de charger les interventions : {{ error?.message || "Erreur inconnue" }}
            </Message>
            <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch" class="mt-2" />
        </div>

        <!-- Table -->
        <template v-else-if="data">
            <DataTable
                :value="data.items"
                :loading="isLoading"
                paginator
                :rows="pageSize"
                :totalRecords="data.total"
                :first="(page - 1) * pageSize"
                @page="onPage"
                stripedRows
                size="small"
                @row-click="goToDetail"
                class="job-table"
            >
                <Column field="title" header="Titre" sortable />
                <Column header="Client">
                    <template #body="{ data: row }">
                        {{ row.client?.full_name || "—" }}
                    </template>
                </Column>
                <Column header="Statut">
                    <template #body="{ data: row }">
                        <Chip :label="row.status" :severity="statusSeverity(row.status)" size="small" />
                    </template>
                </Column>
                <Column field="priority" header="Priorité">
                    <template #body="{ data: row }">
                        <Chip
                            :label="priorityLabel(row.priority)"
                            :severity="prioritySeverity(row.priority)"
                            size="small"
                        />
                    </template>
                </Column>
                <Column field="scheduled_date" header="Date" sortable />
            </DataTable>

            <!-- Empty state -->
            <div v-if="data.items.length === 0" class="empty-state">
                <i class="pi pi-inbox empty-icon" />
                <p class="empty-text">Aucune intervention trouvée</p>
                <Button label="Nouveau job" icon="pi pi-plus" fluid @click="showNewDialog = true" />
                            </div>
                        </template>

                        <!-- Nouveau job Dialog -->
        <Dialog v-model:visible="showNewDialog" header="Nouvelle intervention" modal :style="{ width: '450px' }">
            <form @submit.prevent="onSubmitJob">
                <!-- Client : recherche ou sélectionné -->
                <div class="field">
                    <label>Client</label>

                    <!-- Mode recherche -->
                    <template v-if="!selectedClient">
                        <InputText
                                                    v-model="clientSearchQuery"
                                                    placeholder="Rechercher un client..."
                                                    fluid
                                                />

                        <!-- Résultats de recherche -->
                        <div v-if="clientSearchResults.length > 0" class="client-results">
                            <div
                                v-for="c in clientSearchResults"
                                :key="c.id"
                                class="client-result-item"
                                @click="selectClient(c)"
                            >
                                <span class="client-result-name">{{ c.full_name }}</span>
                                <span class="client-result-phone">{{ c.phone }}</span>
                            </div>
                        </div>

                        <!-- Aucun résultat → bouton nouveau client -->
                        <div v-if="clientSearchQuery && clientSearchResults.length === 0" class="client-no-result">
                            <Button
                                label="➕ Nouveau client"
                                severity="secondary"
                                fluid
                                @click="showNewClientForm = true"
                            />
                        </div>
                    </template>

                    <!-- Client sélectionné -->
                    <div v-else class="client-selected">
                        <Chip
                            :label="selectedClient.full_name"
                            removable
                            @remove="clearSelectedClient"
                        />
                    </div>
                </div>

                <!-- Nouveau client inline -->
                <div v-if="showNewClientForm" class="new-client-section">
                    <h4 class="new-client-title">Nouveau client</h4>
                    <div class="field">
                        <label for="ncname">Nom complet *</label>
                        <InputText id="ncname" v-model="newClientName" placeholder="Ex: Jean Dupont" fluid />
                    </div>
                    <div class="field">
                        <label for="ncphone">Téléphone *</label>
                        <InputText id="ncphone" v-model="newClientPhone" placeholder="Ex: 06 12 34 56 78" fluid />
                    </div>
                    <div class="field">
                        <label for="ncaddr">Adresse</label>
                        <InputText id="ncaddr" v-model="newClientAddress" placeholder="Ex: 12 rue de Paris" fluid />
                    </div>
                    <Button
                        label="Annuler"
                        severity="secondary"
                        size="small"
                        fluid
                        @click="cancelNewClient"
                        class="mb-2"
                    />
                </div>

                <div class="field">
                    <label for="jtitle">Titre</label>
                    <InputText id="jtitle" v-model="newJobTitle" placeholder="Ex: Depannage chaudiere" fluid />
                </div>
                <div class="field">
                    <label for="jdesc">Description</label>
                    <Textarea
                        id="jdesc"
                        v-model="newJobDescription"
                        placeholder="Details (optionnel)"
                        fluid
                        rows="3"
                    />
                </div>
                <div class="field">
                    <label for="jdate">Date</label>
                    <DatePicker
                        id="jdate"
                        v-model="newJobDate"
                        dateFormat="dd/mm/yy"
                        placeholder="Sélectionner une date"
                        fluid
                    />
                </div>
                <div class="field">
                    <label for="jpriority">Priorité</label>
                    <Select
                        id="jpriority"
                        v-model="newJobPriority"
                        :options="priorityOptions"
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Normale"
                        fluid
                    />
                </div>
                <div class="dialog-actions">
                    <Button label="Annuler" severity="secondary" fluid @click="showNewDialog = false" />
                    <Button type="submit" label="Créer" fluid :loading="jobSubmitting" />
                </div>
            </form>
        </Dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useQuery } from "@tanstack/vue-query";
import Button from "primevue/button";
import Select from "primevue/select";
import DatePicker from "primevue/datepicker";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Chip from "primevue/chip";
import Skeleton from "primevue/skeleton";
import Message from "primevue/message";
import { useAuthStore } from "@/stores/auth";
import { jobsApi, clientsApi, statusSeverity, prioritySeverity, priorityLabel } from "@/api/client";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const toast = useToast();

// ── Filters ──────────────────────────────────────────────

const filterStatus = ref<string | null>((route.query.status as string) || null);
const filterDate = ref<Date | null>(route.query.date ? new Date(route.query.date as string) : null);
const page = ref(1);
const pageSize = 25;

const showNewDialog = ref(false);

const statusOptions = [
    { label: "Planifié", value: "planifié" },
    { label: "En cours", value: "en_cours" },
    { label: "Terminé", value: "terminé" },
    { label: "Annulé", value: "annulé" },
];

const hasActiveFilters = computed(() => filterStatus.value || filterDate.value);

// Build date string for API
const dateString = computed(() => {
    if (!filterDate.value) return undefined;
    const d = filterDate.value;
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
});

function applyFilters() {
    page.value = 1;
    // Sync filters with URL query params
    router.replace({
        query: {
            ...(filterStatus.value ? { status: filterStatus.value } : {}),
            ...(dateString.value ? { date: dateString.value } : {}),
        },
    });
}

function clearFilters() {
    filterStatus.value = null;
    filterDate.value = null;
    page.value = 1;
    router.replace({ query: {} });
}

// ── Query ────────────────────────────────────────────────

const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["jobs", filterStatus, dateString, page],
    queryFn: () =>
        jobsApi.list(auth.token!, {
            status: filterStatus.value || undefined,
            date: dateString.value,
            page: page.value,
            page_size: pageSize,
        }),
    keepPreviousData: true,
});

// ── Nouveau job Dialog ────────────────────────────────

const clientsList = ref<{ id: number; full_name: string; phone: string }[]>([]);
const clientsLoading = ref(false);
const jobSubmitting = ref(false);

// Form fields
const newJobTitle = ref("");
const newJobDescription = ref("");
const newJobDate = ref<Date | null>(null);
const newJobPriority = ref("normale");

// Client search & selection
const clientSearchQuery = ref("");
const selectedClient = ref<{ id: number; full_name: string } | null>(null);
const showNewClientForm = ref(false);
const newClientName = ref("");
const newClientPhone = ref("");
const newClientAddress = ref("");

// Client search results (client-side filter on preloaded list)
const clientSearchResults = computed(() => {
    if (!clientSearchQuery.value.trim()) return [];
    const q = clientSearchQuery.value.toLowerCase();
    return clientsList.value.filter(
        (c) => c.full_name.toLowerCase().includes(q) || c.phone.toLowerCase().includes(q),
    );
});

function selectClient(client: { id: number; full_name: string }) {
    selectedClient.value = client;
    clientSearchQuery.value = "";
    showNewClientForm.value = false;
}

function clearSelectedClient() {
    selectedClient.value = null;
}

function cancelNewClient() {
    showNewClientForm.value = false;
    newClientName.value = "";
    newClientPhone.value = "";
    newClientAddress.value = "";
}

// Fetch clients when dialog opens
watch(showNewDialog, async (open) => {
    if (open) {
        if (clientsList.value.length === 0) {
            clientsLoading.value = true;
            try {
                const res = await clientsApi.list(auth.token!, { page_size: 100 });
                clientsList.value = res.items;
            } catch (err) {
                console.error("Failed to load clients", err);
            } finally {
                clientsLoading.value = false;
            }
        }
        // Reset form
        newJobTitle.value = "";
        newJobDescription.value = "";
        newJobDate.value = null;
        newJobPriority.value = "normale";
        clientSearchQuery.value = "";
        selectedClient.value = null;
        showNewClientForm.value = false;
        newClientName.value = "";
        newClientPhone.value = "";
        newClientAddress.value = "";
    }
});

const priorityOptions = [
    { label: "Basse", value: "basse" },
    { label: "Normale", value: "normale" },
    { label: "Haute", value: "haute" },
    { label: "Urgente", value: "urgente" },
];

async function onSubmitJob() {
    // Déterminer le client_id (existant ou nouveau)
    let clientId: number;

    if (selectedClient.value) {
        clientId = selectedClient.value.id;
    } else if (showNewClientForm.value && newClientName.value.trim()) {
        // Étape 1 : créer le client
        jobSubmitting.value = true;
        try {
            const created = await clientsApi.create(auth.token!, {
                full_name: newClientName.value.trim(),
                phone: newClientPhone.value.trim(),
                address: newClientAddress.value.trim() || newClientName.value.trim(),
            });
            clientId = created.id;
            // Rafraîchir la liste clients pour la prochaine fois
            const res = await clientsApi.list(auth.token!, { page_size: 100 });
            clientsList.value = res.items;
        } catch (err: any) {
            toast.add({
                severity: "error",
                summary: "Erreur création client",
                detail: err.detail || "Impossible de créer le client",
                life: 5000,
            });
            jobSubmitting.value = false;
            return;
        }
    } else {
        toast.add({
            severity: "error",
            summary: "Client requis",
            detail: "Sélectionnez un client existant ou créez-en un nouveau",
            life: 3000,
        });
        return;
    }

    // Étape 2 : créer le job
    const title = newJobTitle.value.trim() || newJobDescription.value.trim().slice(0, 80) || "Intervention";
    const dateStr = newJobDate.value
        ? newJobDate.value instanceof Date
            ? `${newJobDate.value.getFullYear()}-${String(newJobDate.value.getMonth() + 1).padStart(2, "0")}-${String(newJobDate.value.getDate()).padStart(2, "0")}`
            : newJobDate.value
        : new Date().toISOString().split("T")[0];

    jobSubmitting.value = true;
    try {
        const newJob = await jobsApi.create(auth.token!, {
            client_id: clientId,
            title,
            description: newJobDescription.value || undefined,
            scheduled_date: dateStr,
            priority: newJobPriority.value,
        });
        toast.add({ severity: "success", summary: "Job créé", detail: newJob.title, life: 3000 });
        showNewDialog.value = false;
        refetch();
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de créer le job",
            life: 5000,
        });
    } finally {
        jobSubmitting.value = false;
    }
}

// ── Pagination ──────────────────────────────────────────

function onPage(event: { page: number }) {
    page.value = event.page + 1; // DataTable is 0-indexed
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Navigation ──────────────────────────────────────────

function goToDetail(event: { data: { id: number } }) {
    router.push({ name: "JobDetail", params: { id: event.data.id } });
}

// Watch route changes to sync filters (e.g. browser back/forward)
watch(
    () => route.query,
    (q) => {
        filterStatus.value = (q.status as string) || null;
        filterDate.value = q.date ? new Date(q.date as string) : null;
        // Open new job dialog when navigated from Dashboard "Nouveau job"
        if (q.newJob === "1") {
            showNewDialog.value = true;
            // Clean query param to avoid re-opening on back navigation
            router.replace({ query: { ...q, newJob: undefined } });
        }
    },
    { immediate: true },
);
</script>

<style scoped>
.jobs-page {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.page-header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.page-header h1 {
    font-size: 1.4rem;
    font-weight: 700;
    margin: 0;
}

.filters {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.filter-select {
    flex: 1;
    min-width: 0;
}

.filter-date {
    flex: 1;
    min-width: 0;
}

.job-table {
    width: 100%;
}

.loading-state {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.error-state {
    text-align: center;
}

.empty-state {
    text-align: center;
    padding: 3rem 0;
}

.empty-icon {
    font-size: 3rem;
    color: #d1d5db;
    margin-bottom: 1rem;
}

.empty-text {
    color: #9ca3af;
    font-size: 1rem;
    margin: 0 0 1rem;
}

.mt-2 {
    margin-top: 0.5rem;
}
.mt-2 {
    margin-top: 0.5rem;
}

.field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    margin-bottom: 0.8rem;
}

.field label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #374151;
}

.dialog-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
}

.error-msg {
    color: #e24c4c;
    font-size: 0.8rem;
}

/* ── Client search ─────────────────────────────── */
.client-results {
    display: flex;
    flex-direction: column;
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
    align-items: center;
    gap: 0.5rem;
    border-bottom: 1px solid #f3f4f6;
    transition: background 0.15s;
}

.client-result-item:last-child {
    border-bottom: none;
}

.client-result-item:hover {
    background: #eff6ff;
}

.client-result-item:active {
    background: #dbeafe;
}

.client-result-name {
    font-weight: 600;
    font-size: 0.9rem;
    color: #1f2937;
}

.client-result-phone {
    font-size: 0.8rem;
    color: #9ca3af;
}

.client-no-result {
    padding-top: 0.5rem;
}

.client-selected {
    padding: 0.25rem 0;
}

/* ── New client inline form ────────────────────── */
.new-client-section {
    background: #f9fafb;
    border-radius: 8px;
    padding: 0.75rem;
    margin-bottom: 0.8rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.new-client-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #374151;
    margin: 0;
}

.mb-2 {
    margin-bottom: 0.5rem;
}
</style>
