# INT-36 : Frontend — ReviewPage publique (star rating + commentaire)

## Contexte

Page **publique** accessible via le lien `https://resq.app/review/{share_token}`.
Le client peut noter l'intervention (1-5 étoiles), laisser un commentaire
optionnel, et donner son nom (optionnel) — **sans création de compte**.

---

## Architecture

### Fichiers créés / modifiés

| Fichier | Changement |
|---|---|
| `frontend/src/pages/ReviewPage.vue` | **Nouveau** — page publique complète |
| `frontend/src/router/index.ts` | Route `/review/:token` ajoutée avec `meta: { hideNav: true }` |
| `frontend/src/App.vue` | Layout : `hideNav` remplace `isLoginPage` |

---

## 1. Route — `/review/:token`

```typescript
{
    path: "/review/:token",
    name: "Review",
    component: () => import("@/pages/ReviewPage.vue"),
    meta: { hideNav: true, title: "Votre avis" },
}
```

**Points clés :**
- **Pas de `requiresAuth`** → accessible sans login
- **Pas de `guest`** → accessible même connecté (un tech peut prévisualiser)
- **`hideNav: true`** → pas de BottomNav, layout fullscreen comme la page Login

### Impact sur `App.vue`

Avant :
```typescript
const isLoginPage = computed(() => route.path === '/login')
```

Après :
```typescript
const hideNav = computed(() => route.meta.hideNav === true)
```

| Route | Avant | Après |
|---|---|---|
| `/login` | ✅ pas de nav | ✅ pas de nav (meta.hideNav=true implicite via guest) |
| `/review/:token` | ❌ avait BottomNav | ✅ pas de nav (meta.hideNav=true explicite) |
| Autres routes | ✅ BottomNav | ✅ BottomNav |

---

## 2. Template — 4 états

```vue
<div v-if="isLoading">
  <!-- Spinner de chargement -->
</div>

<div v-else-if="isError">
  <!-- Token invalide / expiré -->
  <i class="pi pi-exclamation-circle" />
  <h2>Ce lien n'est plus valable</h2>
</div>

<template v-else-if="reviewData">
  <!-- Infos job (toujours visible) -->
  <div class="job-info">
    <p>{{ reviewData.job.title }}</p>
    <p>Réalisée le {{ formatDate(reviewData.job.completed_at) }}</p>
    <p v-if="reviewData.technician.full_name">Par {{ ... }}</p>
  </div>

  <!-- Déjà soumis ? -->
  <div v-if="reviewData.already_reviewed">
    <h2>Merci !</h2>
    <p>Votre avis a bien été enregistré.</p>
  </div>

  <!-- Sinon : formulaire -->
  <form v-else @submit.prevent="handleSubmit">
    <Rating v-model="rating" :stars="5" :cancel="false" />
    <Textarea v-model="comment" />
    <InputText v-model="reviewerName" />
    <Button type="submit" :loading="submitting">Envoyer mon avis</Button>
  </form>
</template>
```

### `v-if`/`v-else-if`/`v-else` hiérarchie

```
isLoading → isError → reviewData
                         ├── already_reviewed → "Merci !"
                         └── else → formulaire
```

C'est un arbre de décision à 4 branches mutuellement exclusives.

---

## 3. Script — fetch sans auth

```typescript
const token = useRoute().params.token as string;

// GET (pas de Bearer — endpoint public)
const res = await fetch(`/api/v1/review/${token}`);
if (!res.ok) throw new Error("Not found");
reviewData.value = await res.json();

// POST (pas de Bearer — endpoint public)
const res = await fetch(`/api/v1/review/${token}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        rating: rating.value,
        comment: comment.value || null,
        reviewer_name: reviewerName.value || null,
    }),
});
```

**Différence avec les appels API classiques :**
```typescript
// Appel authentifié (avec token)
headers: { Authorization: `Bearer ${auth.token}` }

// Appel public (sans token) — INT-36
// Pas de header Authorization du tout
```

---

## 4. PrimeVue Rating

```vue
<Rating v-model="rating" :stars="5" :cancel="false" />
```

| Prop | Rôle |
|---|---|
| `v-model="rating"` |双向 binding → `rating.value` (number 0-5) |
| `:stars="5"` | Nombre d'étoiles (défaut : 5) |
| `:cancel="false"` | Cache le bouton "annuler" (remettre à 0) |

---

## 5. Design

```css
.review-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.review-card {
    max-width: 480px;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
```

- **Gradient violet** (#667eea → #764ba2) pour un aspect professionnel
- **Card blanche centrée** (max 480px) comme sur les pages de paiement
- **Pas de BottomNav** → `meta: { hideNav: true }` dans le routeur
- **Pas de padding-bottom** (contrairement aux pages avec BottomNav qui ont `72px`)

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `frontend/src/pages/ReviewPage.vue` | Page publique : 4 états, formulaire, design épuré |
| `frontend/src/router/index.ts` | Route + meta.hideNav |
| `frontend/src/App.vue` | Layout conditionnel basé sur hideNav |
