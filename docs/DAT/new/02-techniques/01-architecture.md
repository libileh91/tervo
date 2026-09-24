# Tervo — Architecture technique

> Architecture cible de Tervo.
>
> Ce document traduit les besoins fonctionnels en composants techniques, sans détailler le modèle de données ni l'ensemble des endpoints API.

---

## 1. Objectif

Tervo est une application web de gestion d'activité CVC orientée :

* gestion des clients et sites ;
* suivi des équipements installés ;
* planification et réalisation d'interventions ;
* checklists techniques ;
* photos et pièces justificatives ;
* matériel utilisé ;
* génération de rapports ;
* suivi commercial showroom ;
* historique des opérations.

L'architecture doit privilégier :

* simplicité ;
* maintenabilité ;
* séparation claire des responsabilités ;
* évolutivité progressive ;
* déploiement simple ;
* cohérence des données métier.

Tervo ne doit pas être conçu comme une architecture distribuée complexe dès le départ.

---

# 2. Architecture générale

L'application suit une architecture web classique en trois grandes parties :

```text
┌──────────────────────────────────────────────────────────┐
│                      UTILISATEUR                         │
│                 Navigateur Web / Mobile                  │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTPS
                           ▼
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND WEB                          │
│                                                          │
│  Interface utilisateur                                   │
│  - Clients / sites                                       │
│  - Équipements                                           │
│  - Interventions                                         │
│  - Checklists                                            │
│  - Photos                                                │
│  - Rapports                                              │
│  - Showroom                                              │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP / JSON
                           ▼
┌──────────────────────────────────────────────────────────┐
│                      API                                 │
│                                                          │
│  Authentification                                        │
│  Routes HTTP                                             │
│  Validation des entrées                                  │
│  Règles métier                                           │
│  Accès aux données                                       │
│  Génération de documents                                 │
└───────────────┬───────────────────────────┬──────────────┘
                │                           │
                ▼                           ▼
┌─────────────────────────┐       ┌────────────────────────┐
│      PostgreSQL         │       │   Stockage fichiers    │
│                         │       │                        │
│ Clients / sites         │       │ Photos                 │
│ Équipements             │       │ Rapports               │
│ Interventions           │       │ Documents               │
│ Catalogue / ventes      │       │                        │
│ Checklists              │       │                        │
└─────────────────────────┘       └────────────────────────┘
```

---

# 3. Organisation du backend

Le backend est organisé par responsabilités.

```text
API
 │
 ▼
Routers / Controllers
 │
 ▼
Services métier
 │
 ├── Clients
 ├── Sites
 ├── Équipements
 ├── Interventions
 ├── Checklists
 ├── Catalogue
 ├── Commercial
 ├── Rapports
 └── Documents
 │
 ▼
Repositories / Data Access
 │
 ▼
PostgreSQL
```

Le principe important est :

> Une route HTTP ne doit pas contenir directement toute la logique métier.

Exemple :

```text
POST /interventions
        │
        ▼
Intervention Router
        │
        ▼
Intervention Service
        │
        ├── validation métier
        ├── création
        └── événements éventuels
        │
        ▼
Repository
        │
        ▼
PostgreSQL
```

Le pipeline d'import constitue une **capacité transverse** du backend, indépendante des
écrans métier :

```text
Migration / Import historique
     │
     ├── ExcelReader / FormatDetector   (lecture + mapping des colonnes)
     ├── Normalizer / Validator         (normalisation + validation)
     ├── ClientMatcher                  (rapprochement fuzzy, 3 zones)
     └── ImportService                  (2 passes + transactions par batch)
     │
     ▼
PostgreSQL  (ImportBatch / ImportRecord / ImportError)
```

Lecture V1 : `.xlsx` et `.csv`, multi-feuilles, en-tête détecté ou choisi, encodage et séparateur visibles. Les sources restent intactes ; l’aperçu conserve fichier/feuille/ligne physique, valeurs brutes, normalisées, anomalies et propositions. Les décisions détaillées et les champs de traçabilité sont définis dans [le modèle de données](02-data-model.md#décisions-lot-2-validées).

La validation structurelle produit des candidats, pas une autorisation d’écriture. Le rapprochement privilégie les références source fiables, puis propose des correspondances métier. Les seuils 95/80 n’annulent ni un conflit d’identité ni une demande explicite de revue. L’exécution doit utiliser le fichier, le mapping et les décisions effectivement validés. La lecture actuelle charge une feuille en mémoire ; les transactions par 500 lignes concernent la persistance, pas une garantie de lecture en flux.

Il est conçu **conjointement** avec le modèle de données métier (champs nullable de
l'historique, provenance, traçabilité).

---

# 4. Frontend

Le frontend constitue l'interface principale utilisée par les différents profils.

Il doit permettre une utilisation adaptée au contexte terrain.

## 4.1 Principales zones

```text
Application
├── Dashboard
├── Clients
│   ├── Clients
│   └── Sites
├── Équipements
├── Interventions
│   ├── Planning
│   └── Historique
├── Catalogue
├── Commercial / Showroom
├── Rapports
└── Administration
```

## 4.2 Vue équipement

L'équipement constitue une vue métier importante.

Une fiche équipement doit permettre de retrouver rapidement :

```text
Équipement
├── Informations générales
├── Client
├── Site
├── Produit catalogue
├── Installation
├── Garantie
├── Historique
│   ├── Maintenance
│   ├── Dépannage
│   ├── SAV
│   └── Autres interventions
└── Documents
```

L'objectif est qu'un technicien puisse comprendre rapidement l'historique de l'équipement avant d'intervenir.

---

# 5. Backend API

L'API constitue le point d'entrée du frontend.

Elle est responsable notamment de :

* authentifier l'utilisateur ;
* autoriser les opérations ;
* valider les données entrantes ;
* appeler les services métier ;
* retourner des réponses structurées ;
* gérer les erreurs ;
* déclencher certaines opérations asynchrones si nécessaire.

Exemple :

```text
Frontend
   │
   │ POST /api/v1/interventions
   ▼
API
   │
   ▼
Validation
   │
   ▼
InterventionService
   │
   ├── vérifier le site
   ├── vérifier l'équipement
   ├── vérifier les droits
   └── créer l'intervention
   │
   ▼
Repository
   │
   ▼
Database
```

---

# 6. Organisation par domaine

Le backend doit suivre les domaines métier plutôt qu'une organisation purement technique.

Exemple cible :

```text
backend/
└── app/
    ├── api/
    │   └── v1/
    │
    ├── domains/
    │   ├── clients/
    │   ├── sites/
    │   ├── equipment/
    │   ├── interventions/
    │   ├── checklists/
    │   ├── catalogue/
    │   ├── commercial/
    │   ├── reports/
    │   └── documents/
    │
    ├── infrastructure/
    │   ├── database/
    │   ├── storage/
    │   └── ...
    │
    └── core/
        ├── config/
        ├── security/
        └── ...
```

Cette organisation permet de faire évoluer progressivement les domaines sans créer un backend monolithique difficile à maintenir.

---

# 7. Services métier

Les services contiennent les règles qui dépassent la simple persistance.

Exemple :

```text
InterventionService
├── create()
├── schedule()
├── start()
├── complete()
├── cancel()
├── add_photo()
├── add_material()
└── generate_report()
```

Le service doit notamment garantir les règles métier.

Exemple :

```text
Impossible de démarrer une intervention annulée.
```

ou :

```text
Une intervention terminée doit avoir un résultat.
```

Ces règles ne doivent pas dépendre uniquement du frontend.

---

# 8. Accès aux données

L'accès à PostgreSQL doit être séparé de la logique métier.

```text
Service
   │
   ▼
Repository
   │
   ▼
ORM / SQL
   │
   ▼
PostgreSQL
```

Le repository est responsable de la lecture et de l'écriture des données.

Le service décide **pourquoi** et **dans quelles conditions** ces opérations doivent être effectuées.

---

# 9. Base de données

PostgreSQL constitue le stockage principal des données métier.

Les données structurées comprennent notamment :

```text
Clients
Sites
Équipements
Produits
Ventes
Installations
Interventions
Checklists
Photos / métadonnées
Matériel utilisé
Rapports
Avis
Showroom
Garantie
```

Le modèle exact et les relations entre ces entités sont définis dans :

```text
docs/DAT/02-techniques/02-data-model.md
```

---

# 10. Stockage des fichiers

Les fichiers binaires ne doivent pas être stockés directement dans les tables métier.

Sont concernés notamment :

* photos d'intervention ;
* rapports PDF ;
* documents ;
* éventuelles pièces jointes.

Le système doit conserver en base les métadonnées nécessaires :

```text
Photo
├── intervention_id
├── chemin / identifiant de stockage
├── nom
├── type
├── taille
├── date
└── métadonnées éventuelles
```

Le stockage physique peut évoluer sans modifier le modèle métier.

Exemple :

```text
Application
    │
    ▼
Storage abstraction
    │
    ├── stockage local
    ├── volume Docker
    └── stockage objet futur
```

En V1, un stockage simple sur volume persistant est suffisant.

---

# 11. Génération de documents

Les rapports sont générés à partir des données d'une intervention.

```text
Intervention
     │
     ▼
Report Service
     │
     ▼
Template
     │
     ▼
PDF
     │
     ▼
Storage
```

La génération doit être indépendante de l'interface utilisateur.

Exemple :

```text
POST /interventions/{id}/report
```

Le backend peut :

1. récupérer l'intervention ;
2. vérifier qu'elle est suffisamment complète ;
3. construire les données du rapport ;
4. générer le document ;
5. enregistrer sa référence ;
6. retourner le document ou son identifiant.

---

# 12. Traitements asynchrones

Certaines opérations peuvent être longues sans nécessiter de bloquer une requête HTTP.

Exemples :

* génération d'un gros rapport ;
* traitement de nombreuses photos ;
* import de données ;
* génération de documents en volume ;
* notifications futures.

Le principe cible est :

```text
HTTP Request
     │
     ▼
Création du traitement
     │
     ▼
Réponse rapide
     │
     ▼
Traitement en arrière-plan
```

L'asynchrone ne doit cependant pas être introduit partout.

Une opération courte et directement nécessaire à la réponse HTTP doit rester synchrone.

---

# 13. Authentification et autorisation

Tervo doit distinguer :

```text
Authentification
    │
    └── Qui est l'utilisateur ?
    
Autorisation
    │
    └── Que peut-il faire ?
```

Les rôles métier envisagés sont notamment :

```text
ADMIN
MANAGER
TECHNICIEN
COMMERCIAL
```

Les permissions précises seront définies dans :

```text
docs/DAT/02-techniques/04-securite.md
```

L'autorisation doit être contrôlée côté backend.

Le frontend peut masquer une fonctionnalité, mais cette protection ne constitue pas une sécurité suffisante.

---

# 14. API versionnée

L'API doit être versionnée dès le départ :

```text
/api/v1/
```

Exemples :

```text
/api/v1/clients
/api/v1/sites
/api/v1/equipment
/api/v1/interventions
/api/v1/checklists
/api/v1/catalogue
```

L'objectif est de permettre une évolution contrôlée de l'API.

La liste détaillée des endpoints sera définie dans :

```text
docs/DAT/02-techniques/03-api.md
```

---

# 15. Gestion des erreurs

L'API doit retourner des erreurs structurées.

Exemple conceptuel :

```json
{
  "error": {
    "code": "INTERVENTION_NOT_FOUND",
    "message": "Intervention introuvable"
  }
}
```

Les erreurs métier doivent être distinguées des erreurs techniques.

Exemples :

```text
404
Intervention inexistante

403
Utilisateur non autorisé

409
Transition métier impossible

422
Données invalides

500
Erreur technique interne
```

---

# 16. Transactions

Les opérations qui modifient plusieurs éléments liés doivent être traitées de manière atomique lorsque nécessaire.

Exemple :

```text
Création d'une installation
        │
        ├── installation
        └── équipement
```

Si la création de l'équipement échoue, l'opération ne doit pas laisser une installation partiellement créée si les deux éléments constituent une seule opération métier.

```text
BEGIN
  │
  ├── créer installation
  ├── créer équipement
  └── COMMIT
```

En cas d'erreur :

```text
ROLLBACK
```

---

# 17. Cohérence et historique

Tervo manipule des données historiques importantes.

Certaines données peuvent être modifiées normalement :

```text
Coordonnées client
Adresse
Informations de contact
```

D'autres nécessitent davantage de précautions :

```text
Interventions terminées
Rapports transmis
Historique équipement
Données de garantie
```

Le système doit éviter les suppressions destructrices lorsque celles-ci font disparaître un historique métier utile.

Exemple :

```text
Équipement remplacé
       │
       └── conservé comme historique
```

---

# 18. Architecture de déploiement

L'architecture cible reste volontairement simple :

```text
                    Internet
                       │
                     HTTPS
                       │
                       ▼
                Reverse Proxy
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
      Frontend                    API
          │                         │
          │                         ├──── PostgreSQL
          │                         │
          │                         └──── Storage
          │
          └──────── navigateur
```

Les différents composants sont déployés sur une infrastructure Docker.

Le déploiement doit privilégier :

* reproductibilité ;
* volumes persistants ;
* sauvegardes ;
* configuration par variables d'environnement ;
* séparation des secrets ;
* logs exploitables.

L'orchestration complexe n'est pas nécessaire pour le périmètre initial.

---

# 19. Environnement de développement

Le développement local doit permettre de lancer rapidement les dépendances principales.

Exemple :

```text
docker compose up -d
```

Services principaux :

```text
frontend
backend
postgres
```

Les services auxiliaires ne doivent être ajoutés que lorsqu'un besoin concret apparaît.

---

# 20. Configuration

Les configurations dépendant de l'environnement ne doivent pas être codées en dur.

Exemples :

```text
DATABASE_URL
SECRET_KEY
STORAGE_PATH
CORS_ORIGINS
ENVIRONMENT
```

Organisation :

```text
Code
 │
 ├── configuration locale
 ├── configuration test
 └── configuration production
```

Les secrets ne doivent jamais être commités dans Git.

---

# 21. Observabilité

Tervo doit fournir un niveau d'observabilité adapté à sa taille.

Minimum :

* logs backend ;
* erreurs avec contexte ;
* logs des opérations importantes ;
* healthcheck de l'API ;
* état de la base de données ;
* surveillance de l'espace disque pour les fichiers.

Exemple :

```text
GET /health
```

Réponse conceptuelle :

```json
{
  "status": "ok"
}
```

Des mécanismes plus avancés de métriques et de tracing pourront être ajoutés si l'utilisation de Tervo le justifie.

---

# 22. Sauvegardes

Les éléments à sauvegarder sont principalement :

```text
PostgreSQL
    +
Storage fichiers
```

Une sauvegarde de la base seule ne suffit pas si les photos et rapports sont stockés séparément.

La stratégie de sauvegarde doit donc préserver la cohérence entre :

```text
Données métier
+
Fichiers
```

La stratégie opérationnelle détaillée pourra être documentée séparément si nécessaire.

---

# 23. Principes d'architecture

Les décisions suivantes guident l'architecture initiale.

### A1 — Monolithe modulaire

Tervo démarre sous forme d'une application backend unique organisée par domaines.

Pas de microservices en V1.

### A2 — API-first

Le frontend communique avec le backend via une API clairement définie.

### A3 — Domaine avant infrastructure

Les règles métier ne doivent pas être dispersées dans :

* les routes HTTP ;
* les composants frontend ;
* les repositories ;
* les scripts SQL.

### A4 — PostgreSQL comme source de vérité

Les données métier structurées sont centralisées dans PostgreSQL.

### A5 — Fichiers séparés des données relationnelles

Photos et documents sont stockés dans un système de fichiers ou stockage objet, avec leurs métadonnées en base.

### A6 — Historique préservé

Les événements et états historiques importants ne doivent pas être détruits simplement parce que la situation actuelle a changé.

### A7 — Asynchrone uniquement lorsque nécessaire

Un traitement n'est rendu asynchrone que lorsqu'il existe une vraie raison fonctionnelle ou technique.

### A8 — Évolution progressive

Les fonctionnalités avancées sont ajoutées lorsque le besoin métier est confirmé.

---

# 24. Architecture cible simplifiée

```text
┌────────────────────────────────────────────────────────────┐
│                         FRONTEND                           │
│                                                            │
│  Clients │ Sites │ Équipements │ Interventions │ Showroom │
└─────────────────────────────┬──────────────────────────────┘
                              │
                         HTTPS / JSON
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                           API                              │
│                                                            │
│  Auth │ Clients │ Sites │ Equipment │ Interventions       │
│       │ Catalogue │ Commercial │ Reports │ Documents       │
└─────────────────────────────┬──────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
             ┌─────────────┐     ┌──────────────┐
             │ PostgreSQL  │     │   Storage    │
             │             │     │              │
             │ Données     │     │ Photos       │
             │ métier      │     │ PDF          │
             └─────────────┘     │ Documents    │
                                 └──────────────┘
```

Cette architecture constitue la base technique de Tervo sans imposer prématurément des mécanismes complexes.

Les détails du modèle relationnel, des contraintes et des relations sont définis dans le modèle de données.
