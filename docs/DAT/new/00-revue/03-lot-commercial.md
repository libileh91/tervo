# Lot 3 — Chaîne commerciale 🟡

> **Objectif :** relier le catalogue à l'équipement via la vente et l'installation.
> **Périmètre :** parcours commercial — hors API et implémentation.
> **Statut :** ✅ verrouillé.

---

# 1. Vue d'ensemble

```text
Produit ──► Vente ──► SaleLine ──► Installation ──► Équipement
```

La vente et l'installation sont **deux événements distincts** : un produit peut être vendu
sans être installé, et l'installation peut intervenir des semaines après la vente.

---

# 2. Vente (`Sale`) et ligne de vente (`SaleLine`)

- `Sale` : `client_id`, `site_id`, `sale_date`, `status` (`DRAFT / CONFIRMED / CANCELLED`).
- `SaleLine` : `sale_id`, `product_id`, `quantity`, `unit_price`.
- `Sale 1 → N SaleLine` ; une vente confirmée contient **au moins** une ligne.

**Point clé — la quantité :** `quantity > 1` est la source du `SaleLine 1 → N Installation`.
Une PAC vendue ×3 donnera **3 installations** et **3 équipements** distincts.

---

# 3. Installation

`Installation` est l'événement qui transforme une ligne vendue en équipement physique.

**Données :** `sale_line_id`, `site_id`, `scheduled_start/end`, `started_at`, `completed_at`,
`installation_date`, `commissioning_date`, `status`, `technician_notes`.

**Statut :**

```text
SCHEDULED
    ↓ start
IN_PROGRESS
    ↓ complete
COMPLETED
    (CANCELLED : sortie alternative autorisée)
```

**Transition `complete` (transaction métier atomique) :**

```text
Installation → COMPLETED
       +
Equipment → créé / rattaché
```

Une installation **terminée** crée ou rattache l'équipement ; une installation **planifiée**
ne crée **pas** d'équipement.

---

# 4. Showroom

Le showroom est une activité de prospection, distincte de l'installation terrain.

- `ShowroomVisit` : `client_id` (nullable), `visitor_name`, `visited_at`, `salesperson_id`,
  `follow_up_status`, `notes`.
- `ShowroomVisit N → N Product` via `ShowroomVisitProduct`.

> **`client_id` nullable :** une visite peut concerner un prospect pas encore client.
> `visitor_name` conserve l'identité du visiteur.

**Suivi commercial :** `TO_FOLLOW_UP / CONSIDERING / QUOTE_REQUESTED / QUOTE_SENT / SOLD /
LOST / NO_FURTHER_ACTION`.

> Le suivi commercial n'est **pas** le statut d'une vente, et ne doit pas transformer la
> visite en CRM complet.

---

# 5. Garantie / SAV

- La **garantie** est portée par l'équipement (`warranty_start/end`).
- Le **SAV** est une activité sur cet équipement, traitée par une intervention.

```text
Équipement
    ├── Garantie
    └── SAV ──► Intervention
```

L'historique SAV se reconstruit naturellement à partir de l'historique de l'équipement.

---

# 6. Décisions verrouillées

- [x] Vente ≠ Installation ≠ Équipement
- [x] `Sale 1 → N SaleLine` · `SaleLine 1 → N Installation` (`quantity > 1`)
- [x] Statuts `Installation` : `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`
- [x] `complete` → `Installation COMPLETED` + `Equipment` créé (atomique)
- [x] `ShowroomVisit.client_id` nullable (`visitor_name` requis en secours)
- [x] `Quote` (devis) hors modèle V1 — `QUOTE_REQUESTED / QUOTE_SENT` suffisent

### Points de raffinement (non bloquants)

- [ ] Liste définitive des états de suivi showroom
- [ ] Règles précises de garantie (multi-garanties → entité `Warranty` dédiée, plus tard)
