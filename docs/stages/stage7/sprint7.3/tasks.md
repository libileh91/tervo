# Sprint 7.3 — Chaîne commerciale

> **Tervo V2** · INT-102 à INT-103 · **Statut :** À démarrer — prochaine tâche INT-102
> **Dépendances :** Sprint 7.1 ; raccorder la FK Installation laissée en attente dans TD-B014.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.3/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

---

## INT-102 — `Sale` + `SaleLine` (5 pts)

**User Story**
En tant que **commercial**,
Je veux **enregistrer une vente avec ses lignes de produits**,
Afin de **distinguer l'événement commercial de l'installation future**.

**Acceptance Criteria**
- [ ] `Sale` : `client_id`, `site_id`, `sale_date`, `status` (`DRAFT / CONFIRMED / CANCELLED`)
- [ ] `SaleLine` : `sale_id`, `product_id`, `quantity`, `unit_price`
- [ ] `Sale 1 → N SaleLine` ; une vente confirmée a ≥ 1 ligne
- [ ] API : `POST /sales`, `POST /sales/{id}/confirm`, `POST /sales/{id}/cancel`
- [ ] Test : `quantity = 3` → 3 lignes possibles → 3 installations ultérieures

**Technical Notes**
- `quantity` > 1 est la clé du `SaleLine 1 → N Installation`

---

## INT-103 — `Installation` (5 pts)

**User Story**
En tant que **technicien**,
Je veux **suivre l'installation d'un équipement vendu**,
Afin de **créer l'équipement physique au moment où il est réellement installé**.

**Acceptance Criteria**
- [ ] `Installation` : `sale_line_id`, `site_id`, `scheduled_start/end`, `started_at`, `completed_at`, `installation_date`, `commissioning_date`, `status`
- [ ] `status` ∈ `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`
- [ ] `POST /installations/{id}/start`, `/complete`, `/cancel`
- [ ] `complete` (même transaction) : `Installation → COMPLETED` + `Equipment` créé/rattaché
- [ ] Test : installation complétée → 1 équipement créé, `installation_id` renseigné

**Technical Notes**
- `complete` est une **transaction métier** (installation + équipement atomiques)

---

## Cas de test

Voir [test-cases.json](test-cases.json).
