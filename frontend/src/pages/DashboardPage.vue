<template>
    <div class="dashboard-page">
        <div class="page-header">
            <h1>Tableau de bord</h1>
            <p class="date">{{ todayDate }}</p>
        </div>

        <!-- Loading -->
        <div v-if="isLoading" class="loading-state">
            <Skeleton height="80px" class="mb-2" />
            <Skeleton height="80px" class="mb-2" />
            <Skeleton height="80px" />
        </div>

        <!-- Error -->
        <div v-else-if="isError" class="error-state">
            <Message severity="error">
                Impossible de charger le tableau de bord : {{ error?.message || "Erreur inconnue" }}
            </Message>
            <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch()" class="mt-2" />
        </div>

        <!-- Data -->
        <template v-else-if="dashboard">
            <!-- Compteurs -->
            <div class="counters">
                <div class="counter-card">
                    <span class="counter-value">{{ dashboard.today.interventions_total }}</span>
                    <span class="counter-label">Total</span>
                </div>
                <div class="counter-card in-progress">
                    <span class="counter-value">{{ dashboard.today.interventions_in_progress }}</span>
                    <span class="counter-label">En cours</span>
                </div>
                <div class="counter-card completed">
                    <span class="counter-value">{{ dashboard.today.interventions_completed }}</span>
                    <span class="counter-label">Terminés</span>
                </div>
            </div>

            <!-- Aucun intervention (ni planifié ni en cours) -->
            <div v-if="dashboard.today.interventions_total === 0" class="empty-state">
                <i class="pi pi-calendar-plus empty-icon" />
                <p class="empty-text">Aucun intervention aujourd'hui</p>
                <Button label="Nouveau intervention" icon="pi pi-plus" fluid @click="goToNewIntervention" />
            </div>

            <!-- Carte Prochain intervention -->
            <div
                v-if="dashboard.next_intervention"
                class="card next-intervention-card clickable-card"
                @click="router.push({ name: 'InterventionDetail', params: { id: dashboard.next_intervention!.id } })"
            >
                <div class="card-header">
                    <h2>Prochain intervention</h2>
                    <Chip
                        :label="dashboard.next_intervention.priority"
                        :severity="prioritySeverity(dashboard.next_intervention.priority)"
                        size="small"
                    />
                </div>
                <h3 class="intervention-title">{{ dashboard.next_intervention.title }}</h3>
                <div class="intervention-details">
                    <p><i class="pi pi-home" /> {{ dashboard.next_intervention.site_name }}</p>
                    <p><i class="pi pi-map-marker" /> {{ dashboard.next_intervention.site_address }}</p>
                    <p v-if="dashboard.next_intervention.scheduled_start_time">
                        <i class="pi pi-clock" /> {{ dashboard.next_intervention.scheduled_start_time }}
                    </p>
                </div>
                <Button
                    label="▶ Démarrer"
                    severity="success"
                    fluid
                    @click.stop="startIntervention(dashboard.next_intervention!.id)"
                    :loading="startingInterventionId === dashboard.next_intervention.id"
                />
            </div>

            <!-- Carte Intervention en cours -->
            <div
                v-if="dashboard.in_progress_intervention"
                class="card in-progress-card clickable-card"
                @click="router.push({ name: 'InterventionDetail', params: { id: dashboard.in_progress_intervention!.id } })"
            >
                <div class="card-header">
                    <h2>Intervention en cours</h2>
                    <Chip label="En cours" severity="info" size="small" />
                </div>
                <h3 class="intervention-title">{{ dashboard.in_progress_intervention.title }}</h3>
                <Button
                    label="Terminer"
                    severity="danger"
                    fluid
                    @click="router.push({ name: 'InterventionDetail', params: { id: dashboard.in_progress_intervention!.id } })"
                />
            </div>

            <!-- Carte En retard -->
            <div v-if="dashboard.overdue_interventions && dashboard.overdue_interventions.length > 0" class="card overdue-card">
                <div class="card-header">
                    <h2><i class="pi pi-exclamation-triangle" /> En retard</h2>
                </div>
                <div class="overdue-list">
                    <div v-for="intervention in dashboard.overdue_interventions" :key="intervention.id" class="overdue-item">
                        <div class="overdue-item-header">
                            <h3 class="intervention-title">{{ intervention.title }}</h3>
                            <Chip
                                :label="'J-' + intervention.days_overdue"
                                severity="warn"
                                size="small"
                            />
                        </div>
                        <div class="intervention-details">
                            <p><i class="pi pi-home" /> {{ intervention.site_name }}</p>
                            <p><i class="pi pi-map-marker" /> {{ intervention.site_address }}</p>
                            <p><i class="pi pi-calendar" /> {{ intervention.scheduled_date }}</p>
                        </div>
                        <div class="overdue-item-actions">
                            <Button
                                label="▶ Démarrer"
                                severity="success"
                                size="small"
                                fluid
                                :loading="startingInterventionId === intervention.id"
                                @click.stop="startIntervention(intervention.id)"
                            />
                            <Button
                                label="❌ Annuler"
                                severity="warn"
                                size="small"
                                fluid
                                :loading="cancellingInterventionId === intervention.id"
                                @click.stop="cancelIntervention(intervention.id)"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@tanstack/vue-query";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Chip from "primevue/chip";
import Skeleton from "primevue/skeleton";
import Message from "primevue/message";
import { useAuthStore } from "@/stores/auth";
import { dashboardApi, prioritySeverity, api } from "@/api/client";

const router = useRouter();
const auth = useAuthStore();
const toast = useToast();

// ── Dashboard query (auto-refresh every 10s) ──────────────

const {
    data: dashboard,
    isLoading,
    isError,
    error,
    refetch,
} = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.summary(auth.token!),
    refetchInterval: 10000,
    enabled: !!auth.token,
});

// ── Date du jour ──────────────────────────────────────────

const todayDate = computed(() => {
    const d = new Date();
    return d.toLocaleDateString("fr-FR", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
    });
});

// ── Start intervention ─────────────────────────────────────────────

const startingInterventionId = ref<number | null>(null);

async function startIntervention(interventionId: number) {
    startingInterventionId.value = interventionId;
    try {
        await api.put(`/interventions/${interventionId}/start`, {}, auth.token);
        toast.add({ severity: "success", summary: "Intervention démarré", life: 3000 });
        refetch();
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de démarrer le intervention",
            life: 5000,
        });
    } finally {
        startingInterventionId.value = null;
    }
}

// ── Cancel intervention ────────────────────────────────────────────

const cancellingInterventionId = ref<number | null>(null);

async function cancelIntervention(interventionId: number) {
    cancellingInterventionId.value = interventionId;
    try {
        await api.put(`/interventions/${interventionId}/cancel`, {}, auth.token);
        toast.add({ severity: "success", summary: "Intervention annulé", life: 3000 });
        refetch();
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible d'annuler le intervention",
            life: 5000,
        });
    } finally {
        cancellingInterventionId.value = null;
    }
}

// ── Navigation ────────────────────────────────────────────

function goToNewIntervention() {
    router.push({ name: "Interventions", query: { newIntervention: "1" } });
}
</script>

<style scoped>
.dashboard-page {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.page-header h1 {
    font-size: 1.4rem;
    font-weight: 700;
    margin: 0;
}

.date {
    color: #6b7280;
    font-size: 0.85rem;
    margin: 0.25rem 0 0;
    text-transform: capitalize;
}

.counters {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
}

.counter-card {
    background: white;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.counter-value {
    display: block;
    font-size: 1.8rem;
    font-weight: 800;
    color: #1f2937;
}

.counter-label {
    font-size: 0.75rem;
    color: #6b7280;
    font-weight: 500;
}

.counter-card.in-progress .counter-value {
    color: #2563eb;
}
.counter-card.completed .counter-value {
    color: #16a34a;
}

.card {
    background: white;
    border-radius: 10px;
    padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.card-header h2 {
    font-size: 0.9rem;
    font-weight: 600;
    color: #6b7280;
    margin: 0;
}

.intervention-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0;
}

.intervention-details {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.intervention-details p {
    margin: 0;
    font-size: 0.85rem;
    color: #4b5563;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.timer-section {
    text-align: center;
    padding: 0.75rem 0;
}

.loading-state {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.error-state {
    text-align: center;
}

.empty-state {
    text-align: center;
    padding: 2rem 0;
}

.clickable-card {
    cursor: pointer;
    transition: box-shadow 0.2s, transform 0.15s;
}

.clickable-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.clickable-card:active {
    transform: scale(0.99);
}

/* ── Overdue card ──────────────────────────── */
.overdue-card {
    border-left: 4px solid #f59e0b;
    background: #fffbeb;
}

.overdue-card .card-header h2 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: #d97706;
}

.overdue-card .card-header h2 i {
    font-size: 1rem;
}

.overdue-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.overdue-item {
    padding-bottom: 1rem;
    border-bottom: 1px solid #fde68a;
}

.overdue-item:last-child {
    padding-bottom: 0;
    border-bottom: none;
}

.overdue-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.overdue-item-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
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
.mb-2 {
    margin-bottom: 0.5rem;
}
</style>
