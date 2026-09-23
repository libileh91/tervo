# Tervo — Roadmap d'implémentation

## 1. Objectif

Cette roadmap définit l'ordre dans lequel Tervo doit être construit à partir du modèle fonctionnel et technique défini dans le DAT.

Elle ne constitue pas une liste exhaustive de tickets.

Son objectif est de répondre à trois questions :

1. **dans quel ordre construire les briques ;**
2. **quelles dépendances respecter ;**
3. **à quel moment considérer qu'un périmètre est réellement utilisable.**

Principe général :

```text
Fondations
    ↓
Référentiels
    ↓
Client / Site
    ↓
Catalogue
    ↓
Vente / Installation
    ↓
Équipement
    ↓
Intervention
    ↓
Preuves et rapport
    ↓
Showroom / commercial
    ↓
Durcissement / exploitation
```

Le développement doit suivre le modèle métier plutôt que l'ordre des écrans.

---

# 2. Principe directeur

Le premier parcours métier réellement utile à Tervo est :

```text
Client
  ↓
Site
  ↓
Produit
  ↓
Vente
  ↓
Installation
  ↓
Équipement
  ↓
Intervention
  ↓
Rapport
```

Une fois ce parcours fonctionnel, Tervo possède déjà son cœur de valeur :

> **savoir ce qui a été vendu, ce qui a été installé, où, et ce qui a ensuite été fait dessus.**

Le showroom vient ensuite compléter le parcours commercial.

---

# 3. Avant de coder : décisions verrouillées

Ces points du modèle sont **verrouillés** avant l'implémentation.

Ils ne doivent plus être rediscutés implicitement pendant le développement.

---

## 3.1 Identifiants

**Décision verrouillée :** identifiant **entier auto-incrémenté**
(`SERIAL` / `Integer`). Pas d'`UUID` en V1.

Le choix doit être cohérent pour :

* PostgreSQL ;
* API ;
* frontend ;
* relations ;
* URLs ;
* migrations.

Aucun mélange arbitraire entre plusieurs stratégies ne doit apparaître.

---

## 3.2 Installation et équipement

Le modèle doit conserver la distinction :

```text
Installation = événement
Equipment    = objet physique
```

Une installation terminée crée ou confirme l'existence d'un équipement physique.

Le modèle V1 doit donc éviter de créer artificiellement un équipement simplement parce qu'une installation est planifiée.

Conséquence :

```text
Installation planifiée
    ↓
pas encore nécessairement d'Equipment

Installation réalisée
    ↓
Equipment physique
```

Le statut `PLANNED` sur `Equipment` est donc **écarté** (décision verrouillée).

### Décision cible

Pour V1 :

```text
Equipment
├── ACTIVE
├── OUT_OF_SERVICE
├── REPLACED
└── RETIRED
```

Une installation future est portée par `Installation`, pas par un faux équipement `PLANNED`.

---

## 3.3 Planning d'installation

Le modèle `Installation` doit distinguer :

```text
scheduled_start
scheduled_end

installation_date
commissioning_date
```

Les premières représentent le planning.

Les secondes représentent les événements réellement réalisés.

Cela évite d'utiliser une même date pour deux concepts différents.

---

## 3.4 Quantité d'une ligne de vente

Une ligne de vente peut avoir :

```text
quantity > 1
```

Mais un équipement est toujours une instance physique individuelle.

Le modèle cible est donc :

```text
SaleLine
quantity = 3
   │
   ├── Installation #1 → Equipment #1
   ├── Installation #2 → Equipment #2
   └── Installation #3 → Equipment #3
```

`SaleLine 1 → N Installation` doit être conservé.

---

## 3.5 Garantie

V1 conserve les dates de garantie directement sur `Equipment` :

```text
warranty_start
warranty_end
```

Une entité `Warranty` séparée n'est introduite que si les règles métier deviennent plus complexes.

L'intervention doit pouvoir indiquer explicitement si elle est traitée sous garantie lorsque ce contexte est nécessaire.

---

## 3.6 Rapport

Le concept doit être :

```text
Intervention
    │
    └── Report
           ├── version 1
           ├── version 2
           └── ...
```

Une version transmise doit rester historiquement identifiable.

Il faut éviter un modèle dans lequel plusieurs lignes `Report` sont créées sans distinction claire entre document logique et version.

La décision d'implémentation devra donc préciser :

```text
Report = document logique
ReportVersion = version physique
```

ou une représentation équivalente.

---

## 3.7 Prospect / client

Le showroom peut commencer avec une personne qui n'est pas encore cliente.

Le modèle doit donc permettre :

```text
ShowroomVisit
├── client_id nullable
└── visitor information
```

La création d'un `Client` ne doit pas être artificiellement obligatoire pour enregistrer une visite.

---

## 3.8 Devis

Le devis est identifié fonctionnellement mais n'est pas encore suffisamment nécessaire pour justifier un module complet dans le cœur technique V1.

Décision :

```text
Showroom
    ↓
QUOTE_REQUESTED / QUOTE_SENT
```

suffit dans un premier temps.

Une véritable entité `Quote` pourra être introduite lorsque le besoin commercial sera confirmé.

---

## 3.9 Récapitulatif des décisions verrouillées

| Décision | Verdict |
|----------|---------|
| Identifiants | entier auto-incrémenté (pas d'UUID en V1) |
| `Equipment` sans `PLANNED` | ACTIVE / OUT_OF_SERVICE / REPLACED / RETIRED |
| `SaleLine 1 → N Installation` | confirmé |
| Statuts `Installation` | SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED |
| `Report` versioning V1 | document logique + versions |
| `ShowroomVisit.client_id` nullable | confirmé |
| Devis (`Quote`) | hors modèle V1 |
| Rôles | normalisés (admin, manager, technicien, commercial) |
| `Equipment.replaced_by_id` | ancien → nouveau |
| `Intervention.under_warranty` | confirmé |

---

# 4. Phase 0 — Fondations du projet

## Objectif

Obtenir une application qui démarre proprement avant d'implémenter le métier.

### Backend

Mettre en place :

```text
FastAPI
Configuration
Logging
Gestion des erreurs
SQLAlchemy
Alembic
PostgreSQL
Tests
```

Structure cible :

```text
backend/app/
├── api/
├── domains/
├── infrastructure/
└── core/
```

### Frontend

Mettre en place :

```text
Vue
Routing
Gestion de l'authentification
Client HTTP
Gestion des erreurs
Layout principal
```

### Infrastructure

Mettre en place :

```text
Docker Compose
PostgreSQL
Backend
Frontend
Storage
Reverse proxy
```

### Validation

À la fin de cette phase :

```text
docker compose up
        ↓
application accessible
        ↓
API accessible
        ↓
PostgreSQL accessible
        ↓
migration Alembic fonctionnelle
        ↓
tests exécutables
```

Aucun module métier ne doit être commencé tant que cette base n'est pas stable.

---

# 5. Phase 1 — Authentification et utilisateurs

## Objectif

Construire la frontière de sécurité avant les données métier.

### Backend

Implémenter :

```text
User
Role
Authentication
Password hashing
Authorization
```

Endpoints minimaux :

```http
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

Puis :

```text
ADMIN
MANAGER
TECHNICIAN
COMMERCIAL
```

### Tests

Tester notamment :

```text
utilisateur valide
mot de passe incorrect
compte désactivé
route protégée
route publique
rôle insuffisant
```

### Critère de sortie

Une route métier ne peut pas être considérée comme terminée tant que :

```text
authentification
+
autorisation
```

ne sont pas testées.

---

# 6. Phase 2 — Client et Site

## Objectif

Créer la structure géographique et relationnelle de base.

```text
Client
   │
   └── Site
```

### Backend

Implémenter :

```text
Client
Site
```

CRUD minimal.

Endpoints :

```http
GET    /clients
POST   /clients
GET    /clients/{id}
PATCH  /clients/{id}

GET    /sites
POST   /sites
GET    /sites/{id}
PATCH  /sites/{id}
```

### Frontend

Créer :

```text
Liste clients
Fiche client
Création/modification client

Liste sites
Fiche site
Création/modification site
```

### Critère de sortie

Depuis un client :

```text
Client
   ↓
Sites
```

et depuis un site :

```text
Site
   ↓
Client
```

doivent être consultables.

---

# 7. Phase 3 — Catalogue

## Objectif

Construire le référentiel produit.

```text
Product
```

### Backend

Implémenter :

```text
Product
```

avec :

* référence ;
* nom ;
* description ;
* marque ;
* catégorie ;
* actif.

Endpoints :

```http
GET    /products
POST   /products
GET    /products/{id}
PATCH  /products/{id}
POST   /products/{id}/deactivate
```

### Frontend

Créer :

```text
Liste produits
Recherche
Filtres
Fiche produit
Création
Modification
Désactivation
```

### Critère de sortie

Un produit peut être :

```text
créé
consulté
modifié
désactivé
```

sans aucune dépendance au stock.

---

# 8. Phase 4 — Vente

## Objectif

Introduire le premier événement commercial reliant client, site et catalogue.

Modèle :

```text
Sale
   │
   └── SaleLine
          │
          └── Product
```

### Backend

Implémenter :

```text
Sale
SaleLine
```

États minimum :

```text
DRAFT
CONFIRMED
CANCELLED
```

Actions :

```http
POST /sales/{id}/confirm
POST /sales/{id}/cancel
```

### Règles

Une vente :

* appartient à un client ;
* peut être associée à un site ;
* contient une ou plusieurs lignes ;
* référence des produits ;
* conserve les quantités et informations commerciales nécessaires.

### Point important

Le prix de vente doit être **figé sur `SaleLine`**.

Il ne faut pas recalculer une ancienne vente à partir d'un futur prix catalogue.

---

# 9. Phase 5 — Installation

## Objectif

Transformer une vente en événement d'installation.

```text
SaleLine
    ↓
Installation
```

### Modèle

```text
Installation
├── sale_line_id
├── site_id
├── scheduled_start
├── scheduled_end
├── installation_date
├── commissioning_date
├── status
└── technician_notes
```

### Workflow

```text
SCHEDULED
    ↓ start
IN_PROGRESS
    ↓ complete
COMPLETED
    (CANCELLED : sortie alternative autorisée)
```

Les états sont verrouillés : `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`.

### Critère important

Une installation planifiée ne crée pas automatiquement un équipement physique.

---

# 10. Phase 6 — Équipement

## Objectif

Créer le cœur du modèle technique.

```text
Installation
    ↓
Equipment
```

### Données principales

```text
Equipment
├── site_id
├── product_id
├── installation_id
├── serial_number
├── installed_at
├── commissioned_at
├── warranty_start
├── warranty_end
├── lifecycle_status
└── replaced_by_id
```

### Workflow

```text
Installation réalisée
       ↓
Equipment créé
       ↓
Equipment actif
```

### Vue équipement

La fiche doit afficher :

```text
Produit
Site
Client
Numéro de série
Installation
Mise en service
Garantie
Statut
Historique
```

### Critère de sortie

Depuis un équipement, on doit pouvoir retrouver :

```text
client
site
produit
installation
interventions
```

---

# 11. Phase 7 — Historique équipement

Cette phase peut être développée immédiatement après l'équipement, avant les fonctions avancées d'intervention.

Objectif :

```text
Equipment
    ↓
History
```

L'historique est une vue construite à partir des événements.

Exemple :

```text
10/09/2026 — Installation
12/09/2026 — Mise en service
20/11/2026 — Maintenance préventive
03/03/2027 — Dépannage
```

Il n'est pas nécessaire de créer une table `EquipmentHistory`.

### Critère de sortie

La fiche équipement devient le point d'entrée naturel vers son passé technique.

---

# 12. Phase 8 — Interventions : cœur métier

## Objectif

Permettre au technicien de gérer une intervention de bout en bout.

### Première version

Commencer volontairement avec :

```text
Intervention
InterventionTechnician
```

Puis :

```text
PLANNED
    ↓
IN_PROGRESS
    ↓
COMPLETED
```

avec :

```text
type
result
description
observations
dates
```

### API

```http
GET    /interventions
POST   /interventions
GET    /interventions/{id}
PATCH  /interventions/{id}

POST   /interventions/{id}/start
POST   /interventions/{id}/complete
POST   /interventions/{id}/cancel
```

### Critère de sortie

Un technicien peut :

```text
voir
ouvrir
démarrer
documenter
terminer
```

une intervention.

---

# 13. Phase 9 — Checklists

## Objectif

Standardiser l'exécution technique.

Construire :

```text
ChecklistTemplate
        ↓
InterventionChecklist
        ↓
ChecklistItem
```

### Ordre d'implémentation

1. templates ;
2. version ;
3. instanciation ;
4. items ;
5. résultats ;
6. commentaires.

### Règle fondamentale

Une intervention possède un snapshot de la checklist utilisée.

```text
Template v3
    ↓
Intervention #1054
    ↓
Checklist v3
```

Une future v4 ne modifie pas l'intervention #1054.

---

# 14. Phase 10 — Photos

## Objectif

Permettre au technicien de documenter l'intervention.

Implémenter :

```text
Photo
```

avec stockage séparé.

Workflow :

```text
Frontend
   ↓
Upload multipart
   ↓
API
   ↓
Validation
   ↓
Storage
   ↓
Metadata PostgreSQL
```

### Critères

Tester :

* type autorisé ;
* taille maximale ;
* utilisateur autorisé ;
* rattachement à l'intervention ;
* téléchargement protégé ;
* suppression contrôlée.

---

# 15. Phase 11 — Matériel utilisé

## Objectif

Permettre de déclarer ce qui a été utilisé pendant l'intervention.

V1 :

```text
MaterialUsage
├── designation
├── quantity
└── unit
```

Exemple :

```text
2 × raccord cuivre
1 × filtre
```

Le stock n'est pas encore impliqué.

Cette séparation est importante :

```text
Matériel utilisé
       ≠
Gestion de stock
```

---

# 16. Phase 12 — Résultat et clôture métier

## Objectif

Faire de la clôture une véritable opération métier.

Une intervention terminée doit pouvoir indiquer :

```text
RESOLVED
PARTIALLY_RESOLVED
UNRESOLVED
PART_REQUIRED
QUOTE_REQUIRED
FOLLOW_UP_REQUIRED
```

### Exemple

```text
Type :
TROUBLESHOOTING

Status :
COMPLETED

Result :
PART_REQUIRED
```

### Règle

Le backend valide la cohérence :

```text
status
+
result
+
checklist
+
données obligatoires
```

avant de clôturer.

---

# 17. Phase 13 — Rapports

## Objectif

Transformer les données d'intervention en document exploitable.

Pipeline :

```text
Intervention
    ↓
Report data
    ↓
PDF
    ↓
Storage
    ↓
Report metadata
```

Le rapport doit inclure au minimum :

```text
Client
Site
Équipement
Techniciens
Dates
Type
Résultat
Checklist
Photos
Matériel
Observations
```

### Versionnement

Le système doit pouvoir distinguer :

```text
version générée
version modifiée
version transmise
```

Le mécanisme exact `Report / ReportVersion` doit être fixé avant la génération du premier rapport transmis.

---

# 18. Phase 14 — Avis

## Objectif

Ajouter le retour client sans bloquer l'opération technique.

```text
Intervention
    │
    └── 0..1 Review
```

Un avis peut contenir :

```text
rating
comment
created_at
```

L'absence d'avis est normale.

Le technicien ne doit pas être empêché de terminer une intervention parce qu'aucun avis n'existe.

---

# 19. Phase 15 — Remplacement d'équipement

## Objectif

Préserver l'historique lorsqu'un équipement est remplacé.

Workflow :

```text
Ancien Equipment
      │
      │ replace
      ▼
Nouvel Equipment
```

L'ancien passe par exemple à :

```text
REPLACED
```

et conserve ses interventions.

Le nouveau possède :

```text
replaced_by / replaced_from
```

selon la direction de relation finalement retenue.

### Critère

L'historique avant remplacement reste consultable.

---

# 20. Phase 16 — Showroom

Le showroom peut être développé une fois le cœur client/catalogue/vente stabilisé.

Modèle :

```text
ShowroomVisit
       │
       └── ShowroomVisitProduct
```

Fonctions :

```text
création visite
produits présentés
notes
commercial
suivi
```

Statuts :

```text
TO_FOLLOW_UP
CONSIDERING
QUOTE_REQUESTED
QUOTE_SENT
SOLD
LOST
NO_FURTHER_ACTION
```

Le showroom ne doit pas bloquer le parcours technique principal.

---

# 21. Phase 17 — Recherche et vues transverses

Une fois les domaines principaux fonctionnels, construire les vues qui apportent réellement de la valeur.

### Recherche globale

Recherche par :

```text
client
site
équipement
numéro de série
intervention
produit
```

### Historique client

```text
Client
├── Sites
├── Équipements
├── Interventions
├── Ventes
└── Visites showroom
```

### Historique équipement

```text
Equipment
├── Installation
├── Mise en service
├── Maintenance
├── Dépannage
├── SAV
└── Rapports
```

Ces vues sont plus importantes pour l'utilisateur que la multiplication de CRUD isolés.

---

# 22. Migration des données existantes (remontée)

> **Décision verrouillée :** la migration n'est **plus une phase finale**. Elle est remontée
> juste après le **cœur physique** (`Client → Site → Product → Equipment → Intervention`),
> car elle ne dépend que de ces entités : les équipements historiques ont `installation_id`
> nullable (pas de vente/installation enregistrée pour 20 ans de données).

**Contrainte de conception dès le départ :** le modèle doit pouvoir représenter les données
historiques sans les dénaturer — champs nullable (`installation_id`, `equipment_id`),
équipement sans vente, intervention sans équipement identifiable, client/site incomplet,
produit inconnu, dates absentes, doublons.

Processus :

```text
Anciennes données
       ↓
Analyse
       ↓
Mapping
       ↓
Transformation
       ↓
Validation
       ↓
Import
       ↓
Contrôle
```

Mécanismes : normalisation, fuzzy matching (3 zones 95/80), 2 passes, transaction par batch,
idempotence SHA-256, orphelins tracés.

Pour les données ambiguës :

```text
attacher à l'existant
        OU
créer une nouvelle entité
        OU
corriger
        OU
ignorer avec justification
```

Il ne faut jamais inventer une relation simplement pour faire disparaître une anomalie.

---

# 23. Phase 19 — Tests métier

Les tests doivent suivre le modèle métier, pas uniquement les endpoints.

## Tests critiques

### Client / Site

```text
Client → Site
```

### Vente

```text
Sale → SaleLine → Product
```

### Installation

```text
SaleLine → Installation
```

### Équipement

```text
Installation → Equipment
```

### Intervention

```text
Equipment → Intervention
```

### Historique

```text
Equipment → Interventions
```

### Remplacement

```text
Old Equipment → New Equipment
```

### Checklist

```text
Template v1
    ↓
Intervention
    ↓
Template v2
```

L'intervention doit toujours conserver sa version historique.

---

# 24. Tests de sécurité

En parallèle des tests fonctionnels :

```text
authentification
autorisation
isolation des données
upload
accès fichiers
validation
erreurs
```

Exemples importants :

```text
Technicien A
    ↓
ne doit pas accéder arbitrairement
à une ressource hors de son périmètre
```

et :

```text
Connaître l'ID d'un équipement
    ≠
avoir le droit de le consulter
```

---

# 25. Phase 20 — Observabilité et exploitation

Avant la mise en production :

```text
Health check
Logs
Metrics minimales
Backups
Restore test
Storage monitoring
```

Endpoints :

```http
GET /health
GET /health/ready
```

Les logs doivent permettre d'identifier :

```text
quoi
quand
où
```

sans exposer de données sensibles.

---

# 26. Phase 21 — Durcissement production

Avant production :

* HTTPS ;
* secrets hors Git ;
* PostgreSQL non public ;
* permissions minimales ;
* CORS configuré ;
* upload sécurisé ;
* sauvegardes automatisées ;
* restauration testée ;
* comptes désactivables ;
* gestion d'erreurs production ;
* logs sans secrets ;
* volumes persistants ;
* migrations versionnées.

---

# 27. Ordre de développement recommandé

L'ordre global est donc :

```text
00 — Fondations
 │
 ▼
01 — Auth / Users
 │
 ▼
02 — Clients / Sites
 │
 ▼
03 — Catalogue
 │
 ▼
04 — Ventes / SaleLines
 │
 ▼
05 — Installations
 │
 ▼
06 — Équipements
 │
 ▼
07 — Historique équipement
 │
 ▼
08 — Interventions
 │
 ▼
09 — MIGRATION (remontée)   ← cible : Client / Site / Product / Equipment / Intervention
 │
 ▼
10 — Checklists
 │
 ▼
11 — Photos
 │
 ▼
12 — Matériel
 │
 ▼
13 — Résultats / Clôture
 │
 ▼
14 — Rapports
 │
 ▼
15 — Avis
 │
 ▼
16 — Remplacement équipement
 │
 ▼
17 — Showroom
 │
 ▼
18 — Vues transverses
 │
 ▼
19 — Tests / sécurité
 │
 ▼
20 — Exploitation
 │
 ▼
21 — Production
```

> **Remontée de la migration :** elle est placée en position 09 — juste après le **cœur
> physique** (`Client/Site/Product/Equipment/Intervention`), sans attendre le cycle terrain
> (10-17). La chaîne commerciale (04-05) n'est pas un prérequis : les équipements historiques
> ont `installation_id` nullable. Le modèle est **migration-aware** dès le départ.

---

# 28. Premier incrément réellement utilisable

Il ne faut pas attendre la fin de toute la roadmap pour obtenir une première version utile.

Le premier incrément métier doit être :

```text
Client
   ↓
Site
   ↓
Product
   ↓
Sale
   ↓
Installation
   ↓
Equipment
```

Cela permet déjà de répondre à :

> Qui possède quoi, où, et comment cet équipement a-t-il été installé ?

---

# 29. Deuxième incrément

Ajouter :

```text
Equipment
    ↓
Intervention
```

avec :

* planification ;
* technicien ;
* démarrage ;
* observations ;
* résultat ;
* clôture.

Tervo devient alors utilisable pour le suivi opérationnel.

---

# 30. Troisième incrément

Ajouter :

```text
Checklist
Photos
MaterialUsage
```

Le technicien peut alors réellement documenter son intervention.

---

# 31. Quatrième incrément

Ajouter :

```text
Report
Review
```

Le cycle devient :

```text
Intervention
    ↓
Exécution
    ↓
Preuves
    ↓
Résultat
    ↓
Rapport
    ↓
Avis
```

Ce constitue le premier cycle opérationnel complet.

---

# 32. Cinquième incrément

Ajouter :

```text
Showroom
    ↓
Suivi commercial
```

Puis connecter le parcours :

```text
Showroom
   ↓
Vente
   ↓
Installation
   ↓
Equipment
   ↓
Intervention
```

---

# 33. Ce qui ne doit pas être développé trop tôt

Ne pas commencer par :

```text
Stock avancé
Fournisseurs
Achats
Contrats complexes
Facturation
Comptabilité
KPI avancés
Optimisation automatique des tournées
Microservices
Event bus
Architecture distribuée
```

Ces fonctionnalités peuvent être utiles, mais elles dépendent du cœur métier.

Le risque serait de construire beaucoup d'infrastructure autour d'un modèle encore instable.

---

# 34. Definition of Done d'un module

Un module n'est pas considéré comme terminé simplement parce que :

```text
table créée
+
endpoint créé
+
écran créé
```

Il est terminé lorsque :

```text
Modèle
+
Migration
+
API
+
Autorisation
+
Validation
+
Workflow métier
+
Frontend
+
Tests
+
Gestion des erreurs
```

sont cohérents.

Pour les modules contenant des fichiers :

```text
+
Storage
+
Contrôle d'accès
```

---

# 35. Critères de sortie de la V1

Tervo V1 peut être considéré comme cohérent lorsque le parcours suivant fonctionne sans intervention manuelle dans la base :

```text
Créer client
    ↓
Créer site
    ↓
Créer produit
    ↓
Créer vente
    ↓
Ajouter produit à la vente
    ↓
Planifier installation
    ↓
Réaliser installation
    ↓
Créer équipement
    ↓
Planifier intervention
    ↓
Affecter technicien
    ↓
Démarrer intervention
    ↓
Exécuter checklist
    ↓
Ajouter photos
    ↓
Déclarer matériel
    ↓
Renseigner résultat
    ↓
Terminer intervention
    ↓
Générer rapport
    ↓
Consulter historique équipement
```

Ce parcours est le **test de cohérence principal de Tervo**.

---

# 36. Architecture finale visée

À terme :

```text
                    ┌──────────────┐
                    │   Showroom   │
                    └──────┬───────┘
                           │
                           ▼
Client ────────► Vente ──► SaleLine
  │                           │
  │                           ▼
  └──► Site              Installation
                              │
                              ▼
                          Equipment
                              │
                              ▼
                        Intervention
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
           Checklist       Photos       Material
                │             │             │
                └─────────────┼─────────────┘
                              ▼
                           Result
                              │
                              ▼
                            Report
                              │
                              ▼
                            Review
```

---

# 37. Principe de livraison

Le développement doit avancer par **vertical slices métier** plutôt que par couches techniques isolées.

À éviter :

```text
"Je termine toute la base de données."
"Puis toute l'API."
"Puis tout le frontend."
```

Préférer :

```text
Client
├── DB
├── API
├── Frontend
└── Tests
        ↓
Site
├── DB
├── API
├── Frontend
└── Tests
        ↓
...
```

Cela permet de détecter beaucoup plus tôt les incohérences entre le modèle, l'API et l'interface.

---

# 38. Règle de progression

Chaque phase doit répondre à une question métier.

```text
Clients / Sites
→ Qui est concerné et où ?

Catalogue
→ Quel produit ?

Vente
→ Qu'est-ce qui a été vendu ?

Installation
→ Quand et comment a-t-il été installé ?

Equipment
→ Quel appareil existe réellement ?

Intervention
→ Qu'a-t-on fait dessus ?

Checklist / Photos / Matériel
→ Comment l'intervention a-t-elle été exécutée ?

Result
→ Quel a été le résultat ?

Report
→ Quelle restitution a été produite ?

History
→ Que s'est-il passé depuis l'installation ?
```

Si une fonctionnalité ne répond à aucune question métier claire, elle ne doit pas automatiquement entrer dans la V1.

---

# 39. Priorités

### P0 — cœur indispensable

```text
Auth
Clients
Sites
Catalogue
Sales
SaleLines
Installations
Equipment
Interventions
```

### P1 — exploitation opérationnelle

```text
Checklists
Photos
MaterialUsage
Reports
Historique
```

### P2 — enrichissement

```text
Reviews
Showroom
Replacement workflows
Recherche transverse
```

### P3 — extensions

```text
Quotes
Stock
Suppliers
Contracts
KPI avancés
Automatisation
```

---

# 40. Principe final

La roadmap Tervo suit une progression volontairement simple :

```text
STRUCTURER
    ↓
VENDRE
    ↓
INSTALLER
    ↓
IDENTIFIER L'ÉQUIPEMENT
    ↓
INTERVENIR
    ↓
PROUVER
    ↓
RESTITUER
    ↓
HISTORISER
```

Le développement doit toujours préserver cette chaîne.

> **Tervo ne doit pas devenir une collection de modules indépendants. Le produit doit progressivement construire une histoire cohérente allant du produit vendu jusqu'à l'historique technique de l'équipement.**
