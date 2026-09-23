<template>
    <div class="review-page">
        <div class="review-card">
            <!-- En-tête -->
            <div class="review-header">
                <h1>Votre avis</h1>
                <p class="subtitle">Aidez-nous à améliorer notre service</p>
            </div>

            <!-- Loading -->
            <div v-if="isLoading" class="review-loading">
                <i class="pi pi-spin pi-spinner" style="font-size: 2rem" />
            </div>

            <!-- Token invalide / expiré -->
            <div v-else-if="isError" class="review-error">
                <i class="pi pi-exclamation-circle" style="font-size: 3rem; color: #f97316" />
                <h2>Ce lien n'est plus valable</h2>
                <p>Le lien d'avis a expiré ou est invalide.</p>
                <Button label="Réessayer" icon="pi pi-refresh" fluid @click="loadReviewData" class="mt-2" />
            </div>

            <!-- Données chargées -->
            <template v-else-if="reviewData">
                <!-- Infos intervention -->
                <div class="intervention-info">
                    <p class="intervention-title">{{ reviewData.intervention.title }}</p>
                    <p class="intervention-meta">Réalisée le {{ formatDate(reviewData.intervention.completed_at) }}</p>
                    <p class="intervention-meta" v-if="reviewData.technician.full_name">
                        Par {{ reviewData.technician.full_name }}
                    </p>
                </div>

                <!-- Déjà soumis : message de remerciement -->
                <div v-if="reviewData.already_reviewed" class="already-reviewed">
                    <i class="pi pi-check-circle" style="font-size: 3rem; color: #16a34a" />
                    <h2>Merci !</h2>
                    <p>Votre avis a bien été enregistré.</p>
                </div>

                <!-- Formulaire -->
                <form v-else @submit.prevent="handleSubmit" class="review-form">
                    <div class="field">
                        <label>Note</label>
                        <Rating v-model="rating" :stars="5" :cancel="false" />
                    </div>

                    <div class="field">
                        <label for="comment">Commentaire (optionnel)</label>
                        <Textarea
                            id="comment"
                            v-model="comment"
                            rows="4"
                            placeholder="Partagez votre expérience..."
                            :maxlength="2000"
                            fluid
                        />
                    </div>

                    <div class="field">
                        <label for="name">Votre nom (optionnel)</label>
                        <InputText
                            id="name"
                            v-model="reviewerName"
                            placeholder="Ex: M. Dupont"
                            :maxlength="255"
                            fluid
                        />
                    </div>

                    <Button
                        type="submit"
                        label="Envoyer mon avis"
                        icon="pi pi-send"
                        severity="primary"
                        fluid
                        :loading="submitting"
                    />
                </form>
            </template>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Rating from "primevue/rating";
import Textarea from "primevue/textarea";

// ── Route ──────────────────────────────────────────────

const route = useRoute();
const token = route.params.token as string;

// ── State ──────────────────────────────────────────────

const isLoading = ref(true);
const isError = ref(false);
const reviewData = ref<{
    intervention: { title: string; completed_at: string };
    technician: { full_name: string | null };
    already_reviewed: boolean;
} | null>(null);

const rating = ref<number>(0);
const comment = ref("");
const reviewerName = ref("");
const submitting = ref(false);

// ── Chargement des données ────────────────────────────

async function loadReviewData() {
    isLoading.value = true;
    isError.value = false;
    try {
        const res = await fetch(`/api/v1/review/${token}`);
        if (!res.ok) throw new Error("Not found");
        reviewData.value = await res.json();
    } catch {
        isError.value = true;
    } finally {
        isLoading.value = false;
    }
}

onMounted(loadReviewData);

// ── Soumission ────────────────────────────────────────

async function handleSubmit() {
    if (rating.value < 1) return;

    submitting.value = true;
    try {
        const res = await fetch(`/api/v1/review/${token}/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                rating: rating.value,
                comment: comment.value || null,
                reviewer_name: reviewerName.value || null,
            }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Erreur");
        }

        // Marquer comme soumis
        if (reviewData.value) {
            reviewData.value.already_reviewed = true;
        }
    } catch (err: any) {
        alert(err.message || "Impossible d'envoyer votre avis");
    } finally {
        submitting.value = false;
    }
}

// ── Helpers ────────────────────────────────────────────

function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
    });
}
</script>

<style scoped>
.review-page {
    min-height: 100dvh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.review-card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    padding: 2rem;
    width: 100%;
    max-width: 480px;
}

.review-header {
    text-align: center;
    margin-bottom: 1.5rem;
}

.review-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}

.subtitle {
    color: #6b7280;
    font-size: 0.9rem;
}

/* ── Loading ──────────────────────────── */
.review-loading {
    text-align: center;
    padding: 2rem 0;
    color: #667eea;
}

/* ── Error ────────────────────────────── */
.review-error {
    text-align: center;
    padding: 1.5rem 0;
}

.review-error h2 {
    margin: 0.75rem 0 0.25rem;
    font-size: 1.2rem;
    color: #1f2937;
}

.review-error p {
    color: #6b7280;
    font-size: 0.9rem;
}

/* ── Intervention info ─────────────────────────── */
.intervention-info {
    background: #f9fafb;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 1.5rem;
}

.intervention-title {
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 0.25rem;
}

.intervention-meta {
    color: #6b7280;
    font-size: 0.85rem;
    margin: 0.1rem 0;
}

/* ── Already reviewed ────────────────── */
.already-reviewed {
    text-align: center;
    padding: 1.5rem 0;
}

.already-reviewed h2 {
    margin: 0.75rem 0 0.25rem;
    font-size: 1.3rem;
    color: #1f2937;
}

.already-reviewed p {
    color: #6b7280;
}

/* ── Form ─────────────────────────────── */
.review-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

.field {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}

.field label {
    font-size: 0.9rem;
    font-weight: 600;
    color: #374151;
}
</style>
