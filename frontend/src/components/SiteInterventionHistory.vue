<template>
    <section aria-label="Historique des interventions">
        <Skeleton v-if="isLoading" height="60px" />
        <div v-else-if="isError">
            <Message severity="error">Impossible de charger l'historique.</Message>
            <Button label="Réessayer" @click="refetch()" />
        </div>
        <template v-else-if="data">
            <p v-if="!data.items.length">Aucune intervention.</p>
            <article v-for="item in data.items" :key="item.id">
                <RouterLink :to="{ name: 'InterventionDetail', params: { id: item.id } }">{{ item.title }}</RouterLink>
                <p>Statut : {{ statusLabel(item.status) }} — Résultat : {{ interventionResultLabel(item.result) }}</p>
                <p v-if="item.technician_name">{{ item.technician_name }}</p>
            </article>
            <div v-if="data.pages > 1">
                <Button label="Précédent" :disabled="page <= 1 || isFetching" @click="page--" />
                <span>Page {{ data.page }} / {{ data.pages }}</span>
                <Button label="Suivant" :disabled="page >= data.pages || isFetching" @click="page++" />
            </div>
        </template>
    </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import Button from "primevue/button";
import Message from "primevue/message";
import Skeleton from "primevue/skeleton";
import { sitesApi, statusLabel } from "@/api/client";
import { interventionResultLabel } from "@/composables/interventionCompletion";
import { useAuthStore } from "@/stores/auth";

const props = defineProps<{ siteId: number }>();
const auth = useAuthStore();
const page = ref(1);
const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ["site-interventions", () => props.siteId, page],
    queryFn: () => sitesApi.getInterventions(auth.token!, props.siteId, page.value),
});
</script>
