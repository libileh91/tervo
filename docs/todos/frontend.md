  # Todos Frontend — Tervo

> Fichier central des fonctionnalités frontend reportées.  
> Scanné à chaque fin de tâche pour voir si des dépendances backend sont débloquées.

---

## TD-F001 — DashboardPage (jobs du jour + boutons)

| Champ                 | Valeur                                                 |
| --------------------- | ------------------------------------------------------ |
| **Créé dans**         | INT-13 (spec Sprint 1.2)                               |
| **Dépend du backend** | `GET /api/v1/dashboard/summary` (INT-12 ✅)            |
|                       | `PUT /api/v1/jobs/{id}/start` (INT-10 ✅)              |
| **Fichiers**          | `frontend/src/pages/DashboardPage.vue`                 |
| **Action**            | Remplacer le placeholder par :                         |
|                       | • Appel API `GET /dashboard/summary`                   |
|                       | • Compteurs : jobs_total, en_cours, terminés           |
|                       | • Carte "Prochain job" + bouton ▶ Démarrer             |
|                       | • Carte "Job en cours" + chronomètre + bouton Terminer |
|                       | • États loading/empty/error                            |
|                       | • Rafraîchissement auto 10s (Vue Query)                |
| **Statut**            | ✅ Fait (INT-12 ✅ backend + INT-13 ✅ frontend)                  |

---

## TD-F002 — JobListPage (filtre statut/date)

| Champ                 | Valeur                                            |
| --------------------- | ------------------------------------------------- |
| **Créé dans**         | INT-14 (spec Sprint 1.2)                          |
| **Dépend du backend** | `GET /api/v1/jobs` (INT-09 ✅)                    |
| **Fichiers**          | `frontend/src/pages/JobsPage.vue`                 |
| **Action**            | Remplacer le placeholder par :                    |
|                       | • Liste paginée avec DataTable PrimeVue           |
|                       | • Filtres : statut (dropdown), date (date picker) |
|                       | • Chips colorées par statut                       |
|                       | • Navigation vers JobDetailPage au clic           |
|                       | • Bouton "+ Nouveau job"                          |
| **Statut**            | ✅ Fait (backend INT-09 + frontend INT-14)                        |

---

## TD-F003 — JobDetailPage (fiche avec onglets)

| Champ                 | Valeur                                                            |
| --------------------- | ----------------------------------------------------------------- |
| **Créé dans**         | INT-15 (spec Sprint 1.2)                                          |
| **Dépend du backend** | `GET /api/v1/jobs/{id}` (INT-09 ✅)                               |
|                       | `PUT /api/v1/jobs/{id}/start` (INT-10 ✅)                         |
|                       | `PUT /api/v1/jobs/{id}/complete` (INT-11)                         |
|                       | • Onglet Checklist → `PUT /checklist` (INT-18 Sprint 1.3)         |
|                       | • Onglet Photos → upload (Phase 2)                                |
|                       | • Onglet Matériaux → `GET/POST /materials` (Phase 2)              |
|                       | • Onglet Rapport → PDF (Phase 2)                                  |
| **Fichiers**          | `frontend/src/pages/JobDetailPage.vue`                            |
| **Action**            | Remplacer le placeholder par :                                    |
|                       | • En-tête : titre, statut chip, priorité chip, client             |
|                       | • TabView PrimeVue (Infos, Checklist, Photos, Matériaux, Rapport) |
|                       | • Onglet Infos actif, les autres désactivés                       |
|                       | • Boutons "▶ Démarrer" / "Terminer"                               |
|                       | • Bouton "Supprimer" avec confirmation Dialog                     |
| **Statut**            | ✅ Fait — Photos (INT-27), Matériaux (INT-28), Checklist (INT-20), Rapport encore `:disabled` |

---

## TD-F004 — ClientListPage + ClientDetailPage

| Champ                 | Valeur                                                            |
| --------------------- | ----------------------------------------------------------------- |
| **Créé dans**         | INT-16 (spec Sprint 1.2)                                          |
| **Dépend du backend** | `GET /api/v1/clients` (INT-05 ✅)                                 |
|                       | `GET /api/v1/clients/{id}` (INT-05 ✅)                            |
|                       | `GET /api/v1/clients/{id}/jobs` (INT-06 ✅)                       |
| **Fichiers**          | `frontend/src/pages/ClientsPage.vue`                              |
| **Action**            | Remplacer le placeholder par :                                    |
|                       | • Liste paginée + champ recherche (debounce 300ms)                |
|                       | • Détail client avec toutes les infos                             |
|                       | • Historique des jobs (tableau)                                   |
|                       | • Boutons Modifier / Supprimer / + Nouveau client / + Nouveau job |
| **Statut**            | ✅ Fait (backend INT-05/06 + frontend INT-16)                     |

---

## TD-F005 — Page Profil : modification email/full_name

| Champ                 | Valeur                                                       |
| --------------------- | ------------------------------------------------------------ |
| **Créé dans**         | INT-03 (spec Sprint 1.1)                                     |
| **Dépend du backend** | `PUT /api/v1/auth/me` (INT-03 ✅)                            |
| **Fichiers**          | `frontend/src/pages/ProfilePage.vue`                         |
| **Action**            | Ajouter un formulaire d'édition du profil (email, full_name) |
| **Statut**    | ⏳ Backend prêt — frontend formulaire d'édition non développé       |

---

## TD-F006 — Bouton "Terminer" avec validation checklist

| Champ                 | Valeur                                                       |
| --------------------- | ------------------------------------------------------------ |
| **Créé dans**         | INT-21 (spec Sprint 1.3)                                     |
| **Dépend du backend** | `PUT /api/v1/jobs/{id}/complete` (INT-11 ✅)                 |
|                       | Checklist validation (INT-17 ✅ — `ChecklistService` prêt)   |
| **Fichiers**          | `frontend/src/pages/DashboardPage.vue` (carte en cours)      |
|                       | `frontend/src/pages/JobDetailPage.vue` (`en_cours` actions)  |
| **Action**            | Ajouter un bouton "Terminer" sur :                          |
|                       | • `DashboardPage` — dans la carte "Job en cours"             |
|                       | • `JobDetailPage` — à côté de "📋 Checklist" quand `en_cours`|
|                       | Le bouton doit être :                                        |
|                       | • Désactivé si checklist incomplète avec tooltip explicatif   |
|                       | • Actif si checklist complète → appelle `api.put('/jobs/{id}/complete')` |
|                       | • Invalider `['dashboard']`, `['jobs']`, `['job', jobId]`    |
| **Statut**            | ✅ Fait — Bouton "Terminer" sur JobDetailPage + InspectionPage |


---

## TD-F007 — Reprendre les besoins frontend catalogue/showroom dans le modèle V2

| Champ | Valeur |
|---|---|
| **Créé dans** | Restructuration Stage 7 ; reprise de l’ancien INT-83 avant suppression du sprint 6.3 |
| **Dépend de** | INT-96 (catalogue, sprint7.1), INT-109 (visites showroom, sprint7.5), cadrage frontend du DAT V2 |
| **Fichiers** | `frontend/src/pages/`, `frontend/src/router/`, `docs/stages/stage7/sprint7.5/tasks.md` |
| **Action attendue** | Vérifier l’existant et planifier les écrans V2 : catalogue, détail et édition, visites showroom, navigation, recherche/filtres et états loading/empty/error avec réessai. Adapter les cas E2E de l’ancien INT-83 au modèle V2 ; ne pas reprendre implicitement exposition physique, prix catalogue ou badges essai/vendable. |
| **Statut** | ⏳ À cadrer avant livraison des interfaces V2 ; aucune réalisation frontend déduite de la clôture backend d’INT-96 |
