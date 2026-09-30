# INT-94 — Renommer `job` → `intervention`

> Tervo v2 · Sprint 7.1 · Lot 1 (socle physique)

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

### 5. Reporté au moment d’INT-94 (réalisé depuis)

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

Point clé : `ALTER TYPE ... RENAME VALUE` **n'existe pas sur SQLite**. Les tests SQLite ne prouvent donc pas que la migration fonctionne. La CI a depuis été complétée par les migrations PostgreSQL dans INT-101.

## Vérification à la livraison d’INT-94

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
- une **migration versionnée** doit couvrir table, colonnes FK, enum et index ; Alembic évite de rejouer une révision déjà appliquée.


## Revue du socle après INT-97

`site_id` est requis depuis INT-95 et `equipment_id` est maintenant une FK nullable. Le service valide Equipment.site_id == Intervention.site_id en création et modification ; null permet de dissocier un appareil. `under_warranty` est accessible en création/modification. Le scénario PostgreSQL de montée/descente conserve une intervention historique et traduit correctement son statut.

## Lire le renommage dans le code

Le changement Python et le changement SQL sont deux opérations distinctes. Voici le passage de la migration qui transforme les données déjà stockées, puis ajoute le nouveau champ.

Extrait du fichier [9d34b52092ce_rename_job_to_intervention.py](../../../backend/alembic/versions/9d34b52092ce_rename_job_to_intervention.py), lignes 23 à 37 :

```python
# 1. Enum `jobstatus` → `interventionstatus` (valeurs français → anglais).
op.execute("ALTER TYPE jobstatus RENAME TO interventionstatus")
op.execute("ALTER TYPE interventionstatus RENAME VALUE 'planifié' TO 'PLANNED'")
op.execute("ALTER TYPE interventionstatus RENAME VALUE 'en_cours' TO 'IN_PROGRESS'")
op.execute("ALTER TYPE interventionstatus RENAME VALUE 'terminé' TO 'COMPLETED'")
op.execute("ALTER TYPE interventionstatus RENAME VALUE 'annulé' TO 'CANCELLED'")

# 2. Table principale.
op.rename_table("job", "intervention")
op.add_column(
    "intervention",
    sa.Column("under_warranty", sa.Boolean(), nullable=False, server_default=sa.text("false")),
)

# 3. Table photo + colonnes FK `job_id` → `intervention_id`.
```

`ALTER TYPE` renomme le type PostgreSQL puis ses valeurs. `rename_table` conserve les lignes et leurs identifiants. `server_default=false` donne une valeur aux interventions déjà présentes lors de l’ajout de la colonne non nullable ; un simple `default=False` dans le modèle Python ne suffirait pas à ce travail SQL.

Dans le modèle actuel, SQLAlchemy utilise les valeurs de l’enum :

Extrait du fichier [intervention.py](../../../backend/app/models/intervention.py), lignes 55 à 60 :

```python
status = Column(
    Enum(InterventionStatus, values_callable=lambda x: [e.value for e in x]),
    default=InterventionStatus.PLANNED,
    nullable=False,
    index=True,
)
```

`values_callable` extrait chaque `e.value`. `default` définit le statut des nouvelles instances insérées via SQLAlchemy ; `nullable=False` interdit une valeur SQL NULL. Cette colonne ne traduit pas les libellés affichés dans Vue.

Le second `alembic upgrade head` ne rejoue pas les `ALTER TYPE` : Alembic connaît les révisions déjà appliquées. Le corps de cette migration, exécuté deux fois manuellement, n’est pas idempotent. La vérification de la migration doit utiliser PostgreSQL ; `metadata.create_all()` sur SQLite valide seulement la création du modèle courant.
