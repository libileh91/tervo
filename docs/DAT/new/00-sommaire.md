# Tervo — Document d'Architecture Technique

> **Projet :** Tervo — gestion des activités d'intervention CVC
> **Statut :** refonte du DAT
> **Sprints Tervo V2 :** [Stage 7 — découpage et avancement](../../stages/stage7/README.md)
> **Branche de travail :** `chore/rewrite-dat`

## 1. Rôle du DAT

Ce document décrit les décisions structurantes de Tervo : son fonctionnement métier, son modèle de domaine, ses workflows, puis leur traduction technique.

Le DAT sert de référence pour concevoir et faire évoluer le produit. Il ne remplace ni le code, ni les procédures d'exploitation, ni les notes de travail.

## 2. Organisation

```text
docs/DAT/
├── 00-sommaire.md
├── 00-revue/
│   ├── 00-vue-ensemble.md
│   ├── 01-lot-core-metier.md
│   ├── 02-lot-workflows.md
│   ├── 03-lot-commercial.md
│   ├── 04-lot-evolutions.md
│   └── 05-migration-donnees.md
├── 01-fonctionnel/
│   ├── 01-specifications.md
│   ├── 02-modele-metier.md
│   └── 03-workflows.md
├── 02-techniques/
│   ├── 01-architecture.md
│   ├── 02-data-model.md
│   ├── 03-api.md
│   └── 04-securite.md
├── 03-modules/
│   ├── catalogues.md
│   ├── interventions.md
│   └── showroom.md
└── 04-roadmap/
    └── implementation.md
```

## 3. Périmètre

Le cœur de Tervo couvre :

* clients et sites ;
* catalogue de produits ;
* ventes et installations ;
* équipements installés ;
* interventions CVC ;
* checklists, photos et matériel utilisé ;
* rapports d'intervention ;
* avis clients ;
* showroom et suivi commercial ;
* conservation de l'historique.

Le stock, les fournisseurs, les achats, les contrats avancés et le reporting métier avancé restent des fonctions périphériques tant qu'elles ne sont pas nécessaires au cœur du produit.

## 4. Principe métier central

Tervo doit d'abord savoir :

> **ce qui a été vendu, ce qui a été installé pour quel client et ce qui a été fait dessus.**

Le cycle métier de référence est :

```text
CATALOGUE
    │
    ▼
  VENTE
    │
    ▼
INSTALLATION
    │
    ▼
ÉQUIPEMENT
    ├── Maintenance
    ├── Dépannage
    └── SAV
           │
           ▼
      INTERVENTION
       ├── Checklist
       ├── Photos
       ├── Matériel
       ├── Rapport
       └── Avis
```

Cette chaîne constitue la base sur laquelle les fonctions commerciales, de maintenance et de suivi pourront évoluer.
