# Tervo — Modèle de Données

> **Objet :** Schéma relationnel complet de Tervo.
>
> **Documents liés :** `04-architecture.md`, `specs/03-api-spec.md`

---

## 1. Vue d'ensemble

```
Client
    │
    ├───< Job (intervention)
    │        │
    │        ├───< ChecklistItem
    │        ├───< JobPhoto
    │        ├───< Material
    │        └───< Review
    │
    ├───< Devis (phase 2) ────< LigneDevis
    │        │
    │        └───< Facture (phase 2) ────< LigneFacture
    │
    └───< ContratSAV (phase 2)

Produit ────< ExpositionShowroom
Produit ────< Stock (phase 2)

ImportBatch ────< ImportError ────< ImportRecord
```

**Légende :** les entités marquées *(phase 2)* sont spécifiées ici mais hors périmètre du Stage 6.

---

## 2. Entités cœur

### 2.1 `client`

```sql
CREATE TABLE client (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    address VARCHAR(500) NOT NULL,
    postal_code VARCHAR(20),
    city VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_client_phone ON client(phone);
CREATE INDEX idx_client_name ON client(full_name);
CREATE INDEX idx_client_city ON client(city);
```

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | SERIAL | PK |
| `full_name` | VARCHAR(255) | Nom complet (ou entreprise) |
| `phone` | VARCHAR(50) | Téléphone |
| `email` | VARCHAR(255) | Email |
| `address` | VARCHAR(500) | Adresse |
| `postal_code` | VARCHAR(20) | Code postal |
| `city` | VARCHAR(255) | Ville |
| `notes` | TEXT | Notes (code porte, étage…) |

> **Extension pro (phase 2) :** `siret VARCHAR(14)`, `tva_intra VARCHAR(20)`, `type VARCHAR(20)` (`particulier` / `professionnel`).

---

### 2.2 `user`

```sql
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'technician',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

| Colonne | Type | Description |
|---------|------|-------------|
| `username` | VARCHAR(100) | Identifiant unique |
| `email` | VARCHAR(255) | Email unique |
| `hashed_password` | VARCHAR(255) | Hash bcrypt |
| `role` | VARCHAR(20) | `technician`, `admin` |
| `is_active` | BOOLEAN | Compte actif |

> **Extension (phase 2) :** rôle `comptable` pour le module financier.

---

### 2.3 `job`

```sql
CREATE TABLE job (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL,
    technician_id INTEGER,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'planifié',
    priority VARCHAR(20) DEFAULT 'normale',
    scheduled_date DATE NOT NULL,
    scheduled_start_time TIME,
    scheduled_end_time TIME,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    observations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_client FOREIGN KEY (client_id)
        REFERENCES client(id) ON DELETE CASCADE,
    CONSTRAINT fk_technician FOREIGN KEY (technician_id)
        REFERENCES "user"(id) ON DELETE SET NULL,
    CONSTRAINT chk_status CHECK (status IN ('planifié', 'en_cours', 'terminé', 'annulé')),
    CONSTRAINT chk_priority CHECK (priority IN ('basse', 'normale', 'haute', 'urgente'))
);

CREATE INDEX idx_job_client ON job(client_id);
CREATE INDEX idx_job_technician ON job(technician_id);
CREATE INDEX idx_job_status ON job(status);
CREATE INDEX idx_job_scheduled_date ON job(scheduled_date);
CREATE INDEX idx_job_priority ON job(priority);
```

| Colonne | Type | Description |
|---------|------|-------------|
| `client_id` | INTEGER | FK → client |
| `technician_id` | INTEGER | FK → user |
| `title` | VARCHAR(255) | Titre |
| `description` | TEXT | Description détaillée |
| `status` | VARCHAR(20) | planifié, en_cours, terminé, annulé |
| `priority` | VARCHAR(20) | basse, normale, haute, urgente |
| `scheduled_date` | DATE | Date planifiée |
| `scheduled_start_time` / `scheduled_end_time` | TIME | Créneau |
| `started_at` | TIMESTAMP | Début réel |
| `completed_at` | TIMESTAMP | Fin réelle |
| `observations` | TEXT | Observations |

---

### 2.4 `checklist_item`

```sql
CREATE TABLE checklist_item (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    category VARCHAR(20) NOT NULL,
    label VARCHAR(255) NOT NULL,
    checked BOOLEAN DEFAULT FALSE,
    note TEXT,
    position INTEGER DEFAULT 0,

    CONSTRAINT fk_job FOREIGN KEY (job_id)
        REFERENCES job(id) ON DELETE CASCADE,
    CONSTRAINT chk_category CHECK (category IN ('pre_intervention', 'post_intervention'))
);

CREATE INDEX idx_checklist_job ON checklist_item(job_id);
```

| Colonne | Type | Description |
|---------|------|-------------|
| `category` | VARCHAR(20) | pré ou post intervention |
| `label` | VARCHAR(255) | Intitulé |
| `checked` | BOOLEAN | Coché ou non |
| `note` | TEXT | Note libre |
| `position` | INTEGER | Ordre d'affichage |

---

### 2.5 `job_photo`

```sql
CREATE TABLE job_photo (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    category VARCHAR(20) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    thumbnail_path VARCHAR(500),
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_job FOREIGN KEY (job_id)
        REFERENCES job(id) ON DELETE CASCADE,
    CONSTRAINT chk_photo_category CHECK (category IN ('avant', 'après'))
);

CREATE INDEX idx_photo_job ON job_photo(job_id);
```

---

### 2.6 `material`

```sql
CREATE TABLE material (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    quantity VARCHAR(50),
    position INTEGER DEFAULT 0,

    CONSTRAINT fk_job FOREIGN KEY (job_id)
        REFERENCES job(id) ON DELETE CASCADE
);

CREATE INDEX idx_material_job ON material(job_id);
```

---

### 2.7 `review`

```sql
CREATE TABLE review (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL UNIQUE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    reviewer_name VARCHAR(255),
    share_token VARCHAR(64) UNIQUE NOT NULL,
    share_token_expires_at TIMESTAMP,
    submitted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_job FOREIGN KEY (job_id)
        REFERENCES job(id) ON DELETE CASCADE
);

CREATE INDEX idx_review_share_token ON review(share_token);
```

| Colonne | Type | Description |
|---------|------|-------------|
| `job_id` | INTEGER | FK → job (UNIQUE : un avis par job) |
| `rating` | INTEGER | 1 à 5 |
| `share_token` | VARCHAR(64) | Token unique du lien public |
| `share_token_expires_at` | TIMESTAMP | Expiration (30 jours) |

---

## 3. Catalogue produits

### 3.1 `produit`

| Champ | Type | Obligatoire | Note |
|-------|------|:-----------:|------|
| `reference` | VARCHAR(100) | ✅ | Unique (interne ou constructeur) |
| `nom` | VARCHAR(255) | ✅ | |
| `categorie` | VARCHAR(20) | ✅ | clim, chaudiere, pac, chauffage, autre |
| `marque` | VARCHAR(100) | | |
| `prix_achat_ht` | DECIMAL(10,2) | | |
| `prix_vente_ht` | DECIMAL(10,2) | ✅ | |
| `photo` | VARCHAR(500) | | |
| `statut` | VARCHAR(20) | ✅ | en_exposition, en_stock, discontinue |

```sql
CREATE TABLE produit (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(100) UNIQUE NOT NULL,
    nom VARCHAR(255) NOT NULL,
    categorie VARCHAR(20) NOT NULL,
    marque VARCHAR(100),
    prix_achat_ht DECIMAL(10,2),
    prix_vente_ht DECIMAL(10,2) NOT NULL,
    photo VARCHAR(500),
    statut VARCHAR(20) NOT NULL DEFAULT 'en_stock',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_produit_categorie
        CHECK (categorie IN ('clim', 'chaudiere', 'pac', 'chauffage', 'autre')),
    CONSTRAINT chk_produit_statut
        CHECK (statut IN ('en_exposition', 'en_stock', 'discontinue'))
);

CREATE INDEX idx_produit_categorie ON produit(categorie);
CREATE INDEX idx_produit_statut ON produit(statut);
```

> **Point de modélisation :** `statut` décrit le **cycle de vie** du produit. L'exposition en salle est une notion **distincte** (§3.2).

### 3.2 `exposition_showroom`

| Champ | Type | Note |
|-------|------|------|
| `produit_id` | FK (UNIQUE) | → `produit` (CASCADE) |
| `emplacement` | VARCHAR(100) | Zone du showroom |
| `disponible_essai` | BOOLEAN | Le client peut tester sur place |
| `vendable_showroom` | BOOLEAN | Vendable immédiatement ou démo uniquement |
| `date_installation_demo` | DATE | |

```sql
CREATE TABLE exposition_showroom (
    id SERIAL PRIMARY KEY,
    produit_id INTEGER UNIQUE NOT NULL,
    emplacement VARCHAR(100),
    disponible_essai BOOLEAN DEFAULT TRUE,
    vendable_showroom BOOLEAN DEFAULT TRUE,
    date_installation_demo DATE,

    CONSTRAINT fk_expo_produit FOREIGN KEY (produit_id)
        REFERENCES produit(id) ON DELETE CASCADE
);
```

> **Point de modélisation :** `disponible_essai` (essai physique) ≠ `vendable_showroom` (peut être vendu). Un modèle de démonstration peut être essayable mais **pas** vendable.

---

## 4. Module financier *(phase 2)*

### 4.1 `devis` et `ligne_devis`

```sql
CREATE TABLE devis (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES client(id) ON DELETE CASCADE,
    numero VARCHAR(20) UNIQUE NOT NULL,        -- DEV-AAAA-NNNNN
    date_emission DATE NOT NULL DEFAULT CURRENT_DATE,
    date_validite DATE,
    statut VARCHAR(20) DEFAULT 'brouillon',    -- brouillon, envoyé, accepté, refusé, expiré
    montant_ht DECIMAL(10,2) DEFAULT 0,
    tva_taux DECIMAL(5,2) DEFAULT 20.0,
    montant_ttc DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    pdf_path VARCHAR(500),
    created_by INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ligne_devis (
    id SERIAL PRIMARY KEY,
    devis_id INTEGER NOT NULL REFERENCES devis(id) ON DELETE CASCADE,
    description VARCHAR(500) NOT NULL,
    quantite DECIMAL(10,2) DEFAULT 1,
    unite VARCHAR(20) DEFAULT 'unité',
    prix_unitaire_ht DECIMAL(10,2) NOT NULL,
    montant_ht DECIMAL(10,2) GENERATED ALWAYS AS (quantite * prix_unitaire_ht) STORED,
    position INTEGER DEFAULT 0
);
```

### 4.2 `facture` et `ligne_facture`

```sql
CREATE TABLE facture (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES client(id) ON DELETE CASCADE,
    devis_id INTEGER REFERENCES devis(id) ON DELETE SET NULL,
    numero VARCHAR(20) UNIQUE NOT NULL,        -- FAC-AAAA-NNNNN
    date_emission DATE NOT NULL DEFAULT CURRENT_DATE,
    date_echeance DATE NOT NULL,
    statut VARCHAR(20) DEFAULT 'en_attente',   -- en_attente, payée, retard, annulée
    montant_ht DECIMAL(10,2) DEFAULT 0,
    tva_taux DECIMAL(5,2) DEFAULT 20.0,
    montant_ttc DECIMAL(10,2) DEFAULT 0,
    date_paiement DATE,
    mode_paiement VARCHAR(50),
    pdf_path VARCHAR(500),
    created_by INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
```

> **Positionnement :** gestion commerciale **simplifiée**. Ce n'est **pas** un logiciel comptable — l'intégration EBP/Sage est hors périmètre.

### 4.3 Bilans

> **Décision :** les bilans sont **calculés à la demande** à partir des données financières (`SELECT … WHERE date_emission >= …`).
>
> Une table de snapshot mensuel pourra être introduite **plus tard** si le volume ou l'historisation le justifient. Un cron mensuel serait prématuré à cette échelle.

---

## 5. Import Excel

### 5.1 `import_batch`

```sql
CREATE TABLE import_batch (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,        -- SHA-256 du fichier
    type_import VARCHAR(50) NOT NULL,      -- clients, jobs, complet
    status VARCHAR(20) DEFAULT 'running',  -- running, success, partial, failed, skipped
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    lignes_traitees INTEGER DEFAULT 0,
    lignes_creees INTEGER DEFAULT 0,
    lignes_ignorees INTEGER DEFAULT 0,
    lignes_erreurs INTEGER DEFAULT 0,
    rapport TEXT,
    imported_by INTEGER REFERENCES "user"(id)
);

CREATE INDEX idx_import_batch_hash ON import_batch(file_hash);
```

**Rôle :** porte l'**idempotence**. Si `file_hash` existe avec `status = success`, l'import est ignoré.

### 5.2 `import_record` (traçabilité ligne à ligne)

```sql
CREATE TABLE import_record (
    id SERIAL PRIMARY KEY,
    import_batch_id INTEGER NOT NULL REFERENCES import_batch(id) ON DELETE CASCADE,
    source_file VARCHAR(500) NOT NULL,
    source_row INTEGER NOT NULL,
    source_hash VARCHAR(64),
    entity_type VARCHAR(50) NOT NULL,      -- client, job
    entity_id INTEGER
);

CREATE INDEX idx_import_record_batch ON import_record(import_batch_id);
```

### 5.3 `import_error`

```sql
CREATE TABLE import_error (
    id SERIAL PRIMARY KEY,
    import_batch_id INTEGER NOT NULL REFERENCES import_batch(id) ON DELETE CASCADE,
    ligne INTEGER NOT NULL,
    colonne VARCHAR(255),
    valeur TEXT,
    erreur VARCHAR(500) NOT NULL,
    status VARCHAR(30) NOT NULL,           -- VALIDATION_ERROR, ORPHAN, DUPLICATE_AMBIGUOUS
    original_value TEXT,                   -- ex. nom du client introuvable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_error_batch ON import_error(import_batch_id);
```

> **Règle :** un job dont le client n'est pas identifiable va dans `import_errors` avec `status = ORPHAN` — **il n'est jamais ignoré silencieusement**, et n'est pas inséré tant qu'il n'est pas résolu.

---

## 6. Schéma des relations

```
client (1) ──→ (N) job
user   (1) ──→ (N) job
job    (1) ──→ (N) checklist_item
job    (1) ──→ (N) job_photo
job    (1) ──→ (N) material
job    (1) ──→ (1) review

produit (1) ──→ (1) exposition_showroom

client (1) ──→ (N) devis  ──→ (N) ligne_devis        (phase 2)
client (1) ──→ (N) facture ──→ (N) ligne_facture     (phase 2)
devis  (1) ──→ (N) facture                            (phase 2)

import_batch (1) ──→ (N) import_record
import_batch (1) ──→ (N) import_error
```

### Foreign keys

```
job.client_id            → client.id           (CASCADE)
job.technician_id        → user.id             (SET NULL)
checklist_item.job_id    → job.id              (CASCADE)
job_photo.job_id         → job.id              (CASCADE)
material.job_id          → job.id              (CASCADE)
review.job_id            → job.id              (CASCADE)

exposition_showroom.produit_id → produit.id    (CASCADE)

devis.client_id          → client.id           (CASCADE)
ligne_devis.devis_id     → devis.id            (CASCADE)
facture.client_id        → client.id           (CASCADE)
facture.devis_id         → devis.id            (SET NULL)
ligne_facture.facture_id → facture.id          (CASCADE)

import_record.import_batch_id → import_batch.id (CASCADE)
import_error.import_batch_id  → import_batch.id (CASCADE)
```

---

## 7. Règles métier

| Table | Règle |
|-------|-------|
| `job` | `started_at` renseigné quand `status = en_cours` |
| `job` | `completed_at` renseigné quand `status = terminé` |
| `job` | `completed_at` ≥ `started_at` |
| `checklist_item` | Items pré créés par défaut à la création du job |
| `job_photo` | Min. 1 photo avant + 1 photo après pour terminer |
| `review` | Un seul avis par job (`UNIQUE job_id`) |
| `review` | `share_token_expires_at` = `completed_at` + 30 jours |
| `produit` | `reference` unique |
| `exposition_showroom` | Un produit → au plus une exposition (`UNIQUE produit_id`) |
| `devis` | `numero` auto-généré (DEV-AAAA-NNNNN) |
| `facture` | `numero` auto-généré (FAC-AAAA-NNNNN) |
| `facture` | `montant_ttc` = `montant_ht` × (1 + `tva_taux`/100) |
| `import_batch` | Idempotence via `file_hash` (SHA-256) |
| `import_error` | Job non rattachable → `status = ORPHAN`, jamais ignoré |

---

## 8. Pipeline d'import — rappel

```
Excel → ExcelReader → FormatDetector → Normalizer → Validators
      → Matcher (rapidfuzz, 3 zones)
      → ImportService
          ├── PASS 1 — CLIENTS → IDs canoniques
          └── PASS 2 — JOBS    → résolution client_id
      → Transaction par batch
      → PostgreSQL
      → Rapport
```

Détail complet : `04-architecture.md` §6 et `06-workflows.md`.

---

> **Sommaire :** `00-sommaire.md`
> **Architecture :** `04-architecture.md`
> **API :** `specs/03-api-spec.md`
