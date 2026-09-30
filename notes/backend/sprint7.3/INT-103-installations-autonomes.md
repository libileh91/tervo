# INT-103 — Installation autonome, clôture atomique et lien Equipment

**28 septembre 2026 — INT-103 partiellement terminée.** L'utilisateur a explicitement validé l'ordre INT-103 avant INT-102. Le backend autonome est livré et testé ; aucun frontend, commit ni déploiement n'a été effectué.

Références : [tâches](../../../docs/stages/stage7/sprint7.3/tasks.md), [cas de test](../../../docs/stages/stage7/sprint7.3/test-cases.json), [DAT](../../../docs/DAT/new/00-revue/03-lot-commercial.md), [todos](../../../docs/todos/backend.md).

## 1. Installation n'est ni une vente ni un équipement planifié

L'installation représente la pose d'une unité physique sur un **site existant obligatoire**. Le matériel peut être fourni par le client, acheté ailleurs. Aucun stock, vente fictive ou catalogue obligatoire n'est nécessaire.

```python
class Installation(Base):
    __tablename__ = "installation"

    site_id = Column(
        Integer,
        ForeignKey("site.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(
            InstallationStatus,
            native_enum=False,
            create_constraint=True,
            name="installation_status",
        ),
        nullable=False,
        default=InstallationStatus.SCHEDULED,
        server_default="SCHEDULED",
        index=True,
    )
```

- Une installation SCHEDULED ou IN_PROGRESS ne crée aucun équipement.
- La clôture crée un Equipment ACTIVE ou rattache un Equipment ACTIVE existant.
- `Equipment.installation_id` reste nullable pour les équipements historiques ; lorsqu'il est renseigné, c'est désormais une **FK réelle et unique**. Une installation ne produit donc jamais deux équipements.
- Aucun statut Equipment.PLANNED n'est ajouté.

### Écart temporaire explicite avec le modèle cible

Sale et SaleLine n'existent pas encore. Il n'y a **ni colonne entière libre sale_line_id, ni champ commercial dans les réponses ou contrats de création/clôture**. Avec `extra="forbid"`, sa présence, même `null`, est rejetée en 422. Accepter une valeur puis l'ignorer serait trompeur.

```python
class InstallationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: int = Field(gt=0)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    technician_notes: str | None = None
```

Le contrat ne déclare volontairement pas `sale_line_id`. Pydantic refuse donc une requête ambiguë au lieu de l'accepter silencieusement :

```json
{
  "site_id": 1,
  "sale_line_id": null
}
```

```text
HTTP 422 Unprocessable Entity
Extra inputs are not permitted
```

INT-102 / **TD-B017** ajoutera la vraie FK nullable, l'acceptation de null et la vérification des références, du site, du produit et des règles commerciales. Les installations autonomes existantes resteront sans vente, sans backfill artificiel. Les tests de provenance commerciale et de ligne inconnue en 404 sont **différés**, pas déclarés réussis. TD-B014 physique est résolu, mais cela ne termine pas INT-103 entière.

## 2. API disponible

Préfixe : `/api/v1`. Toutes les routes exigent le JWT d'un utilisateur actif.

| Méthode | Route                          | Résultat                                                                 |
| ------- | ------------------------------ | ------------------------------------------------------------------------ |
| POST    | `/installations`               | 201, installation SCHEDULED                                              |
| GET     | `/installations`               | Liste paginée ; filtres `site_id`, `status`, `page`, `page_size` (1–100) |
| GET     | `/installations/{id}`          | Installation et équipement associé, sinon 404                            |
| POST    | `/installations/{id}/start`    | SCHEDULED → IN_PROGRESS, started_at serveur                              |
| POST    | `/installations/{id}/complete` | IN_PROGRESS → COMPLETED et équipement, atomiquement                      |
| POST    | `/installations/{id}/cancel`   | SCHEDULED ou IN_PROGRESS → CANCELLED                                     |

COMPLETED et CANCELLED sont terminaux. Toute répétition de start/complete/cancel ou transition interdite retourne **409** sans changement ; la clôture n'est pas un rejeu HTTP 200 idempotent, mais ne peut pas dupliquer l'équipement.

```python
@router.post("/{installation_id}/start", response_model=InstallationResponse)
async def start_installation(
    installation_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await InstallationService(db).transition(installation_id, "start")


@router.post("/{installation_id}/complete", response_model=InstallationResponse)
async def complete_installation(
    installation_id: int,
    body: InstallationComplete,
    db: AsyncSession = Depends(get_db),
):
    return await InstallationService(db).complete(installation_id, body)
```

### Création autonome

```json
{
  "site_id": 1,
  "scheduled_start": "2026-09-28T08:00:00Z",
  "scheduled_end": "2026-09-28T10:00:00Z",
  "technician_notes": "PAC fournie par le client"
}
```

Le planning est optionnel ; une fin exige un début antérieur ou égal. Les offsets reçus sont convertis en UTC puis stockés sans fuseau, conformément aux DateTime existants du projet. Les dates sans offset sont interprétées comme UTC ; les réponses ont donc des timestamps sans suffixe de fuseau. `started_at` et `completed_at` sont générés par le serveur, jamais imposés par le client.

```python
@field_validator("scheduled_start", "scheduled_end")
@classmethod
def utc_naive(cls, value):
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


@model_validator(mode="after")
def planning_order(self):
    if self.scheduled_end and (
        not self.scheduled_start
        or self.scheduled_end < self.scheduled_start
    ):
        raise ValueError("La fin planifiée nécessite un début antérieur ou égal")
    return self
```

### Clôture : choix obligatoire et explicite

**Créer une nouvelle instance** :

```json
{
  "installation_date": "2026-09-28",
  "commissioning_date": "2026-09-28",
  "equipment": {
    "mode": "create",
    "product_id": 1,
    "serial_number": "PAC-CLIENT-001",
    "notes": "Matériel fourni par le client"
  }
}
```

`product_id`, `serial_number` et `notes` sont facultatifs. Si le produit est fourni, son existence est vérifiée (404 sinon) ; un produit catalogue inactif reste une référence valable, comme dans EquipmentService. Le site et installation_id proviennent de l'installation, le statut est ACTIVE : le client ne peut pas les substituer.

**Rattacher une instance existante** :

```json
{
  "installation_date": "2026-09-28",
  "commissioning_date": "2026-09-28",
  "equipment": { "mode": "attach", "equipment_id": 42 }
}
```

Une union discriminée Pydantic sélectionne le contrat par `equipment.mode`. Un numéro de série ne déclenche jamais de rapprochement implicite.

```python
class CreateInstalledEquipment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["create"]
    product_id: int | None = Field(None, gt=0)
    serial_number: str | None = Field(None, max_length=255)
    notes: str | None = None


class AttachInstalledEquipment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["attach"]
    equipment_id: int = Field(gt=0)


class InstallationComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    installation_date: date
    commissioning_date: date | None = None
    equipment: Annotated[
        CreateInstalledEquipment | AttachInstalledEquipment,
        Field(discriminator="mode"),
    ]
```

Conditions de rattachement :

1. L'équipement existe (sinon 404), appartient au même site (sinon 422).
2. Il est ACTIVE, non remplacé, et n'a pas déjà d'installation (sinon 409). Cette action n'est pas une remise en service d'un équipement OUT_OF_SERVICE.
3. Produit, série, garanties et notes sont conservés ; le contrat attach n'autorise pas leur écrasement.
4. Les dates déjà connues ne sont jamais effacées ou remplacées : la requête doit les reprendre à l'identique, sinon 409. Les dates absentes sont complétées.

`installation_date` est obligatoire lors de complete. `commissioning_date` est optionnelle mais ne peut précéder la pose. La garantie n'est pas déduite automatiquement de ces dates.

## 3. Pourquoi le service possède la transaction

Fichiers :

- `backend/app/models/installation.py` : état persistant et relations.
- `backend/app/schemas/installation.py` : contrats d'entrée stricts et réponses.
- `backend/app/repositories/installation.py` : requêtes et écritures **sans commit**.
- `backend/app/services/installation.py` : règles métier, commit unique, rollback.
- `backend/app/api/v1/installations.py` : HTTP et dépendances partagées.

Les anciens `EquipmentRepository.create()` et `replace()` possèdent leur propre commit. Les appeler au milieu de complete casserait l'atomicité : le nouveau repository fait seulement un flush pour vérifier les contraintes, puis le service valide l'ensemble.

Une session SQLAlchemy a souvent déjà une transaction ouverte par les lectures d'authentification (`autobegin`). Le service réutilise cette transaction plutôt que d'appeler aveuglément `db.begin()` et provoquer « transaction already begun ».

```python
async def create_equipment(self, values):
    self.db.add(Equipment(**values))
    await self.db.flush()  # pas de commit dans le repository
```

Le service reste ainsi le seul propriétaire du `commit` et du `rollback` :

```python
try:
    # transition Installation + écriture Equipment
    await self.db.commit()
except IntegrityError as exc:
    await self.db.rollback()
    raise HTTPException(
        409,
        "Conflit de référence ou équipement déjà lié à cette installation",
    ) from exc
except Exception:
    await self.db.rollback()
    raise
```

Déroulé de complete :

1. Lire l'installation (404 si absente).
2. Effectuer un `UPDATE ... WHERE status = 'IN_PROGRESS'` vers COMPLETED ; exiger `rowcount == 1`.
3. Créer l'équipement ou vérifier/verrouiller puis rattacher l'existant avec un second UPDATE conditionnel.
4. Commit unique. Si une référence, un statut, une contrainte ou une écriture échoue : **rollback de toute la transaction**.
5. Relire avec chargement explicite de l'équipement (`selectinload`), sans lazy loading async pendant la sérialisation.

Le passage temporaire à COMPLETED n'est pas validé en base avant l'écriture Equipment. Il sert aussi de verrou contre les autres actions. Sous PostgreSQL, une action concurrente attend puis réévalue le WHERE ; sous SQLite, les écritures sont sérialisées. L'unicité SQL reste le dernier garde-fou, y compris contre des écritures hors API. Une IntegrityError est transformée en 409 après rollback ; une erreur inattendue est rollbackée puis propagée, jamais transformée en faux succès.

```python
async def transition(self, installation_id, allowed, values):
    result = await self.db.execute(
        update(Installation)
        .where(
            Installation.id == installation_id,
            Installation.status.in_(allowed),
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1
```

Pour un rattachement, l'`UPDATE` conditionnel répète les invariants importants au niveau de l'écriture :

```python
result = await self.db.execute(
    update(Equipment)
    .where(
        Equipment.id == equipment_id,
        Equipment.site_id == site_id,
        Equipment.installation_id.is_(None),
        Equipment.replaced_by_id.is_(None),
        Equipment.lifecycle_status == EquipmentStatus.ACTIVE,
    )
    .values(**values)
)
```

Les tests lancent réellement deux requêtes concurrentes : complete/complete, deux installations pour le même équipement, cancel/complete. Ils injectent aussi une exception **après** l'écriture Equipment et relisent depuis une nouvelle session : ni date de clôture ni équipement partiel ne subsiste.

## 4. Auth et conservation de l'historique

Le code actuel ne définit que ADMIN et TECHNICIAN. Les nouvelles routes suivent Equipment/Site avec `get_current_user` : JWT valide, utilisateur existant et actif. Les tests utilisent de vrais JWT, sans remplacement du garde d'authentification.

Cela n'implémente pas une affectation nominative des techniciens, un contrôle par propriétaire/site ou les futurs rôles MANAGER/COMMERCIAL. TD-B013 reste ouvert. Le modèle cible de sécurité ne doit pas être annoncé comme entièrement livré.

La suppression d'un site ou client avec installation retourne 409, même avant la création d'un équipement. Les FK RESTRICT protègent aussi les références en base. Aucune route DELETE Installation n'est exposée.

## 5. Migration non destructive

Révision `e103e0010001`, après `d100e0010001` :

- création de la table installation, FK site, enum CHECK et index ;
- ajout de la FK Equipment.installation_id et contrainte UNIQUE, sans remplir les historiques ;
- relations ORM Equipment ↔ Installation et Site ↔ Installation.

**Préflight :** avant toute DDL, si un Equipment a déjà un installation_id non null, la migration échoue avec une demande d'arbitrage. Aucune table Installation n'existait auparavant : l'identifiant ne peut donc pas être vérifié. Il n'est ni supprimé, ni associé à une installation inventée.

```python
connection = op.get_bind()
if connection.execute(
    sa.text(
        "SELECT id FROM equipment "
        "WHERE installation_id IS NOT NULL LIMIT 1"
    )
).first():
    raise RuntimeError(
        "Equipment.installation_id non vérifiable : "
        "arbitrage manuel requis avant migration"
    )
```

La cardinalité `Installation 1 → 0..1 Equipment` est garantie en base par la FK et l'unicité :

```python
with op.batch_alter_table("equipment") as batch:
    batch.create_foreign_key(
        "equipment_installation_id_fkey",
        "installation",
        ["installation_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    batch.create_unique_constraint(
        "uq_equipment_installation_id",
        ["installation_id"],
    )
```

**Downgrade :** refus si des installations existent, même sans équipement, pour ne pas perdre de planning/historique. Sur une table vide, le retour arrière enlève uniquement les nouvelles contraintes et la table Installation ; les équipements historiques sont conservés.

Les anciennes migrations comportent `ALTER TYPE`, spécifique à PostgreSQL. Le test SQLite reconstitue le schéma précédent dans un fichier jetable et valide **uniquement la nouvelle révision**. Le test PostgreSQL crée un schéma aléatoire isolé et exécute **toute la chaîne Alembic depuis zéro**, puis aller/retour avec données historiques. Les tests contrôlent FK, unicité, statuts, nullabilité, conservation des liens de remplacement et refus des données non vérifiables. Aucune ancienne migration n'a été modifiée pour masquer cette différence.

## 6. Validation exécutée

Résultats locaux, Python 3.12 et PostgreSQL 17.4 :

| Validation                                                                    | Résultat                                                   |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Suite backend complète, répertoire de travail et uploads temporaires          | **267 passed**, 5 avertissements de dépréciation existants |
| Installation API/transactions + migration, PostgreSQL                         | **53 cas**, inclus dans le groupe ci-dessous               |
| Installation + migrations + régression import service/API, PostgreSQL jetable | **92 passed**, 1 avertissement passlib/crypt               |

Un premier lancement global avait échoué sur un test JWT ancien qui décode avec la clé de développement en dur, car le runner fournissait une autre clé fictive. Le lancement final utilise explicitement la clé de développement attendue ; aucun changement de ce test ni secret réel n'a été nécessaire.

Commandes ciblées (depuis backend, environnement de test seulement) :

```sh
DATABASE_URL=sqlite:///:memory: .venv/bin/python -m pytest tests/test_installations.py tests/test_installation_migration.py -q
```

Pour PostgreSQL, les tests prennent explicitement `TERVO_INSTALLATION_TEST_DATABASE_URL` (asyncpg), `TERVO_INSTALLATION_MIGRATION_TEST_URL` (psycopg2), et le groupe import existant prend `TERVO_IMPORT_TEST_DATABASE_URL`. Les nouvelles fixtures créent/suppriment uniquement leur schéma aléatoire de test ; ne pas utiliser d'identifiants de production.

La validation locale a utilisé un conteneur `postgres:17.4` dédié, `--rm`, stockage tmpfs, port loopback 55439, identifiants fictifs. Le conteneur a été arrêté après validation. Les bases locales existantes et les données réelles n'ont pas été migrées.

Pour la suite générale, les anciens tests écrivent/suppriment `./test_tervo.db`. Le runner a donc exécuté pytest avec `cwd` dans un `TemporaryDirectory`, `PYTHONPATH` pointant vers backend, `DATABASE_URL=sqlite:///:memory:`, `UPLOAD_DIR` temporaire et `SECRET_KEY=dev-secret-key-change-in-production`. Cela conserve le fichier test_tervo.db préexistant du projet. Ne pas lancer naïvement cette suite depuis un répertoire contenant une base à conserver.

`.github/workflows/ci.yml` exécute désormais les 53 tests Installation/migration contre le PostgreSQL CI déjà provisionné, en plus de la suite générale et du groupe import. La configuration CI est mise à jour ; aucun run GitHub distant ni déploiement n'est revendiqué.

## 7. Reprise

- **INT-103 reste partielle** jusqu'à TD-B017 / INT-102 ; ne pas cocher le lien commercial sur la seule base de ce travail.
- Aucun écran Installation n'a été implémenté.
- Les notes et modifications DAT préexistantes ont été conservées ; le DAT reste le modèle cible, le présent document décrit l'état effectivement livré.
- TD-B010 (données de déploiement), TD-B013 (rôles) et TD-B016 (volume réel d'import) restent ouverts, sans rapport avec la réussite de ces tests.
