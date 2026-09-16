<template>
  <div class="page">
    <h1>Profil</h1>

    <!-- Loading -->
    <div v-if="auth.loading" class="loading-state">
      <Skeleton height="40px" class="mb-2" />
      <Skeleton height="40px" class="mb-2" />
      <Skeleton height="40px" />
    </div>

    <!-- Empty / non connecté -->
    <div v-else-if="!auth.user" class="empty-state">
      <i class="pi pi-user" style="font-size: 3rem; color: #d1d5db" />
      <p class="empty-text">Impossible de charger le profil</p>
      <Button label="Réessayer" icon="pi pi-refresh" fluid @click="auth.fetchUser()" />
    </div>

    <!-- Données -->
    <div v-else class="profile-info">
      <p><strong>Nom :</strong> {{ auth.user.full_name }}</p>
      <p><strong>Identifiant :</strong> {{ auth.user.username }}</p>
      <p><strong>Email :</strong> {{ auth.user.email }}</p>
      <p><strong>Rôle :</strong> {{ auth.user.role }}</p>
    </div>

    <Button label="Se déconnecter" severity="danger" fluid @click="handleLogout" class="logout-btn" />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.page { padding: 1rem; display: flex; flex-direction: column; gap: 1rem; }
.page h1 { font-size: 1.4rem; font-weight: 700; margin: 0; }
.profile-info { display: flex; flex-direction: column; gap: 0.75rem; }
.profile-info p { margin: 0; font-size: 1rem; color: #374151; }
.profile-info p strong { color: #1f2937; display: inline-block; min-width: 5rem; }
.loading-state { display: flex; flex-direction: column; gap: 0.5rem; }
.empty-state { text-align: center; padding: 2rem 0; display: flex; flex-direction: column; gap: 1rem; align-items: center; }
.empty-text { color: #9ca3af; font-size: 1rem; margin: 0; }
.logout-btn { margin-top: 1rem; }
.mb-2 { margin-bottom: 0.5rem; }
</style>
