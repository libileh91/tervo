<template>
    <div class="inspection-page">
        <div class="header">
            <Button icon="pi pi-arrow-left" text rounded @click="router.push({ name: 'InterventionDetail', params: { id: interventionId } })" />
            <h1>Inspection</h1>
        </div>
        <Skeleton v-if="isLoading || interventionLoading" height="120px" />
        <div v-else-if="isError || interventionError">
            <Message severity="error">Impossible de charger l'inspection.</Message>
            <Button label="Réessayer" @click="retry" />
        </div>
        <template v-else-if="snapshot">
            <h2>{{ snapshot.template_name || 'Checklist sans modèle' }}
                <small v-if="snapshot.template_version !== null">— version {{ snapshot.template_version }}</small>
            </h2>
            <Message v-if="!canEdit" severity="info">Seul le technicien assigné peut modifier une intervention planifiée ou en cours.</Message>
            <Message v-if="!items.length" severity="info">Cette checklist ne contient aucun item.</Message>
            <section v-for="group in groups" :key="group.category">
                <h3>{{ categoryLabel(group.category) }}</h3>
                <div v-for="item in group.items" :key="item.id" class="checklist-item">
                    <div class="item-row">
                        <Checkbox :binary="true" :model-value="drafts[item.id]?.result != null"
                            :disabled="!canEdit || completing"
                            @update:model-value="toggleItem(item.id, $event)" />
                        <span>{{ item.label }}</span>
                        <small v-if="drafts[item.id]?.result != null">Résultat : {{ drafts[item.id]?.result }}</small>
                    </div>
                    <InputText :model-value="drafts[item.id]?.result ?? ''" maxlength="100"
                        placeholder="Résultat (vide = en attente)" fluid :disabled="!canEdit || completing"
                        @update:model-value="updateResult(item.id, $event)" />
                    <Textarea :model-value="drafts[item.id]?.comment" placeholder="Commentaire..."
                        autoResize rows="1" fluid :disabled="!canEdit || completing"
                        @update:model-value="updateComment(item.id, $event)" />
                    <Message v-if="saveErrors[item.id]" severity="error">{{ saveErrors[item.id] }}</Message>
                </div>
            </section>
            <Button label="Sauvegarder" icon="pi pi-check" severity="success" fluid
                :loading="saving" :disabled="!canEdit || !dirtyItems.size || completing" @click="handleSave" />
            <Message v-if="dirtyItems.size" severity="warn">Sauvegardez les modifications avant de terminer.</Message>
            <Button v-if="intervention?.status === 'IN_PROGRESS'" label="Terminer l'intervention"
                severity="danger" fluid :disabled="!canComplete" :loading="completing" @click="handleComplete" />
        </template>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Textarea from "primevue/textarea";
import InputText from "primevue/inputtext";
import Skeleton from "primevue/skeleton";
import Message from "primevue/message";
import { useAuthStore } from "@/stores/auth";
import { api, checklistApi, interventionsApi, type ChecklistSnapshot } from "@/api/client";
import { acknowledgeSavedDraft, checkboxResult, refreshCleanDrafts, type ChecklistDraft } from "@/composables/checklistDrafts";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const toast = useToast();
const queryClient = useQueryClient();
const interventionId = Number(route.params.id);
const saving = ref(false);
const completing = ref(false);
const drafts = ref<Record<number, ChecklistDraft>>({});
const dirtyItems = ref(new Set<number>());
const saveErrors = ref<Record<number, string>>({});
const { data: intervention, isLoading: interventionLoading, isError: interventionError, refetch: refetchIntervention } = useQuery({
    queryKey: ["intervention", interventionId],
    queryFn: () => interventionsApi.getById(auth.token!, interventionId),
});
const { data: snapshot, isLoading, isError, refetch } = useQuery({
    queryKey: ["checklist", interventionId],
    queryFn: () => checklistApi.getSnapshot(auth.token!, interventionId),
});
const items = computed(() => [...(snapshot.value?.items || [])].sort((a, b) => a.position - b.position));
watch(snapshot, (value) => {
    refreshCleanDrafts(drafts.value, dirtyItems.value, value?.items || []);
}, { immediate: true });
const canEdit = computed(() => !!auth.user && intervention.value?.technician?.id === auth.user.id
    && ["PLANNED", "IN_PROGRESS"].includes(intervention.value?.status || ""));
const canComplete = computed(() => canEdit.value && intervention.value?.status === "IN_PROGRESS"
    && !!snapshot.value && !isError.value && !dirtyItems.value.size && !saving.value && !completing.value
    && items.value.every(item => item.result !== null));
const groups = computed(() => [...new Set(items.value.map(item => item.category))]
    .map(category => ({ category, items: items.value.filter(item => item.category === category) })));
function categoryLabel(category: string) {
    return ({ pre_intervention: "Pré-intervention", post_intervention: "Post-intervention" } as Record<string, string>)[category] || category;
}
function toggleItem(id: number, checked: boolean) {
    if (!canEdit.value || completing.value) return;
    drafts.value[id].result = checkboxResult(drafts.value[id].result, checked);
    dirtyItems.value.add(id);
}
function updateComment(id: number, comment: string | undefined) {
    if (!canEdit.value || completing.value) return;
    drafts.value[id].comment = comment ?? null;
    dirtyItems.value.add(id);
}
function updateResult(id: number, result: string | undefined) {
    if (!canEdit.value || completing.value) return;
    drafts.value[id].result = result || null;
    dirtyItems.value.add(id);
}
async function retry() {
    await Promise.all([refetch(), refetchIntervention()]);
}
function errorMessage(error: unknown) {
    return (error as { detail?: string; message?: string })?.detail
        || (error as { message?: string })?.message || "Impossible de sauvegarder cet item.";
}
async function handleSave() {
    if (!canEdit.value || saving.value || completing.value) return;
    const pending = [...dirtyItems.value].map(id => ({ id, data: { ...drafts.value[id] } }));
    if (!pending.length) return;
    saving.value = true;
    try {
        await queryClient.cancelQueries({ queryKey: ["checklist", interventionId] });
        await Promise.all(pending.map(async ({ id, data }) => {
            try {
                const updated = await checklistApi.updateItem(auth.token!, id, data);
                queryClient.setQueryData<ChecklistSnapshot>(["checklist", interventionId], previous => previous
                    ? { ...previous, items: previous.items.map(item => item.id === id ? updated : item) } : previous);
                delete saveErrors.value[id];
                acknowledgeSavedDraft(drafts.value, dirtyItems.value, id, data, updated);
            } catch (error) {
                saveErrors.value[id] = errorMessage(error);
            }
        }));
        const failures = pending.filter(({ id }) => saveErrors.value[id]).length;
        toast.add({ severity: failures ? "error" : "success",
            summary: failures ? `${failures} item(s) non sauvegardé(s)` : "Modifications sauvegardées", life: 5000 });
        await queryClient.invalidateQueries({ queryKey: ["checklist", interventionId] });
    } finally {
        saving.value = false;
    }
}
async function handleComplete() {
    if (!canComplete.value) return;
    completing.value = true;
    try {
        await api.put(`/interventions/${interventionId}/complete`, { observations: null }, auth.token);
        await Promise.all(["intervention", "interventions", "dashboard"].map(key =>
            queryClient.invalidateQueries({ queryKey: key === "intervention" ? [key, interventionId] : [key] })));
        completing.value = false;
        await router.push({ name: "InterventionDetail", params: { id: interventionId } });
    } catch (error) {
        toast.add({ severity: "error", summary: "Impossible de terminer", detail: errorMessage(error), life: 5000 });
    } finally {
        completing.value = false;
    }
}
onBeforeRouteLeave(() => {
    if (saving.value || completing.value) return false;
    return !dirtyItems.value.size || window.confirm("Quitter sans sauvegarder les modifications ?");
});
</script>

<style scoped>
.inspection-page { padding: 1rem 1rem 100px; display: flex; flex-direction: column; gap: 1rem; }
.header, .item-row { display: flex; align-items: center; gap: .75rem; }
.checklist-item { padding: 1rem; margin-bottom: .75rem; border: 1px solid var(--p-content-border-color); border-radius: .5rem; }
.item-row { margin-bottom: .5rem; flex-wrap: wrap; }
</style>
