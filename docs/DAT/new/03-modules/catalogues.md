# Tervo — Module Catalogue

## 1. Objectif

Le module Catalogue constitue le référentiel des produits commercialisés par Tervo.

Il permet de :

* créer et gérer les produits ;
* rechercher et filtrer le catalogue ;
* présenter les produits dans le contexte commercial ;
* associer un produit à une vente ;
* retrouver le produit à l'origine d'un équipement installé.

Le catalogue ne représente pas les équipements physiques présents chez les clients.

La distinction fondamentale est :

```text
Produit catalogue
    │
    │ vendu
    ▼
Ligne de vente
    │
    │ installé
    ▼
Installation
    │
    ▼
Équipement physique
```

Un même produit peut donc être vendu et installé chez plusieurs clients.

---

# 2. Périmètre

## 2.1 Inclus en V1

Le module gère :

* références produits ;
* nom ;
* marque ;
* catégorie ;
* description ;
* état actif/inactif ;
* recherche ;
* filtrage ;
* consultation du produit ;
* utilisation dans les ventes ;
* utilisation dans le showroom ;
* rattachement indirect aux équipements installés.

---

## 2.2 Hors périmètre V1

Le module ne gère pas encore :

* stock physique ;
* mouvements de stock ;
* inventaires ;
* commandes fournisseurs ;
* réapprovisionnement ;
* prix d'achat ;
* marges avancées ;
* gestion complète des fournisseurs ;
* facturation ;
* paiement ;
* comptabilité.

Ces fonctionnalités pourront être ajoutées ultérieurement sans remettre en cause le concept de produit.

---

# 3. Modèle métier

Le produit représente une **référence commerciale**.

```text
Product
├── référence
├── nom
├── marque
├── catégorie
├── description
└── actif
```

Il ne contient pas les informations propres à une installation particulière.

Par exemple :

```text
Produit
└── Daikin Perfera 3,5 kW
```

peut donner :

```text
Équipement #001
Client : Dupont
Site : Massy
N° série : ...
Installé : 2026-09-10

Équipement #002
Client : Martin
Site : Palaiseau
N° série : ...
Installé : 2026-09-15
```

Les deux équipements référencent le même produit catalogue.

---

# 4. Relations

Le chemin métier principal est :

```text
Product
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

Relations principales :

```text
Product 1 ─── N SaleLine

Sale 1 ─── N SaleLine

SaleLine 1 ─── N Installation

Installation 1 ─── 0..1 Equipment

Product 1 ─── N Equipment
```

La relation directe `Product → Equipment` permet une consultation simple du parc installé.

La relation `Equipment → Installation → SaleLine → Product` conserve également la provenance commerciale.

---

# 5. Données produit

Le modèle V1 est volontairement minimal.

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

### `reference`

Référence commerciale ou interne du produit.

Exemple :

```text
DAI-FTXM35R
```

La référence doit être suffisamment stable pour identifier le produit.

### `name`

Nom commercial affiché dans l'application.

Exemple :

```text
Daikin Perfera 3,5 kW
```

### `brand`

Marque du produit.

Exemple :

```text
Daikin
```

### `category`

Catégorie fonctionnelle.

Exemples :

```text
Climatisation
Pompe à chaleur
Chauffage
Ventilation
Accessoire
```

La liste exacte des catégories pourra évoluer.

### `active`

Indique si le produit peut encore être utilisé dans les nouvelles opérations commerciales.

Un produit désactivé reste conservé pour préserver l'historique.

---

# 6. Cycle de vie

Un produit suit un cycle simple :

```text
ACTIF
  │
  │ désactivation
  ▼
INACTIF
```

La désactivation est préférable à la suppression physique.

Exemple :

```text
Product
reference = DAI-FTXM35R
active = false
```

Les anciennes ventes et les anciens équipements continuent de référencer ce produit.

---

# 7. Création d'un produit

La création nécessite au minimum :

```text
Référence
Nom
```

Les autres informations peuvent être renseignées selon les besoins.

Exemple :

```json
{
  "reference": "DAI-FTXM35R",
  "name": "Daikin Perfera 3,5 kW",
  "brand": "Daikin",
  "category": "Climatisation",
  "description": "Unité intérieure murale 3,5 kW"
}
```

Le backend vérifie notamment :

* format des champs ;
* longueur ;
* cohérence des valeurs ;
* unicité de la référence si cette règle est retenue ;
* droits de l'utilisateur.

---

# 8. Modification

Les informations descriptives peuvent être modifiées tant que cela ne détruit pas l'historique métier.

Exemple :

```text
description
brand
category
name
```

Une modification du catalogue ne doit cependant pas réécrire les informations historiques propres à une vente ou à un équipement.

Exemple :

```text
Product
name = "Modèle X"
```

puis :

```text
name = "Modèle X nouvelle génération"
```

ne doit pas modifier rétroactivement les rapports d'intervention déjà produits.

---

# 9. Désactivation

Un produit utilisé historiquement ne doit pas être supprimé simplement parce qu'il n'est plus commercialisé.

Action :

```http
POST /api/v1/products/{id}/deactivate
```

Résultat :

```text
active = false
```

Le produit :

* reste consultable ;
* reste visible dans l'historique ;
* reste associé aux équipements existants ;
* ne doit plus être proposé par défaut pour une nouvelle vente.

---

# 10. Recherche et filtrage

La liste catalogue doit permettre au minimum :

```text
Recherche
├── référence
├── nom
└── marque

Filtres
├── catégorie
└── actif/inactif
```

Exemple :

```http
GET /api/v1/products?search=daikin&category=Climatisation&active=true
```

La pagination doit être utilisée lorsque le volume de produits augmente.

---

# 11. Consultation d'un produit

La fiche produit doit permettre de consulter :

```text
Produit
├── informations générales
├── statut
├── ventes associées
├── équipements installés
└── éventuellement utilisation showroom
```

La consultation des équipements doit respecter les règles d'autorisation définies dans le modèle de sécurité.

---

# 12. Produit et vente

Un produit ne doit pas être directement lié à une vente.

La relation passe par `SaleLine`.

```text
Sale
│
├── SaleLine
│      ├── Product A
│      └── quantity = 2
│
└── SaleLine
       ├── Product B
       └── quantity = 1
```

Cela permet une vente contenant plusieurs produits.

Exemple :

```text
Vente #2026-0042

1 × Daikin Perfera 3,5 kW
1 × Kit Wi-Fi
2 × Support mural
```

Chaque ligne conserve son produit et sa quantité.

---

# 13. Quantité et équipements physiques

Une ligne de vente peut représenter plusieurs unités :

```text
SaleLine
product = Daikin Perfera 3,5 kW
quantity = 3
```

Les équipements physiques doivent néanmoins être individualisés.

Le modèle cible est donc :

```text
SaleLine
   │
   ├── Installation #1
   │       └── Equipment #1
   │
   ├── Installation #2
   │       └── Equipment #2
   │
   └── Installation #3
           └── Equipment #3
```

Cela permet de conserver pour chaque appareil :

* numéro de série ;
* date d'installation ;
* garantie ;
* historique ;
* interventions ;
* remplacement éventuel.

---

# 14. Produit et équipement

Le produit décrit **ce qui est commercialisé**.

L'équipement décrit **ce qui existe physiquement chez le client**.

### Produit

```text
Daikin Perfera 3,5 kW
Référence : DAI-FTXM35R
```

### Équipement

```text
Équipement #842

Produit : Daikin Perfera 3,5 kW
Client : Dupont
Site : Massy
N° série : SN123456789
Installé le : 2026-09-10
Garantie jusqu'au : 2030-09-10
```

Les données spécifiques à l'équipement ne doivent pas être ajoutées au produit.

---

# 15. Produit et showroom

Le showroom peut présenter des produits issus du catalogue.

```text
Product
    │
    ▼
ShowroomVisitProduct
    │
    ▼
ShowroomVisit
```

Le fait qu'un produit ait été présenté ne signifie pas qu'il a été vendu.

```text
Produit présenté
       ≠
Produit vendu
       ≠
Produit installé
       ≠
Équipement physique
```

Cette distinction doit être conservée dans le modèle métier.

---

# 16. Produit et intervention

Une intervention ne référence normalement pas directement un produit.

Elle référence un équipement :

```text
Intervention
      │
      ▼
Equipment
      │
      ▼
Product
```

Exemple :

```text
Intervention
"Recherche de panne"

   ↓

Équipement
"SN123456789"

   ↓

Produit
"Daikin Perfera 3,5 kW"
```

Cela permet de connaître le modèle concerné sans perdre l'identité physique de l'appareil.

---

# 17. Historique

Le catalogue doit préserver l'historique métier.

Un produit désactivé peut continuer à être référencé par :

* une vente ;
* une installation ;
* un équipement ;
* une intervention ;
* un rapport ;
* une visite showroom.

Il ne doit donc pas être supprimé physiquement si des données métier le référencent.

---

# 18. API cible

## Produits

```http
GET    /api/v1/products
POST   /api/v1/products
GET    /api/v1/products/{id}
PATCH  /api/v1/products/{id}
POST   /api/v1/products/{id}/deactivate
```

## Utilisation

Les autres domaines consomment le catalogue via leurs propres ressources :

```http
GET /api/v1/sales/{id}
GET /api/v1/equipment/{id}
GET /api/v1/showroom/visits/{id}
```

Le frontend ne doit pas reconstruire lui-même les relations métier à partir de plusieurs appels inutiles lorsque l'API peut fournir une vue adaptée.

---

# 19. Règles métier

### R1 — Une référence identifie un produit

La référence doit être contrôlée selon la politique d'unicité retenue.

### R2 — Un produit peut être utilisé plusieurs fois

Un produit peut apparaître dans plusieurs ventes et produire plusieurs équipements.

### R3 — Un équipement est individuel

Chaque équipement physique possède son propre historique.

### R4 — La suppression physique est évitée

La désactivation est utilisée lorsqu'un produit n'est plus commercialisé.

### R5 — Le catalogue ne gère pas le stock V1

L'existence d'un produit dans le catalogue ne signifie pas qu'il est disponible physiquement.

### R6 — Une intervention passe par l'équipement

Lorsqu'un équipement est identifié, l'intervention référence l'équipement et non simplement le produit.

### R7 — Les historiques ne sont pas réécrits

Une modification du catalogue ne doit pas altérer les documents ou événements historiques.

---

# 20. Cas métier complet

Exemple réel :

```text
1. Création du produit
   │
   ▼
Daikin Perfera 3,5 kW
DAI-FTXM35R
   │
   ▼
2. Vente
   │
   ▼
Vente #2026-0042
   │
   ▼
3. Ligne de vente
   │
   ▼
1 × DAI-FTXM35R
   │
   ▼
4. Installation
   │
   ▼
Installation du 10/09/2026
   │
   ▼
5. Équipement
   │
   ├── SN123456789
   ├── Site : Massy
   ├── Garantie
   └── Historique
          │
          ▼
6. Intervention
   │
   ├── diagnostic
   ├── checklist
   ├── photos
   ├── matériel
   └── rapport
```

Le catalogue est donc le **point de référence produit**, mais le cœur de l'historique technique reste l'équipement.

---

# 21. Évolution future

Le module pourra évoluer vers :

```text
Catalogue
├── Produits
├── Variantes
├── Caractéristiques techniques
├── Documents produits
├── Tarification
├── Prix d'achat
├── Fournisseurs
└── Stock
```

Ces extensions ne doivent être introduites que lorsque le besoin métier est confirmé.

Le modèle V1 doit rester suffisamment simple pour permettre de construire rapidement :

```text
Produit
    ↓
Vente
    ↓
Installation
    ↓
Équipement
```

---

# 22. Critères d'acceptation

Le module Catalogue est considéré comme fonctionnel lorsque :

* un utilisateur autorisé peut créer un produit ;
* une référence peut être recherchée ;
* un produit peut être modifié ;
* un produit peut être désactivé ;
* un produit désactivé reste visible dans l'historique ;
* un produit peut être ajouté à une vente ;
* une ligne de vente peut avoir une quantité supérieure à 1 ;
* plusieurs équipements peuvent provenir d'une même ligne de vente ;
* chaque équipement conserve son identité propre ;
* une intervention peut retrouver le produit via son équipement ;
* le catalogue ne prétend pas gérer le stock ;
* les suppressions ne détruisent pas l'historique métier.

---

# 23. Principe du module

> **Le catalogue décrit ce que Tervo vend. Il ne décrit pas ce qui est physiquement installé chez le client.**

La séparation :

```text
Produit
   ↓
Vente
   ↓
Installation
   ↓
Équipement
   ↓
Interventions
```

est fondamentale pour conserver un historique technique fiable.
