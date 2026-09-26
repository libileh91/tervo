# Sprint 7.5 — Showroom et remplacement

> **Tervo V2** · INT-109 à INT-110 · **Statut :** À traiter
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
- [ ] `ShowroomVisit` : `client_id` (nullable), `visitor_name`, `visited_at`, `salesperson_id`, `follow_up_status`, `notes`
- [ ] `ShowroomVisitProduct` : `visit_id`, `product_id` (N↔N)
- [ ] `follow_up_status` ∈ `TO_FOLLOW_UP / CONSIDERING / QUOTE_REQUESTED / QUOTE_SENT / SOLD / LOST / NO_FURTHER_ACTION`
- [ ] API : `GET/POST /showroom/visits`, `POST /showroom/visits/{id}/products`

**Technical Notes**
- `client_id` nullable : prospect pas encore client (`visitor_name` requis en secours)
- Fichiers : `app/models/showroom.py`, `app/services/showroom.py`, `app/api/v1/showroom.py`

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
