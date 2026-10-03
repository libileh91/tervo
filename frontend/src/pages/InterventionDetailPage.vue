<template>
    <div class="detail-page">
        <!-- Loading -->
        <div v-if="isLoading" class="loading-state">
            <Skeleton height="40px" class="mb-2" />
            <Skeleton height="120px" />
        </div>

        <!-- Error -->
        <div v-else-if="isError" class="error-state">
            <Message severity="error">
                Impossible de charger l'intervention : {{ error?.message || "Erreur inconnue" }}
            </Message>
            <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch()" class="mt-2" />
        </div>

        <template v-else-if="intervention">
            <!-- En-tête -->
            <div class="header">
                <Button icon="pi pi-arrow-left" text rounded @click="router.push({ name: 'Interventions' })" />
                <div class="header-info">
                    <h1>{{ intervention.title }}</h1>
                    <div class="header-chips">
                        <Chip :label="statusLabel(intervention.status)" :severity="statusSeverity(intervention.status)" size="small" />
                        <Chip :label="`Résultat : ${interventionResultLabel(intervention.result)}`" size="small" />
                        <Chip
                            :label="priorityLabel(intervention.priority)"
                            :severity="prioritySeverity(intervention.priority)"
                            size="small"
                        />
                        <Chip :label="intervention.site?.name || '—'" severity="contrast" size="small" />
                    </div>
                </div>
            </div>

            <!-- Actions -->
            <div class="actions">
                <Button
                    v-if="intervention.status === 'PLANNED'"
                    label="▶ Démarrer"
                    severity="success"
                    fluid
                    :loading="actionLoading"
                    @click="handleStart"
                />
                <Button
                    v-if="intervention.status === 'PLANNED'"
                    label="❌ Annuler"
                    severity="warn"
                    fluid
                    @click="showCancelDialog = true"
                />
                <Button
                    label="📋 Checklist"
                    severity="info"
                    fluid
                    @click="router.push({ name: 'Inspection', params: { id: intervention.id } })"
                />
                <Button
                    v-if="intervention.status === 'IN_PROGRESS'"
                    label="✅ Vérifier et terminer"
                    severity="danger"
                    fluid
                    :loading="actionLoading"
                    @click="router.push({ name: 'Inspection', params: { id: intervention.id } })"
                />
                <Button
                    v-if="intervention.status === 'PLANNED' || intervention.status === 'CANCELLED'"
                    label="Supprimer"
                    severity="secondary"
                    fluid
                    @click="showDeleteDialog = true"
                />
            </div>

            <!-- Onglets -->
            <TabView>
                <TabPanel value="0" header="Infos">
                    <div class="info-grid">
                        <div class="info-field">
                            <label>Site</label>
                            <p>{{ intervention.site?.name || "—" }}</p>
                        </div>
                        <div class="info-field">
                            <label>Adresse</label>
                            <p>{{ intervention.site?.address || "—" }}</p>
                        </div>
                        <div class="info-field">
                            <label>Technicien</label>
                            <p>{{ intervention.technician?.full_name || "Non assigné" }}</p>
                        </div>
                        <div class="info-field">
                            <label>Date planifiée</label>
                            <p>{{ intervention.scheduled_date }}</p>
                        </div>
                        <div class="info-field" v-if="intervention.scheduled_start_time">
                            <label>Créneau</label>
                            <p>
                                {{ intervention.scheduled_start_time
                                }}{{ intervention.scheduled_end_time ? ` - ${intervention.scheduled_end_time}` : "" }}
                            </p>
                        </div>
                        <div class="info-field" v-if="intervention.started_at">
                            <label>Démarré le</label>
                            <p>{{ formatDate(intervention.started_at) }}</p>
                        </div>
                        <div class="info-field" v-if="intervention.completed_at">
                            <label>Terminé le</label>
                            <p>{{ formatDate(intervention.completed_at) }}</p>
                        </div>
                        <div class="info-field" v-if="intervention.description">
                            <label>Description</label>
                            <p>{{ intervention.description }}</p>
                        </div>
                        <div class="info-field" v-if="intervention.observations">
                            <label>Observations</label>
                            <p>{{ intervention.observations }}</p>
                        </div>
                    </div>
                </TabPanel>

                <TabPanel value="1" header="Checklist" :disabled="true">
                    <p class="placeholder-tab">
                        Disponible dans une prochaine version
                        <i class="pi pi-hourglass" />
                    </p>
                </TabPanel>

                <TabPanel value="2" header="Photos">
                    <div class="photos-tab">
                        <!-- Upload buttons -->
                        <label for="photo-usage">Usage de la photo</label>
                        <select id="photo-usage" v-model="uploadUsage" :disabled="uploading">
                            <option v-for="usage in photoUsages" :key="usage.value" :value="usage.value">{{ usage.label }}</option>
                        </select>
                        <Message v-if="photoError" severity="error">{{ photoError }}</Message>
                        <div class="upload-buttons">
                            <Button
                                label="📷 Prendre une photo"
                                severity="info"
                                fluid
                                @click="triggerUpload"
                                :loading="uploading"
                            />
                            <Button
                                label="🖼 Choisir dans la galerie"
                                severity="info"
                                fluid
                                @click="triggerGalleryUpload"
                                :loading="uploading"
                            />
                        </div>
                        <!-- Input caméra (capture=environment) -->
                        <input
                            ref="cameraInputRef"
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            capture="environment"
                            class="hidden-input"
                            @change="onFileSelected"
                        />
                        <!-- Input galerie (sans capture) -->
                        <input
                            ref="galleryInputRef"
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            class="hidden-input"
                            @change="onFileSelected"
                        />

                        <!-- Avant -->
                        <div v-for="group in photoGroups" :key="group.value" class="photo-section">
                            <h3 class="section-label">{{ group.label }} ({{ group.photos.length }})</h3>
                            <div class="photo-grid" :class="{ 'photo-grid--many': group.photos.length >= 3 }">
                                <div
                                    v-for="photo in group.photos"
                                    :key="photo.id"
                                    class="photo-card"
                                    @click="openPreview(photo.file_url)"
                                >
                                    <img :src="photo.thumbnail_url || photo.file_url" :alt="group.label" class="photo-thumb" />
                                    <Button
                                        icon="pi pi-trash"
                                        severity="danger"
                                        rounded
                                        size="small"
                                        class="delete-btn"
                                        @click.stop="deletePhoto(photo.id)"
                                    />
                                </div>
                            </div>
                        </div>

                        <p v-if="!intervention.photos || intervention.photos.length === 0" class="empty-photos">
                            Aucune photo pour l'instant.
                        </p>

                        <!-- Preview Dialog -->
                        <Dialog
                            v-model:visible="showPreview"
                            :header="undefined"
                            modal
                            dismissableMask
                            :style="{ maxWidth: '95vw', maxHeight: '90vh' }"
                            :closable="true"
                            @hide="previewPhoto = null"
                        >
                            <img v-if="previewPhoto" :src="previewPhoto" class="preview-image" alt="Photo preview" />
                        </Dialog>
                    </div>
                </TabPanel>

                <TabPanel value="3" header="Matériaux">
                    <div class="materials-tab">
                        <!-- Liste des matériaux existants -->
                        <div v-for="mat in materials" :key="mat.id" class="material-row">
                            <InputText
                                v-model="mat.designation"
                                placeholder="Désignation"
                                aria-label="Désignation"
                                :maxlength="255"
                                :disabled="mat.saving"
                                class="mat-input"
                                @update:model-value="markEdited(mat)"
                            />
                            <input
                                v-model="mat.quantity"
                                type="number"
                                min="0.001"
                                max="999999999.999"
                                step="0.001"
                                aria-label="Quantité"
                                :disabled="mat.saving"
                                placeholder="Qté"
                                class="mat-qty"
                                @input="markEdited(mat)"
                            />
                            <InputText v-model="mat.unit" placeholder="Unité (ex. pièce)"
                                aria-label="Unité" :maxlength="50" :disabled="mat.saving"
                                @update:model-value="markEdited(mat)" />
                            <Message v-if="mat.error" severity="error">{{ mat.error }}</Message>
                            <Button
                                v-if="mat.id < 0"
                                :loading="mat.saving"
                                icon="pi pi-check"
                                severity="success"
                                rounded
                                size="small"
                                @click="addMaterial(mat)"
                            />
                            <Button
                                v-else
                                :loading="mat.saving"
                                icon="pi pi-save"
                                severity="info"
                                rounded
                                size="small"
                                @click="updateMaterial(mat)"
                            />
                            <Button
                                :disabled="mat.saving"
                                icon="pi pi-trash"
                                severity="danger"
                                rounded
                                size="small"
                                @click="deleteMaterial(mat.id)"
                            />
                        </div>

                        <p v-if="materials.length === 0 && !loadingMaterials" class="empty-materials">
                            Aucun matériau saisi.
                        </p>

                        <Button
                            label="➕ Ajouter un matériau"
                            icon="pi pi-plus"
                            severity="success"
                            fluid
                            @click="addRow"
                        />
                    </div>
                </TabPanel>

                <TabPanel value="4" header="Rapport">
                    <div v-if="intervention.status !== 'COMPLETED'" class="placeholder-tab">
                        <i class="pi pi-lock" />
                        <span>Rapport disponible après complétion</span>
                    </div>
                    <Message v-else-if="!canAccessReport" severity="info">
                        Rapport réservé à l'administrateur ou au technicien assigné.
                    </Message>

                    <div v-else class="report-tab">
                        <div class="report-actions">
                            <Button :label="reportMetadata ? 'Générer une nouvelle version' : 'Générer le rapport'"
                                :loading="reportLoading" @click="generateReport" />
                            <select v-if="reportMetadata" v-model.number="reportVersion" aria-label="Version du rapport"
                                :disabled="reportLoading" @change="loadReport">
                                <option v-for="version in reportMetadata.versions" :key="version.id" :value="version.version">
                                    Version {{ version.version }} — {{ version.transmitted_at ? 'Transmission confirmée' : 'Générée' }}
                                </option>
                            </select>
                            <Button v-if="selectedReportVersion && !selectedReportVersion.transmitted_at"
                                label="Confirmer la transmission externe" :disabled="reportLoading" @click="confirmReportTransmission" />
                            <Button
                                label="📥 Télécharger le PDF"
                                icon="pi pi-download"
                                severity="primary"
                                :loading="reportLoading"
                                :disabled="!reportMetadata || reportLoading"
                                @click="downloadReport"
                            />
                        </div>

                        <div v-if="reportLoading" class="loading-state">
                            <Skeleton height="400px" />
                        </div>

                        <iframe
                            v-else-if="reportBlobUrl"
                            :src="reportBlobUrl"
                            class="pdf-preview"
                            title="Aperçu du rapport"
                        />

                        <div v-else-if="reportError">
                            <Message severity="error">Impossible de charger le rapport.</Message>
                            <Button label="Réessayer" @click="loadReport" />
                        </div>
                        <Message v-else-if="!reportMetadata" severity="info">Aucune version archivée. Générer explicitement le premier rapport.</Message>
                        <p v-if="selectedReportVersion?.transmitted_at">Transmission confirmée manuellement le {{ formatDate(selectedReportVersion.transmitted_at) }}. Aucun email envoyé par Tervo.</p>
                    </div>
                </TabPanel>
            </TabView>
        </template>

        <!-- Dialog annulation -->
        <Dialog v-model:visible="showCancelDialog" header="Confirmer l'annulation" modal>
            <p>Annuler cette intervention ? Cette action est réversible (vous pourrez la réactiver plus tard).</p>
            <div class="dialog-actions">
                <Button label="Non" severity="secondary" fluid @click="showCancelDialog = false" />
                <Button label="Oui, annuler" severity="warn" fluid :loading="cancelLoading" @click="handleCancel" />
            </div>
        </Dialog>

        <!-- Dialog suppression -->
        <Dialog v-model:visible="showDeleteDialog" header="Confirmer la suppression" modal>
            <p>Supprimer cette intervention ? Cette action est irréversible.</p>
            <div class="dialog-actions">
                <Button label="Annuler" severity="secondary" fluid @click="showDeleteDialog = false" />
                <Button label="Confirmer" severity="danger" fluid :loading="actionLoading" @click="handleDelete" />
            </div>
        </Dialog>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { useToast } from "primevue/usetoast";
import Button from "primevue/button";
import Chip from "primevue/chip";
import InputText from "primevue/inputtext";
import Skeleton from "primevue/skeleton";
import Message from "primevue/message";
import TabView from "primevue/tabview";
import TabPanel from "primevue/tabpanel";
import Dialog from "primevue/dialog";
import { useAuthStore } from "@/stores/auth";
import { interventionResultLabel } from "@/composables/interventionCompletion";
import { groupPhotos, photoUsages, reconcileMaterials, materialRow, validateMaterial, type MaterialRow } from "@/utils/interventionMedia";
import type { PhotoUsage } from "@/api/client";
import {
    api,
    interventionsApi,
    materialsApi,
    photosApi,
    reportsApi,
    statusSeverity,
    statusLabel,
    prioritySeverity,
    priorityLabel,
} from "@/api/client";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const toast = useToast();
const queryClient = useQueryClient();

const interventionId = Number(route.params.id);
const showDeleteDialog = ref(false);
const showCancelDialog = ref(false);
const actionLoading = ref(false);
const cancelLoading = ref(false);

// ── Photos state ───────────────────────────────────────

const cameraInputRef = ref<HTMLInputElement | null>(null);
const galleryInputRef = ref<HTMLInputElement | null>(null);
const uploadUsage = ref<PhotoUsage>("BEFORE");
const photoError = ref<string | null>(null);
const uploading = ref(false);
const showPreview = ref(false);
const previewPhoto = ref<string | null>(null);

function openPreview(fileUrl: string) {
    previewPhoto.value = fileUrl;
    showPreview.value = true;
}

// ── Fetch intervention detail ────────────────────────────────────

const {
    data: intervention,
    isLoading,
    isError,
    error,
    refetch,
} = useQuery({
    queryKey: ["intervention", interventionId],
    queryFn: () => interventionsApi.getById(auth.token!, interventionId),
    enabled: !!interventionId,
});

const photoGroups = computed(() => groupPhotos(intervention.value?.photos || []));

// ── Materials state ───────────────────────────────────────

const materials = ref<MaterialRow[]>([]);
const loadingMaterials = ref(false);
let tempIdCounter = 0;

// Charger les matériaux quand le intervention est chargé
watch(
    () => intervention.value?.materials,
    (mats) => {
        if (mats) {
            materials.value = reconcileMaterials(materials.value, mats);
        }
    },
    { immediate: true },
);

function addRow() {
    tempIdCounter--;
    materials.value.push({ id: tempIdCounter, designation: "", quantity: 1, unit: "pièce",
        dirty: true, saving: false, error: null });
}

function markEdited(mat: MaterialRow) {
    mat.dirty = true;
    mat.error = null;
}

async function addMaterial(mat: MaterialRow) {
    await saveMaterial(mat);
}

async function updateMaterial(mat: MaterialRow) {
    await saveMaterial(mat);
}

async function saveMaterial(mat: MaterialRow) {
    if (mat.saving) return;
    const result = validateMaterial(mat);
    if (!result.data) {
        mat.error = result.error;
        return;
    }
    mat.saving = true;
    mat.error = null;
    try {
        const saved = mat.id < 0
            ? await materialsApi.add(auth.token!, interventionId, result.data)
            : await materialsApi.update(auth.token!, interventionId, mat.id, result.data);
        Object.assign(mat, materialRow(saved), { saving: true });
        toast.add({ severity: "success", summary: "Matériau enregistré", life: 2000 });
        await queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
        mat.error = err.message || "Impossible d’enregistrer le matériau.";
        toast.add({ severity: "error", summary: "Erreur", detail: err.detail || "Erreur", life: 4000 });
    } finally {
        mat.saving = false;
    }
}

async function deleteMaterial(materialId: number) {
    if (materialId < 0) {
        materials.value = materials.value.filter((m) => m.id !== materialId);
        return;
    }
    const row = materials.value.find((m) => m.id === materialId);
    if (!row || row.saving) return;
    row.saving = true;
    row.error = null;
    try {
        await materialsApi.remove(auth.token!, interventionId, materialId);
        materials.value = materials.value.filter((m) => m.id !== materialId);
        toast.add({ severity: "success", summary: "Matériau supprimé", life: 2000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
        row.error = err.message || "Impossible de supprimer le matériau.";
        toast.add({ severity: "error", summary: "Erreur", detail: err.detail || "Erreur", life: 4000 });
    } finally {
        row.saving = false;
    }
}

// ── Upload photo ───────────────────────────────────────

/** Ouvre l'appareil photo natif */
function triggerUpload() {
    cameraInputRef.value?.click();
}

/** Ouvre la galerie */
function triggerGalleryUpload() {
    galleryInputRef.value?.click();
}

async function onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];

    uploading.value = true;
    photoError.value = null;
    try {
        await photosApi.upload(auth.token!, interventionId, file, uploadUsage.value);
        toast.add({ severity: "success", summary: "Photo ajoutée", life: 3000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
        photoError.value = err.message || "Impossible d’ajouter la photo.";
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible d'uploader la photo",
            life: 5000,
        });
    } finally {
        uploading.value = false;
        input.value = ""; // reset input
    }
}

// ── Delete photo ───────────────────────────────────────

async function deletePhoto(photoId: number) {
    photoError.value = null;
    try {
        await photosApi.delete(auth.token!, interventionId, photoId);
        toast.add({ severity: "success", summary: "Photo supprimée", life: 3000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
        photoError.value = err.message || "Impossible de supprimer la photo.";
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de supprimer",
            life: 5000,
        });
    }
}

// ── Start intervention ───────────────────────────────────────────

async function handleStart() {
    actionLoading.value = true;
    try {
        await api.put(`/interventions/${interventionId}/start`, {}, auth.token);
        toast.add({ severity: "success", summary: "Intervention demarre", life: 3000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
        queryClient.invalidateQueries({ queryKey: ["interventions"] });
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de demarrer",
            life: 5000,
        });
    } finally {
        actionLoading.value = false;
    }
}

// ── Cancel intervention ─────────────────────────────────────────

async function handleCancel() {
    cancelLoading.value = true;
    try {
        await api.put(`/interventions/${interventionId}/cancel`, {}, auth.token);
        toast.add({ severity: "success", summary: "Intervention annulé", life: 3000 });
        showCancelDialog.value = false;
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible d'annuler",
            life: 5000,
        });
    } finally {
        cancelLoading.value = false;
    }
}

// ── Delete intervention ──────────────────────────────────────────

async function handleDelete() {
    actionLoading.value = true;
    try {
        await api.delete(`/interventions/${interventionId}`, auth.token);
        toast.add({ severity: "success", summary: "Intervention supprimé", life: 3000 });
        showDeleteDialog.value = false;
        router.push({ name: "Interventions" });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de supprimer",
            life: 5000,
        });
    } finally {
        actionLoading.value = false;
    }
}

// ── Helpers ─────────────────────────────────────────────

// ── Report (PDF) ──────────────────────────────────────────

const reportLoading = ref(false);
const reportError = ref(false);
const reportBlobUrl = ref<string | null>(null);
const reportMetadata = ref<import("@/api/client").ReportMetadata | null>(null);
const reportVersion = ref<number | null>(null);
const reportRequestKey = ref<string | null>(null);
const selectedReportVersion = computed(() => reportMetadata.value?.versions.find(v => v.version === reportVersion.value));
const canAccessReport = computed(() => auth.user?.role === "admin"
    || auth.user?.id === intervention.value?.technician?.id);

/** Télécharge le PDF avec le token d'auth et crée une blob URL pour l'iframe. */
async function loadReport() {
    if (!intervention.value || intervention.value.status !== "COMPLETED") return;

    reportLoading.value = true;
    reportError.value = false;
    if (reportBlobUrl.value) URL.revokeObjectURL(reportBlobUrl.value);
    reportBlobUrl.value = null;

    try {
        reportMetadata.value = await reportsApi.getForIntervention(auth.token!, interventionId);
        if (!reportMetadata.value.versions.some(v => v.version === reportVersion.value)) {
            reportVersion.value = reportMetadata.value.versions[reportMetadata.value.versions.length - 1]?.version ?? null;
        }
        if (reportVersion.value === null) return;
        const blob = await reportsApi.file(auth.token!, reportMetadata.value.id, reportVersion.value);
        reportBlobUrl.value = URL.createObjectURL(blob);
    } catch (error: unknown) {
        if ((error as { status?: number }).status === 404) {
            reportMetadata.value = null;
            reportVersion.value = null;
        } else reportError.value = true;
    } finally {
        reportLoading.value = false;
    }
}

async function generateReport() {
    if (reportLoading.value || !canAccessReport.value) return;
    reportLoading.value = true;
    reportRequestKey.value ??= crypto.randomUUID();
    try {
        const version = await reportsApi.generate(auth.token!, interventionId, reportRequestKey.value);
        reportVersion.value = version.version;
        reportRequestKey.value = null;
        await loadReport();
    } catch (error: unknown) {
        toast.add({ severity: "error", summary: "Génération refusée", detail: (error as { detail?: string }).detail || "Réessayer avec la même clé", life: 5000 });
    } finally { reportLoading.value = false; }
}

async function confirmReportTransmission() {
    if (reportLoading.value || !canAccessReport.value || !reportMetadata.value || reportVersion.value === null) return;
    if (!window.confirm("Confirmer que cette version précise a été transmise hors de Tervo ? Aucun email ne sera envoyé.")) return;
    reportLoading.value = true;
    try {
        await reportsApi.confirmTransmission(auth.token!, reportMetadata.value.id, reportVersion.value);
        await loadReport();
    } catch (error: unknown) {
        toast.add({ severity: "error", summary: "Confirmation refusée", detail: (error as { detail?: string }).detail || "Erreur", life: 5000 });
    } finally { reportLoading.value = false; }
}

/** Télécharger le PDF via blob + anchor temporaire */
async function downloadReport() {
    if (!canAccessReport.value || !reportMetadata.value || reportVersion.value === null) return;

    reportLoading.value = true;
    try {
        const blob = await reportsApi.file(auth.token!, reportMetadata.value.id, reportVersion.value);
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `rapport-${reportMetadata.value.id}-v${reportVersion.value}.pdf`;
        anchor.click();
        URL.revokeObjectURL(url);
    } catch {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: "Impossible de télécharger le rapport",
            life: 5000,
        });
    } finally {
        reportLoading.value = false;
    }
}

/** Charger le rapport quand le intervention est terminé */
watch(
    () => intervention.value?.status,
    (status) => {
        if (status === "COMPLETED") {
            loadReport();
        } else {
            reportBlobUrl.value = null;
            reportError.value = false;
        }
    },
);

function formatDate(iso: string): string {
    return new Date(iso).toLocaleString("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}
</script>

<style scoped>
.detail-page {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.header {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.header-info {
    flex: 1;
}

.header-info h1 {
    font-size: 1.3rem;
    font-weight: 700;
    margin: 0 0 0.5rem;
}

.header-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}

.actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.info-grid {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.info-field label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.info-field p {
    margin: 0.2rem 0 0;
    font-size: 0.95rem;
    color: #1f2937;
}

.placeholder-tab {
    text-align: center;
    color: #9ca3af;
    font-style: italic;
    padding: 2rem 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}

.placeholder-tab i {
    font-size: 2rem;
    color: #d1d5db;
}

.dialog-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
}

.loading-state {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.mb-2 {
    margin-bottom: 0.5rem;
}

/* ── Photos tab ────────────────────────────── */
.photos-tab {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.upload-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.hidden-input {
    display: none;
}
.section-label {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 0.5rem;
}
.section-label.avant {
    color: #2563eb;
}
.section-label.apres {
    color: #16a34a;
}
.photo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
}
.photo-grid--many {
    grid-template-columns: repeat(3, 1fr);
}
.photo-card {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
    cursor: pointer;
    transition: transform 0.15s ease;
}
.photo-card:active {
    transform: scale(0.96);
}
.photo-thumb {
    width: 100%;
    height: 160px;
    object-fit: cover;
    display: block;
}
.delete-btn {
    position: absolute;
    top: 4px;
    right: 4px;
    opacity: 0.85;
}
.empty-photos {
    color: #9ca3af;
    text-align: center;
    padding: 1rem 0;
}

/* ── Preview Dialog ─────────────────────────── */
.preview-image {
    width: 100%;
    height: auto;
    display: block;
    border-radius: 4px;
}

/* ── Materials tab ──────────────────────────── */
.materials-tab {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.material-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}
.mat-input {
    flex: 1;
    min-width: 0;
}
.mat-qty {
    width: 80px;
    flex-shrink: 0;
}
.empty-materials {
    color: #9ca3af;
    text-align: center;
    padding: 1rem 0;
}

/* ── Report tab (INT-35) ────────────────────────── */
.report-tab {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.report-actions {
    display: flex;
    justify-content: flex-end;
}
.pdf-preview {
    width: 100%;
    height: 500px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
</style>
