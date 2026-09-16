# Paperless-ngx vs Papra — Choix GED pour MB Chauffage

> **Date :** 13/07/2026
> **Contexte :** Sélection d'une solution de GED (Gestion Électronique de Documents) pour MB Chauffage.
> **Projet :** MB Chauffage — entreprise CVC avec 20+ ans d'archives papier et Excel.

---

## 1. Contexte MB Chauffage

### Le problème

L'entreprise MB Chauffage existe depuis plus de 20 ans. Sur cette période, elle a accumulé :

- **Des classeurs entiers de devis papiers** — signés par les clients, parfois scannés, parfois perdus
- **Des factures fournisseurs** — pièces détachées, matériels, fournitures
- **Des rapports d'intervention manuscrits** — écrits par les techniciens, souvent illisibles
- **Des photos d'installations** — stockées sur les téléphones personnels des techniciens (risque RGPD)
- **Des fichiers Excel éparpillés** — devis, factures, clients, avec des formats qui changent selon les années
- **Des e-mails avec pièces jointes** — devis reçus par mail, factures fournisseurs, etc.

**Aujourd'hui, si le gérant veut retrouver un devis précis de 2013**, il lui faut :
1. Aller dans le dossier Windows "Devis 2013"
2. Parcourir 200 fichiers nommés `devis_03_2013.xls`, `Devis_Mars_2013.xlsx`, `DEV-2013-03-15.xls`
3. Ouvrir chaque Excel jusqu'à trouver le bon

→ **C'est chronophage, source d'erreurs, et ça ne s'améliore pas avec le temps.**

### L'enjeu

Le passage à l'application MB Chauffage (FastAPI + Vue.js) ne résout que la partie **future** : nouveaux devis, nouvelles interventions, nouvelles photos. Mais **20 ans d'archives existantes** doivent être intégrées et rendues exploitables.

**L'application métier ne peut pas tout gérer :**
- Elle gère les données structurées (clients, jobs, devis, factures)
- Elle gère les PDFs générés par elle-même (rapports)
- Mais elle n'est pas faite pour : l'OCR de scans, la classification automatique, l'archivage longue durée, la recherche full-text sur 20 ans de documents

→ **Il faut un outil dédié : une GED (Gestion Électronique de Documents).**

### Les risques

| Risque | Impact si non traité |
|--------|---------------------|
| **Perte de documents** | Un scan mal rangé = un client qui n'a pas de trace de son devis 2015 |
| **RGPD** | Photos clients sur téléphones persos des techniciens → pas de droit à l'oubli possible, pas de traçabilité |
| **Productivité** | 20 min de recherche par document × 50 documents/mois = 16h perdues/mois |
| **Continuité** | Si le gérant part à la retraite, son savoir-faire documentaire part avec lui |

---

## 2. Les solutions candidates

### Paperless-ngx

> Site : https://docs.paperless-ngx.com | GitHub : ~20 000 stars | Maturité : ~8 ans

Paperless-ngx est la référence open source en gestion documentaire. C'est un fork de Paperless (2016), complètement réécrit et maintenu depuis 2021.

**Philosophie :** "Transforme tes documents papier en fichiers consultables, classés et indexés."

**Stack technique :**
- Python (Django) — back-end solide, mature
- PostgreSQL — stockage fiable, recherche full-text
- Redis — queue de tâches OCR asynchrone
- Tesseract — moteur OCR de référence

**Concept clé :** Chaque document a un **correspondant** (client/fournisseur), un **type** (devis/facture/rapport), et des **tags** (urgent/retenue/année). L'utilisateur classe les premiers documents, et le système **apprend automatiquement** via un modèle ML intégré pour proposer des classements ensuite.

**Déploiement :** 3 conteneurs Docker (web + Redis + PostgreSQL).

---

### Papra

> Site : https://papra.app | GitHub : ~5 000 stars | Maturité : ~1 an

Papra est un nouveau venu (première release ~2024/2025). Par sa propre description : une "plateforme minimaliste d'archivage et de gestion documentaire". Conçu en réaction à la complexité de Paperless-ngx.

**Philosophie :** "Simple, accessible à tous, facile à déployer."

**Stack technique :**
- TypeScript (SolidJS frontend + HonoJS backend)
- Drizzle ORM sur **SQLite** par défaut (Turso optionnel pour le cloud)
- CadenceMQ — leur propre queue de tâches (pas de Redis)
- Content extraction (OCR basique, pas Tesseract)

**Concept clé :** Organisations + tags. Pas de correspondants ou types structurés. Plus orienté "boîte à archives personnelle" que "GED professionnelle".

**Déploiement :** 1 seul conteneur Docker (tout-en-un). Simple.

---

## 3. Comparatif détaillé

### 3.1 Fiche d'identité

| Critère | Paperless-ngx | Papra |
|---------|:------------:|:-----:|
| **Création** | ~2016 (fork ngx 2021) | ~2024/2025 |
| **Stars GitHub** | **~20 000** | 5 000 |
| **Forks** | **~1 100** | 257 |
| **Langage** | Python (Django) | TypeScript (SolidJS + HonoJS) |
| **Base de données** | **PostgreSQL** | SQLite / Turso |
| **Queue / OCR** | Redis + Tesseract | CadenceMQ + extraction basique |
| **License** | **GPL-3.0** (entreprise-friendly) | AGPL-3.0 (restrictif SaaS) |
| **Conteneurs** | 3 (web + broker + db) | 1 (tout-en-un) |
| **RAM nécessaire** | ~1 Go | ~300 Mo |
| **Version actuelle** | 3.x (stable, releases régulières) | 26.x (102 releases en 1 an — rythme intense) |
| **Auteur principal** | Équipe de mainteneurs | Corentin Thomasset (1 personne) |

### 3.2 Matching avec les besoins MB Chauffage

| Besoin MB Chauffage | Paperless-ngx | Papra | Gagnant |
|---|---|---|---|
| **OCR de vieux documents scannés** | ✅ Tesseract OCR complet : auto-rotation, binarization, despeckling, détection de langue | 🟡 "Content extraction" : basique, pas de pipeline OCR complet | **Paperless** |
| **Classification par client** | ✅ **Correspondant natif** — doc lié à un client, un contact | ❌ Tags uniquement — pas de notion de "client" | **Paperless** |
| **Classification automatique** | ✅ ML intégré : apprend des classements manuels, propose le suivant | 🟡 Règles de tagging statiques (si tag X alors tag Y) | **Paperless** |
| **Recherche full-text** | ✅ PostgreSQL FTS — rapide, précis, multi-langue | ✅ Content extraction indexée | Égal |
| **API REST pour intégration app** | ✅ Complète : documents, correspondants, types, tags | ✅ API + SDK + Webhooks (SDK en bonus) | Légèrement Papra |
| **Maturité et stabilité** | ✅ 8+ ans, 20k stars, communauté large | 🟡 1 an, 5k stars, 1 développeur principal | **Paperless** |
| **Partage de documents** | ✅ Liens de partage | ✅ Liens avec expiration + mot de passe | **Papra** |
| **Multi-organisations** | ❌ Pas natif | ✅ Organizations | **Papra** |
| **Simplicité de déploiement** | 🟡 3 conteneurs | ✅ 1 conteneur | **Papra** |
| **Consume folder (drop auto)** | ✅ Dossier surveillé | ✅ Folder ingestion | Égal |
| **Consommation email** | ✅ | ✅ | Égal |
| **Documentation / Support** | ✅ Docs riches, forum actif, Wiki | 🟡 Docs en construction, Discord | **Paperless** |
| **Application mobile** | PWA (fonctionnelle) | ❌ "Maybe one day" | **Paperless** |

### 3.3 Scénarios réels

#### Scénario 1 — Le gérant retrouve un devis de 2010

```
Le gérant : "Je veux le devis que j'avais fait pour M. Lambert en mars 2010"
```

**Avec Paperless-ngx :**
1. Ouvrir Paperless → barre de recherche
2. Taper : `Lambert devis 2010`
3. Résultat : 1 document — le bon — affiché directement
4. Pourquoi ? Le scan a été OCRisé (Tesseract), le correspondant "Lambert" a été assigné, le type "Devis" a été mis

**Avec Papra :**
1. Ouvrir Papra → barre de recherche
2. Taper : `Lambert devis 2010`
3. Résultat : plusieurs documents contenant le mot "Lambert" dans le texte extrait — mélange devis, factures, courriers
4. Pourquoi ? Pas de correspondant, pas de type — seulement des tags. La recherche se base sur le texte brut extrait

➡ **Paperless gagne : la structure correspondant + type filtre immédiatement 90% du bruit.**

#### Scénario 2 — Un technicien prend une photo, elle doit être liée au client

```
But : associer une photo de chaudière au client M. Dupont
```

**Avec Paperless :**
- L'app MB Chauffage upload la photo via `POST /api/documents/post_document/`
- Paramètres : `correspondent_id=42` (M. Dupont), `document_type_id=5` (Photo intervention)
- ✅ La photo est automatiquement liée au client dans Paperless

**Avec Papra :**
- L'app upload via l'API Papra
- Paramètres : tags `["photo", "intervention"]` + custom field `client: "M. Dupont"`
- 🟡 Le tag ne relie pas le document à une entité métier — juste un mot-clé

➡ **Paperless : le correspondant est une entité de premier ordre, pas un tag.**

#### Scénario 3 — Import massif de 20 ans d'archives

```
L'admin upload 5000 scans de 2005 à 2025
```

**Avec Paperless :**
1. Déposer les fichiers dans `/consume/`
2. Paperless OCRise chaque document en arrière-plan (file d'attente Redis)
3. Pour les 50 premiers, l'admin classe manuellement (correspondant + type + date)
4. Dès le 51e, Paperless **propose automatiquement** le classement (ML)
5. Au bout de 200 documents, le système classe tout seul avec 95% de précision

**Avec Papra :**
1. Déposer les fichiers dans le folder d'ingestion
2. OCR basique (content extraction) — pas de vrai OCR
3. L'admin doit tagger **chaque document** manuellement (pas de ML)
4. Possibilité de créer des règles de tagging pour automatiser partiellement

➡ **Paperless : le ML change la donne sur un volume de 5000 documents.**

---

## 4. Forces et faiblesses

### Forces de Paperless-ngx ✅

| Force | Pourquoi c'est crucial pour MB Chauffage |
|-------|------------------------------------------|
| **OCR Tesseract** | Pipeline OCR professionnel : auto-rotation, correction perspective, binarisation, français supporté nativement |
| **Correspondant** | Mappe parfaitement au client de l'app métier — lien direct entre les deux systèmes |
| **Classification ML** | Sur 5000+ documents historiques, l'auto-classification fait gagner des dizaines d'heures |
| **Maturité 8 ans** | Projet stable, pas de risque d'abandon — critical pour des archives longue durée |
| **PostgreSQL** | Même SGBD que l'app métier — backup unifié, expertise partagée |
| **GPL-3.0** | Licence permissive — pas de contrainte de publication des modifications |
| **Communauté** | Documentation riche, Stack Overflow, forums, résolution de bugs active |

### Faiblesses de Paperless-ngx 🟡

| Faiblesse | Mitigation |
|-----------|-----------|
| 3 conteneurs (web + broker + db) | Sur un VPS 4 Go, 1 Go pour Paperless est acceptable |
| Pas de multi-organisation natif | Pas nécessaire — MB Chauffage est une entreprise unique |
| Pas de partage avec expiration | Le partage simple suffit (envoi du lien par email) |

### Forces de Papra ✅

| Force | Mais... |
|-------|---------|
| **1 seul conteneur** | Simple, mais pas d'OCR sérieux, pas de ML, pas de correspondant |
| **Organizations** | Fonctionnalité intéressante mais pas utile pour une seule entreprise |
| **Partage avec expiration** | Fonctionnalité avancée mais secondaire |
| **SDK** | Sympa, mais une API REST suffit pour l'intégration |
| **Croissance rapide** | 5k stars en 1 an, mais pas encore assez mature pour des archives pro |

### Faiblesses de Papra 🔴

| Faiblesse | Impact |
|-----------|--------|
| **Pas de correspondant** | Impossible de lier un document à un client de l'app métier |
| **OCR basique** | Les scans anciens (qualité variable) ne seront pas correctement OCRisés |
| **Pas de ML** | Classification manuelle de 5000 documents = jours de travail |
| **SQLite** | Pas de recherche full-text avancée, backup complexe, pas de réplication |
| **AGPL-3.0** | Si on modifie Papra (custom fields, etc.), les modifs doivent être publiées |
| **1 développeur** | Si Corentin arrête, le projet meurt |

---

## 5. Verdict

```diff
+  Paperless-ngx est le choix pour MB Chauffage
```

| La raison #1 | Le problème qu'elle résout |
|---|---|
| **OCR Tesseract** | Sans OCR pro, les 20 ans de scans ne sont pas exploitables |
| **Correspondant** | Le document est lié au client — pas juste un mot-clé dans un tag |
| **Classification ML** | Passer de 5000 documents à classer → 50 à classer (le ML fait le reste) |
| **Maturité 8 ans** | Les archives doivent survivre à l'outil qui les gère |

**Papra est un projet prometteur** (5k stars en 1 an, très actif), mais il arrive trop tôt pour MB Chauffage. Il répond à un besoin de GED **personnelle et légère**, pas à un besoin professionnel d'archivage longue durée avec OCR, correspondants et classification automatique.

---

## 6. Impact sur l'architecture MB Chauffage

### Si Paperless est choisi (recommandé)

```
1Panel → Websites → Reverse Proxy
  ├── mbchauffage.com       → Swarm (app métier)
  ├── api.mbchauffage.com   → Swarm (backend)
  └── docs.mbchauffage.com  → Paperless-ngx (3 conteneurs Docker Compose)
```

| Aspect | Détail |
|--------|--------|
| **Déploiement** | Docker Compose dans `/opt/paperless/` (3 conteneurs) |
| **Reverse proxy** | 1Panel : docs.mbchauffage.com → localhost:8000 |
| **SSL** | Let's Encrypt one-click via 1Panel |
| **Base de données** | PostgreSQL 17 (dédiée, ou partagée avec l'app) |
| **Stockage** | Volume Docker : `/opt/paperless/media/` pour les documents |
| **Backup** | pg_dump de paperless-db + sync des médias vers Object Storage |
| **Intégration app** | POST /api/documents/post_document/ depuis le backend FastAPI |

### Si Papra était choisi (non retenu)

```
1Panel → Websites → Reverse Proxy
  └── docs.mbchauffage.com  → Papra (1 conteneur Docker)
```

| Aspect | Détail |
|--------|--------|
| **Déploiement** | `docker run -d --name papra ghcr.io/papra-hq/papra:latest` |
| **Base de données** | SQLite dans le conteneur |
| **Intégration app** | API REST possible |
| **⚠️ Problème** | Pas de correspondant client, pas d'OCR pro, pas de ML |

---

> **Document lié :** `notes/backend/deploy/paperless-ngx.md` (procédure d'installation Paperless)
> **Architecture principale :** `04-architecture.md`
