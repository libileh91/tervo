# Sprint 5.1 : Admin & Notifications (Semaine 6)

> **Durée :** 5 jours | **Points :** 18 | **Tâches :** 5 (INT-56 à INT-60)

---

## INT-56 — `GET/POST/PUT /admin/users` (5 pts)

**User Story**  
En tant que **manager**,  
Je veux **gérer les comptes des techniciens**  
Afin de **pouvoir ajouter, modifier et consulter les utilisateurs**.

**Acceptance Criteria**
- [ ] `GET /api/v1/admin/users` — liste paginée des utilisateurs (rôle admin requis)
- [ ] `POST /api/v1/admin/users` — création d'un utilisateur (username, email, password, full_name, role)
- [ ] `PUT /api/v1/admin/users/{id}` — modification d'un utilisateur
- [ ] Accès réservé aux admins (vérification `current_user.role == 'admin'`)
- [ ] Le password est hashé avant stockage (bcrypt)
- [ ] 409 si username ou email déjà existant

**Technical Notes**
- Router : `backend/app/api/v1/admin.py` (nouveau)
- Dépendance `require_admin` : vérifie `current_user.role == 'admin'`
- Schémas Pydantic : `AdminUserCreate`, `AdminUserUpdate`, `AdminUserResponse`
- Réutiliser `UserRepository` existant

---

## INT-57 — `DELETE /admin/users/{id}` (soft-delete) (2 pts)

**User Story**  
En tant que **manager**,  
Je veux **désactiver un compte technicien**  
Afin de **ne pas perdre l'historique de ses interventions**.

**Acceptance Criteria**
- [ ] `DELETE /api/v1/admin/users/{id}` → `is_active = false` (soft-delete)
- [ ] Le user n'est pas supprimé de la base (ON DELETE SET NULL sur les jobs préservé)
- [ ] Retourne 204
- [ ] Impossible de soft-delete son propre compte
- [ ] 404 si user inexistant
- [ ] Accès admin requis

**Technical Notes**
- Soft-delete : `user.is_active = False` au lieu de `db.delete(user)`
- Filtre `is_active = True` dans les endpoints de login (déjà fait dans INT-02)

---

## INT-58 — `POST /admin/register` (création technicien) (3 pts)

**User Story**  
En tant que **manager**,  
Je veux **créer un nouveau compte technicien rapidement**  
Afin de **lui donner accès à l'application**.

**Acceptance Criteria**
- [ ] `POST /api/v1/admin/register` — endpoint dédié à la création de compte par admin
- [ ] Body : `{ "username", "email", "password", "full_name" }`
- [ ] Validation : username unique, email unique, password ≥ 6 car.
- [ ] Rôle par défaut : `technician`
- [ ] Retourne 201 avec les infos du user créé (sans le password)
- [ ] Accès admin requis

**Technical Notes**
- Ce endpoint remplace/utilise TD-B002 (qui était non prioritaire)
- Réutiliser `UserService` ou créer directement dans le router admin

---

## INT-59 — Frontend : `UserManagementPage` (5 pts)

**User Story**  
En tant que **manager**,  
Je veux **une page pour gérer les techniciens**  
Afin de **les ajouter, modifier ou désactiver depuis l'interface**.

**Acceptance Criteria**
- [ ] Route : `/admin/users` (accessible seulement aux admins)
- [ ] Liste des utilisateurs (username, email, rôle, statut actif/inactif)
- [ ] Bouton "➕ Nouveau technicien" → formulaire modal
- [ ] Bouton "✏ Modifier" sur chaque ligne → formulaire modal
- [ ] Bouton "🚫 Désactiver" → confirmation dialog (soft-delete)
- [ ] Chip de statut : actif 🟢 / inactif 🔴
- [ ] Protection : si l'utilisateur courant n'est pas admin → redirection
- [ ] États loading/empty/error

**Technical Notes**
- Fichier : `frontend/src/pages/AdminUsersPage.vue` (nouveau)
- Route : `{ path: '/admin/users', name: 'AdminUsers', meta: { requiresAuth: true, requiresAdmin: true } }`
- Guard admin : `router.beforeEach` vérifie `auth.user.role === 'admin'`
- API : `adminApi.list()`, `adminApi.create()`, `adminApi.update()`, `adminApi.deactivate()`

---

## INT-60 — Logs d'audit (qui a fait quoi, quand) (3 pts)

**User Story**  
En tant que **manager**,  
Je veux **voir qui a fait quoi et quand**  
Afin de **pouvoir tracer les actions importantes**.

**Acceptance Criteria**
- [ ] Logger les actions suivantes :
  - Création de job
  - Démarrage / complétion de job
  - Upload / suppression de photo
  - Création / modification / suppression de client
  - Création / désactivation d'utilisateur
- [ ] Stockage : table `audit_log` (id, user_id, action, entity_type, entity_id, details, created_at)
- [ ] Endpoint : `GET /api/v1/admin/audit-logs?page=&page_size=`
- [ ] Accès admin uniquement
- [ ] Frontend : page simple avec tableau chronologique

**Technical Notes**
- Modèle : `backend/app/models/audit_log.py` (nouveau)
- Service : `AuditService.log(user_id, action, entity_type, entity_id, details)`
- Appeler `AuditService.log()` dans chaque service métier concerné
- Frontend : page simple avec DataTable PrimeVue triée par date desc

---

## Tests Cases Sprint 5.1

Les tests cases détaillés sont dans `test-cases.json`.
