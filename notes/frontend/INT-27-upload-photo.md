# INT-27 — Frontend Upload photo (appareil natif + galerie)

> **Objectif** : Activer l'onglet Photos dans JobDetailPage avec upload natif et galerie
> **Stack** : Vue 3 + PrimeVue + FormData + `capture="environment"`

---

## 1. Ce qui a été fait

| Fichier                       | Action                                                                                                         |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `src/api/client.ts`           | `api.upload()` (FormData sans Content-Type), `photosApi` (upload/delete), `materialsApi` (préparé pour INT-28) |
| `src/pages/JobDetailPage.vue` | Onglet Photos activé avec upload + preview + delete                                                            |

---

## 2. Upload multipart sans Axios

```ts
// api/client.ts — fonction uploadFile dédiée
async function uploadFile<T>(path: string, formData: FormData, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  // NE PAS définir Content-Type — le navigateur le fait avec le boundary

  const res = await fetch(`${API_BASE}${path}`, { method: "POST", headers, body: formData });
  return res.json();
}
```

**Pourquoi une fonction séparée ?** Le `request()` standard met `Content-Type: application/json` ce qui empêche l'upload de fichiers. `uploadFile()` n'a pas de Content-Type → fetch utilise `multipart/form-data; boundary=...` automatiquement.

---

## 3. Appareil natif vs galerie

```vue
<!-- Appareil photo natif (mobile) -->
<input type="file" accept="image/jpeg,image/png" capture="environment" @change="onFileSelected" />

<!-- Galerie (desktop) → même input sans capture -->
```

**`capture="environment"`** : sur mobile, ouvre directement l'appareil photo arrière. Sur desktop, ignoré.

Les deux boutons utilisent le **même** `<input>` caché — seule la `category` change :

```ts
function triggerUpload(category: string) {
  uploadCategory.value = category; // "avant" ou "après"
  fileInputRef.value?.click(); // ouvre le file picker
}
```

---

## 4. Affichage par catégorie

```ts
const avantPhotos = computed(() => job.value?.photos.filter((p) => p.category === "avant") || []);
const apresPhotos = computed(() => job.value?.photos.filter((p) => p.category === "après") || []);
```

Les photos sont filtrées côté client depuis `job.photos` (déjà chargé via `GET /jobs/{id}`).

---

## 5. Invalidation du cache

```ts
async function deletePhoto(photoId: number) {
  await photosApi.delete(auth.token!, jobId, photoId);
  queryClient.invalidateQueries({ queryKey: ["job", jobId] });
  // ← le cache est marqué périmé → Vue Query re-fetch automatiquement
}
```

Après upload ou suppression, on invalide `['job', jobId]` pour que la grille des photos se mette à jour sans rafraîchissement manuel.
