# Sprint 7.3 — Chaîne commerciale

> **Tervo V2** · INT-102 à INT-103 · **Statut :** INT-102 et le raccordement commercial INT-103 livrés ; validations PostgreSQL à exécuter
> **Dépendances :** Sprint 7.1 ; TD-B014 et le raccordement commercial TD-B017 réalisés.
> **Ordre validé explicitement :** INT-103 autonome avant INT-102. Sale/SaleLine sont désormais présentes ; sale_line_id est une FK réelle nullable, sans vente artificielle.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.3/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

---

## INT-102 — `Sale` + `SaleLine` (5 pts)

**User Story**
En tant que **commercial**,
Je veux **enregistrer une vente avec ses lignes de produits**,
Afin de **distinguer l'événement commercial de l'installation future**.

**Acceptance Criteria**
- [x] `Sale` : `client_id`, `site_id`, `sale_date`, `status` (`DRAFT / CONFIRMED / CANCELLED`)
- [x] `SaleLine` : `sale_id`, `product_id`, `quantity`, `unit_price`
- [x] `Sale 1 → N SaleLine` ; une vente confirmée a ≥ 1 ligne
- [x] API : `POST /sales`, `POST /sales/{id}/confirm`, `POST /sales/{id}/cancel`
- [x] Test : `quantity = 3` → une ligne de quantité 3 → trois installations commerciales ultérieures

**Technical Notes**
- `quantity` > 1 est la clé du `SaleLine 1 → N Installation`.
- `Installation.sale_line_id` est nullable et FK réelle : la provenance client reste autonome ; les lignes inconnues et incohérences vente/site/produit sont refusées.
- Les ventes sont accessibles aux utilisateurs actifs authentifiés ; les rôles COMMERCIAL/MANAGER restent différés à TD-B013.

---

## INT-103 — `Installation` (5 pts)

**User Story**
En tant que **technicien**,
Je veux **suivre l'installation d'un équipement fourni par l'entreprise ou par le client (acheté ailleurs)**,
Afin de **créer l'équipement physique au moment où il est réellement installé**.

**Acceptance Criteria**
- [x] `Installation` autonome : `site_id` (FK requis), `scheduled_start/end`, `started_at`, `completed_at`, `installation_date`, `commissioning_date`, `status`, `technician_notes`
- [x] `sale_line_id` FK nullable vers SaleLine (TD-B017)
- [x] `status` ∈ `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`
- [x] `POST /installations`, `GET /installations` et `GET /installations/{id}`
- [x] `POST /installations/{id}/start`, `/complete`, `/cancel`
- [x] `complete` (même transaction) : `Installation → COMPLETED` + `Equipment` créé/rattaché
- [x] Test : installation complétée → 1 équipement créé, `installation_id` renseigné
- [x] Matériel fourni par le client : création sans champ `sale_line_id`, sans vente fictive ni stock requis
- [x] Accepter `sale_line_id` absent ou `null`, sans créer de vente fictive
- [x] Si `sale_line_id` est renseigné, vérifier vente confirmée, site, quantité et produit, puis conserver la provenance commerciale
- [x] Tests : parcours autonome jusqu'à clôture, site obligatoire, champs non supportés refusés, rollback après écriture de l'équipement (création et rattachement)
- [x] Test : ligne inconnue rejetée avec 404 ; parcours commercial avec provenance vérifié
- [x] TD-B014 : FK Equipment.installation_id nullable et unique, relations ORM, conservation des équipements historiques
- [x] Tests : matrice des transitions, clôture répétée (409), concurrence, même site, équipement actif non lié, conservation des dates et métadonnées
- [x] Tests : JWT actif requis, protection historique site/client, migrations sur bases jetables SQLite ciblée et PostgreSQL complète

**Technical Notes**
- `complete` est une **transaction métier** (installation + équipement atomiques), avec ou sans vente.
- `Equipment.installation_id` nullable couvre un autre cas : équipement historique sans installation enregistrée. Une installation sans vente terminée renseigne bien ce lien.
- Le catalogue n'est pas le stock ; aucun mouvement de stock automatique en V1. Ne pas créer de vente ou ligne artificielle pour représenter le matériel du client.
- Contrat de clôture : `installation_date` requise, `commissioning_date` optionnelle ; `equipment.mode` obligatoire (`create` avec produit facultatif vérifié, ou `attach` avec equipment_id). Aucun choix implicite par numéro de série.
- Rattachement : équipement ACTIVE, même site, sans installation ni remplacement ; produit et métadonnées conservés. Les dates existantes doivent correspondre aux dates demandées (sinon 409).
- Annulation depuis SCHEDULED ou IN_PROGRESS ; COMPLETED et CANCELLED sont terminaux. Les actions répétées donnent 409, sans doublon.
- Auth actuelle : ADMIN et TECHNICIAN actifs, sans affectation nominative ni rôles MANAGER/COMMERCIAL ajoutés (TD-B013 reste ouvert).
- Validation locale du 29/09/2026 : **271 tests backend réussis** sur SQLite. Les **92 tests PostgreSQL 17.4** mentionnés pour INT-103 ont été exécutés antérieurement ; PostgreSQL n'a pas été relancé pour INT-102. Aucun déploiement.
- Note : [INT-103 — installations autonomes](../../../../notes/backend/sprint7.3/INT-103-installations-autonomes.md).

---

## Cas de test

Voir [test-cases.json](test-cases.json).
