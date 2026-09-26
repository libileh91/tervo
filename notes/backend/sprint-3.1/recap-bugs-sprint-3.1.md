# Sprint 3.1 — Récapitulatif des bugs corrigés

> **Date :** 26/06/2026
> **Contexte :** Tests fonctionnels du sprint 3.1 (First Deploy) — bugs découverts pendant le test du frontend.

---

## Timeline des fixes

### 1. Login bloqué (LoginPage)
- `@submit.prevent="handleSubmit"` au lieu de `onSubmit` — VeeValidate factory appelée sans callback → rien ne se passait
- **Fichier :** `LoginPage.vue`

### 2. Statut "en_cours" persistant après completion
- Bouton "Terminer" désactivé (checklist vide → `allChecked = false`)
- Cache TanStack Query non mis à jour après API call
- **Solution :** Bouton "Terminer" direct sur JobDetailPage + mutation de `job.value`
- **Fichiers :** `JobDetailPage.vue`, `InspectionPage.vue`, `DashboardPage.vue`

### 3. Création job bloquée par Zod/VeeValidate
- `z.number()` rejetait `undefined` (valeur initiale du Select)
- **Solution :** Retrait de Zod/VeeValidate → refs simples + validation manuelle
- **Fichier :** `JobsPage.vue`

### 4. Caractères échappés (`\u00e9`)
- `edit_file` échappait les accents → placeholders invisibles
- **Solution :** `sed` pour remplacer `\u00e9` → `é`
- **Fichiers :** `JobsPage.vue`, `JobDetailPage.vue`, `useFormValidation.ts`

### 5. Timer Dashboard infini
- `ElapsedTimer` continuait à tourner après completion
- **Solution :** Retrait du composant timer
- **Fichier :** `DashboardPage.vue`

### 6. Checklist auto-création
- Jobs du seed sans checklist → page inspection vide
- **Solution :** `get_items()` auto-crée si liste vide
- **Fichier :** `checklist.py`

### 7. Erreur format date SQLite
- `row.completed_at.isoformat()` crash sur SQLite (str, pas datetime)
- **Solution :** `hasattr(row.completed_at, "isoformat")`
- **Fichier :** `repositories/job.py`

### 8. Historique jobs client — 500
- Même bug `.isoformat()` que #7

---

## Fichiers modifiés ce sprint

| Fichier | Type | Changement |
|---------|------|-----------|
| `JobDetailPage.vue` | frontend | Bouton Terminer + handleComplete |
| `InspectionPage.vue` | frontend | allChecked vide = true |
| `DashboardPage.vue` | frontend | Retrait ElapsedTimer |
| `JobsPage.vue` | frontend | Retrait Zod, titre, fix import |
| `LoginPage.vue` | frontend | onSubmit fix |
| `ClientsPage.vue` | frontend | Dialog création client |
| `useFormValidation.ts` | frontend | Fix accents, jobSchema |
| `api/client.ts` | frontend | createClient, createJob |
| `checklist.py` | backend | Auto-création items |
| `repositories/job.py` | backend | Fix isoformat |
| `services/job.py` | backend | Checklist validation (restaurée) |
| `pyproject.toml` | backend | asyncpg, pytest-asyncio, pytest-cov |
