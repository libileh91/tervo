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
            <Button label="Réessayer" icon="pi pi-refresh" fluid @click="refetch" class="mt-2" />
        </div>

        <template v-else-if="intervention">
            <!-- En-tête -->
            <div class="header">
                <Button icon="pi pi-arrow-left" text rounded @click="router.push({ name: 'Interventions' })" />
                <div class="header-info">
                    <h1>{{ intervention.title }}</h1>
                    <div class="header-chips">
                        <Chip :label="statusLabel(intervention.status)" :severity="statusSeverity(intervention.status)" size="small" />
                        <Chip
                            :label="priorityLabel(intervention.priority)"
                            :severity="prioritySeverity(intervention.priority)"
                            size="small"
                        />
                        <Chip :label="intervention.client?.full_name || '—'" severity="contrast" size="small" />
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
                    v-if="intervention.status === 'IN_PROGRESS'"
                    label="📋 Checklist"
                    severity="info"
                    fluid
                    @click="router.push({ name: 'Inspection', params: { id: intervention.id } })"
                />
                <Button
                    v-if="intervention.status === 'IN_PROGRESS'"
                    label="✅ Terminer"
                    severity="danger"
                    fluid
                    :loading="actionLoading"
                    @click="handleComplete"
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
                <TabPanel header="Infos">
                    <div class="info-grid">
                        <div class="info-field">
                            <label>Client</label>
                            <p>{{ intervention.client?.full_name || "—" }}</p>
                        </div>
                        <div class="info-field">
                            <label>Adresse</label>
                            <p>{{ intervention.client?.address || "—" }}</p>
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

                <TabPanel header="Checklist" :disabled="true">
                    <p class="placeholder-tab">
                        Disponible dans une prochaine version
                        <i class="pi pi-hourglass" />
                    </p>
                </TabPanel>

                <TabPanel header="Photos">
                    <div class="photos-tab">
                        <!-- Upload buttons -->
                        <div class="upload-buttons">
                            <Button
                                label="📷 Prendre une photo"
                                severity="info"
                                fluid
                                @click="triggerUpload('avant')"
                                :loading="uploading"
                            />
                            <Button
                                label="🖼 Choisir dans la galerie"
                                severity="info"
                                fluid
                                @click="triggerGalleryUpload('après')"
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
                        <div v-if="avantPhotos.length > 0" class="photo-section">
                            <h3 class="section-label avant">📸 Avant ({{ avantPhotos.length }})</h3>
                            <div class="photo-grid" :class="{ 'photo-grid--many': avantPhotos.length >= 3 }">
                                <div
                                    v-for="photo in avantPhotos"
                                    :key="photo.id"
                                    class="photo-card"
                                    @click="openPreview(photo.file_url)"
                                >
                                    <img :src="photo.thumbnail_url || photo.file_url" class="photo-thumb" />
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

                        <!-- Après -->
                        <div v-if="apresPhotos.length > 0" class="photo-section">
                            <h3 class="section-label apres">✅ Après ({{ apresPhotos.length }})</h3>
                            <div class="photo-grid" :class="{ 'photo-grid--many': apresPhotos.length >= 3 }">
                                <div
                                    v-for="photo in apresPhotos"
                                    :key="photo.id"
                                    class="photo-card"
                                    @click="openPreview(photo.file_url)"
                                >
                                    <img :src="photo.thumbnail_url || photo.file_url" class="photo-thumb" />
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
                            :header="null"
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

                <TabPanel header="Matériaux">
                    <div class="materials-tab">
                        <!-- Liste des matériaux existants -->
                        <div v-for="(mat, index) in materials" :key="mat.id" class="material-row">
                            <InputText
                                v-model="mat.name"
                                placeholder="Nom du matériau"
                                class="mat-input"
                                @update:model-value="markEdited(mat)"
                            />
                            <InputText
                                v-model="mat.quantity"
                                placeholder="Qté"
                                class="mat-qty"
                                @update:model-value="markEdited(mat)"
                            />
                            <Button
                                v-if="mat.id < 0"
                                icon="pi pi-check"
                                severity="success"
                                rounded
                                size="small"
                                @click="addMaterial(mat)"
                            />
                            <Button
                                v-else
                                icon="pi pi-save"
                                severity="info"
                                rounded
                                size="small"
                                @click="updateMaterial(mat)"
                            />
                            <Button
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

                <TabPanel header="Rapport">
                    <div v-if="intervention.status !== 'COMPLETED'" class="placeholder-tab">
                        <i class="pi pi-lock" />
                        <span>Rapport disponible après complétion</span>
                    </div>

                    <div v-else class="report-tab">
                        <div class="report-actions">
                            <Button
                                label="📥 Télécharger le PDF"
                                icon="pi pi-download"
                                severity="primary"
                                :loading="reportLoading"
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

                        <Message v-else-if="reportError" severity="error">
                            Impossible de charger le rapport.
                        </Message>
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
import {
    api,
    interventionsApi,
    materialsApi,
    photosApi,
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
const uploadCategory = ref<string>("avant");
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

// ── Computed photos by category ────────────────────────

const avantPhotos = computed(() => (intervention.value?.photos || []).filter((p: any) => p.category === "avant"));

const apresPhotos = computed(() => (intervention.value?.photos || []).filter((p: any) => p.category === "après"));

// ── Materials state ───────────────────────────────────────

interface MaterialRow {
    id: number;
    name: string;
    quantity: string | null;
}

const materials = ref<MaterialRow[]>([]);
const loadingMaterials = ref(false);
let tempIdCounter = 0;

// Charger les matériaux quand le intervention est chargé
watch(
    () => intervention.value?.materials,
    (mats) => {
        if (mats) {
            materials.value = mats.map((m: any) => ({
                id: m.id,
                name: m.name,
                quantity: m.quantity,
            }));
        }
    },
    { immediate: true },
);

function addRow() {
    tempIdCounter--;
    materials.value.push({ id: tempIdCounter, name: "", quantity: null });
}

function markEdited(mat: MaterialRow) {
    // Rien de spécial — le v-model fait le binding
}

async function addMaterial(mat: MaterialRow) {
    try {
        const created = await materialsApi.add(auth.token!, interventionId, {
            name: mat.name,
            quantity: mat.quantity || undefined,
        });
        mat.id = created.id;
        toast.add({ severity: "success", summary: "Matériau ajouté", life: 2000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
        toast.add({ severity: "error", summary: "Erreur", detail: err.detail || "Erreur", life: 4000 });
    }
}

async function updateMaterial(mat: MaterialRow) {
    try {
        await materialsApi.update(auth.token!, interventionId, mat.id, {
            name: mat.name,
            quantity: mat.quantity || undefined,
        });
        toast.add({ severity: "success", summary: "Matériau mis à jour", life: 2000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
        toast.add({ severity: "error", summary: "Erreur", detail: err.detail || "Erreur", life: 4000 });
    }
}

async function deleteMaterial(materialId: number) {
    try {
        await materialsApi.remove(auth.token!, interventionId, materialId);
        materials.value = materials.value.filter((m) => m.id !== materialId);
        toast.add({ severity: "success", summary: "Matériau supprimé", life: 2000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
        toast.add({ severity: "error", summary: "Erreur", detail: err.detail || "Erreur", life: 4000 });
    }
}

// ── Upload photo ───────────────────────────────────────

/** Ouvre l'appareil photo natif */
function triggerUpload(category: string) {
    uploadCategory.value = category;
    cameraInputRef.value?.click();
}

/** Ouvre la galerie */
function triggerGalleryUpload(category: string) {
    uploadCategory.value = category;
    galleryInputRef.value?.click();
}

async function onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];

    uploading.value = true;
    try {
        await photosApi.upload(auth.token!, interventionId, file, uploadCategory.value);
        toast.add({ severity: "success", summary: "Photo ajoutée", life: 3000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
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
    try {
        await photosApi.delete(auth.token!, interventionId, photoId);
        toast.add({ severity: "success", summary: "Photo supprimée", life: 3000 });
        queryClient.invalidateQueries({ queryKey: ["intervention", interventionId] });
    } catch (err: any) {
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

async function handleComplete() {
    actionLoading.value = true;
    try {
        await api.put(`/interventions/${interventionId}/complete`, { observations: null }, auth.token);
        toast.add({ severity: "success", summary: "Intervention terminee", life: 3000 });
        // Muter directement le intervention affiche
        intervention.value = { ...intervention.value!, status: "COMPLETED" as any, completed_at: new Date().toISOString() as any };
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        queryClient.invalidateQueries({ queryKey: ["interventions"] });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur",
            detail: err.detail || "Impossible de terminer",
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

/** Télécharge le PDF avec le token d'auth et crée une blob URL pour l'iframe. */
async function loadReport() {
    if (!intervention.value || intervention.value.status !== "COMPLETED") return;

    reportLoading.value = true;
    reportError.value = false;
    reportBlobUrl.value = null;

    try {
        const response = await fetch(`/api/v1/interventions/${interventionId}/report/download`, {
            headers: { Authorization: `Bearer ${auth.token}` },
        });

        if (!response.ok) throw new Error("Erreur chargement PDF");

        const blob = await response.blob();
        reportBlobUrl.value = URL.createObjectURL(blob);
    } catch {
        reportError.value = true;
    } finally {
        reportLoading.value = false;
    }
}

/** Télécharger le PDF via blob + anchor temporaire */
async function downloadReport() {
    if (!intervention.value || intervention.value.status !== "COMPLETED") return;

    reportLoading.value = true;
    try {
        const response = await fetch(`/api/v1/interventions/${interventionId}/report/download`, {
            headers: { Authorization: `Bearer ${auth.token}` },
        });
        if (!response.ok) throw new Error();

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `rapport-intervention-${interventionId}.pdf`;
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
