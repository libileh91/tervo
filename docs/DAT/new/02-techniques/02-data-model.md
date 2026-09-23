# Tervo — Modèle de données

> Modèle de données métier et relationnel cible de Tervo.
>
> Ce document définit les principales entités, leurs responsabilités et leurs relations.
> Il sert de référence avant l'implémentation de la base de données.

---

# 1. Principes du modèle

Le modèle repose sur une distinction fondamentale entre :

```text
Référence commerciale
        │
        ▼
Produit catalogue
        │
        ▼
Vente
        │
        ▼
Installation
        │
        ▼
Équipement physique
        │
        ▼
Interventions
```

Ces concepts ne doivent pas être fusionnés.

Un produit catalogue décrit **ce qui peut être vendu**.

Un équipement décrit **ce qui est réellement installé chez un client**.

Une intervention décrit **ce qui a réellement été fait**.

---

# 2. Vue d'ensemble

```text
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1:N
       ▼
┌─────────────┐
│    Site     │
└──────┬──────┘
       │ 1:N
       ▼
┌─────────────────┐
│    Equipment    │
└──────┬──────────┘
       │ 1:N
       ▼
┌─────────────────┐
│  Intervention   │
└──────┬──────────┘
       │
       ├──── Checklist
       ├──── Photo
       ├──── Material
       ├──── Report
       └──── Review


┌─────────────────┐
│ ProductCatalog  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      Sale       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    SaleLine     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Installation   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Equipment    │
└─────────────────┘
```

Le modèle permet ainsi de relier le parcours commercial au parcours technique sans les confondre.

---

# 3. Client

## 3.1 Responsabilité

`Client` représente la personne ou l'organisation pour laquelle Tervo réalise une activité.

Types possibles :

```text
PERSON
COMPANY
ORGANIZATION
```

## 3.2 Données principales

```text
Client
├── id
├── type
├── name
├── email
├── phone
├── notes
├── created_at
└── updated_at
```

Les informations exactes de contact pourront évoluer sans modifier les relations métier principales.

## 3.3 Relations

```text
Client 1 ───── N Site
Client 1 ───── N Sale
Client 1 ───── N ShowroomVisit
```

---

# 4. Site

## 4.1 Responsabilité

`Site` représente un lieu physique appartenant à un client.

Exemples :

* domicile ;
* agence ;
* magasin ;
* atelier ;
* bâtiment professionnel.

Un client peut avoir plusieurs sites.

```text
Client
 ├── Site Massy
 ├── Site Paris
 └── Site Versailles
```

## 4.2 Données principales

```text
Site
├── id
├── client_id
├── name
├── address
├── postal_code
├── city
├── country
├── access_notes
├── notes
├── created_at
└── updated_at
```

## 4.3 Relations

```text
Client 1 ───── N Site
Site   1 ───── N Equipment
Site   1 ───── N Intervention
```

Une intervention peut être rattachée au site même lorsqu'aucun équipement précis n'a encore été identifié.

---

# 5. Produit catalogue

## 5.1 Responsabilité

`Product` représente une référence commerciale.

Exemples :

```text
PAC Air/Eau 8 kW
Climatiseur mural 3,5 kW
VMC double flux
Filtre
Thermostat
```

Le produit catalogue ne représente pas une machine physique précise.

## 5.2 Données principales

```text
Product
├── id
├── reference
├── name
├── description
├── brand
├── category
├── active
├── created_at
└── updated_at
```

Selon le besoin, des attributs techniques pourront être ajoutés ultérieurement.

## 5.3 Relations

```text
Product 1 ───── N SaleLine
Product 1 ───── N Equipment
```

La relation directe avec `Equipment` représente le produit dont provient l'équipement.

Elle ne remplace pas la traçabilité par la vente et l'installation.

---

# 6. Vente

## 6.1 Responsabilité

`Sale` représente un événement commercial.

Elle répond à la question :

> Qu'est-ce qui a été vendu, à quel client et quand ?

Une vente peut contenir plusieurs produits.

## 6.2 Données principales

```text
Sale
├── id
├── client_id
├── site_id
├── sale_date
├── status
├── notes
├── created_at
└── updated_at
```

Le `site_id` peut être facultatif lorsqu'il n'est pas encore déterminé au moment de la vente.

## 6.3 Statut

Le statut exact pourra évoluer, mais le modèle doit permettre au minimum de distinguer :

```text
DRAFT
CONFIRMED
CANCELLED
```

La notion de statut commercial ne doit pas être confondue avec l'état d'une installation.

---

# 7. Ligne de vente

## 7.1 Pourquoi une entité séparée ?

Une vente peut contenir plusieurs produits.

Exemple :

```text
Vente #5001

1 × PAC Air/Eau 8 kW
1 × Thermostat
2 × Accessoires
```

Il faut donc une entité `SaleLine`.

## 7.2 Données

```text
SaleLine
├── id
├── sale_id
├── product_id
├── quantity
├── unit_price
└── description
```

La description peut servir à conserver une information commerciale historique même si le produit catalogue évolue.

## 7.3 Relations

```text
Sale 1 ───── N SaleLine
Product 1 ── N SaleLine
```

---

# 8. Installation

## 8.1 Responsabilité

`Installation` représente l'événement technique qui transforme une vente ou une ligne vendue en équipement réellement installé.

Cette distinction est importante.

```text
Vente
   │
   ▼
Ligne de vente
   │
   ▼
Installation
   │
   ▼
Équipement
```

Une vente peut exister avant l'installation.

Une installation peut avoir lieu plusieurs jours ou mois après la vente.

## 8.2 Données principales

```text
Installation
├── id
├── sale_line_id
├── site_id
├── installation_date
├── commissioning_date
├── status
├── technician_notes
├── scheduled_start
├── scheduled_end
├── started_at
├── completed_at
├── created_at
└── updated_at
```

Le rattachement à `SaleLine` permet de conserver la provenance commerciale de l'équipement.

## 8.3 Statut

Exemple :

```text
SCHEDULED
IN_PROGRESS
COMPLETED
CANCELLED
```

Une installation terminée peut créer ou activer un équipement.

---

# 9. Équipement

## 9.1 Responsabilité

`Equipment` représente une **instance physique** installée sur un site.

Exemple :

```text
Produit :
PAC Daikin Altherma 8 kW

Équipement :
PAC installée chez M. Dupont
N° série : ABC123456
```

Le produit catalogue est une référence.

L'équipement est la machine réelle.

---

# 10. Données de l'équipement

```text
Equipment
├── id
├── site_id
├── product_id
├── installation_id
├── serial_number
├── installed_at
├── commissioned_at
├── warranty_start
├── warranty_end
├── lifecycle_status
├── replaced_by_id
├── notes
├── created_at
└── updated_at
```

Certains champs peuvent être facultatifs selon le type d'équipement et les informations disponibles.

`replaced_by_id` pointe depuis l'ancien équipement vers le nouvel équipement.
Exemple :
ancien_equipement.replaced_by_id = nouvel_equipement.id

---

# 11. Cycle de vie d'un équipement

Le modèle doit permettre de distinguer plusieurs états.

Exemple :

```text
INSTALLED
    │
    ▼
IN_SERVICE
    │
    ├──────────────┐
    ▼              ▼
MAINTENANCE      SAV / REPAIR
    │              │
    └──────┬───────┘
           │
           ▼
      REPLACED / RETIRED
```

La liste exacte des valeurs peut être simplifiée lors de l'implémentation.

Point important :

> Le remplacement d'un équipement ne supprime jamais l'ancien équipement.

---

# 12. Remplacement d'équipement

Exemple :

```text
Equipment #100
PAC ancienne
        │
        │ replaced_by_id
        ▼
Equipment #205
PAC nouvelle
```

L'ancien équipement conserve :

* son numéro de série ;
* ses dates ;
* ses interventions ;
* ses rapports ;
* son historique.

Le nouvel équipement possède sa propre histoire.

Cela permet :

```text
Site
 │
 ├── PAC #100 — remplacée
 │    ├── Maintenance 2023
 │    └── Dépannage 2024
 │
 └── PAC #205 — en service
      └── Maintenance 2026
```

---

# 13. Intervention

## 13.1 Responsabilité

`Intervention` est l'entité centrale du fonctionnement terrain.

Elle représente une opération technique réalisée ou planifiée.

## 13.2 Données principales

```text
Intervention
├── id
├── site_id
├── equipment_id
├── type
├── status
├── result
├── scheduled_start
├── scheduled_end
├── started_at
├── completed_at
├── under_warranty: boolean
├── description
├── observations
├── created_by
├── created_at
└── updated_at
```

`equipment_id` peut être nullable.

`under_warranty` conserve la qualification métier de l'intervention
au moment de sa réalisation. Il ne remplace pas les dates de garantie
portées par l'équipement.

Cela permet le cas :

```text
Diagnostic sur site
        │
        ▼
Équipement non identifié
```

Puis, une fois l'équipement identifié :

```text
Intervention
       │
       ▼
Equipment #123
```

---

# 14. Type d'intervention

Le type décrit **pourquoi** l'intervention existe.

Valeurs initiales :

```text
INSTALLATION
COMMISSIONING
PREVENTIVE_MAINTENANCE
CORRECTIVE_MAINTENANCE
TROUBLESHOOTING
DIAGNOSTIC
SAV
OTHER
```

Le type pourra évoluer sans modifier la structure générale.

---

# 15. Statut d'intervention

Le statut décrit **où en est le rendez-vous ou traitement**.

```text
PLANNED
    │
    ▼
IN_PROGRESS
    │
    ▼
COMPLETED
```

Une intervention peut également être :

```text
CANCELLED
```

Le statut ne décrit pas le résultat technique.

---

# 16. Résultat d'intervention

Le résultat décrit **ce qui a été obtenu**.

Valeurs initiales :

```text
RESOLVED
PARTIALLY_RESOLVED
UNRESOLVED
PART_REQUIRED
QUOTE_REQUIRED
FOLLOW_UP_REQUIRED
```

Exemple :

```text
status = COMPLETED
result = PART_REQUIRED
```

Cette séparation permet d'éviter un modèle ambigu du type :

```text
COMPLETED_WITH_PART_REQUIRED
```

qui mélange deux informations différentes.

---

# 17. Techniciens et intervenants

Une intervention peut nécessiter plusieurs personnes.

```text
Intervention
      │
      ├── Technician A
      ├── Technician B
      └── Technician C
```

Le modèle prévoit donc une relation plusieurs-à-plusieurs :

```text
User N ───── N Intervention
```

via une entité d'association, par exemple :

```text
InterventionTechnician
├── intervention_id
├── user_id
└── role
```

Le `role` permet éventuellement de distinguer :

```text
LEAD
ASSISTANT
OBSERVER
```

Sans imposer ces valeurs dès la V1 si le besoin n'est pas confirmé.

---

# 18. Checklist

Il faut distinguer :

```text
ChecklistTemplate
```

et :

```text
InterventionChecklist
```

## 18.1 Modèle

```text
ChecklistTemplate
├── id
├── name
├── intervention_type
├── version
├── active
└── ...
```

## 18.2 Instance historique

```text
InterventionChecklist
├── id
├── intervention_id
├── template_id
├── template_version
└── ...
```

Les éléments de la checklist sont ensuite enregistrés avec l'intervention.

---

# 19. Éléments de checklist

```text
ChecklistItem
├── id
├── intervention_checklist_id
├── label
├── position
├── result
├── comment
└── completed_at
```

Exemple :

```text
☑ Pression contrôlée
☑ Température mesurée
☑ Connexions vérifiées
☐ Nettoyage à effectuer
```

Le libellé et la position doivent rester cohérents avec l'état historique de l'intervention.

---

# 20. Photos

Une photo appartient à une intervention.

```text
Photo
├── id
├── intervention_id
├── storage_key
├── filename
├── mime_type
├── size
├── category
├── captured_at
└── created_at
```

Catégories initiales :

```text
BEFORE
AFTER
EQUIPMENT
ANOMALY
PART
OTHER
```

Le fichier physique est stocké hors de PostgreSQL.

---

# 21. Matériel utilisé

En V1, le matériel utilisé peut rester volontairement simple.

```text
MaterialUsage
├── id
├── intervention_id
├── designation
├── quantity
└── unit
```

Exemple :

```text
Intervention #1042

Filtre        1 unité
Collier       2 unités
Câble         5 m
```

Une future version pourra ajouter :

```text
product_id
stock_item_id
lot_number
```

si la gestion de stock devient nécessaire.

---

# 22. Rapport

Le rapport représente la restitution documentaire d'une intervention.

```text
Report
├── id
├── intervention_id
├── version
├── status
├── generated_at
├── transmitted_at
├── storage_key
└── created_at
```

## 22.1 Historique

Le système doit pouvoir conserver plusieurs versions lorsqu'un nouveau rapport est généré.

```text
Intervention #1042
       │
       ├── Rapport v1
       └── Rapport v2
```

Le principe est :

> Une nouvelle génération crée une nouvelle représentation documentaire plutôt que de modifier silencieusement un rapport déjà transmis.

---

# 23. Avis client

Une intervention peut avoir zéro ou un avis.

```text
Review
├── id
├── intervention_id
├── rating
├── comment
├── created_at
└── ...
```

Relation :

```text
Intervention 1 ───── 0..1 Review
```

Une contrainte d'unicité doit empêcher plusieurs avis pour la même intervention si cette règle reste celle retenue.

---

# 24. Garantie

La garantie concerne l'équipement physique.

Elle peut être représentée initialement directement sur `Equipment` :

```text
warranty_start
warranty_end
```

Cette approche est suffisante si Tervo ne gère qu'une garantie simple.

Si plusieurs garanties doivent être supportées ultérieurement, le modèle pourra évoluer vers :

```text
Equipment
    │
    └── N Warranty
```

avec par exemple :

```text
Warranty
├── id
├── equipment_id
├── type
├── start_date
├── end_date
├── provider
└── terms
```

En V1, il n'est pas nécessaire d'introduire cette entité si le besoin n'est pas confirmé.

---

# 25. Intervention sous garantie

Une intervention SAV ne doit pas déduire automatiquement son statut de garantie uniquement à partir des dates de l'équipement.

Une qualification explicite est préférable.

Exemple :

```text
Intervention
├── type = SAV
└── under_warranty = true
```

Cela permet de distinguer :

```text
Équipement sous garantie
```

de :

```text
Intervention effectivement traitée sous garantie
```

Cette distinction est importante pour les cas commerciaux ou contractuels.

---

# 26. Showroom

Le showroom possède son propre modèle minimal.

## 26.1 Visite

```text
ShowroomVisit
├── id
├── client_id
├── visitor_name
├── visited_at
├── salesperson_id
├── follow_up_status
├── notes
└── created_at
```

Une visite peut concerner plusieurs produits.

`client_id`: Une visite showroom peut concerner un prospect qui n'est pas encore
enregistré comme client. `client_id` est donc nullable ; `visitor_name`
permet de conserver l'identité du visiteur.

```text
ShowroomVisit N ───── N Product
```

via :

```text
ShowroomVisitProduct
├── visit_id
└── product_id
```

## 26.2 Suivi commercial

Valeurs initiales possibles :

```text
TO_FOLLOW_UP
CONSIDERING
QUOTE_REQUESTED
QUOTE_SENT
SOLD
LOST
NO_FURTHER_ACTION
```

Ces valeurs décrivent le suivi commercial et ne doivent pas être confondues avec le statut d'une vente.

---

# 27. Lien showroom → vente

Le parcours peut être :

```text
ShowroomVisit
      │
      ▼
Commercial follow-up
      │
      ▼
Sale
      │
      ▼
Installation
      │
      ▼
Equipment
```

Le modèle doit conserver ce lien lorsque la vente provient effectivement d'une visite showroom.

La visite n'est cependant pas obligatoire pour créer une vente.

---

# 28. Relations principales

Vue simplifiée :

```text
Client
 │
 ├───────────────< Site
 │                   │
 │                   ├──────< Equipment
 │                   │            │
 │                   │            ├──────< Intervention
 │                   │            │           ├──< Photo
 │                   │            │           ├──< MaterialUsage
 │                   │            │           ├──< Report
 │                   │            │           ├──< Review
 │                   │            │           └──< Checklist
 │                   │            │
 │                   │            └──────< Equipment
 │                   │
 │                   └──────< Intervention
 │
 ├───────────────< Sale
 │                   │
 │                   └──────< SaleLine >──── Product
 │                                      │
 │                                      ▼
 │                                 Installation
 │                                      │
 │                                      ▼
 │                                  Equipment
 │
 └───────────────< ShowroomVisit
                         │
                         └────< ShowroomVisitProduct >──── Product
```

---

# 29. Entités V1

Le périmètre relationnel principal est :

| Entité                   | Rôle                                   |
| ------------------------ | -------------------------------------- |
| `Client`                 | Client de Tervo                        |
| `Site`                   | Lieu physique                          |
| `Product`                | Référence catalogue                    |
| `Sale`                   | Événement commercial                   |
| `SaleLine`               | Produit vendu dans une vente           |
| `Installation`           | Événement d'installation               |
| `Equipment`              | Instance physique installée            |
| `Intervention`           | Opération technique                    |
| `InterventionTechnician` | Techniciens affectés                   |
| `ChecklistTemplate`      | Modèle de checklist                    |
| `InterventionChecklist`  | Checklist appliquée à une intervention |
| `ChecklistItem`          | Élément historique de checklist        |
| `Photo`                  | Photo d'intervention                   |
| `MaterialUsage`          | Matériel consommé/utilisé              |
| `Report`                 | Document d'intervention                |
| `Review`                 | Avis client                            |
| `ShowroomVisit`          | Visite showroom                        |
| `ShowroomVisitProduct`   | Produits présentés                     |

---

# Entités techniques de migration

Les trois entités suivantes ne font **pas** partie du modèle métier : ce sont des entités
**techniques** qui assurent la traçabilité et l'idempotence du pipeline d'import.

| Entité         | Rôle                                                        |
| -------------- | ----------------------------------------------------------- |
| `ImportBatch`  | un lot d'import (fichier, hash SHA-256, statut)             |
| `ImportRecord` | traçabilité ligne à ligne (source → entité créée)           |
| `ImportError`  | les anomalies (validation, orphelin, rapprochement ambigu)  |

```text
ImportBatch
├── id
├── filename
├── file_hash            -- SHA-256 du fichier (idempotence)
├── type_import
├── status               -- running / success / partial / failed / skipped
├── started_at
├── completed_at
├── rapport
└── imported_by

ImportRecord
├── id
├── import_batch_id
├── source_file
├── source_row
├── source_hash
├── entity_type         -- client / site / equipment / intervention / product
└── entity_id

ImportError
├── id
├── import_batch_id
├── ligne
├── colonne
├── valeur
├── erreur
├── status               -- VALIDATION_ERROR / ORPHAN / DUPLICATE_AMBIGUOUS
├── original_value
└── created_at
```

> **Règle :** ces tables assurent la **traçabilité du pipeline de migration** et ne
> constituent **pas** le modèle métier principal. Elles ne sont utilisées que par l'import,
> jamais par les écrans métier.

---

# 30. Entités volontairement différées

Ne pas introduire immédiatement des entités pour :

```text
Stock
Supplier
PurchaseOrder
Contract
MaintenanceContract
Invoice
Payment
Advanced KPI
```

Ces concepts pourront être ajoutés lorsque leur besoin métier sera suffisamment précis.

Le modèle actuel doit toutefois éviter de rendre leur ajout impossible.

---

# 31. Contraintes métier importantes

## Client / Site

```text
Site.client_id → Client.id
```

Un site ne doit pas exister sans client.

---

## Équipement

```text
Equipment.site_id → Site.id
```

Un équipement installé doit toujours avoir un site.

---

## Intervention

```text
Intervention.site_id → Site.id
Intervention.equipment_id → Equipment.id NULLABLE
```

Lorsque `equipment_id` est renseigné, l'équipement doit appartenir au même site que l'intervention.

Cette règle doit être garantie au niveau métier.

---

## Installation

```text
Installation.sale_line_id → SaleLine.id
Installation.site_id → Site.id

SaleLine 1 ─── N Installation
Installation 1 ─── 0..1 Equipment
```

Une installation doit identifier ce qui est installé et où.

Une ligne de vente peut correspondre à plusieurs installations lorsque la
quantité vendue est supérieure à 1.

Chaque installation représente l'installation physique d'une unité.
Une installation terminée crée ou rattache un équipement physique.

---

## Vente

```text
Sale.client_id → Client.id
Sale 1 → N SaleLine
```

Une vente confirmée doit contenir au moins une ligne.

---

# 32. Historique et suppression

Les données métier historiques ne doivent pas être supprimées physiquement sans raison.

Exemples particulièrement sensibles :

```text
Equipment
Intervention
Report
Installation
Sale
```

Une suppression logique ou un changement d'état peut être préférable lorsqu'il faut conserver l'historique.

Le choix exact entre :

```text
soft delete
```

et :

```text
statut / archivage
```

sera déterminé lors de l'implémentation.

---

# 33. Identifiants

Chaque entité possède un identifiant technique unique.

**Décision verrouillée :** identifiant **entier auto-incrémenté**
(`SERIAL` / `Integer`). Pas d'`UUID` en V1 : le monolithe PostgreSQL n'a pas
besoin de clés distribuées, et l'existant est déjà en entiers.

Le système doit permettre de référencer une entité de manière stable dans
les API et les documents.

---

# 34. Dates

Les dates métier importantes doivent être distinguées des dates techniques.

Exemple pour une intervention :

```text
scheduled_start
scheduled_end

started_at
completed_at

created_at
updated_at
```

Ainsi :

```text
date planifiée
```

ne signifie pas :

```text
date réellement réalisée
```

Même principe pour l'installation :

```text
installation_date
commissioning_date
created_at
updated_at
```

---

# 35. Exemple complet

Cas réel simplifié :

> Un client achète une PAC. Elle est installée dans sa maison. Six mois plus tard, un technicien réalise une maintenance.

```text
Client
└── Dupont
     │
     └── Site
          └── Maison Massy
               │
               └── Equipment
                    ├── Product : PAC Air/Eau 8 kW
                    ├── Serial : ABC123
                    ├── Installed : 2026-03-12
                    └── Warranty : 2026-03 → 2030-03
                         │
                         └── Intervention
                              ├── Type : PREVENTIVE_MAINTENANCE
                              ├── Status : COMPLETED
                              ├── Result : RESOLVED
                              ├── Checklist
                              ├── Photos
                              ├── Material
                              └── Report
```

La provenance commerciale reste accessible :

```text
Product
   │
   ▼
Sale
   │
   ▼
SaleLine
   │
   ▼
Installation
   │
   ▼
Equipment
```

Le système peut donc répondre à plusieurs questions :

```text
Quel produit a été vendu ?
        ↓
Quelle vente ?
        ↓
Quelle installation ?
        ↓
Quel équipement ?
        ↓
Où est-il installé ?
        ↓
Quelles interventions ?
        ↓
Quels résultats ?
        ↓
Quels rapports ?
```

---

# 36. Principes structurants

Le modèle doit respecter les principes suivants.

### D1 — Produit ≠ équipement

Une référence catalogue peut correspondre à plusieurs équipements physiques.

### D2 — Vente ≠ installation

Une vente peut être réalisée avant l'installation.

### D3 — Installation ≠ équipement

L'installation est un événement ; l'équipement est l'objet physique qui en résulte.

### D4 — Équipement = centre de l'historique technique

L'historique des interventions doit être consultable depuis l'équipement.

### D5 — Intervention ≠ résultat

Le statut de traitement et le résultat technique sont deux informations différentes.

### D6 — Checklist modèle ≠ checklist historique

Une intervention conserve l'état de sa checklist au moment de son exécution.

### D7 — Rapport ≠ simple vue dynamique

Un rapport transmis constitue une représentation historique de l'intervention.

### D8 — Remplacement ≠ suppression

Un ancien équipement reste consultable.

### D9 — Garantie ≠ SAV

La garantie est une caractéristique de l'équipement ; le SAV est une activité pouvant donner lieu à une intervention.

### D10 — Showroom ≠ vente

Une visite commerciale ne signifie pas qu'une vente a eu lieu.

### D11 — Historique > simplification

Le modèle doit privilégier la conservation de l'historique métier plutôt que la suppression d'informations pour simplifier la base.

---

# 37. Modèle cible résumé

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
                           │  EQUIPMENT  │◄──────────────┐
                           └──────┬──────┘               │
                                  │                      │
                                  ▼                      │
                           ┌─────────────┐               │
                           │INTERVENTION │               │
                           └──────┬──────┘               │
                                  │                      │
                 ┌────────────────┼───────────────┐      │
                 ▼                ▼               ▼      │
            CHECKLIST          PHOTO          MATERIAL   │
                 │                │               │      │
                 └────────────────┼───────────────┘      │
                                  ▼                      │
                              REPORT                     │
                                                         │
                                                         │
PRODUCT ──► SALE ──► SALE_LINE ──► INSTALLATION ────────┘
   │
   └──────────────► SHOWROOM VISIT
```

Ce modèle constitue la base relationnelle de Tervo.

Les choix d'implémentation — ORM, types SQL, index, contraintes techniques, migrations — sont définis lors de l'implémentation à partir de ce modèle.
