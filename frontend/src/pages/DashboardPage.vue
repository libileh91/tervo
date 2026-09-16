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
            <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch" class="mt-2" />
        </div>

        <!-- Data -->
        <template v-else-if="dashboard">
            <!-- Compteurs -->
            <div class="counters">
                <div class="counter-card">
                    <span class="counter-value">{{ dashboard.today.jobs_total }}</span>
                    <span class="counter-label">Total</span>
                </div>
                <div class="counter-card in-progress">
                    <span class="counter-value">{{ dashboard.today.jobs_in_progress }}</span>
                    <span class="counter-label">En cours</span>
                </div>
                <div class="counter-card completed">
                    <span class="counter-value">{{ dashboard.today.jobs_completed }}</span>
                    <span class="counter-label">Terminés</span>
                </div>
            </div>

            <!-- Aucun job (ni planifié ni en cours) -->
            <div v-if="dashboard.today.jobs_total === 0" class="empty-state">
                <i class="pi pi-calendar-plus empty-icon" />
                <p class="empty-text">Aucun job aujourd'hui</p>
                <Button label="Nouveau job" icon="pi pi-plus" fluid @click="goToNewJob" />
            </div>

            <!-- Carte Prochain job -->
            <div
                v-if="dashboard.next_job"
                class="card next-job-card clickable-card"
                @click="router.push({ name: 'JobDetail', params: { id: dashboard.next_job!.id } })"
            >
                <div class="card-header">
                    <h2>Prochain job</h2>
                    <Chip
                        :label="dashboard.next_job.priority"
                        :severity="prioritySeverity(dashboard.next_job.priority)"
                        size="small"
                    />
                </div>
                <h3 class="job-title">{{ dashboard.next_job.title }}</h3>
                <div class="job-details">
                    <p><i class="pi pi-user" /> {{ dashboard.next_job.client_full_name }}</p>
                    <p><i class="pi pi-map-marker" /> {{ dashboard.next_job.client_address }}</p>
                    <p v-if="dashboard.next_job.scheduled_start_time">
                        <i class="pi pi-clock" /> {{ dashboard.next_job.scheduled_start_time }}
                    </p>
                </div>
                <Button
                    label="▶ Démarrer"
                    severity="success"
                    fluid
                    @click.stop="startJob(dashboard.next_job!.id)"
                    :loading="startingJobId === dashboard.next_job.id"
                />
            </div>

            <!-- Carte Job en cours -->
            <div
                v-if="dashboard.in_progress_job"
                class="card in-progress-card clickable-card"
                @click="router.push({ name: 'JobDetail', params: { id: dashboard.in_progress_job!.id } })"
            >
                <div class="card-header">
                    <h2>Job en cours</h2>
                    <Chip label="En cours" severity="info" size="small" />
                </div>
                <h3 class="job-title">{{ dashboard.in_progress_job.title }}</h3>
                <Button
                    label="Terminer"
                    severity="danger"
                    fluid
                    @click="router.push({ name: 'JobDetail', params: { id: dashboard.in_progress_job!.id } })"
                />
            </div>

            <!-- Carte En retard -->
            <div v-if="dashboard.overdue_jobs && dashboard.overdue_jobs.length > 0" class="card overdue-card">
                <div class="card-header">
                    <h2><i class="pi pi-exclamation-triangle" /> En retard</h2>
                </div>
                <div class="overdue-list">
                    <div v-for="job in dashboard.overdue_jobs" :key="job.id" class="overdue-item">
                        <div class="overdue-item-header">
                            <h3 class="job-title">{{ job.title }}</h3>
                            <Chip
                                :label="'J-' + job.days_overdue"
                                severity="warn"
                                size="small"
                            />
                        </div>
                        <div class="job-details">
                            <p><i class="pi pi-user" /> {{ job.client_full_name }}</p>
                            <p><i class="pi pi-map-marker" /> {{ job.client_address }}</p>
                            <p><i class="pi pi-calendar" /> {{ job.scheduled_date }}</p>
                        </div>
                        <div class="overdue-item-actions">
                            <Button
                                label="▶ Démarrer"
                                severity="success"
                                size="small"
                                fluid
                                :loading="startingJobId === job.id"
                                @click.stop="startJob(job.id)"
                            />
                            <Button
                                label="❌ Annuler"
                                severity="warn"
                                size="small"
                                fluid
                                :loading="cancellingJobId === job.id"
                                @click.stop="cancelJob(job.id)"
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

// ── Start job ─────────────────────────────────────────────

const startingJobId = ref<number | null>(null);

async function startJob(jobId: number) {
    startingJobId.value = jobId;
    try {
        await api.put(`/jobs/${jobId}/start`, {}, auth.token);
        toast.add({ severity: "success", summary: "Job démarré", life: 3000 });
        refetch();
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de démarrer le job",
            life: 5000,
        });
    } finally {
        startingJobId.value = null;
    }
}

// ── Cancel job ────────────────────────────────────────────

const cancellingJobId = ref<number | null>(null);

async function cancelJob(jobId: number) {
    cancellingJobId.value = jobId;
    try {
        await api.put(`/jobs/${jobId}/cancel`, {}, auth.token);
        toast.add({ severity: "success", summary: "Job annulé", life: 3000 });
        refetch();
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible d'annuler le job",
            life: 5000,
        });
    } finally {
        cancellingJobId.value = null;
    }
}

// ── Navigation ────────────────────────────────────────────

function goToNewJob() {
    router.push({ name: "Jobs", query: { newJob: "1" } });
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

.job-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0;
}

.job-details {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.job-details p {
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
