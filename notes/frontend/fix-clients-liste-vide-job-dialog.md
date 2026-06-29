# Fix — Bug#2 : Formulaire création job bloqué

> **Date :** 26/06/2026
> **Cause racine :** Validation Zod/VeeValidate trop stricte + caractères échappés + import manquant.

---

## Problème 1 — Zod bloquait le formulaire

```typescript
// COMPOSANT AVANT — VeeValidate + Zod
const { handleSubmit, errors, meta } = useForm({
    validationSchema: toTypedSchema(jobSchema),
});
const { value: jobTitle } = useField<string>("title");
const { value: jobClientId } = useField<number>("client_id");
// ...
```

- `useField<number>` démarre à `undefined`, mais `z.number()` rejette `undefined` → erreur "Ce champ est requis"
- Le Select renvoie `undefined` tant qu'aucun client n'est sélectionné → même problème
- Les erreurs apparaissent avant même que l'utilisateur touche le formulaire

**Solution :** Vire VeeValidate/Zod. Refs simples + validation manuelle.

```typescript
// COMPOSANT APRES — Refs simples
const newJobTitle = ref("");
const newJobClientId = ref<number | null>(null);
const newJobDescription = ref("");

async function onSubmitJob() {
    if (!newJobClientId.value) {
        toast.add({ severity: "error", summary: "Client requis" });
        return;
    }
    const title = newJobTitle.value.trim()
        || newJobDescription.value.trim().slice(0, 80)
        || "Intervention";
    // ... appel API
}
```

---

## Problème 2 — Caractères échappés (\\u00e9 au lieu de é)

L'outil `edit_file` échappait les accents dans le JSON. Résultat : `\u00e9` stocké **littéralement** dans le fichier → placeholders invisibles.

```
placeholder="Ex: D\u00e9pannage chaudi\u00e8re"   ← stocké comme ça
```

Corrigé avec `sed` :
```bash
sed -i 's/\\u00e9/é/g; s/\\u00e8/è/g; s/\\u00e0/à/g' *.vue
```

Fichiers corrigés : `JobsPage.vue`, `JobDetailPage.vue`, `useFormValidation.ts`.

---

## Problème 3 — Import InputText manquant

Le champ Titre utilisait `<InputText>` mais l'import n'avait pas été ajouté.

```typescript
// AVANT
import Textarea from "primevue/textarea";

// APRES
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
```

---

## Formulaire final

```
Client     → Select (dropdown chargé au clic)
Titre      → InputText (fallback: description ou "Intervention")
Description → Textarea (optionnel)
Date       → DatePicker (fallback: aujourd'hui)
Priorité   → Select (normale par défaut)
```

---

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `JobsPage.vue` | Retrait Zod/VeeValidate, refs simples, ajout titre, fix imports |
| `useFormValidation.ts` | Corrigé `\u00e9` → `é` |
| `JobDetailPage.vue` | Corrigé `\u00e9` → `é` |
