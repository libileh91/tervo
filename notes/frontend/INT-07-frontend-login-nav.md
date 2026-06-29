# INT-07 — Frontend : LoginPage + App.vue + BottomNav

> **Objectif** : Créer l'application frontend Vue.js avec authentification et navigation
> **Stack** : Vue 3 + Vite + TypeScript + Pinia + Vue Router + PrimeVue 4

---

## 1. Bun vs Node.js

Avant de commencer, on a fait le choix de remplacer **Node.js** par **Bun**.

| Critère | Node.js | Bun |
|---------|---------|-----|
| Install des dépendances | ~45s | **~6.5s** |
| Build production | ~3s | **~2s** |
| Dev server | V8 moteur | JavaScriptCore (20-40% + rapide) |
| Installation | `npm install` | `bun install` |
| Lancement | `npm run dev` | `bun dev` |

**Commande d'installation :** `bun install` au lieu de `npm install`

---

## 2. Structure du projet frontend

```
frontend/
├── index.html                   # Point d'entrée HTML
├── package.json                 # Dépendances (Bun)
├── tsconfig.json                # TypeScript config
├── tsconfig.node.json           # TS config pour Vite
├── vite.config.ts               # Vite + proxy API
└── src/
    ├── main.ts                  # Bootstrap App
    ├── App.vue                  # Root component + layout
    ├── env.d.ts                 # TypeScript declarations
    ├── api/
    │   └── client.ts            # API client (fetch sans Axios)
    ├── stores/
    │   └── auth.ts              # Pinia auth store
    ├── router/
    │   └── index.ts             # Routes + auth guard
    ├── components/
    │   └── BottomNav.vue        # Barre de navigation mobile
    └── pages/
        ├── LoginPage.vue        # Formulaire de connexion
        ├── DashboardPage.vue    # Accueil (placeholder)
        ├── JobsPage.vue         # Interventions (placeholder)
        ├── ClientsPage.vue      # Clients (placeholder)
        └── ProfilePage.vue      # Profil + déconnexion
```

---

## 3. PrimeVue 4 — Nouveau système de thème

PrimeVue 4 a changé son système de thème. Fini les imports CSS traditionnels :

```diff
- import 'primevue/resources/themes/lara-light-blue/theme.css'
+ import Lara from '@primevue/themes/lara'
```

Configuration dans `main.ts` :
```ts
import PrimeVue from 'primevue/config'
import Lara from '@primevue/themes/lara'

app.use(PrimeVue, {
  theme: {
    preset: Lara,
    options: {
      prefix: 'p',
      darkModeSelector: false,
      cssLayer: false,
    },
  },
})
```

---

## 4. API Client — Sans Axios

Fichier : `src/api/client.ts`

J'ai choisi de **ne pas utiliser Axios** pour éviter une dépendance lourde. Le `fetch` natif suffit :

```ts
async function request<T>(method: string, path: string, body?: unknown, token?: string | null): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`/api/v1${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined })

  if (!res.ok) {
    const err = { status: res.status, detail: (await res.json()).detail }
    throw err
  }
  return res.json()
}
```

**Points clés :**
- `/api/v1` est le préfixe de toutes les routes backend
- Le proxy Vite en dev redirige `/api` → `http://localhost:8000`
- Le token JWT est injecté automatiquement dans le header `Authorization`
- Les erreurs 401/404 sont propagées en exception

---

## 5. Auth Store (Pinia)

Fichier : `src/stores/auth.ts`

```ts
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('resq_access_token'))
  const user = ref<UserResponse | null>(null)

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password })
    token.value = res.access_token
    localStorage.setItem('resq_access_token', res.access_token)
    localStorage.setItem('resq_refresh_token', res.refresh_token)
    await fetchUser()  // ← charge le profil immédiatement
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('resq_access_token')
    localStorage.removeItem('resq_refresh_token')
  }
})
```

**Concepts :**
- **`ref()`** : état réactif Vue 3 (Composition API)
- **`localStorage`** : persistence du token entre les sessions
- **`login()`** : appelle l'API, stocke le token, charge l'utilisateur
- **`logout()`** : nettoie tout (token + store + localStorage)

---

## 6. Route Guard

Fichier : `src/router/index.ts`

```ts
router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated()) {
    next({ name: 'Login' })           // ← pas connecté → Login
  } else if (to.meta.guest && auth.isAuthenticated()) {
    next({ name: 'Dashboard' })       // ← connecté → Dashboard
  } else {
    next()
  }
})
```

**Comment ça marche :**
1. Avant chaque navigation, le guard vérifie `to.meta.requiresAuth`
2. Si la route est protégée et qu'il n'y a pas de token → redirection vers `/login`
3. Si la route est réservée aux invités (`/login`) et qu'on est connecté → redirection vers `/`

---

## 7. BottomNav — Navigation mobile

Fichier : `src/components/BottomNav.vue`

```vue
<nav class="bottom-nav">
  <router-link v-for="tab in tabs" :key="tab.to" :to="tab.to"
    :class="{ active: isActive(tab.to) }">
    <i :class="tab.icon" />
    <span>{{ tab.label }}</span>
  </router-link>
</nav>
```

**Caractéristiques :**
- **Fixe en bas** (`position: fixed; bottom: 0`)
- **4 onglets** : Accueil, Interventions, Clients, Profil
- **Icônes PrimeIcons** : `pi-home`, `pi-list`, `pi-users`, `pi-user`
- **Onglet actif** : coloré en bleu via la classe `.active`
- **Safe area** : `padding-bottom: env(safe-area-inset-bottom)` pour les iPhone X+

---

## 8. App.vue — Layout conditionnel

```vue
<template v-if="isLoginPage">
  <router-view />                 <!-- Login : plein écran, sans nav -->
</template>
<template v-else>
  <main class="app-content">
    <router-view />               <!-- Pages connectées -->
  </main>
  <BottomNav />                   <!-- Barre de navigation -->
</template>
```

**Pourquoi un layout conditionnel ?**
- La page de login doit être **plein écran** (pas de BottomNav)
- Les pages connectées ont **BottomNav en bas + padding** pour ne pas être cachées par la nav

---

## 9. Commandes

```bash
# Installer les dépendances (Bun)
cd frontend/
bun install

# Lancer le dev server (avec proxy API → backend)
bun dev

# Build production
bun run build
```

**Proxy Vite :** Le fichier `vite.config.ts` configure un proxy :
```ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // ← backend FastAPI
      changeOrigin: true,
    },
  },
}
```

Ainsi, en dev, les appels à `/api/v1/auth/login` sont automatiquement redirigés vers `http://localhost:8000/api/v1/auth/login`.

---

## 10. Résumé

```mermaid
flowchart TD
    subgraph Frontend [Frontend Vue.js]
        A[main.ts] --> B[App.vue]
        B --> C{Route actuelle?}
        C -->|/login| D[LoginPage.vue]
        C -->|Autres| E[Pages connectées]
        E --> F[BottomNav.vue]
        D --> G[authStore.login]
        G --> H[api/client.ts → POST /auth/login]
    end
    subgraph Backend [Backend FastAPI]
        I[/api/v1/auth/login]
    end
    H --> I
```
