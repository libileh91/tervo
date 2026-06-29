<template>
    <div class="jobs-page">
        <div class="page-header">
            <h1>Interventions</h1>
            <Button label="Nouveau job" icon="pi pi-plus" size="small" @click="showNewDialog = true" />
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
            <Button label="Réessayer" icon="pi pi-refresh" @click="refetch" class="mt-2" />
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
                <Button label="Nouveau job" icon="pi pi-plus" @click="showNewDialog = true" />
            </div>
        </template>

        <!-- Nouveau job Dialog -->
        <Dialog v-model:visible="showNewDialog" header="Nouvelle intervention" modal :style="{ width: '450px' }">
            <form @submit.prevent="onSubmitJob">
                <div class="field">
                    <label for="jclient">Client</label>
                    <Select
                        id="jclient"
                        v-model="newJobClientId"
                        :options="clientsOptions"
                        optionLabel="full_name"
                        optionValue="id"
                        placeholder="Selectionner un client"
                        fluid
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
                    <Button label="Annuler" severity="secondary" @click="showNewDialog = false" />
                    <Button type="submit" label="Créer" :loading="jobSubmitting" />
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

const clientsList = ref<{ id: number; full_name: string }[]>([]);
const clientsLoading = ref(false);
const jobSubmitting = ref(false);

// Form fields
const newJobTitle = ref("");
const newJobClientId = ref<number | null>(null);
const newJobDescription = ref("");
const newJobDate = ref<Date | null>(null);
const newJobPriority = ref("normale");

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
        newJobClientId.value = null;
        newJobDescription.value = "";
        newJobDate.value = null;
        newJobPriority.value = "normale";
    }
});

const clientsOptions = computed(() => clientsList.value);

const priorityOptions = [
    { label: "Basse", value: "basse" },
    { label: "Normale", value: "normale" },
    { label: "Haute", value: "haute" },
    { label: "Urgente", value: "urgente" },
];

async function onSubmitJob() {
    if (!newJobClientId.value) {
        toast.add({
            severity: "error",
            summary: "Client requis",
            detail: "Sélectionnez un client",
            life: 3000,
        });
        return;
    }
    const title = newJobTitle.value.trim() || newJobDescription.value.trim().slice(0, 80) || "Intervention";
    const dateStr = newJobDate.value
        ? newJobDate.value instanceof Date
            ? `${newJobDate.value.getFullYear()}-${String(newJobDate.value.getMonth() + 1).padStart(2, "0")}-${String(newJobDate.value.getDate()).padStart(2, "0")}`
            : newJobDate.value
        : new Date().toISOString().split("T")[0];

    jobSubmitting.value = true;
    try {
        const newJob = await jobsApi.create(auth.token!, {
            client_id: newJobClientId.value,
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
    },
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
    justify-content: space-between;
    align-items: center;
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
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1rem;
}

.error-msg {
    color: #e24c4c;
    font-size: 0.8rem;
}
</style>
