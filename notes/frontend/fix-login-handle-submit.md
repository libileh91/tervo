# Fix : Login bloqué sur la page de connexion

> **Date :** 25/06/2026
> **Contexte :** Après INT-47 (validation Zod+VeeValidate), impossible de se connecter — aucun log backend/frontend/console.

---

## Cause

```vue
<!-- ❌ AVANT : la factory handleSubmit est appelée comme event handler -->
<form @submit.prevent="handleSubmit">
```

Avec VeeValidate, `useForm()` retourne `handleSubmit` qui est une **factory function**. Elle attend un callback et retourne le vrai handler :

```typescript
const { handleSubmit, errors, meta, isSubmitting } = useForm({
  validationSchema: toTypedSchema(loginSchema),
})

// handleSubmit = factory function
// onSubmit     = le vrai handler (handleSubmit appelé avec le callback)
const onSubmit = handleSubmit(async (values) => {
  await auth.login(values.username, values.password)
  router.push('/')
})
```

En faisant `@submit.prevent="handleSubmit"`, on appelait la factory sans callback → elle retournait `undefined` → rien ne se passait.

## Correction

```vue
<!-- ✅ APRÈS : le vrai handler onSubmit est appelé -->
<form @submit.prevent="onSubmit">
```

## Leçon

Avec VeeValidate `useForm()` :
- `handleSubmit` = **factory** (prend un callback)
- `const onSubmit = handleSubmit(callback)` = **handler** (à utiliser dans le template)

Toujours stocker le résultat de `handleSubmit()` dans une variable et utiliser celle-ci dans `@submit.prevent`.

---

## Fichier modifié

- `frontend/src/pages/LoginPage.vue` → ligne 9 : `handleSubmit` → `onSubmit`
