# INT-113 — R1 : socle modulaire, Base unique et composition explicite

> **Chantier :** [refactor monolithe modulaire](../../../docs/stages/stage7/refactor-monolithe-modulaire/README.md), avant Sprint 7.4.
> **Branche :** `refactor/modular-monolith`.
> **Baseline source :** `544a23d6cb2cbe878fbc8ddf2d962c7adf76c000`.
> **État :** R1 validé par l'utilisateur et committé localement (`73e5ac9`). R2 a reçu son feu vert distinct ; voir la [note INT-114](INT-114-R2-customers.md) pour sa livraison.

## 1. Ce que R1 livre — et ne livre pas

R1 introduit les points de composition qui permettront de déplacer un domaine à la fois. Les implémentations Client, Site, Product, Sale, Installation, Equipment, Intervention et Import restent encore dans les packages historiques.

La différence est structurelle :

```text
Avant                            Après R1
app/main.py → 15 routers         app/main.py → app/router.py → 15 routers legacy
app/models/base.py → Base        app/core/base.py → Base unique
app/models/__init__ → modèles    app/model_registry.py → chargement explicite
```

Les exports legacy restent disponibles pendant la transition, mais ils ne définissent pas de deuxième Base ou de deuxième classe ORM. Aucun bus, microservice, UnitOfWork, repository supplémentaire ou module futur n'est créé.

Arborescence nouvelle :

```text
backend/app/
├── core/
│   └── base.py
├── model_registry.py
├── router.py
└── modules/
    └── __init__.py
```

`app/modules/` est volontairement un package sans domaines anticipés. `customers/` sera créé seulement au feu vert R2.

## 2. Pourquoi isoler la Base de l'engine et des modèles ?

SQLAlchemy associe les classes héritant d'une `DeclarativeBase` à sa `MetaData` et à son registre de mappers.

Une seule Base signifie notamment :

- une même collection de tables pour Alembic ;
- un même registre pour résoudre les relations ORM déclarées par nom de classe ;
- pas de table dupliquée après réimport ;
- des FK inter-domaines toujours résolues dans une base commune.

La Base est désormais définie dans `backend/app/core/base.py` :

```python
"""Shared SQLAlchemy declarative base, without engine or domain imports."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Ce fichier n'importe ni `app.config`, ni les modèles, ni `app.core.database`, ni FastAPI. Dans un processus neuf :

```python
from app.core.base import Base

assert not Base.metadata.tables
assert not set(Base.registry.mappers)
```

Ce contrôle doit être fait avant d'importer les domaines : une suite déjà collectée aurait potentiellement rempli la metadata et masquerait la dépendance réelle.

`app/core/database.py` conserve ses responsabilités existantes : conversion d'URL, engine asynchrone, sessions et dépendance `get_db()`. La Base ne doit pas créer un engine uniquement parce qu'Alembic ou un outil veut inspecter les classes ORM.

## 3. Compatibilité transitoire, sans double implémentation

L'ancien `backend/app/models/base.py` est remplacé par un réexport :

```python
"""Legacy import path; all models share the Base defined in core."""

from app.core.base import Base  # noqa: F401
```

La compatibilité porte sur l'identité de l'objet, pas seulement sur son nom :

```python
from app.core.base import Base
from app.models import Base as package_base
from app.models.base import Base as legacy_base

assert package_base is legacy_base is Base
```

Les **13 fichiers de modèles** importent maintenant `Base` directement depuis `app.core.base`. Ils définissent les **17 classes mappées** actuelles : les ventes et le journal d'import contiennent plusieurs classes par fichier.

Leur contenu a été comparé à la source Git R0. Pour chacun :

```python
assert current_source == baseline_source.replace(
    "from app.models.base import Base",
    "from app.core.base import Base",
)
```

Ce contrôle établit que les déclarations métier, relations, index, enums, defaults Python et éventuelles déclarations de séquences n'ont pas été retouchées. Il complète le snapshot metadata, qui ne décrit pas exhaustivement toutes ces propriétés.

`app.models.__init__` garde temporairement ses exports historiques, avec la même Base technique. Importer ce package continue donc à charger les modèles legacy. Cette compatibilité ne doit pas être confondue avec la pureté de `core.base` ni utilisée comme remplacement du registre explicite.

Les fichiers de modèles seront supprimés après leur cutover respectif, pas pendant R1.

## 4. Un registre explicite, sans découverte automatique

`backend/app/model_registry.py` fournit une fonction `load_models()` :

```python
def load_models() -> None:
    """Register all current models on the shared Base, without creating an engine."""
    # Local imports keep importing this registry independent of loading domains.
    # Python's module cache makes repeated calls safe without a second registry.
    from app.models.checklist_item import ChecklistItem  # noqa: F401
    from app.models.client import Client  # noqa: F401
    from app.models.equipment import Equipment  # noqa: F401
    from app.models.import_batch import (  # noqa: F401
        ImportBatch,
        ImportError,
        ImportRecord,
        ImportReference,
    )
    # ... les autres modèles sont également importés explicitement dans le fichier.
```

L'extrait est abrégé ; le fichier livré liste tous les modèles :

| Périmètre | Modèles chargés |
|---|---|
| Identity | User |
| Customers | Client, Site |
| Catalogue | Product |
| Sales | Sale, SaleLine |
| Installations | Installation |
| Equipment | Equipment |
| Interventions | Intervention, ChecklistItem, InterventionPhoto, Material, Review |
| Imports | ImportBatch, ImportRecord, ImportReference, ImportError |

Importer le registre ne charge pas encore les modèles. **Appeler la fonction** les charge. Ce choix rend l'intention visible dans les points d'entrée et maintient l'import du registre indépendant du métier.

L'enregistrement ORM a lieu lorsque Python exécute les déclarations de classes. La fonction ne crée pas manuellement de Table, ne configure pas de plugin et ne crée aucune session. Des appels répétés réutilisent les modules déjà importés grâce au cache Python : les classes, tables et mappers gardent leur identité.

Ne pas utiliser `importlib.reload()` sur les modules qui définissent les classes ORM pour tenter de « recharger le registre » : cela réexécuterait les déclarations de tables. L'idempotence attendue est celle de `load_models()`.

## 5. Les trois points d'entrée chargent explicitement les modèles

### Application FastAPI

`app/main.py` conserve la configuration FastAPI, le lifespan, CORS et le montage des uploads. Avant d'inclure l'API :

```python
load_models()

from app.router import api_router

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
```

### Alembic

`alembic/env.py` ne dépend plus du chemin legacy de Base :

```python
from app.config import settings
from app.core.base import Base
from app.model_registry import load_models

load_models()
target_metadata = Base.metadata
```

L'ordre est essentiel : une Base importée seule a une metadata vide. Oublier l'appel pourrait laisser l'autogénération interpréter des tables SQL existantes comme des tables retirées du modèle.

### Seed

Le seed garde son emplacement et son comportement actuel. Sa seule adaptation fonctionnelle au bootstrap est :

```python
async def seed():
    load_models()
    # ── 0. Créer les tables si elles n'existent pas ──────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Le seed n'a pas été exécuté** : il contient un nettoyage de données et n'est pas requis pour prouver R1. Un test AST vérifie l'appel avant `create_all`, sans déclencher le nettoyage ni créer de connexion.

## 6. Composition des routes : mêmes contrats et même ordre

`app/router.py` agrège les 15 routeurs existants dans un `APIRouter` :

```python
api_router = APIRouter()
api_router.include_router(imports_router)
api_router.include_router(auth_router)
api_router.include_router(clients_router)
api_router.include_router(interventions_router)
# ... même ordre historique pour les autres routeurs.
api_router.include_router(sales_router)
```

L'ordre complet reste : imports, auth, clients, interventions, dashboard, checklist, photos, materials, reports, reviews, sites, products, equipment, installations, sales.

Le préfixe global est ajouté **une seule fois**, par `main`. Les préfixes propres aux domaines restent définis dans leurs routeurs. Les dépendances d'authentification, schémas Pydantic, codes de réponse et fonctions endpoints ne sont pas déplacés.

Aucun module n'est découvert par parcours du filesystem ou import dynamique. Chaque vague modifiera seulement les imports et inclusions correspondant au domaine déplacé.

Le snapshot public reste strictement identique à R0 : **46 chemins, 63 opérations**, mêmes schémas et identifiants d'opération. Cette égalité couvre aussi les payloads déclarés ; les tests API vérifient le comportement effectif.

## 7. Ce qui ne change pas dans le métier et les transactions

Les couches route → schéma → service → repository → ORM restent celles de la baseline. R1 ne modifie ni leurs règles ni leurs écritures.

En particulier :

- `InstallationService` conserve la clôture atomique Installation + Equipment ;
- les repositories ne reçoivent aucun nouveau commit ;
- les imports gardent leurs sous-lots transactionnels, leurs verrous et leur reprise ;
- la même `AsyncSession` reste partagée dans les workflows transverses ;
- ventes confirmées, quantité disponible, cohérence site/produit et parcours autonome ne sont pas réinterprétés ;
- aucun statut métier, rôle ou endpoint de Sprint 7.4 n'est ajouté.

Le registre n'est pas un gestionnaire de transactions : il enregistre les classes avant l'utilisation de la metadata. Il n'effectue aucun SQL.

## 8. Tests de bootstrap : éviter les faux positifs

Le nouveau fichier `backend/tests/test_modular_bootstrap.py` contient **14 cas pytest** :

| Scénario | Ce qu'il protège |
|---|---|
| Base pure en processus neuf | Aucun domaine, API ou engine chargé ; metadata vide |
| Import du registre sans appel | Pas de chargement anticipé des modèles |
| Chargement explicite complet | Les 17 tables et 17 mappers exacts de R0 |
| Registre sans initialisation legacy | Les imports du registre sont réellement exhaustifs |
| Appels répétés | Même metadata, mêmes Table et mêmes mappers |
| Compatibilité legacy | Identité de Base et des classes exportées |
| Ordres legacy-first / registry-first | Pas de dépendance à un ordre chanceux |
| Snapshot metadata | Colonnes/contraintes/FK identiques à R0 |
| Snapshot OpenAPI | Contrat public complet identique |
| Agrégation des routes | Mêmes endpoints, chemins, méthodes, noms et ordre |
| AST main / Alembic / seed | Appel explicite avant l'utilisation, non masqué par le legacy |

Les tests d'import s'exécutent dans des sous-processus, avec cwd et uploads temporaires, `PYTHONPATH` backend et timeout de 20 secondes. Des gardes interceptent les imports interdits, la création d'engine et les accès SQL selon le scénario.

### Pourquoi neutraliser le package legacy dans un test ?

Sans ce contrôle, le premier import d'un sous-module de `app.models` exécuterait son `__init__`, qui charge tous les modèles. Un import oublié dans le registre pourrait donc passer inaperçu.

Un test remplace temporairement ce package **dans son sous-processus uniquement** par un `ModuleType` possédant le bon `__path__`, mais sans son initialisation. Les vrais fichiers de modèles sont toujours importés. Le registre doit alors réussir seul à fournir les 17 tables et mappers.

La revue indépendante a identifié ce risque de faux positif ; le test a été ajouté avant la validation finale. Aucun monkeypatch de ce type n'est livré dans l'application.

Les tests AST sont des contrôles de structure source, pas une exécution des points d'entrée. Les migrations PostgreSQL et le démarrage Uvicorn sont validés séparément par de vraies exécutions.

## 9. PostgreSQL : aucune nouvelle différence Alembic

Un conteneur PostgreSQL **17.4** indépendant a été lancé depuis l'image locale avec `--pull never`, sans volume nommé et avec un port publié uniquement sur `127.0.0.1`. Le port attribué à ce run était `32769`.

Commandes exécutées par les sous-processus sur la base jetable :

```text
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini downgrade -1
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini check
```

Les trois premières réussissent. `alembic check` reste non nul pour la différence déjà connue :

```text
remove_fk : intervention.technician_id → user.id, sans ondelete
add_fk    : même relation, ondelete='SET NULL' selon l'ORM
```

Une comparaison supplémentaire `compare_metadata()` a vérifié **les opérations structurées**, pas seulement le texte des logs : exactement deux opérations, les mêmes colonnes et tables, `job_technician_id_fkey` pour la FK retirée, `None` puis `SET NULL` pour `ondelete`. Aucune opération supplémentaire de création/suppression de table ou modification de colonne n'a été détectée.

Les fichiers de révisions Alembic ont également été comparés au SHA R0 : ils sont inchangés. **Aucune migration SQL n'a été générée.**

La chaîne complète SQLite reste incompatible avec une ancienne instruction PostgreSQL `ALTER TYPE`, comme observé en R0. Elle n'a pas été corrigée ni relancée pour R1 : la chaîne complète est validée ici sur PostgreSQL.

## 10. Commandes et résultats réellement observés

Les exécutions utilisent l'interpréteur déjà installé `backend/.venv/bin/python`. Aucun ajout de dépendance, `uv sync` ou build d'image applicative n'a été effectué.

| Validation | Résultat observé |
|---|---|
| Ciblé : `python -m pytest tests/test_modular_bootstrap.py -q -p no:cacheprovider` | **14 passed**, 11,77 s avant le seul nettoyage d'import/noqa |
| Suite complète isolée : `python -m pytest <backend>/tests -q -p no:cacheprovider` | **285 passed**, 5 warnings, 52,82 s |
| PostgreSQL : installations, ventes, migration installation | **56 passed**, 1 warning, 24,91 s |
| PostgreSQL : service import et API admin | **39 passed**, 1 warning, 27,29 s |
| Aller-retour dernière révision PostgreSQL | Réussite |
| Comparaison autogenerate structurée | Seulement les deux opérations FK connues de R0 |
| Source ORM et migrations | 13 fichiers ORM : seul import de Base changé ; révisions inchangées |
| Snapshots OpenAPI / metadata | Égalité complète à R0 |
| Uvicorn réel, `/openapi.json` et `/docs` | HTTP 200 ; startup et shutdown ASGI complets |

La suite contient les **271 tests existants + 14 nouveaux cas**. Les 95 cas PostgreSQL sont des réexécutions ciblées de la suite, pas 95 tests supplémentaires.

L'environnement local est celui de R0 : Python **3.12.0** et PostgreSQL **17.4**. Ces commandes ne sont pas un run GitHub Actions sur Python 3.11. Aucune CI distante ni aucun déploiement n'est annoncé comme validé.

Les warnings de suite restent ceux de passlib (`crypt`) et du service Intervention (`datetime.utcnow()`). Le contrôle de diagnostics de l'éditeur signale aussi des erreurs de typage dans des fichiers historiques non refondus ; il ne faut pas confondre les tests verts avec une certification « zéro diagnostic » du dépôt.

### Arrêt Uvicorn : distinguer signal et erreur applicative

Le premier script HTTP a exigé à tort un code de sortie `0` après `proc.terminate()`. Les requêtes HTTP et le shutdown avaient réussi, mais le processus a renvoyé **`-15`**, soit `SIGTERM` sur Linux.

Le contrôle a été rejoué avec logs capturés et une assertion adaptée : accepter `0` ou `-SIGTERM`, tout en exigeant les messages `Application startup complete` et `Application shutdown complete`. Ce second contrôle a réussi et le processus a été attendu puis nettoyé. Aucune modification du lifespan n'a été nécessaire.

## 11. Preuves conservées après R1

Les preuves sont distinctes des fichiers R0 :

| Artefact | Contenu |
|---|---|
| [R1-openapi.json](R1-openapi.json) | OpenAPI après composition, égale à R0 |
| [R1-metadata.json](R1-metadata.json) | Metadata après changement d'import, égale à R0 |
| [R1-postgresql-results.json](R1-postgresql-results.json) | Commandes, codes de retour, logs, opérations autogenerate normalisées et tests PostgreSQL |
| [R1-sqlite-results.json](R1-sqlite-results.json) | Sortie de la suite finale de 285 tests |
| [R1-source-invariants.json](R1-source-invariants.json) | Comparaison des déclarations ORM et révisions à la source R0 |
| [R1-runtime-results.json](R1-runtime-results.json) | Contrôles HTTP et log complet du startup/shutdown |
| [R1-validation.json](R1-validation.json) | Synthèse et empreintes des preuves/source de R1 |

Les JSON R0 et les fichiers du pack Excel restent intacts. La note R0 et le planning enregistrent seulement la décision utilisateur ultérieure et la création de branche, sans remplacer les captures historiques.

Les ressources jetables ont été supprimées ; aucun conteneur de vérification ou processus Uvicorn n'est laissé actif. Les bases locales, la base déployée, les images backend/frontend et les conteneurs existants n'ont pas été migrés ni redémarrés.

## 12. Suite autorisée et limites

- R1 est livré localement ; les critères INT-113 sont cochés et les neuf scénarios documentaires associés sont renseignés avec leurs preuves.
- Après validation utilisateur, R0 et R1 ont été committés localement (`6754a50` et `73e5ac9`) ; R2 a reçu son feu vert distinct. La [note INT-114](INT-114-R2-customers.md) décrit le déplacement Client/Site maintenant livré, sans réécrire les résultats capturés pour R1.
- Aucun todo métier n'est débloqué par ce seul squelette. TD-B013 (rôles), TD-B016 (volume d'import) et TD-F007 (frontend) restent distincts.
- La FK technicien reste explicitement hors correction du refactor.
- Le seed n'est pas exécuté et son contenu métier n'est pas réécrit.
- La comparaison complète des résultats du pack Excel avant/après sera réalisée dans R9, au-delà des empreintes et tests déjà conservés.
- Aucun commit au moment de la capture des preuves R1 ; les deux commits locaux ont été créés ensuite après accord utilisateur. Aucun push, tag ou réécriture d'historique.
