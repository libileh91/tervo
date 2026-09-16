# INT-38 — Responsive mobile (layout bottom nav, plein écran)

> **Date :** 13/07/2026
> **Fichiers modifiés :** `index.html`, `App.vue`, `BottomNav.vue`, `DashboardPage.vue`, `JobsPage.vue`, `ClientsPage.vue`, `ClientDetailPage.vue`, `JobDetailPage.vue`, `InspectionPage.vue`, `ProfilePage.vue`, `LoginPage.vue`, `ReviewPage.vue`

---

## 1. `100dvh` — Viewport dynamique mobile

### Problème
`100vh` sur mobile inclut la hauteur de la barre d'adresse du navigateur. Quand l'utilisateur scroll, la barre d'adresse disparaît, la `vh` change, mais `100vh` ne se met pas à jour → espace blanc en bas.

### Solution
```css
#app {
    min-height: 100dvh;
}
```

`dvh` = *dynamic viewport height* — s'adapte en temps réel à la barre d'adresse qui se rétracte.

### Pages concernées
- `App.vue` — `#app` et `.app`
- `LoginPage.vue` — `.login-page`
- `ReviewPage.vue` — `.review-page`

---

## 2. Safe area iPhone X+ (notch + home indicator)

### Problème
Les iPhone X et plus récents ont un "home indicator" en bas de l'écran. Sans `safe-area-inset-bottom`, la BottomNav et le contenu peuvent être masqués.

### Solution

**1. `index.html`** — Activer le viewport `fit-cover` pour que le CSS puisse utiliser les `env()` :
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
```

**2. `BottomNav.vue`** — Ajouter un padding pour que les icônes ne soient pas derrière le home indicator :
```css
.bottom-nav {
    padding-bottom: env(safe-area-inset-bottom, 0);
}
```

**3. `App.vue`** — Éviter que le contenu soit masqué par la nav + safe area :
```css
.app-content {
    padding-bottom: calc(60px + 12px + env(safe-area-inset-bottom, 0px));
}
```

### `env(safe-area-inset-bottom)` — Comment ça marche
- `env()` est une fonction CSS qui donne accès aux variables d'environnement du navigateur
- `safe-area-inset-bottom` = la hauteur de la zone non-affichable en bas (0 sur Android sans notch, 34px sur iPhone X+)
- La valeur de fallback `, 0` garantit le fonctionnement sur les appareils sans safe area

---

## 3. `font-size: 16px` — Éviter le zoom automatique iOS

### Problème
Sur iOS Safari, quand un `<input>` ou `<textarea>` a une `font-size < 16px`, le navigateur zoome automatiquement quand l'élément reçoit le focus. Très gênant pour l'utilisateur qui doit pinch-unzoom ensuite.

### Solution — Règle CSS globale
```css
input,
textarea,
select,
.p-inputtext,
.p-password input,
.p-datepicker input,
.p-select-label,
.p-inputtextarea {
    font-size: 16px !important;
}
```

Sélecteurs PrimeVue inclus pour couvrir les composants PrimeVue qui utilisent leurs propres classes internes (`p-inputtext`, `p-password input`, etc.).

---

## 4. PrimeVue `fluid` — Boutons full width

### Principe
Le prop `fluid` dans PrimeVue est équivalent à `width: 100%` :
```html
<Button label="Réessayer" fluid />
```

### Audit complet des boutons `fluid` ajoutés

| Page | Bouton | État avant |
|------|--------|-----------|
| **DashboardPage** | "Réessayer" | ❌ manquait `fluid` |
| **DashboardPage** | "Nouveau job" (empty state) | ❌ manquait `fluid` |
| **JobsPage** | "Nouveau job" (header) | ❌ manquait `fluid` |
| **JobsPage** | "Réessayer" | ❌ manquait `fluid` |
| **JobsPage** | "Nouveau job" (empty state) | ❌ manquait `fluid` |
| **JobsPage** | Dialog "Annuler" / "Créer" | ❌ manquait `fluid` |
| **ClientsPage** | "Nouveau client" (header) | ❌ manquait `fluid` |
| **ClientsPage** | "Réessayer" | ❌ manquait `fluid` |
| **ClientsPage** | Dialog "Annuler" / "Créer" | ❌ manquait `fluid` |
| **ClientDetailPage** | Dialog "Annuler" / "Confirmer" | ❌ manquait `fluid` |
| **JobDetailPage** | Dialog "Annuler" / "Confirmer" | ❌ manquait `fluid` |
| **ProfilePage** | "Se déconnecter" | ❌ manquait `fluid` |

### Adaptation des `dialog-actions`
Les boutons de dialogue sont passés en `flex-direction: column` pour qu'ils s'empilent verticalement au lieu d'être côte à côte (meilleurs cibles tactiles sur mobile) :
```css
.dialog-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
```

### Adaptation des `page-header`
Les en-têtes de page (titre + bouton d'action) sont passés en `flex-direction: column` pour que le bouton full width se place sous le titre :
```css
.page-header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
```

---

## 5. `box-sizing: border-box` global

### Principe
Déjà présent dans `App.vue` :
```css
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}
```

Avec `border-box`, `width: 100%` sur un champ inclut le padding et la bordure → pas de débordement horizontal.
Le prop `fluid` de PrimeVue applique `width: 100%` → combiné avec `border-box`, les champs remplissent leur conteneur sans dépasser.

---

## Résumé des fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `frontend/index.html` | Ajout de `viewport-fit=cover` |
| `frontend/src/App.vue` | `100vh` → `100dvh`, règle `font-size: 16px` iOS, safe-area padding |
| `frontend/src/pages/LoginPage.vue` | `100vh` → `100dvh` |
| `frontend/src/pages/ReviewPage.vue` | `100vh` → `100dvh` |
| `frontend/src/pages/DashboardPage.vue` | 2 boutons `fluid` |
| `frontend/src/pages/JobsPage.vue` | 3 boutons `fluid`, `.page-header` column, `.dialog-actions` column |
| `frontend/src/pages/ClientsPage.vue` | 3 boutons `fluid`, `.page-header` column, `.dialog-actions` column |
| `frontend/src/pages/ClientDetailPage.vue` | 2 boutons `fluid`, `.dialog-actions` column |
| `frontend/src/pages/JobDetailPage.vue` | 2 boutons `fluid`, `.dialog-actions` column |
| `frontend/src/pages/ProfilePage.vue` | 1 bouton `fluid` |

---

## Commandes de vérification

### Vérifier qu'aucune erreur TS n'a été introduite
```bash
cd frontend && npx vue-tsc --noEmit
```

### Tester responsive dans le navigateur (Chrome DevTools)
1. Appuyer sur `F12` → basculer en mode mobile
2. Sélectionner un viewport 375px (iPhone SE) et 430px (Galaxy S22)
3. Vérifier :
   - Pas de scroll horizontal
   - BottomNav bien collée en bas
   - Safe area simulée (Chrome > Rendering > Simulate viewport-fit=cover)
   - Boutons full width
   - Champs de formulaire avec `font-size: 16px`
