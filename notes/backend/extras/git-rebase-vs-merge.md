# Git — intégrer une feature dans `main` : rebase ou merge ?

> **Contexte :** intégration du travail DAT (`chore/rewrite-dat`) sur `main`.
> **Question de départ :** « rebase est-il la meilleure option pour feature → main ? »
> **Réponse courte :** presque — **rebaser la feature _sur_ `main`** ≠ **intégrer _dans_ `main`**.

---

## 1. Deux opérations différentes

| Opération                         | Commande                                  | Sens                                                 | Historique          |
| --------------------------------- | ----------------------------------------- | ---------------------------------------------------- | ------------------- |
| Rebaser la feature **sur** `main` | `git checkout feature && git rebase main` | rejoue les commits de la feature par-dessus `main`   | linéaire            |
| Merger la feature **dans** `main` | `git checkout main && git merge feature`  | intègre la feature (commit de merge ou fast-forward) | ramifié ou linéaire |

> Le **rebase** ne fait pas _entrer_ la feature dans `main` : il **remet la feature à jour**
> par rapport à `main`. L'intégration se fait par **merge**.

---

## 2. La règle d'or (multi-personnes)

- **Rebase** → branches **privées / feature** (une seule personne les pousse).
- **Merge** → intégration **dans** les branches **partagées** (`main`, `develop`).
- **Ne jamais réécrire** l'historique d'une branche partagée → sinon tout le monde doit
  re-cloner / force-pull.

- **Rebaser la feature _sur_ main** → `git checkout feature && git rebase main` (mettre la feature **à jour**)
- **Merger la feature _dans_ main** → `git checkout main && git merge feature` (intégrer)

Le rebase **ne fait pas entrer** la feature dans `main` : il **remet la feature à jour** par rapport à `main`. L'intégration, c'est le **merge**.


| Branche                        | Opération                        | Pourquoi                                    |
| ------------------------------ | -------------------------------- | ------------------------------------------- |
| **feature privée** (1 dev)     | `rebase` sur main ✅             | historique linéaire, réécriture sans risque |
| **feature partagée** (2+ devs) | `merge main` **dans** la feature | sinon chacun aurait un SHA différent        |
| **`main` elle-même**           | **merge** (ou ff-only)           | ne jamais réécrire une branche partagée     |


> Corollaire : une feature partagée par 2 devs ne se rebase **pas** (chacun aurait un SHA
> différent). Dans ce cas, on `git merge main` **dans** la feature pour la mettre à jour.

---

## 3. Les 3 façons de mettre à jour une feature

```bash
# A. Rebase (feature privée) — historique linéaire
git checkout feature && git rebase main      # puis git push --force-with-lease

# B. Merge de main dans la feature (feature partagée) — pas de réécriture
git checkout feature && git merge main

# C. Rien (si main n'a pas bougé) — c'est notre cas
```

---

## 4. Les 3 façons d'intégrer dans main

```bash
# A. Fast-forward (si la feature est linéaire et à jour) — aucun commit de merge
git checkout main && git merge --ff-only feature

# B. Merge commit (garde la trace « ceci était une feature »)
git checkout main && git merge --no-ff feature

# C. Squash-merge (1 seul commit sur main, via GitHub ou git merge --squash)
```

> `--ff-only` **refuse** de fusionner si `main` a divergé : garde-fou anti-merge silencieux.

---

## 5. Notre cas

```text
main (9094300) ──► 9f07b6e ──► 6a7be77 ──► 94447ab ──► a5b0519 ──► a9ccadb (chore/rewrite-dat)
```

`chore/rewrite-dat` est un **descendant linéaire** de `main` (`main` n'a pas bougé depuis la
création de la branche).

- `git rebase main` → **no-op** (`Current branch chore/rewrite-dat is up to date`) : rien à rejouer.
- Intégration propre → **fast-forward** :

```bash
git checkout main
git merge --ff-only chore/rewrite-dat
git push origin main
```

ou directement :

```bash
git push origin chore/rewrite-dat:main
```

> Le tag `dat-before-rewrite-2026-09-21` sur `9094300` marque l'état de `main` **avant** la
> refonte — utile pour comparer ou revenir en arrière.

---

## 6. `git commit --amend --no-edit`

Utilisé pour **ajouter des fichiers au dernier commit** sans changer son message (ici : le
skill `SKILL.md` dans le commit de revue du sprint).

```bash
git add .agents/skills/fuliyeh/SKILL.md
git commit --amend --no-edit
```

- **Réécrit** le commit → nouveau SHA (`89d3746` → `a9ccadb`).
- Si le commit était poussé → **force-push obligatoire** : `git push --force-with-lease`
  (plus sûr que `--force` : échoue si le distant a bougé entre-temps).
- ⚠️ Même règle que le rebase : à réserver aux commits **non partagés**.

---

## 7. Résumé

| Besoin                                 | Commande                                        |
| -------------------------------------- | ----------------------------------------------- |
| Mettre à jour une feature **privée**   | `git rebase main`                               |
| Mettre à jour une feature **partagée** | `git merge main`                                |
| Intégrer une feature **dans main**     | `git merge --ff-only` (ou `--no-ff`, ou squash) |
| Ajouter des fichiers au dernier commit | `git commit --amend --no-edit`                  |
| Pousser après réécriture d'historique  | `git push --force-with-lease`                   |
| **Jamais**                             | réécrire `main` / rebaser une branche partagée  |
