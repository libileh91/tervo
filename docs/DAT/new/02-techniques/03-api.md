# Tervo — API

> Spécification initiale de l'API HTTP de Tervo.
>
> L'API expose les capacités métier nécessaires au frontend et aux futurs clients de Tervo.
>
> Le document définit les ressources, opérations et règles principales sans figer prématurément chaque détail d'implémentation.

---

# 1. Principes

L'API Tervo respecte les principes suivants :

* HTTP/JSON ;
* API versionnée ;
* ressources métier explicites ;
* validation côté backend ;
* erreurs structurées ;
* pagination pour les collections ;
* filtres métier ;
* contrôle d'autorisation côté backend ;
* aucune dépendance du frontend à la structure interne de la base.

Version initiale :

```text
/api/v1
```

---

# 2. Organisation générale

Les ressources principales sont :

```text
/api/v1
├── auth
├── users
├── clients
├── sites
├── products
├── sales
├── installations
├── equipment
├── interventions
├── checklists
├── reports
├── reviews
├── showroom
└── files
```

Toutes les ressources ne sont pas nécessairement exposées en CRUD complet.

L'API doit privilégier les opérations correspondant à de vraies actions métier.

---

# 3. Authentification

## 3.1 Connexion

```http
POST /api/v1/auth/login
```

Exemple :

```json
{
  "email": "technicien@example.com",
  "password": "********"
}
```

Réponse conceptuelle :

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "...",
    "name": "Jean Dupont",
    "role": "TECHNICIAN"
  }
}
```

---

## 3.2 Utilisateur courant

```http
GET /api/v1/auth/me
```

Retourne l'utilisateur authentifié et ses informations principales.

---

# 4. Clients

## 4.1 Liste

```http
GET /api/v1/clients
```

Filtres possibles :

```text
search
type
page
limit
```

Exemple :

```http
GET /api/v1/clients?search=Dupont&page=1&limit=20
```

---

## 4.2 Création

```http
POST /api/v1/clients
```

Exemple :

```json
{
  "type": "PERSON",
  "name": "Jean Dupont",
  "email": "jean@example.com",
  "phone": "0600000000"
}
```

---

## 4.3 Consultation

```http
GET /api/v1/clients/{client_id}
```

---

## 4.4 Modification

```http
PATCH /api/v1/clients/{client_id}
```

Les modifications doivent respecter les règles d'autorisation.

---

## 4.5 Sites d'un client

```http
GET /api/v1/clients/{client_id}/sites
```

---

# 5. Sites

## 5.1 Liste

```http
GET /api/v1/sites
```

Filtres :

```text
client_id
city
postal_code
search
page
limit
```

---

## 5.2 Création

```http
POST /api/v1/sites
```

Exemple :

```json
{
  "client_id": "...",
  "name": "Maison principale",
  "address": "10 rue Exemple",
  "postal_code": "91300",
  "city": "Massy"
}
```

---

## 5.3 Consultation

```http
GET /api/v1/sites/{site_id}
```

La réponse peut inclure les informations synthétiques :

```text
client
equipment_count
open_intervention_count
```

sans retourner systématiquement tout l'historique.

---

## 5.4 Équipements du site

```http
GET /api/v1/sites/{site_id}/equipment
```

---

## 5.5 Interventions du site

```http
GET /api/v1/sites/{site_id}/interventions
```

---

# 6. Catalogue produits

## 6.1 Liste

```http
GET /api/v1/products
```

Filtres :

```text
search
brand
category
active
page
limit
```

---

## 6.2 Création

```http
POST /api/v1/products
```

---

## 6.3 Consultation

```http
GET /api/v1/products/{product_id}
```

---

## 6.4 Modification

```http
PATCH /api/v1/products/{product_id}
```

---

## 6.5 Désactivation

Un produit historique ne doit pas nécessairement être supprimé.

```http
POST /api/v1/products/{product_id}/deactivate
```

Le produit reste disponible pour l'historique mais n'est plus proposé comme référence active.

---

# 7. Ventes

## 7.1 Liste

```http
GET /api/v1/sales
```

Filtres :

```text
client_id
status
date_from
date_to
page
limit
```

---

## 7.2 Création

```http
POST /api/v1/sales
```

Exemple :

```json
{
  "client_id": "...",
  "site_id": "...",
  "sale_date": "2026-09-20",
  "lines": [
    {
      "product_id": "...",
      "quantity": 1,
      "unit_price": 8500
    },
    {
      "product_id": "...",
      "quantity": 1,
      "unit_price": 250
    }
  ]
}
```

La création d'une vente et de ses lignes constitue une seule opération métier.

---

## 7.3 Consultation

```http
GET /api/v1/sales/{sale_id}
```

La réponse peut inclure :

```text
client
site
lines
installations
```

---

## 7.4 Confirmation

```http
POST /api/v1/sales/{sale_id}/confirm
```

Une vente confirmée ne doit pas pouvoir être modifiée librement comme un brouillon.

Les règles précises de modification seront définies lors de l'implémentation.

---

## 7.5 Annulation

```http
POST /api/v1/sales/{sale_id}/cancel
```

Une annulation doit respecter les contraintes liées aux installations déjà réalisées.

---

# 8. Installations

L'installation constitue une ressource métier distincte de la vente.

## 8.1 Liste

```http
POST /installations/{id}/start
POST /installations/{id}/complete
POST /installations/{id}/cancel
GET /api/v1/installations
```

Filtres :

```text
site_id
status
date_from
date_to
technician_id
```

---

## 8.2 Création / planification

```http
POST /api/v1/installations
```

Exemple :

```json
{
  "sale_line_id": "...",
  "site_id": "...",
  "scheduled_date": "2026-10-15"
}
```

---

## 8.3 Démarrage

```http
POST /api/v1/installations/{installation_id}/start
```

Transition :

```text
SCHEDULED
   ↓ start
IN_PROGRESS
   ↓ complete
COMPLETED
   +
Equipment → créé/rattaché
```

---

## 8.4 Finalisation

```http
POST /api/v1/installations/{installation_id}/complete
```

La finalisation doit permettre de renseigner les informations réelles de l'installation.

Exemple :

```json
{
  "installation_date": "2026-10-15",
  "commissioning_date": "2026-10-15",
  "serial_number": "ABC123456",
  "warranty_start": "2026-10-15",
  "warranty_end": "2030-10-15"
}
```

La finalisation crée ou associe l'équipement correspondant.

---

# 9. Équipements

L'équipement constitue une ressource centrale de l'API.

## 9.1 Liste

```http
GET /api/v1/equipment
```

Filtres :

```text
client_id
site_id
product_id
serial_number
lifecycle_status
search
page
limit
```

---

## 9.2 Consultation

```http
GET /api/v1/equipment/{equipment_id}
```

La réponse doit permettre d'obtenir rapidement :

```text
product
client
site
installation
warranty
lifecycle status
```

---

## 9.3 Historique

```http
GET /api/v1/equipment/{equipment_id}/history
```

Cette route constitue une vue métier importante.

Elle peut regrouper :

```text
installation
interventions
reports
replacement
```

Exemple :

```json
{
  "equipment": {
    "id": "...",
    "serial_number": "ABC123456"
  },
  "history": [
    {
      "type": "INSTALLATION",
      "date": "2026-03-12"
    },
    {
      "type": "INTERVENTION",
      "date": "2026-06-10",
      "intervention_type": "PREVENTIVE_MAINTENANCE"
    },
    {
      "type": "INTERVENTION",
      "date": "2026-09-05",
      "intervention_type": "TROUBLESHOOTING"
    }
  ]
}
```

---

## 9.4 Interventions

```http
GET /api/v1/equipment/{equipment_id}/interventions
```

---

## 9.5 Remplacement

Le remplacement est une action métier.

```http
POST /api/v1/equipment/{equipment_id}/replace
```

Exemple :

```json
{
  "new_product_id": "...",
  "installation_date": "2026-10-15",
  "serial_number": "XYZ789"
}
```

L'ancien équipement passe dans un état historique.

Le nouvel équipement possède sa propre identité.

---

# 10. Interventions

## 10.1 Liste

```http
GET /api/v1/interventions
```

Filtres :

```text
status
result
type
client_id
site_id
equipment_id
technician_id
date_from
date_to
page
limit
```

Exemple :

```http
GET /api/v1/interventions?status=PLANNED&date_from=2026-09-21
```

---

# 11. Création d'une intervention

```http
POST /api/v1/interventions
```

Exemple :

```json
{
  "site_id": "...",
  "equipment_id": "...",
  "type": "TROUBLESHOOTING",
  "scheduled_start": "2026-09-22T09:00:00",
  "scheduled_end": "2026-09-22T11:00:00",
  "description": "PAC ne produit plus suffisamment de chaleur",
  "technician_ids": ["..."],
  "under_warranty": false,
  "status": "PLANNED"
}
```

`equipment_id` peut être absent pour un diagnostic initial.

---

# 12. Consultation d'une intervention

```http
GET /api/v1/interventions/{intervention_id}
```

La réponse peut inclure :

```text
client
site
equipment
technicians
checklist
photos
materials
report
review
```

La réponse doit toutefois éviter de devenir excessivement lourde.

Des sous-ressources peuvent être utilisées pour les éléments volumineux.

---

# 13. Démarrage

```http
POST /api/v1/interventions/{intervention_id}/start
```

Transition :

```text
PLANNED
   ↓
IN_PROGRESS
```

Le backend enregistre `started_at`.

---

# 14. Finalisation

```http
POST /api/v1/interventions/{intervention_id}/complete
```

Exemple :

```json
{
  "result": "RESOLVED",
  "observations": "Pression corrigée et fonctionnement vérifié."
}
```

Le backend enregistre notamment :

```text
status = COMPLETED
completed_at = now
result = RESOLVED
```

---

# 15. Annulation

```http
POST /api/v1/interventions/{intervention_id}/cancel
```

Exemple :

```json
{
  "reason": "Client indisponible"
}
```

Une intervention annulée ne peut pas être démarrée normalement.

---

# 16. Techniciens

## 16.1 Affectation

```http
POST /api/v1/interventions/{intervention_id}/technicians
```

Exemple :

```json
{
  "user_id": "...",
  "role": "ASSISTANT"
}
```

## 16.2 Retrait

```http
DELETE /api/v1/interventions/{intervention_id}/technicians/{user_id}
```

Les règles d'autorisation doivent empêcher une modification non autorisée d'une intervention déjà clôturée.

---

# 17. Checklist

## 17.1 Modèles

```http
GET /api/v1/checklists/templates
```

```http
POST /api/v1/checklists/templates
```

```http
PATCH /api/v1/checklists/templates/{template_id}
```

Les modifications d'un modèle ne doivent pas modifier les checklists historiques.

---

# 18. Checklist d'une intervention

```http
GET /api/v1/interventions/{intervention_id}/checklist
```

Si nécessaire :

```http
POST /api/v1/interventions/{intervention_id}/checklist
```

La création peut sélectionner le modèle approprié automatiquement à partir du type d'intervention.

---

## 18.1 Mise à jour d'un élément

```http
PATCH /api/v1/interventions/{intervention_id}/checklist/items/{item_id}
```

Exemple :

```json
{
  "result": "OK",
  "comment": "Valeur dans la plage normale"
}
```

---

# 19. Photos

## 19.1 Liste

```http
GET /api/v1/interventions/{intervention_id}/photos
```

---

## 19.2 Upload

```http
POST /api/v1/interventions/{intervention_id}/photos
```

Format :

```text
multipart/form-data
```

Métadonnées :

```text
category
```

Exemple :

```text
category=ANOMALY
file=photo.jpg
```

---

## 19.3 Suppression

```http
DELETE /api/v1/interventions/{intervention_id}/photos/{photo_id}
```

La suppression d'une photo après transmission d'un rapport peut nécessiter des règles spécifiques afin de préserver l'intégrité documentaire.

---

# 20. Matériel

## 20.1 Liste

```http
GET /api/v1/interventions/{intervention_id}/materials
```

## 20.2 Ajout

```http
POST /api/v1/interventions/{intervention_id}/materials
```

Exemple :

```json
{
  "designation": "Filtre",
  "quantity": 1,
  "unit": "piece"
}
```

---

# 21. Rapports

## 21.1 Génération

```http
POST /api/v1/interventions/{intervention_id}/reports
```

Le backend :

1. vérifie l'intervention ;
2. vérifie les données nécessaires ;
3. génère le rapport ;
4. stocke le fichier ;
5. crée l'enregistrement du rapport.

---

## 21.2 Liste des rapports

```http
GET /api/v1/interventions/{intervention_id}/reports
```

---

## 21.3 Consultation

```http
GET /api/v1/reports/{report_id}
```

---

## 21.4 Téléchargement / affichage

```http
GET /api/v1/reports/{report_id}/file
```

L'accès doit être soumis aux permissions appropriées.

---

## 21.5 Transmission

Lorsque Tervo gérera l'envoi au client :

```http
POST /api/v1/reports/{report_id}/send
```

Cette opération pourra déclencher un traitement asynchrone.

Le rapport transmis doit rester identifiable comme la version effectivement envoyée.

---

# 22. Avis client

## 22.1 Création

```http
POST /api/v1/interventions/{intervention_id}/review
```

Exemple :

```json
{
  "rating": 5,
  "comment": "Intervention rapide et efficace."
}
```

Une intervention ne peut avoir qu'un seul avis selon le modèle V1.

---

## 22.2 Consultation

```http
GET /api/v1/interventions/{intervention_id}/review
```

---

# 23. Showroom

## 23.1 Visites

```http
GET /api/v1/showroom/visits
```

```http
POST /api/v1/showroom/visits
```

---

## 23.2 Consultation

```http
GET /api/v1/showroom/visits/{visit_id}
```

---

## 23.3 Produits présentés

```http
POST /api/v1/showroom/visits/{visit_id}/products
```

Exemple :

```json
{
  "product_id": "..."
}
```

---

## 23.4 Suivi

```http
PATCH /api/v1/showroom/visits/{visit_id}
```

Exemple :

```json
{
  "follow_up_status": "QUOTE_SENT"
}
```

---

# 24. Pagination

Toutes les collections potentiellement volumineuses doivent être paginées.

Exemple :

```http
GET /api/v1/interventions?page=2&limit=25
```

Réponse :

```json
{
  "items": [],
  "pagination": {
    "page": 2,
    "limit": 25,
    "total": 137,
    "pages": 6
  }
}
```

Les valeurs maximales de `limit` seront définies côté API.

---

# 25. Tri

Les collections importantes doivent permettre un tri contrôlé.

Exemple :

```http
GET /api/v1/interventions?sort=-scheduled_start
```

Le backend ne doit pas accepter arbitrairement n'importe quel champ comme critère de tri.

Une liste blanche de champs autorisés doit être utilisée.

---

# 26. Recherche

Les ressources principales doivent proposer une recherche adaptée à leur usage.

Exemple :

```http
GET /api/v1/clients?search=Dupont
```

```http
GET /api/v1/equipment?search=ABC123
```

```http
GET /api/v1/products?search=Daikin
```

La recherche avancée pourra évoluer ultérieurement.

---

# 27. Filtres d'intervention

La vue planning nécessitera notamment :

```text
status
type
technician_id
site_id
date_from
date_to
```

Exemple :

```http
GET /api/v1/interventions
    ?status=PLANNED
    &technician_id=...
    &date_from=2026-09-21
    &date_to=2026-09-27
```

---

# 28. Transitions métier

Les transitions importantes sont exposées comme des actions métier plutôt que comme de simples modifications arbitraires du champ `status`.

Exemple :

```text id="r0h5bt"
POST /interventions/{id}/start
POST /interventions/{id}/complete
POST /interventions/{id}/cancel
```

Plutôt que :

```text id="n6t4me"
PATCH /interventions/{id}

{
  "status": "COMPLETED"
}
```

Cela permet au backend de contrôler les règles associées à la transition.

---

# 29. Exemple de transition invalide

Une intervention :

```text
status = CANCELLED
```

ne doit pas accepter :

```http
POST /interventions/{id}/start
```

Réponse :

```http
409 Conflict
```

Exemple :

```json
{
  "error": {
    "code": "INVALID_INTERVENTION_TRANSITION",
    "message": "Une intervention annulée ne peut pas être démarrée."
  }
}
```

---

# 30. Validation métier

La validation doit exister à plusieurs niveaux.

## Validation de format

Exemple :

```text
email invalide
date incorrecte
UUID invalide
```

→ `422 Unprocessable Entity`

## Validation métier

Exemple :

```text
équipement appartenant à un autre site
```

→ `409 Conflict` ou erreur métier appropriée.

## Autorisation

Exemple :

```text
technicien tentant de modifier une vente
```

→ `403 Forbidden`

---

# 31. Format d'erreur

Format cible :

```json
{
  "error": {
    "code": "EQUIPMENT_NOT_FOUND",
    "message": "Équipement introuvable",
    "details": {}
  }
}
```

Codes d'erreur stables :

```text
CLIENT_NOT_FOUND
SITE_NOT_FOUND
PRODUCT_NOT_FOUND
SALE_NOT_FOUND
INSTALLATION_NOT_FOUND
EQUIPMENT_NOT_FOUND
INTERVENTION_NOT_FOUND
REPORT_NOT_FOUND
INVALID_INTERVENTION_TRANSITION
INVALID_INSTALLATION_TRANSITION
EQUIPMENT_SITE_MISMATCH
SALE_NOT_MODIFIABLE
```

Les messages peuvent évoluer ; les codes doivent rester relativement stables pour permettre au frontend de les exploiter.

---

# 32. Autorisation

Les permissions sont contrôlées côté backend.

Exemple conceptuel :

| Action                | Admin | Manager |   Technicien |   Commercial |
| --------------------- | ----: | ------: | -----------: | -----------: |
| Consulter clients     |     ✓ |       ✓ |            ✓ |            ✓ |
| Modifier clients      |     ✓ |       ✓ | selon besoin |            ✓ |
| Consulter équipements |     ✓ |       ✓ |            ✓ |            ✓ |
| Modifier équipement   |     ✓ |       ✓ |            ✓ |       limité |
| Créer intervention    |     ✓ |       ✓ |            ✓ | selon besoin |
| Réaliser intervention |     ✓ |       ✓ |            ✓ |            — |
| Modifier résultat     |     ✓ |       ✓ |            ✓ |            — |
| Gérer catalogue       |     ✓ |       ✓ |            — |            ✓ |
| Gérer ventes          |     ✓ |       ✓ |            — |            ✓ |
| Gérer showroom        |     ✓ |       ✓ |            — |            ✓ |
| Gérer utilisateurs    |     ✓ |       — |            — |            — |

Cette matrice constitue une base fonctionnelle et sera précisée dans le document sécurité.

---

# 33. Idempotence

Certaines opérations sensibles doivent éviter les doublons lorsqu'une requête est répétée.

Exemples :

```text
création d'un rapport
envoi d'un rapport
finalisation d'une installation
```

Pour les opérations concernées, l'API pourra utiliser une clé d'idempotence.

Exemple :

```http
Idempotency-Key: 8f5d...
```

Le mécanisme exact sera défini lors de l'implémentation si nécessaire.

---

# 34. Uploads

Les fichiers volumineux ne doivent pas transiter inutilement par des payloads JSON.

Pour les photos :

```text
multipart/form-data
```

ou, si le stockage évolue :

```text
URL d'upload temporaire
```

Le backend conserve ensuite les métadonnées nécessaires.

---

# 35. API et historique

L'API ne doit pas exposer des opérations permettant de détruire facilement l'historique.

Exemple :

```text
DELETE /equipment/{id}
```

ne constitue pas nécessairement une opération métier valide.

À la place :

```text
POST /equipment/{id}/retire
```

ou :

```text
POST /equipment/{id}/replace
```

selon le contexte.

Même principe pour les interventions terminées.

---

# 36. Santé de l'API

Endpoint minimal :

```http
GET /health
```

Il permet de vérifier que l'application répond.

Un endpoint plus complet pourra vérifier les dépendances :

```http
GET /health/ready
```

par exemple :

```text
API
 ├── Database ✓
 └── Storage ✓
```

Ces endpoints ne doivent pas exposer d'informations sensibles.

---

# 37. Structure des réponses

Les réponses doivent rester prévisibles.

Collection :

```json
{
  "items": [],
  "pagination": {}
}
```

Ressource unique :

```json
{
  "id": "...",
  "name": "..."
}
```

Erreur :

```json
{
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

Cette cohérence simplifie le frontend.

---

# 38. Endpoints prioritaires V1

Le premier périmètre API réellement nécessaire est :

```text
AUTH
├── POST /auth/login
└── GET  /auth/me

CLIENTS
├── GET  /clients
├── POST /clients
├── GET  /clients/{id}
└── PATCH /clients/{id}

SITES
├── GET  /sites
├── POST /sites
├── GET  /sites/{id}
└── PATCH /sites/{id}

PRODUCTS
├── GET  /products
├── POST /products
├── GET  /products/{id}
└── PATCH /products/{id}

EQUIPMENT
├── GET /equipment
├── GET /equipment/{id}
├── GET /equipment/{id}/history
└── GET /equipment/{id}/interventions

INTERVENTIONS
├── GET  /interventions
├── POST /interventions
├── GET  /interventions/{id}
├── POST /interventions/{id}/start
├── POST /interventions/{id}/complete
├── POST /interventions/{id}/cancel
├── GET  /interventions/{id}/checklist
├── GET  /interventions/{id}/photos
├── POST /interventions/{id}/photos
├── GET  /interventions/{id}/materials
└── POST /interventions/{id}/materials

REPORTS
├── POST /interventions/{id}/reports
├── GET  /interventions/{id}/reports
└── GET  /reports/{id}/file
```

Les ventes, installations et showroom peuvent être ajoutés selon l'ordre réel de développement du produit.

---

# 39. Principe directeur

L'API doit refléter les actions que les utilisateurs effectuent réellement.

Exemples :

```text
Démarrer une intervention
        ↓
POST /interventions/{id}/start
```

```text
Terminer une intervention
        ↓
POST /interventions/{id}/complete
```

```text
Remplacer un équipement
        ↓
POST /equipment/{id}/replace
```

```text
Générer un rapport
        ↓
POST /interventions/{id}/reports
```

plutôt que de transformer toutes les opérations métier en simples :

```text
PATCH /resource/{id}
```

---

# 40. Principe final

L'API doit rester une traduction du domaine métier :

```text
CLIENT
   ↓
SITE
   ↓
ÉQUIPEMENT
   ↓
INTERVENTION
   ├── CHECKLIST
   ├── PHOTO
   ├── MATERIAL
   ├── REPORT
   └── REVIEW
```

et du parcours commercial :

```text
PRODUCT
   ↓
SALE
   ↓
SALE LINE
   ↓
INSTALLATION
   ↓
EQUIPMENT
```

L'API ne doit pas exposer inutilement les détails internes de PostgreSQL ou de l'ORM.

Le modèle métier reste la source de vérité ; l'API en est l'interface technique.

---

# Administration — migration des archives (INT-101)

Toutes les routes `/api/v1/admin/import` exigent un utilisateur actif `ADMIN`. Un technicien reçoit `403` ; l’absence de jeton suit le garde HTTPBearer commun. Les sources, coordonnées et anomalies ne sont pas publiques.

| Méthode et suffixe | Entrée | Résultat |
| --- | --- | --- |
| `POST /preview` | multipart : `file`, `source_namespace`, `selections` (liste JSON) | Import conservé, dix lignes maximum, provenance, mapping, valeurs brutes/normalisées, anomalies et propositions |
| `POST /validate` | `batch_id`, `decisions`, `selections` facultatives | Plan révisé, `plan_token`, compteurs create/associate/ignore/pending/committed/ready/duplicates |
| `POST /execute` | `batch_id`, `plan_token` seulement | Rapport du plan approuvé, sans recalcul ni nouveaux choix |
| `GET /batches` | `page`, `page_size` | Historique paginé avec compteurs |
| `GET /batches/{id}` | `page`, `page_size` | Lignes du plan et manifeste de lecture |
| `GET /batches/{id}/errors` | `page`, `page_size` | Journal des anomalies de toutes les révisions |

La pagination commence à 1 ; `page_size` vaut au maximum 100. Les listes de batches et d’erreurs renvoient `items`, `total`, `page`, `page_size`, `pages`. Le détail possède `total`, `items`, `page` et `page_size`.

Exemple de manifeste multipart, avec une nature explicite par feuille :

```json
[
  {"sheet":"Clients","kind":"clients"},
  {"sheet":"Sites","kind":"sites"},
  {"sheet":"Equipements","kind":"equipment"}
]
```

Options : `header_row` (ligne physique, à partir de 1), `encoding`, `separator`, `two_digit_year_base` (1900 ou 2000) et `mapping` (champ interne → colonne source). Formats acceptés : XLSX et CSV, au maximum 10 Mio. `mixed` doit être séparé en sélections de natures explicites ; PDF/OCR est hors périmètre.

Une décision est indexée par la clé de ligne renvoyée par l’aperçu, par exemple `Clients:6:clients` :

```json
{
  "batch_id": 1,
  "decisions": {
    "Clients:6:clients": {
      "action": "associate",
      "associate_source_id": "C001",
      "note": "Doublon confirmé après comparaison des archives"
    },
    "Sites:2:sites": {
      "action": "create",
      "corrections": {"site_name": "Maison — 12 rue des Lilas"},
      "note": "Libellé confirmé"
    }
  }
}
```

Actions : `create`, `associate`, `ignore`, `review`. `review` applique une correction puis soumet à nouveau la ligne au rapprochement. Une association exige exactement une cible : `entity_id` Tervo ou `associate_source_id` du même namespace et du même type. Le motif est obligatoire. Les décisions fournies remplacent les décisions précédentes des mêmes lignes ; les autres restent conservées.

Le fichier est conservé sous empreinte SHA-256. Recharger le même contenu dans le même namespace retrouve le même import ; pour changer le mapping, utiliser `validate`. Une nouvelle validation invalide l’ancien jeton. Un changement du référentiel métier impose aussi une revalidation (`409`). Dès le premier sous-lot commité, le mapping et les décisions des lignes traitées sont figés. Un import réussi retourne son rapport existant.

`MISSING_PHONE` reste visible dans les anomalies. Une correction permet la création ; une association certaine conserve les coordonnées de la cible. Les anomalies journalisées décrivent leurs révisions et les données originales : consulter le plan courant pour connaître les lignes encore `pending`.

`422` : fichier, manifeste ou contrat invalide ; `413` : fichier trop volumineux ; `404` : import absent ; `409` : approbation périmée, import occupé ou modification d’une ligne commitée. Une réponse `200` d’exécution contient un rapport dont le statut doit être lu : `success`, `partial` ou `failed` (rollback d’un sous-lot).

L’exécution est synchrone. `ready` compte les opérations approuvées restant à exécuter ; `committed` compte les traces persistées. Les compteurs d’opérations décrivent le plan et ne sont pas des promesses de débit.
