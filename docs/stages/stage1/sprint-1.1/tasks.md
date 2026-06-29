# Sprint 1.1 : Base (Semaine 1, Lun-Mer)

> **Durée :** 3 jours | **Points :** 23 | **Tâches :** 8 (INT-00 à INT-07)

---

## INT-00 — Initialiser Alembic (1 pt)

**User Story**  
En tant que **développeur backend**,  
Je veux **initialiser Alembic et configurer `env.py`**  
Afin de **gérer les migrations de base de données dès le premier jour**.

**Acceptance Criteria**
- [x] `alembic init backend/alembic` exécuté avec succès
- [x] `env.py` configuré : `target_metadata = Base.metadata` importé depuis `app.models.base`
- [x] `env.py` lit `DATABASE_URL` depuis `app.config`
- [x] Première migration vide créée et appliquée : `alembic upgrade head`
- [x] SQLite utilisé en dev, PostgreSQL en prod via variable d'environnement

**Technical Notes**
- Configurer `alembic.ini` pour pointer vers `backend/alembic/`
- `env.py` doit importer tous les modèles via `from app.models import Base` (les sous-modules seront ajoutés plus tard)
- Utiliser `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)` dans `env.py`
- Créer le fichier `backend/app/models/__init__.py` qui exporte `Base`
- Créer `backend/app/models/base.py` avec `declarative_base()`

---

## INT-01 — Modèle User + 1ère migration (3 pts)

**User Story**  
En tant que **développeur backend**,  
Je veux **créer le modèle `User` avec tous ses champs et sa première migration**  
Afin de **pouvoir authentifier les techniciens et admins**.

**Acceptance Criteria**
- [x] Modèle `User` créé avec : id, username (UNIQUE), email (UNIQUE), hashed_password, full_name, role, is_active, created_at, updated_at
- [x] Rôle : `technician` (défaut) ou `admin`
- [x] Migration automatique générée : `alembic revision --autogenerate -m "add user table"`
- [x] Migration appliquée : `alembic upgrade head`
- [x] Le modèle est importé dans `models/__init__.py`
- [x] Table nommée `"user"` (guillemets pour éviter conflit SQL)

**Technical Notes**
- Utiliser `__tablename__ = "user"` (attention au mot réservé SQL)
- Enum `Role` séparé (technician, admin)
- `hashed_password` stocke le hash bcrypt, pas le mot de passe en clair
- `is_active` par défaut `True`

---

## INT-02 — POST /auth/login + POST /auth/refresh JWT (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **me connecter avec mon identifiant et mot de passe**  
Afin **d'accéder à l'application et obtenir un token JWT**.

**Acceptance Criteria**
- [x] `POST /api/v1/auth/login` accepte `{ username, password }` → retourne `{ access_token, refresh_token, token_type, expires_in }`
- [x] `POST /api/v1/auth/refresh` accepte `{ refresh_token }` → retourne un nouveau `access_token`
- [x] Access token expire après 30 minutes
- [x] Refresh token expire après 7 jours
- [x] Hash bcrypt : passlib pour vérifier le mot de passe
- [x] Erreur 401 si identifiants invalides
- [x] Erreur 401 si refresh token invalide ou expiré

**Technical Notes**
- Utiliser `python-jose` pour JWT
- Créer `app/core/security.py` : `create_access_token()`, `create_refresh_token()`, `verify_password()`, `get_password_hash()`
- `app/core/deps.py` : dépendance `get_current_user` qui vérifie le Bearer token
- Payload JWT : `{ sub: user_id, exp, type: "access"|"refresh" }`

---

## INT-03 — GET /auth/me + PUT /auth/me (2 pts)

**User Story**  
En tant que **technicien connecté**,  
Je veux **consulter et modifier mon profil**  
Afin de **mettre à jour mes informations personnelles**.

**Acceptance Criteria**
- [x] `GET /api/v1/auth/me` retourne l'utilisateur courant (id, username, email, full_name, role, is_active)
- [x] `PUT /api/v1/auth/me` permet de modifier email, full_name
- [x] Le username ne peut pas être modifié
- [x] Authentification requise (Bearer token)
- [x] Retourne 401 si non authentifié

**Technical Notes**
- `GET /me` utilise la dépendance `get_current_user`
- `PUT /me` accepte un body partiel (PATCH-like)
- Le mot de passe se change via un endpoint dédié (P2)

---

## INT-04 — Modèle Client + migration (2 pts)

**User Story**  
En tant que **développeur backend**,  
Je veux **créer le modèle `Client` et sa migration**  
Afin de **pouvoir gérer les fiches clients**.

**Acceptance Criteria**
- [x] Modèle `Client` créé : id, full_name, phone, email, address, postal_code, city, notes, created_at, updated_at
- [x] Migration automatique générée et appliquée
- [x] Index sur `phone`, `full_name`, `city`
- [x] Tous les champs obligatoires sauf email, postal_code, city, notes

**Technical Notes**
- `__tablename__ = "client"`
- `phone` doit être NOT NULL
- Les index améliorent les performances de recherche

---

## INT-05 — GET/POST /clients + GET/PUT/DELETE /clients/{id} (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **créer, consulter, modifier et supprimer des clients**  
Afin de **gérer mon carnet d'adresses clients**.

**Acceptance Criteria**
- [x] `GET /api/v1/clients` : liste paginée (`?page=1&page_size=25`) avec recherche textuelle (`?search=dupont`)
- [x] `POST /api/v1/clients` : création d'un client → retourne 201 + le client créé
- [x] `GET /api/v1/clients/{id}` : détail d'un client (inclut `jobs_count` et `last_job_date` — dynamiques via ORM)
- [x] `PUT /api/v1/clients/{id}` : modification partielle ou complète
- [x] `DELETE /api/v1/clients/{id}` : suppression → retourne 204
- [x] Validation Pydantic : full_name requis, phone requis
- [x] Authentification requise sur tous les endpoints
- [x] Recherche par nom ET par téléphone simultanément
- [x] 404 si client inexistant

**Technical Notes**
- Endpoints sous `/api/v1/clients`
- Repository pattern : `ClientRepository` avec méthodes CRUD
- Service pattern : `ClientService` pour la logique métier (exist check, etc.)
- Schémas Pydantic : `ClientCreate`, `ClientUpdate`, `ClientResponse`, `ClientListResponse`

---

## INT-06 — GET /clients/{id}/jobs (historique) (2 pts)

**User Story**  
En tant que **technicien**,  
Je veux **consulter l'historique des interventions d'un client**  
Afin de **connaître les travaux déjà effectués chez lui**.

**Acceptance Criteria**
- [x] `GET /api/v1/clients/{id}/jobs` retourne les jobs du client
- [x] Liste ordonnée par date décroissante (plus récent en premier)
- [x] Champs retournés : id, title, status, completed_at, technician full_name
- [x] Pagination supportée
- [x] 404 si client inexistant

**Technical Notes**
- Réutilise le `JobRepository` pour la requête
- Inclure le nom du technicien associé (join)
- Limiter à 50 résultats par défaut

---

## INT-07 — Frontend : LoginPage + App.vue + BottomNav (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **ouvrir l'application, me connecter et naviguer**  
Afin **d'accéder aux fonctionnalités de l'application**.

**Acceptance Criteria**
- [x] `App.vue` : structure de base, routage, état de connexion global
- [x] `LoginPage` : formulaire username + password, bouton "Se connecter"
- [x] Appel API `POST /auth/login` avec gestion d'erreur
- [x] Stockage du token JWT dans `localStorage` / Pinia `authStore`
- [x] Redirection vers Dashboard après connexion réussie
- [x] BottomNav fixe : 4 onglets — 🏠 Accueil, 📋 Jobs, 📁 Clients, 👤 Profil
- [x] Déconnexion : suppression du token, redirection vers login
- [x] Guard de route : redirection vers `/login` si non authentifié
- [x] Template PrimeVue : utilisation de `InputText`, `Password`, `Button`, `Toast`

**Technical Notes**
- `authStore` Pinia : `token`, `user`, `login()`, `logout()`, `fetchUser()`
- Route guard avec `router.beforeEach` ou `navigation guards` dans `router/index.ts`
- BottomNav : composant custom `BottomNav.vue` (pas de composant PrimeVue natif)
- Pages vides pour les onglets non développés : "Page en construction"
- Styling mobile-first : bottom nav fixe, hauteur 56px, icônes PrimeVue

---

## Tests Cases Sprint 1.1

Les tests cases détaillés sont dans `test-cases.json`.
