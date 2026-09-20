# Sprint 6.3 : Catalogue produits & exposition (2.5 jours)

> **Durée :** 2.5 jours (7h/j) | **Points :** 11 | **Tâches :** INT-81 à INT-84
>
> **Référence :** `docs/DAT/08-module-catalogue.md` §4.1, §4.2
>
> **Approche :** **backend-first**. Le modèle métier et les API d'abord, le frontend minimal ensuite.

---

## Pourquoi ce sprint

Le projet Tervo doit avoir une identité fonctionnelle. Le catalogue produits + l'exposition en salle donnent le contexte métier : un particulier vient voir, comparer, essayer avant de se décider.

**Périmètre volontairement limité :**
- ✅ `produit` — fiche produit (référence, catégorie, marque, prix)
- ✅ `exposition_showroom` — quel produit est en salle, essayable, vendable
- ❌ Pas de `stock` / `mouvement_stock` (bonus si le temps le permet)
- ❌ Pas de `visite_showroom` (dépend du module Devis, hors scope)
- ❌ Pas de `fournisseur`, `contrat_sav`

**Ce qu'on peut dire en entretien :**
> « J'ai modélisé un catalogue produits avec une notion d'exposition en salle — entités, relations, API REST et une UI minimale. Le showroom relie un produit physique à un emplacement, avec des attributs métier comme "essayable" ou "vendable sur place". »

---

## INT-81 — Modèle `produit` + Catalogue API (3 pts)

**User Story**
En tant que **vendeur**,
Je veux **gérer un catalogue de produits**,
Afin de **présenter l'offre disponible aux clients**.

**Acceptance Criteria**
- [ ] Modèle `produit` : `reference`, `nom`, `categorie`, `marque`, `prix_achat_ht`, `prix_vente_ht`, `photo`, `statut`
- [ ] `categorie` : énum (`clim`, `chaudiere`, `pac`, `chauffage`, `autre`)
- [ ] `statut` : énum (`en_exposition`, `en_stock`, `discontinue`)
- [ ] `reference` unique
- [ ] `prix_vente_ht` obligatoire
- [ ] Migration Alembic
- [ ] API : `GET/POST /api/v1/produits`, `GET/PUT/DELETE /api/v1/produits/{id}`
- [ ] Filtres : `?categorie=clim&statut=en_exposition&search=...`
- [ ] Pagination (`page`, `page_size`)
- [ ] Upload photo produit (réutilise le service existant)

**Technical Notes**
- Fichiers : `models/produit.py`, `schemas/produit.py`, `repositories/produit.py`, `services/produit.py`, `api/v1/produits.py`
- Réutiliser le pattern Router → Service → Repository existant
- Photo : réutiliser `services/photo.py` (thumbnails Pillow)
- **Décision de modélisation :** `statut` est un énum + un booléen d'exposition (INT-82) — ne pas mélanger les deux notions

---

## INT-82 — Modèle `exposition_showroom` + API (3 pts)

**User Story**
En tant que **vendeur**,
Je veux **savoir quels produits sont exposés en salle et lesquels sont essayables**,
Afin de **guider le client pendant sa visite**.

**Acceptance Criteria**
- [ ] Modèle `exposition_showroom` : `produit_id`, `emplacement`, `disponible_essai`, `vendable_showroom`, `date_installation_demo`
- [ ] `produit_id` : FK → `produit` (CASCADE)
- [ ] Relation : un produit → 0 ou 1 exposition
- [ ] `emplacement` : zone du showroom (texte)
- [ ] `disponible_essai` : le client peut tester le produit
- [ ] `vendable_showroom` : vendable immédiatement **ou** démo uniquement
- [ ] Migration Alembic
- [ ] API : `GET/POST /api/v1/expositions`, `PUT/DELETE /api/v1/expositions/{id}`
- [ ] `GET /api/v1/expositions` retourne le produit joint (nom, catégorie, prix)

**Technical Notes**
- Fichiers : `models/exposition_showroom.py` + schemas/repositories/services/api
- **Point de modélisation à expliquer :** `disponible_essai` (essai physique) ≠ `vendable_showroom` (peut être vendu) — deux notions distinctes, souvent confondues
- **Rappel entretien :** « J'ai séparé "essayable" de "vendable" — un modèle d'exposition peut être essayable mais pas vendable (démo uniquement). »

---

## INT-83 — Frontend minimal : catalogue + exposition (3 pts)

**User Story**
En tant que **vendeur**,
Je veux **consulter le catalogue et la vue salle**,
Afin de **présenter les produits à un client sur tablette**.

**Acceptance Criteria**
- [ ] Route `/produits` → `ProduitsPage` (liste + filtres catégorie/statut + recherche)
- [ ] Route `/showroom` → `ShowroomPage` (vue par emplacement, badges essai/vendable)
- [ ] Route `/produits/:id` → `ProduitDetailPage` (fiche + photo + tarif)
- [ ] Dialogue création/édition produit avec validation Zod
- [ ] États Loading / Empty / Error sur les 3 pages (suivre INT-39)
- [ ] Ajout des entrées dans la BottomNav

**Technical Notes**
- Fichiers : `frontend/src/pages/ProduitsPage.vue`, `ShowroomPage.vue`, `ProduitDetailPage.vue`
- Réutiliser les composants PrimeVue déjà en place (DataTable, Dialog, Chip, Skeleton)
- **Ne pas sur-investir** : UI fonctionnelle, pas de design poussé
- **Rappel entretien :** « Le frontend n'est pas mon domaine principal — je l'ai fait fonctionnel, avec Vue/TS. »

---

## INT-84 — Tests + note pédagogique (2 pts)

**User Story**
En tant que **dev backend**,
Je veux **tester le catalogue et documenter les choix de modélisation**,
Afin de **pouvoir justifier le modèle en entretien**.

**Acceptance Criteria**
- [ ] Tests API : CRUD produits (create, read, update, delete, filtres)
- [ ] Tests API : CRUD expositions + relation produit
- [ ] Test contrainte : `reference` unique → 409 en cas de doublon
- [ ] Test cascade : supprimer un produit supprime son exposition
- [ ] Note pédagogique : `notes/backend/catalogue/modelisation-produit.md`
  - Pourquoi `statut` ≠ `exposition`
  - Pourquoi `disponible_essai` ≠ `vendable_showroom`
  - Relations et contraintes

**Technical Notes**
- Fichiers : `backend/tests/test_produits_api.py`, `test_expositions_api.py`
- Objectif : pouvoir **défendre le modèle**, pas seulement le faire tourner

---

## Tests Cases Sprint 6.3

Les tests cases détaillés sont dans `test-cases.json`.
