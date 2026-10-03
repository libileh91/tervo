# INT-104 — Modèles de checklist et snapshots historiques

> Cette note décrit la livraison INT-104 et ses preuves à ce stade. Les contrats
> photos/matériel ont ensuite évolué dans [INT-105](INT-105-photos-materiel-v2.md) :
> `usage`, `designation`, quantité numérique et unité. Le contrat du snapshot
> checklist présenté ici reste inchangé ; les anciennes fixtures demeurent
> des références historiques, pas le contrat média courant.

## 1. Ce qui change, et pourquoi

INT-104 distingue une **définition réutilisable** des contrôles et la **checklist
réellement appliquée à une intervention**.

Avant cette tâche, cinq contrôles étaient ajoutés directement dans `checklist_item`.
L'item portait `intervention_id`, `checked` et `note`. Il n'y avait ni modèle
administrable, ni version de définition, ni instance permettant de conserver
l'origine de la checklist.

Le nouveau parcours est :

```text
ChecklistTemplate v1
        |
        | copie à la création de l'intervention
        v
InterventionChecklist — nom/version figés
        |
        v
ChecklistItem — structure copiée, result/comment modifiables
```

Si le modèle passe en v2, la checklist créée avec v1 garde ses libellés, son
ordre, son nom et sa version. « Snapshot immuable » signifie ici que **la
structure n'est pas modifiable par l'API d'exécution** : le technicien peut
bien entendu renseigner les résultats et commentaires de ses contrôles.

Deux décisions ont été validées explicitement :

1. Sélection du modèle par `checklist_template_id` à la création, sans introduire
   un nouveau type métier sur `Intervention`. `intervention_type` décrit le modèle ;
   il ne déclenche pas une sélection automatique.
2. Pas de compatibilité checklist legacy : les champs `checked`/`note`, les
   routes PUT item/batch et le POST d'item personnalisé sont retirés. Les
   consommateurs frontend, rapport, seed et tests suivent le contrat V2.

Les autres fonctionnalités de 7.4 ne sont pas livrées par cette tâche : résultat
global de l'intervention, photos/matériel, rapport versionné et avis client
conservent leur périmètre propre.

## 2. Où se trouve le code

Les chemins horizontaux `app/models/`, `app/services/` et `app/api/v1/` ne sont
plus les sources actuelles. Le préalable TD-B018 a été traité dans le planning,
sans modifier le DAT ni cocher INT-105 à INT-108.

| Couche | Source actuelle | Responsabilité |
|---|---|---|
| ORM définition/snapshot | `backend/app/modules/interventions/models/checklist.py` | Tables, FK, unicité et versions |
| ORM item | `models/checklist_item.py` dans le même module | Résultat, commentaire, réalisation |
| ORM intervention | `models/intervention.py` | Possession du snapshot et projection des items |
| Schémas modèles | `schemas/checklist.py` | Validation des définitions, réponses snapshot |
| Schémas intervention/item | `schemas/intervention.py` | Sélection à la création et PATCH de réalisation |
| Routes | `api/checklist.py` | Authentification et autorisation |
| Service checklist | `services/checklist.py` | Copie des définitions et versionnement |
| Repository checklist | `repositories/checklist.py` | Lecture/persistance des résultats |
| Service/repository intervention | `services/intervention.py`, `repositories/intervention.py` | Transaction de création et verrou partagé |
| Import | `backend/app/modules/imports/{planner,service}.py` | Historique sans contrôles inventés |
| Rapport | `backend/app/modules/reports/{renderer.py,templates/report_template.html}` | Affichage V2 et échappement HTML |
| Frontend | `frontend/src/pages/{InspectionPage,InterventionsPage,InterventionDetailPage}.vue` | Sélection, saisie, sauvegarde et clôture |

Le registre `backend/app/model_registry.py` charge les deux nouvelles classes.
Le runtime compte désormais **19 tables/mappers**, sur une seule `Base`.

## 3. Modèle relationnel et invariants

### 3.1 La définition réutilisable

`ChecklistTemplate` contient :

| Champ | Règle |
|---|---|
| `id` | Entier, clé primaire |
| `name` | Non vide, 255 caractères au maximum |
| `intervention_type` | Texte descriptif non vide, 100 caractères au maximum |
| `version` | Entier positif, initialisé à 1 par le serveur |
| `active` | Booléen ; un modèle inactif n'est plus sélectionnable |
| `items` | Liste JSON non vide de définitions validées |

Chaque définition comporte `label`, `category` et `position`. Les catégories
acceptées sont `pre_intervention` et `post_intervention`, la position est un
entier strict non négatif, et un libellé constitué seulement d'espaces est
refusé. Les booléens ne sont pas acceptés comme positions entières.

Les définitions restent en JSON dans le modèle : elles sont toujours remplacées
comme un ensemble validé, puis copiées en lignes lors de l'instanciation.
Les items exécutés ne référencent donc pas des objets JSON mutables du modèle.

Le [modèle SQLAlchemy](../../../backend/app/modules/interventions/models/checklist.py#L9)
montre la distinction entre **contrainte SQL** et **valeur par défaut ORM** :

```python
class ChecklistTemplate(Base):
    __tablename__ = "checklist_template"
    __table_args__ = (CheckConstraint("version >= 1", name="ck_checklist_template_version"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    intervention_type = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    items = Column(JSON, nullable=False)
```

- `__tablename__` nomme la table ; la classe n'est pas une nouvelle connexion DB.
- `default=1` fournit la version quand SQLAlchemy insère un objet sans version.
  Ce n'est pas un `server_default` SQL : une insertion SQL directe doit fournir
  les valeurs obligatoires.
- `CheckConstraint` interdit une version non positive même si l'écriture ne
  passe pas par FastAPI.
- `JSON` stocke les définitions ; `nullable=False` ne valide pas leur forme.
  La liste non vide, les catégories et les limites de texte relèvent des schémas
  Pydantic présentés plus loin.

### 3.2 Le snapshot historique

Extrait réel de l'ORM :

```python
intervention_id = Column(Integer, ForeignKey("intervention.id", ondelete="CASCADE"), nullable=False, unique=True)
template_id = Column(Integer, ForeignKey("checklist_template.id", ondelete="RESTRICT"), nullable=True)
template_name = Column(String(255), nullable=False)
template_version = Column(Integer, nullable=False)
```

L'unicité de `intervention_id` impose au plus une checklist par intervention.
La FK nullable `template_id` permet les checklists par défaut et l'historique
importé sans inventer un modèle réutilisable.

`template_name` et `template_version` sont des **copies**, pas des lectures
dynamiques du modèle. Les labels, catégories et positions sont également copiés.
La référence au modèle sert à la provenance ; elle ne reconstruit pas l'historique.

Deux contraintes SQL vérifient les versions positives :

```text
ck_checklist_template_version                : version >= 1
ck_intervention_checklist_template_version   : template_version >= 1
```

Supprimer une intervention supprime son snapshot et ses items. La FK d'un
snapshot vers son modèle est `RESTRICT` : une définition référencée ne peut pas
être effacée silencieusement. L'API fournit la désactivation plutôt qu'un DELETE.

### 3.3 Les items exécutés

`ChecklistItem` porte désormais `intervention_checklist_id`, et non
`intervention_id`. Ses champs sont :

```text
id / intervention_checklist_id / category / label / position
result / comment / completed_at
```

`result` est un texte non blanc de 100 caractères au maximum, ou `null`.
Le DAT ne fixe pas d'enum pour ce résultat ; la tâche n'en invente pas.

| Valeur | Interprétation |
|---|---|
| `null` | Contrôle non réalisé |
| `"OK"` | Contrôle réalisé avec ce résultat |
| `"Non conforme — action requise"` | Contrôle réalisé avec une anomalie documentée |

Un contrôle **réalisé n'est pas forcément conforme**. La clôture vérifie que
chaque item a un résultat, pas que chaque résultat vaut `"OK"`. Ce n'est pas
non plus le résultat global de l'intervention, qui relève d'INT-106.

Le serveur gère `completed_at`. Un changement réel de résultat met à jour la
date ; remettre le résultat à `null` l'efface. Un commentaire seul, ou un PATCH
répétant le même résultat, ne réécrit pas la date.

`Intervention.checklist_items` reste une projection ORM `viewonly` pour le
détail et le rapport. Ce n'est plus une collection dans laquelle ajouter des
items pour persister des contrôles : la collection propriétaire est
`InterventionChecklist.items`.

Voici les [deux relations de l'intervention](../../../backend/app/modules/interventions/models/intervention.py#L82)
dans le code livré :

```python
checklist = relationship(
    "InterventionChecklist", back_populates="intervention", uselist=False,
    cascade="all, delete-orphan",
)
checklist_items = relationship(
    "ChecklistItem", secondary="intervention_checklist",
    primaryjoin="Intervention.id == InterventionChecklist.intervention_id",
    secondaryjoin="InterventionChecklist.id == ChecklistItem.intervention_checklist_id",
    viewonly=True, order_by="ChecklistItem.position",
)
```

`uselist=False` donne un objet snapshot, pas une liste. C'est la contrainte
`UNIQUE` en base, et non ce seul paramètre Python, qui impose l'unicité.
`back_populates` relie les deux côtés de la relation ORM.

La deuxième relation traverse `intervention_checklist` avec deux jointures :
intervention → snapshot, puis snapshot → items. Ici, `secondary` ne signifie
pas que le domaine est many-to-many ; il sert à exposer une projection de lecture.
`viewonly=True` interdit de considérer cette projection comme le chemin de
persistance. Les cascades ORM passent par `checklist`, puis par ses `items`.
Les FK `ON DELETE CASCADE` fournissent, séparément, la cascade côté base.

## 4. Contrats API

Préfixe commun : `/api/v1`.

| Méthode et route | Autorisation | Réponse |
|---|---|---|
| `GET /checklist-templates` | Utilisateur authentifié | Liste des modèles, actifs ou non |
| `POST /checklist-templates` | ADMIN | 201, modèle version 1 |
| `PATCH /checklist-templates/{template_id}` | ADMIN | Modèle à la version suivante |
| `GET /interventions/{intervention_id}/checklist` | Utilisateur authentifié | Objet snapshot contenant les items |
| `PATCH /checklist-items/{item_id}` | Technicien assigné, intervention PLANNED ou IN_PROGRESS | Item V2 complet |
| `POST /interventions` | Contrat d'authentification existant | Intervention avec snapshot créé atomiquement |

MANAGER et COMMERCIAL ne sont pas introduits ici. TD-B013 reste ouvert.
Le frontend ne dispose pas encore d'un écran d'administration des modèles ;
les écritures sont disponibles par l'API.

### 4.1 Créer une définition

```json
{
  "name": "Contrôle chaudière",
  "intervention_type": "Entretien chaudière",
  "active": true,
  "items": [
    {"label": "Contrôler pression", "category": "pre_intervention", "position": 0},
    {"label": "Tester fonctionnement", "category": "post_intervention", "position": 1}
  ]
}
```

La version initiale est serveur-owned. Envoyer `version` dans la création est
refusé comme champ supplémentaire ; il n'est pas possible de commencer
artificiellement à la version 42.

Un PATCH vide, une valeur explicite `null` sur un champ de définition, une liste
vide ou un champ inconnu sont refusés en 422. Un modèle absent donne 404.

#### Lire les validations, pas seulement l'exemple JSON

Extrait des [définitions Pydantic](../../../backend/app/modules/interventions/schemas/checklist.py#L11) :

```python
class TemplateItem(BaseModel):
    model_config = {"extra": "forbid"}
    label: str = Field(min_length=1, max_length=255)
    category: Literal["pre_intervention", "post_intervention"]
    position: StrictInt = Field(ge=0)

    @field_validator("label")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("label must be nonblank")
        return value
```

`min_length=1` refuse `""`, mais ne refuse pas `"   "` : le validateur complète
donc la règle. Il utilise `strip()` pour **tester** le texte, sans normaliser
la valeur stockée, puisque le retour est `value`.
`Literal` ferme l'ensemble des catégories. `StrictInt` refuse notamment `True`,
que Python traite pourtant comme un entier dans certains contextes.
`extra="forbid"` évite d'accepter silencieusement un champ que le backend ignore.

Pour [le PATCH du modèle](../../../backend/app/modules/interventions/schemas/checklist.py#L40),
deux validations supplémentaires distinguent un champ omis d'un champ fourni :

```python
@field_validator("name", "intervention_type", "active", "items")
@classmethod
def not_null_or_blank(cls, value):
    if value is None or isinstance(value, str) and not value.strip():
        raise ValueError("value must not be null or blank")
    return value

@model_validator(mode="after")
def require_change(self):
    if not self.model_fields_set:
        raise ValueError("at least one template field is required")
    return self
```

Un champ omis garde son défaut et n'est pas inclus dans
`model_dump(exclude_unset=True)`. Un champ explicitement envoyé à `null` est
validé et refusé. `active: false` reste valide : la condition teste `is None`,
pas la vérité de la valeur. Enfin, `model_fields_set` vide identifie `{}`.

### 4.2 Créer l'intervention

```json
{
  "site_id": 1,
  "title": "Entretien chaudière",
  "scheduled_date": "2026-10-02",
  "checklist_template_id": 1
}
```

La sélection doit être positive. Le modèle absent donne 404 ; un modèle inactif
donne 422. Aucune intervention partiellement créée ne reste en base.

Si la sélection est absente ou `null`, les cinq contrôles existants sont copiés
dans un snapshot nommé `Checklist par défaut`, version 1 : trois contrôles
pré-intervention et deux post-intervention. Ils sont tous non réalisés.

### 4.3 Lire et réaliser les contrôles

Le GET retourne un objet, **et non plus une liste plate** :

```json
{
  "id": 1,
  "intervention_id": 1,
  "template_id": 1,
  "template_name": "Contrôle chaudière",
  "template_version": 1,
  "created_at": "2026-10-02T12:00:00",
  "items": [
    {
      "id": 1,
      "intervention_checklist_id": 1,
      "category": "pre_intervention",
      "label": "Contrôler pression",
      "position": 0,
      "result": null,
      "comment": null,
      "completed_at": null
    }
  ]
}
```

Ce JSON illustre le contrat, pas une capture de production.
La lecture ne crée pas de contrôles : une intervention sans snapshot donne 404.

PATCH :

```json
{
  "result": "À remplacer",
  "comment": "Pression faible"
}
```

Les champs omis sont conservés ; `comment: null` efface le commentaire ;
`result: null` remet le contrôle en attente. `label`, `position`, `checked`,
`note` et `completed_at` sont interdits dans cette requête.

Le PATCH retourne l'item complet, afin que le frontend mette à jour son cache
avec la valeur réellement persistée et le timestamp serveur.

Le [schéma de réalisation](../../../backend/app/modules/interventions/schemas/intervention.py#L102)
ferme volontairement les champs modifiables :

```python
class ChecklistItemUpdate(BaseModel):
    """Only completion data is mutable; snapshot structure is immutable."""

    model_config = {"extra": "forbid"}
    result: str | None = Field(None, max_length=100)
    comment: str | None = None

    @field_validator("result")
    @classmethod
    def nonblank_result(cls, value):
        if value is not None and not value.strip():
            raise ValueError("result must be nonblank or null")
        return value
```

Contrairement à un champ de définition, `null` est ici un changement métier
autorisé. C'est pourquoi le handler transmet
`body.model_dump(exclude_unset=True)`, **pas** `exclude_none=True` : supprimer
les valeurs nulles empêcherait d'effacer un résultat ou un commentaire.

Le [repository](../../../backend/app/modules/interventions/repositories/checklist.py#L26)
applique cette distinction et la règle du timestamp :

```python
async def update_item(self, item, data):
    if "result" in data and data["result"] != item.result:
        item.result = data["result"]
        item.completed_at = datetime.now(timezone.utc).replace(tzinfo=None) if item.result is not None else None
    if "comment" in data:
        item.comment = data["comment"]
    await self.db.commit()
    await self.db.refresh(item)
    return item
```

La présence de la clé et sa valeur répondent à deux questions différentes :
« le client veut-il changer ce champ ? » et « quelle valeur veut-il écrire ? ».
La comparaison avec le résultat actuel empêche de dater à nouveau un contrôle
quand le frontend renvoie le même résultat avec un commentaire corrigé.
Le timestamp est calculé en UTC, puis stocké sans timezone conformément à la
colonne `DateTime` actuelle ; ce code ne fournit pas un timestamp timezone-aware.
`refresh` recharge l'objet après commit avant sa sérialisation.

### 4.4 Les contrats retirés

Ces routes n'existent plus :

```text
POST /interventions/{id}/checklist
PUT  /interventions/{id}/checklist/{item_id}
PUT  /interventions/{id}/checklist/batch
```

Les schémas batch hérités ont également été retirés. Il n'y a pas d'alias API
transformant `checked` en résultat ou `note` en commentaire.

## 5. Transactions et concurrence

### 5.1 Pourquoi `flush` n'est pas `commit`

Extrait réel du service de création :

```python
try:
    intervention = await self.repo.create(create_data)
    await ChecklistService(self.db).create_snapshot(intervention.id, template_id)
    await self.db.commit()
except Exception:
    await self.db.rollback()
    raise
```

Le repository crée l'intervention et effectue un `flush`. SQLAlchemy obtient
l'ID, mais la transaction n'est pas validée. Le service ajoute ensuite le snapshot
et les items, puis fait un seul `commit`.

La différence est visible dans
[le repository de création](../../../backend/app/modules/interventions/repositories/intervention.py#L87) :

```python
async def create(self, data: dict) -> Intervention:
    intervention = Intervention(**data)
    self.db.add(intervention)
    await self.db.flush()
    return intervention  # type: ignore[arg-type]
```

Le repository ne termine plus la transaction. Son appelant possède le périmètre
métier complet à committer. Appeler cette méthode seule sans commit ne livre
donc pas une intervention durable ; ce n'est pas un remplacement implicite du
service applicatif.

Un test injecte une erreur **après le flush du snapshot et de ses items** :
les trois tables restent sans création partielle. Tester une erreur avant
l'insertion ne suffirait pas à prouver cette atomicité.

### 5.2 Une version de modèle cohérente

La lecture du modèle sélectionné se fait sous `SELECT ... FOR UPDATE` sur
PostgreSQL. Le verrou est conservé jusqu'au commit du snapshot.

Extrait de [la branche avec modèle sélectionné et de la création du snapshot](../../../backend/app/modules/interventions/services/checklist.py#L34) :

```python
template = (await self.db.execute(select(ChecklistTemplate)
    .where(ChecklistTemplate.id == template_id).with_for_update()
    .execution_options(populate_existing=True))).scalar_one_or_none()
if template is None:
    raise HTTPException(404, "Modèle de checklist non trouvé")
if not template.active:
    raise HTTPException(422, "Modèle de checklist inactif")
name, version, definitions = template.name, template.version, template.items
```

Puis, après la branche qui prépare soit les définitions du modèle, soit les cinq
contrôles par défaut :

```python
snapshot = InterventionChecklist(
    intervention_id=intervention_id, template_id=template_id,
    template_name=name, template_version=version,
    items=[ChecklistItem(**definition) for definition in definitions],
)
self.db.add(snapshot)
await self.db.flush()
return snapshot
```

La compréhension crée **de nouveaux objets `ChecklistItem`**, pas une relation
vers les items JSON du modèle. Chaque objet reçoit ses propres colonnes scalaires.
SQLAlchemy persiste la collection `items` avec le snapshot grâce à la relation
propriétaire et à sa cascade. Aucun résultat n'est copié depuis le modèle :
les définitions ne contiennent que la structure des contrôles.

Le service ne fait pas de commit ici. La même méthode est appelée depuis la
transaction de création de l'intervention ; committer dans cette méthode
casserait l'atomicité expliquée en 5.1.

Un PATCH concurrent peut lire une ancienne version, mais son UPDATE attend
le verrou. La copie contient donc un ensemble cohérent : nom, version et
définitions de la même version, pas un mélange v1/v2.

La modification d'un modèle utilise également un compare-and-swap :

```text
UPDATE checklist_template
SET ..., version = version + 1
WHERE id = :id AND version = :version_lue
```

Si deux writers ont lu la même version, un seul modifie la ligne ; le second
reçoit 409. L'absence de conflit au dernier commit ne suffit pas : le nombre de
lignes affectées doit être contrôlé.

Le [compare-and-swap réellement exécuté](../../../backend/app/modules/interventions/services/checklist.py#L95)
est celui-ci :

```python
version = template.version
result = await self.db.execute(update(ChecklistTemplate)
    .where(ChecklistTemplate.id == template_id, ChecklistTemplate.version == version)
    .values(**body.model_dump(exclude_unset=True), version=version + 1)
    .execution_options(synchronize_session=False))
if result.rowcount != 1:
    await self.db.rollback()
    raise HTTPException(409, "Le modèle de checklist a été modifié")
await self.db.commit()
await self.db.refresh(template)
return template
```

Le prédicat sur la version transforme la lecture suivie d'un UPDATE en contrôle
optimiste explicite. `synchronize_session=False` évite de synchroniser
automatiquement l'ancien objet ORM avec cet UPDATE direct ; le `refresh` final
recharge la version et les valeurs effectives. Un PATCH non vide peut incrémenter
la version même s'il répète une valeur existante : le code rejette `{}`, mais
ne compare pas tout le contenu pour détecter une mutation sémantiquement vide.

### 5.3 Même verrou pour résultats et transitions terminales

La revue a révélé un vrai interleaving dangereux :

```text
PATCH lit IN_PROGRESS
complete valide les résultats puis commit COMPLETED
PATCH efface ensuite un résultat
```

Le simple test de statut avant le PATCH n'empêche pas cette course.
Le PATCH et les transitions start/cancel/complete prennent désormais le même
verrou d'intervention avant leurs contrôles.

Dans [le handler PATCH](../../../backend/app/modules/interventions/api/checklist.py#L54),
après avoir retrouvé l'item et son snapshot :

```python
snapshot = await db.get(InterventionChecklist, item.intervention_checklist_id)
intervention = await InterventionRepository(db).get_by_id(snapshot.intervention_id, for_update=True)
# The item may have been read before waiting for the intervention lock.
await db.refresh(item)
if intervention.technician_id != user.id:
    raise HTTPException(403, "Vous n'êtes pas assigné à cette intervention")
if intervention.status not in (InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS):
    raise HTTPException(422, "La checklist est verrouillée pour ce statut")
return await service.update_item(item_id, body.model_dump(exclude_unset=True))
```

L'ordre important est : **acquérir le verrou → recharger → autoriser → écrire**.
Vérifier l'assignation et le statut avant l'attente laisserait le PATCH agir
sur un état devenu périmé.

La [branche de verrouillage du repository](../../../backend/app/modules/interventions/repositories/intervention.py#L80)
utilise :

```python
query = query.with_for_update().execution_options(populate_existing=True)
```

`populate_existing` recharge le statut après une éventuelle attente : le cache
ORM ne doit pas conserver IN_PROGRESS alors que l'autre transaction a déjà
committé COMPLETED. L'item lu avant l'attente est également rafraîchi.

Quatre tests PostgreSQL imposent les deux ordres pour clôture et annulation :

| Premier writer | Second writer | Résultat attendu et observé |
|---|---|---|
| PATCH efface un résultat | complete | complete attend, puis refuse en 400 |
| complete | PATCH | PATCH attend, puis refuse en 422 ; résultat conservé |
| PATCH | cancel | cancel attend, puis annule |
| cancel | PATCH | PATCH attend, puis refuse en 422 |

Cette preuve est exécutée sur PostgreSQL 17.4. SQLite ne fournit pas le même
verrouillage `FOR UPDATE` ; la suite SQLite ne sert pas à revendiquer cette
garantie de concurrence PostgreSQL.

La relecture indépendante finale confirme l'ordre commun intervention → item,
le rafraîchissement après attente et la couverture des quatre interleavings ;
aucun nouveau bloqueur n'a été identifié sur cette correction. Le reviewer
n'a pas relancé les suites : les résultats ci-dessus sont ceux du run parent.

Le rejet du PATCH vide concerne le **modèle**. Le PATCH d'item `{}` reste un
no-op autorisé après contrôle d'assignation/statut ; ne pas confondre ces contrats.

## 6. Migration et conservation des données

Nouvelle révision : `g104e0010001`, après `f102e0010001`.
Les migrations précédentes ne sont pas réécrites.

L'upgrade :

1. Crée les tables définition et snapshot.
2. Crée un snapshot `Checklist historique`, version 1, pour chaque intervention
   existante, même si elle n'a aucun item.
3. Rattache les items existants au snapshot en conservant leurs IDs.
4. Convertit `checked=true` en `result="OK"`, sinon `null`.
5. Renomme `note` en `comment`, sans inventer de `completed_at`.
6. Remplace la FK vers l'intervention par une FK obligatoire vers le snapshot.

Cette conversion permet une montée de version sûre même si les données locales
actuelles sont des mocks. Elle n'autorise pas une suppression implicite d'une
base applicative.

Dans [l'upgrade Alembic](../../../backend/alembic/versions/g104e0010001_checklist_snapshots.py#L44),
le backfill est explicite :

```python
op.execute(sa.text(
    "INSERT INTO intervention_checklist (intervention_id, template_name, template_version) "
    "SELECT id, 'Checklist historique', 1 FROM intervention"
))
with op.batch_alter_table("checklist_item") as batch:
    batch.add_column(sa.Column("intervention_checklist_id", sa.Integer(), nullable=True))
    batch.add_column(sa.Column("result", sa.String(100), nullable=True))
    batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
op.execute(sa.text(
    "UPDATE checklist_item SET intervention_checklist_id = "
    "(SELECT id FROM intervention_checklist WHERE intervention_id = checklist_item.intervention_id), "
    "result = CASE WHEN checked THEN 'OK' ELSE NULL END"
))
```

On ajoute d'abord la FK comme colonne nullable, puis on renseigne chaque ligne,
puis seulement on applique `nullable=False` et la nouvelle contrainte.
Imposer immédiatement NOT NULL sur une table déjà peuplée aurait échoué.
`INSERT ... SELECT` couvre aussi les interventions sans contrôle ; l'UPDATE
ne recrée pas les items et conserve donc leurs clés primaires.

`batch_alter_table` fournit une opération Alembic portable pour cette évolution :
sur SQLite, Alembic peut reconstruire la table ; sur PostgreSQL, il utilise les
opérations ALTER appropriées. Cela ne rend pas toutes les anciennes migrations
du projet portables à SQLite : les tests distinguent bien schéma ciblé et chaîne
PostgreSQL réelle.

Le downgrade vérifie les données **avant toute DDL**. Il refuse notamment :
modèles présents, provenance de snapshot non représentable dans l'ancien schéma,
résultats autres que `"OK"`/`null`, ou timestamps de réalisation.

Le [garde du downgrade](../../../backend/alembic/versions/g104e0010001_checklist_snapshots.py#L81)
parcourt les requêtes de détection avant le premier changement de table :

```python
for query, reason in checks:
    if bind.execute(sa.text(query)).first():
        raise RuntimeError(f"INT-104 downgrade refused: would lose {reason}")
```

`LIMIT 1` dans les requêtes de `checks` suffit à prouver une incompatibilité ;
il n'est pas nécessaire de charger toutes les lignes en mémoire. Le refus
précise quelle information serait perdue. Les tests vérifient que ce refus
n'a ni modifié les items ni supprimé les tables V2.

Un snapshot interactif `Checklist par défaut` porte déjà une provenance que
l'ancien schéma ne représente pas : son downgrade peut donc être refusé même
si aucun résultat n'a été saisi. La procédure sûre est restauration d'une
sauvegarde/arbitrage explicite, pas suppression automatique des données.

Les tests couvrent :
IDs/libellés/positions/commentaires conservés, snapshot historique vide,
unicité par intervention, FK obligatoire, cascade, référence modèle restreinte,
round trip compatible et refus de perte d'information.

La fixture historique d'installation a été corrigée : reconstruire un schéma
antérieur depuis toute la metadata **courante** introduisait les tables INT-104
avant leur migration. Elle exclut maintenant le nouveau modèle et reconstruit
explicitement l'ancienne table checklist avant de stamper la révision précédente.

## 7. Import Excel, rapport et seed

### Import historique

L'import ne dispose pas de contrôles historiques fiables. Il crée donc un snapshot
vide `Checklist historique` : pas de modèle choisi artificiellement, pas de
contrôle validé fictif. Snapshot et intervention restent dans la transaction
de batch de l'import.

La création interactive et la création importée utilisent une partie du même
schéma de validation, mais n'ont pas le même body ORM. L'intégration a détecté
que le nouveau champ de requête `checklist_template_id` fuyait dans le plan
d'import et dans le constructeur ORM.

La correction est à la frontière du planner :

```python
result.pop('checklist_template_id')
```

L'import n'expose pas cette sélection ; la retirer du body ORM conserve aussi
le plan et l'oracle historiques, au lieu de masquer une erreur au commit.

### Rapport

Le rapport affiche les vrais résultats et commentaires, avec `Non réalisé`
pour un résultat `null`. L'échappement HTML est activé : un commentaire ou un
résultat contenant une balise est imprimé comme du texte, pas exécuté/interprété.

Les fixtures HTML R7 sont conservées. Le test compare tout le HTML avec un
delta explicite en mémoire : titres de colonnes V2, résultats à la place de
O/X et échappement des valeurs de recette. Un autre test injecte des balises
dans résultat/commentaire et vérifie leur échappement.

Le vrai PDF et l'API de téléchargement restent testés. Cela ne livre pas le
versionnement/transmission du rapport prévu dans INT-107.

### Seed

Les mocks du seed suivent le modèle V2 : **7 snapshots × 5 contrôles = 35 items**,
tous sans résultat, commentaire ni date de réalisation inventés.

Le seed a été testé deux fois sur sa propre SQLite temporaire dédiée.
Il n'a pas été exécuté sur une base existante. TD-B019 reste ouvert : ces tests
ne rendent pas son usage destructif sûr sur une base peuplée.

## 8. Frontend : préserver les saisies, pas les anciens contrats

La création d'intervention propose les modèles actifs, ou la checklist par défaut.
L'inspection affiche le nom et la version du snapshot, des résultats libres et
des commentaires. Les états chargement, erreur avec réessai et vide sont traités.
L'ajout ad hoc d'un item a été supprimé : la structure appartient au snapshot.

La checkbox est un raccourci de saisie `"OK"`/`null`, pas une deuxième donnée
persistée. Elle préserve un résultat libre déjà présent quand elle reste cochée.

Le [raccourci de checkbox](../../../frontend/src/composables/checklistDrafts.ts#L4)
conserve donc une valeur métier arbitraire :

```typescript
export function checkboxResult(current: string | null, checked: boolean): string | null {
    return checked ? current ?? "OK" : null;
}
```

`??` ne remplace que `null`/`undefined`. Cocher un item dont le résultat vaut
`"À remplacer"` ne transforme pas ce résultat en `"OK"`. Décocher est, au
contraire, une action explicite de remise en attente.

Il n'y a plus de route batch. La sauvegarde fait un PATCH par item et traite
chaque réponse individuellement :

- succès : le cache reçoit l'item serveur ;
- échec : le message reste associé à l'item et le brouillon reste dirty ;
- saisie pendant la requête : le succès ne doit pas acquitter une valeur
  que cette requête n'a jamais envoyée ;
- refresh : seuls les items non dirty remplacent leurs brouillons.

La [préparation de la sauvegarde](../../../frontend/src/pages/InspectionPage.vue#L116)
copie les valeurs soumises, plutôt que de conserver une référence vers le
brouillon qui peut encore être édité :

```typescript
const pending = [...dirtyItems.value].map(id => ({ id, data: { ...drafts.value[id] } }));
```

Ce sont des champs scalaires : la copie superficielle suffit ici. Si l'utilisateur
saisit un autre commentaire pendant la requête, `data` garde celui effectivement
envoyé. Cette distinction permet de ne pas acquitter la nouvelle saisie par erreur.

Extrait du traitement individuel des PATCH dans le même handler :

```typescript
await Promise.all(pending.map(async ({ id, data }) => {
    try {
        const updated = await checklistApi.updateItem(auth.token!, id, data);
        queryClient.setQueryData<ChecklistSnapshot>(["checklist", interventionId], previous => previous
            ? { ...previous, items: previous.items.map(item => item.id === id ? updated : item) } : previous);
        delete saveErrors.value[id];
        acknowledgeSavedDraft(drafts.value, dirtyItems.value, id, data, updated);
    } catch (error) {
        saveErrors.value[id] = errorMessage(error);
    }
}));
```

Le `catch` est **dans** chaque opération : un échec n'efface pas les succès
des autres items et ne laisse pas croire que tout le groupe a été enregistré.
Il n'y a pas d'atomicité multi-items côté frontend ; chaque PATCH a sa transaction.
Le cache reçoit la réponse complète du serveur, pas un résultat reconstruit
localement, et le message d'erreur reste attaché au bon ID.

Extrait du [helper d'acquittement](../../../frontend/src/composables/checklistDrafts.ts#L20) :

```typescript
const current = drafts[id];
if (current.result === submitted.result && current.comment === submitted.comment) {
    dirty.delete(id);
    drafts[id] = { result: saved.result, comment: saved.comment };
}
```

Le [refresh des brouillons](../../../frontend/src/composables/checklistDrafts.ts#L8)
applique la même frontière entre valeur serveur et saisie non sauvegardée :

```typescript
for (const item of items) {
    if (!dirty.has(item.id)) drafts[item.id] = { result: item.result, comment: item.comment };
}
```

Un `invalidateQueries` déclenche une relecture, mais ne doit pas prendre le
contrôle de ce que l'utilisateur est encore en train d'écrire. Ici, l'ensemble
`dirty` définit explicitement quels champs restent propriétaires de la saisie locale.

La clôture est empêchée tant qu'une saisie reste dirty, qu'une sauvegarde ou
clôture est en cours, ou qu'un item n'a pas de résultat. Le handler revérifie
la garde et positionne `completing` avant son premier `await`, empêchant le
double clic. Le détail dirige vers l'inspection pour vérifier et terminer.

La [garde calculée](../../../frontend/src/pages/InspectionPage.vue#L86) lit les
résultats du snapshot serveur lorsque les brouillons sont tous propres :

```typescript
const canComplete = computed(() => canEdit.value && intervention.value?.status === "IN_PROGRESS"
    && !!snapshot.value && !isError.value && !dirtyItems.value.size && !saving.value && !completing.value
    && items.value.every(item => item.result !== null));
```

Le blocage ne repose donc pas seulement sur l'apparence des checkboxes.
`every` sur une liste vide vaut `true` : une checklist historique vide ne bloque
pas la clôture, conformément au contrat documenté. L'autorisation, le statut et
les états de requête restent requis même dans ce cas.

Ces gardes améliorent l'expérience utilisateur ; elles ne remplacent pas
l'autorisation et le verrou côté serveur.

## 9. Tests et preuves réellement exécutés

| Vérification | Résultat local observé |
|---|---|
| Suite backend complète, SQLite et schémas temporaires | **450 passed, 6 skipped, 7 warnings**, 103,95 s |
| PostgreSQL canoniques ventes/installations/imports + INT-104/migration | **132 passed, 2 warnings**, 55,98 s |
| INT-104/migration PostgreSQL incluant les quatre courses terminales | **37 passed, 2 warnings**, 12,16 s |
| Helpers de projection de contrat | **27 passed**, 0,28 s |
| Helpers frontend de brouillons | **4 pass, 0 fail**, 11 assertions |
| Frontend typecheck et build | Réussis ; Vite 6.4.3, 451 modules lors du run parent |
| Chaîne Alembic réelle PostgreSQL | upgrade head → downgrade -1 → upgrade head réussis |
| Comparaison structurée metadata PostgreSQL | Aucun nouvel écart INT-104 |
| Smoke navigateur réel | Login, snapshot v1, résultats/commentaires, échec partiel/réessai, clôture et PDF réussis |

Les six skips de la suite sans URL PostgreSQL correspondent au test de chaîne
migration PostgreSQL et aux cinq tests de verrouillage PostgreSQL. Les cas
PostgreSQL sont exécutés dans les runs dédiés ; ils ne sont pas présentés
comme ayant tourné dans le run SQLite.

`alembic check` retourne toujours **255** : seul l'écart historique de FK
`intervention.technician_id → user.id` est détecté, sans `ON DELETE` côté
migration historique et avec `SET NULL` côté ORM. La comparaison structurée
vérifie précisément remove/add de cette FK et aucune autre opération.
Ce n'est pas un `alembic check` vert.

Les warnings concernent `crypt`/passlib et `datetime.utcnow()` des transitions
existantes. Ils ne sont pas cachés ni corrigés transversalement dans INT-104.

### Lire deux tests représentatifs

Le [test de rollback](../../../backend/tests/test_int104_checklists.py#L195)
ne se contente pas de fournir un ID de modèle invalide : il provoque une erreur
après que SQLAlchemy a effectivement écrit les objets dans la transaction :

```python
original = ChecklistService.create_snapshot
async def fail_after_flush(self, *args):
    await original(self, *args)
    raise RuntimeError("snapshot failure after items flushed")
monkeypatch.setattr(ChecklistService, "create_snapshot", fail_after_flush)
async with sessions() as db:
    user = await db.get(User, tech_id)
    with pytest.raises(RuntimeError, match="snapshot failure"):
        await InterventionService(db).create_intervention(InterventionCreate(**body), user)
async with sessions() as db:
    for model in (Intervention, InterventionChecklist, ChecklistItem):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
```

`monkeypatch` remplace la méthode uniquement pour ce test. L'implémentation réelle
est d'abord appelée : le test exerce donc le vrai flush, les vraies relations et
le vrai rollback. La seconde session relit la base, au lieu de vérifier seulement
le contenu de l'identity map de la session qui a échoué.

Le [test de concurrence](../../../backend/tests/test_int104_checklists.py#L411)
fait attendre le premier writer après acquisition du verrou, puis lance l'autre :

```python
await asyncio.wait_for(locked.wait(), 10)
second_task = asyncio.create_task(actions[second](), name="second-writer")
await asyncio.wait_for(second_started.wait(), 10)
await asyncio.sleep(0.05)
assert not second_task.done(), "The second writer must wait for the intervention lock"
release_first.set()
first_response, second_response = await asyncio.wait_for(asyncio.gather(first_task, second_task), 10)
```

Les événements `locked` et `second_started` rendent l'ordre explicite ; le test
ne dépend pas seulement de deux requêtes lancées « à peu près en même temps ».
Les timeouts bornent un deadlock éventuel. Après ces lignes, le test contrôle
les codes HTTP et relit l'item et le statut persistés. Le court `sleep` sert à
observer l'attente du second writer, pas à définir à lui seul l'ordre de la course.

### Commandes exécutées

Interpréteur parent : le venv préexistant du checkout principal, sans installation
`pip --user` ni modification du Python utilisateur.

```sh
ROOT=/home/lob/workspace/python/fastapi/Tervo
# Depuis un cwd scratch, DATABASE_URL SQLite et UPLOAD_DIR temporaires :
"$ROOT/backend/.venv/bin/python" -m pytest "$ROOT/backend/tests" \
  -q --tb=short -p no:cacheprovider

# Même isolation, URLs TERVO_* pointant sur le PostgreSQL Docker jetable :
"$ROOT/backend/.venv/bin/python" -m pytest \
  "$ROOT/backend/tests/test_installations.py" \
  "$ROOT/backend/tests/test_sales.py" \
  "$ROOT/backend/tests/test_installation_migration.py" \
  "$ROOT/backend/tests/test_import_service_v2.py" \
  "$ROOT/backend/tests/test_import_api_v2.py" \
  "$ROOT/backend/tests/test_int104_checklists.py" \
  "$ROOT/backend/tests/test_checklist_migration.py" \
  -q --tb=short -p no:cacheprovider

cd "$ROOT/backend"
# DATABASE_URL PostgreSQL jetable, pas la base applicative :
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic downgrade -1
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic check

cd "$ROOT/frontend"
bun test tests
bun run typecheck
bun run build
```

Les conteneurs PostgreSQL utilisent l'image locale `postgres:17.4`, `--pull never`,
un port hôte éphémère lié à `127.0.0.1`, aucun volume existant et un arrêt/nettoyage
en fin de run. Les tests PostgreSQL INT-104 créent leurs propres schémas aléatoires.

Le workflow CI a été adapté : tests backend actuels, étapes PostgreSQL existantes,
nouvelle étape checklist avec les deux URLs `TERVO_CHECKLIST_*`, et tests Bun
de brouillons. **Cette configuration n'est pas la preuve d'un run distant INT-104
réussi.** La CI verte du commit refactor `adc5954` concerne l'état précédent.

### Smoke navigateur réellement exécuté

Le scout a exécuté Playwright sur des données fictives propres à
`/tmp/tervo-smoke-int104` : SQLite et uploads isolés, utilisateurs technicien/ADMIN,
un site et une intervention IN_PROGRESS avec un snapshot v1 de deux contrôles.
Ce montage ORM est un setup de recette, pas l'exécution d'`app.seed`.

Le backend utilise le venv préexistant et le `PYTHONPATH` du backend testé.
Playwright et le navigateur sont installés dans ce répertoire temporaire, pas
dans le Python utilisateur. Un premier téléchargement a expiré ; le téléchargement
de repli a permis de lancer le navigateur. Les appels `/api/v1/**` du navigateur
sont redirigés vers le backend de recette, sans modification du proxy Vite.
Versions exécutées : Playwright npm **1.49.1**, Chromium **131.0.6778.33**,
build navigateur Playwright **v1148** (fallback Ubuntu 20.04 x64).

Résultats observés :

| Étape | Observation |
|---|---|
| Login UI | HTTP 200, `/auth/me` 200 |
| Inspection | Snapshot `Template Inspection Smoke — version 1`, deux résultats initialement null |
| Saisie | Résultats et commentaires libres ; sauvegarde disponible, clôture empêchée avant sauvegarde |
| Échec partiel injecté | Premier PATCH 500 volontaire, second PATCH 200 |
| Conservation | Résultat/commentaire de l'item échoué toujours présents ; réessai disponible |
| Réessai | PATCH 200, relecture snapshot 200 |
| Clôture | PUT complete 200, navigation détail et statut COMPLETED |
| API ADMIN | GET modèles 200, POST modèle 201 |
| PDF | 200, `application/pdf`, fichier `rapport-intervention-1.pdf`, **13 032 octets** |

Aucun `pageerror` n'a été observé. La console contient les messages Vite,
l'information autofocus, l'erreur HTTP 500 **injectée volontairement** et une
dépréciation PrimeVue Tabs. On ne prétend donc pas « zéro erreur HTTP » sans
distinguer l'injection de test.

Cette recette prouve le parcours d'inspection. La sélection du modèle dans le
formulaire de création est couverte par le code typé/build et la sélection API
par les tests backend ; elle n'est pas revendiquée comme sélection UI exécutée
dans ce smoke. L'écran d'administration des modèles reste hors périmètre.
Les processus backend/frontend/navigateur de recette sont arrêtés, et les ports
8765/4173 sont libres. Le répertoire temporaire de preuves est conservé.

## 10. Preuves historiques et contrat courant

R0–R11 documentent une refactorisation sans changement métier ; INT-104 est
une évolution fonctionnelle après cette refactorisation. Exiger que la metadata
et l'OpenAPI actuelles soient encore identiques à R0 serait maintenant faux.

Les fichiers R0 metadata/OpenAPI, le pack d'import, `before.json`, les fixtures
de rapports et leurs SHA restent immuables.

Les gardes courantes :

- exigent 19 tables/mappers et la même identité de `Base` ;
- comparent les tables R0 hors checklist exactement ;
- contrôlent les colonnes, FK, unicité et versions des nouvelles tables ;
- comparent les routes/schémas non concernés par INT-104 à R0 ;
- contrôlent les routes supprimées et nouvelles, le snapshot et le PATCH V2.

L'oracle d'import retire les nouvelles tables de sa projection historique
**après contrôle** : aucun modèle ni item fictif, exactement un snapshot vide
par intervention, provenance historique/version 1. Ignorer aveuglément les
nouvelles lignes aurait pu masquer une régression.

## 11. Limites et suite

- Le smoke navigateur est distinct des tests de helpers/build ; sa portée
  exacte et l'échec partiel injecté sont documentés ci-dessus.
- Pas d'écran d'administration des modèles ; l'API existe.
- Pas de résultat global d'intervention ni de versionnement de rapport.
- TD-B013 (rôles), TD-B016 (volume réel d'import), TD-B019 (seed sûr),
  TD-F005 et TD-F007 restent ouverts.
- Aucun déploiement et aucun accès à une base applicative existante.
- Aucun benchmark d'import réel déduit des tests fictifs.
- Le DAT n'a pas été réécrit dans le cadre de la reprise de chemins TD-B018.

La prochaine tâche nécessite son propre feu vert ; INT-105 ne démarre pas
automatiquement après INT-104.
