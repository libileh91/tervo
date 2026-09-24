<template>
    <div class="clients-page">
        <div class="page-header">
            <h1>Clients</h1>
            <Button label="Nouveau client" icon="pi pi-plus" fluid @click="showNewDialog = true" />
        </div>

        <!-- Recherche -->
        <div class="search-bar">
            <InputText
                v-model="search"
                placeholder="Rechercher un client (nom ou téléphone)..."
                fluid
                @input="onSearchInput"
            />
            <Button v-if="search" icon="pi pi-times" severity="secondary" rounded @click="clearSearch" />
        </div>

        <!-- Loading -->
        <div v-if="isLoading" class="loading-state">
            <Skeleton v-for="i in 5" :key="i" height="60px" class="mb-2" />
        </div>

        <!-- Error -->
        <div v-else-if="isError" class="error-state">
            <Message severity="error">
                Impossible de charger les clients : {{ error?.message || "Erreur inconnue" }}
            </Message>
            <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch()" class="mt-2" />
        </div>

        <!-- Liste -->
        <template v-else-if="data">
            <DataTable
                :value="data.items"
                paginator
                :rows="pageSize"
                :totalRecords="data.total"
                :first="(page - 1) * pageSize"
                @page="onPage"
                @row-click="goToDetail"
                stripedRows
                size="small"
                class="client-table"
            >
                <Column field="full_name" header="Nom" sortable />
                <Column field="phone" header="Téléphone" />
                <Column field="city" header="Ville" />
            </DataTable>

            <div v-if="data.items.length === 0" class="empty-state">
                <i class="pi pi-users empty-icon" />
                <p class="empty-text">{{ search ? "Aucun client trouvé" : "Aucun client" }}</p>
                <Button label="Nouveau client" icon="pi pi-plus" fluid @click="showNewDialog = true" />
            </div>
        </template>

        <!-- Nouveau client Dialog -->
        <Dialog v-model:visible="showNewDialog" header="Nouveau client" modal :style="{ width: '450px' }">
            <form @submit.prevent="onSubmit">
                <div class="field">
                    <label for="cfull_name">Nom complet *</label>
                    <InputText id="cfull_name" v-model="full_name" :invalid="!!errors.full_name" fluid />
                    <small v-if="errors.full_name" class="error-msg">{{ errors.full_name }}</small>
                </div>
                <div class="field">
                    <label for="cphone">Téléphone *</label>
                    <InputText id="cphone" v-model="phone" :invalid="!!errors.phone" fluid />
                    <small v-if="errors.phone" class="error-msg">{{ errors.phone }}</small>
                </div>
                <div class="field">
                    <label for="cemail">Email</label>
                    <InputText id="cemail" v-model="email" :invalid="!!errors.email" fluid />
                    <small v-if="errors.email" class="error-msg">{{ errors.email }}</small>
                </div>
                <div class="field">
                    <label for="caddress">Adresse *</label>
                    <Textarea id="caddress" v-model="address" :invalid="!!errors.address" fluid rows="2" />
                    <small v-if="errors.address" class="error-msg">{{ errors.address }}</small>
                </div>
                <div class="field-row">
                    <div class="field flex-1">
                        <label for="cpostal_code">Code postal</label>
                        <InputText id="cpostal_code" v-model="postal_code" :invalid="!!errors.postal_code" fluid />
                        <small v-if="errors.postal_code" class="error-msg">{{ errors.postal_code }}</small>
                    </div>
                    <div class="field flex-1">
                        <label for="ccity">Ville</label>
                        <InputText id="ccity" v-model="city" :invalid="!!errors.city" fluid />
                        <small v-if="errors.city" class="error-msg">{{ errors.city }}</small>
                    </div>
                </div>
                <div class="dialog-actions">
                    <Button label="Annuler" severity="secondary" fluid @click="showNewDialog = false" />
                    <Button
                        type="submit"
                        label="Créer"
                        fluid
                        :disabled="!meta.valid && meta.touched"
                        :loading="submitting"
                    />
                </div>
            </form>
        </Dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@tanstack/vue-query";
import { useForm, useField } from "vee-validate";
import { toTypedSchema } from "@vee-validate/zod";
import { clientCreateSchema } from "@/composables/useFormValidation";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import Dialog from "primevue/dialog";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Skeleton from "primevue/skeleton";
import Message from "primevue/message";
import { useAuthStore } from "@/stores/auth";
import { clientsApi } from "@/api/client";
import { useToast } from "primevue/usetoast";

const router = useRouter();
const auth = useAuthStore();
const toast = useToast();

// ── Liste ───────────────────────────────────────────────

const search = ref("");
const page = ref(1);
const pageSize = 25;
const debounceTimer = ref<ReturnType<typeof setTimeout> | null>(null);

function onSearchInput() {
    if (debounceTimer.value) clearTimeout(debounceTimer.value);
    debounceTimer.value = setTimeout(() => {
        page.value = 1;
        refetch();
    }, 300);
}

function clearSearch() {
    search.value = "";
    page.value = 1;
    refetch();
}

const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["clients", search, page],
    queryFn: () =>
        clientsApi.list(auth.token!, {
            search: search.value || undefined,
            page: page.value,
            page_size: pageSize,
        }),
});

function onPage(event: { page: number }) {
    page.value = event.page + 1;
}

function goToDetail(event: { data: { id: number } }) {
    router.push({ name: "ClientDetail", params: { id: event.data.id } });
}

// ── Nouveau client Dialog ────────────────────────────

const showNewDialog = ref(false);
const submitting = ref(false);

const { handleSubmit, errors, meta } = useForm({
    validationSchema: toTypedSchema(clientCreateSchema),
});

const { value: full_name } = useField<string>("full_name");
const { value: phone } = useField<string>("phone");
const { value: email } = useField<string>("email");
const { value: address } = useField<string>("address");
const { value: postal_code } = useField<string>("postal_code");
const { value: city } = useField<string>("city");
const { value: notes } = useField<string>("notes");

const onSubmit = handleSubmit(async (values) => {
    submitting.value = true;
    try {
        const newClient = await clientsApi.create(auth.token!, values);
        toast.add({
            severity: "success",
            summary: "Client créé",
            detail: `${newClient.full_name} ajouté`,
            life: 3000,
        });
        showNewDialog.value = false;
        refetch();
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de créer le client",
            life: 5000,
        });
    } finally {
        submitting.value = false;
    }
});
</script>

<style scoped>
.clients-page {
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
.search-bar {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}
.client-table {
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
    margin: 0;
}
.mt-2 {
    margin-top: 0.5rem;
}
.mb-2 {
    margin-bottom: 0.5rem;
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

.field-row {
    display: flex;
    gap: 0.8rem;
}

.flex-1 {
    flex: 1;
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
</style>
