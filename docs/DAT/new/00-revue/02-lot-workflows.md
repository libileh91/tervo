# Lot 2 — Workflows métier 🟠

> **Objectif :** définir le comportement métier autour de l'intervention.
> **Périmètre :** règles et workflows — hors API et implémentation.
> **Statut :** ✅ verrouillé.

---

# 1. Statut ≠ Résultat

L'avancement d'une intervention et son issue métier sont **deux informations différentes**.

| Statut (avancement) | Résultat (issue métier) |
|---------------------|--------------------------|
| `PLANNED` | `Résolu` |
| `IN_PROGRESS` | `Partiellement résolu` |
| `COMPLETED` | `Non résolu` / `Pièce nécessaire` / `Devis nécessaire` / `À replanifier` |
| `CANCELLED` | — |

Exemple : une intervention peut être **`COMPLETED`** avec un résultat **`Pièce nécessaire`**.
« Terminée » ne signifie pas « résolu ».

Le résultat est renseigné à la clôture et reste indépendant du statut.

---

# 2. Checklist : modèle vs snapshot historique

Une checklist possède deux niveaux :

```text
Modèle de checklist
       │  au moment de la création
       ▼
Checklist de l'intervention   (snapshot)
```

- Le **modèle** est rattaché à un type d'intervention.
- Le **snapshot** est généré à la création de l'intervention et devient sa donnée historique.

> **Règle :** modifier un modèle ne doit **jamais** modifier les checklists des interventions
> passées.

---

# 3. Rapport : document historisé et versionné

Le rapport est un **document métier**, pas une simple vue d'écran.

```text
Intervention
      │
      └── Report (document logique)
             ├── version 1   ← transmise au client
             ├── version 2
             └── ...
```

- Un rapport transmis reste **historiquement stable** : corriger l'intervention ne réécrit pas
  le document déjà envoyé.
- Une correction conduit à générer une **nouvelle version**, l'ancienne est conservée.

---

# 4. Matériel utilisé

**V1 :** matériel libre (désignation + quantité), sans dépendance au catalogue.

```text
Matériel
├── désignation
└── quantité
```

**Évolution possible :** relier le matériel au `Product` (catalogue) — mais cette dépendance
n'est **pas imposée** au cœur du MVP.

---

# 5. Avis client

```text
Intervention 1 → 0..1 Avis
```

- Une intervention produit **zéro ou un** avis.
- L'avis est rattaché à l'intervention pour conserver le contexte.
- Une intervention terminée **peut** donner lieu à une demande d'avis (le déclenchement
  automatique exact reste un raffinement).

---

# 6. Remplacement d'équipement

Lorsqu'un équipement est remplacé :

```text
Ancien Equipment
      │
      ▼
Nouvel Equipment créé
      │
      ▼
ancien.replaced_by_id = nouveau.id
      │
      ▼
historique ancien conservé
```

Le nouvel équipement possède sa **propre** identité et son **propre** historique.

---

# 7. Garantie et `under_warranty`

- La **garantie** est une propriété de l'**équipement** (`warranty_start/end`).
- `under_warranty` est une qualification de l'**intervention** : elle conserve le fait que
  l'opération a été traitée **sous garantie** au moment de sa réalisation.

> **Ne pas déduire** « intervention sur équipement garanti = intervention sous garantie ».
> Le contexte de l'intervention détermine la couverture réelle, et cette qualification est
> **historisée** sur l'intervention.

---

# 8. Décisions verrouillées

- [x] Séparer **statut** et **résultat**
- [x] Checklist **modèle vs snapshot** (l'historique ne bouge pas)
- [x] Rapport **versionné** (document logique + versions physiques)
- [x] Matériel **libre** en V1
- [x] Avis `0..1` par intervention
- [x] Remplacement via `replaced_by_id`, ancien conservé
- [x] `under_warranty` sur l'intervention, distinct des dates de garantie

### Points de raffinement (non bloquants)

- [ ] Liste définitive des types d'intervention et des résultats
- [ ] Quelles interventions déclenchent une demande d'avis
- [ ] Moment exact où une intervention devient définitivement clôturée
