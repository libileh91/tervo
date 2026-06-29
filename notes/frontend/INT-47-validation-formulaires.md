# INT-47 — Validation formulaires (Zod + VeeValidate)

> **Objectif :** Ajouter la validation frontend des formulaires avec Zod + VeeValidate.
> **Date :** 25/06/2026

---

## Stack

```
Zod v3          → Schémas de validation (type-safe, messages en français)
@vee-validate/zod → Pont entre Zod et VeeValidate (useForm + useField)
VeeValidate v4  → Gestion des états (errors, meta.valid, isSubmitting)
```

---

## Fichier central : `frontend/src/composables/useFormValidation.ts`

Tous les schémas Zod sont centralisés dans un seul fichier :

```typescript
// ── Login ────────────────────────────────────────────────
export const loginSchema = z.object({
  username: z.string().min(1).min(3, 'Minimum 3 caractères'),
  password: z.string().min(1).min(3, 'Minimum 3 caractères'),
})

// ── Client ───────────────────────────────────────────────
export const clientCreateSchema = z.object({
  full_name: z.string().min(2).max(255),
  phone: z.string().regex(/^0[1-9]\d{8}$/, 'Numéro invalide'),
  address: z.string().min(5).max(500),
  email: z.string().email('Email invalide').optional().or(z.literal('')),
  postal_code: z.string().regex(/^\d{5}$/, '5 chiffres').optional().or(z.literal('')),
  // ...
})

// ── Job ──────────────────────────────────────────────────
export const jobSchema = z.object({
  client_id: z.number().int().positive('Sélectionnez un client'),
  title: z.string().min(3).max(255),
  scheduled_date: z.string().min(1, 'Date requise'),
  priority: z.enum(['basse', 'normale', 'haute', 'urgente']).default('normale'),
})
```

---

## Pattern d'utilisation dans un Vue composant

```vue
<script setup lang="ts">
import { useForm, useField } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { loginSchema } from '@/composables/useFormValidation'

// 1. Initialiser le formulaire avec le schéma Zod
const { handleSubmit, errors, meta, isSubmitting } = useForm({
  validationSchema: toTypedSchema(loginSchema),
})

// 2. Lier chaque champ
const { value: username } = useField<string>('username')
const { value: password } = useField<string>('password')

// 3. Soumission type-safe (values est typé automatiquement)
const onSubmit = handleSubmit(async (values) => {
  await auth.login(values.username, values.password)
})
</script>

<template>
  <form @submit.prevent="onSubmit">
    <InputText
      v-model="username"
      :invalid="!!errors.username"      <!-- bordure rouge si erreur -->
    />
    <small v-if="errors.username" class="error-msg">
      {{ errors.username }}              <!-- message d'erreur -->
    </small>

    <Button
      type="submit"
      :disabled="!meta.valid && meta.touched"  <!-- bouton désactivé si invalide -->
      :loading="isSubmitting"
    />
  </form>
</template>
```

---

## Formulaires modifiés

| Page | Formulaires | Validation |
|------|------------|------------|
| `LoginPage.vue` | Identifiant + Mot de passe | `loginSchema` |
| `ClientsPage.vue` | Dialogue "Nouveau client" | `clientCreateSchema` (7 champs avec regex téléphone/CP) |
| `JobsPage.vue` | Dialogue "Nouvelle intervention" | `jobSchema` (5 champs + sélecteur client) |

**Patterns VeeValidate utilisés :**
- `useForm({ validationSchema })` → wrapper du formulaire
- `useField('fieldName')` → liaison champ individuel
- `errors.fieldName` → message d'erreur (mis à jour en temps réel)
- `meta.valid` → true si tous les champs sont valides
- `meta.touched` → true si au moins un champ a été modifié
- `isSubmitting` → true pendant la soumission (désactive le bouton)

---

## Validation des schémas

```bash
# Build frontend
cd frontend/
bun run build

# Preview
bun run preview
```

---

## Résultat

| Critère | Statut |
|---------|--------|
| Schémas Zod pour Login / Client / Job / Material | ✅ |
| Messages d'erreur en français | ✅ |
| Validation à la volée (au fur et à mesure) | ✅ |
| Bouton submit désactivé si invalide | ✅ |
| Build frontend (0 erreur) | ✅ |

---

> **Prochaine tâche :** INT-DPL — Config 1Panel : build image, DB, reverse proxy
