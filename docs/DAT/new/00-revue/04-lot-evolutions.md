# Lot 4 — Évolutions futures 🔵

> **Objectif :** délimiter ce qui **n'est pas** développé maintenant, et pourquoi.
> **Statut :** différé (documenté comme backlog, pas simulé).

---

# 1. Pourquoi un Lot 4

Tervo ne doit pas devenir un ERP/CRM complet avant d'avoir stabilisé son cœur. Les fonctions
ci-dessous **dépendent** du cœur métier — les construire trop tôt reviendrait à bâtir de
l'infrastructure autour d'un modèle encore instable.

---

# 2. Stock

Trois concepts distincts à ne pas confondre :

| Concept | Signification |
|---------|---------------|
| **Produit** (catalogue) | la référence visible |
| **Produit exposé** (showroom) | la référence présentée |
| **Stock** | le produit physiquement disponible |

La gestion complète (entrées, sorties, inventaire, seuils, réapprovisionnement) est **hors
cœur V1**. Une simple information de disponibilité peut suffire.

---

# 3. Fournisseurs / achats

```text
Fournisseur → Commande → Réception → Stock
```

C'est quasiment un **module d'achat** à part entière. Conservé comme évolution future, sans
dépendance avec le cœur actuel.

---

# 4. Contrats d'entretien

Un contrat peut être rattaché à un équipement :

```text
Équipement
    ├── Garantie
    ├── Contrat d'entretien
    └── Interventions
```

La gestion complète des contrats (échéances, reconduction, périmètre) est **hors MVP** —
à ne pas sur-modéliser en V1.

---

# 5. Reporting / KPI

Des KPI sont envisageables (interventions, maintenance, taux de résolution, équipements,
activité commerciale), mais un reporting avancé **prématuré** est un piège : il figerait des
mesures sur un modèle encore en évolution.

---

# 6. Devis (`Quote`)

Le devis est identifié fonctionnellement mais **pas nécessaire** au cœur technique V1.

```text
Showroom → QUOTE_REQUESTED / QUOTE_SENT   (suffit en V1)
```

Une entité `Quote` sera introduite quand le besoin commercial sera confirmé.

---

# 7. Périmètre final

| Niveau | Contenu |
|--------|---------|
| **🟢 Cœur V1** | Client, Site, Produit, Équipement, Intervention, Checklist, Photos, Matériel, Rapport |
| **🟠 V1 étendue** | Avis, Showroom, Vente, Installation, Garantie, SAV, Migration |
| **🔵 Évolution** | Stock, Fournisseurs, Achats, Contrats, KPI, Devis |

> **Principe :** les modules périphériques gravitent autour du cœur **sans le définir**.
