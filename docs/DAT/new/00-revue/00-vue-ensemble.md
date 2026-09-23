# Revue fonctionnelle & modèle métier — Tervo v2

> **Statut :** DAT retravaillé et **verrouillé** (post-refonte).
> **Objet :** vue d'ensemble (« gros plan ») du modèle métier et découpage en lots.
> **Source de vérité :** `docs/DAT/new/` — `01-fonctionnel/`, `02-techniques/`, `03-modules/`, `04-roadmap/`.
> **Hors périmètre de cette revue :** architecture technique (FastAPI, SQLAlchemy, Docker, endpoints).

---

# 1. Synthèse

La première revue a montré que le modèle était trop centré sur **l'intervention** :

```text
Client ──► Intervention ──► Checklist / Photos / Matériel / Rapport / Avis
```

Pour une activité CVC qui évolue vers la maintenance, le SAV et la garantie, le point
d'ancrage naturel n'est pas l'intervention mais **l'équipement physique installé**.

Le DAT a donc été retravaillé autour de **deux chaînes** :

```text
①  Chaîne physique    —  Client ──► Site ──► Équipement ──► Intervention
②  Chaîne commerciale —  Produit ──► Vente ──► SaleLine ──► Installation ──► Équipement
```

Et une **activité de prospection** (showroom) qui alimente la chaîne commerciale.

> **Principe directeur :** Tervo doit savoir **ce qui a été vendu, ce qui a été installé
> chez quel client, et ce qui a été fait dessus.**

---

# 2. Les distinctions structurantes

Le modèle verrouillé repose sur **quatre séparations** qui évitent les confusions
classiques d'un outil de gestion CVC :

| Distinction                                | Pourquoi                                                                                  |
| ------------------------------------------ | ----------------------------------------------------------------------------------------- |
| **Produit ≠ Équipement**                   | la référence catalogue est vendue N fois ; l'équipement est l'instance physique installée |
| **Vente ≠ Installation ≠ Équipement**      | trois événements distincts : vendu, installé, en service                                  |
| **Statut ≠ Résultat**                      | « terminée » ≠ « résolu » — l'avancement n'est pas l'issue métier                         |
| **Checklist modèle ≠ snapshot historique** | modifier un modèle ne réécrit pas les interventions passées                               |

---

# 3. Organisation des lots

| Lot       | Priorité      | Objet                                                                       | Fichier                 |
| --------- | ------------- | --------------------------------------------------------------------------- | ----------------------- |
| **Lot 1** | 🔴 Cœur       | `Client`, `Site`, `Product`, `Equipment`, `Intervention`                    | `01-lot-core-metier.md` |
| **Lot 2** | 🟠 Workflow   | statut/résultat, checklist, rapport, matériel, avis, remplacement, garantie | `02-lot-workflows.md`   |
| **Lot 3** | 🟡 Commercial | `Sale`/`SaleLine`, `Installation`, showroom, garantie/SAV                   | `03-lot-commercial.md`  |
| **Lot 4** | 🔵 Futur      | stock, fournisseurs, achats, contrats, KPI, devis                           | `04-lot-evolutions.md`  |

> La **migration Excel** n'est pas un lot fonctionnel : c'est le **différenciateur
> transverse**, documenté dans `05-migration-donnees.md`.

---

# 4. Décisions verrouillées

Toutes les décisions qui étaient « à prendre » lors de la première revue sont désormais
**actées** :

| Décision                           | Verdict                                             |
| ---------------------------------- | --------------------------------------------------- |
| Identifiants                       | entier auto-incrémenté (pas d'UUID)                 |
| `Equipment` sans `PLANNED`         | `ACTIVE / OUT_OF_SERVICE / REPLACED / RETIRED`      |
| `SaleLine 1 → N Installation`      | oui (`quantity > 1` → N installations)              |
| Statuts `Installation`             | `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`   |
| `Report` versionné V1              | document logique + versions                         |
| `ShowroomVisit.client_id` nullable | oui (prospect non encore client)                    |
| Devis (`Quote`)                    | hors modèle V1                                      |
| Rôles                              | normalisés (admin, manager, technicien, commercial) |
| `replaced_by_id`                   | ancien → nouveau                                    |
| `Intervention.under_warranty`      | oui                                                 |

---

# 5. La migration, différenciateur transverse

La migration de **20 ans d'Excel** est le sujet technique central du projet. Elle est
**remontée** dans la priorité (elle ne dépend que du Lot 1) et cible :

```text
Client ──► Site ──► Équipement ──► Intervention   (+ Product pour le catalogue)
```

Point important : les équipements historiques ont `installation_id` **nullable** — ils ont
été installés il y a des années, sans vente/installation enregistrée dans Tervo. La migration
ne doit donc **pas inventer** de données manquantes (pas de vente, pas de n° de série fictif).

Les mécanismes conservés : **normalisation → fuzzy matching (3 zones 95/80) → validation →
2 passes → transaction par batch → idempotence SHA-256 → orphelins tracés**.

---

# 6. Modèle cible

```text
                           ┌─────────────┐
                           │   CLIENT    │
                           └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │    SITE     │
                           └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │  EQUIPMENT  │◄───────────────┐
                           └──────┬──────┘                │
                                  │                       │
                                  ▼                       │
                           ┌─────────────┐                │
                           │INTERVENTION │                │
                           └──────┬──────┘                │
                                  │                       │
                 ┌────────────────┼───────────────┐       │
                 ▼                ▼               ▼       │
            CHECKLIST          PHOTO          MATERIAL    │
                 │                │               │       │
                 └────────────────┼───────────────┘       │
                                  ▼                       │
                              REPORT                      │
                                                          │
PRODUCT ──► SALE ──► SALE_LINE ──► INSTALLATION ──────────┘
   │
   └──────────────► SHOWROOM VISIT
```

---

# 7. Principe directeur final

```text
STRUCTURER  →  VENDRE  →  INSTALLER  →  IDENTIFIER L'ÉQUIPEMENT
     →  INTERVENIR  →  PROUVER  →  RESTITUER  →  HISTORISER
```

> **Tervo ne doit pas devenir une collection de modules indépendants.** Le produit construit
> une histoire cohérente, du produit vendu jusqu'à l'historique technique de l'équipement.
