# Tervo — Module Interventions

## 1. Objectif

Le module Interventions constitue le cœur opérationnel de Tervo.

Il permet de gérer le cycle de vie d'une intervention technique :

```text id="3j6m4w"
Équipement
    │
    ▼
Intervention
    │
    ├── Techniciens
    ├── Checklist
    ├── Photos
    ├── Matériel utilisé
    ├── Observations
    ├── Résultat
    ├── Rapport
    └── Avis
```

Le module doit permettre à un technicien de répondre à une question simple :

> **Qu'est-ce qui a été fait, sur quel équipement, avec quel résultat, et quelles preuves ont été produites ?**

---

# 2. Périmètre

## 2.1 Inclus en V1

Le module gère :

* création d'interventions ;
* planification ;
* affectation des techniciens ;
* démarrage ;
* exécution ;
* checklists ;
* photos ;
* matériel utilisé ;
* observations ;
* résultat ;
* clôture ;
* rapport ;
* avis client ;
* historique technique de l'équipement ;
* interventions de maintenance ;
* dépannage ;
* diagnostic ;
* SAV ;
* installation et mise en service.

---

## 2.2 Hors périmètre V1

Ne sont pas nécessaires au premier périmètre :

* planning avancé avec optimisation automatique des tournées ;
* GPS temps réel ;
* gestion complète des contrats de maintenance ;
* gestion complète des pièces de stock ;
* achats fournisseurs ;
* facturation ;
* comptabilité ;
* dispatching automatique ;
* maintenance prédictive ;
* moteur de recommandation.

Ces fonctionnalités pourront consommer le module Interventions ultérieurement.

---

# 3. Principe central

Une intervention représente une **action technique réalisée ou planifiée**.

Elle ne représente pas l'équipement lui-même.

```text id="k0g2hr"
Equipment
    │
    ├── Intervention #1
    ├── Intervention #2
    ├── Intervention #3
    └── Intervention #4
```

Un équipement peut donc avoir un historique d'interventions important.

Inversement :

```text id="y2x6j4"
Intervention
    │
    └── Equipment
```

permet de savoir exactement sur quel équipement l'action a porté.

---

# 4. Intervention sans équipement identifié

Toutes les interventions ne permettent pas immédiatement d'identifier un équipement.

Exemple :

> Le client signale une panne de climatisation mais ne connaît ni le modèle ni le numéro de série.

Tervo peut alors créer :

```text id="8q1h1p"
Intervention
├── site_id = 42
└── equipment_id = null
```

Le technicien peut identifier l'équipement sur place.

Après identification :

```text id="7d0ykr"
Intervention
├── site_id = 42
└── equipment_id = 137
```

Une intervention rattachée à un équipement doit respecter :

```text id="l2j8sd"
Equipment.site_id == Intervention.site_id
```

Cette règle est obligatoire pour préserver la cohérence métier.

---

# 5. Types d'intervention

Les types V1 sont :

```text id="e5w0hl"
INSTALLATION
COMMISSIONING
PREVENTIVE_MAINTENANCE
CORRECTIVE_MAINTENANCE
TROUBLESHOOTING
DIAGNOSTIC
SAV
OTHER
```

### Installation

Pose physique d'un équipement.

### Mise en service

Mise en fonctionnement et vérification de l'installation.

### Maintenance préventive

Opération planifiée destinée à maintenir l'équipement en état.

### Maintenance corrective

Intervention destinée à corriger une anomalie identifiée.

### Dépannage

Intervention visant à rétablir le fonctionnement d'un équipement en panne.

### Diagnostic

Recherche de la cause d'un dysfonctionnement.

### SAV

Intervention réalisée dans le cadre du service après-vente.

### Autre

Cas ne correspondant pas aux catégories précédentes.

---

# 6. Type d'intervention ≠ résultat

Le type décrit :

> **Pourquoi / dans quel contexte l'intervention est réalisée.**

Le résultat décrit :

> **Ce qui s'est passé à la fin.**

Exemple :

```text id="jz1tgd"
Type :
TROUBLESHOOTING

Résultat :
PART_REQUIRED
```

Cela signifie :

> Une intervention de dépannage a été réalisée, mais une pièce est nécessaire avant résolution complète.

Il ne faut donc pas utiliser le type comme résultat.

---

# 7. Statut de l'intervention

Le statut décrit l'état du workflow :

```text id="q2f1ob"
PLANNED
   │
   ▼
IN_PROGRESS
   │
   ▼
COMPLETED
```

Une intervention peut également être :

```text id="ps8v48"
PLANNED
   │
   ▼
CANCELLED
```

Les statuts V1 sont :

```text id="zqf4m0"
PLANNED
IN_PROGRESS
COMPLETED
CANCELLED
```

---

# 8. Résultat de l'intervention

Le résultat est renseigné lorsque l'intervention est suffisamment avancée pour être qualifiée.

Valeurs V1 :

```text id="d8vqz8"
RESOLVED
PARTIALLY_RESOLVED
UNRESOLVED
PART_REQUIRED
QUOTE_REQUIRED
FOLLOW_UP_REQUIRED
```

Exemple :

```text id="2gk9bv"
status = COMPLETED
result = PARTIALLY_RESOLVED
```

Le statut `COMPLETED` signifie que l'intervention elle-même est terminée.

Il ne signifie pas nécessairement que le problème initial est totalement résolu.

---

# 9. Cycle de vie

## 9.1 Création

Une intervention est créée avec au minimum :

```text id="b4u8jq"
site_id
type
```

L'équipement est recommandé mais peut être absent lors d'un diagnostic initial.

---

## 9.2 Planification

Une intervention planifiée peut recevoir :

```text id="l9f5pg"
scheduled_start
scheduled_end
```

Elle peut également être affectée à un ou plusieurs techniciens.

---

## 9.3 Démarrage

Action :

```http id="p1x8r4"
POST /api/v1/interventions/{id}/start
```

Le système :

* vérifie les droits ;
* vérifie l'état actuel ;
* enregistre `started_at` ;
* passe le statut à `IN_PROGRESS`.

---

## 9.4 Exécution

Pendant l'intervention, le technicien peut :

* consulter la checklist ;
* renseigner les résultats ;
* ajouter des observations ;
* prendre des photos ;
* ajouter le matériel utilisé ;
* compléter les informations techniques ;
* identifier l'équipement si nécessaire.

---

## 9.5 Clôture

Action :

```http id="n3q4n4"
POST /api/v1/interventions/{id}/complete
```

Le backend vérifie notamment :

* que l'intervention est en cours ;
* que les informations obligatoires sont présentes ;
* que les règles de checklist applicables sont respectées ;
* qu'un résultat est renseigné lorsque requis.

Puis :

```text id="bd4k1v"
status = COMPLETED
completed_at = maintenant
```

---

# 10. Affectation des techniciens

Une intervention peut impliquer plusieurs techniciens.

Relation :

```text id="r5z9c8"
Intervention
      │
      └── InterventionTechnician
                │
                ├── User
                └── role
```

Exemple :

```text id="u7q7jz"
Intervention #1054

Technicien principal :
    Mohamed

Technicien :
    Paul
```

Le champ `role` permet de distinguer les responsabilités lorsque nécessaire.

---

# 11. Checklist

Les checklists permettent de standardiser l'exécution.

Il faut distinguer :

```text id="4o3u5j"
ChecklistTemplate
        │
        │ instanciation
        ▼
InterventionChecklist
        │
        ▼
ChecklistItem
```

Le template est réutilisable.

La checklist de l'intervention est historique.

---

# 12. Template de checklist

Exemple :

```text id="m0x7xg"
Template :
Maintenance préventive — climatisation

Version :
3
```

Items :

```text id="c2o7a7"
1. Vérifier l'état général
2. Contrôler les filtres
3. Vérifier les condensats
4. Contrôler les connexions
5. Mesurer les températures
6. Vérifier le fonctionnement
```

Le template peut évoluer.

---

# 13. Snapshot de checklist

Lorsqu'une intervention utilise un template, les éléments nécessaires doivent être copiés dans l'instance historique.

Exemple :

```text id="4d2q1v"
Template v3
    │
    ▼
Intervention #1054
    │
    └── Checklist v3
```

Si le template devient ensuite :

```text id="x2z4n9"
Template v4
```

l'intervention #1054 continue de conserver sa checklist v3.

Une modification future du template ne doit pas modifier rétroactivement une intervention terminée.

---

# 14. Résultat d'une checklist

Chaque item peut avoir un résultat et éventuellement un commentaire.

Exemple :

```text id="x1p8w2"
☑ Filtres contrôlés
☑ Condensats contrôlés
☑ Température relevée

☑ Connexions contrôlées
  Commentaire :
  "Serrage légèrement repris."

☐ Fonctionnement
```

Le modèle peut évoluer vers des résultats plus riches, mais V1 doit rester simple.

---

# 15. Photos

Les photos appartiennent à une intervention.

```text id="q5f7n2"
Intervention
    │
    ├── Photo
    ├── Photo
    └── Photo
```

Catégories V1 :

```text id="1f6l0c"
BEFORE
AFTER
EQUIPMENT
ANOMALY
PART
OTHER
```

Exemple :

```text id="h2f3d1"
Photo
├── category = ANOMALY
├── filename = IMG_20260921.jpg
└── captured_at = ...
```

---

# 16. Photos et historique

Une photo ne doit pas être remplacée silencieusement.

Elle constitue une preuve associée à l'intervention.

Les métadonnées doivent rester disponibles :

* intervention ;
* catégorie ;
* date ;
* nom original ;
* stockage ;
* type MIME ;
* taille.

La suppression d'une photo historique doit être contrôlée et, si nécessaire, auditée.

---

# 17. Matériel utilisé

V1 utilise un modèle volontairement simple :

```text id="1q3h0j"
MaterialUsage
├── designation
├── quantity
└── unit
```

Exemple :

```text id="4s2f5x"
1 × filtre
2 × raccord cuivre
0.5 × mètre de câble
```

La référence catalogue n'est pas obligatoire en V1.

---

# 18. Évolution du matériel

Plus tard, `MaterialUsage` pourra être relié au catalogue ou au stock :

```text id="i0n9jg"
MaterialUsage
       │
       └── Product
               │
               └── Stock
```

Cela permettra éventuellement de déduire les consommations de stock.

Mais le module Interventions V1 ne doit pas dépendre du futur module Stock.

---

# 19. Observations

L'intervention doit permettre de conserver des informations libres structurées autour de l'exécution.

Exemples :

```text id="e5o8aq"
description
observations
```

Exemple :

> Unité extérieure accessible depuis la terrasse. Filtre fortement encrassé. Température de soufflage conforme après nettoyage.

Ces informations alimentent notamment le rapport.

---

# 20. Résultat et suite à donner

Une intervention peut se terminer avec une action complémentaire.

Exemple :

```text id="x9m5gd"
status = COMPLETED
result = PART_REQUIRED
```

Cela signifie :

```text id="3j8xk7"
Intervention terminée
        │
        ▼
Pièce nécessaire
        │
        ▼
Nouvelle action future
```

Autre exemple :

```text id="5k8r3f"
result = QUOTE_REQUIRED
```

L'intervention est terminée mais une proposition commerciale est nécessaire.

---

# 21. Dépannage

Workflow type :

```text id="4j5c7r"
Client signale une panne
        │
        ▼
Intervention TROUBLESHOOTING
        │
        ▼
Diagnostic
        │
        ├── panne résolue
        │       ↓
        │    RESOLVED
        │
        ├── pièce nécessaire
        │       ↓
        │    PART_REQUIRED
        │
        └── devis nécessaire
                ↓
            QUOTE_REQUIRED
```

Le diagnostic peut commencer sans équipement identifié.

Une fois l'équipement identifié, celui-ci doit être rattaché à l'intervention.

---

# 22. Maintenance préventive

Exemple :

```text id="6h3f5m"
Equipment
    │
    ▼
Intervention
type = PREVENTIVE_MAINTENANCE
    │
    ├── Checklist
    ├── Photos
    ├── Matériel
    └── Rapport
```

La checklist utilisée dépend du type d'intervention et du template actif au moment de la création.

---

# 23. SAV et garantie

Le SAV n'est pas un modèle technique complètement séparé en V1.

Il est représenté par :

```text id="b7k3sv"
Intervention
├── type = SAV
└── under_warranty: boolean
```

L'équipement concerné reste le point de rattachement.

La garantie appartient à l'équipement :

```text id="x5z9c1"
Equipment
├── warranty_start
└── warranty_end
```

Une intervention peut être qualifiée comme réalisée sous garantie lorsque cela est nécessaire au métier.

Il faut distinguer :

```text id="4n8p2v"
Équipement sous garantie
        ≠
Intervention automatiquement sous garantie
```

Le contexte de l'intervention doit déterminer si l'opération est effectivement traitée au titre de la garantie.

Le statut de garantie de l'intervention (`under_warranty`) est distinct des
dates de garantie de l'équipement. Il constitue une information historique
de l'intervention.

---

# 24. Installation

Une installation peut être représentée comme une intervention :

```text id="q7h4m1"
Intervention
type = INSTALLATION
```

Elle doit cependant rester liée à l'entité `Installation` du modèle commercial/technique lorsqu'elle provient d'une vente.

Cela permet de distinguer :

```text id="3r7b9m"
Installation commerciale
        │
        └── événement d'installation
                 │
                 ▼
          Équipement physique
```

et :

```text id="k1x6t4"
Intervention INSTALLATION
        │
        └── travail technique réalisé
```

Ces deux notions peuvent être liées sans être confondues.

---

# 25. Mise en service

Même principe pour :

```text id="2m8v5s"
Intervention
type = COMMISSIONING
```

La mise en service peut intervenir après l'installation physique.

Exemple :

```text id="4v6d9x"
Installation
    ↓
Equipment créé
    ↓
Intervention COMMISSIONING
    ↓
Equipment opérationnel
```

---

# 26. Rapport

Le rapport constitue la restitution de l'intervention.

Il est construit à partir de :

```text id="q0r3s9"
Intervention
├── client
├── site
├── equipment
├── techniciens
├── dates
├── type
├── résultat
├── checklist
├── photos
├── matériel
└── observations
```

Le rapport peut être généré en PDF.

---

# 27. Versionnement du rapport

Un rapport doit pouvoir évoluer sans perdre l'historique.

Exemple :

```text id="n7c1y8"
Rapport v1
    ↓
corrigé
    ↓
Rapport v2
```

Une version transmise au client doit rester identifiable.

Le système ne doit pas modifier silencieusement un document déjà transmis.

---

# 28. Génération du rapport

Action cible :

```http id="r4f1v7"
POST /api/v1/interventions/{id}/reports
```

Le backend :

1. vérifie l'accès à l'intervention ;
2. récupère les données nécessaires ;
3. génère le document ;
4. stocke le fichier ;
5. enregistre ses métadonnées ;
6. associe la version à l'intervention.

---

# 29. Avis client

Une intervention peut avoir :

```text id="z3p8v6"
0 ou 1 Review
```

Exemple :

```text id="j7n2w4"
Intervention #1054
        │
        └── Review
              ├── rating = 5
              └── comment = "Intervention rapide."
```

Une intervention sans avis reste parfaitement valide.

L'avis ne doit pas être obligatoire pour clôturer l'intervention.

---

# 30. Historique équipement

La fiche équipement doit permettre de retrouver les interventions :

```text id="q8s3w5"
Equipment
   │
   ├── Installation
   ├── Commissioning
   ├── Maintenance
   ├── Dépannage
   ├── Diagnostic
   └── SAV
```

L'historique constitue une vue métier construite à partir des événements existants.

Il n'est pas nécessaire de créer une table `EquipmentHistory` en V1.

---

# 31. Remplacement d'un équipement

Lorsqu'un équipement est remplacé, l'ancien équipement ne doit pas être supprimé.

```text id="w4m8j2"
Ancien équipement
      │
      │ replaced_by
      ▼
Nouvel équipement
```

L'ancien conserve :

* ses interventions ;
* ses rapports ;
* ses photos ;
* son numéro de série ;
* son historique de garantie ;
* ses informations d'installation.

Le nouvel équipement démarre son propre historique.

---

# 32. Permissions

Les règles générales d'autorisation s'appliquent.

### Technicien

Peut notamment :

* consulter ses interventions accessibles ;
* démarrer une intervention ;
* renseigner la checklist ;
* ajouter des photos ;
* ajouter du matériel ;
* renseigner les observations ;
* renseigner le résultat ;
* terminer l'intervention.

### Manager

Peut :

* consulter les interventions ;
* planifier ;
* affecter les techniciens ;
* modifier certaines données ;
* superviser les résultats ;
* consulter les rapports.

### Commercial

Accès limité aux informations nécessaires :

* état global ;
* résultats utiles au suivi commercial ;
* rapports lorsque nécessaire.

### Admin

Accès complet selon les règles générales.

---

# 33. API cible

## Interventions

```http id="l9y7c4"
GET    /api/v1/interventions
POST   /api/v1/interventions
GET    /api/v1/interventions/{id}
PATCH  /api/v1/interventions/{id}

POST   /api/v1/interventions/{id}/start
POST   /api/v1/interventions/{id}/complete
POST   /api/v1/interventions/{id}/cancel
```

## Techniciens

```http id="m2v5j8"
POST   /api/v1/interventions/{id}/technicians
DELETE /api/v1/interventions/{id}/technicians/{user_id}
```

## Checklist

```http id="n5c7k1"
GET   /api/v1/interventions/{id}/checklist
PATCH /api/v1/interventions/{id}/checklist/items/{item_id}
```

## Photos

```http id="s4h8x2"
GET  /api/v1/interventions/{id}/photos
POST /api/v1/interventions/{id}/photos
DELETE /api/v1/interventions/{id}/photos/{photo_id}
```

## Matériel

```http id="e6w3p9"
GET   /api/v1/interventions/{id}/materials
POST  /api/v1/interventions/{id}/materials
PATCH /api/v1/interventions/{id}/materials/{material_id}
DELETE /api/v1/interventions/{id}/materials/{material_id}
```

## Rapports

```http id="r2k6v5"
GET  /api/v1/interventions/{id}/reports
POST /api/v1/interventions/{id}/reports
GET  /api/v1/reports/{id}
GET  /api/v1/reports/{id}/file
```

## Avis

```http id="p8j4m7"
GET  /api/v1/interventions/{id}/review
POST /api/v1/interventions/{id}/review
```

---

# 34. Filtres

La liste des interventions doit permettre de filtrer notamment par :

```text id="k6q9r3"
site
equipment
technician
type
status
result
date planifiée
date de réalisation
```

Exemple :

```http id="w3s7n5"
GET /api/v1/interventions
    ?equipment_id=137
    &type=PREVENTIVE_MAINTENANCE
    &status=COMPLETED
```

---

# 35. Transactions

Certaines opérations doivent être transactionnelles.

Exemple : clôture d'une intervention.

```text id="y5p1r8"
Complete intervention
       │
       ├── status = COMPLETED
       ├── completed_at
       ├── result
       └── données associées
              │
              ▼
          COMMIT
```

Si une étape obligatoire échoue, l'opération ne doit pas laisser une intervention dans un état incohérent.

Même principe pour les opérations impliquant plusieurs entités.

---

# 36. Idempotence

Les actions métier sensibles doivent éviter les doubles traitements.

Exemple :

```http id="q4v7n2"
POST /interventions/1054/complete
```

Si la requête est répétée après une première réussite, le backend doit détecter que l'intervention est déjà terminée plutôt que d'exécuter une seconde clôture incohérente.

Même principe pour les opérations critiques telles que :

* génération de document ;
* transmission future d'un rapport ;
* annulation ;
* remplacement d'équipement.

---

# 37. Notifications

Les notifications ne constituent pas une dépendance obligatoire du module V1.

Elles pourront être ajoutées ultérieurement pour :

* intervention planifiée ;
* intervention affectée ;
* rapport généré ;
* rapport transmis ;
* suivi nécessaire.

Le cœur métier doit fonctionner sans système de notification.

---

# 38. Workflow complet

Exemple de dépannage :

```text id="r8k2m6"
Client
  │
  │ signale une panne
  ▼
Création intervention
  │
  ├── type = TROUBLESHOOTING
  ├── site = Massy
  └── equipment = null
  │
  ▼
Planification
  │
  ▼
Affectation technicien
  │
  ▼
Début
  │
  ▼
IN_PROGRESS
  │
  ├── identification équipement
  ├── checklist
  ├── diagnostic
  ├── photos
  ├── matériel
  └── observations
  │
  ▼
Résultat
  │
  ├── RESOLVED
  ├── PART_REQUIRED
  ├── QUOTE_REQUIRED
  └── ...
  │
  ▼
COMPLETED
  │
  ▼
Rapport
  │
  ▼
Avis éventuel
```

---

# 39. Règles métier principales

### R1 — Une intervention appartient à un site

`site_id` est obligatoire.

### R2 — L'équipement est optionnel au départ

Une intervention peut commencer sans équipement identifié.

### R3 — Cohérence site/équipement

Si un équipement est renseigné :

```text id="8k2m4v"
equipment.site_id == intervention.site_id
```

### R4 — Le statut et le résultat sont distincts

`COMPLETED` ne signifie pas `RESOLVED`.

### R5 — Une intervention terminée conserve son historique

Les données essentielles ne doivent pas être écrasées arbitrairement.

### R6 — Une checklist historique ne dépend plus du template courant

Une modification du template ne modifie pas les anciennes interventions.

### R7 — Les photos appartiennent à l'intervention

Elles ne sont pas stockées comme des objets indépendants sans contexte métier.

### R8 — Le matériel est historisé

La consommation déclarée reste liée à l'intervention.

### R9 — Un rapport transmis reste identifiable

Une nouvelle version ne doit pas écraser silencieusement l'ancienne.

### R10 — Une intervention peut avoir au maximum un avis en V1

Relation :

```text
Intervention 1 ─── 0..1 Review
```

---

# 40. Critères d'acceptation

Le module est considéré comme fonctionnel lorsque :

* une intervention peut être créée ;
* elle est obligatoirement rattachée à un site ;
* elle peut être créée sans équipement identifié ;
* un équipement peut être ajouté ultérieurement ;
* la cohérence site/équipement est vérifiée ;
* une intervention peut être planifiée ;
* un ou plusieurs techniciens peuvent être affectés ;
* une intervention peut être démarrée ;
* une checklist historique peut être exécutée ;
* des photos peuvent être ajoutées ;
* du matériel peut être déclaré ;
* les observations peuvent être renseignées ;
* un résultat distinct du statut peut être enregistré ;
* une intervention peut être terminée ;
* un rapport peut être généré ;
* le rapport reste historisé ;
* un avis peut être associé ;
* l'historique de l'équipement permet de retrouver ses interventions ;
* le remplacement d'un équipement ne détruit pas son historique ;
* les droits d'accès sont contrôlés.

---

# 41. Principe du module

> **Une intervention est l'enregistrement complet d'une action technique : ce qui devait être fait, ce qui a été fait, sur quel équipement, avec quelles preuves et avec quel résultat.**

Le cœur de Tervo peut donc être résumé ainsi :

```text id="6m9q4x"
CLIENT
   │
   ▼
SITE
   │
   ▼
ÉQUIPEMENT
   │
   ▼
INTERVENTION
   │
   ├── TECHNICIENS
   ├── CHECKLIST
   ├── PHOTOS
   ├── MATÉRIEL
   ├── OBSERVATIONS
   ├── RÉSULTAT
   ├── RAPPORT
   └── AVIS
```

C'est cette structure qui permet à Tervo de passer d'un simple outil de planning à un véritable historique technique des équipements.
