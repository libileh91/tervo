# INT-40 — Animations de transition entre pages (Vue.js)

> **Sprint 4.1** | Points : 2 | Statut : ✅

---

## Ce qui a été fait

Ajout de transitions fluides (slide horizontale + fade) entre les pages de l'application Vue.js.

### Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `frontend/src/App.vue` | Ajout `<Transition>` wrapper, CSS des animations |
| `frontend/src/router/index.ts` | Ajout `meta: { noTransition: true }` pour Login |

### Code ajouté — App.vue

```vue
<!-- Wrapper Transition autour du router-view -->
<router-view v-slot="{ Component, route }">
    <Transition :name="route.meta.noTransition ? '' : 'slide-fade'" mode="out-in">
        <component :is="Component" :key="route.path" />
    </Transition>
</router-view>
```

### Code ajouté — CSS des transitions

```css
.slide-fade-enter-active,
.slide-fade-leave-active {
    transition: all 0.25s ease;
}

.slide-fade-enter-from {
    transform: translateX(20px);
    opacity: 0;
}

.slide-fade-leave-to {
    transform: translateX(-20px);
    opacity: 0;
}
```

---

## Explication technique

### `<Transition>` en Vue.js 3

`<Transition>` est un composant intégré de Vue qui applique des animations lorsqu'un élément est inséré/supprimé du DOM.

```vue
<Transition name="slide-fade" mode="out-in">
    <!-- L'élément ici est animé à l'entrée/sortie -->
</Transition>
```

- **`name="slide-fade"`** : préfixe des classes CSS générées automatiquement (`.slide-fade-enter-active`, `.slide-fade-leave-active`, etc.)
- **`mode="out-in"`** : l'élément sort d'abord, puis le nouveau entre (pas de chevauchement)
- **`:key="route.path"`** : force Vue à détruire/recréer le composant quand la route change

### Classes CSS de transition

Vue génère automatiquement ces classes :

| Classe | Quand |
|--------|-------|
| `.slide-fade-enter-active` | Pendant toute la phase d'entrée |
| `.slide-fade-leave-active` | Pendant toute la phase de sortie |
| `.slide-fade-enter-from` | Début de l'entrée (opacité 0, décalé à droite) |
| `.slide-fade-leave-to` | Fin de la sortie (opacité 0, décalé à gauche) |

### Pourquoi `mode="out-in"` ?

Sans `mode`, les deux animations (entrée et sortie) se déclenchent en même temps → effet de chevauchement moche. Avec `out-in`, la page actuelle sort complètement avant que la nouvelle entre.

### Pourquoi `:key` sur le route path ?

Sans `key`, Vue réutilise le même composant si la route change mais le template reste le même (ex: `/jobs/1` → `/jobs/2`). Avec `:key="route.path"`, Vue voit un changement et déclenche la transition.

---

## Test visuel

```
Navigation : Dashboard → Jobs → JobDetail
  → La page glisse vers la gauche, la nouvelle arrive par la droite
  → Durée : 250ms

Navigation : JobDetail → Inspection
  → Même animation slide

Login → Dashboard
  → Pas d'animation (noTransition: true)
```

---

## Pour aller plus loin

Variantes possibles :

```css
/* Slide vertical (haut/bas) */
.slide-up-enter-from { transform: translateY(20px); opacity: 0; }
.slide-up-leave-to { transform: translateY(-20px); opacity: 0; }

/* Scale (zoom) */
.scale-enter-from { transform: scale(0.95); opacity: 0; }
.scale-leave-to { transform: scale(1.05); opacity: 0; }
```

Documentation Vue : https://vuejs.org/guide/built-ins/transition.html
