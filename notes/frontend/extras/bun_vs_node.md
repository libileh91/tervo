Bun 1.2.20 déjà installé. Voici le versus :

---

## Node vs Bun pour ResQ

### Comparatif

| Critère                    | Node.js (22.x)      | Bun (1.2.20)                                          |
| -------------------------- | ------------------- | ----------------------------------------------------- |
| **Installation**           | ✅ Déjà installé    | ✅ Déjà installé                                      |
| **Vitesse npm install**    | ⏳ 30-60s           | ⚡ 5-10s                                              |
| **Exécution scripts**      | V8 (classique)      | JavaScriptCore (20-40% plus rapide)                   |
| **Dev server (Vite)**      | ✅ Excellent        | ✅ Idem                                               |
| **PrimeVue 4**             | ✅ Compatible       | ✅ Compatible                                         |
| **TypeScript natif**       | ❌ `tsc` séparé     | ✅ Intégré (pas de `tsc` nécessaire)                  |
| **Compatibilité API**      | 100% standard       | ~95% (quelques edge cases Node)                       |
| **Écosystème**             | Mature, tout existe | Rapide, mais certains packages legacy peuvent planter |
| **CI/CD (GitHub Actions)** | ✅ Ubuntu natif     | ✅ Aussi supporté                                     |

### Impact concret sur ResQ

**Pour Bun :**

- `npm install` passe de 45s à ~8s
- Le hot-reload de Vite est plus réactif
- On peut retirer `vue-tsc` du build car Bun comprend le TypeScript nativement
- Un seul binaire au lieu de Node + npm + npx

**Pour Node :**

- 100% compatible avec PrimeVue 4
- Les GitHub Actions sont plus simples sans setup Bun
- Plus de ressources en ligne pour le debugging
- Pas de surprises avec des packages legacy

### Mon avis

**Pour ce projet (mobile-first, Vue 3, PrimeVue), Bun est un meilleur choix.**

Raisons :

1. Le projet est **greenfield** — pas de legacy à gérer
2. Les dépendances sont modernes (PrimeVue 4, TanStack Query 5) — tout est compatible Bun
3. Le gain de temps (install + dev) est réel sur un projet qu'on build fréquemment
4. Bun 1.2.x est stable pour du dev frontend Vue

**Risque mineur :** Les GitHub Actions, il faudra installer Bun (1 ligne) au lieu de Node.

### Si on switch, ce qui change

```diff
- npm install         → bun install
- npm run dev         → bun dev
- npm run build       → bun run build
- npx vite            → bun vite
```

Et dans `package.json` on peut retirer `vue-tsc` du build car Bun transpile le TS nativement.

---

**Tu donnes le feu-vert pour basculer le projet sur Bun ?** Si oui, je supprime le `package.json` créé, je recrée avec Bun, et j'installe les dépendances.
