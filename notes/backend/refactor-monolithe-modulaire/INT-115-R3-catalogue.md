# INT-115 — R3 : extraction verticale du catalogue Product

> **Planning :** [refactor monolithe modulaire](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md).
> **Branche :** `refactor/modular-monolith`.
> **Parent R2 :** `ed67168c5ddbda80a81fb1264f83ad3d8d0f8005`.
> **État :** R3 accepté et revérifié après naming ; livraison dans le commit INT-115 contenant cette note, après le commit de naming documentaire `8f3e876`. R4 non commencé, feu vert distinct requis.
> **Preuve :** [R3-validation.json](R3-validation.json), capture avant naming conservée et section `post_naming` avec résultats et empreintes des sources finales.

`app/modules` reste inchangé ; seul le package Python devient `catalog` (anglais américain), avec `tests/test_catalog_module.py`. Routes `/products`, classes et `catalogue_editor` restent inchangés. Le titre français et le nom historique de cette note sont conservés, ainsi que les captures R0/R1/R2, sans réécriture Git. Les résultats initiaux sont distingués des réexécutions après naming, détaillées en section 10.

## 1. Reprise de R2 et périmètre strict de R3

L'utilisateur a validé R2, demandé son commit propre, puis autorisé R3 distinctement. R2 a été committé sous `[DEV]INT-114 — Refactor : isoler le domaine customers` (`ed67168`), après vérification des empreintes des sources/artefacts et réexécution des **43 tests ciblés**.

Le worktree Delta ne possédait pas encore de venv. `cd backend && uv sync --frozen` l'a recréé depuis le lockfile inchangé, avec Python **3.12.0**. Les premières preuves R2 n'ont pas été réécrites : leurs mentions « non committé » restent des états de capture historiques.

R3 ne livre ni catalogue nouveau, ni règle d'activité supplémentaire, ni stock. Il déplace le catalogue existant dans sa frontière métier :

```text
app/modules/catalog/
├── __init__.py
├── models.py
├── schemas.py
├── repository.py
├── service.py
└── api.py
```

Le choix est un **déplacement vertical**, pas une façade au-dessus des anciens fichiers. Une façade laisserait deux chemins actifs à entretenir et masquerait le cutover. Ici les cinq fichiers legacy disparaissent, les consommateurs changent leurs imports et les définitions métier restent identiques.

| Avant, sous `backend/app/` | Propriétaire actuel |
|---|---|
| `models/product.py` | `modules/catalog/models.py` |
| `schemas/product.py` | `modules/catalog/schemas.py` |
| `repositories/product.py` | `modules/catalog/repository.py` |
| `services/product.py` | `modules/catalog/service.py` |
| `api/v1/products.py` | `modules/catalog/api.py` |

`__init__.py` ne contient qu'une docstring. Importer le package n'importe donc pas l'API, n'instancie pas d'engine et ne charge pas le registre global. Chaque couche est importée explicitement là où elle sert.

## 2. Product reste une référence, pas un appareil physique

La référence commerciale est partagée par plusieurs instances installées :

```text
Product ──► Equipment (plusieurs appareils physiques)
       └──► SaleLine (provenance commerciale)
```

Product porte référence, nom, marque, modèle, catégorie, description, caractéristiques JSON et activité. Il ne possède ni numéro de série d'appareil, ni site, ni quantité en stock, ni prix catalogue ajouté par R3.

Extrait fidèle du [modèle déplacé](../../../backend/app/modules/catalog/models.py#L7-L12) :

```python
class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
```

Le module importe la **même** `Base` depuis `app.core.base`. Le nom Python du package change ; `__tablename__`, colonnes, contraintes, index, valeurs par défaut et relations ne changent pas.

L'activité conserve ses deux valeurs par défaut :

```python
active = Column(Boolean, nullable=False, default=True, server_default=true())
```

- `default=True` s'applique aux écritures ORM ;
- `server_default=true()` représente le défaut SQL pour une écriture qui omet la colonne.

Les deux sont préservés. Une simple comparaison des comptes de tables ne suffirait pas à prouver cela : R3 compare aussi l'AST complet des modules déplacés, hors imports.

`Product.equipment` et `Equipment.product` restent bidirectionnels avec `back_populates`. `SaleLine.product` reste une relation vers Product, sans inventer une collection inverse `Product.sale_lines`. La FK de ligne de vente garde `ON DELETE RESTRICT`. Aucune cascade destructrice n'est ajoutée.

## 3. Rôle des couches : même code, propriétaire explicite

| Couche | Responsabilité conservée |
|---|---|
| `api.py` | Routage HTTP, auth, validation des paramètres de pagination, injection de la session |
| `schemas.py` | Corps Pydantic stricts, contraintes des chaînes, réponses et PATCH |
| `service.py` | Produit introuvable, unicité de référence, pagination de réponse, désactivation, conversion des conflits SQL |
| `repository.py` | Lectures SQL, filtres/recherche, tri, pagination et persistance avec commit/refresh existants |
| `models.py` | Table et relations ORM |

Le routeur utilise le service local :

```python
from app.modules.catalog.service import ProductService

@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(body: ProductCreate, user: User = Depends(catalogue_editor),
                         db: AsyncSession = Depends(get_db)):
    return await ProductService(db).create_product(body)
```

Ce n'est pas une nouvelle API : nom de fonction, décorateur, statut et dépendances sont conservés, donc aussi l'identifiant d'opération OpenAPI. `app/router.py` inclut ce routeur à la position historique, entre sites et equipment.

## 4. Contrats HTTP et auth inchangés

Préfixe effectif : `/api/v1/products`, tag : `products`.

| Méthode / route | Résultat normal | Accès actuel |
|---|---|---|
| `GET /products` | `200`, liste paginée | Authentifié |
| `POST /products` | `201`, produit créé | ADMIN |
| `GET /products/{product_id}` | `200`, produit | Authentifié |
| `PATCH /products/{product_id}` | `200`, produit modifié | ADMIN |
| `POST /products/{product_id}/deactivate` | `200`, produit inactif | ADMIN |

Il n'y a pas de DELETE métier : `DELETE /products/{id}` reste **405**. Désactiver n'est pas supprimer.

L'auth n'est pas modernisée sous couvert de déplacement :

```python
async def catalogue_editor(user: User = Depends(get_current_user)):
    # Todo later (TD-B013): allow MANAGER/COMMERCIAL when these roles exist.
    if user.role != Role.ADMIN:
        raise HTTPException(403, "Gestion du catalogue réservée aux administrateurs")
    return user
```

TECHNICIAN lit mais n'écrit pas. MANAGER et COMMERCIAL restent absents du modèle actuel ; le todo TD-B013 est ouvert, avec son chemin API actualisé vers `modules/catalog/api.py`.

### Création et validation

Exemple de requête conforme :

```json
{
  "reference": "R3-HISTORY",
  "name": "PAC historique",
  "brand": "Tervo",
  "model": "R3",
  "category": "PAC",
  "description": "Catalogue conservé",
  "characteristics": { "power_kw": 12 }
}
```

Le serveur applique `active=true` par défaut. `reference` et `category` utilisent des chaînes de 1 à 100 caractères ; nom, marque et modèle de 1 à 255. `strip_whitespace=True` nettoie les espaces avant validation. Une chaîne vide après nettoyage est refusée. `extra="forbid"` interdit les champs inconnus ; `characteristics` doit être un dictionnaire ou `null`.

### PATCH : omis n'est pas null

Le contrat distingue :

- champ absent : ne pas toucher sa valeur ;
- `description=null` ou `characteristics=null` : effacer ce champ facultatif ;
- `reference=null`, `name=null`, `brand=null`, `model=null`, `category=null` ou `active=null` : **422**.

Le validateur et le service restent tels quels :

```python
@model_validator(mode="after")
def reject_null_required_fields(self):
    for field in self.model_fields_set - {"description", "characteristics"}:
        if getattr(self, field) is None:
            raise ValueError(f"{field} ne peut pas être null")
    return self
```

```python
values = data.model_dump(exclude_unset=True)
```

`model_fields_set` dit quels champs ont réellement été fournis ; `exclude_unset=True` empêche un PATCH partiel d'écraser les autres valeurs par leurs défauts.

### Recherche et pagination

`GET /products` conserve `page=1`, `page_size=25`, limites de 1 à 100 et l'alias `limit`, prioritaire lorsqu'il est fourni. Filtres : `search`, `brand`, `category`, `active`.

Le repository recherche sans distinction de casse dans référence, nom, marque et modèle. `%` et `_` sont échappés : ils restent des caractères littéraux de recherche, pas des jokers SQL imposés par l'utilisateur.

```python
pattern = "%" + search.replace("/", "//").replace("%", "/%").replace("_", "/_") + "%"
```

Le tri reste `(Product.name, Product.id)` avant offset/limit. Les clés de réponse restent `items`, `total`, `page`, `page_size`, `pages`, avec au moins une page même si le résultat est vide. Aucun renommage de paramètre ou changement de tri n'est inclus dans R3.

## 5. Unicité et transaction : ne pas généraliser le pattern des installations

La règle de référence unique possède deux protections :

1. `_check_reference()` relit une référence existante et retourne **409** avant l'écriture si un autre produit la possède.
2. La contrainte SQL unique reste l'arbitre final, notamment si deux requêtes passent simultanément la pré-vérification.

Le repository catalogue possède déjà son commit. R3 **conserve ce propriétaire**, même si le repository installations fonctionne autrement :

```python
async def save(self, product):
    self.db.add(product)
    await self.db.commit()
    await self.db.refresh(product)
    return product
```

Le service gère le conflit :

```python
async def _save(self, product):
    try:
        return await self.repo.save(product)
    except IntegrityError:
        await self.db.rollback()
        raise HTTPException(409, "Référence produit déjà utilisée") from None
```

Le rollback rétablit la session après l'erreur SQL ; le 409 est le contrat public. Le nouveau test injecte `IntegrityError` dans `repo.save`, vérifie l'appel au rollback et le message exact. Il s'agit d'un **test contrôlé de cette branche**, pas d'une preuve de concurrence réelle entre deux créations Product.

Pas de UnitOfWork, de session supplémentaire, de bus ou de commit transverse introduit. `ProductService` et son repository partagent la session injectée. SaleService, EquipmentService et ImportService ne sont pas réécrits pour passer systématiquement par ce service : appeler son commit au milieu d'un sous-lot d'import changerait les frontières transactionnelles.

## 6. Désactivation et consommateurs : préserver le réel

La désactivation est une mise à jour :

```python
async def deactivate_product(self, product_id):
    product = await self.get_product(product_id)
    product.active = False
    return await self._save(product)
```

Elle reste répétable et le produit reste consultable. Un PATCH `{"active": true}` permet toujours la réactivation.

**Règle actuelle importante : les nouveaux équipements et les nouvelles ventes peuvent aussi référencer un produit inactif.** EquipmentService l'autorise explicitement ; SaleService vérifie l'existence du produit, pas `active`. R3 ne transforme pas cet état en interdiction implicite. Si l'on veut changer cette politique commerciale, il faut un cadrage métier distinct.

Les consommateurs adaptés sont :

- `EquipmentService` : importe Product depuis `catalog`, garde ses règles physiques et son historique de remplacement ;
- `SaleService` : garde ses vérifications client/site/produit, lignes, prix Decimal et transaction ;
- `ImportPlanner` : utilise le même `ProductCreate`, déplacé ;
- `ImportService` : utilise la même classe Product dans `MODELS`, avec les mêmes verrous SQL et commits par sous-lot ;
- tests équipements, ventes, installations et service d'import : imports orientés vers la nouvelle implémentation.

Le registre explicite charge Product depuis `catalog`. Le réexport transitoire `app.models.Product` reste le **même objet**, pas une classe wrapper. Les FK et les relations stringifiées se résolvent après `load_models()` et `configure_mappers()`.

## 7. Preuve structurelle et tests supplémentaires

Les cinq modules legacy du commit R2 ont été lus avec `git show ed67168:<path>` et comparés aux cinq modules déplacés par AST. On retire uniquement les nœuds `Import` et `ImportFrom` de premier niveau ; **tout le reste doit être égal** :

- les **13 définitions** de classes/fonctions, avec méthodes et décorateurs ;
- les alias de validation, docstrings et affectations de module ;
- les colonnes/index/defaults/relations ORM ;
- les branches métier, requêtes, commits, rollback et messages.

Aucune normalisation de nom de routeur n'est nécessaire ici : l'export s'appelle toujours `router`. Cette vérification complète la metadata R0, qui ne sérialise pas tous les détails des index et des defaults Python.

`tests/test_catalog_module.py` (nom après naming) ajoute **7 cas collectables** :

| Scénario | Preuve attendue |
|---|---|
| Structure et scan AST des imports | Six fichiers locaux, init pur, cinq sources legacy absentes, aucun import legacy actif |
| Import pur `models` | Une table Product seule, sans engine/API/package legacy |
| Import pur `schemas` | Aucune table et schéma utilisable |
| Catalogue-first | Même Product et Base après chargement du legacy et du registre |
| Legacy-first | Même identité, 17 mappers, FK et relations résolues, registre idempotent |
| Désactivation multi-domaines | Client/site/produit/vente/ligne/équipement créés via API, données et liens conservés |
| `IntegrityError` contrôlée | Rollback appelé, 409 et détail exact |

Le scénario API utilise une vraie SQLite temporaire avec FK actives et un JWT ADMIN de la fixture installations. Il relit les données avec une nouvelle session, vérifie notamment `SaleLine.unit_price == Decimal("1250.50")` et conserve les IDs, séries, notes et caractéristiques.

Les routes de lecture products/equipment/clients/sites sont exercées. Sales n'expose **pas de GET détail** : le test utilise sa route existante de confirmation, vérifie que seules `status` et éventuellement `updated_at` changent. Une nouvelle vente et un nouvel équipement sur le produit désactivé restent acceptés, conformément au code existant.

Les tests produits antérieurs restent intacts et couvrent CRUD, filtres, unicité, champs nuls, auth, 405 DELETE, réactivation et migration produit isolée. Les suites consommateurs/imports sont rejouées, pas remplacées par le seul test de structure.

## 8. Validations réellement exécutées — capture avant naming

| Vérification | Résultat observé |
|---|---|
| Bootstrap + catalogue + produits + équipements + ventes + installations + imports service/API | **128 passed**, 1 warning, 38,25 s |
| Suite backend entière SQLite | **299 passed**, 5 warnings, 66,98 s |
| PostgreSQL 17.4 : ventes/installations/migrations | **56 passed**, 1 warning, 23,52 s |
| PostgreSQL 17.4 : imports service/API | **39 passed**, 1 warning, 26,47 s |
| PostgreSQL `upgrade head → downgrade -1 → upgrade head` | Réussite, head `f102e0010001` |
| `alembic check` | Code 255 attendu : uniquement la FK technicien connue |
| Autogenerate structuré | `remove_fk`/`add_fk` égaux à R2, aucune nouvelle opération |
| OpenAPI complète | Égale à R0/R1/R2 : 46 chemins, 63 opérations |
| Metadata complète | Égale à R0/R1/R2 : 17 tables |
| Uvicorn réel et HTTP | Startup/shutdown complets ; `/docs` et `/openapi.json` : 200 |
| Fichiers Alembic, preuves JSON R0/R1/R2, fixtures d'import | Inchangés |

**299 = 292 R2 + 7 nouveaux cas R3.** Les groupes PostgreSQL sont des réexécutions ciblées, pas 95 tests nouveaux.

Une revue indépendante a comparé le cutover au parent `ed67168`, sans finding. Elle a rejoué uniquement le test de module (désormais nommé `test_catalog_module.py`) et `test_products.py` dans son environnement temporaire, avant naming : **19 passed, 1 warning**. Elle n'a pas répété les suites complètes ni présenté les résultats PostgreSQL du parent comme une exécution indépendante.

### Commandes et isolation

Le venv est installé avec `uv`. Les vérifications utilisent ensuite directement `backend/.venv/bin/python` depuis un cwd temporaire, pour éviter les `create_all/drop_all` historiques sur un fichier SQLite du projet :

```text
cd backend && uv sync --frozen
python -m pytest <8 fichiers ciblés, chemins absolus> -q -p no:cacheprovider
python -m pytest <backend>/tests -q -p no:cacheprovider
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini downgrade -1
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini check
python -m pytest <tests installations/ventes/migration> -q -p no:cacheprovider
python -m pytest <tests import service/API> -q -p no:cacheprovider
python -m uvicorn app.main:app --host 127.0.0.1 --port <port libre>
git diff --check
```

`PYTHONPATH` pointe sur le backend source, `DATABASE_URL` SQLite et `UPLOAD_DIR` pointent vers le dossier temporaire. Les variables `TERVO_*` sont retirées pour la suite SQLite. Pour PostgreSQL, les quatre variables de fixtures habituelles ciblent le serveur jetable ; `DATABASE_URL` synchrone ne sert qu'aux commandes Alembic.

L'enveloppe SQLite exécutée suit ce schéma reproductible, depuis la racine du dépôt :

```python
backend = Path.cwd() / "backend"
files = [
    "test_modular_bootstrap.py", "test_catalog_module.py", "test_products.py",
    "test_equipment.py", "test_sales.py", "test_installations.py",
    "test_import_service_v2.py", "test_import_api_v2.py",
]
with tempfile.TemporaryDirectory(prefix="tervo-r3-tests-") as work:
    env = {k: v for k, v in os.environ.items() if not k.startswith("TERVO_")}
    env.update(
        PYTHONPATH=str(backend),
        DATABASE_URL="sqlite:///./tervo.db",
        UPLOAD_DIR=str(Path(work) / "uploads"),
    )
    for paths in (
        [str(backend / "tests" / file) for file in files],
        [str(backend / "tests")],
    ):
        subprocess.run(
            [str(backend / ".venv/bin/python"), "-m", "pytest",
             *paths, "-q", "-p", "no:cacheprovider"],
            cwd=work, env=env, check=True, timeout=240,
        )
```

Cet extrait omet seulement la capture des sorties pour la synthèse JSON. Il utilise `Path`, `os`, `tempfile` et `subprocess` de la bibliothèque standard ; il ne doit pas être lancé depuis `backend/`, car la résolution de racine serait différente.

Le conteneur utilise l'image existante `postgres:17.4`, `--pull never`, un port aléatoire publié sur **127.0.0.1** et aucun volume nommé. Il est supprimé dans `finally`. Uvicorn est terminé et attendu après les lectures HTTP ; son code `-15` correspond à SIGTERM, avec shutdown ASGI complet, pas à une erreur applicative.

### Essais initiaux non retenus comme réussites

Un premier démarrage PostgreSQL a répondu à `pg_isready` sur le serveur provisoire d'initialisation avant que la base de test existe. Le conteneur a été supprimé ; l'attente a été corrigée pour exiger une requête SQL TCP sur cette base.

Le premier run ciblé a donné **127 passed / 1 failed** : le nouveau test supposait à tort l'existence de `GET /sales/{id}`. Le test a été corrigé pour utiliser `POST /sales/{id}/confirm`. Aucune route supplémentaire n'a été créée pour rendre vert un test incorrect. Les résultats finaux du tableau viennent des runs après cette correction.

### Alembic : zéro nouvelle différence, pas zéro différence totale

Le SQL historique de `job_technician_id_fkey` n'a pas `ON DELETE SET NULL`, contrairement à l'ORM. Les opérations normalisées sont exactement :

```text
remove_fk : intervention.technician_id → user.id, ondelete=None
add_fk    : intervention.technician_id → user.id, ondelete=SET NULL
```

Cet écart est celui de R0, conservé. Aucune migration n'est créée ou corrigée pour déplacer un package Python. La chaîne Alembic complète SQLite reste incompatible avec l'ancien `ALTER TYPE` PostgreSQL et n'a pas été rendue portable ici.

## 9. Preuves, todos et prochaine décision

[R3-validation.json](R3-validation.json) conserve les commandes/périmètres, comptes et durées observés, opérations Alembic normalisées, résultats HTTP, comparaison AST et empreintes des **19 sources/tests** de R3. Il ne duplique pas les gros snapshots : les snapshots recalculés sont égaux et sérialisés **octet pour octet** comme R0 ; leurs références et SHA-256 sont dans le manifeste.

Les todos backend/frontend ont été relus. Aucun besoin métier n'est débloqué par le move : TD-B013 (rôles), TD-B016 (volume représentatif), TD-F007 (interfaces V2) restent ouverts. TD-B013 pointe désormais sur la nouvelle API ; TD-B012 retrouve le modèle Product dans `catalog`. Les notes R1/R2 restent des explications de leurs propres captures, avec état de reprise actualisé pour R2.

Limites :

- validation locale Python 3.12.0, pas de run CI distant Python 3.11 ;
- le nouveau scénario historique et le test contrôlé rollback ne sont pas présentés comme exécutés sur PostgreSQL ; les 95 réexécutions PostgreSQL sont les groupes existants ;
- aucune exécution du seed destructeur, aucune base existante migrée ;
- aucun build frontend, E2E navigateur, déploiement, push ou réécriture Git ;
- comparaison complète avant/après des journaux du pack d'import réservée à R9 ;
- R3 est accepté par l'utilisateur et revérifié après naming ; **R4 / INT-116 n'est pas commencé**, feu vert distinct requis.

## 10. Naming final `catalog` et revalidation avant commit

L'utilisateur a retenu `modules`, pas `contexts`. `catalog` est le nom anglais américain du package ; « catalogue » reste le vocabulaire métier français. Le renommage concerne six fichiers du package, les imports et les tests, pas les routes `/products`, les classes Product, les fonctions API ou `catalogue_editor`.

Le cutover doit être complet : il n'y a pas de wrapper `app.modules.catalogue`. Les tests interdisent les anciens imports et vérifient qu'aucun fichier Python source ne subsiste sous ce nom. Les anciens fichiers horizontaux Product sont également absents. Le modèle et le schéma restent identiques ; les autres couches ne diffèrent que par les imports.

Le premier essai de renommage a révélé une divergence entre le succès annoncé par l'outil de déplacement et les fichiers réellement présents sur disque : les imports visaient `catalog` mais les six fichiers étaient encore sous `catalogue`. La collection SQLite a retourné 2 avec six erreurs d'import, et la validation PostgreSQL déléguée a été bloquée. Des opérations explicites ajout/suppression ont corrigé les chemins ; les résultats suivants proviennent uniquement des runs après correction.

| Vérification après naming | Résultat observé |
|---|---|
| Huit fichiers de tests ciblés, dont `test_catalog_module.py` | **128 passed**, 1 warning, 39,39 s |
| Suite complète SQLite | **299 passed**, 5 warnings, 65,51 s |
| PostgreSQL 17.4 : ventes/installations/migrations | **56 passed**, 1 warning, 23,18 s |
| PostgreSQL 17.4 : imports service/API | **39 passed**, 1 warning, 25,41 s |
| Alembic `upgrade head → downgrade -1 → upgrade head` | Réussite |
| `alembic check` et autogenerate structuré | Code 255, uniquement les deux opérations FK historiques égales à R2 et R3 initial |
| HTTP `/docs`, `/openapi.json` et cycle ASGI | 200, startup/shutdown complets |
| Snapshots recalculés | OpenAPI/metadata sérialisées octet pour octet comme R0/R1/R2 |
| AST des cinq couches, hors imports | Égal au parent R2, 13 définitions |

Les commandes et précautions de la section 8 ont été reprises, avec le nom de test final `test_catalog_module.py`. Les nouveaux conteneurs et le processus Uvicorn ont été nettoyés. L'exécution PostgreSQL bloquée du scout n'est pas présentée comme une réussite : les résultats PostgreSQL finaux ont été exécutés ensuite par l'agent principal.

La section `post_naming` de `R3-validation.json` garde les nouvelles empreintes des 19 sources/tests ; les empreintes initiales sous `catalogue` restent une capture historique distincte. Les captures JSON R0/R1/R2 et les fixtures d'import restent inchangées. La revue indépendante de 19 tests en section 8 précède le naming ; elle n'est pas présentée comme une nouvelle revue après renommage.

### Deux commits cohérents, dans l'ordre demandé

1. `8f3e876` — `[DEV]INT-115 — Notes : adopter le nom de package catalog` : seulement la décision et les noms cibles dans le plan. L'application de ce commit reste celle de R2 ; aucun import n'y vise encore un package non livré.
2. Le commit `[DEV]INT-115 — Refactor : isoler le domaine catalog` contenant cette note : déplacement complet, imports, tests, suivi, todos et preuves après naming réunis.

La livraison n'insère pas son propre SHA dans ses fichiers : celui-ci dépendrait de leur contenu et serait autoréférentiel. Le commit de naming est référencé explicitement ; le commit R3 est celui qui contient la note et le manifeste finaux. Aucun push, déploiement, réécriture d'historique ni passage à R4.
