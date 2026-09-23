<template>
  <nav class="bottom-nav">
    <router-link
      v-for="tab in tabs"
      :key="tab.to"
      :to="tab.to"
      class="bottom-nav__item"
      :class="{ active: isActive(tab.to) }"
    >
      <i :class="tab.icon" class="bottom-nav__icon" />
      <span class="bottom-nav__label">{{ tab.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { to: '/', icon: 'pi pi-home', label: 'Accueil' },
  { to: '/interventions', icon: 'pi pi-list', label: 'Interventions' },
  { to: '/clients', icon: 'pi pi-users', label: 'Clients' },
  { to: '/profile', icon: 'pi pi-user', label: 'Profil' },
]

function isActive(path: string): boolean {
  return route.path === path
}
</script>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: #ffffff;
  border-top: 1px solid #e0e0e0;
  z-index: 1000;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.bottom-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  text-decoration: none;
  color: #6b7280;
  transition: color 0.2s;
  cursor: pointer;
  gap: 2px;
}

.bottom-nav__item.active {
  color: #3b82f6;
}

.bottom-nav__icon {
  font-size: 1.25rem;
}

.bottom-nav__label {
  font-size: 0.7rem;
  font-weight: 500;
}
</style>
