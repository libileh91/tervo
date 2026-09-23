# INT-94 — Renommer `job` → `intervention`

> Tervo v2 · Sprint 6.2-v2 · Lot 1 (socle physique)

## Objectif

Aligner le vocabulaire du code sur le modèle métier v2 verrouillé dans le DAT :
l'entité terrain **`job`** devient **`intervention`**. C'est un renommage mécanique
fait **une fois, tôt** — plus il est tard, plus il coûte cher (chaque écran, test
et migration qui s'appuie dessus).

## Ce qui a changé

### 1. Modèle (ORM)

| Avant                  | Après                                     |
| ---------------------- | ----------------------------------------- |
| `Job`                  | `Intervention`                            |
| `JobStatus`            | `InterventionStatus`                      |
| `JobPhoto`             | `InterventionPhoto`                       |
| table `job`            | `intervention`                            |
| table `job_photo`      | `intervention_photo`                      |
| colonne `job_id`       | `intervention_id` (checklist, material, review, photo) |

Fichiers renommés : `models/job.py` → `models/intervention.py`,
`models/job_photo.py` → `models/intervention_photo.py`.

### 2. Enum : français → anglais

Le statut était stocké en base **en français** (`planifié`, `en_cours`, `terminé`,
`annulé`). Le DAT v2 impose des valeurs **anglaises**, stables, non ambiguës :

```python
class InterventionStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
```

- **Pourquoi ?** Le statut est une *donnée machine* (il circule dans l'API, les
  filtres, les tests). Le français avec accents (`terminé`) est une mauvaise clé.
- **Où vit le français désormais ?** Uniquement à l'affichage : le frontend mappe
  via `statusLabel()` (`COMPLETED` → « Terminée »).
- L'enum `Priority` **reste en français** (`basse/normale/haute/urgente`) : il
  n'était pas dans le périmètre de ce ticket et sera traité plus tard si besoin.

### 3. Nouveau champ

`Intervention.under_warranty: bool` (défaut `false`) — demandé par le DAT v2 pour
savoir si l'intervention est sous garantie.

### 4. Routes API

`/api/v1/jobs*` → `/api/v1/interventions*` (et `/clients/{id}/jobs` →
`/clients/{id}/interventions`). Le frontend (`api/client.ts`, router, pages) suit.

### 5. Reporté (hors périmètre de ce ticket)

`site_id` (requis) et `equipment_id` (nullable) sont **reportés** à INT-95
(`Site`) et INT-97 (`Equipment`) : les tables n'existent pas encore. Idem pour le
pipeline `importers/` + `import_service.py` qui parlent encore de `jobs` — ils
seront **retargetés** par INT-98.

## La migration Alembic

`alembic/versions/9d34b52092ce_rename_job_to_intervention.py` — **PostgreSQL
uniquement** (les tests créent le schéma via `metadata.create_all`, pas via
Alembic). Elle fait :

1. `ALTER TYPE jobstatus RENAME TO interventionstatus` + renommage des 4 valeurs
   (français → anglais).
2. `op.rename_table("job", "intervention")` + ajout `under_warranty`.
3. `op.rename_table("job_photo", "intervention_photo")` + `op.alter_column` des
   colonnes `job_id` → `intervention_id`.
4. Renommage des index (`ix_job_*` → `ix_intervention_*`, etc.).

Point clé : `ALTER TYPE ... RENAME VALUE` **n'existe pas sur SQLite**. Comme les
tests ne déroulent pas la migration, on peut s'appuyer dessus sans casser la CI.

## Vérification

- `uv run pytest tests/ -q` → **114 passed**.
- `npm run build` (frontend) → **✓ built** (les pages renommées `InterventionsPage`
  et `InterventionDetailPage` sont bien bundlées).

## Le pattern à retenir

Renommer une entité « partout » ne se résume pas à `sed 's/job/intervention/'` :

- il y a le **capital** (`Job` → `Intervention`) et le **minuscule** (`job` →
  `intervention`), chacun avec ses pièges (`JobStatus`, `jobs_total`, `/jobs`) ;
- les **valeurs en base** (enum) et les **libellés d'affichage** sont deux choses
  différentes : on traduit les clés, on garde le français à l'écran ;
- les **fichiers** se renomment (modèles, schémas, services, repositories, router,
  pages Vue) en même temps que leurs **imports** ;
- une **migration idempotente** doit couvrir table, colonnes FK, enum et index.
