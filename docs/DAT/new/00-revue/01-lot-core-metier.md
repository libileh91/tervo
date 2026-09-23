# Lot 1 — Cœur métier 🔴

> **Objectif :** stabiliser les cinq entités fondatrices du modèle Tervo.
> **Périmètre :** responsabilités métier et relations — hors API, SQL, ORM.
> **Statut :** ✅ verrouillé.

---

# 1. Vue d'ensemble

Le cœur **physique** de Tervo est une chaîne de rattachement :

```text
Client ──► Site ──► Équipement ──► Intervention
                      ▲
                      │ référence d'origine
                   Produit
```

Le **Produit** (catalogue) n'appartient pas à la chaîne physique : c'est la _référence
commerciale_ dont l'équipement est issu.

---

# 2. Client

**Responsabilité** — le propriétaire ou l'interlocuteur commercial de la relation.

Un client peut être une personne, une entreprise ou une organisation.

**Relation :** `Client 1 → N Site`.

**Données :** identité, coordonnées, type (particulier / entreprise / organisation).

> Le client **n'est pas** une adresse physique. L'adresse appartient au **Site**.

---

# 3. Site

**Responsabilité** — le lieu physique où l'activité a lieu.

**Relations :** `Client 1 → N Site` · `Site 1 → N Équipement`.

**Données :** `name`, `address`, `postal_code`, `city`, `notes`.

Un site possède au minimum une identité et une localisation permettant d'intervenir.

Exemple :

```text
Client : Société Dupont
├── Site : Agence Massy
│    ├── PAC air/eau
│    └── Climatisation bureaux
└── Site : Agence Palaiseau
     └── Chaudière gaz
```

---

# 4. Produit catalogue

**Responsabilité** — la référence commerciale vendue ou présentée.

**Données :** `brand`, `model`, `reference`, `category`, `characteristics`, `active`.

**Relation :** `Produit 1 → N Équipement` (un produit peut être installé plusieurs fois).

> **Distinction clé :** un produit n'a pas d'historique d'intervention propre. Il n'est
> « suivi » qu'à travers les équipements physiques qui en sont issus.

---

# 5. Équipement

**Responsabilité** — l'instance **physique** réellement installée sur un site. C'est le
**centre de l'historique technique**.

**Données :** `site_id` (requis), `product_id` (nullable), `installation_id` (nullable),
`serial_number`, `installed_at`, `commissioned_at`, `warranty_start/end`,
`lifecycle_status`, `replaced_by_id`, `notes`.

**Cycle de vie :**

```text
ACTIVE ──► OUT_OF_SERVICE ──► REPLACED / RETIRED
```

> **Pas de `PLANNED`.** La planification relève de l'`Installation`, pas de l'équipement
> physique. Un équipement ne doit pas être créé artificiellement juste parce qu'une
> installation est planifiée.

**Remplacement :** `replaced_by_id` pointe de l'ancien vers le nouveau. L'ancien équipement
est **conservé** — il garde son n° de série, ses dates, ses interventions et son historique.

---

# 6. Intervention

**Responsabilité** — l'opération technique réalisée ou planifiée. C'est l'entité terrain
centrale (l'ancien « job », renommé).

**Données :** `site_id` (requis), `equipment_id` (nullable), `type`, `status`, `result`,
`scheduled_start/end`, `started_at`, `completed_at`, `under_warranty`, `description`,
`observations`, `created_by`.

**Règles :**

- `equipment_id` nullable — un diagnostic peut être créé au niveau du site, sans équipement
  encore identifié.
- Si `equipment_id` est renseigné → `Equipment.site_id == Intervention.site_id` (garanti
  côté métier).

**Type d'intervention :** installation, mise en service, maintenance préventive, maintenance
corrective, dépannage, diagnostic, SAV, autre.

---

# 7. Relations principales

| Relation                  | Cardinalité |
| ------------------------- | ----------- |
| Client → Site             | 1 → N       |
| Site → Équipement         | 1 → N       |
| Produit → Équipement      | 1 → N       |
| Équipement → Intervention | 1 → N       |

---

# 8. Décisions verrouillées

- [x] `Equipment` sans `PLANNED` — `ACTIVE / OUT_OF_SERVICE / REPLACED / RETIRED`
- [x] `replaced_by_id` (ancien → nouveau), l'ancien conservé
- [x] `equipment_id` nullable sur `Intervention` + règle site/équipement
- [x] `installation_id` nullable sur `Equipment` (import 20 ans)
- [x] `Intervention.under_warranty` (défaut `false`)
- [x] Identifiants entiers auto-incrémentés
