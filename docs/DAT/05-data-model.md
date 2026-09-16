# Tervo — Data Model

## 1. Vue d'ensemble

Le modèle de données couvre 5 entités principales pour la gestion d'interventions terrain :

```
Client
    │
    └───< Job (intervention)
                │
                ├───< ChecklistItem
                ├───< JobPhoto
                ├───< Material
                └───< Review
```

---

## 2. Tables & Schéma détaillé

### 2.1 Table `client`

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

**Colonnes :**

| Colonne       | Type         | Description                 |
| ------------- | ------------ | --------------------------- |
| `id`          | SERIAL       | PK                          |
| `full_name`   | VARCHAR(255) | Nom complet (ou entreprise) |
| `phone`       | VARCHAR(50)  | Téléphone                   |
| `email`       | VARCHAR(255) | Email                       |
| `address`     | VARCHAR(500) | Adresse                     |
| `postal_code` | VARCHAR(20)  | Code postal                 |
| `city`        | VARCHAR(255) | Ville                       |
| `notes`       | TEXT         | Notes (code porte, étage…)  |
| `created_at`  | TIMESTAMP    | Création                    |
| `updated_at`  | TIMESTAMP    | Modification                |

---

### 2.2 Table `user`

```sql
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'technician',
    -- 'technician', 'admin'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2.3 Table `job`

```sql
CREATE TABLE job (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL,
    technician_id INTEGER,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'planifié',
    -- 'planifié', 'en_cours', 'terminé', 'annulé'
    priority VARCHAR(20) DEFAULT 'normale',
    -- 'basse', 'normale', 'haute', 'urgente'
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

**Colonnes :**

| Colonne                | Type         | Description                         |
| ---------------------- | ------------ | ----------------------------------- |
| `id`                   | SERIAL       | PK                                  |
| `client_id`            | INTEGER      | FK → client                         |
| `technician_id`        | INTEGER      | FK → user (technicien assigné)      |
| `title`                | VARCHAR(255) | Titre du job                        |
| `description`          | TEXT         | Description détaillée               |
| `status`               | VARCHAR(20)  | planifié, en_cours, terminé, annulé |
| `priority`             | VARCHAR(20)  | basse, normale, haute, urgente      |
| `scheduled_date`       | DATE         | Date planifiée                      |
| `scheduled_start_time` | TIME         | Créneau début                       |
| `scheduled_end_time`   | TIME         | Créneau fin                         |
| `started_at`           | TIMESTAMP    | Heure de début réelle               |
| `completed_at`         | TIMESTAMP    | Heure de fin réelle                 |
| `observations`         | TEXT         | Observations générales              |
| `created_at`           | TIMESTAMP    | Création                            |
| `updated_at`           | TIMESTAMP    | Modification                        |

---

### 2.4 Table `checklist_item`

```sql
CREATE TABLE checklist_item (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    category VARCHAR(20) NOT NULL,
    -- 'pre_intervention', 'post_intervention'
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

**Colonnes :**

| Colonne    | Type         | Description              |
| ---------- | ------------ | ------------------------ |
| `id`       | SERIAL       | PK                       |
| `job_id`   | INTEGER      | FK → job                 |
| `category` | VARCHAR(20)  | pré ou post intervention |
| `label`    | VARCHAR(255) | Intitulé de l'item       |
| `checked`  | BOOLEAN      | ✅ ou ❌                 |
| `note`     | TEXT         | Note libre               |
| `position` | INTEGER      | Ordre d'affichage        |

---

### 2.5 Table `job_photo`

```sql
CREATE TABLE job_photo (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    category VARCHAR(20) NOT NULL,
    -- 'avant', 'après'
    file_path VARCHAR(500) NOT NULL,
    thumbnail_path VARCHAR(500),
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_job FOREIGN KEY (job_id)
        REFERENCES job(id) ON DELETE CASCADE,
    CONSTRAINT chk_photo_category CHECK (category IN ('avant', 'après'))
);

CREATE INDEX idx_photo_job ON job_photo(job_id);
```

**Colonnes :**

| Colonne          | Type         | Description    |
| ---------------- | ------------ | -------------- |
| `id`             | SERIAL       | PK             |
| `job_id`         | INTEGER      | FK → job       |
| `category`       | VARCHAR(20)  | avant ou après |
| `file_path`      | VARCHAR(500) | Chemin fichier |
| `thumbnail_path` | VARCHAR(500) | Miniature      |
| `taken_at`       | TIMESTAMP    | Horodatage     |

---

### 2.6 Table `material`

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

**Colonnes :**

| Colonne    | Type         | Description                            |
| ---------- | ------------ | -------------------------------------- |
| `id`       | SERIAL       | PK                                     |
| `job_id`   | INTEGER      | FK → job                               |
| `name`     | VARCHAR(255) | Nom du matériau                        |
| `quantity` | VARCHAR(50)  | Quantité (texte libre : "1", "0.5 kg") |
| `position` | INTEGER      | Ordre                                  |

---

### 2.7 Table `review`

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

**Colonnes :**

| Colonne                  | Type         | Description                        |
| ------------------------ | ------------ | ---------------------------------- |
| `id`                     | SERIAL       | PK                                 |
| `job_id`                 | INTEGER      | FK → job (UNIQUE, un avis par job) |
| `rating`                 | INTEGER      | 1 à 5                              |
| `comment`                | TEXT         | Commentaire client                 |
| `reviewer_name`          | VARCHAR(255) | Nom du client (optionnel)          |
| `share_token`            | VARCHAR(64)  | Token unique pour le lien public   |
| `share_token_expires_at` | TIMESTAMP    | Expiration du lien (30 jours)      |
| `submitted_at`           | TIMESTAMP    | Date de soumission de l'avis       |

---

## 3. Schéma des relations

```
client (1) ──────→ (N) job
user (1) ──────→ (N) job

job (1) ──────→ (N) checklist_item
job (1) ──────→ (N) job_photo
job (1) ──────→ (N) material
job (1) ──────→ (1) review
```

### Foreign Keys

```
job.client_id → client.id (CASCADE)
job.technician_id → user.id (SET NULL)
checklist_item.job_id → job.id (CASCADE)
job_photo.job_id → job.id (CASCADE)
material.job_id → job.id (CASCADE)
review.job_id → job.id (CASCADE)
```

---

## 4. Script SQL de création complet

```sql
-- ============================================
-- HVAC/CVC App - Database initialization
-- ============================================

-- TABLE: client
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

-- TABLE: user
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

-- TABLE: job
CREATE TABLE job (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES client(id) ON DELETE CASCADE,
    technician_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'planifié'
        CHECK (status IN ('planifié', 'en_cours', 'terminé', 'annulé')),
    priority VARCHAR(20) DEFAULT 'normale'
        CHECK (priority IN ('basse', 'normale', 'haute', 'urgente')),
    scheduled_date DATE NOT NULL,
    scheduled_start_time TIME,
    scheduled_end_time TIME,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    observations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_job_client ON job(client_id);
CREATE INDEX idx_job_technician ON job(technician_id);
CREATE INDEX idx_job_status ON job(status);
CREATE INDEX idx_job_scheduled_date ON job(scheduled_date);

-- TABLE: checklist_item
CREATE TABLE checklist_item (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES job(id) ON DELETE CASCADE,
    category VARCHAR(20) NOT NULL CHECK (category IN ('pre_intervention', 'post_intervention')),
    label VARCHAR(255) NOT NULL,
    checked BOOLEAN DEFAULT FALSE,
    note TEXT,
    position INTEGER DEFAULT 0
);
CREATE INDEX idx_checklist_job ON checklist_item(job_id);

-- TABLE: job_photo
CREATE TABLE job_photo (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES job(id) ON DELETE CASCADE,
    category VARCHAR(20) NOT NULL CHECK (category IN ('avant', 'après')),
    file_path VARCHAR(500) NOT NULL,
    thumbnail_path VARCHAR(500),
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_photo_job ON job_photo(job_id);

-- TABLE: material
CREATE TABLE material (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES job(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    quantity VARCHAR(50),
    position INTEGER DEFAULT 0
);
CREATE INDEX idx_material_job ON material(job_id);

-- TABLE: review
CREATE TABLE review (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL UNIQUE REFERENCES job(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    reviewer_name VARCHAR(255),
    share_token VARCHAR(64) UNIQUE NOT NULL,
    share_token_expires_at TIMESTAMP,
    submitted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_review_share_token ON review(share_token);
```

---

## 5. Règles métier

| Table          | Règle                                                         |
| -------------- | ------------------------------------------------------------- |
| client         | `phone` unique dans le scope technicien (P2)                  |
| job            | `started_at` renseigné quand `status= en_cours`               |
| job            | `completed_at` renseigné quand `status= terminé`              |
| job            | `completed_at` ≥ `started_at`                                 |
| checklist_item | Items pré par défaut à la création du job                     |
| job_photo      | Min. 1 photo avant + 1 photo après obligatoires pour terminer |
| review         | `share_token` généré à la fin du job                          |
| review         | `share_token_expires_at` = `completed_at` + 30 jours          |
| review         | Un seul avis par job (UNIQUE job_id)                          |

---

> **Document mis à jour le 03/06/2026**
> **Version :** 3.0 (Refonte MVP)
