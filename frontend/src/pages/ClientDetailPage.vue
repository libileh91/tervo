<template>
  <div class="detail-page">
    <!-- Loading -->
    <div v-if="isLoading" class="loading-state">
      <Skeleton height="40px" class="mb-2" />
      <Skeleton height="100px" />
      <Skeleton height="120px" />
    </div>

    <!-- Error -->
    <div v-else-if="isError" class="error-state">
      <Message severity="error">
        Impossible de charger le client : {{ error?.message || "Erreur inconnue" }}
      </Message>
      <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetchClient" class="mt-2" />
    </div>

    <template v-else-if="client">
      <!-- En-tête -->
      <div class="header">
        <Button icon="pi pi-arrow-left" text rounded @click="router.push({ name: 'Clients' })" />
        <div class="header-info">
          <h1>{{ client.full_name }}</h1>
          <Chip :label="`${client.jobs_count} intervention(s)`" severity="info" size="small" />
        </div>
      </div>

      <!-- Infos client -->
      <div class="card">
        <div class="info-grid">
          <div class="info-field">
            <label>Téléphone</label>
            <p>{{ client.phone }}</p>
          </div>
          <div class="info-field" v-if="client.email">
            <label>Email</label>
            <p>{{ client.email }}</p>
          </div>
          <div class="info-field">
            <label>Adresse</label>
            <p>{{ client.address }}</p>
          </div>
          <div class="info-field" v-if="client.city || client.postal_code">
            <label>Ville / CP</label>
            <p>{{ [client.postal_code, client.city].filter(Boolean).join(" ") }}</p>
          </div>
          <div class="info-field" v-if="client.notes">
            <label>Notes</label>
            <p>{{ client.notes }}</p>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="actions">
        <Button label="+ Nouveau job" icon="pi pi-plus" severity="success" fluid />
        <Button label="Modifier" icon="pi pi-pencil" severity="info" fluid />
        <Button label="Supprimer" icon="pi pi-trash" severity="danger" fluid @click="showDeleteDialog = true" />
      </div>

      <!-- Historique des jobs -->
      <div class="card">
        <h2 class="section-title">Historique des interventions</h2>

        <div v-if="jobsLoading" class="loading-state">
          <Skeleton height="40px" v-for="i in 3" :key="i" class="mb-1" />
        </div>

        <div v-else-if="jobsData && jobsData.items.length > 0">
          <DataTable :value="jobsData.items" stripedRows size="small">
            <Column field="title" header="Titre" />
            <Column header="Statut">
              <template #body="{ data: row }">
                <Chip :label="row.status" :severity="statusSeverity(row.status)" size="small" />
              </template>
            </Column>
            <Column header="Technicien">
              <template #body="{ data: row }">{{ row.technician_name || "—" }}</template>
            </Column>
            <Column field="completed_at" header="Terminé le" />
          </DataTable>
        </div>

        <!-- Jobs error -->
        <div v-else-if="jobsError" class="error-state">
          <Message severity="warn">
            Erreur chargement historique : {{ jobsErrorObj?.message || "Erreur inconnue" }}
          </Message>
          <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetchJobs" class="mt-2" />
        </div>

        <p v-else class="empty-text">Aucune intervention pour ce client.</p>
      </div>
    </template>

    <!-- Dialog suppression -->
    <Dialog v-model:visible="showDeleteDialog" header="Confirmer la suppression" modal>
      <p>Supprimer ce client ? Toutes ses interventions seront également supprimées.</p>
      <div class="dialog-actions">
        <Button label="Annuler" severity="secondary" fluid @click="showDeleteDialog = false" />
        <Button label="Confirmer" severity="danger" fluid :loading="deleting" @click="handleDelete" />
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Chip from "primevue/chip";
import Skeleton from "primevue/skeleton";
import Message from "primevue/message";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import Dialog from "primevue/dialog";
import { useAuthStore } from "@/stores/auth";
import { clientsApi, statusSeverity } from "@/api/client";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const toast = useToast();
const queryClient = useQueryClient();

const clientId = Number(route.params.id);
const showDeleteDialog = ref(false);
const deleting = ref(false);

  // Client detail
  const {
    data: client,
    isLoading,
    isError,
    error,
    refetch: refetchClient,
  } = useQuery({
    queryKey: ["client", clientId],
    queryFn: () => clientsApi.getById(auth.token!, clientId),
    enabled: !!clientId,
  });

  // Job history
  const {
    data: jobsData,
    isLoading: jobsLoading,
    isError: jobsError,
    error: jobsErrorObj,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: ["client-jobs", clientId],
    queryFn: () => clientsApi.getJobs(auth.token!, clientId),
    enabled: !!clientId,
  });

// Delete
async function handleDelete() {
  deleting.value = true;
  try {
    await clientsApi.delete(auth.token!, clientId);
    toast.add({ severity: "success", summary: "Client supprimé", life: 3000 });
    queryClient.invalidateQueries({ queryKey: ["clients"] });
    router.push({ name: "Clients" });
  } catch (err: any) {
    toast.add({
      severity: "error",
      summary: "Erreur",
      detail: err.detail || "Impossible de supprimer",
      life: 5000,
    });
  } finally {
    deleting.value = false;
    showDeleteDialog.value = false;
  }
}
</script>

<style scoped>
.detail-page { padding: 1rem; display: flex; flex-direction: column; gap: 1rem; }
.header { display: flex; align-items: flex-start; gap: 0.75rem; }
.header-info { flex: 1; }
.header-info h1 { font-size: 1.3rem; font-weight: 700; margin: 0 0 0.5rem; }
.card { background: white; border-radius: 10px; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.section-title { font-size: 1rem; font-weight: 600; margin: 0 0 1rem; }
.info-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.info-field label { font-size: 0.75rem; font-weight: 600; color: #6b7280; text-transform: uppercase; }
.info-field p { margin: 0.2rem 0 0; font-size: 0.95rem; color: #1f2937; }
.actions { display: flex; flex-direction: column; gap: 0.5rem; }
.loading-state { display: flex; flex-direction: column; gap: 0.5rem; }
.empty-text { color: #9ca3af; text-align: center; padding: 1rem 0; }
.dialog-actions { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-1 { margin-bottom: 0.25rem; }
</style>
