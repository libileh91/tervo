# 1. Spécification Fonctionnelle — MB Chauffage

> **Objet :** Spécification fonctionnelle pour l'application MB Chauffage.
> **Client :** MB Chauffage, entreprise CVC avec 20+ ans d'historique.
> **Projet source :** Tervo (`docs/DAT/specs/01-specs-fonctionnelle.md`)

---

## Sommaire

1. Vision produit
2. Périmètre
3. Personas
4. Fiches clients
5. Jobs / Interventions
6. Formulaire d'inspection
7. Photos avant/après
8. Rapport post-intervention
9. Avis / Review client
10. **Devis et Factures (module financier)**
11. **Bilans mensuels (tableau de bord financier)**
12. **Import historique Excel**
13. **Administration (users, backups)**
14. User stories
15. Workflows

---

## 1. Vision produit

MB Chauffage passe d'une gestion papier/Excel à une application web centralisée. L'objectif est de :

- **Rassembler 20 ans de données** éparpillées dans des fichiers Excel en une base de données unique
- **Standardiser les processus** de devis, facturation, interventions
- **Donner aux techniciens** un outil mobile simple pour les interventions terrain
- **Donner au gérant/comptable** une vue consolidée de l'activité (bilans mensuels, impayés)
- **Pérenniser les données** avec des backups automatisés

---

## 2. Périmètre

### Modules

| Module               | Priorité | Description                                           |
| -------------------- | -------- | ----------------------------------------------------- |
| **Core**             | P0       | Auth, Clients, Jobs, Checklist — socle Tervo existant |
| **Data Migration**   | P0       | Import 20 ans d'Excels → PostgreSQL                   |
| **Interventions**    | P1       | Photos, Matériaux, Rapport PDF, Avis client           |
| **Module Financier** | P1       | Devis, Factures, Bilans                               |
| **Déploiement Prod** | P1       | VPS, 1Panel, SSL, Backups                             |
| **Admin**            | P2       | Gestion utilisateurs, import, logs                    |
| **Polish**           | P2       | PWA, Dark mode, Signature client, QR codes            |

### Hors périmètre MVP

- Module RH (congés, plannings avancés)
- Gestion de stock / inventaire pièces détachées
- Portail client (espace personnel avec historique)
- Intégration comptable (exports EBP, Sage, etc.)
- Application native mobile (iOS/Android) — la PWA suffit

---

## 3. Personas

### 3.1 Technicien CVC

- 3-5 techniciens, expérience 2-20 ans
- Utilise l'app sur smartphone (4G) pendant les interventions
- Besoins : planning du jour, fiche client, checklist, photos, rapport

### 3.2 Comptable / Gérant

- 1 personne, utilise un PC de bureau
- Besoins : créer des devis, facturer, suivre les paiements, consulter les bilans
- N'a jamais utilisé d'outil de gestion moderne — Excel uniquement

### 3.3 Admin technique

- Gère les utilisateurs, les imports de données, les sauvegardes
- Besoins : interface d'import Excel, dashboard de monitoring

---

## 4. Fiches clients

### Champs

| Champ         | Type        | Obligatoire | Note                        |
| ------------- | ----------- | ----------- | --------------------------- |
| `full_name`   | Texte       | ✅          | Nom complet ou entreprise   |
| `phone`       | Téléphone   | ✅          | Format libre                |
| `email`       | Email       |             |                             |
| `address`     | Adresse     | ✅          |                             |
| `postal_code` | Code postal |             |                             |
| `city`        | Ville       |             |                             |
| `siret`       | SIRET       | Si pro      | 14 chiffres                 |
| `tva_intra`   | TVA intra   | Si pro      | FRXX...                     |
| `type`        | Liste       | ✅          | particulier / professionnel |
| `notes`       | Texte long  |             | Code porte, étage, etc.     |

### Comportement

- Recherche par nom, téléphone, adresse
- Historique des interventions avec notes et avis
- Historique des devis et factures

---

## 5. Jobs / Interventions

Même modèle que Tervo, avec ces ajouts :

- `devis_id` : si l'intervention est liée à un devis accepté
- `facture_id` : si l'intervention a été facturée

### Workflow de statuts

```
planifié → en_cours → terminé
              ↓
           annulé
```

---

## 6. Formulaire d'inspection

Identique à Tervo (checklist pré/post intervention).

---

## 7. Photos avant/après

Identique à Tervo (upload multipart, thumbnails, min. 1 avant + 1 après).

---

## 8. Rapport post-intervention

Identique à Tervo (génération PDF automatique avec WeasyPrint).

---

## 9. Avis / Review client

Identique à Tervo (lien public avec token unique, note 1-5 + commentaire).

---

## 10. Devis et Factures (module financier)

### 10.1 Devis

**Champs :**

| Champ           | Type    | Description                                |
| --------------- | ------- | ------------------------------------------ |
| `numero`        | Auto    | DEV-AAAA-NNNNN                             |
| `client_id`     | FK      | Client concerné                            |
| `date_emission` | Date    | Date de création                           |
| `date_validite` | Date    | Date d'expiration (+30j)                   |
| `statut`        | Énum    | brouillon, envoyé, accepté, refusé, expiré |
| `lignes`        | Liste   | Description, quantité, prix unitaire       |
| `montant_ht`    | Calculé | Somme des lignes                           |
| `montant_ttc`   | Calculé | HT + TVA                                   |

**Workflow :**

1. Créer un devis (brouillon)
2. Ajouter des lignes (description, qté, prix HT)
3. Générer le PDF
4. Envoyer au client (email)
5. Statut : Envoyé
6. Client accepte → Statut : Accepté
7. Possibilité de créer le job + la facture

### 10.2 Factures

**Champs :**

| Champ           | Type        | Description                         |
| --------------- | ----------- | ----------------------------------- |
| `numero`        | Auto        | FAC-AAAA-NNNNN                      |
| `client_id`     | FK          | Client                              |
| `devis_id`      | FK nullable | Devis source                        |
| `date_emission` | Date        |                                     |
| `date_echeance` | Date        | +30j                                |
| `statut`        | Énum        | en_attente, payée, retard, annulée  |
| `lignes`        | Liste       | Reprise du devis ou saisie manuelle |
| `montant_ht`    | Calculé     |                                     |
| `montant_ttc`   | Calculé     |                                     |
| `date_paiement` | Date        | Date de règlement                   |
| `mode_paiement` | Liste       | virement, chèque, espèces, CB       |

**Workflow :**

1. Créer une facture (depuis un devis accepté ou de zéro)
2. Générer le PDF
3. Envoyer au client
4. Suivi : en_attente → payée (ou retard si date dépassée)
5. Dashboard des impayés avec alertes

### 10.3 Génération PDF

Les devis et factures utilisent un template HTML professionnel avec :

- Logo MB Chauffage
- Coordonnées de l'entreprise (SIRET, TVA, adresse)
- Coordonnées du client
- Tableau des lignes avec totaux HT, TVA, TTC
- Mentions légales (TVA, conditions de paiement)
- Date d'échéance pour les factures
- Date de validité pour les devis

---

## 11. Bilans mensuels (tableau de bord financier)

### 11.1 KPIs

| Indicateur                | Description                      |
| ------------------------- | -------------------------------- |
| Nombre d'interventions    | Jobs terminés dans le mois       |
| Nombre de devis émis      | Nouveaux devis créés             |
| Taux de conversion devis  | % de devis acceptés              |
| Nombre de factures émises |                                  |
| Total facturé HT / TTC    |                                  |
| Total encaissé            | Somme des factures payées        |
| Total impayé              | Somme des factures en retard     |
| Panier moyen HT           | Montant moyen par intervention   |
| Délai de paiement moyen   | Jours entre émission et paiement |

### 11.2 Calcul automatique

Un CRON mensuel (1er du mois à 2h00) calcule le bilan du mois précédent et le stocke dans la table `bilan`.

### 11.3 Affichage

Dashboard avec graphiques (courbes d'évolution, barres mensuelles, camembert statuts).

---

## 12. Import historique Excel

### 12.1 Fonctionnalités

- Upload de fichiers `.xlsx` ou `.xls`
- Détection automatique du mapping des colonnes
- Preview des 10 premières lignes avant import
- Validation complète (doublons, erreurs, champs obligatoires)
- Résolution manuelle des doublons clients (fuzzy matching)
- Import en 2 passes (clients → jobs)
- Rapport détaillé post-import (créés, ignorés, erreurs)
- Idempotent : ré-exécutable sans doublons

### 12.2 Formats acceptés

| Type     | Description                                        |
| -------- | -------------------------------------------------- |
| Clients  | Liste des clients avec coordonnées                 |
| Jobs     | Historique des interventions                       |
| Mixte    | Fichier combinant clients + jobs (le plus courant) |
| Devis    | Devis historiques                                  |
| Factures | Factures historiques                               |

### 12.3 Règles d'import

- Un client est considéré comme doublon si nom + téléphone matchent à 90% (fuzzy)
- Les jobs orphelins (client non trouvé) sont ignorés avec warning
- Les champs obligatoires manquants bloquent la ligne (pas d'import partiel)
- L'import est transactionnel : tout ou rien par lot

---

## 13. Administration

### 13.1 Gestion utilisateurs

- Créer / Modifier / Désactiver des comptes techniciens
- Créer des comptes comptables
- Réinitialiser les mots de passe

### 13.2 Logs d'import

- Historique de tous les imports (fichier, date, résultat, erreurs)
- Consultation du détail des erreurs par ligne

### 13.3 Backups

- Dashboard de statut des backups (dernier backup réussi, taille)
- Possibilité de déclencher un backup manuel
- Possibilité de restaurer un backup (admin uniquement)

---

## 14. User Stories

### US-01 — En tant que technicien, je veux consulter mon planning du jour

- Dashboard avec jobs du jour, statuts, prochain job
- Priorité : P0

### US-02 — En tant que technicien, je veux créer une intervention urgente

- Recherche rapide client → création job → démarrage immédiat
- Priorité : P0

### US-03 — En tant que technicien, je veux prendre des photos avant/après

- Upload depuis l'appareil photo du téléphone
- Priorité : P1

### US-04 — En tant que technicien, je veux générer un rapport d'intervention

- PDF automatique avec photos, checklist, matériaux
- Priorité : P1

### US-05 — En tant que comptable, je veux créer un devis

- Interface avec lignes dynamiques, calcul auto des totaux
- Priorité : P1

### US-06 — En tant que comptable, je veux transformer un devis en facture

- Un clic depuis le devis accepté
- Priorité : P1

### US-07 — En tant que comptable, je veux suivre les paiements

- Dashboard des factures en attente et en retard
- Priorité : P1

### US-08 — En tant que gérant, je veux consulter les bilans mensuels

- KPIs : CA, interventions, panier moyen, impayés
- Priorité : P1

### US-09 — En tant qu'admin, je veux importer l'historique Excel

- Upload → preview → validation → import
- Priorité : P0 (données historiques critiques)

### US-10 — En tant qu'admin, je veux gérer les utilisateurs

- CRUD utilisateurs, rôles, activation/désactivation
- Priorité : P2

---

## 15. Workflows

Voir `06-workflows.md` pour le détail des workflows :

1. Intervention complète de A à Z
2. Import historique Excel
3. Création devis → facture
4. Backup & restore
5. Déploiement production

---

---

                                              #########################################################

---

# 2- Spécification Technique — MB Chauffage

> **Objet :** Complément technique au DAT. Stack, CI/CD, infrastructure.
>
> **Partie principal :** `4-architecture` (DAT complet : archi, flux, PDF, photos, sécurité, déploiement).

---

## 1. Stack technique

### Backend

| Technologie     | Version | Rôle                                       |
| --------------- | ------- | ------------------------------------------ |
| **Python**      | 3.11+   | Langage principal                          |
| **FastAPI**     | 0.111+  | Framework API REST                         |
| **SQLAlchemy**  | 2.0+    | ORM (async)                                |
| **Pydantic**    | 2.x     | Validation / sérialisation                 |
| **Alembic**     | 1.13+   | Migrations DB                              |
| **PostgreSQL**  | 17      | Base de données (pas de SQLite)            |
| **Uvicorn**     | 0.30+   | Serveur ASGI                               |
| **python-jose** | 3.3+    | JWT                                        |
| **passlib**     | 1.7+    | Hashage bcrypt                             |
| **WeasyPrint**  | —       | Génération PDF (rapports, devis, factures) |
| **Pillow**      | 10.x    | Thumbnails photos                          |
| **pandas**      | 2.x     | Import données Excel                       |
| **openpyxl**    | 3.x     | Lecture fichiers .xlsx                     |
| **rapidfuzz**   | 3.x     | Fuzzy matching (dédoublonnage clients)     |
| **Pytest**      | 8.x     | Tests                                      |

### Frontend

| Technologie                    | Version   | Rôle                           |
| ------------------------------ | --------- | ------------------------------ |
| **Bun**                        | 1.2+      | Runtime JS                     |
| **Vue.js**                     | 3.x       | Framework UI (Composition API) |
| **TypeScript**                 | 5.x       | Typage                         |
| **Vue Router**                 | 4.x       | Routing SPA                    |
| **Pinia**                      | 2.x       | Gestion d'état                 |
| **Vue Query (TanStack)**       | 5.x       | Cache serveur                  |
| **PrimeVue**                   | 4.x       | Composants UI                  |
| **PrimeFlex**                  | 3.x       | Styling utilitaire             |
| **VeeValidate + Zod**          | 4.x / 3.x | Formulaires + validation       |
| **date-fns**                   | 3.x       | Manipulation dates             |
| **Chart.js** ou **ApexCharts** | —         | Graphiques bilans              |
| **Vite**                       | 6.x       | Bundler                        |

### DevOps

| Technologie        | Rôle                                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| **Docker**         | Conteneurisation                                                                               |
| **Docker Compose** | Orchestration production (app principale + services annexes)                                   |
| **1Panel**         | Reverse proxy (OpenResty) + SSL (Let's Encrypt) + File Manager + DB GUI + Backups + Monitoring |
| **GitHub Actions** | CI/CD                                                                                          |
| **pg_dump**        | Backups PostgreSQL                                                                             |
| **s3cmd**          | Sync backups → Hetzner Object Storage                                                          |
| **ufw**            | Firewall VPS                                                                                   |
| **fail2ban**       | Protection SSH                                                                                 |
| **UptimeRobot**    | Monitoring uptime                                                                              |
| **Paperless-ngx**  | GED : OCR, classification auto, recherche full-text, archivage documents                       |

---

## 2. Frontend (Vue.js)

### Arbre de routes

```
/login                       → LoginPage
/                            → DashboardPage

/clients                     → ClientListPage
/clients/new                 → ClientCreatePage
/clients/:id                 → ClientDetailPage
/clients/:id/edit            → ClientEditPage

/jobs                        → JobListPage
/jobs/new                    → JobCreatePage
/jobs/:id                    → JobDetailPage
/jobs/:id/inspection         → InspectionPage
/jobs/:id/report             → ReportPreviewPage

/devis                       → DevisListPage
/devis/new                   → DevisCreatePage
/devis/:id                   → DevisDetailPage

/factures                    → FactureListPage
/factures/new                → FactureCreatePage
/factures/:id                → FactureDetailPage

/bilans                      → BilanDashboard (comptable/admin)

/admin/import                → AdminImportPage
/admin/users                 → AdminUsersPage (futur)

/review/:token               → ReviewPage (public)
```

### Gestion d'état

| Store (Pinia)  | Usage                                       |
| -------------- | ------------------------------------------- |
| `authStore`    | Connexion, token, utilisateur courant, rôle |
| `jobStore`     | Jobs du jour, job courant                   |
| `devisStore`   | Devis courant, lignes                       |
| `factureStore` | Facture courante, lignes                    |

### Middleware de routes

- Routes `/devis`, `/factures`, `/bilans` → accessibles si `role = admin OU comptable`
- Routes `/admin/*` → accessibles si `role = admin`
- Redirection `/login` si non authentifié

---

## 3. Infrastructure — Docker Compose + 1Panel

> **Décision (révisée) :** Docker Swarm a été écarté après analyse du besoin réel. Aucun des critères qui justifieraient l'orchestration multi-nœud n'est présent à ce stade : pas de contrainte de charge identifiée (3-5 techniciens + 1 comptable), pas de SLA contractuel avec MB Chauffage, pas de date fixée pour un multi-node (modules `pay`/`iq` non scopés), et un budget serré qui pousse à éviter la RAM supplémentaire qu'un manager Swarm consommerait sur un VPS 4 Go déjà chargé (backend, frontend, Postgres, Paperless-ngx + sa propre DB/Redis). La complexité Swarm (réseaux overlay, `docker stack deploy` et ses pièges — pas de `build:` supporté, `env_file` mal géré, secrets à gérer différemment) n'est donc pas justifiée : c'est de la scalabilité anticipée pour un besoin qui n'existe pas. Migration possible vers Swarm plus tard, si un signal concret (charge mesurée, SLA, multi-node daté) apparaît.

### 3.1 docker-compose.prod.yml (production)

```yaml
version: "3.8"

services:
  backend:
    image: mbchauffage-backend:latest
    environment:
      - DATABASE_URL=postgresql://mbchauffage:${DB_PASSWORD}@postgres:5432/mbchauffage_db
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - uploads_data:/app/uploads
    ports:
      - "8000:8000"
    networks:
      - mb_network
    restart: unless-stopped
    depends_on:
      - postgres

  frontend:
    image: mbchauffage-frontend:latest
    ports:
      - "3000:80"
    networks:
      - mb_network
    restart: unless-stopped

  postgres:
    image: postgres:17
    environment:
      - POSTGRES_DB=mbchauffage_db
      - POSTGRES_USER=mbchauffage
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - mb_network
    restart: unless-stopped

volumes:
  postgres_data:
  uploads_data:

networks:
  mb_network:
    driver: bridge
```

> **1Panel n'a jamais eu besoin de gérer l'orchestrateur** (rôle inchangé, avec ou sans Swarm) : il route en reverse proxy vers `localhost:PORT`, peu importe ce qui tourne derrière. 1Panel gère : reverse proxy, SSL Let's Encrypt, File Manager, DB GUI, Backups Cron, Monitoring — tout ce qui **entoure** les conteneurs.

### 3.2 Logique de déploiement

```bash
# 1. Build
DOCKER_BUILDKIT=1 docker build -t mbchauffage-backend:latest -f backend/Dockerfile backend/
DOCKER_BUILDKIT=1 docker build -t mbchauffage-frontend:latest -f frontend/Dockerfile frontend/

# 2. Déploiement (recreate des services modifiés uniquement)
docker compose -f docker-compose.prod.yml up -d

# → Coupure de quelques secondes le temps du recreate du container backend/frontend
# → Acceptable : usage interne (3-5 techniciens), pas de trafic public continu,
#   pas de SLA contractuel nécessitant du zero-downtime
```

### 3.3 Configuration 1Panel

```
1Panel → Websites → Create Website → Reverse Proxy

Site 1: mbchauffage.com
  - Proxy Address: http://localhost:3000
  - HTTPS → Let's Encrypt → Enable (one-click)

Site 2: api.mbchauffage.com
  - Proxy Address: http://localhost:8000
  - HTTPS → Let's Encrypt → Enable (one-click)

1Panel → Cron Jobs → créer backup quotidien
1Panel → File Manager → accès aux uploads / PDF
1Panel → Database → PostgreSQL console

Site 3: docs.mbchauffage.com
  - Proxy Address: http://localhost:8000
  - HTTPS → Let's Encrypt → Enable (one-click)
```

### 3.4 Paperless-ngx — Docker Compose annexe

> Paperless-ngx tourne en Docker Compose séparé dans `/opt/paperless/`, indépendamment du stack applicatif principal. Service annexe avec ses propres dépendances (PostgreSQL 15, Redis 7).

```yaml
# /opt/paperless/docker-compose.yml
version: "3.8"

services:
  broker:
    image: redis:7
    container_name: paperless-broker
    volumes:
      - /opt/paperless/redis:/data
    restart: unless-stopped

  db:
    image: postgres:17
    container_name: paperless-db
    environment:
      POSTGRES_DB: paperless
      POSTGRES_USER: paperless
      POSTGRES_PASSWORD: ${PAPERLESS_DB_PASSWORD}
    volumes:
      - /opt/paperless/db:/var/lib/postgresql/data
    restart: unless-stopped

  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    container_name: paperless-ngx
    depends_on:
      - db
      - broker
    ports:
      - "8000:8000"
    volumes:
      - /opt/paperless/data:/usr/src/paperless/data
      - /opt/paperless/media:/usr/src/paperless/media
      - /opt/paperless/export:/usr/src/paperless/export
      - /opt/paperless/consume:/usr/src/paperless/consume
    environment:
      PAPERLESS_DBUSER: paperless
      PAPERLESS_DBPASS: ${PAPERLESS_DB_PASSWORD}
      PAPERLESS_DBHOST: db
      PAPERLESS_DBPORT: "5432"
      PAPERLESS_DBNAME: paperless
      PAPERLESS_REDIS: redis://broker:6379
      PAPERLESS_SECRET_KEY: ${PAPERLESS_SECRET_KEY}
      PAPERLESS_URL: https://docs.mbchauffage.com
      PAPERLESS_TIME_ZONE: Europe/Paris
      PAPERLESS_OCR_LANGUAGE: fra
      PAPERLESS_CONSUMER_POLLING: "60"
    restart: unless-stopped
```

**Lancement :**

```bash
cd /opt/paperless
docker compose up -d
```

**Site 1Panel :** `docs.mbchauffage.com → http://localhost:8000`

---

## 4. CI/CD (GitHub Actions)

```yaml
name: CI/CD

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_DB: mbchauffage_test
          POSTGRES_USER: mbchauffage
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { python-version: "3.11" }
      - run: uv sync --frozen
      - run: uv run pytest backend/tests/ --cov=app

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build images
        run: |
          docker build -t mbchauffage-backend:latest -f backend/Dockerfile backend/
          docker build -t mbchauffage-frontend:latest -f frontend/Dockerfile frontend/
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/mbchauffage
            git pull
            docker build -t mbchauffage-backend:latest -f backend/Dockerfile backend/
            docker build -t mbchauffage-frontend:latest -f frontend/Dockerfile frontend/
            docker compose -f docker-compose.prod.yml up -d
            # Recreate des services modifiés — quelques secondes de coupure, acceptable (usage interne)
```

---

## 5. Sécurité

| Couche           | Mesure                                                                                         |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| **Réseau**       | ufw : ports 22, 80, 443, 7410 uniquement                                                       |
| **SSH**          | fail2ban, clé SSH uniquement (pas de mot de passe)                                             |
| **SSL**          | Let's Encrypt via 1Panel (one-click), renouvellement automatique                               |
| **API**          | CORS whitelist (mbchauffage.com), rate limiting                                                |
| **Auth**         | JWT, bcrypt, refresh tokens                                                                    |
| **DB**           | Mot de passe dans `.env` (pas en clair dans le yaml)                                           |
| **Backups**      | Chiffrement GPG avant envoi Object Storage (P2)                                                |
| **Mises à jour** | unattended-upgrades pour les patchs de sécurité Ubuntu                                         |
| **Secrets**      | `.env` hors dépôt Git (`.gitignore`), permissions fichier restreintes (`chmod 600`) sur le VPS |

---

## 6. Backups

### Script backup quotidien (`/usr/local/bin/backup.sh`)

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/var/backups/mbchauffage
BUCKET=s3://mbchauffage-backups/daily/$(date +%Y/%m)

mkdir -p $BACKUP_DIR

# ── App DB ──────────────────────────────────────────────
docker exec mbchauffage_postgres pg_dump -U mbchauffage mbchauffage_db | gzip > $BACKUP_DIR/mbchauffage_${DATE}.sql.gz

# ── Paperless DB ─────────────────────────────────────────
docker exec paperless-db pg_dump -U paperless paperless | gzip > $BACKUP_DIR/paperless-db_${DATE}.sql.gz

# ── Paperless media ──────────────────────────────────────
tar czf $BACKUP_DIR/paperless-media_${DATE}.tar.gz -C /opt/paperless media consume

# ── Sync Object Storage ─────────────────────────────────
s3cmd put $BACKUP_DIR/mbchauffage_${DATE}.sql.gz $BUCKET/
s3cmd put $BACKUP_DIR/paperless-db_${DATE}.sql.gz $BUCKET/
s3cmd put $BACKUP_DIR/paperless-media_${DATE}.tar.gz $BUCKET/

# Rotation : garder 30 jours
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Test de restauration mensuel (`/usr/local/bin/restore-test.sh`)

```bash
#!/bin/bash
LATEST_BACKUP=$(ls -t /var/backups/mbchauffage/*.sql.gz | head -1)

# Créer une DB temporaire
docker exec mbchauffage_postgres psql -U mbchauffage -c "DROP DATABASE IF EXISTS mbchauffage_restore_test;"
docker exec mbchauffage_postgres psql -U mbchauffage -c "CREATE DATABASE mbchauffage_restore_test;"

# Restaurer
gunzip -c $LATEST_BACKUP | docker exec -i mbchauffage_postgres psql -U mbchauffage mbchauffage_restore_test

# Vérifier
TABLES=$(docker exec mbchauffage_postgres psql -U mbchauffage -d mbchauffage_restore_test -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "Tables: $TABLES"

# Nettoyer
docker exec mbchauffage_postgres psql -U mbchauffage -c "DROP DATABASE mbchauffage_restore_test;"

echo "Restore test OK"
```

---

---

                                              #########################################################

---

# 4- MB Chauffage — Architecture Technique (DAT)

> Document d'Architecture Technique — vue complète du système.
> Projet client réel : **MB Chauffage**, entreprise CVC avec 20+ ans de données historiques (Excel).

---

## 1. Objectif

Application Web **mobile-first** pour techniciens CVC d'une entreprise établie :

- Gérer les fiches clients et leur historique d'interventions (20 ans de données)
- Créer et suivre des jobs de A à Z (planifié → en cours → terminé)
- Remplir des checklists d'inspection pré/post-intervention
- Capturer des photos avant/après
- Générer des rapports PDF automatiques
- Recueillir les avis clients via lien de partage
- **Générer des devis et factures** (module financier)
- **Consulter les bilans mensuels/annuels** (tableau de bord financier)
- **Importer l'historique Excel existant** (data migration)

---

## 2. Stack technique

| Domaine           | Technologie                | Version    | Rôle                                                                                  |
| ----------------- | -------------------------- | ---------- | ------------------------------------------------------------------------------------- |
| **Backend**       | Python                     | 3.11+      | Langage                                                                               |
|                   | FastAPI                    | 0.111+     | Framework API REST                                                                    |
|                   | SQLAlchemy                 | 2.0+       | ORM (async)                                                                           |
|                   | Pydantic                   | 2.x        | Validation / sérialisation                                                            |
|                   | **Alembic**                | **1.13+**  | **Migrations DB (dès J1)**                                                            |
|                   | PostgreSQL                 | 17         | Base de données (unique, pas de SQLite)                                               |
|                   | Uvicorn                    | 0.30+      | Serveur ASGI                                                                          |
|                   | python-jose                | 3.3+       | JWT                                                                                   |
|                   | passlib                    | 1.7+       | Hashage bcrypt                                                                        |
|                   | WeasyPrint                 | —          | Génération PDF (rapports, devis, factures)                                            |
|                   | Pillow                     | 10.x       | Thumbnails photos                                                                     |
|                   | **pandas**                 | **2.x**    | **Import données Excel**                                                              |
|                   | **openpyxl**               | **3.x**    | **Lecture fichiers .xlsx**                                                            |
|                   | Pytest                     | 8.x        | Tests                                                                                 |
| **Frontend**      | Vue.js                     | 3.x        | Framework UI                                                                          |
|                   | **Bun**                    | **1.2+**   | **Runtime JS**                                                                        |
|                   | TypeScript                 | 5.x        | Typage                                                                                |
|                   | Vue Router                 | 4.x        | Routing                                                                               |
|                   | Pinia                      | 2.x        | Gestion d'état                                                                        |
|                   | Vue Query                  | 5.x        | Cache serveur                                                                         |
|                   | PrimeVue                   | 4.x        | Composants UI                                                                         |
|                   | PrimeFlex                  | 3.x        | Styling                                                                               |
|                   | VeeValidate + Zod          | 4.x / 3.x  | Formulaires                                                                           |
|                   | date-fns                   | 3.x        | Dates                                                                                 |
|                   | Vite                       | 6.x        | Bundler                                                                               |
| **DevOps**        | Docker + Compose           | —          | Conteneurisation (dev **et** production, service unique)                              |
|                   | **1Panel**                 | **2.x**    | **Reverse proxy (OpenResty) + SSL (Let's Encrypt) + File Manager + DB GUI + Backups** |
|                   | GitHub Actions             | —          | CI/CD                                                                                 |
|                   | **pg_dump**                | —          | **Backups quotidiens**                                                                |
|                   | **Hetzner Object Storage** | —          | **Stockage backups + photos**                                                         |
| **Documentation** | **Paperless-ngx**          | **latest** | **GED : OCR, classification auto, archivage devis/factures/rapports**                 |

---

## 3. Architecture générale

```
Navigateur mobile (Vue.js SPA)
    │ multipart (photos) + JSON (API)
    ▼
1Panel OpenResty (reverse proxy, Let's Encrypt SSL)
    │
    ├── mbchauffage.com → frontend (Nginx, port 3000) [Docker Compose]
    ├── api.mbchauffage.com → backend (FastAPI, port 8000) [Docker Compose]
    ├── docs.mbchauffage.com → Paperless-ngx (port 8000) [Docker Compose]
    ├── [futur] pay.mbchauffage.com → module paiement [Docker Compose]
    └── [futur] iq.mbchauffage.com → analytics [Docker Compose]
    │
    ▼
Docker Compose — stack applicatif          Docker Compose — Paperless (annexe)
    ├── mb-backend (port 8000)             ├── paperless-ngx (port 8000)
    ├── mb-frontend (port 3000)            ├── paperless-db (postgres:17)
    ├── mb-postgres (port 5432)            └── paperless-broker (redis:7)
    ├── [futur] mb-pay
    └── [futur] mb-iq
    │
    ▼
FastAPI Routers (api/v1/)       Services → Repositories → SQLAlchemy → PostgreSQL
    │
    ▼
Exporters → Génération PDF (WeasyPrint) — rapports, devis, factures

Exporters → Auto-archivage → Paperless API → documents OCRisés
```

---

## 4. Pourquoi 1Panel et pas Cloudflare Tunnel (ni Traefik) ?

### 4.1 Tunnel vs VPS direct

| Critère             | Cloudflare Tunnel (Tervo)                  | 1Panel (MB Chauffage)                           |
| ------------------- | ------------------------------------------ | ----------------------------------------------- |
| **Type de serveur** | Serveur domestique (mini-s1), IP dynamique | VPS avec IP publique fixe, ports 80/443 directs |
| **SSL**             | Automatique via Cloudflare Edge            | Let's Encrypt one-click dans l'UI 1Panel        |
| **Routage**         | Sous-domaines → `config.yml` tunnel + DNS  | UI Websites 1Panel (formulaire, pas de YAML)    |
| **Exposition**      | Connexion sortante uniquement (sécurisé)   | Ports 80/443 ouverts (ufw + fail2ban)           |
| **Adapté pour**     | Serveur domestique sans IP fixe            | VPS pro avec IP publique                        |

Sur un VPS, les ports 80/443 sont directement accessibles → pas besoin de tunnel.

### 4.2 Pourquoi 1Panel plutôt que Traefik

| Critère                | Traefik                                                   | 1Panel                                                     |
| ---------------------- | --------------------------------------------------------- | ---------------------------------------------------------- |
| **Reverse proxy**      | Labels Docker dans `docker-compose.yml`                   | UI graphique : Websites → Create → Reverse Proxy           |
| **SSL**                | Let's Encrypt (YAML config)                               | Let's Encrypt (one-click UI)                               |
| **Multi-domaine**      | Labels `traefik.http.routers.*` par service               | Un site par sous-domaine dans l'UI                         |
| **Apprentissage**      | Syntaxe YAML Traefik + middleware + certificate resolvers | Interface graphique qu'on maîtrise déjà                    |
| **File manager**       | ❌ Besoin d'un outil séparé                               | ✅ Navigateur de fichiers intégré (accès aux uploads, PDF) |
| **DB GUI**             | ❌ Besoin de phpPgAdmin/Adminer en plus                   | ✅ Console PostgreSQL intégrée                             |
| **Backups**            | ❌ Besoin de scripts cron manuels                         | ✅ Planificateur de backups intégré                        |
| **Monitoring**         | ❌ Besoin de Portainer/Dockge en plus                     | ✅ CPU, RAM, logs des conteneurs en direct                 |
| **Cron jobs**          | ❌ Besoin de crontab + scripts                            | ✅ Interface de planification intégrée                     |
| **Ajout d'un service** | Ajouter 5 labels Traefik dans le yaml, redéployer         | UI 1Panel : formulaire en 2 minutes                        |

**1Panel est un couteau suisse.** Traefik ne fait que le reverse proxy + SSL. Pour un projet client réel, 1Panel couvre tous les besoins opérationnels dans un seul outil :

1. **Reverse proxy** (OpenResty/Nginx) pour tous les sous-domaines
2. **SSL** Let's Encrypt en un clic (pas de YAML, pas de labels Docker)
3. **File manager** : le gérant peut télécharger un rapport PDF directement depuis le navigateur
4. **DB GUI** : vérifier une facture dans PostgreSQL sans ligne de commande
5. **Backups** : planifier les dumps PostgreSQL sans écrire de cron à la main
6. **Monitoring** : voir l'état des conteneurs, la RAM, les logs en un coup d'oeil

**Note :** 1Panel a été testé ponctuellement sur Tervo mais retiré depuis (remplacé par Cloudflare Tunnel, plus adapté à un serveur domestique sans IP fixe). Ce n'est donc pas un outil déjà maîtrisé en production — une phase de prise en main est à prévoir sur MB Chauffage, mais l'interface graphique reste nettement moins complexe à apprendre que la syntaxe Traefik (labels, middleware, certificate resolvers).

---

## 5. Infrastructure de production

### 5.1 VPS

| Spécification   | Valeur           |
| --------------- | ---------------- |
| **Fournisseur** | Hetzner CX22     |
| **vCPU**        | 2                |
| **RAM**         | 4 Go             |
| **Stockage**    | 40 Go NVMe       |
| **OS**          | Ubuntu 24.04 LTS |
| **Coût estimé** | ~8 €/mois        |

### 5.2 Topologie — Docker Compose + 1Panel

```
VPS (Hetzner CX22)
  │
  ├── 1Panel (port 7410) — UI d'administration
  │   ├── OpenResty (ports 80/443, mode bridge)
  │   │   ├── mbchauffage.com → localhost:3000 (frontend)
  │   │   ├── api.mbchauffage.com → localhost:8000 (backend)
  │   │   ├── docs.mbchauffage.com → localhost:8000 (Paperless-ngx)
  │   │   ├── [futur] pay.mbchauffage.com → localhost:5000 (pay)
  │   │   └── [futur] iq.mbchauffage.com → localhost:5100 (iq)
  │   ├── Let's Encrypt SSL (one-click par site)
  │   ├── File Manager → accès aux uploads, PDFs
  │   ├── Database GUI → exploration PostgreSQL
  │   └── Cron Jobs → backups planifiés
  │
  ├── Docker Compose — stack applicatif (docker-compose.prod.yml)
  │   ├── mb-frontend (Nginx static, port 3000 publié)
  │   ├── mb-backend (uvicorn, port 8000 publié, restart: unless-stopped)
  │   ├── mb-postgres (PostgreSQL 17, port 5432 interne)
  │   ├── [futur] mb-pay (port 5000 publié)
  │   └── [futur] mb-iq (port 5100 publié)
  │
  ├── Volumes Docker (bind mounts / volumes nommés)
  │   ├── postgres_data → /var/lib/docker/volumes/postgres_data
  │   ├── uploads_data → /var/lib/docker/volumes/uploads_data
  │   └── backup_data → /var/lib/docker/volumes/backup_data
  │
  ├── Paperless-ngx (Docker Compose, géré séparément)
  │   ├── paperless-ngx (port 8000 publié)
  │   ├── paperless-db (PostgreSQL 15)
  │   └── paperless-broker (Redis 7)
  │
  └── Backups (via 1Panel Cron)
      ├── pg_dump quotidien → Hetzner Object Storage
      ├── uploads sync → Hetzner Object Storage
      └── Restore test (1er du mois)
```

> **Docker Compose + 1Panel :** Compose orchestre les conteneurs (`restart: unless-stopped` pour l'auto-restart, `docker compose up -d` pour les mises à jour), 1Panel gère tout le reste (reverse proxy, SSL, file manager, DB GUI, backups, monitoring). Les services exposent leurs ports sur l'hôte, et 1Panel route via `localhost:PORT` — ce pattern est identique qu'il y ait ou non un orchestrateur multi-nœud derrière, donc le retrait de Swarm ne change rien côté 1Panel.
>
> **Swarm écarté :** pas de contrainte de charge, de SLA, ni de date fixée pour un multi-node (cf. section 4 du DAT technique). Réévaluation possible si l'un de ces signaux apparaît concrètement.

### 5.3 Backups quotidiens

```bash
# /etc/cron.d/mbchauffage-backup
0 3 * * * root pg_dump -U mbchauffage -h localhost mbchauffage_db | gzip > /var/backups/mbchauffage_$(date +\%Y\%m\%d).sql.gz
0 4 * * * root s3cmd put /var/backups/mbchauffage_$(date +\%Y\%m\%d).sql.gz s3://mbchauffage-backups/
0 5 1 * * root /usr/local/bin/restore-test.sh  # Test mensuel de restauration
```

**Règle d'or :** les backups sont **non-négociables**. Ce sont 20 ans de données réelles. On fait un backup quotidien + un test de restauration mensuel.

---

## 6. Data Migration — 20 ans d'Excels → PostgreSQL

C'est le défi technique majeur du projet. L'entreprise a 20 ans de données dans des fichiers Excel aux formats variables.

### 6.1 Problèmes identifiés

| Problème                                 | Impact                                               | Stratégie                                                  |
| ---------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| Formats Excel variables selon les années | Colonnes renommées, déplacées                        | Mapping par lot (un fichier de config par "année-type")    |
| Données manquantes                       | Champs vides, clients sans téléphone                 | Valeurs par défaut + logs d'avertissement                  |
| Doublons clients                         | Même client avec orthographe différente              | Fuzzy matching (`diffblib`) + validation manuelle          |
| Accents / encoding                       | É, È, À mal encodés dans vieux fichiers              | Normalisation unicode via `unicodedata`                    |
| Pas de FK relationnelle                  | Les jobs référencent les clients par nom, pas par ID | Résolution en deux passes : clients d'abord → jobs ensuite |

### 6.2 Pipeline d'import

```python
# backend/app/services/import_service.py (pseudo-code)
class ImportService:
    def import_excel(self, file_path: Path, import_config: dict) -> ImportResult:
        # 1. Détection du format (headers, colonnes)
        df = pd.read_excel(file_path, engine="openpyxl")
        mapping = self.detect_format(df, import_config)

        # 2. Passe 1 : Clients
        clients_df = df[mapping["client_columns"]].drop_duplicates()
        for _, row in clients_df.iterrows():
            client = self.find_or_create_client(row, mapping)

        # 3. Passe 2 : Jobs
        jobs_df = df[mapping["job_columns"]]
        for _, row in jobs_df.iterrows():
            client = self.match_client(row["client_name"])  # fuzzy
            job = self.create_job(client, row, mapping)

        # 4. Logs + rapport
        return ImportResult(created=..., skipped=..., errors=...)
```

### 6.3 Validation avant import

```bash
# L'admin uploade le fichier → preview → validation → import
POST /api/v1/admin/import/preview   # Aperçu des 10 premières lignes parsées
POST /api/v1/admin/import/validate  # Validation complète (doublons, erreurs)
POST /api/v1/admin/import/execute   # Import réel
```

---

## 7. Sécurité

- **Auth** : JWT (access token 30 min, refresh token 7 jours), hash bcrypt
- **Photos** : upload réservé aux techniciens authentifiés
- **Avis client** : endpoint public protégé par token unique (UUID), sans auth
- **CORS** : whitelist explicite (mbchauffage.com)
- **XSS** : échappement automatique des templates Vue.js
- **SQL injection** : SQLAlchemy paramétré
- **Firewall** : `ufw` sur le VPS (ports 22, 80, 443 uniquement)
- **Fail2Ban** : protection SSH
- **Backups chiffrés** : `gpg` avant envoi vers Object Storage (optionnel P2)

---

## 8. Structure du projet

```text
mbchauffage/
├── docs/
│   └── DAT/
│       └── MBchauffage-DAT/
│           ├── 04-architecture.md        ← ce document
│           ├── 05-data-model.md
│           ├── 06-workflows.md
│           ├── 07-implementation-roadmap.md
│           └── specs/
│               ├── 01-specs-fonctionnelle.md
│               ├── 02-spec-technique.md
│               └── 03-api-spec.md
├── backend/
│   ├── alembic/                          # Migrations DB
│   ├── alembic.ini
│   └── app/
│       ├── main.py, config.py
│       ├── core/           # database, security, deps, exceptions
│       ├── models/         # client, user, job, devis, facture, bilan...
│       ├── schemas/        # Pydantic
│       ├── repositories/   # accès DB
│       ├── services/       # logique métier + import_service
│       ├── api/v1/         # routes REST
│       │   ├── admin/      # import, users management
│       │   └── ...
│       ├── exporters/      # PDF (rapports, devis, factures)
│       └── importers/      # Import Excel
├── frontend/
│   └── src/
│       ├── main.ts, App.vue, router/
│       ├── stores/, composables/, api/
│       ├── pages/
│       │   ├── admin/      # Import, users, dashboard financier
│       │   └── ...
│       └── components/
├── deploy/
│   ├── docker-compose.yml          # Dev local
│   ├── docker-compose.prod.yml     # Production
│   └── backup/
├── paperless/
│   ├── docker-compose.yml          # Paperless-ngx
│   └── .env                        # Mots de passe (ne pas commiter)
│       ├── backup.sh               # Script pg_dump
│       └── restore-test.sh         # Test de restauration mensuel
├── data/
│   └── imports/                    # Fichiers Excel à importer
│       └── README.md               # Procédure d'import
└── README.md
```

---

## 9. Responsabilités des couches

| Couche                    | Responsabilité                                            |
| ------------------------- | --------------------------------------------------------- |
| **API** (FastAPI routers) | Endpoints REST, validation Pydantic, auth JWT             |
| **Services**              | Logique métier (statuts, timers, checklists, PDF, import) |
| **Repositories**          | Accès DB, requêtes SQLAlchemy                             |
| **Models**                | Mapping ORM, relations                                    |
| **Schemas**               | Validation entrée/sortie API                              |
| **Importers**             | Pipeline import Excel → PostgreSQL (pandas)               |
| **Frontend** (Vue.js)     | UI mobile-first, formulaires, photos, navigation          |

---

## 10. Principes d'architecture

- **Mobile-first** : interface pensée pour le smartphone, bottom nav
- **API REST versionnée** : `/api/v1/`
- **Auth JWT** : rôles `technician` / `admin` / `comptable`
- **Migrations DB dès J1** : Alembic + `--autogenerate` + `upgrade`
- **PostgreSQL uniquement** : pas de SQLite (les données sont réelles, pas de "dev db" simplifiée)
- **Validation bi-couche** : Pydantic serveur + Zod client
- **Cache** : Vue Query, invalidation après mutations
- **Photos** : upload multipart, thumbnails, stockage volume Docker + sync Object Storage
- **PDF** : généré côté serveur (WeasyPrint) — rapports, devis, factures
- **Avis client** : endpoint public sans auth, token unique
- **Backups** : quotidiens automatisés, test de restauration mensuel obligatoire
- **Idempotence** : le seed et l'import sont ré-exécutables sans effet de bord
- **1Panel + Docker Compose** : 1Panel pour le proxy/SSL/backups/files/DB/monitoring, Compose pour l'orchestration (`restart: unless-stopped`, recreate au déploiement) — pas de Swarm, aucun besoin multi-nœud identifié à ce stade

---

## 11. Comparaison Tervo vs MB Chauffage

| Dimension            | Tervo (perso)                   | MB Chauffage (client pro)                                                    |
| -------------------- | ------------------------------- | ---------------------------------------------------------------------------- |
| **Serveur**          | mini-s1 (domestique)            | VPS Hetzner CX22                                                             |
| **Orchestration**    | Docker Compose                  | Docker Compose (identique — pas de Swarm, aucun besoin multi-nœud identifié) |
| **Reverse Proxy**    | Cloudflare Tunnel               | **1Panel OpenResty** (reverse proxy) +                                       |
|                      |                                 | **1Panel Let's Encrypt** (SSL one-click)                                     |
| **SSL**              | Cloudflare Edge                 | Let's Encrypt via 1Panel                                                     |
| **DB**               | PostgreSQL (container existant) | PostgreSQL dédié (service Compose)                                           |
| **Backups**          | Aucun                           | Quotidiens + test mensuel                                                    |
| **Data Migration**   | Aucune (seed demo)              | Import 20 ans d'Excels                                                       |
| **Module financier** | Non                             | Devis, Factures, Bilans                                                      |
| **Domaine**          | tervoapp.com                    | mbchauffage.com                                                              |
| **Sous-domaines**    | 2 (api, www)                    | 4+ (api, pay, iq, www) — gérés via UI 1Panel Websites                        |
| **CI/CD**            | GitHub Actions                  | GitHub Actions → `docker compose up -d`                                      |
| **Monitoring**       | Aucun                           | 1Panel dashboard + UptimeRobot                                               |
| **Firewall**         | Routeur NAT                     | ufw + fail2ban                                                               |

---

> **Endpoints API :** `specs/03-api-spec.md`
> **Modèle de données :** `05-data-model.md`
> **Spécification technique :** `specs/02-spec-technique.md`
> **Projet source :** Tervo (`docs/DAT/04-architecture.md`)
