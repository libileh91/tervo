# Safe Upgrade des packages npm (Juillet 2026)

## Contexte

Upgrade "safe" (mineur/patch uniquement) des packages frontend via Bun.

## Pourquoi safe seulement ?

Une analyse des dernières versions a montré que **presque tout** était en major bump :

- PrimeVue 4→5, Pinia 2→4, Vue Router 4→5, Zod 3→4, TypeScript 5→7, Vite 6→8
- Upgrader tout ça aurait cassé le frontend et demandé des heures de debug

Stratégie : on ne touche que ce qui est rétrocompatible (mineur/patch).

## Ce qui a été upgradé

| Package               | Avant   | Après    | Type   |
| --------------------- | ------- | -------- | ------ |
| `vue`                 | ^3.5.0  | ^3.5.40  | mineur |
| `@tanstack/vue-query` | ^5.60.0 | ^5.101.4 | mineur |

## Commandes utilisées

```bash
cd frontend

# Voir la dernière version d'un package
npm view <package> version

# Installer les mises à jour depuis package.json
bun install

# Vérifier que tout compile
bun run build
```

## Résultat

- `bun install` : 17 packages installés en 3.87s
- `bun run build` : 450 modules transformés, 0 erreur, 13.87s
- Rien de cassé ✅

## Pour plus tard (sprint dédié)

Si un jour on veut tout mettre à jour, faudra un vrai sprint frontend avec :

1. PrimeVue 4→5 (refonte des composants UI)
2. Vue Router 4→5 (nouvelle API de routing)
3. Pinia 2→4 (store API changes)
4. Zod 3→4 (rewrite validation)
5. TypeScript 5→7 (breaking changes TS)
6. Vite 6→8 (config build)
7. Tests de non-régression sur toutes les pages
