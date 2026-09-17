GO. J’ai repris le DAT disponible **ligne par ligne**, et je vais être assez exigeant : l’objectif n’est pas seulement d’avoir une architecture « jolie », mais d’avoir une architecture **cohérente et défendable en entretien**.

Le document est déjà bien structuré. En revanche, il y a quelques incohérences techniques importantes et surtout plusieurs endroits où le DAT présente comme acquis des éléments que tu ne devrais pas présenter comme de l’expérience réelle.

## 1. Verdict global

Je garderais l’architecture générale :

```text
                    Internet
                       │
                  HTTPS :443
                       │
                ┌──────▼──────┐
                │   1Panel    │
                │  OpenResty  │
                │ SSL / Proxy │
                └──────┬──────┘
                       │
          ┌────────────┴────────────┐
          │                         │
     Frontend SPA               FastAPI
       Vue.js                     │
          │                  Services métier
          │                         │
          │                   Repositories
          │                         │
          │                    PostgreSQL
          │
          └────── API REST ─────────┘

             + stockage fichiers
             + sauvegardes
             + Paperless
```

C'est parfaitement raisonnable pour **3–5 techniciens + 1 comptable**. Le fait d'avoir abandonné Swarm est également cohérent avec le périmètre décrit dans le document. 

Mais je ferais **6 corrections majeures**.

---

# 2. 🔴 Correction majeure n°1 — Paperless et les ports

C'est actuellement le problème technique le plus évident.

Dans le Compose principal :

```yaml
backend:
  ports:
    - "8000:8000"
```

Et dans le Compose Paperless :

```yaml
webserver:
  ports:
    - "8000:8000"
```

Or les deux stacks sont sur **le même VPS**.

➡️ Ils ne peuvent pas tous les deux binder `0.0.0.0:8000`.

Le DAT représente pourtant :

```text
api.mbchauffage.com  → localhost:8000
docs.mbchauffage.com → localhost:8000
```

C'est impossible tel quel.

### Correction

Je ferais plutôt :

```yaml
backend:
  ports:
    - "127.0.0.1:8000:8000"
```

et Paperless :

```yaml
webserver:
  ports:
    - "127.0.0.1:8001:8000"
```

Puis :

```text
api.mbchauffage.com
        ↓
1Panel
        ↓
127.0.0.1:8000
        ↓
FastAPI
```

et :

```text
docs.mbchauffage.com
        ↓
1Panel
        ↓
127.0.0.1:8001
        ↓
Paperless
```

Encore mieux : **ne pas exposer les ports applicatifs publiquement**. Les binder sur `127.0.0.1` limite l'accès à l'hôte et force le trafic externe à passer par le reverse proxy.

### Ce que tu peux dire en entretien

> « Les services applicatifs ne sont pas directement exposés à Internet. Le reverse proxy est le point d'entrée HTTPS et route vers les services sur le réseau local du VPS. »

Ça, c'est une bonne réponse d'architecture.

---

# 3. 🔴 Correction majeure n°2 — le backend n'a pas besoin d'être exposé au frontend

Actuellement tu raisonnes comme :

```text
browser
   │
   ├── mbchauffage.com:3000
   │
   └── api.mbchauffage.com:8000
```

C'est acceptable, mais les ports `3000` et `8000` ne devraient pas être des ports publics.

Je préfère :

```text
Internet
    │
    ▼
  80/443
    │
  1Panel
    │
    ├── mbchauffage.com ──► frontend:80
    │
    ├── api.mbchauffage.com ──► backend:8000
    │
    └── docs.mbchauffage.com ──► paperless:8000
```

Avec les containers accessibles uniquement via Docker/localhost.

C'est plus propre et plus facile à expliquer.

---

# 4. 🔴 Correction majeure n°3 — `depends_on` ≠ readiness

Le Compose contient :

```yaml
depends_on:
  - postgres
```

Ça signifie essentiellement :

> « démarre PostgreSQL avant le backend »

Ça ne signifie pas :

> « PostgreSQL est prêt à accepter des connexions ».

Pour une architecture sérieuse, ajoute un `healthcheck`.

Par exemple :

```yaml
postgres:
  image: postgres:17
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U mbchauffage -d mbchauffage_db"]
    interval: 10s
    timeout: 5s
    retries: 5
```

Puis :

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

### Question d'entretien probable

**« Pourquoi utilisez-vous un healthcheck ? »**

Réponse :

> « Parce que le démarrage du container PostgreSQL ne garantit pas que la base soit déjà prête à accepter les connexions. Le healthcheck permet au service dépendant de distinguer un container démarré d'un service réellement disponible. »

Très bon petit point DevOps à connaître.

---

# 5. 🔴 Correction majeure n°4 — le CI/CD actuel est incohérent

Le pipeline fait :

```text
GitHub Actions
   │
   ├── test
   │
   ├── build images
   │
   └── SSH VPS
           │
           ├── git pull
           ├── docker build backend
           ├── docker build frontend
           └── docker compose up
```

Donc les images sont **buildées deux fois**.

Une fois dans GitHub Actions :

```yaml
docker build ...
```

puis une deuxième fois sur le VPS :

```bash
docker build ...
```

Le premier build n'est donc pas utilisé.

### Je simplifierais

Pour ton niveau et la taille du projet :

```text
push main
    │
    ▼
GitHub Actions
    │
    ├── tests
    │
    └── SSH
          │
          ▼
         VPS
          │
       git pull
          │
    docker compose build
          │
    docker compose up -d
```

Ou, architecture plus mature :

```text
GitHub
   │
   ▼
GitHub Actions
   │
   ├── tests
   ├── build
   ├── push image
   │
   ▼
GHCR
   │
   ▼
VPS
   │
 docker compose pull
   │
 docker compose up -d
```

### Pour TON projet

Je choisirais la deuxième comme **évolution possible**, mais je ne prétendrais pas que tu l'as déjà maîtrisée.

Tu peux dire :

> « Pour la première version, j'ai privilégié un déploiement simple par SSH et Docker Compose. Une évolution naturelle serait de publier les images dans un registry puis de faire uniquement un `docker compose pull` sur le VPS. »

Excellent niveau de réponse sans survendre ton expérience.

---

# 6. 🔴 Correction majeure n°5 — l'idempotence de l'import n'est pas suffisamment définie

Le DAT dit :

> « Idempotent : ré-exécutable sans doublons » 

et :

> « Idempotence : le seed et l'import sont ré-exécutables sans effet de bord » 

Mais **comment ?**

C'est LA question qu'un interviewer peut poser.

Il faut définir le mécanisme.

### Je propose

Créer une notion de :

```text
ImportBatch
```

avec par exemple :

```text
id
filename
file_hash
started_at
completed_at
status
```

Et pour chaque ligne importée :

```text
source_file
source_row
source_hash
entity_type
entity_id
```

On peut alors avoir :

```text
fichier Excel
     │
     ▼
SHA-256
     │
     ├── déjà importé ?
     │       │
     │       └── oui → ne pas réimporter
     │
     └── non
            │
            ▼
       traitement
```

Mais attention : **je présente ça comme une amélioration de conception**, pas comme ton implémentation historique.

---

# 7. 🔥 Le vrai cœur du projet : la migration Excel

C'est ici que ton projet devient intéressant pour un entretien.

Le DAT identifie correctement les problèmes :

* formats variables ;
* données manquantes ;
* doublons ;
* accents/encodage ;
* absence de FK historique ;
* nécessité de faire clients puis jobs. 

Et le pipeline proposé est :

```text
Excel
  │
  ▼
Pandas / openpyxl
  │
  ▼
Détection du format
  │
  ▼
Normalisation
  │
  ▼
Validation
  │
  ▼
Détection doublons
  │
  ▼
Validation humaine
  │
  ▼
PASS 1
Clients
  │
  ▼
PASS 2
Jobs
  │
  ▼
PostgreSQL
  │
  ▼
Rapport
```

Ça, je le conserverais.

---

# 8. 🟠 Mais je corrigerais le fuzzy matching

Le DAT dit :

```text
nom + téléphone matchent à 90%
```

C'est trop simpliste.

Parce que :

```text
Jean Dupont
06 12 34 56 78
```

et

```text
Jean DUPONT
0612345678
```

ne doivent pas être comparés comme des chaînes brutes.

### Étape 1 — normalisation

```python
def normalize_name(value):
    ...
```

Objectif :

```text
" Élodie  DUPONT "
        ↓
"elodie dupont"
```

Téléphone :

```text
"06 12 34 56 78"
        ↓
"0612345678"
```

### Étape 2 — matching

Puis `rapidfuzz`.

Le document indique bien `rapidfuzz` dans le stack technique, alors que la partie migration mentionne `diffblib`.  

➡️ **Je remplacerais partout `diffblib` par `rapidfuzz`.**

---

# 9. Encore mieux : trois zones de décision

Plutôt que :

```text
score >= 90 → doublon
```

je recommande :

```text
score >= 95
     ↓
match automatique

80 <= score < 95
     ↓
validation humaine

score < 80
     ↓
nouveau client
```

Les valeurs **95/80 sont des paramètres de conception à calibrer**, pas des vérités universelles.

Et c'est beaucoup plus intéressant en entretien parce que tu peux expliquer :

> « Je ne veux pas automatiser aveuglément la fusion des clients. Une erreur de rapprochement est potentiellement plus grave qu'un doublon temporaire. Je préfère donc une zone automatique, une zone d'ambiguïté avec validation humaine et une zone de non-match. »

Là, tu montres une vraie réflexion data.

---

# 10. 🔥 Transaction : je modifierais légèrement le DAT

Le document dit :

> « tout ou rien par lot » 

Très bien.

Mais il faut formaliser :

```text
VALIDATION
    ↓
BEGIN TRANSACTION
    ↓
clients
    ↓
jobs
    ↓
logs
    ↓
COMMIT
```

Si erreur :

```text
ROLLBACK
```

### Surtout pas

```text
20 ans Excel
     ↓
une énorme transaction
```

Ça serait inutilement lourd.

Je conserverais :

> **transaction par batch d'import**

par exemple :

```text
1 fichier
  ├── batch 1
  ├── batch 2
  ├── batch 3
  └── ...
```

---

# 11. 🟢 Le choix « clients puis jobs » est très bon

Le DAT l'explique déjà correctement :

```text
historique Excel

Job
 └── "Dupont Jean"
```

alors que PostgreSQL veut :

```text
job.client_id → client.id
```

Donc :

### Pass 1

```text
Excel
 ↓
Clients
 ↓
canonical client IDs
```

### Pass 2

```text
Excel jobs
 ↓
matching client
 ↓
client_id
 ↓
Job
```

C'est exactement le genre de problème de migration qu'un interviewer peut te donner comme exercice.

Le document le formalise déjà dans le pipeline. 

---

# 12. 🔴 Attention à « jobs orphelins ignorés »

Actuellement :

> « Les jobs orphelins ... sont ignorés avec warning » 

Je changerais ça.

**Ignorer définitivement une donnée historique est dangereux.**

Je préfère :

```text
job sans client identifiable
          │
          ▼
    import_errors
          │
          ├── status = ORPHAN
          ├── source_row
          ├── original_client_name
          └── reason
```

Puis l'admin peut traiter les cas problématiques.

Donc :

> « Les jobs ne pouvant pas être rattachés automatiquement sont placés en anomalie d'import et ne sont pas insérés comme jobs métier tant qu'ils n'ont pas été résolus. »

Beaucoup plus robuste.

---

# 13. 🟠 Module financier : attention au niveau de réalité

Le DAT décrit :

* devis ;
* factures ;
* paiements ;
* TVA ;
* échéances ;
* bilans ;
* conversion devis → facture. 

C'est intéressant mais **je ne te conseille pas de présenter ça comme une comptabilité complète**.

Tu dois dire :

> « C'est un module de gestion commerciale simplifié : devis, factures, suivi des règlements et indicateurs. Ce n'est pas un logiciel comptable et l'intégration avec EBP/Sage est hors périmètre. »

D'ailleurs le DAT le prévoit déjà comme hors périmètre. 

---

# 14. 🔴 Le cron mensuel du bilan est probablement inutile

Tu as :

```text
1er du mois à 2h
       ↓
calcul du mois précédent
       ↓
table bilan
```

Pour quelques utilisateurs et peu de données, je trouve ça prématuré.

Tu peux simplement calculer les KPIs à la demande :

```sql
SELECT ...
FROM invoices
WHERE date_emission >= ...
```

Puis éventuellement ajouter une table de snapshot si le volume ou les besoins métier le justifient.

### Je changerais le DAT en :

> « Les bilans sont calculés à partir des données financières. Une table de snapshot mensuel pourra être introduite ultérieurement si les besoins de performance ou d'historisation le justifient. »

C'est plus proportionné.

---

# 15. 🟠 Frontend : je ne mettrais pas autant de technologie

Le DAT contient :

* Vue
* TypeScript
* Pinia
* Vue Query
* PrimeVue
* PrimeFlex
* VeeValidate
* Zod
* date-fns
* Chart.js/ApexCharts
* Vite
* Bun

Pour quelqu'un qui se présente principalement comme **Java/backend**, ça peut devenir une machine à questions.

Un recruteur peut te demander :

> « Pourquoi Pinia ET Vue Query ? »

> « Quelle différence entre état serveur et état client ? »

> « Pourquoi Bun plutôt que npm ? »

> « Pourquoi VeeValidate + Zod ? »

Et là tu vas te retrouver à défendre une stack que tu n'as pas réellement maîtrisée.

### Je simplifierais

```text
Vue 3
TypeScript
Vite
Vue Router
Vue Query
PrimeVue
```

Et seulement les autres bibliothèques **si réellement utilisées**.

Pour l'entretien :

> « Le frontend n'est pas mon domaine d'expertise principal. J'ai utilisé Vue/TypeScript pour compléter le projet, avec un accompagnement important de l'IA sur cette partie. Mon cœur de compétence reste le backend et l'architecture. »

C'est beaucoup plus crédible.

---

# 16. 🔴 Même problème avec les versions

Le DAT est très précis :

```text
FastAPI 0.111+
PostgreSQL 17
Vite 6
Bun 1.2
...
```

Pour un projet en évolution, ces versions vieillissent.

Je préfère dans le DAT :

```text
Python 3.11+
FastAPI
SQLAlchemy 2.x
PostgreSQL
...
```

et laisser les versions exactes dans :

```text
pyproject.toml
package.json
compose.yaml
```

Le DAT décrit l'architecture ; le lockfile décrit l'état exact des dépendances.

---

# 17. 🔴 Backups : très bon principe, mais le script doit être renforcé

Tu as le bon principe :

```text
backup quotidien
       +
stockage distant
       +
restore test mensuel
```

Et c'est particulièrement pertinent pour un historique de 20 ans. 

Mais ton script actuel affiche :

```text
Restore test OK
```

après avoir seulement vérifié le nombre de tables.

Ce n'est pas suffisant.

Un backup peut restaurer :

```text
15 tables
```

mais contenir des données corrompues ou incomplètes.

Je ferais au minimum :

```text
restore
 ↓
check schema
 ↓
check tables
 ↓
check row counts
 ↓
check quelques contraintes
 ↓
check application query
 ↓
OK
```

Et idéalement :

```text
backup
 ↓
restore dans DB temporaire
 ↓
smoke tests
```

---

# 18. 🔴 Et surtout : backup ≠ synchronisation

Le DAT parle de :

```text
photos → Object Storage
```

et :

```text
PostgreSQL → pg_dump → Object Storage
```

Très bien.

Mais il faut distinguer :

### Backup

```text
snapshot/version
```

de :

### Synchronisation

```text
source → destination
```

Pour les fichiers, je préfère une stratégie versionnée ou avec rétention, plutôt qu'un simple miroir qui pourrait propager une suppression accidentelle.

---

# 19. 🟢 1Panel : je garde

Contrairement à certaines parties, je ne pense pas qu'il faille retirer 1Panel.

Ton raisonnement est cohérent :

```text
Docker Compose
    ↓
gère les services

1Panel
    ↓
opérations / administration
    ├── reverse proxy
    ├── SSL
    ├── fichiers
    ├── monitoring
    ├── backups
    └── administration
```

Et le DAT explique correctement que le choix est lié à la simplicité opérationnelle du projet. 

Mais je supprimerais la phrase :

> « 1Panel est un couteau suisse »

du DAT final.

C'est très bien dans une discussion informelle, moins dans une architecture professionnelle.

---

# 20. 🔴 `ports 22,80,443,7410`

Tu as deux versions contradictoires :

```text
ports 22, 80, 443, 7410
```

puis plus loin :

```text
ports 22, 80, 443 uniquement
```

 

Il faut décider.

Et je recommande :

```text
22
80
443
```

**7410 ne devrait pas être exposé publiquement.**

Pour administrer 1Panel :

```text
SSH
 ↓
tunnel SSH
 ↓
localhost:7410
```

ou restriction firewall à une IP d'administration connue.

---

# 21. 🟠 JWT : attention au stockage du token

Le DAT dit :

```text
JWT
access token 30 min
refresh token 7 jours
```

C'est bien comme concept.

Mais le DAT ne précise pas où ils sont stockés.

Pour une SPA, c'est une vraie question d'architecture.

Je ne figerais pas ça dans le DAT tant que tu n'as pas décidé précisément la stratégie.

Pour l'entretien, retiens surtout :

```text
access token court
refresh token contrôlé
HTTPS obligatoire
rotation/révocation si nécessaire
```

---

# 22. 🟢 Architecture backend : très bonne base

Cette partie :

```text
Router
   ↓
Service
   ↓
Repository
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

est cohérente et très facile à rapprocher de ton expérience Java.

Tu peux même l'expliquer :

| MB Chauffage   | Java/Spring      |
| -------------- | ---------------- |
| FastAPI Router | Controller       |
| Pydantic       | DTO / validation |
| Service        | Service          |
| Repository     | Repository       |
| SQLAlchemy     | JPA/Hibernate    |
| PostgreSQL     | PostgreSQL       |

Et là ton expérience Java devient un **avantage pour comprendre le projet Python**, plutôt qu'un handicap.

---

# 23. 🔥 Le point que je veux ajouter : architecture d'import séparée

Actuellement le projet mélange :

```text
services/
   import_service.py
```

et :

```text
importers/
```

Je clarifierais.

Je voudrais :

```text
importers/
├── excel_reader.py
├── format_detector.py
├── normalizer.py
├── validators.py
├── matcher.py
└── report.py

services/
└── import_service.py
```

Responsabilités :

```text
ExcelReader
    ↓
FormatDetector
    ↓
Normalizer
    ↓
Validator
    ↓
Matcher
    ↓
ImportService
    ↓
Repository
```

Cela rend ton architecture beaucoup plus facile à défendre.

---

# 24. Architecture finale que je recommande

Pour MB Chauffage, je partirais finalement sur :

```text
                         INTERNET
                            │
                        HTTPS 443
                            │
                    ┌───────▼────────┐
                    │     1Panel     │
                    │    OpenResty   │
                    │  SSL / Routing │
                    └───────┬────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
     Frontend SPA       FastAPI          Paperless
       Vue.js             API               GED
          │                 │
          │          ┌──────▼──────┐
          │          │   Router    │
          │          └──────┬──────┘
          │                 │
          │          ┌──────▼──────┐
          │          │  Services   │
          │          └──────┬──────┘
          │                 │
          │          ┌──────▼──────┐
          │          │ Repositories│
          │          └──────┬──────┘
          │                 │
          │          ┌──────▼──────┐
          │          │ PostgreSQL  │
          │          └─────────────┘
          │
          │
          └──────────── API REST


          DATA MIGRATION
                │
             Excel
                │
                ▼
       Pandas / openpyxl
                │
                ▼
          Format detector
                │
                ▼
           Normalisation
                │
                ▼
            Validation
                │
                ▼
         Fuzzy matching
                │
          ┌─────┴─────┐
          │           │
       certain      ambigu
          │           │
          ▼           ▼
       auto       validation
                     humaine
          │           │
          └─────┬─────┘
                ▼
        PASS 1 — CLIENTS
                │
                ▼
        PASS 2 — JOBS
                │
                ▼
       Transaction / batch
                │
                ▼
           PostgreSQL
                │
                ▼
         Import report
```

---

# 25. Ce que je changerais dans le DAT maintenant

### À conserver 🟢

* FastAPI
* PostgreSQL
* SQLAlchemy
* architecture Router → Service → Repository
* Docker Compose
* 1Panel
* VPS
* migration Excel
* Pandas
* `rapidfuzz`
* deux passes clients/jobs
* validation avant import
* transactions par batch
* backups
* restore tests
* mobile-first
* REST `/api/v1`

### À corriger 🟠

* ports
* healthchecks
* CI/CD
* idempotence
* fuzzy matching
* gestion des jobs orphelins
* backups/restore
* versions trop précises
* cron des bilans
* séparation importer/service

### À simplifier 🔵

* frontend
* Paperless si pas indispensable au MVP
* futures architectures `pay` / `iq`
* monitoring trop ambitieux
* tout ce qui ressemble à du « futur enterprise »

### À ne surtout pas présenter comme expérience 🟣

* expertise Vue/TypeScript
* expertise GitHub Actions
* expertise VPS/production
* maîtrise avancée de Python
* maîtrise avancée de 1Panel
* architecture financière complète
* architecture distribuée/scalable

---

## Et surtout : le projet devient intéressant pour ton entretien

Je ne le présenterais **pas** comme :

> « J'ai développé une application full-stack Python/Vue/DevOps. »

Je le présenterais plutôt comme :

> **« MB Chauffage est un projet métier que j'ai conçu pour digitaliser une entreprise CVC. Mon socle reste le backend et l'architecture Java, mais j'ai volontairement élargi le périmètre sur ce projet : FastAPI côté backend, PostgreSQL, Docker Compose et une première approche CI/CD et déploiement VPS. Le principal sujet technique était la migration de plus de 20 ans d'historique Excel vers une base relationnelle, avec normalisation, détection de doublons, fuzzy matching, validation et import en deux passes. »**

Ça colle beaucoup mieux à ton vrai profil.

### Prochaine étape

Le **plus gros morceau maintenant est `05-data-model.md` + `03-api-spec.md` + `06-workflows.md`**. C'est là qu'on peut vérifier si l'architecture que je viens de corriger est réellement cohérente avec les données et les API.

Le lien GitHub que tu m'as donné n'est pas récupérable depuis mon accès web actuellement ; je ne vais donc pas inventer le contenu de ces fichiers. Si tu les ajoutes ici, je peux faire la **revue niveau 2 : modèle SQL → API → workflows → cohérence bout-en-bout**, puis on transformera les points importants en questions d'entretien.
