<template>
  <div class="page">
    <h1>Profil</h1>
    <div v-if="auth.user" class="profile-info">
      <p><strong>Nom :</strong> {{ auth.user.full_name }}</p>
      <p><strong>Identifiant :</strong> {{ auth.user.username }}</p>
      <p><strong>Email :</strong> {{ auth.user.email }}</p>
      <p><strong>Rôle :</strong> {{ auth.user.role }}</p>
    </div>
    <Button label="Se déconnecter" severity="danger" @click="handleLogout" />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Button from 'primevue/button'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.page { padding: 1rem; }
.profile-info { margin-bottom: 1.5rem; }
.profile-info p { margin: 0.5rem 0; }
</style>
