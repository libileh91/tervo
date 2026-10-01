# Tervo — Plan de refactorisation vers un monolithe modulaire

> **Statut :** plan final de chantier backend  
> **Base vérifiée :** `libileh91/tervo`, `main` au 30/09/2026  
> **Baseline Git :** `544a23d6cb2cbe878fbc8ddf2d962c7adf76c000`  
> **Point de départ fonctionnel :** Sprint 7.3 terminé et poussé ; `Sale`, `SaleLine` et `Installation` sont maintenant dans le code.  
> **Important :** l'historique Git ayant été réécrit, les anciens SHA ne doivent plus servir de baseline de comparaison.
> **Avancement du chantier :** R0 à R7 validés et committés sur `refactor/modular-monolith` ; dernier commit : `7a52d03` (interventions), naming documentaire : `8f3e876`. R8 / INT-120 vérifié localement et accepté : [note et preuve](../refactor-monolithe-modulaire/INT-120-R8-reports.md), [planning technique](../../../docs/stages/stage7/refactor-monolithe-modulaire/README.md). Commit R8 autorisé, feu vert distinct R9 reçu ; R10 à R11 non commencées. La [baseline R0](refactor-monolithe-modulaire/R0-baseline.md) et l'écart FK technicien sont conservés sans correction.

### Décision de naming

`app/modules` est conservé. Le package Python `catalog` (anglais américain) remplace `catalogue` : `app/modules/catalog` et `app.modules.catalog`. Les routes `/products`, noms de classes et `catalogue_editor` restent inchangés, comme le vocabulaire métier français « catalogue ». Aucun renommage rétroactif des captures JSON R0/R1/R2 ni réécriture Git. La capture R3 avant naming reste conservée ; la section `post_naming` du manifeste contient les validations et empreintes finales. Le choix documentaire est enregistré dans `8f3e876`, puis le cutover applicatif et sa validation dans le commit de livraison R3.

---

## 1. Objectif

Le backend Tervo est aujourd'hui organisé principalement **par couches techniques** :

```text
backend/app/
├── api/v1/
├── models/
├── repositories/
├── schemas/
├── services/
├── importers/
├── exporters/
└── core/
```

Cette organisation fonctionne, mais un même métier est dispersé dans plusieurs dossiers.
Exemple : `Client` existe dans `models/client.py`, `schemas/client.py`,
`repositories/client.py`, `services/client.py` et `api/v1/clients.py`.

Le but du chantier est de passer à un :

> **monolithe modulaire orienté domaines** (*domain-oriented modular monolith*)

avec des frontières suffisamment propres pour permettre une extraction future en microservice si un besoin réel apparaît, **sans introduire aujourd'hui la complexité des microservices**.

Principe directeur :

> **Créer des frontières de microservices dans le code avant de créer des microservices dans l'infrastructure.**

Tervo reste :

- un seul backend FastAPI ;
- un seul processus applicatif ;
- une seule base PostgreSQL ;
- un seul système d'authentification ;
- un seul déploiement backend.

---

## 2. État actuel vérifié après Sprint 7.3

La structure horizontale est toujours présente, mais le métier couvert est plus large qu'au moment de la première version de ce plan.

Le code courant contient notamment :

```text
api/v1/
├── clients.py
├── sites.py
├── products.py
├── equipment.py
├── sales.py
├── installations.py
├── interventions.py
├── checklist.py
├── photos.py
├── materials.py
├── reports.py
├── reviews.py
├── imports.py
├── auth.py
└── dashboard.py
```

Les modèles principaux présents sont désormais :

```text
Client
Site
Product
Sale
SaleLine
Installation
Equipment
Intervention
ChecklistItem
InterventionPhoto
Material
Review
User
ImportBatch / ImportRecord / ImportReference / ImportError
```

Sprint 7.3 a donc changé une hypothèse importante du premier plan :

```text
Sale / SaleLine       = maintenant implémentés
Installation          = maintenant implémentée
sale_line_id          = FK nullable réelle
Equipment.installation_id = FK nullable réelle
```

Ils ne doivent plus être décrits comme des modules « futurs ».

### Point documentaire à ne pas mélanger au refactor

Certains fichiers de suivi du Stage 7 indiquent encore que des validations PostgreSQL de 7.3 sont à exécuter, alors que le code, l'historique réécrit et le statut donné pour ce chantier considèrent 7.3 terminé.

Ce décalage documentaire est à nettoyer séparément si nécessaire. **Le refactor architectural ne doit pas profiter de cette divergence pour modifier les règles métier ou les résultats de tests.**

---

## 3. Pourquoi ce checkpoint est intéressant

Le moment est particulièrement adapté au refactor :

```text
Sprint 7.1  Socle physique       ✅
Sprint 7.2  Migration Excel      ✅
Sprint 7.3  Chaîne commerciale   ✅
Sprint 7.4  Cycle terrain        prochain gros chantier
```

Le Sprint 7.4 doit précisément remodeler :

- checklist ;
- photos ;
- matériel utilisé ;
- clôture d'intervention ;
- rapports versionnés ;
- avis.

Faire le découpage modulaire **avant** de commencer 7.4 évite de développer de nouvelles fonctionnalités dans l'ancienne organisation pour les déplacer juste après.

Recommandation :

> soit faire ce refactor maintenant, avant 7.4 ;  
> soit attendre la fin complète de 7.4.  
> Éviter de faire les deux chantiers simultanément sur les mêmes fichiers.

---

## 4. Ce que le refactor doit préserver

La première passe est **structurelle**.

Le chantier ne doit pas modifier volontairement :

- les URLs API ;
- les payloads Pydantic ;
- les statuts métier ;
- les noms de tables ;
- les noms de colonnes ;
- les clés étrangères ;
- les règles de transaction ;
- les contraintes Alembic ;
- le comportement du pipeline Excel ;
- le modèle métier du DAT.

Un déplacement de fichier Python ne doit pas produire une migration SQL.

### Hors périmètre explicite

Ne pas ajouter pendant ce chantier :

- Kafka / RabbitMQ ;
- message bus ;
- event bus généralisé ;
- listeners métier ;
- CQRS ;
- saga ;
- transaction distribuée ;
- base de données par module ;
- appels HTTP internes entre modules ;
- framework de dependency injection ;
- interfaces abstraites pour tous les repositories ;
- séparation en plusieurs conteneurs métier.

---

# 5. Modules métier cibles

Le découpage suit le **modèle métier réel du DAT** et le code effectivement présent après 7.3.

## 5.1 `identity`

Responsabilités :

```text
User
Authentication
Authorization applicative liée à l'utilisateur
```

À déplacer :

```text
models/user.py
schemas/auth.py
api/v1/auth.py
```

`core/security.py` reste dans `core` tant qu'il ne contient que des primitives génériques : JWT, hash de mot de passe, vérification de token, etc.

---

## 5.2 `customers`

Responsabilités :

```text
Client
  └── Site
```

Le couple Client/Site reste dans le même module : le site est le lieu physique rattaché au client et constitue la racine de nombreux parcours Tervo.

À déplacer :

```text
models/client.py
models/site.py
schemas/client.py
schemas/site.py
repositories/client.py
repositories/site.py
services/client.py
services/site.py
api/v1/clients.py
api/v1/sites.py
```

---

## 5.3 `catalog`

Responsabilité :

```text
Product
```

Le catalogue décrit une **référence commerciale**, pas un objet physique installé.

À déplacer :

```text
models/product.py
schemas/product.py
repositories/product.py
services/product.py
api/v1/products.py
```

---

## 5.4 `sales`

Responsabilités :

```text
Sale
└── SaleLine
```

Nom recommandé : **`sales`** plutôt que `commercial`.

Raison : le module courant possède aujourd'hui un périmètre précis — vente et lignes de vente. Le futur showroom possède son propre workflow et ne doit pas être absorbé artificiellement dans un gros module `commercial`.

À déplacer :

```text
models/sale.py
schemas/sale.py
services/sale.py
api/v1/sales.py
```

Il n'existe pas actuellement de repository dédié aux ventes. **Ne pas en créer un uniquement pour obtenir une arborescence symétrique pendant le move.**

Un repository pourra être extrait plus tard si le service devient réellement trop chargé en accès SQL.

---

## 5.5 `equipment`

Responsabilité : le cycle de vie de l'équipement physique.

```text
Site
  └── Equipment
```

À déplacer :

```text
models/equipment.py
schemas/equipment.py
repositories/equipment.py
services/equipment.py
api/v1/equipment.py
```

Invariants à préserver :

- `Equipment` reste distinct de `Product` ;
- pas de statut `PLANNED` ;
- `installation_id` reste nullable pour l'historique ;
- `replaced_by_id` conserve l'ancien équipement et pointe vers le nouveau ;
- l'équipement historique reste valide même sans installation enregistrée.

---

## 5.6 `installations`

Responsabilité : l'événement technique d'installation.

```text
SaleLine 0..1
     │
     ▼
Installation
     │
     └── 0..1 Equipment
```

À déplacer :

```text
models/installation.py
schemas/installation.py
repositories/installation.py
services/installation.py
api/v1/installations.py
```

Invariants Sprint 7.3 à préserver :

- installation autonome possible ;
- `sale_line_id` nullable ;
- aucune vente fictive pour le matériel du client ;
- une vente renseignée doit être confirmée ;
- cohérence site / produit / quantité ;
- clôture atomique Installation + Equipment ;
- `Installation 1 → 0..1 Equipment` ;
- équipements historiques non réécrits.

---

## 5.7 `interventions`

C'est le contexte opérationnel terrain.

Aujourd'hui, il regroupe naturellement :

```text
Intervention
├── Checklist
├── Photos
├── Matériel utilisé
└── Avis
```

À rapprocher :

```text
models/intervention.py
models/checklist_item.py
models/intervention_photo.py
models/material.py
models/review.py

repositories/intervention.py
repositories/checklist.py
repositories/photo.py
repositories/material.py
repositories/review.py

services/intervention.py
services/checklist.py
services/photo.py
services/material.py
services/review.py

api/v1/interventions.py
api/v1/checklist.py
api/v1/photos.py
api/v1/materials.py
api/v1/reviews.py
```

### Important pour Sprint 7.4

Le refactor doit déplacer **l'existant tel quel**.

Il ne doit pas anticiper pendant le move les futures transformations :

```text
ChecklistItem plat
    ↓ Sprint 7.4
ChecklistTemplate + InterventionChecklist + ChecklistItem snapshot

InterventionPhoto
    ↓ Sprint 7.4
Photo

Material
    ↓ Sprint 7.4
MaterialUsage
```

Ces changements appartiennent à INT-104/105 et restent des évolutions métier distinctes.

---

## 5.8 `reports`

Responsabilités actuelles :

- API de rapport ;
- génération PDF ;
- rendu HTML ;
- template WeasyPrint.

À déplacer :

```text
api/v1/reports.py
exporters/report.py
exporters/report_template.html
```

Cible simple :

```text
modules/reports/
├── api.py
├── service.py          # si nécessaire
├── renderer.py
└── templates/
    └── report.html
```

Sprint 7.4 introduira ensuite `Report` + `ReportVersion`. Ne pas inventer ces modèles dans le refactor lui-même.

---

## 5.9 `imports`

Le pipeline d'import historique est transverse, mais il possède assez de logique et de cycle de vie pour être un module à part entière.

Il possède :

```text
ImportBatch
ImportRecord
ImportReference
ImportError
```

et le pipeline :

```text
ExcelReader
FormatDetector
Normalizer
Validators
Matcher / MultiLevelMatcher
ImportPlanner
ImportService
```

À déplacer :

```text
api/v1/imports.py
models/import_batch.py
schemas/imports.py
services/import_planner.py
services/import_service.py
importers/*
```

Le module `imports` **orchestre** les domaines métier ; il ne devient pas propriétaire de leurs entités.

Pipeline métier principal :

```text
Client → Site → Equipment → Intervention
                    + Product lorsque disponible
```

Les ventes et installations ne deviennent pas obligatoires pour importer l'historique.

---

## 5.10 `dashboard`

Le dashboard est un module de lecture transverse, pas un domaine propriétaire.

```text
dashboard/
├── schemas.py       # si nécessaire
├── service.py       # agrégation de lecture
└── api.py
```

Il peut consulter plusieurs modules, mais ne doit contenir aucune règle métier qui appartient à `customers`, `equipment`, `sales`, etc.

---

# 6. Modules futurs — ne pas créer maintenant

Après 7.3, les modules réellement futurs sont surtout :

```text
showroom/
documents/      # seulement si un vrai domaine documentaire apparaît
```

`showroom` arrivera avec Sprint 7.5 autour de :

```text
ShowroomVisit
ShowroomVisitProduct
```

Ne pas créer de dossier vide pour anticiper cette livraison.

---

# 7. Structure cible

```text
backend/app/
├── __init__.py
├── main.py
├── config.py
├── router.py
├── model_registry.py
│
├── core/
│   ├── database.py
│   ├── deps.py
│   └── security.py
│
└── modules/
    ├── identity/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── service.py          # uniquement si utile
    │   └── api.py
    │
    ├── customers/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── repository.py
    │   ├── service.py
    │   └── api.py
    │
    ├── catalog/
    ├── sales/
    ├── equipment/
    ├── installations/
    ├── interventions/
    ├── reports/
    ├── imports/
    │   └── pipeline/
    └── dashboard/
```

### Pas de symétrie artificielle

Chaque module **n'est pas obligé** d'avoir tous les fichiers suivants :

```text
models.py
schemas.py
repository.py
service.py
api.py
```

La règle est :

> créer le fichier parce qu'il contient une responsabilité réelle, pas pour remplir un template.

Exemple concret : `sales` n'a actuellement pas de repository dédié ; le refactor initial ne doit pas en inventer un uniquement pour « faire propre ».

---

# 8. Composition FastAPI

Aujourd'hui `app/main.py` importe directement de nombreux routers.

Après refactor, conserver une composition explicite, simple :

```python
# app/router.py
from fastapi import APIRouter

from app.modules.customers.api import router as customers_router
from app.modules.catalog.api import router as catalog_router
from app.modules.sales.api import router as sales_router
from app.modules.equipment.api import router as equipment_router
from app.modules.installations.api import router as installations_router

api_router = APIRouter()
api_router.include_router(customers_router)
api_router.include_router(catalog_router)
api_router.include_router(sales_router)
api_router.include_router(equipment_router)
api_router.include_router(installations_router)
```

Puis `main.py` reste principalement du wiring :

```python
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
```

Ne pas utiliser :

- découverte automatique des routers par filesystem ;
- import dynamique ;
- registry magique de plugins.

---

# 9. Règles de dépendances

## 9.1 API → service local

```text
module/api.py
    ↓
module/service.py
    ↓
module/repository.py
```

Une route ne doit pas absorber la logique métier.

---

## 9.2 Repository local au module

À éviter :

```python
# installations/service.py
from app.modules.customers.repository import ClientRepository
```

Préférer un contrat de module plus haut niveau lorsque cela apporte réellement quelque chose :

```python
from app.modules.customers.service import CustomerService
```

Cependant le refactor initial ne doit pas réécrire toutes les requêtes SQL uniquement pour atteindre cet idéal.

---

## 9.3 Service → service autorisé

Dans ce monolithe :

```text
InstallationService
      ↓
EquipmentService
```

est parfaitement acceptable.

Pas besoin d'événement ou de bus.

---

## 9.4 Foreign keys inter-modules autorisées

Exemples normaux :

```text
Site.client_id                → Client.id
Sale.site_id                  → Site.id
SaleLine.product_id           → Product.id
Installation.sale_line_id     → SaleLine.id
Equipment.installation_id     → Installation.id
Equipment.site_id             → Site.id
Intervention.equipment_id     → Equipment.id
```

Une base partagée et des FK réelles sont un choix cohérent pour un monolithe modulaire.

---

## 9.5 Sens de dépendances métier

Vue simplifiée :

```text
identity  ─────────────► garde d'accès des APIs

customers       catalog
    │               │
    ├──────┐   ┌────┘
    ▼      ▼   ▼
   sales  equipment
      │      ▲
      ▼      │
 installations
      │
      └─────────────► equipment

customers / equipment
          │
          ▼
   interventions
          │
          ▼
       reports

imports ─────► customers / catalog / equipment / interventions

dashboard ───► lectures transverses
```

Les relations ORM croisées ne doivent pas provoquer une architecture de services circulaire.

---

# 10. SQLAlchemy et Alembic

C'est un point critique du chantier.

Aujourd'hui :

```text
app/models/base.py
app/models/__init__.py
alembic/env.py → from app.models.base import Base
```

Après déplacement, Alembic doit charger explicitement tous les modèles avant de lire `Base.metadata`.

## Cible

Conserver une Base technique commune :

```text
app/core/database.py        # session / engine
app/model_registry.py       # import explicite des modèles ORM
```

Exemple conceptuel :

```python
# app/model_registry.py
from app.modules.identity.models import User
from app.modules.customers.models import Client, Site
from app.modules.catalog.models import Product
from app.modules.sales.models import Sale, SaleLine
from app.modules.installations.models import Installation
from app.modules.equipment.models import Equipment
from app.modules.interventions.models import Intervention
from app.modules.imports.models import ImportBatch, ImportRecord, ImportReference, ImportError
```

Puis `alembic/env.py` importe ce registre pour ses effets de chargement avant :

```python
target_metadata = Base.metadata
```

### Invariant obligatoire

Après chaque déplacement de module :

```text
alembic check / autogenerate inspecté
→ aucune DROP/CREATE artificielle causée par les imports Python
```

Ne jamais accepter une migration SQL uniquement parce qu'un modèle a changé de package.

---

# 11. Transactions

Ne pas introduire un `UnitOfWork` généralisé pendant ce chantier.

Conserver :

```text
FastAPI dependency
      ↓
AsyncSession
      ↓
Service
      ↓
Repository / SQLAlchemy
```

Les workflows transverses continuent à partager la même `AsyncSession` lorsqu'ils doivent être atomiques.

Exemples critiques à préserver :

```text
Installation.complete
→ Installation + Equipment dans la même transaction

ImportService
→ sous-lots transactionnels et reprise cohérente
```

---

# 12. Plan de refactorisation

Le terme **vague** est conservé afin de ne pas confondre ce chantier technique avec les Lots fonctionnels et les Sprints 7.x.

Chaque vague doit laisser `main` ou la branche de refactor dans un état exécutable et testable.

---

## R0 — Figer la baseline actuelle

### Objectif

Créer un point de comparaison fiable après la réécriture de l'historique Git.

### Actions

- partir du `main` actuel ;
- enregistrer le SHA baseline : `544a23d6cb2cbe878fbc8ddf2d962c7adf76c000` ;
- créer une branche dédiée au refactor ;
- éventuellement créer un tag local/poussé du type `pre-modular-refactor` ;
- lancer la suite backend complète ;
- lancer les groupes PostgreSQL applicables ;
- lancer Alembic sur une base jetable ;
- démarrer FastAPI ;
- sauvegarder l'OpenAPI courant si utile ;
- noter les résultats réellement observés.

### Règle Git après réécriture

Ne pas utiliser comme référence les anciens SHA antérieurs à la réécriture.

À partir de cette baseline :

> **pas de nouvelle réécriture d'historique pendant le refactor sauf demande explicite.**

### Critère de sortie

```text
baseline SHA connue
suite de tests connue
API démarre
Alembic fonctionne
aucune modification métier
```

---

## R1 — Créer le squelette modulaire

Créer uniquement :

```text
app/modules/
app/router.py
app/model_registry.py
```

Ne pas créer dix dossiers vides « pour préparer la suite ».

Le registre de modèles doit pouvoir cohabiter temporairement avec l'ancienne structure.

---

## R2 — `customers`

Premier module pilote :

```text
Client + Site
```

Pourquoi :

- racine du modèle métier ;
- périmètre maîtrisable ;
- repositories et services déjà présents ;
- beaucoup de relations aval permettent de valider immédiatement les imports inter-modules.

Sortie :

```text
routes identiques
schéma DB identique
tests Client/Site verts
Alembic sans diff structurelle
anciens fichiers supprimés après cutover
```

---

## R3 — `catalog`

Déplacer verticalement :

```text
Product
schema
repository
service
API
```

Préserver la séparation :

```text
Product ≠ Equipment
```

---

## R4 — `sales`

Déplacer :

```text
Sale
SaleLine
schemas
SaleService
sales API
```

Ne pas profiter du move pour introduire un repository qui n'existe pas encore.

Tests critiques :

- création brouillon ;
- confirmation avec au moins une ligne ;
- annulation ;
- `quantity > 0` ;
- prix Decimal/Numeric ;
- cohérence Client/Site ;
- produit existant.

---

## R5 — `equipment`

Déplacer le domaine physique avant l'orchestrateur Installation.

Tests critiques :

- FK Site/Product ;
- cycle de vie ;
- `installation_id` nullable ;
- lien de remplacement ;
- historique non détruit.

---

## R6 — `installations`

Déplacer le périmètre livré par Sprint 7.3 :

```text
Installation
schemas
repository
service
API
```

Tests critiques :

- parcours autonome ;
- parcours avec SaleLine ;
- vente confirmée ;
- limite de quantité ;
- cohérence site/produit ;
- création/rattachement Equipment atomique ;
- rollback ;
- concurrence ;
- conservation des historiques.

Cette vague doit fournir **exactement** les mêmes comportements qu'avant le refactor.

---

## R7 — `interventions`

Déplacer ensemble le contexte terrain existant :

```text
Intervention
ChecklistItem
InterventionPhoto
Material
Review
```

et leurs couches associées.

### Règle importante

Ne pas implémenter INT-104 à INT-108 dans cette vague.

Le but est uniquement de donner au Sprint 7.4 une nouvelle maison propre :

```text
modules/interventions/
```

Une fois R7 mergée, les chemins décrits dans `sprint7.4/tasks.md` devront être ajustés aux nouveaux packages avant de commencer les évolutions métier.

---

## R8 — `reports`

Déplacer :

```text
reports API
ReportExporter
template HTML
```

Le futur versionnement `Report / ReportVersion` reste INT-107.

---

## R9 — `imports`

Déplacer le pipeline Excel en dernier parmi les domaines métier principaux, car il orchestre plusieurs modules déjà déplacés.

Cible :

```text
modules/imports/
├── models.py
├── schemas.py
├── service.py
├── api.py
└── pipeline/
    ├── excel_reader.py
    ├── format_detector.py
    ├── ingestion.py
    ├── normalizer.py
    ├── validators.py
    ├── matcher.py
    ├── multi_matcher.py
    ├── planner.py
    └── report.py
```

À préserver absolument :

- fichiers source intacts ;
- `.xlsx` / `.csv` ;
- multi-feuilles ;
- provenance fichier / feuille / ligne ;
- valeurs brutes et normalisées ;
- validations ;
- rapprochement multi-niveaux ;
- décisions explicites ;
- SHA-256 ;
- plan validé avant exécution ;
- reprise ;
- sérialisation / verrouillage existants ;
- transactions par sous-lots ;
- erreurs/orphelins tracés ;
- Equipment historique sans Installation ;
- Intervention historique sans Equipment lorsque nécessaire.

### Test de non-régression recommandé

Utiliser le même pack d'import avant/après et comparer :

```text
ImportBatch
ImportRecord
ImportReference
ImportError
clients créés/rattachés
sites créés/rattachés
équipements créés/rattachés
interventions créées/rattachées
```

Le résultat fonctionnel doit rester identique.

---

## R10 — `identity`, `dashboard`, seed et composition finale

### `identity`

Déplacer User/Auth, en gardant les primitives techniques dans `core`.

### `dashboard`

Déplacer l'agrégation de lecture transverse.

### Seed

Le seed peut rester temporairement dans `app/seed.py` si son déplacement n'apporte rien.

Si déplacé :

```text
backend/scripts/seed.py
```

mais sans créer une deuxième implémentation des règles métier.

---

## R11 — Suppression de l'architecture horizontale legacy

Lorsque tout est réellement migré, supprimer les dossiers devenus inutiles :

```text
app/models/
app/repositories/
app/schemas/
app/services/
app/api/v1/
app/importers/
app/exporters/
```

Seulement s'ils sont effectivement vides et qu'aucun code ne les référence encore.

Recherche finale obligatoire :

```text
app.models
app.repositories
app.schemas
app.services
app.api.v1
app.importers
app.exporters
```

Puis :

- tests ;
- Alembic ;
- démarrage FastAPI ;
- contrôle OpenAPI ;
- parcours frontend critiques.

---

# 13. Stratégie Git adaptée au dépôt actuel

L'historique vient d'être réécrit et le dépôt utilise désormais des commits par tâche.

Le refactor ne doit pas revenir à un énorme commit transversal.

## Recommandation

Créer une tâche technique par vague ou groupe de vagues, puis suivre la convention du projet :

```text
[DEV]INT-XXX — Refactor : introduire le squelette modulaire
[DEV]INT-XXX — Refactor : déplacer le domaine customers
[DEV]INT-XXX — Refactor : déplacer le catalogue
[DEV]INT-XXX — Refactor : déplacer les ventes
[DEV]INT-XXX — Refactor : déplacer équipements et installations
[DEV]INT-XXX — Refactor : déplacer le domaine interventions
[DEV]INT-XXX — Refactor : consolider le module imports
[DEV]INT-XXX — Refactor : supprimer les couches horizontales legacy
```

Les numéros exacts doivent être attribués dans le planning avant exécution ; ne pas inventer un INT déjà utilisé.

Chaque tâche/commit doit contenir :

- move de fichiers ;
- corrections d'imports ;
- tests adaptés ;
- éventuelle note pédagogique ;
- aucune évolution métier cachée.

### À éviter

```text
refactor entire backend
```

avec 80 fichiers déplacés et aucune frontière de validation intermédiaire.

---

# 14. Règles pour l'agent

1. Lire le DAT et les tâches Stage 7 avant de définir une frontière.
2. Considérer Sprint 7.3 comme partie de la baseline : `sales` et `installations` existent réellement.
3. Ne pas utiliser d'anciens SHA Git comme référence après la réécriture de l'historique.
4. Ne pas mélanger refactor structurel et évolution métier.
5. Conserver les URLs et payloads existants.
6. Ne pas renommer les tables ou colonnes pendant un move.
7. Ne pas produire de migration Alembic pour un changement de package Python.
8. Déplacer verticalement un métier : model + schema + repository/service/API réellement existants + tests.
9. Ne pas créer un repository, une interface ou une abstraction uniquement pour obtenir une structure symétrique.
10. Supprimer l'ancien fichier après cutover ; ne pas garder deux implémentations actives.
11. Les appels Python service → service sont autorisés.
12. Les FK SQL entre modules sont autorisées.
13. Ne pas introduire bus, listeners, CQRS ou HTTP interne.
14. Garder `core` strictement technique.
15. Préserver les transactions d'Installation et d'Import.
16. Tester Alembic après chaque déplacement de modèles.
17. Tester les routes du module après chaque vague.
18. Pour `imports`, comparer un jeu fixe avant/après.
19. Pour `interventions`, ne pas anticiper INT-104 à INT-108 pendant le move.
20. Si un vrai bug apparaît, séparer autant que possible son correctif du commit de déplacement.
21. Ne pas réécrire à nouveau l'historique publié sans demande explicite.

---

# 15. Definition of Done globale

```text
[x] baseline actuelle enregistrée après la réécriture Git
[ ] chaque domaine actif possède une frontière explicite dans app/modules/
[x] customers est isolé
[x] catalog est isolé (vérifié avant et après naming)
[x] sales est isolé
[x] equipment est isolé
[x] installations est isolé
[x] interventions est isolé
[x] reports est isolé
[ ] imports est isolé
[ ] identity est isolé
[ ] dashboard reste une lecture transverse
[ ] core ne contient que des préoccupations techniques
[ ] aucune couche horizontale métier legacy n'est encore utilisée
[ ] aucun endpoint public n'a changé involontairement
[ ] aucun payload public n'a changé involontairement
[ ] schéma PostgreSQL inchangé par le refactor
[ ] Alembic découvre tous les modèles
[ ] migrations existantes restent fonctionnelles
[ ] tests backend passent
[ ] tests PostgreSQL critiques passent
[ ] FastAPI démarre
[ ] OpenAPI ne présente pas de régression involontaire
[ ] scénario Migration Excel identique avant/après
[ ] parcours Installation autonome identique avant/après
[ ] parcours SaleLine → Installation → Equipment identique avant/après
[ ] aucun bus/listener/microservice artificiel ajouté
[ ] documentation Stage 7 utilise les nouveaux chemins avant Sprint 7.4
```

---

# 16. Architecture cible

```text
                               FastAPI
                                  │
                                  ▼
                        ┌──────────────────┐
                        │    router.py     │
                        └────────┬─────────┘
                                 │
       ┌───────────────┬─────────┼──────────┬───────────────┐
       ▼               ▼         ▼          ▼               ▼
  customers        catalog      sales   installations    identity
       │               │          │          │
       └──────┬────────┘          └────┬─────┘
              ▼                        ▼
          equipment ◄──────────────────┘
              │
              ▼
        interventions
              │
              ▼
           reports

 imports ─────► customers / catalog / equipment / interventions
 dashboard ───► lectures transverses

              tous les modules
                    │
                    ▼
               PostgreSQL
```

---

# 17. Résultat recherché

À la fin du chantier, un développeur ou un agent doit pouvoir ouvrir :

```text
app/modules/installations/
```

et trouver immédiatement tout ce qui concerne ce métier, sans parcourir cinq dossiers globaux.

Même logique pour :

```text
customers
catalog
sales
equipment
interventions
imports
```

Le code gagne ainsi :

- en lisibilité ;
- en ownership métier ;
- en capacité de test ciblé ;
- en facilité de maintenance ;
- en compréhension pour l'entretien ;
- en possibilité d'extraction future.

Sans payer aujourd'hui le coût opérationnel d'une architecture distribuée.

> **Cible : monolithe modulaire aujourd'hui, extraction possible demain seulement si un besoin concret la justifie.**
