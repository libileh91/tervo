# Tervo — Module Showroom

## 1. Objectif

Le module Showroom permet de suivre les interactions commerciales autour des produits présentés ou étudiés par un client ou un prospect.

Il permet de :

* enregistrer une visite ;
* identifier le visiteur ;
* enregistrer les produits présentés ;
* noter les besoins ou observations ;
* suivre l'état du suivi commercial ;
* rattacher la visite à une vente lorsqu'elle aboutit.

Le showroom constitue donc le point d'entrée commercial du parcours :

```text
Visite
   ↓
Produits présentés
   ↓
Suivi commercial
   ↓
Devis éventuel
   ↓
Vente
   ↓
Installation
   ↓
Équipement
```

Le module ne cherche pas à devenir un CRM complet en V1.

---

# 2. Périmètre

## 2.1 Inclus en V1

Le module gère :

* visites showroom ;
* client ou prospect associé ;
* nom du visiteur ;
* date et heure ;
* commercial responsable ;
* produits présentés ;
* notes ;
* statut de suivi ;
* consultation de l'historique des visites.

---

## 2.2 Hors périmètre V1

Ne sont pas nécessaires dans le module showroom V1 :

* CRM complet ;
* campagnes marketing ;
* emailing massif ;
* scoring de prospects ;
* pipeline commercial complexe ;
* facturation ;
* paiement ;
* gestion comptable ;
* gestion avancée des devis ;
* signature électronique.

Un futur module commercial pourra prendre en charge ces besoins.

---

# 3. Client ou prospect

Le parcours showroom peut commencer avec une personne qui n'est pas encore un client.

Le modèle doit donc distinguer :

```text id="0z4q6v"
Visiteur
   │
   ├── client existant
   │
   └── prospect
```

Le système ne doit pas obliger à créer artificiellement un client complet simplement pour enregistrer une visite.

### Principe recommandé

Une visite peut contenir :

* `client_id` lorsque la personne est déjà connue ;
* les informations minimales du visiteur lorsque le prospect n'existe pas encore comme client.

Exemple :

```text id="m1d8su"
ShowroomVisit
├── client_id = null
├── visitor_name = "Jean Dupont"
├── visited_at
└── notes
```

Lorsque le prospect devient réellement un client, la visite peut ensuite être rattachée au client.

---

# 4. Modèle métier

Une visite showroom représente un **événement commercial**.

```text id="g8d7x2"
ShowroomVisit
├── visiteur
├── date
├── commercial
├── produits présentés
├── statut de suivi
└── notes
```

Une visite n'est pas une vente.

```text id="8y7ncr"
Visite
   ≠
Vente
```

Une personne peut :

* visiter le showroom sans acheter ;
* revenir plusieurs fois ;
* demander un devis ;
* acheter plusieurs jours plus tard ;
* ne jamais donner suite.

L'historique doit conserver ces événements.

---

# 5. Visite showroom

## 5.1 Données principales

```text id="b9r7vh"
ShowroomVisit
├── id
├── client_id nullable
├── visitor_name
├── visited_at
├── salesperson_id
├── follow_up_status
├── notes
└── created_at
```

Les informations pourront être enrichies ultérieurement si le besoin est confirmé.

---

# 6. Produits présentés

Une visite peut concerner plusieurs produits.

La relation passe par :

```text id="zj2a8v"
ShowroomVisit
      │
      └── ShowroomVisitProduct
                 │
                 └── Product
```

Exemple :

```text id="j6k1do"
Visite du 21/09/2026

Produits présentés :
├── Daikin Perfera 3,5 kW
├── Pompe à chaleur Air/Eau
└── Thermostat connecté
```

Le fait qu'un produit soit présenté ne signifie pas qu'il sera vendu.

---

# 7. Statut de suivi

Le suivi doit être représenté par un état explicite plutôt qu'un simple booléen.

Le modèle V1 peut utiliser :

```text id="9yqzbf"
TO_FOLLOW_UP
CONSIDERING
QUOTE_REQUESTED
QUOTE_SENT
SOLD
LOST
NO_FURTHER_ACTION
```

### Signification

| Statut              | Signification                       |
| ------------------- | ----------------------------------- |
| `TO_FOLLOW_UP`      | Une action commerciale est attendue |
| `CONSIDERING`       | Le prospect/client réfléchit        |
| `QUOTE_REQUESTED`   | Une demande de devis a été formulée |
| `QUOTE_SENT`        | Un devis a été envoyé               |
| `SOLD`              | Une vente a été réalisée            |
| `LOST`              | L'opportunité n'a pas abouti        |
| `NO_FURTHER_ACTION` | Aucun suivi supplémentaire prévu    |

Le statut décrit le **suivi commercial de la visite**, pas l'état d'une vente.

---

# 8. Pourquoi ne pas utiliser `suite_donnee`

Un champ :

```text
suite_donnee = true
```

ne permet pas de représenter correctement le parcours.

Il ne distingue pas :

```text
à relancer
réflexion
devis demandé
devis envoyé
vendu
perdu
aucune suite
```

Le statut explicite permet également d'ajouter de nouveaux états sans modifier le concept métier.

---

# 9. Création d'une visite

La création peut être réalisée depuis :

* l'écran showroom ;
* la fiche client ;
* éventuellement une fiche prospect.

Exemple :

```json id="8a1jtc"
{
  "visitor_name": "Jean Dupont",
  "visited_at": "2026-09-21T14:30:00",
  "salesperson_id": 12,
  "notes": "Recherche une climatisation pour un appartement de 70 m²"
}
```

Le système peut ensuite associer les produits présentés.

---

# 10. Ajout des produits présentés

Exemple :

```http id="1h4w87"
POST /api/v1/showroom/visits/{visit_id}/products
```

Payload :

```json id="m8n8bw"
{
  "product_id": 42
}
```

Une même visite ne doit pas enregistrer plusieurs fois le même produit.

---

# 11. Suivi commercial

Le suivi peut évoluer :

```text id="x1gk6u"
TO_FOLLOW_UP
      ↓
CONSIDERING
      ↓
QUOTE_REQUESTED
      ↓
QUOTE_SENT
      ↓
SOLD
```

Mais tous les parcours ne suivent pas nécessairement cette séquence.

Exemple :

```text id="x7h8br"
TO_FOLLOW_UP
      ↓
NO_FURTHER_ACTION
```

ou :

```text id="y6pr4c"
CONSIDERING
      ↓
LOST
```

Le système doit donc contrôler les transitions pertinentes sans imposer un workflow commercial artificiellement rigide en V1.

---

# 12. Visite et devis

Le devis est une étape commerciale distincte.

```text id="3s6f2k"
Visite
   ↓
Demande de devis
   ↓
Devis
   ↓
Acceptation
   ↓
Vente
```

Le module showroom n'a pas besoin de gérer l'intégralité du devis en V1.

Le statut :

```text
QUOTE_REQUESTED
QUOTE_SENT
```

permet néanmoins de suivre le parcours commercial.

Un futur module `commercial` pourra introduire une véritable entité :

```text
Quote
```

sans remettre en cause `ShowroomVisit`.

---

# 13. Visite et vente

Une vente est un événement distinct.

```text id="y1j4bp"
ShowroomVisit
       │
       │ peut aboutir à
       ▼
Sale
```

Il n'est pas nécessaire de mettre un `sale_id` directement dans `ShowroomVisit` en V1 si la relation peut être retrouvée par le client et l'historique commercial.

Si une traçabilité directe devient nécessaire, elle pourra être ajoutée ultérieurement.

---

# 14. Parcours complet

Exemple :

```text id="l5s1n8"
1. Jean Dupont visite le showroom
        │
        ▼
2. Visite enregistrée
        │
        ├── Perfera 3,5 kW
        └── Thermostat connecté
        │
        ▼
3. Statut = TO_FOLLOW_UP
        │
        ▼
4. Client demande un devis
        │
        ▼
5. Statut = QUOTE_REQUESTED
        │
        ▼
6. Devis envoyé
        │
        ▼
7. Statut = QUOTE_SENT
        │
        ▼
8. Vente confirmée
        │
        ▼
9. Statut = SOLD
        │
        ▼
10. Installation
        │
        ▼
11. Équipement
```

Le showroom constitue donc une **origine commerciale possible** du parcours matériel.

---

# 15. Plusieurs visites

Un même client peut avoir plusieurs visites.

```text id="9o8m4n"
Client
  │
  ├── Visite #1
  │
  ├── Visite #2
  │
  └── Visite #3
```

Chaque visite conserve son propre contexte.

Exemple :

```text id="9tq0uk"
Visite #1
"Découverte des solutions"

Visite #2
"Comparaison PAC air/eau"

Visite #3
"Validation du modèle"
```

Il ne faut donc pas stocker uniquement le dernier statut ou la dernière visite sur le client.

---

# 16. Historique

La fiche client peut afficher :

```text id="z5j6jq"
Historique commercial
├── Visites showroom
├── Produits présentés
├── Suivis
├── Ventes
└── Installations
```

Le showroom conserve les événements commerciaux.

Les données techniques restent dans les domaines :

```text id="d7kj8k"
Installation
Equipment
Intervention
Report
```

---

# 17. Autorisations

Les droits suivent le modèle général Tervo.

### Commercial

Peut notamment :

* créer une visite ;
* consulter les visites ;
* modifier les informations commerciales ;
* ajouter des produits ;
* modifier le suivi.

### Manager

Peut :

* consulter les visites ;
* superviser les suivis ;
* modifier les données selon ses droits ;
* consulter l'activité commerciale.

### Technicien

Le showroom n'est pas son domaine principal.

L'accès doit rester limité aux informations nécessaires à son activité.

### Admin

Accès complet selon les règles générales de sécurité.

---

# 18. API cible

## Visites

```http
GET    /api/v1/showroom/visits
POST   /api/v1/showroom/visits
GET    /api/v1/showroom/visits/{id}
PATCH  /api/v1/showroom/visits/{id}
```

## Produits présentés

```http
POST   /api/v1/showroom/visits/{id}/products
DELETE /api/v1/showroom/visits/{id}/products/{product_id}
```

## Suivi

Le suivi peut être modifié via :

```http
PATCH /api/v1/showroom/visits/{id}
```

avec validation métier du nouveau statut.

Exemple :

```json id="8r1o0x"
{
  "follow_up_status": "QUOTE_SENT"
}
```

---

# 19. Recherche et filtres

La liste des visites doit permettre de filtrer notamment par :

```text id="g1v9fk"
Client
Commercial
Date
Statut de suivi
Produit
```

Exemple :

```http id="j6a5od"
GET /api/v1/showroom/visits?follow_up_status=TO_FOLLOW_UP
```

Un écran manager peut ainsi identifier les visites nécessitant une action.

---

# 20. Règles métier

### R1 — Une visite est un événement

Une visite ne doit pas être écrasée par une visite ultérieure.

### R2 — Une visite peut présenter plusieurs produits

La relation passe par `ShowroomVisitProduct`.

### R3 — Produit présenté ≠ produit vendu

Une présentation ne constitue pas une vente.

### R4 — Visite ≠ devis

Le devis est une étape commerciale distincte.

### R5 — Devis ≠ vente

L'envoi d'un devis ne signifie pas que la vente est réalisée.

### R6 — Vente ≠ installation

Une vente peut précéder l'installation.

### R7 — Installation ≠ équipement

L'installation est l'événement ; l'équipement est l'objet physique résultant.

### R8 — L'historique est conservé

Les visites ne doivent pas être supprimées simplement parce qu'elles n'ont pas abouti.

---

# 21. Cas particulier : prospect

Exemple :

```text id="v4q7u2"
Une personne arrive au showroom.

Nom : Sarah Martin
Téléphone : ...
Email : ...

Aucun Client existant.
```

Tervo doit pouvoir enregistrer :

```text
ShowroomVisit
├── client_id = null
├── visitor_name = Sarah Martin
└── ...
```

Si la personne devient cliente :

```text
Prospect
   ↓
Client
   ↓
Site
   ↓
Vente
   ↓
Installation
```

La visite historique doit rester accessible.

---

# 22. Ce que le showroom ne doit pas faire

Le module ne doit pas devenir un endroit où l'on mélange :

```text
Produit
Client
Prospect
Devis
Vente
Installation
Équipement
```

Chaque concept conserve son rôle.

Le showroom orchestre uniquement la partie :

```text
Interaction commerciale
        ↓
Suivi
        ↓
Orientation vers le processus commercial
```

---

# 23. Évolution future

Si l'activité commerciale devient plus importante, un module dédié pourra introduire :

```text
Commercial
├── Prospect
├── Opportunity
├── Quote
├── QuoteLine
├── Sale
└── SalesActivity
```

Le showroom pourra alors devenir une source d'opportunités commerciales.

Exemple :

```text
ShowroomVisit
      ↓
Opportunity
      ↓
Quote
      ↓
Sale
      ↓
Installation
      ↓
Equipment
```

Cette évolution ne doit pas être anticipée dans le modèle V1 tant que le besoin n'est pas confirmé.

---

# 24. Critères d'acceptation

Le module Showroom est considéré comme fonctionnel lorsque :

* une visite peut être enregistrée ;
* une visite peut être liée à un client existant ;
* une visite peut également être enregistrée pour un prospect ;
* plusieurs produits peuvent être associés à une visite ;
* un même produit ne peut pas être ajouté deux fois à la même visite ;
* le statut de suivi peut être modifié ;
* les différents états de suivi sont distingués ;
* les visites historiques restent consultables ;
* une visite n'est pas considérée automatiquement comme une vente ;
* une vente reste distincte de l'installation ;
* une installation reste distincte de l'équipement ;
* les droits d'accès respectent les rôles ;
* les données commerciales ne contaminent pas l'historique technique.

---

# 25. Principe du module

> **Le showroom enregistre ce qui s'est passé commercialement avant la vente ; il ne devient pas lui-même la vente.**

Le parcours cible est :

```text
Showroom
   ↓
Visite
   ↓
Produits présentés
   ↓
Suivi commercial
   ↓
Devis éventuel
   ↓
Vente
   ↓
Installation
   ↓
Équipement
   ↓
Interventions
```

La séparation entre ces étapes permet à Tervo de conserver un historique cohérent aussi bien pour le commercial que pour le technique.
