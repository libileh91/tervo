# Tervo — Sécurité technique

## 1. Objectif

La sécurité de Tervo doit protéger :

* les comptes utilisateurs ;
* les données clients et sites ;
* les informations relatives aux équipements et interventions ;
* les photos et documents techniques ;
* les rapports transmis aux clients ;
* les opérations métier sensibles.

L'objectif V1 est une sécurité **simple, explicite et adaptée à une application métier**, sans introduire prématurément une infrastructure complexe.

Principes directeurs :

1. authentifier avant d'accéder aux ressources protégées ;
2. autoriser selon le rôle et le périmètre métier ;
3. ne jamais faire confiance aux données reçues du client ;
4. protéger les fichiers séparément des données métier ;
5. ne jamais exposer de secrets dans le code ou les réponses API ;
6. conserver une trace des opérations sensibles ;
7. appliquer le principe du moindre privilège.

---

## 2. Modèle de sécurité

La sécurité repose sur quatre niveaux complémentaires :

```text
Utilisateur
    │
    ▼
Authentification
    │
    ▼
Autorisation par rôle
    │
    ▼
Contrôle du périmètre métier
    │
    ▼
Ressource
(Client / Site / Équipement / Intervention / Document)
```

Un utilisateur authentifié ne doit donc pas automatiquement pouvoir accéder à toutes les données.

Exemple :

```text
TECHNICIAN
   │
   ├── peut consulter une intervention qui lui est accessible
   ├── peut modifier les données d'exécution autorisées
   ├── peut ajouter photos et matériel
   └── ne peut pas modifier les droits d'un autre utilisateur
```

---

# 3. Authentification

## 3.1 Principe

Toutes les routes métier sont protégées par authentification.

Exceptions :

```text
GET /health
GET /health/ready
POST /api/v1/auth/login
```

Les autres endpoints nécessitent une identité utilisateur valide.

L'implémentation exacte du mécanisme de session/token reste un choix technique d'implémentation, mais elle doit respecter les principes suivants :

* transport exclusivement via HTTPS en production ;
* durée de validité limitée ;
* possibilité d'invalider une session/token ;
* absence de mot de passe dans les logs ;
* absence de token dans les logs applicatifs ;
* contrôle systématique côté backend.

Le frontend ne doit jamais être considéré comme une frontière de sécurité.

---

## 3.2 Mots de passe

Les mots de passe ne sont jamais stockés en clair.

Le backend doit utiliser un algorithme de hachage adapté aux mots de passe, par exemple :

* Argon2id ;
* ou bcrypt si nécessaire pour compatibilité.

Le hash est stocké en base :

```text
password
    ↓
hash(password)
    ↓
password_hash
```

Lors d'une connexion :

```text
mot de passe fourni
        ↓
vérification du hash
        ↓
succès → authentification
échec  → erreur générique
```

Le message d'erreur ne doit pas permettre de distinguer :

```text
utilisateur inexistant
```

de :

```text
mot de passe incorrect
```

---

# 4. Autorisation

## 4.1 Rôles

Les rôles fonctionnels V1 sont :

| Rôle         | Usage principal                            |
| ------------ | ------------------------------------------ |
| `ADMIN`      | Administration technique et fonctionnelle  |
| `MANAGER`    | Gestion de l'activité et supervision       |
| `TECHNICIAN` | Exécution des interventions                |
| `COMMERCIAL` | Clients, catalogue et activité commerciale |

Les noms définitifs doivent être standardisés dans le code et l'API.

---

## 4.2 Matrice indicative

| Action                          | ADMIN | MANAGER |   TECHNICIAN |   COMMERCIAL |
| ------------------------------- | ----: | ------: | -----------: | -----------: |
| Gérer utilisateurs              |     ✓ |  limité |            — |            — |
| Consulter clients               |     ✓ |       ✓ |            ✓ |            ✓ |
| Modifier clients                |     ✓ |       ✓ | selon besoin |            ✓ |
| Gérer catalogue                 |     ✓ |       ✓ |            — |            ✓ |
| Créer une vente                 |     ✓ |       ✓ |            — |            ✓ |
| Gérer installations             |     ✓ |       ✓ |            ✓ |            — |
| Exécuter intervention           |     ✓ |       ✓ |            ✓ |            — |
| Ajouter photos                  |     ✓ |       ✓ |            ✓ |            — |
| Ajouter matériel utilisé        |     ✓ |       ✓ |            ✓ |            — |
| Générer rapport                 |     ✓ |       ✓ |            ✓ | selon besoin |
| Consulter historique équipement |     ✓ |       ✓ |            ✓ | selon besoin |
| Gérer checklists                |     ✓ |       ✓ |            — |            — |
| Administrer la sécurité         |     ✓ |       — |            — |            — |

Cette matrice est une base de conception. Les permissions fines seront précisées lors de l'implémentation des modules.

---

# 5. Contrôle du périmètre métier

Le rôle seul ne suffit pas.

Le backend doit également vérifier les relations métier.

Exemple :

```text
Intervention
    ├── site_id = 42
    └── equipment_id = 17
```

Le backend doit vérifier que :

```text
Equipment 17
    appartient bien
        au Site 42
```

Une requête telle que :

```http
GET /equipment/17
```

ne doit jamais permettre d'accéder à un équipement simplement parce que son identifiant est connu.

Même principe pour :

* interventions ;
* rapports ;
* photos ;
* installations ;
* ventes ;
* sites ;
* documents.

---

# 6. Validation des données

Toutes les données entrantes doivent être validées côté backend.

Cela concerne notamment :

* paramètres d'URL ;
* paramètres de requête ;
* payloads JSON ;
* formulaires ;
* fichiers uploadés ;
* identifiants ;
* dates ;
* quantités ;
* valeurs d'énumération.

Exemple :

```json
{
  "result": "INVALID_VALUE"
}
```

ne doit pas pouvoir contourner le modèle métier simplement parce que le frontend a accepté la valeur.

Le frontend améliore l'expérience utilisateur.

Le backend fait respecter les règles.

---

# 7. Sécurité des fichiers

Les photos et rapports sont particulièrement importants dans Tervo.

Les fichiers ne doivent pas être stockés directement avec un nom fourni par l'utilisateur.

Mauvais modèle :

```text
/uploads/photo-client.jpg
```

Meilleur modèle :

```text
storage/
└── interventions/
    └── <intervention-id>/
        └── <generated-storage-key>
```

Le nom physique du fichier est généré par Tervo.

Les métadonnées sont conservées en base :

```text
Photo
├── intervention_id
├── storage_key
├── filename
├── mime_type
├── size
└── captured_at
```

Le `filename` original sert uniquement à l'information utilisateur.

---

## 7.1 Contrôles d'upload

Tout upload doit vérifier au minimum :

* taille maximale ;
* type MIME déclaré ;
* extension ;
* type réellement détecté lorsque nécessaire ;
* nom de fichier ;
* emplacement de stockage ;
* utilisateur autorisé à effectuer l'upload.

Pour les photos V1, les formats autorisés doivent être volontairement limités.

Exemple :

```text
image/jpeg
image/png
image/webp
```

Les exécutables et formats non nécessaires au métier ne sont pas acceptés.

---

## 7.2 Accès aux fichiers

Les fichiers ne doivent pas être exposés par un répertoire public contenant directement les documents.

Le backend contrôle l'accès :

```text
GET /api/v1/reports/{id}/file
```

ou :

```text
GET /api/v1/interventions/{id}/photos/{photo_id}
```

Le backend vérifie :

```text
utilisateur authentifié
        +
autorisation
        +
appartenance métier
        ↓
accès au fichier
```

---

# 8. Rapports et documents transmis

Un rapport transmis au client constitue un document métier historique.

Après transmission, son contenu ne doit pas être silencieusement remplacé.

Le système doit privilégier :

```text
Rapport v1
    ↓
transmis
    ↓
modification nécessaire
    ↓
Rapport v2
```

L'historique doit rester identifiable.

Les fichiers générés doivent également être protégés contre un accès direct non autorisé.

---

# 9. Protection contre les injections

Les accès PostgreSQL doivent utiliser les mécanismes de paramétrage fournis par la couche d'accès aux données.

Le code ne doit pas construire des requêtes SQL à partir de chaînes utilisateur concaténées.

Exemple à éviter conceptuellement :

```text
"SELECT ... WHERE name = '" + user_input + "'"
```

Les ORM et requêtes paramétrées doivent être utilisés systématiquement.

Cela concerne également :

* filtres ;
* recherches ;
* tris ;
* pagination ;
* exports ;
* recherches administratives.

Les champs de tri doivent notamment être issus d'une liste blanche connue du backend.

---

# 10. CORS et CSRF

## 10.1 CORS

En production, les origines autorisées doivent être explicitement configurées.

Éviter :

```text
Access-Control-Allow-Origin: *
```

pour une API authentifiée.

Exemple conceptuel :

```text
Frontend Tervo
    https://app.example.com

API Tervo
    https://api.example.com
```

L'API n'autorise que les origines prévues.

---

## 10.2 CSRF

La stratégie dépend du mécanisme d'authentification retenu.

Si l'authentification utilise des cookies, une protection CSRF adaptée doit être mise en place.

Si l'authentification repose sur un mécanisme différent, les protections correspondantes doivent être appliquées.

Le choix définitif sera arrêté lors de l'implémentation de l'authentification.

---

# 11. Secrets et configuration

Aucun secret ne doit être commité dans Git.

Cela inclut :

* mots de passe PostgreSQL ;
* clés JWT ;
* clés de chiffrement ;
* credentials SMTP ;
* credentials de stockage ;
* tokens externes.

La configuration doit être injectée par l'environnement :

```text
.env
Docker secrets
variables d'environnement
```

Le dépôt peut contenir :

```text
.env.example
```

mais jamais les valeurs réelles.

Exemple :

```text
DATABASE_URL=...
SECRET_KEY=...
SMTP_PASSWORD=...
```

---

# 12. PostgreSQL et infrastructure

Le conteneur PostgreSQL ne doit pas être exposé publiquement lorsque cela n'est pas nécessaire.

Architecture cible :

```text
Internet
   │
   ▼
Reverse Proxy
   │
   ├── Frontend
   │
   └── API
          │
          ▼
      PostgreSQL
      réseau privé
```

PostgreSQL doit être accessible uniquement par les services qui en ont besoin.

Même principe pour le stockage interne.

---

# 13. HTTPS

En production :

```text
HTTP
  ↓
redirect
  ↓
HTTPS
```

Le reverse proxy est responsable de la terminaison TLS.

Les cookies ou tokens sensibles ne doivent jamais transiter sur une connexion HTTP non sécurisée.

Les certificats doivent être renouvelés automatiquement lorsque l'infrastructure le permet.

---

# 14. En-têtes de sécurité

Le reverse proxy et/ou l'application doivent mettre en place les en-têtes de sécurité pertinents.

Notamment :

* `Content-Security-Policy` selon la configuration frontend ;
* `X-Content-Type-Options: nosniff` ;
* `Referrer-Policy` ;
* protections adaptées contre le framing ;
* configuration stricte des transports HTTPS.

La configuration exacte dépendra du reverse proxy retenu.

---

# 15. Gestion des erreurs

Une erreur interne ne doit jamais exposer :

* stack trace ;
* requête SQL ;
* mot de passe ;
* token ;
* chemin interne du serveur ;
* variables d'environnement ;
* détails d'infrastructure.

L'API retourne une erreur structurée.

Exemple :

```json
{
  "error": {
    "code": "EQUIPMENT_NOT_FOUND",
    "message": "Equipment not found",
    "details": null
  }
}
```

Les détails techniques restent dans les logs internes.

---

# 16. Logs et audit

Les logs applicatifs doivent permettre de diagnostiquer les incidents sans enregistrer de données sensibles inutilement.

À éviter :

```text
password=...
Authorization: Bearer ...
```

Les opérations sensibles doivent pouvoir être retracées.

Exemples :

```text
connexion utilisateur
modification des droits
création/suppression logique d'un utilisateur
modification importante d'un équipement
annulation d'une vente
transmission d'un rapport
remplacement d'un équipement
```

Un mécanisme d'audit plus complet pourra être ajouté si les besoins métier le justifient.

---

# 17. Rate limiting

Une limitation du nombre de requêtes est particulièrement pertinente pour :

* connexion ;
* récupération de mot de passe ;
* endpoints sensibles ;
* upload ;
* endpoints coûteux.

En V1, un rate limiting simple peut être appliqué en priorité aux endpoints d'authentification.

Il pourra ensuite être étendu selon les besoins observés.

---

# 18. Gestion du cycle de vie des comptes

Un compte utilisateur doit pouvoir être :

```text
ACTIF
  ↓
DÉSACTIVÉ
```

La désactivation est préférable à une suppression physique lorsqu'un historique métier dépend de l'utilisateur.

Par exemple :

```text
Intervention
    └── technician_id
             ↓
        ancien utilisateur
        désactivé
```

L'historique reste compréhensible.

---

# 19. RGPD et données métier

Tervo traite notamment des données pouvant identifier des personnes :

* nom ;
* email ;
* téléphone ;
* adresse ;
* informations relatives aux interventions ;
* photos ;
* documents.

La conception doit donc appliquer les principes de minimisation :

> stocker uniquement les informations nécessaires au fonctionnement du service.

Les données personnelles ne doivent pas être copiées inutilement dans :

* logs ;
* exports temporaires ;
* fichiers de debug ;
* environnements de développement.

Les besoins de :

* conservation ;
* suppression ;
* export ;
* rectification ;
* accès aux données

doivent être définis selon le contexte réel d'exploitation de Tervo.

Le DAT technique ne remplace pas une analyse juridique RGPD.

---

# 20. Sauvegardes

La sauvegarde doit couvrir deux catégories de données :

```text
PostgreSQL
    +
Stockage fichiers
```

Sauvegarder uniquement PostgreSQL ne suffit pas puisque les photos et rapports sont stockés séparément.

Objectif :

```text
Backup DB
    +
Backup storage
    ↓
restauration cohérente
```

Les sauvegardes doivent être :

* automatisées ;
* protégées ;
* testées périodiquement ;
* séparées du stockage primaire lorsque possible.

Une sauvegarde qui n'a jamais été restaurée n'est pas considérée comme suffisamment validée.

---

# 21. Sécurité Docker

Les conteneurs doivent respecter le principe du moindre privilège.

À éviter lorsque ce n'est pas nécessaire :

```text
privileged: true
```

Les services doivent exposer uniquement les ports nécessaires.

Exemple :

```text
Reverse proxy
    ↓
Frontend/API
    ↓
PostgreSQL
```

PostgreSQL ne doit pas nécessiter un port public pour fonctionner.

Les volumes persistants doivent être explicitement identifiés afin d'éviter une perte accidentelle lors du remplacement d'un conteneur.

---

# 22. Scénarios de menace principaux

| Scénario                              | Protection                                      |
| ------------------------------------- | ----------------------------------------------- |
| Vol d'un mot de passe                 | Hash fort + HTTPS + limitation login            |
| Accès à un équipement par ID connu    | Autorisation + contrôle de périmètre            |
| Accès à une photo privée              | Endpoint protégé + contrôle métier              |
| Upload d'un fichier malveillant       | Type/taille/extension + stockage contrôlé       |
| Injection SQL                         | ORM/requêtes paramétrées                        |
| Fuite de secrets Git                  | Secrets hors dépôt                              |
| Exposition PostgreSQL                 | Réseau privé                                    |
| Fuite de stack trace                  | Gestion d'erreurs structurée                    |
| Compte employé désactivé              | Désactivation plutôt que suppression historique |
| Perte de photos après incident        | Backup du stockage                              |
| Modification silencieuse d'un rapport | Versionnement / historique                      |
| Abus de l'endpoint login              | Rate limiting                                   |

---

# 23. Priorités de sécurité

## P0 — obligatoire avant production

* authentification ;
* hash sécurisé des mots de passe ;
* autorisation par rôle ;
* contrôle du périmètre métier ;
* HTTPS ;
* validation backend ;
* protection des fichiers ;
* secrets hors Git ;
* PostgreSQL non exposé publiquement ;
* gestion sécurisée des erreurs ;
* sauvegardes DB + fichiers.

## P1 — à intégrer rapidement

* rate limiting ;
* audit des opérations sensibles ;
* headers de sécurité ;
* désactivation des comptes ;
* politique de rétention des logs ;
* tests de restauration des sauvegardes.

## P2 — selon évolution

* MFA/2FA ;
* permissions plus fines ;
* audit complet ;
* détection d'activité anormale ;
* chiffrement avancé de certains documents ;
* gestion centralisée des secrets.

---

# 24. Principe d'implémentation

La sécurité ne doit pas être répartie arbitrairement dans les routes.

Le principe cible est :

```text
API
 │
 ├── Authentification
 │
 ▼
Authorization
 │
 ▼
Service métier
 │
 ▼
Repository
 │
 ▼
Database
```

Les règles métier sensibles doivent rester dans les services/domaines plutôt que dépendre uniquement du frontend ou d'une route particulière.

Exemple :

```text
POST /interventions/{id}/complete
        │
        ▼
authentifié ?
        │
        ▼
autorisé ?
        │
        ▼
intervention accessible ?
        │
        ▼
état compatible ?
        │
        ▼
complétion métier
        │
        ▼
transaction DB
```

Cela permet d'avoir une sécurité cohérente quel que soit le client consommant l'API.

---

# 25. Règle générale

La sécurité Tervo repose sur une règle simple :

> **Être authentifié ne signifie pas avoir accès à tout.**

L'accès à une donnée dépend de :

```text
Identité
   +
Rôle
   +
Périmètre métier
   +
État de la ressource
   =
Autorisation
```

Cette approche est suffisante pour construire une V1 robuste sans introduire prématurément une architecture de sécurité disproportionnée.
