<template>
    <div class="inspection-page">
        <!-- Header -->
        <div class="header">
            <Button icon="pi pi-arrow-left" text rounded @click="router.push({ name: 'JobDetail', params: { id: jobId } })" />
            <h1>Inspection</h1>
        </div>

        <!-- Loading checklist -->
        <div v-if="isLoading" class="loading-state">
            <Skeleton height="40px" class="mb-2" />
            <Skeleton height="80px" v-for="i in 3" :key="i" class="mb-1" />
        </div>

        <!-- Error -->
        <div v-else-if="isError" class="error-state">
            <Message severity="error">
                Impossible de charger la checklist : {{ error?.message || "Erreur inconnue" }}
            </Message>
            <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch" class="mt-2" />
        </div>

        <!-- Job not started -->
        <Message v-else-if="job && job.status !== 'en_cours'" severity="warn">
            Démarrez le job d'abord pour accéder à la checklist.
        </Message>

        <template v-else-if="items">
            <!-- Section Pré-intervention -->
            <div class="section">
                <h2 class="section-title pre">🔍 Pré-intervention</h2>
                <div class="items-list">
                    <div
                        v-for="item in preItems"
                        :key="item.id"
                        class="checklist-item"
                        :class="{ checked: localChecked[item.id] }"
                    >
                        <div class="item-row">
                            <Checkbox
                                :binary="true"
                                :model-value="localChecked[item.id] ?? item.checked"
                                @update:model-value="toggleItem(item.id, $event)"
                            />
                            <span class="item-label">{{ item.label }}</span>
                        </div>
                        <Textarea
                            v-model="localNotes[item.id]"
                            :placeholder="'Note...'"
                            autoResize
                            rows="1"
                            class="item-note"
                            @update:model-value="markDirty(item.id)"
                        />
                    </div>
                </div>
            </div>

            <!-- Section Post-intervention -->
            <div class="section">
                <h2 class="section-title post">✅ Post-intervention</h2>
                <div class="items-list">
                    <div
                        v-for="item in postItems"
                        :key="item.id"
                        class="checklist-item"
                        :class="{ checked: localChecked[item.id] }"
                    >
                        <div class="item-row">
                            <Checkbox
                                :binary="true"
                                :model-value="localChecked[item.id] ?? item.checked"
                                @update:model-value="toggleItem(item.id, $event)"
                            />
                            <span class="item-label">{{ item.label }}</span>
                        </div>
                        <Textarea
                            v-model="localNotes[item.id]"
                            placeholder="Note..."
                            autoResize
                            rows="1"
                            class="item-note"
                            @update:model-value="markDirty(item.id)"
                        />
                    </div>
                </div>
            </div>

            <!-- Ajouter un item custom -->
            <div class="add-item-section">
                <InputText
                    v-model="newItemLabel"
                    placeholder="Ajouter un item..."
                    class="add-item-input"
                    @keyup.enter="addCustomItem"
                />
                <Button
                    label="Ajouter"
                    icon="pi pi-plus"
                    size="small"
                    :disabled="!newItemLabel.trim()"
                    @click="addCustomItem"
                />
            </div>

            <!-- Save button -->
            <Button
                label="Sauvegarder"
                icon="pi pi-check"
                severity="success"
                fluid
                :loading="saving"
                @click="handleSave"
            />

            <!-- Terminer button -->
            <Button
                label="Terminer l'intervention"
                icon="pi pi-check-circle"
                severity="danger"
                fluid
                :disabled="!allChecked && items && items.length > 0"
                v-tooltip="
                    !allChecked && items && items.length > 0 ? 'Cochez tous les items de la checklist d\'abord' : ''
                "
                :loading="completing"
                @click="handleComplete"
            />
        </template>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Textarea from "primevue/textarea";
import InputText from "primevue/inputtext";
import Skeleton from "primevue/skeleton";
import Message from "primevue/message";
import { useAuthStore } from "@/stores/auth";
import { api, checklistApi, jobsApi, type ChecklistItemRef } from "@/api/client";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const toast = useToast();
const queryClient = useQueryClient();

const jobId = Number(route.params.id);
const saving = ref(false);
const completing = ref(false);

// ── Local state for optimistic updates ──────────────────

const localChecked = ref<Record<number, boolean>>({});
const localNotes = ref<Record<number, string | null>>({});
const dirtyItems = ref<Set<number>>(new Set());

// ── Fetch job (to check status) ─────────────────────────

const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => jobsApi.getById(auth.token!, jobId),
    enabled: !!jobId,
});

// ── Fetch checklist items ───────────────────────────────

const {
    data: items,
    isLoading,
    isError,
    error,
    refetch,
} = useQuery({
    queryKey: ["checklist", jobId],
    queryFn: () => checklistApi.getItems(auth.token!, jobId),
    enabled: !!jobId,
});

// Initialiser l'état local via watcher
// N'écrase PAS les modifications locales déjà faites par l'utilisateur
watch(
    items,
    (newItems) => {
        if (newItems) {
            for (const item of newItems) {
                if (!(item.id in localChecked.value)) {
                    localChecked.value[item.id] = item.checked;
                }
                if (!(item.id in localNotes.value)) {
                    localNotes.value[item.id] = item.note;
                }
            }
        }
    },
    { immediate: true },
);

// ── Filter items by category ────────────────────────────

const preItems = computed(() =>
    (items.value || []).filter((i: ChecklistItemRef) => i.category === "pre_intervention"),
);

const postItems = computed(() =>
    (items.value || []).filter((i: ChecklistItemRef) => i.category === "post_intervention"),
);

const newItemLabel = ref("");

async function addCustomItem() {
    if (!newItemLabel.value.trim()) return;
    try {
        await api.post(
            `/jobs/${jobId}/checklist`,
            {
                label: newItemLabel.value.trim(),
                category: "post_intervention",
            },
            auth.token,
        );
        newItemLabel.value = "";
        queryClient.invalidateQueries({ queryKey: ["checklist", jobId] });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible d'ajouter",
            life: 3000,
        });
    }
}

// ── All checked? ────────────────────────────────────────

const allChecked = computed(() => {
    if (!items.value || items.value.length === 0) return true; // pas d'items = ok (backend accepte)
    return items.value.every((i: ChecklistItemRef) => localChecked.value[i.id] ?? i.checked);
});

// ── Complete job ────────────────────────────────────────

async function handleComplete() {
    completing.value = true;
    try {
        await api.put(`/jobs/${jobId}/complete`, { observations: null }, auth.token);
        toast.add({ severity: "success", summary: "Intervention terminee", life: 3000 });

        // Muter le cache job directement
        const cachedJob = queryClient.getQueryData(["job", jobId]) as any;
        if (cachedJob) {
            queryClient.setQueryData(["job", jobId], {
                ...cachedJob,
                status: "termine",
                completed_at: new Date().toISOString(),
            });
        }

        // Muter le cache dashboard
        const cachedDash = queryClient.getQueryData(["dashboard"]) as any;
        if (cachedDash) {
            queryClient.setQueryData(["dashboard"], {
                ...cachedDash,
                today: {
                    ...cachedDash.today,
                    jobs_in_progress: Math.max(0, (cachedDash.today.jobs_in_progress || 1) - 1),
                    jobs_completed: (cachedDash.today.jobs_completed || 0) + 1,
                },
                in_progress_job: null,
            });
        }

        // Naviguer vers le detail du job
        router.replace({ name: "JobDetail", params: { id: jobId } });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de terminer",
            life: 5000,
        });
    } finally {
        completing.value = false;
    }
}

// ── Actions ─────────────────────────────────────────────

function toggleItem(itemId: number, checked: boolean) {
    localChecked.value[itemId] = checked;
    dirtyItems.value.add(itemId);
}

function markDirty(itemId: number) {
    dirtyItems.value.add(itemId);
}

async function handleSave() {
    const allItems = items.value || [];
    const batch = allItems
        .filter((item: ChecklistItemRef) => dirtyItems.value.has(item.id))
        .map((item: ChecklistItemRef) => ({
            id: item.id,
            checked: localChecked.value[item.id] ?? item.checked,
            note: localNotes.value[item.id] ?? item.note,
        }));

    if (batch.length === 0) {
        toast.add({ severity: "info", summary: "Rien à sauvegarder", life: 2000 });
        return;
    }

    saving.value = true;
    try {
        await checklistApi.batchUpdate(auth.token!, jobId, batch);
        dirtyItems.value.clear();
        toast.add({ severity: "success", summary: "Checklist sauvegardée", life: 3000 });
        queryClient.invalidateQueries({ queryKey: ["checklist", jobId] });
        queryClient.invalidateQueries({ queryKey: ["job", jobId] });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de sauvegarder",
            life: 5000,
        });
    } finally {
        saving.value = false;
    }
}
</script>

<style scoped>
.inspection-page {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding-bottom: 100px;
}

.header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.header h1 {
    font-size: 1.3rem;
    font-weight: 700;
    margin: 0;
}

.section-title {
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 0.75rem;
}

.section-title.pre {
    color: #2563eb;
}
.section-title.post {
    color: #16a34a;
}

.items-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.checklist-item {
    background: white;
    border-radius: 8px;
    padding: 0.75rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
    transition: opacity 0.2s;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.checklist-item.checked {
    opacity: 0.7;
}

.item-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}

.item-label {
    font-size: 0.9rem;
    line-height: 1.4;
    color: #1f2937;
    flex: 1;
}

.checklist-item.checked .item-label {
    text-decoration: line-through;
    color: #9ca3af;
}

.item-note {
    margin-left: 1.75rem;
    font-size: 0.8rem;
}

.loading-state {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.mb-2 {
    margin-bottom: 0.5rem;
}
.mb-1 {
    margin-bottom: 0.25rem;
}

.add-item-section {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    padding: 0.5rem 0;
    border-top: 1px dashed #e5e7eb;
    margin-top: 0.5rem;
}

.add-item-input {
    flex: 1;
}
</style>
