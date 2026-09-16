# MB Chauffage — Data Model

## 1. Vue d'ensemble

Le modèle de données couvre **9 entités principales** : le modèle Tervo (Client, Job, Checklist, Photos, Matériaux, Review) + le module financier (Devis, Facture, LigneFacture, Bilan) + les tables d'import.

```
Client ─────────┐
                │
                ├───< Job (intervention)
                │       │
                │       ├───< ChecklistItem
                │       ├───< JobPhoto
                │       ├───< Material
                │       └───< Review
                │
                ├───< Devis (devis envoyé)
                │       └───< LigneDevis
                │
                └───< Facture (facture émise)
                        └───< LigneFacture

Bilan (agrégation mensuelle/annuelle) ← vue matérialisée / table calculée

ImportLog ────< ImportError
```

---

## 2. Tables existantes (reprises de Tervo)

Les tables `client`, `user`, `job`, `checklist_item`, `job_photo`, `material`, `review` sont identiques au modèle Tervo (cf. `Tervo/docs/DAT/05-data-model.md`).

**Modifications pour MB Chauffage :**

| Table    | Modification                    | Raison                                                       |
| -------- | ------------------------------- | ------------------------------------------------------------ |
| `user`   | Ajout rôle `comptable`          | Module financier : seul le comptable peut créer des factures |
| `client` | Ajout `siret`, `tva_intra`      | Obligatoire pour les factures professionnelles               |
| `job`    | Ajout `devis_id` FK → devis     | Lier une intervention au devis qui l'a déclenchée            |
| `job`    | Ajout `facture_id` FK → facture | Lier une intervention à sa facture                           |

### 2.1 Table `client` (étendue)

```sql
ALTER TABLE client ADD COLUMN siret VARCHAR(14);
ALTER TABLE client ADD COLUMN tva_intra VARCHAR(20);
ALTER TABLE client ADD COLUMN type VARCHAR(20) DEFAULT 'particulier';
-- 'particulier', 'professionnel'
```

---

## 3. Nouvelles tables — Module financier

### 3.1 Table `devis`

```sql
CREATE TABLE devis (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES client(id) ON DELETE CASCADE,
    numero VARCHAR(20) UNIQUE NOT NULL,        -- "DEV-2026-00042"
    date_emission DATE NOT NULL DEFAULT CURRENT_DATE,
    date_validite DATE,                         -- Date expiration du devis
    statut VARCHAR(20) DEFAULT 'brouillon',     -- 'brouillon', 'envoyé', 'accepté', 'refusé', 'expiré'
    montant_ht DECIMAL(10,2) DEFAULT 0,
    tva_taux DECIMAL(5,2) DEFAULT 20.0,        -- TVA en pourcentage
    montant_ttc DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    pdf_path VARCHAR(500),                      -- Chemin du PDF généré
    created_by INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_devis_client ON devis(client_id);
CREATE INDEX idx_devis_numero ON devis(numero);
CREATE INDEX idx_devis_statut ON devis(statut);
```

**Colonnes :**

| Colonne         | Type        | Description                                |
| --------------- | ----------- | ------------------------------------------ |
| `id`            | SERIAL      | PK                                         |
| `client_id`     | INTEGER     | FK → client                                |
| `numero`        | VARCHAR(20) | Numéro unique (DEV-AAAA-NNNNN)             |
| `date_emission` | DATE        | Date d'émission                            |
| `date_validite` | DATE        | Date de validité (généralement +30j)       |
| `statut`        | VARCHAR(20) | brouillon, envoyé, accepté, refusé, expiré |
| `montant_ht`    | DECIMAL     | Total HT calculé à partir des lignes       |
| `tva_taux`      | DECIMAL     | Taux de TVA appliqué (défaut 20%)          |
| `montant_ttc`   | DECIMAL     | Total TTC                                  |
| `notes`         | TEXT        | Notes libres                               |
| `pdf_path`      | VARCHAR     | Chemin du PDF généré                       |
| `created_by`    | INTEGER     | FK → user (qui a créé le devis)            |

### 3.2 Table `ligne_devis`

```sql
CREATE TABLE ligne_devis (
    id SERIAL PRIMARY KEY,
    devis_id INTEGER NOT NULL REFERENCES devis(id) ON DELETE CASCADE,
    description VARCHAR(500) NOT NULL,
    quantite DECIMAL(10,2) DEFAULT 1,
    unite VARCHAR(20) DEFAULT 'unité',         -- 'unité', 'heure', 'm²', 'forfait'
    prix_unitaire_ht DECIMAL(10,2) NOT NULL,
    montant_ht DECIMAL(10,2) GENERATED ALWAYS AS (quantite * prix_unitaire_ht) STORED,
    position INTEGER DEFAULT 0
);

CREATE INDEX idx_ligne_devis ON ligne_devis(devis_id);
```

### 3.3 Table `facture`

```sql
CREATE TABLE facture (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES client(id) ON DELETE CASCADE,
    devis_id INTEGER REFERENCES devis(id) ON DELETE SET NULL,
    numero VARCHAR(20) UNIQUE NOT NULL,        -- "FAC-2026-00042"
    date_emission DATE NOT NULL DEFAULT CURRENT_DATE,
    date_echeance DATE NOT NULL,                -- Date d'échéance de paiement
    statut VARCHAR(20) DEFAULT 'en_attente',   -- 'en_attente', 'payée', 'retard', 'annulée'
    montant_ht DECIMAL(10,2) DEFAULT 0,
    tva_taux DECIMAL(5,2) DEFAULT 20.0,
    montant_ttc DECIMAL(10,2) DEFAULT 0,
    date_paiement DATE,
    mode_paiement VARCHAR(50),                  -- 'virement', 'chèque', 'espèces', 'CB'
    notes TEXT,
    pdf_path VARCHAR(500),
    created_by INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_facture_client ON facture(client_id);
CREATE INDEX idx_facture_devis ON facture(devis_id);
CREATE INDEX idx_facture_numero ON facture(numero);
CREATE INDEX idx_facture_statut ON facture(statut);
CREATE INDEX idx_facture_echeance ON facture(date_echeance);
```

### 3.4 Table `ligne_facture`

```sql
CREATE TABLE ligne_facture (
    id SERIAL PRIMARY KEY,
    facture_id INTEGER NOT NULL REFERENCES facture(id) ON DELETE CASCADE,
    description VARCHAR(500) NOT NULL,
    quantite DECIMAL(10,2) DEFAULT 1,
    unite VARCHAR(20) DEFAULT 'unité',
    prix_unitaire_ht DECIMAL(10,2) NOT NULL,
    montant_ht DECIMAL(10,2) GENERATED ALWAYS AS (quantite * prix_unitaire_ht) STORED,
    position INTEGER DEFAULT 0
);

CREATE INDEX idx_ligne_facture ON ligne_facture(facture_id);
```

### 3.5 Table `bilan` (vue matérialisée ou table d'agrégation)

```sql
CREATE TABLE bilan (
    id SERIAL PRIMARY KEY,
    periode VARCHAR(7) NOT NULL,                -- '2026-06' (YYYY-MM)
    type VARCHAR(10) NOT NULL,                  -- 'mensuel', 'annuel'
    annee INTEGER NOT NULL,
    mois INTEGER,                               -- NULL pour bilan annuel

    -- Indicateurs
    nb_interventions INTEGER DEFAULT 0,
    nb_devis_emis INTEGER DEFAULT 0,
    nb_devis_acceptes INTEGER DEFAULT 0,
    nb_factures_emises INTEGER DEFAULT 0,
    nb_factures_payees INTEGER DEFAULT 0,

    -- Montants
    total_devis_ht DECIMAL(12,2) DEFAULT 0,
    total_factures_ht DECIMAL(12,2) DEFAULT 0,
    total_factures_ttc DECIMAL(12,2) DEFAULT 0,
    total_encaisse DECIMAL(12,2) DEFAULT 0,     -- Factures payées
    total_impaye DECIMAL(12,2) DEFAULT 0,       -- Factures en retard

    -- Moyennes
    panier_moyen_ht DECIMAL(10,2) DEFAULT 0,    -- Montant moyen par intervention
    delai_paiement_moyen_jours DECIMAL(5,1) DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_bilan_periode_type UNIQUE (periode, type)
);

CREATE INDEX idx_bilan_periode ON bilan(periode);
CREATE INDEX idx_bilan_annee ON bilan(annee);
```

---

## 4. Tables d'import

### 4.1 Table `import_log`

```sql
CREATE TABLE import_log (
    id SERIAL PRIMARY KEY,
    fichier VARCHAR(500) NOT NULL,               -- Nom du fichier importé
    type_import VARCHAR(50) NOT NULL,             -- 'clients', 'jobs', 'devis', 'complet'
    statut VARCHAR(20) DEFAULT 'en_cours',        -- 'en_cours', 'succes', 'echec', 'partiel'
    lignes_traitees INTEGER DEFAULT 0,
    lignes_creees INTEGER DEFAULT 0,
    lignes_ignorees INTEGER DEFAULT 0,
    lignes_erreurs INTEGER DEFAULT 0,
    rapport TEXT,                                 -- Résumé JSON de l'import
    imported_by INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Table `import_error`

```sql
CREATE TABLE import_error (
    id SERIAL PRIMARY KEY,
    import_log_id INTEGER NOT NULL REFERENCES import_log(id) ON DELETE CASCADE,
    ligne INTEGER NOT NULL,                      -- Numéro de ligne dans l'Excel
    colonne VARCHAR(255),                        -- Colonne problématique
    valeur TEXT,                                  -- Valeur erronée
    erreur VARCHAR(500) NOT NULL,                -- Message d'erreur
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_error_log ON import_error(import_log_id);
```

---

## 5. Schéma des relations

```
client (1) ──────→ (N) job
client (1) ──────→ (N) devis
client (1) ──────→ (N) facture
user (1) ──────→ (N) job

devis (1) ──────→ (N) ligne_devis
facture (1) ──────→ (N) ligne_facture
devis (1) ──────→ (N) facture                  (un devis peut être facturé en plusieurs fois — pro)
job (N) ──────→ (1) devis                       (une intervention issue d'un devis)
job (N) ──────→ (1) facture                     (une intervention facturée)

job (1) ──────→ (N) checklist_item
job (1) ──────→ (N) job_photo
job (1) ──────→ (N) material
job (1) ──────→ (1) review

import_log (1) ──────→ (N) import_error

## Documents (Paperless-ngx)

Paperless-ngx gère sa **propre base PostgreSQL** et son **propre stockage de fichiers**. L'application MB Chauffage n'a pas de table "document" dans sa DB — tout passe par l'API REST de Paperless.

```

App MB Chauffage (PostgreSQL) Paperless-ngx (PostgreSQL dédié)
│ │
├── client(id, name, ...) ├── document(id, title, content, ...)
├── job(id, client_id, ...) ├── correspondent(id, name, ...)
├── devis(id, client_id, ...) ├── document_type(id, name, ...)
└── facture(id, client_id, ...) └── storage_path (PDF sur disque)

```

**Lien entre les deux :**

- Le `correspondent` Paperless correspond au `client` de l'app (même nom)
- Les documents sont taggués par `document_type` ("Rapport", "Devis", "Facture")
- L'API Paperless permet de retrouver les documents d'un client via `?correspondent=X`
```

### Foreign Keys

```
job.client_id → client.id (CASCADE)
job.technician_id → user.id (SET NULL)
job.devis_id → devis.id (SET NULL)
job.facture_id → facture.id (SET NULL)

devis.client_id → client.id (CASCADE)
devis.created_by → user.id (SET NULL)

ligne_devis.devis_id → devis.id (CASCADE)

facture.client_id → client.id (CASCADE)
facture.devis_id → devis.id (SET NULL)
facture.created_by → user.id (SET NULL)

ligne_facture.facture_id → facture.id (CASCADE)

checklist_item.job_id → job.id (CASCADE)
job_photo.job_id → job.id (CASCADE)
material.job_id → job.id (CASCADE)
review.job_id → job.id (CASCADE)

import_error.import_log_id → import_log.id (CASCADE)
```

---

## 6. Règles métier

| Table            | Règle                                                                      |
| ---------------- | -------------------------------------------------------------------------- |
| `client`         | `siret` obligatoire si `type = professionnel`                              |
| `client`         | `tva_intra` obligatoire pour les clients pros intracommunautaires          |
| `user`           | Rôle `comptable` : seul accès au module financier (factures, bilans)       |
| `job`            | `started_at` renseigné quand `status = en_cours`                           |
| `job`            | `completed_at` renseigné quand `status = terminé`                          |
| `job`            | `completed_at` ≥ `started_at`                                              |
| `devis`          | `numero` auto-généré (DEV-AAAA-NNNNN)                                      |
| `devis`          | `date_validite` = `date_emission` + 30 jours                               |
| `facture`        | `numero` auto-généré (FAC-AAAA-NNNNN)                                      |
| `facture`        | `date_echeance` = `date_emission` + 30 jours                               |
| `facture`        | `montant_ttc` = `montant_ht` * (1 + `tva_taux`/100)                        |
| `ligne_devis`    | `montant_ht` calculé automatiquement (generated column)                    |
| `ligne_facture`  | `montant_ht` calculé automatiquement (generated column)                    |
| `bilan`          | Recalculé automatiquement via job CRON le 1er de chaque mois               |
| `import_log`     | `statut = succes` si 0 erreur, `partiel` si < 10% d'erreurs, `echec` sinon |
| `checklist_item` | Items pré par défaut à la création du job                                  |
| `job_photo`      | Min. 1 photo avant + 1 photo après obligatoires pour terminer              |
| `review`         | `share_token` généré à la fin du job                                       |
| `review`         | Un seul avis par job (UNIQUE job_id)                                       |

---

> **Document mis à jour le 12/07/2026**
> **Version :** 1.0 (DAT MB Chauffage — basé sur Tervo DAT v3.0)
> **Projet source :** `Tervo/docs/DAT/05-data-model.md`
