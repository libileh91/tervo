# Sprint 7.5 — Showroom et remplacement

> **Tervo V2** · INT-109 à INT-110 · **Statut :** INT-109 vérifiée localement ; INT-110 non démarrée
> **Dépendances :** Sprint 7.1, et 7.3 pour le lien showroom → vente. Vérifier le remplacement déjà amorcé dans INT-97 avant INT-110.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.5/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

> Dépend du Sprint 7.1 (et du Sprint 7.3 pour le lien showroom → vente).

---

> **Suivi frontend :** les besoins catalogue/showroom repris de l’ancien INT-83 sont tracés dans [TD-F007](../../../todos/frontend.md#td-f007--reprendre-les-besoins-frontend-catalogueshowroom-dans-le-modèle-v2).

## INT-109 — ShowroomVisit (4 pts)

**User Story**
En tant que **commercial**,
Je veux **enregistrer une visite showroom avec les produits présentés**,
Afin de **suivre le parcours prospect → vente**.

**Acceptance Criteria**
- [x] `ShowroomVisit` : `client_id` (nullable), `visitor_name`, `visited_at`, `salesperson_id`, `follow_up_status`, `notes`
- [x] `ShowroomVisitProduct` : `visit_id`, `product_id` (N↔N)
- [x] `follow_up_status` ∈ `TO_FOLLOW_UP / CONSIDERING / QUOTE_REQUESTED / QUOTE_SENT / SOLD / LOST / NO_FURTHER_ACTION`
- [x] API : `GET/POST /showroom/visits`, `POST /showroom/visits/{id}/products`

**Validation locale**
- Une recette API intégrée : prospect sans client, rattachement au client,
  présentations dédoublonnées, statut, filtres, droits, historique après
  désactivation du produit et suppression du client refusée.
- 19 cas réussis sur SQLite (recette + gardes de structure + migration
  historique), 4 gardes ciblées ventes/équipements réussies ; l'oracle
  d'import ciblé : 1 réussi. Migration INT-109 ciblée
  sur SQLite jetable : upgrade → downgrade vide → upgrade, CHECK SQL et refus
  du downgrade peuplé vérifiés.
- La recette PostgreSQL est configurée dans `ci.yml`, mais **aucune CI distante
  INT-109 ni migration PostgreSQL INT-109 n'a été exécutée**. Pas de
  smoke navigateur, push ou déploiement. Voir
  [la note pédagogique](../../../../notes/backend/sprint7.5/INT-109-showroom-visites.md).

**Technical Notes**
- Modules V2 : `app/modules/showroom/{models,schemas,repository,service,api}.py`,
  registre ORM, routeur, migration `m109e0010001`. `client_id` nullable ;
  `visitor_name` non blanc requis lorsqu'il est absent, au niveau API et SQL.
- `salesperson_id` = utilisateur connecté ; attribution d'un autre ID refusée.
  Pour l'instant `ADMIN` uniquement, car `MANAGER/COMMERCIAL` n'existent pas
  (TD-B013). Le frontend V2 reste à cadrer (TD-F007).
- GET détail, PATCH suivi/client/notes/date, DELETE association et liste
  paginée/filtrée complètent les routes indispensables pour consulter et
  corriger le suivi. La clé primaire `(visit_id, product_id)` évite les doublons.
- `SOLD` représente le suivi déclaré, pas une vente créée automatiquement.
  Aucun `sale_id` inféré à partir du client : plusieurs visites peuvent
  précéder une même vente. La provenance explicite attend un arbitrage
  métier distinct (TD-B023), sans inventer ici une cardinalité.

---

## INT-110 — Remplacement d'équipement (3 pts)

**User Story**
En tant que **technicien**,
Je veux **remplacer un équipement défaillant**,
Afin de **conserver l'historique de l'ancien et ouvrir un nouveau cycle**.

**Acceptance Criteria**
- [ ] `POST /equipment/{id}/replace` : ancien → `REPLACED` + `replaced_by_id` → nouveau
- [ ] Nouvel équipement : nouveau `serial_number`, `installed_at`, `warranty_*`
- [ ] L'ancien conserve ses interventions, rapports, photos
- [ ] Test : remplacer → ancien pointe vers nouveau, historique intact

**Technical Notes**
- Transaction métier (état ancien + création nouveau atomiques)
- Fichiers : `app/services/equipment.py`, `app/api/v1/equipment.py`

---

## Cas de test

Voir [test-cases.json](test-cases.json).
