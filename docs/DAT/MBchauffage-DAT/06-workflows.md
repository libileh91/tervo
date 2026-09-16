# MB Chauffage — Workflows & UX Patterns

> **Objet :** Workflows utilisateur pour MB Chauffage.
>
> **Documents liés :** `specs/01-specs-fonctionnelle.md`, `specs/03-api-spec.md`

---

## 1. Personas

### 1.1 Technicien CVC

| Attribut | Valeur |
|----------|--------|
| Expérience | 2-20 ans en CVC |
| Tech-savvy | Variable (moyen) |
| Équipement | Smartphone (4G), parfois tablette |
| Contexte | Sur le terrain, sous-sols sans réseau |
| Tâches | Interventions, dépannage, maintenance |
| Besoin | Rapidité, simplicité, pas de double saisie |

**Frustrations :** Papier perdu, photos sur téléphone perso, rapport à refaire le soir.

### 1.2 Comptable / Gérant

| Attribut | Valeur |
|----------|--------|
| Expérience | 10-30 ans dans l'entreprise |
| Tech-savvy | Faible à moyen |
| Équipement | PC de bureau |
| Contexte | Bureau, gestion administrative |
| Tâches | Devis, facturation, bilans, suivi des paiements |
| Besoin | Centraliser les données, ne plus dépendre des Excels éparpillés |

**Frustrations :** Excels multiples incompatibles, données perdues, pas de vue consolidée.

### 1.3 Admin (IT / Gérant technique)

| Attribut | Valeur |
|----------|--------|
| Expérience | Variable |
| Tâches | Gestion utilisateurs, import données, monitoring |
| Besoin | Contrôle total, logs, sauvegardes |

---

## 2. Workflow principal : Intervention complète de A à Z

Identique au workflow Tervo (cf. `Tervo/docs/DAT/06-workflows.md`, section 2.1).

5 phases : Planning → Démarrage → Intervention → Clôture → Rapport & Avis.

---

## 3. Workflow : Import historique Excel

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 : PRÉPARATION                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. L'admin collecte les fichiers Excel historiques              │
│     (un fichier par année ou par type : clients, jobs, devis)    │
│                                                                  │
│  2. L'admin nettoie les fichiers (si nécessaire) :               │
│     - Uniformiser les noms de colonnes                           │
│     - Vérifier l'encoding (UTF-8)                                │
│     - Supprimer les lignes vides                                 │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 2 : UPLOAD & PREVIEW                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Interface Admin → Import → Upload fichier Excel                  │
│                                                                  │
│  POST /api/v1/admin/import/preview                               │
│  → Le serveur parse le fichier (pandas)                          │
│  → Affiche les 10 premières lignes parsées                       │
│  → Détecte automatiquement le mapping des colonnes               │
│                                                                  │
│  Preview :                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Fichier : clients_2015_2020.xlsx                         │    │
│  │ Détecté : 234 lignes, 8 colonnes                        │    │
│  │                                                          │    │
│  │ Mapping proposé :                                        │    │
│  │   Nom complet   → Colonne A "Nom Client"                 │    │
│  │   Téléphone     → Colonne B "Tel"                        │    │
│  │   Adresse       → Colonne C "Adresse" + D "Ville"        │    │
│  │   ...                                                    │    │
│  │                                                          │    │
│  │   [Modifier le mapping]  [Lancer l'import]               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 3 : VALIDATION                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /api/v1/admin/import/validate                              │
│  → Analyse complète sans insertion :                             │
│    - Détection des doublons (fuzzy matching sur noms)            │
│    - Champs obligatoires manquants                               │
│    - Formats invalides (téléphone, email)                        │
│    - Références croisées (jobs sans client connu)                │
│                                                                  │
│  Résultat :                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ✅ 210 clients prêts à importer                          │    │
│  │ ⚠️ 18 clients potentiellement en doublon (à vérifier)    │    │
│  │ ❌ 6 lignes en erreur (champs obligatoires manquants)    │    │
│  │                                                          │    │
│  │   [Voir les doublons]  [Voir les erreurs]                │    │
│  │   [Forcer l'import]    [Annuler]                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 4 : IMPORT RÉEL                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /api/v1/admin/import/execute                               │
│  → Insertion dans PostgreSQL                                     │
│  → Passe 1 : Clients (avec résolution des doublons)             │
│  → Passe 2 : Jobs (avec résolution des FK clients)              │
│  → Passe 3 : Devis / Factures (si présents)                     │
│  → Logs : ImportLog + ImportError                                │
│                                                                  │
│  Résultat final :                                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ✅ Import terminé                                        │    │
│  │ 📊 228 clients créés                                    │    │
│  │ 📊 1 247 jobs importés                                   │    │
│  │ ⚠️ 12 doublons résolus automatiquement                   │    │
│  │ ❌ 4 erreurs ignorées                                    │    │
│  │                                                          │    │
│  │   [Télécharger le rapport]  [Voir les données]           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Workflow : Création devis → Facture

```
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 : CRÉER UN DEVIS                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Interface Comptable → Devis → Nouveau devis                     │
│                                                                  │
│  Client : [Rechercher ou sélectionner]                           │
│                                                                  │
│  Lignes :                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Description                    Qté   Prix HT   Total     │    │
│  │ Maintenance chaudière gaz      1     350.00    350.00    │    │
│  │ Remplacement vanne thermostat  1     120.00    120.00    │    │
│  │ Main d'œuvre (2h)              2      65.00    130.00    │    │
│  │                                            HT : 600.00   │    │
│  │                                       TVA 20% : 120.00   │    │
│  │                                     Total TTC : 720.00   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [Sauvegarder brouillon]  [Générer PDF]  [Envoyer par email]    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 2 : SUIVI DU DEVIS                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Statuts : Brouillon → Envoyé → Accepté / Refusé / Expiré        │
│                                                                  │
│  Si Accepté → possibilité de créer le job correspondant          │
│             → possibilité de générer la facture                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 3 : GÉNÉRER LA FACTURE                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Depuis le devis accepté → "Transformer en facture"              │
│  → Les lignes du devis sont copiées dans la facture              │
│  → Numéro de facture auto-généré (FAC-2026-00042)                │
│  → Date d'échéance = date du jour + 30 jours                     │
│                                                                  │
│  [Générer PDF facture]  [Marquer comme payée]                    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 4 : SUIVI DES PAIEMENTS                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Dashboard financier :                                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 📊 Juillet 2026                                          │    │
│  │ Factures émises : 12    Total : 8 450.00 €               │    │
│  │ Payées : 8              Encaissé : 5 200.00 €            │    │
│  │ En retard : 3           Impayé : 2 150.00 €              │    │
│  │                                                          │    │
│  │ ⚠️ RETARD DE PAIEMENT                                   │    │
│  │ FAC-2026-00038  M. Dupont      1 200 €  (15 jours)      │    │
│  │ FAC-2026-00041  Sté MediaPro   1 850 €  (7 jours)       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Workflow : Backup & Restore

```
┌─────────────────────────────────────────────────────────────────┐
│  QUOTIDIEN (CRON 3h00)                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. pg_dump -U mbchauffage mbchauffage_db | gzip                │
│     → /var/backups/mbchauffage_20260712.sql.gz                   │
│                                                                  │
│  2. s3cmd put → Hetzner Object Storage                           │
│     → s3://mbchauffage-backups/daily/2026/07/12.sql.gz           │
│                                                                  │
│  3. Rotation : garder 30 jours de backups quotidiens             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  MENSUEL (CRON 1er du mois, 5h00)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. pg_dump complet (schema + data)                              │
│     → /var/backups/mbchauffage_20260701_full.sql.gz              │
│                                                                  │
│  2. Copie vers Object Storage + tag "keep-forever"               │
│                                                                  │
│  3. Test de restauration automatique :                           │
│     - Créer une DB temporaire `mbchauffage_restore_test`         │
│     - Restaurer le dump                                          │
│     - Vérifier : nombre de tables, comptage clients, jobs        │
│     - Nettoyer la DB temporaire                                  │
│     - Envoyer un email de confirmation                           │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  MANUEL (en cas d'incident)                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Sélectionner le backup à restaurer                           │
│     → Via l'interface admin ou en CLI                            │
│                                                                  │
│  2. Restaurer :                                                  │
│     gunzip mbchauffage_20260712.sql.gz | psql -U mbchauffage     │
│                                                                  │
│  3. Vérifier l'intégrité :                                       │
│     → Les jobs sont bien liés aux clients                       │
│     → Les photos sont accessibles                                │
│     → Les factures et devis sont présents                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Workflow : Déploiement production

```
┌─────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 : PROVISIONNER LE VPS                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  - Commander VPS Hetzner CX22 (Ubuntu 24.04)                    │
│  - Configurer le domaine mbchauffage.com (DNS → IP VPS)         │
│  - Installer Docker + Docker Swarm init (docker swarm init)     │
│  - Installer 1Panel (curl -sSL https://resource.1panel.cc...)   │
│  - Configurer ufw (ports 22, 80, 443, 7410)                    │
│  - Configurer fail2ban                                            │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 2 : DÉPLOYER L'APPLICATION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  git pull → docker build → docker stack deploy -c docker-stack.yml mbchauffage │
│                                                                  │
│  Les services Swarm exposent leurs ports sur l'hôte :            │
│  - mb-frontend → port 3000                                       │
│  - mb-backend  → port 8000                                       │
│                                                                  │
│  1Panel route le trafic internet vers localhost:3000/8000        │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 3 : CONFIGURER LE REVERSE PROXY                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1Panel → Websites → Create Website → Reverse Proxy              │
│                                                                  │
│  Site 1 : mbchauffage.com                                        │
│    Proxy Address: http://localhost:3000                          │
│    SSL : Let's Encrypt (one-click)                               │
│                                                                  │
│  Site 2 : api.mbchauffage.com                                    │
│    Proxy Address: http://localhost:8000                           │
│    SSL : Let's Encrypt (one-click)                               │
│                                                                  │
│  Note : OpenResty en mode bridge → utilise localhost:PORT       │
│  (pas besoin de résoudre les noms Swarm)                         │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 4 : MIGRATIONS + SEED                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  docker exec mb-backend-1 alembic upgrade head                   │
│  docker exec mb-backend-1 python -m app.seed                     │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 5 : CONFIGURER LES BACKUPS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1Panel → Cron Jobs → créer :                                    │
│    - Backup quotidien : pg_dump + s3cmd sync (3h00)             │
│    - Restore test mensuel (1er du mois, 5h00)                   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ÉTAPE 6 : VÉRIFICATIONS                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ https://mbchauffage.com → Frontend                           │
│  ✅ https://api.mbchauffage.com/docs → Swagger                   │
│  ✅ POST /auth/login → 200                                       │
│  ✅ SSL valide (Let's Encrypt via 1Panel)                        │
│  ✅ Backup quotidien fonctionnel (vérifié dans 1Panel Logs)      │
│  ✅ UptimeRobot configuré                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---


## 7. Workflow : Archivage documentaire (Paperless-ngx)

```
┌─────────────────────────────────────────────────────────────────┐
│  AUTOMATIQUE — Génération de documents                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Quand un rapport PDF est généré par l'app MB Chauffage :       │
│                                                                  │
│  1. Le backend génère le PDF (WeasyPrint)                        │
│  2. Le PDF est stocké sur le volume uploads                     │
│  3. Le backend appelle l'API Paperless :                        │
│     POST /api/documents/post_document/ avec :                   │
│       - document: le PDF                                        │
│       - title: "Rapport - M. Dupont - 15/07/2026"               │
│       - correspondent: client M. Dupont                         │
│       - document_type: "Rapport d'intervention"                  │
│                                                                  │
│  4. Paperless OCRise le PDF, classifie, indexe                  │
│  5. Le document est accessible depuis docs.mbchauffage.com      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  MANUEL — Drop folder                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Le dossier /opt/paperless/consume/ est surveillé par Paperless │
│                                                                  │
│  1. Déposer un PDF, photo ou scan dans le dossier               │
│  2. Paperless détecte automatiquement (polling 60s)             │
│  3. OCR, classification, indexation                             │
│                                                                  │
│  Utile pour :                                                    │
│  - Scanner des vieux devis papiers (les 20 ans d'archives)      │
│  - Uploader des factures fournisseurs reçues par email          │
│  - Ajouter les photos d'intervention en backup                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  API — Intégration depuis l'application                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Dans l'app MB Chauffage, on peut ajouter un onglet "Documents" │
│  sur la fiche client :                                           │
│                                                                  │
│  GET https://docs.mbchauffage.com/api/documents/?correspondent=X │
│  → Afficher les PDFs liés au client                             │
│                                                                  │
│  POST https://docs.mbchauffage.com/api/documents/post_document/ │
│  → Uploader un document depuis l'app                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

> **Document mis à jour le 13/07/2026**
> **Version :** 1.0 (DAT MB Chauffage)
> **Projet source :** `Tervo/docs/DAT/06-workflows.md`
> **Documents liés :** `specs/01-specs-fonctionnelle.md`, `specs/03-api-spec.md`
