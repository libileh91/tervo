# INT-105 — Photos et matériel utilisés : contrat V2, migration et limites

> Le smoke PDF de cette note a été exécuté avant
> [INT-107](INT-107-rapports-versionnes.md). Le parcours actuel exige une
> génération explicite, puis lit le PDF de la version archivée ; le smoke
> INT-105 ne constitue pas une validation navigateur d'INT-107.

## 1. Statut de cette note

Cette note décrit les sources INT-105 présentes dans le checkout pendant la
validation finale du parent. Elle ne constitue pas une annonce de livraison.
Le point de départ est INT-104, commit `74f05a6`.
INT-105 poursuit le cycle terrain sans réimplémenter les snapshots de checklist.

**Validation locale finale : 539 tests backend réussis (7 skips PostgreSQL), 200 tests
PostgreSQL réussis, 10 tests Bun, typecheck et build réussis.**
Les résultats intermédiaires transmis sont distingués des preuves finales.
Aucun succès de CI distante, déploiement ou smoke navigateur n'est présumé.
Cette rédaction ne modifie ni runtime, ni planning, ni todo, ni CI.
Elle n'exécute pas un seed sur une base existante et ne publie aucun commit.

Les extraits Python/TypeScript ci-dessous sont des fragments des sources lues.
Les explications sont placées autour des extraits pour ne pas confondre
commentaire pédagogique et code réellement exécuté.
Les exemples JSON sont des exemples de contrat, pas des traces de production.

## 2. Le problème métier et la transformation

Une photo n'est plus seulement « avant » ou « après ».
Elle peut documenter l'équipement, une anomalie, une pièce ou un autre sujet.
Le matériel consommé ne doit plus être une désignation accompagnée d'un texte
opaque : quantité et unité deviennent des données distinctes.

```text
Historique                         INT-105
intervention_photo.category   ->    photo.usage
material.name                 ->    material_usage.designation
material.quantity : texte     ->    quantity : Numeric(12, 3)
unité absente                 ->    unit : texte nullable pour l'historique
```

Le nom `MaterialUsage` signifie une utilisation de matériel dans l'intervention.
Il ne représente pas un article de stock, un fournisseur ou un inventaire.
La quantité n'entraîne aucune déduction de stock.
L'unité n'est pas un catalogue normalisé d'unités physiques.

La séparation importante est :

- les **nouvelles saisies** doivent être complètes et valides ;
- les **anciennes données** peuvent conserver une quantité ou unité inconnue ;
- une migration ne doit pas inventer une connaissance métier manquante.

La V2 remplace les anciens noms, elle ne maintient pas des alias concurrents.
Envoyer `name` dans un JSON matériel n'est donc pas une compatibilité legacy.
Envoyer uniquement `category` au formulaire photo ne satisfait plus `usage`.

## 3. Carte de lecture des sources

Tous les liens partent de ce dossier de note.
Les sources modulaires sont les sources actuelles, pas les anciens chemins
horizontaux `app/models` ou `app/api/v1`.

| Sujet | Source |
|---|---|
| Enum et ORM photo | [models/photo.py](../../../backend/app/modules/interventions/models/photo.py) |
| ORM matériel | [models/material_usage.py](../../../backend/app/modules/interventions/models/material_usage.py) |
| Relations du parent | [models/intervention.py](../../../backend/app/modules/interventions/models/intervention.py) |
| Contrats Pydantic | [schemas/intervention.py](../../../backend/app/modules/interventions/schemas/intervention.py) |
| Routes photo | [api/photos.py](../../../backend/app/modules/interventions/api/photos.py) |
| Routes matériel | [api/materials.py](../../../backend/app/modules/interventions/api/materials.py) |
| Validation et fichiers | [services/photo.py](../../../backend/app/modules/interventions/services/photo.py) |
| Persistance photo | [repositories/photo.py](../../../backend/app/modules/interventions/repositories/photo.py) |
| Service matériel | [services/material.py](../../../backend/app/modules/interventions/services/material.py) |
| Persistance matériel | [repositories/material.py](../../../backend/app/modules/interventions/repositories/material.py) |
| Migration Alembic | [h105e0010001_media_usage.py](../../../backend/alembic/versions/h105e0010001_media_usage.py) |
| Composition des guards | [contract_int105.py](../../../backend/tests/contract_int105.py) |
| Tests purs des guards | [test_contract_int105.py](../../../backend/tests/test_contract_int105.py) |
| Tests API et fichiers | [test_int105_media.py](../../../backend/tests/test_int105_media.py) |
| Tests migration | [test_media_migration.py](../../../backend/tests/test_media_migration.py) |
| Renderer rapport | [renderer.py](../../../backend/app/modules/reports/renderer.py) |
| Template rapport | [report_template.html](../../../backend/app/modules/reports/templates/report_template.html) |
| Client HTTP frontend | [client.ts](../../../frontend/src/api/client.ts) |
| Utilitaires frontend | [interventionMedia.ts](../../../frontend/src/utils/interventionMedia.ts) |
| Page terrain | [InterventionDetailPage.vue](../../../frontend/src/pages/InterventionDetailPage.vue) |
| Tests frontend | [interventionMedia.test.ts](../../../frontend/tests/interventionMedia.test.ts) |

## 4. Photo : six valeurs, une règle commune

### 4.1 L'enum métier

Extrait de `models/photo.py` :

```python
class PhotoUsage(str, Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    EQUIPMENT = "EQUIPMENT"
    ANOMALY = "ANOMALY"
    PART = "PART"
    OTHER = "OTHER"
```

`str, Enum` donne des valeurs utilisables dans un formulaire et un JSON.
Les valeurs transportées sont en anglais et en majuscules.
Les libellés visibles restent « Avant », « Après », « Équipement », etc.
Une traduction d'interface ne doit pas changer la valeur persistée.

La contrainte SQL reprend le domaine autorisé :

```python
    __table_args__ = (
        CheckConstraint(
            "usage IN ('BEFORE', 'AFTER', 'EQUIPMENT', 'ANOMALY', 'PART', 'OTHER')",
            name="ck_photo_usage",
        ),
    )
```

L'enum protège l'entrée API, le CHECK protège une écriture SQL hors API.
Ce sont deux frontières différentes, pas deux validations interchangeables.
La colonne reste `String(20)`, pas un enum natif PostgreSQL.
La migration et les guards vérifient également ces six valeurs.

### 4.2 Une photo reste un enfant de l'intervention

Le FK vers l'intervention évite une ligne photo orpheline en base.
`CASCADE` porte sur les lignes SQL, **pas sur les fichiers disque**.
`taken_at` est une date serveur par défaut, pas une extraction EXIF.
`file_url` projette le nom du fichier vers `/uploads/photos/`.
Cette projection n'est pas une validation du chemin disque :
celle-ci intervient séparément avant suppression.

## 5. Matériel : précision en base et contrat de saisie

### 5.1 Le modèle SQL

Extrait de `models/material_usage.py` :

```python
class MaterialUsage(Base):
    __tablename__ = "material_usage"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_material_usage_quantity_positive"),)
```

Les champs de consommation, dans la même classe :

```python
    designation = Column(String(255), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=True)
    unit = Column(String(50), nullable=True)
    position = Column(Integer, default=0, nullable=False)
```

`Numeric(12, 3)` réserve douze chiffres, dont trois après la virgule.
Le maximum positif du contrat est `999999999.999`.
`0.001` est admissible ; `0`, `-1` et `0.0001` ne le sont pas.
La base utilise un nombre décimal, pas une chaîne décrivant « deux pièces ».

Le CHECK `quantity > 0` n'interdit pas SQL NULL.
En SQL, une expression comparant NULL n'est pas un booléen faux ordinaire.
Cette nullabilité est volontaire pour l'historique.
Elle ne doit pas être copiée mécaniquement dans le contrat de création.

### 5.2 Création stricte

Extrait de `schemas/intervention.py` :

```python
class MaterialCreate(BaseModel):
    model_config = {"extra": "forbid"}
    designation: str = Field(..., min_length=1, max_length=255)
    quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3, json_schema_extra=_bounded_quantity_schema)
    unit: str = Field(..., min_length=1, max_length=50)

    @field_validator("designation", "unit")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("must be nonblank")
        return value
```

Les trois champs sont requis.
`extra: forbid` rejette notamment `name`, mais aussi un champ futur inconnu.
Le validateur distingue chaîne non vide et chaîne constituée d'espaces.
Il vérifie le contenu sans transformer systématiquement la valeur en `strip()`.
Le frontend, lui, prépare une désignation et une unité nettoyées.

Exemple JSON : `{"designation": "Fluide", "quantity": 0.125, "unit": "kg"}`.

Une chaîne décimale peut aussi être validée par Pydantic.
Ce fait ne rend pas admissibles des descriptions comme `"2 pièces"`.
La précision reste bornée quelle que soit la forme transportée.

### 5.3 La correction du schéma Decimal

Dernier helper lu dans la source :

```python
def _bounded_quantity_schema(schema: dict) -> None:
    """Anchor Pydantic's generated Decimal pattern over the entire string."""
    for variant in schema.get("anyOf", []):
        if variant.get("type") == "string" and "pattern" in variant:
            variant["pattern"] = "(?:" + variant["pattern"] + ")$"
```

Pydantic génère une alternative JSON `number` et une alternative `string`.
La précision décimale publiée par le schéma est portée par le pattern texte.
Un lecteur JSON Schema cherche une correspondance, pas forcément un match
complet à la manière de `fullmatch`.
Le pattern produit doit donc empêcher une correspondance sur un préfixe valide.

Le helper conserve le pattern généré et l'enveloppe avant d'ajouter `$`.
Il complète son ancrage au début par une borne finale.
Cela ne remplace ni la validation Pydantic runtime ni le type SQL.
Cela rend le contrat publié cohérent avec la borne attendue.

Le guard teste le **langage reconnu**, pas une chaîne regex figée :

```python
    pattern = decimal["pattern"]
    assert all(re.search(pattern, value) for value in ("1", "0.001", "999999999.999"))
    assert all(not re.search(pattern, value) for value in ("1000000000", "1.0001"))
```

Cette approche accepte une évolution équivalente du générateur Pydantic.
Elle refuse un schéma qui accepte seulement un morceau de `1.0001`.
La correction du helper est une correction de contrat, pas une permission
de tronquer silencieusement la quantité en base.

### 5.4 Lecture historique et JSON number

```python
class MaterialResponse(BaseModel):
    id: int
    intervention_id: int
    designation: str
    quantity: Decimal | None = None
    unit: str | None = None
    position: int

    model_config = {"from_attributes": True}

    @field_serializer("quantity", when_used="json")
    def quantity_number(self, value) -> float | None:
        return float(value) if value is not None else None
```

Le calcul et le stockage utilisent Decimal/Numeric.
La réponse JSON utilise explicitement un nombre, et non `"0.125"`.
Cette conversion ne transforme pas la base en stockage flottant.
Elle n'est pas non plus une garantie de calcul décimal exact côté JavaScript.

Exemple historique lisible : `{"id": 9, "intervention_id": 1,
"designation": "Pièce historique", "quantity": null, "unit": null, "position": 4}`.

NULL signifie « inconnu », pas zéro ni « pièce » par défaut.
La lecture fonctionne avant enrichissement ultérieur.

## 6. Routes, omission de champs et autorité du parent

### 6.1 Matrice du contrat

Préfixe applicatif : `/api/v1`.

| Méthode | Chemin sous ce préfixe | Contrat |
|---|---|---|
| GET | `/interventions/{id}/photos` | Liste de `PhotoRef` |
| POST | `/interventions/{id}/photos` | Multipart `file` et `usage`, 201 |
| DELETE | `/interventions/{id}/photos/{photo_id}` | Suppression, 204 |
| GET | `/interventions/{id}/materials` | Liste ordonnée par position |
| POST | `/interventions/{id}/materials` | `MaterialCreate`, 201 |
| PUT | `/interventions/{id}/materials/{material_id}` | `MaterialUpdate` |
| DELETE | `/interventions/{id}/materials/{material_id}` | Suppression, 204 |

Le détail intervention expose également `photos` et `materials`.
Il n'est pas nécessaire de fabriquer une autre forme frontend pour le détail.
Le GET photos dédié fournit le même contrat de référence photo.

### 6.2 PUT partiel : ne pas confondre omission et null

```python
class MaterialUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    designation: str = Field(default=None, min_length=1, max_length=255)
    quantity: Decimal = Field(default=None, gt=0, max_digits=12, decimal_places=3, json_schema_extra=_bounded_quantity_schema)
    unit: str = Field(default=None, min_length=1, max_length=50)
```

Les annotations ne sont pas `str | None` ou `Decimal | None`.
Le défaut permet l'omission, pas l'envoi explicite d'un null valide.
Le routeur utilise :

```python
    return await service.update_material(
        intervention_id, material_id, body.model_dump(exclude_unset=True)
    )
```

Une requête `{"designation": "Fluide neuf"}` conserve quantité et unité.
Une requête `{"quantity": null}` est rejetée par le contrat d'entrée.
Cette distinction évite de supprimer une information sous couvert d'édition.
Le routeur matériel utilise PUT, avec une sémantique partielle assumée ici.
Il n'ajoute pas une route PATCH matériel.
La route PATCH de réalisation de checklist appartient à INT-104.
Le principe commun est de ne modifier que les champs effectivement fournis.

### 6.3 L'identifiant enfant n'est pas une autorisation

Extrait du repository photo :

```python
    async def get_by_id(self, intervention_id: int, photo_id: int) -> Photo | None:
        result = await self.db.execute(
            select(Photo).where(Photo.id == photo_id, Photo.intervention_id == intervention_id)
        )
        return result.scalar_one_or_none()
```

Les deux predicates de `where` sont combinés par AND.
Connaître un `photo_id` ne permet pas de le supprimer depuis un autre parent.
Le repository matériel suit la même règle avec `MaterialUsage`.
Un enfant existant sous A demandé sous B donne 404, pas une mutation sous A.

Avant une mutation, le routeur charge le parent avec `with_for_update()`.
Puis il compare `intervention.technician_id` à `current_user.id`.
Le technicien non assigné reçoit 403.
Un parent inexistant reçoit 404.
L'authentification est fournie par `get_current_user`.

Le verrou du parent aide à sérialiser les écritures concurrentes qui suivent
ce protocole, notamment le calcul de la prochaine position matériel.
Il ne remplace ni l'authentification ni le scope de la requête enfant.

Les GET ne prennent pas ce verrou. Le helper de recherche sépare explicitement
lecture et mutation avec `for_update=False` par défaut :

```python
    query = select(Intervention).where(Intervention.id == intervention_id)
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    result = await db.execute(query)
```

POST/PUT/DELETE demandent `for_update=True`, tandis que GET utilise la lecture
simple. Quatre tests de requêtes compilées vérifient cette distinction pour
photos et matériels : un écran de lecture ne bloque pas inutilement un autre
reader sur la ligne parent.
Les garanties de verrouillage dépendent aussi du moteur SQL utilisé.

Les listes vérifient authentification et existence du parent.
Elles ne passent pas par `_check_assignation` dans les routes lues.
Ne pas écrire que tous les GET sont réservés au technicien assigné.
Les rôles élargis restent un sujet TD-B013, pas une livraison INT-105.

## 7. Upload : borner, décoder, puis persister

### 7.1 Taille et contenu réel

Extrait de `services/photo.py` :

```python
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024
```

Le seuil est dix **MiB**, soit `10 * 1024 * 1024` octets.
Le message utilisateur indique « 10 Mo », mais la constante est binaire.
Le code ne se fie pas à une taille annoncée par le client :

```python
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(400, "Format non accepté. Utilisez JPEG, PNG ou WebP.")
        content = await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, "Fichier trop volumineux (max 10 Mo)")
```

Lire un octet de plus permet de détecter le dépassement.
Le service ne lit pas un fichier entier sans borne avant de comparer sa taille.
Cela ne prouve pas une borne globale du buffering multipart dans l'infrastructure.
Un proxy et le serveur peuvent avoir leurs propres règles de corps HTTP.

### 7.2 Pillow et transparence

```python
            with Image.open(io.BytesIO(content)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Unsupported image")
                original.load()
                if original.mode in ("RGBA", "LA", "P", "PA"):
                    rgba = original.convert("RGBA")
                    image = Image.new("RGB", original.size, (255, 255, 255))
                    image.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    image = original.convert("RGB")
                image.thumbnail((300, 300))
                thumbnail = io.BytesIO()
                image.save(thumbnail, "JPEG", quality=85)
```

`Image.open` seul peut être paresseux ; `load()` force le décodage.
Un faux JPEG contenant du texte ne passe pas simplement grâce au MIME.
Le format décodé doit également appartenir à JPEG/PNG/WebP.
Les erreurs de décodage prévues donnent une réponse 400.

La miniature est RGB, JPEG, qualité 85.
Pour les modes avec transparence, le fond blanc reçoit l'image via son alpha.
`thumbnail((300, 300))` borne les dimensions en conservant les proportions.
Il ne s'agit pas d'un recadrage forcé en carré 300 × 300.
L'original est conservé comme bytes reçus, pas remplacé par la miniature.

L'extension originale est choisie par le MIME déclaré accepté :
`image/jpeg -> jpg`, `image/png -> png`, `image/webp -> webp`.
Le code valide aussi le format décodé, mais ne compare pas explicitement
format décodé et MIME pour exiger leur égalité.
Ne pas lui attribuer cette garantie supplémentaire.

## 8. Transaction upload : un commit SQL et une compensation disque

### 8.1 Pourquoi le repository ne commit plus

Extrait de `repositories/photo.py` :

```python
    async def create(self, data: dict) -> Photo:
        photo = Photo(**data)
        self.db.add(photo)
        await self.db.flush()
        await self.db.refresh(photo)
        return photo
```

`flush()` envoie la ligne dans la transaction courante et obtient son identité.
`refresh()` récupère les valeurs nécessaires, dont les valeurs serveur.
Aucune de ces opérations ne signifie que la transaction est validée.
Le service conserve la possibilité de rollback jusqu'à la réponse construite.

### 8.2 L'ordre des opérations

```python
        created: list[Path] = []
        try:
            for path, data in ((file_path, content), (thumb_path, thumbnail.getvalue())):
                # Exclusive creation makes cleanup ownership unambiguous.
                with path.open("xb") as target:
                    created.append(path)
                    target.write(data)
            photo = await self.repo.create({
                "intervention_id": intervention_id,
                "usage": usage,
                "file_path": str(file_path),
                "thumbnail_path": str(thumb_path),
            })
            # Validate the response while the row can still be rolled back.
            response = PhotoRef.model_validate(photo)
            await self.db.commit()
```

L'ouverture `xb` échoue plutôt que d'écraser un fichier existant.
Un UUID aléatoire réduit les collisions, l'ouverture exclusive les traite.
La liste `created` enregistre seulement les chemins effectivement créés ici.
Elle est renseignée avant l'écriture pour nettoyer aussi un fichier partiel.

Construire `PhotoRef` avant commit évite un cas subtil :
la ligne serait validée, puis sa conversion en réponse échouerait.
Le service possède ici le commit unique du parcours d'upload.
Le repository ne ferme pas prématurément sa transaction.

### 8.3 Le chemin d'échec

```python
        except BaseException:
            try:
                await self.db.rollback()
            finally:
                for path in created:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        logger.exception("Failed to clean up upload file %s", path)
            raise
        return response
```

La compensation tente rollback puis nettoyage des seuls chemins créés.
Le `finally` fait tenter le nettoyage même si rollback rencontre une erreur.
`missing_ok=True` rend acceptable un fichier déjà absent.
Une erreur d'unlink est journalisée au lieu d'interrompre toute la boucle.
`BaseException` inclut notamment des interruptions au-delà des erreurs métier.

**Ce n'est pas une transaction distribuée entre SQL et filesystem.**
Un crash du processus peut survenir entre deux étapes sans exécuter ce bloc.
Une erreur de disque peut laisser un fichier à nettoyer.
Un commit dont le résultat devient incertain n'est pas résolu par ce protocole.
La note ne promet donc ni atomicité absolue ni récupération automatique après crash.
Elle décrit une compensation locale pour les échecs interceptés.

## 9. Suppression : refuser le chemin avant toute suppression

Extrait de `delete_photo` :

```python
        root = Path(settings.UPLOAD_DIR).resolve()
        paths = []
        for raw in (photo.file_path, photo.thumbnail_path):
            if raw:
                path = Path(raw).resolve()
                if not path.is_relative_to(root) or path == root:
                    raise HTTPException(400, "Chemin de photo invalide")
                paths.append(path)
        await self.repo.delete(photo)
        for path in paths:
            path.unlink(missing_ok=True)
```

`resolve()` traite les chemins relatifs et les symlinks au moment du contrôle.
Une comparaison de simple préfixe texte ne serait pas suffisante :
`/uploads-other` ne doit pas être considéré comme un enfant de `/uploads`.
La racine elle-même n'est pas un fichier autorisé à supprimer.

Les deux chemins sont validés avant l'appel au repository.
Un chemin dangereux entraîne donc 400 avant suppression de la ligne.
Il ne faut pas attendre d'avoir supprimé l'original pour vérifier la miniature.

Le repository de suppression commit la suppression SQL.
Les unlink viennent ensuite.
Une erreur d'unlink peut donc laisser un fichier sans ligne SQL.
Le contrôle de chemin ne supprime pas cette limite transactionnelle.
Il ne constitue pas non plus une protection universelle contre une modification
concurrente hostile des symlinks après validation.

## 10. Migration : préflight avant toute écriture

### 10.1 Chaîne Alembic

```python
revision = "h105e0010001"
down_revision = "g104e0010001"
branch_labels = None
depends_on = None
```

La dépendance est INT-104, pas une branche indépendante.
Les tables changent de nom ; les identifiants et chemins sont conservés.
Les index sont renommés pour suivre `photo` et `material_usage`.
La conversion PostgreSQL de quantité utilise un cast explicite.

### 10.2 Conversion conservatrice des quantités

```python
def _quantity(value, row_id):
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    # Decimal comma is deliberately not interpreted: it can denote thousands.
    if not re.fullmatch(r"[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", text):
        raise RuntimeError(f"INT-105 quantity refused at id={row_id}: {value!r}")
```

Une quantité vide devient NULL.
La virgule n'est pas remplacée automatiquement par un point.
`1,000` peut signifier un décimal ou un séparateur de milliers.
Deviner produirait une migration techniquement réussie mais métier fausse.
L'erreur fournit l'identifiant permettant de corriger la source.

La suite du helper refuse les nombres non finis, non positifs, hors maximum
et ceux dont l'exposant représente plus de trois décimales.
Cette politique historique est volontairement conservatrice.
Elle ne prétend pas accepter toutes les notations reconnues par Decimal.

### 10.3 Pourquoi préflighter tout le jeu de données

```python
    quantities = [
        (row.id, _quantity(row.quantity, row.id))
        for row in bind.execute(sa.text("SELECT id, quantity FROM material"))
    ]
    # Every source row has passed preflight before any write or DDL.
```

La boucle photo valide auparavant chaque catégorie.
Les catégories legacy `avant`, `après`, `apres` deviennent BEFORE/AFTER.
Les six usages déjà canoniques sont admis.
Une catégorie inconnue bloque au lieu de devenir OTHER par défaut.

Le script collecte toutes les conversions avant UPDATE ou DDL.
Une mauvaise dernière ligne ne doit pas laisser les premières transformées.
Ce choix est utile notamment quand les garanties DDL du moteur diffèrent.
Il ne remplace pas une sauvegarde ni une répétition sur copie représentative.

Après préflight : UPDATE des valeurs, renommage des tables/colonnes,
ajout des CHECK et de `unit`, conversion en Numeric.
Toutes les unités historiques ajoutées restent NULL.
Ni une quantité ni une désignation ne permet d'inférer sûrement une unité.

### 10.4 Downgrade : refuser la perte, conserver le sens

```python
    for row in photos:
        if row.usage not in ("BEFORE", "AFTER"):
            raise RuntimeError(f"INT-105 downgrade refused usage at id={row.id}: {row.usage!r}")
    quantities = []
    for row in bind.execute(sa.text("SELECT id, quantity, unit FROM material_usage")):
        if row.unit is not None:
            raise RuntimeError(f"INT-105 downgrade refused unit at id={row.id}")
```

L'ancien modèle ne sait pas exprimer EQUIPMENT/ANOMALY/PART/OTHER.
Il ne sait pas conserver une unité.
Le downgrade les refuse avant modification au lieu de les jeter.
Un échec de downgrade demande une décision sur les données, pas un contournement.

`02.00` devient numériquement `2`, puis texte `"2"` au retour legacy.
Le roundtrip conserve la valeur, pas les octets de la graphie initiale.
Cette limite est annoncée dans le module de migration et vérifiée par test.
Les identifiants, rattachements et chemins ne doivent pas changer.

## 11. Guards composés : ne pas réécrire l'histoire

Les fixtures R0/R7 restent des preuves historiques.
INT-105 ne les remplace pas par un nouveau résultat présenté comme équivalent.
Il valide son delta, puis projette vers le contrat INT-104.
INT-104 conserve à son tour ses propres contrôles.

Extrait de `contract_int105.py` :

```python
RENAMED_TABLES = {"photo": "intervention_photo", "material_usage": "material"}
USAGES = {"BEFORE", "AFTER", "EQUIPMENT", "ANOMALY", "PART", "OTHER"}
```

Le guard metadata vérifie explicitement les noms, types, nullabilités,
contraintes et FK attendus avant la projection.
Un changement non déclaré dans une autre table reste une erreur.
Le nombre de tables reste 19 : il s'agit ici de renommages, pas de deux ajouts.
Le registre des modèles et les tests de bootstrap suivent les nouveaux modules.

La projection import est particulièrement stricte :

```python
def project_import_database(database):
    projected = deepcopy(database)
    for new, old in RENAMED_TABLES.items():
        assert old not in database
        assert database[new] == [], f"Import unexpectedly populated {new}"
        projected[old] = projected.pop(new)
    return project_import_database104(projected)
```

L'import historique ne doit pas inventer des photos ou consommations.
Une table non vide n'est pas effacée silencieusement par la projection.
`deepcopy` empêche le guard de modifier la preuve qu'il examine.
Les tests purs injectent des mutations pour démontrer les refus.
Un guard qui ne teste que son cas heureux pourrait cacher une projection trop large.

Le guard OpenAPI vérifie entre autres :

- les six valeurs d'enum et le formulaire requis `file`/`usage` ;
- l'absence du contrat photo `category` ;
- les trois champs de création matériel et `additionalProperties: false` ;
- la réponse quantity `number | null` et unit `string | null` ;
- les champs d'update omissibles ;
- la nouvelle liste GET photos ;
- la préservation des autres chemins et du delta INT-104.

## 12. Consommateurs : interface et rapport parlent V2

### 12.1 Six groupes visibles

Extrait de `frontend/src/utils/interventionMedia.ts` :

```typescript
export const photoUsages: { value: PhotoUsage; label: string }[] = [
    { value: "BEFORE", label: "Avant" },
    { value: "AFTER", label: "Après" },
    { value: "EQUIPMENT", label: "Équipement" },
    { value: "ANOMALY", label: "Anomalie" },
    { value: "PART", label: "Pièce" },
    { value: "OTHER", label: "Autre" },
];

export function groupPhotos(photos: PhotoResponse[]) {
    return photoUsages.map((usage) => ({
        ...usage,
        photos: photos.filter((photo) => photo.usage === usage.value),
    }));
}
```

Le client multipart ajoute `usage`, pas `category`.
La page utilise ces libellés pour la sélection et les groupes.
L'interface de lecture matériel accepte quantity/unit nullables.
L'interface d'écriture exige une quantité numérique et une unité.
Cette différence de types représente l'historique plutôt qu'un oubli.

Les lignes locales portent dirty/saving/error.
`reconcileMaterials` conserve les saisies partielles et les nouvelles lignes
pendant un rafraîchissement, au lieu de les écraser par la réponse serveur.
La validation frontend améliore le retour immédiat.
Le backend demeure la frontière d'intégrité.

### 12.2 Rapport effectivement rendu

Extrait du renderer :

```python
        materials_list = []
        for mat in intervention.materials or []:
            quantity = "---" if mat.quantity is None else format(mat.quantity, "f")
            if "." in quantity:
                quantity = quantity.rstrip("0").rstrip(".")
            materials_list.append({
                "designation": mat.designation, "quantity": quantity, "unit": mat.unit,
            })
```

Le rapport ne réutilise pas une vieille colonne `name`.
Il affiche le nombre décimal sans zéros finaux inutiles.
NULL est affiché comme une absence connue, pas une quantité zéro.
Le renderer construit six groupes photo et ne transmet que les groupes non vides.
Les images sont embarquées sous forme de data URI quand leur lecture réussit.

Extrait du template :

```html
    <td>{{ mat.designation }}</td>
    <td>{{ mat.quantity }}</td>
    <td>{{ mat.unit or '---' }}</td>
```

Le renderer initialise `Template(f.read(), autoescape=True)`.
Une désignation contenant du HTML doit rester du texte rendu échappé.
Il ne faut pas ajouter `safe` aux champs utilisateur pour arranger l'affichage.
La vérification du rapport doit porter sur le rendu, pas seulement sur un DTO.
INT-105 ne transforme pas pour autant le rapport en nouveau système versionné.

## 13. Stratégie de validation et preuves disponibles

### 13.1 Ce que couvrent les tests lus

Les tests media produisent de vraies images Pillow et contrôlent usages,
formats, URL, listes/détail, miniature et suppression. Les refus couvrent
faux JPEG, MIME interdit et dépassement. L'échec de commit injecté vérifie
rollback et conservation d'un fichier tiers, pas la récupération après crash.
Les tests combinent mauvais parent/technicien, bornes matériel, champs requis,
alias refusés, null explicite, édition partielle et lecture historique NULL.
Les migrations utilisent des bases jetables : roundtrip, index, FK et refus.
La chaîne PostgreSQL vide signalée ne vaut pas migration d'une base existante.

### 13.2 Résultats intermédiaires transmis, pas validation finale

| Preuve transmise | Résultat connu | Portée / réserve |
|---|---|---|
| Travailleur guards purs | 21 passed | Tests purs ; pas suite applicative complète |
| Travailleur migration | 34 passed | Dont chaîne PostgreSQL vide ; données jetables |
| Sous-ensemble signalé avant intégration | 7 passed | Résultat antérieur au run final parent |
| Travailleur frontend Bun | 10 passed | Utilitaires frontend |
| Travailleur frontend typecheck/build | Réussite signalée | Ni navigateur ni déploiement |
| Suite backend finale parent | **539 passed, 7 skipped, 7 warnings** | SQLite/schémas et uploads temporaires ; 115,23 s |
| Run PostgreSQL final parent | **200 passed, 2 warnings** | Cible PostgreSQL 17.4 jetable ; 64,59 s |
| Frontend final parent | **10 tests, 36 assertions**, typecheck/build réussis | Bun 1.2.20, Vite 6.4.3, 452 modules |
| Smoke navigateur média | Réussi, avec rectification et réexécution du PUT | Détails et réserves ci-dessous |
| CI distante | Non établie | Aucun run distant réussi attesté ici |
| Déploiement | Non réalisé dans cette rédaction | Aucun effet sur une instance réelle |

Une première tentative globale a exposé des références à deux anciens modules
et un pattern Decimal insuffisamment borné dans le contrat publié.
Le parent a corrigé ces causes dans les sources et consommateurs, ainsi que
l'absence de type de retour du serializer Decimal : sans `-> float | None`,
la réponse runtime était numérique mais son schéma OpenAPI annonçait encore
une chaîne. Le guard et les tests API vérifient maintenant le même contrat.
Cette tentative n'est pas retenue comme état final de validation.
La note explique les causes sans afficher un échec intermédiaire comme conclusion.

### 13.3 Exécutions parent et réserves

```text
Suite backend : 539 passed, 7 skipped, 7 warnings, 115.23 s.
Run PostgreSQL canonique + médias + migrations + verrouillage :
  200 passed, 2 warnings, 64.59 s.
Runner : backend/.venv/bin/python du checkout principal existant.
Cwd/SQLite/uploads : scratch ; aucun seed sur une base applicative.
Frontend : bun test tests (10 pass/36 assertions), typecheck et build réussis.
Pattern Decimal : borné sur la chaîne complète sans recopier les limites numériques.
Serializer : type de retour explicite ; réponse JSON et OpenAPI number|null concordent.
Revue : aucun bloqueur comportemental ; tests des deux chemins hors UPLOAD_DIR ajoutés.
Smoke navigateur : login, photos/miniatures/preview, matériel POST/PUT/DELETE vérifiés.
Réserve : DB et filesystem ne forment pas une transaction distribuée.
```

Conserver les sorties, skips et warnings : SQLite n'est pas PostgreSQL,
et une réussite build n'est pas un smoke utilisateur.

Les sept skips du run sans URL PostgreSQL concernent les chaînes migration
checklist/media et les cinq cas de verrouillage INT-104. Ils sont exécutés dans
le run PostgreSQL dédié. Les warnings sont ceux de `crypt`/passlib et des appels
`datetime.utcnow()` existants ; ils ne sont pas cachés.

La vraie commande Alembic avec `env.py` a également réussi
`upgrade head → downgrade -1 → upgrade head`, tête `h105e0010001`.
`alembic check` reste à **255** uniquement pour la FK technicien historique
sans `ON DELETE` côté SQL et `SET NULL` côté ORM. Une comparaison structurée
exige exactement ces deux opérations remove/add ; aucun nouvel écart INT-105.
Ce n'est pas un check Alembic vert.

Commandes parent réellement exécutées, avec `PYTHONPATH=backend` et les variables
SQLite/uploads ou URLs PostgreSQL jetables :

```sh
# Depuis le cwd scratch, avec le Python du venv existant :
"$ROOT/backend/.venv/bin/python" -m pytest "$ROOT/backend/tests" \
  -q --tb=short -p no:cacheprovider

# PostgreSQL : neuf fichiers canoniques, puis test_media_locking.py :
"$ROOT/backend/.venv/bin/python" -m pytest \
  "$ROOT/backend/tests/test_installations.py" \
  "$ROOT/backend/tests/test_sales.py" \
  "$ROOT/backend/tests/test_installation_migration.py" \
  "$ROOT/backend/tests/test_import_service_v2.py" \
  "$ROOT/backend/tests/test_import_api_v2.py" \
  "$ROOT/backend/tests/test_int104_checklists.py" \
  "$ROOT/backend/tests/test_checklist_migration.py" \
  "$ROOT/backend/tests/test_int105_media.py" \
  "$ROOT/backend/tests/test_media_migration.py" \
  "$ROOT/backend/tests/test_media_locking.py" \
  -q --tb=short -p no:cacheprovider
```

`ROOT` désigne `/home/lob/workspace/python/fastapi/Tervo`.
Docker utilise `postgres:17.4 --pull never`, un port loopback éphémère,
aucun volume existant et un arrêt en fin de run. La nouvelle étape PostgreSQL
media du workflow CI utilise `TERVO_MEDIA_TEST_DATABASE_URL` et
`TERVO_MEDIA_MIGRATION_TEST_URL` ; sa configuration n'est pas un run distant validé.

### 13.4 Commandes de reproduction, non exécutées par cette rédaction

Depuis un environnement backend disposant des dépendances du projet :

```sh
cd backend
uv run pytest tests/test_contract_int105.py
uv run pytest tests/test_media_migration.py
uv run pytest tests/test_int105_media.py
uv run pytest
```

Depuis le frontend avec Bun et les dépendances installées :

```sh
cd frontend
bun test tests/interventionMedia.test.ts
bun run typecheck
bun run build
```

Les scripts `typecheck` et `build` sont présents dans `frontend/package.json`.
Le parent doit inscrire ses commandes exactes, avec le runner réellement utilisé.
Les tests PostgreSQL nécessitent la configuration prévue par leurs fixtures.
Ne pas substituer l'URL de la base applicative à une cible jetable.
Ne pas lancer un seed pour « préparer » une base existante à ces tests.

### 13.5 Preuve navigateur ajoutée après le commit de développement

Le commit INT-105 `5b8eb36` a été réalisé avant réception complète du smoke ;
cet enrichissement documentaire ne prétend pas à une nouvelle implémentation.
Playwright 1.49.1, Chromium 131.0.6778.33 / v1148, SQLite/uploads fictifs,
backend avec le venv existant et frontend build isolé.

- Login UI réel réussi.
- PNG ANOMALY et EQUIPMENT : 201, groupes corrects, vraies miniatures et preview.
- TXT volontairement invalide : 400, message visible, photos existantes conservées.
- Suppression photo : 204 et disparition ligne/fichier.
- Matériel POST : `{designation: "Câble", quantity: 0.5, unit: "m"}`, réponse 201
  avec ces valeurs numériques/unités.
- Matériel PUT réexécuté et capturé : `{designation: "Câble", quantity: 0.75,
  unit: "free"}`, réponse JSON 200 avec `quantity: 0.75` et `unit: "free"`.
- Unité vide : message de validation frontend et **zéro requête PUT**.
  Une première observation du scout avait annoncé à tort un PUT 200 ; elle
  est retirée. La preuve positive ci-dessus repose sur payload/réponse capturés.
- Brouillon non sauvegardé conservé au changement d'onglet ; DELETE matériel 204.
- Iframe PDF chargée, mais pas d'extraction textuelle des usages/unités dans ce smoke.

Aucun pageerror ; le HTTP 400 injecté par le fichier invalide est distingué
des erreurs inattendues. Tous les processus de recette sont arrêtés.
Les preuves restent fictives, sans seed/base applicative.

Écart de procédure déclaré : le fallback du scout a téléchargé Chromium dans
`/home/lob/.cache/ms-playwright`, plutôt que dans son scratch. Ce cache est
conservé, sans suppression/désinstallation ; les réexécutions l'utilisent en
lecture seule. Aucune installation Python utilisateur n'a été effectuée.

## 14. Limites et sujets différés

Les critères minimaux INT-105 ne livrent pas tout le DAT photo.
La persistance dédiée du filename d'origine, MIME, taille et audit des suppressions
n'est pas implémentée par ce modèle minimal.
Les contrôler transitoirement à l'upload n'équivaut pas à les historiser.

Le minimum de photos avant/après reste différé : TD-B004, phase 2.
Les six usages ne rendent pas cette règle obligatoire à la clôture.
La présence de BEFORE/AFTER ne prouve pas que les photos sont suffisantes métier.

TD-B013 reste le sujet des rôles élargis.
TD-B016 demande une mesure sur volume représentatif.
Une migration sur base vide ne clôture pas une étude de charge ni un import réel.
TD-B019 concerne le seed unsafe ; cette note ne valide pas son usage réel.
TD-F008, administration des modèles, n'est pas le périmètre frontend de cette tâche.

Le filesystem reste une dépendance locale avec des risques de crash et nettoyage.
Une évolution future pourrait prévoir une réconciliation des fichiers orphelins,
ou un protocole de stockage plus robuste, avec ses propres preuves.
Il n'est pas nécessaire de prétendre que cette évolution existe déjà.
