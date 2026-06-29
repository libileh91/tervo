# INT-35 : Frontend — Onglet Rapport avec iframe PDF

## Contexte

L'onglet "Rapport" dans `JobDetailPage` était désactivé (`:disabled="true"`) avec
un simple message "Disponible dans une prochaine version". Il devient actif et
affiche :

- Un message si le job n'est pas terminé
- Un **iframe** avec le PDF intégré + bouton téléchargement si le job est terminé

---

## Architecture

```
JobDetailPage.vue
  └── TabPanel header="Rapport"
       ├── job.status !== 'terminé'
       │   └── "📄 Rapport disponible après complétion"
       │
       └── job.status === 'terminé'
           ├── Button "📥 Télécharger le PDF"
           ├── loading state → Skeleton height=400px
           ├── iframe :src=reportBlobUrl   ← blob URL
           └── error state → Message "Impossible de charger"
```

---

## 1. Template

```vue
<TabPanel header="Rapport">
  <!-- Job non terminé -->
  <div v-if="job.status !== 'terminé'" class="placeholder-tab">
    <i class="pi pi-lock" />
    <span>Rapport disponible après complétion</span>
  </div>

  <!-- Job terminé -->
  <div v-else class="report-tab">
    <div class="report-actions">
      <Button
        label="📥 Télécharger le PDF"
        icon="pi pi-download"
        severity="primary"
        :loading="reportLoading"
        @click="downloadReport"
      />
    </div>

    <div v-if="reportLoading" class="loading-state">
      <Skeleton height="400px" />
    </div>

    <iframe
      v-else-if="reportBlobUrl"
      :src="reportBlobUrl"
      class="pdf-preview"
      title="Aperçu du rapport"
    />

    <Message v-else-if="reportError" severity="error">
      Impossible de charger le rapport.
    </Message>
  </div>
</TabPanel>
```

## 2. Script

### Pourquoi blob URL au lieu d'un src direct ?

L'endpoint PDF nécessite un **Bearer token** dans le header `Authorization`.
Un `<iframe :src="/api/v1/jobs/14/report/download">` enverrait une requête
**sans header** → HTTP 401.

**Solution** : fetch avec auth → `response.blob()` → `URL.createObjectURL(blob)`.

```typescript
const reportLoading = ref(false);
const reportError = ref(false);
const reportBlobUrl = ref<string | null>(null);

/** Charge le PDF et crée une blob URL pour l'iframe */
async function loadReport() {
  if (!job.value || job.value.status !== 'terminé') return;

  reportLoading.value = true;
  reportError.value = false;
  reportBlobUrl.value = null;

  try {
    const response = await fetch(`/api/v1/jobs/${jobId}/report/download`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    });
    if (!response.ok) throw new Error();

    const blob = await response.blob();
    reportBlobUrl.value = URL.createObjectURL(blob);
  } catch {
    reportError.value = true;
  } finally {
    reportLoading.value = false;
  }
}

/** Déclenche le téléchargement via un anchor temporaire */
async function downloadReport() {
  if (!job.value || job.value.status !== 'terminé') return;

  reportLoading.value = true;
  try {
    const response = await fetch(`/api/v1/jobs/${jobId}/report/download`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    });
    if (!response.ok) throw new Error();

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `rapport-intervention-${jobId}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);  // nettoie la mémoire
  } catch {
    toast.add({ severity: "error", summary: "Erreur", detail: "Impossible de télécharger le rapport", life: 5000 });
  } finally {
    reportLoading.value = false;
  }
}

/** Watch : charge auto le rapport quand le job devient terminé */
watch(
  () => job.value?.status,
  (status) => {
    if (status === 'terminé') {
      loadReport();
    } else {
      reportBlobUrl.value = null;
      reportError.value = false;
    }
  },
);
```

### Points clés du script

| Concept | Explication |
|---|---|
| **`response.blob()`** | Convertit la réponse HTTP en **Blob** (Binary Large Object) — idéal pour les PDF, images, etc. |
| **`URL.createObjectURL(blob)`** | Crée une URL temporaire `blob:http://localhost:5173/xxx` pointant vers le blob en mémoire. Valide le temps de la session. |
| **`URL.revokeObjectURL(url)`** | Libère la mémoire allouée au blob. À appeler après usage. |
| **`document.createElement('a')` + `.click()`** | Technique standard pour déclencher un téléchargement côté JS sans navigation. |
| **Watch sur `job.value?.status`** | Charge auto le PDF dès que le statut passe à 'terminé' (après avoir cliqué "Terminer"). |

---

## 3. Styles

```css
.report-tab {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
.report-actions {
    display: flex;
    justify-content: flex-end;
}
.pdf-preview {
    width: 100%;
    height: 500px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
```

Le `height: 500px` est suffisant pour un aperçu sur desktop et mobile.
Le `border-radius: 8px` adoucit les bords.

---

## Fichier modifié

| Fichier | Changement |
|---|---|
| `frontend/src/pages/JobDetailPage.vue` | TabPanel "Rapport" activé, iframe + blob URL, bouton download, watch auto-chargement, styles |

## Notes

- **Pas de changement backend nécessaire** — le endpoint `GET /jobs/{id}/report/download` existe déjà (INT-30)
- **Blob URL** = solution propre qui évite de mettre le token dans l'URL (query param)
- **`URL.revokeObjectURL()`** est appelé juste après le clic sur le lien de téléchargement — pas de fuite mémoire
- **PrimeVue `Button` avec `:loading="reportLoading"`** : désactive le bouton et affiche un spinner pendant le chargement


---

## Récapitulatif INT-35 ✅

### Changement

| Fichier | Changement |
|---|---|
| `frontend/src/pages/JobDetailPage.vue` | Onglet "Rapport" activé avec iframe PDF (blob URL), bouton download, watch auto-chargement, 3 états (loading/ok/error) |

### Fonctionnement

```
Job non terminé → 🔒 "Rapport disponible après complétion"
Job terminé     → fetch /api/v1/jobs/{id}/report/download (with Bearer)
                   → response.blob()
                   → URL.createObjectURL(blob)
                   → <iframe :src="blobUrl" />
                   + Button @click → downloadReport() (anchor.click())
```

### Défi technique résolu

L'iframe ne peut pas envoyer le header `Authorization: Bearer`. Solution : **fetch avec auth → blob → blob URL**. Même technique pour le bouton télécharger (anchor temporaire avec `download` attribute).

### Note pédagogique

Créée dans `notes/frontend/INT-35-onglet-rapport.md` avec explications détaillées sur `response.blob()`, `URL.createObjectURL()`, `URL.revokeObjectURL()`, et le pattern `document.createElement('a') + .click()`.
