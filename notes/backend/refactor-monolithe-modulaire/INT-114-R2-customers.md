# INT-114 — R2 : extraction du domaine customers

> **Planning :** [refactor monolithe modulaire](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md).
> **Branche :** `refactor/modular-monolith`.
> **Parent R1 :** `73e5ac9bed65112f0ca181cd1af3fcd6ece8ae4e`.
> **État :** R2 accepté par l'utilisateur et committé localement sous `ed67168`. R3 a reçu son feu vert distinct ; voir la [note INT-115](INT-115-R3-catalogue.md). Les JSON R2 décrivent leur capture avant commit et restent inchangés.

## 1. Checkpoint Git avant le déplacement

L'utilisateur a demandé de figer R0/R1 avant de commencer R2. Deux commits **locaux**, sans push ni réécriture, ont donc été créés :

| Commit | Contenu |
|---|---|
| `6754a50` — `[DOC] Refactor — Plan et baseline R0` | Plan fourni, note et captures avant changement de code |
| `73e5ac9` — `[DEV]INT-113 — Refactor : introduire le socle modulaire` | Base unique, registre, composition, tests, planning et preuves R1 |

Les sources et artefacts R1 ont été comparés à leurs SHA-256 avant commit. L'arbre de travail était propre au démarrage de R2.

Le contrôle du premier contenu staged a signalé les doubles espaces de fin de ligne du plan fourni. Ce sont les sauts de ligne Markdown intentionnels : ils ont été conservés. Le contrôle R0 adapté utilisait `git -c core.whitespace=-blank-at-eol diff --cached --check`. Le contrôle standard du contenu staged R1 a réussi. Cette distinction évite d'annoncer à tort que le fichier non suivi avait été vérifié par les contrôles antérieurs.

Les mentions « non committé » dans les manifests R0/R1 décrivent leur capture initiale. Ces preuves historiques n'ont pas été réécrites pour ajouter les SHA des commits ultérieurs.

## 2. Pourquoi Client et Site appartiennent au même module

Le domaine customers porte la racine de la chaîne physique :

```text
Client → Site → Equipment → Intervention
```

`Client` décrit le propriétaire/contact ; `Site` décrit l'emplacement physique. La relation Client 1 → N Site ne doit pas être remplacée par un client par adresse ou par un équipement directement attaché au client.

R2 rassemble ces deux entités et leurs couches sans ajouter une nouvelle fonctionnalité. Le regroupement prépare les déplacements aval, tout en conservant :

- les identifiants entiers et les noms SQL `client` / `site` ;
- les mêmes schémas Pydantic ;
- la pagination, la recherche et les réponses d'erreur existantes ;
- l'historique et les relations avec Equipment, Installation, Sale et Intervention ;
- les responsabilités actuelles des transactions.

## 3. Dix fichiers sources deviennent cinq fichiers métier

```text
backend/app/modules/customers/
├── __init__.py       # docstring seulement
├── models.py         # Client + Site
├── schemas.py        # contrats Client/Site
├── repository.py     # ClientRepository + SiteRepository
├── service.py        # ClientService + SiteService
└── api.py            # clients_router + sites_router
```

| Couche | Anciennes sources supprimées | Nouveau fichier |
|---|---|---|
| ORM | `app/models/client.py`, `site.py` | `customers/models.py` |
| Contrats | `app/schemas/client.py`, `site.py` | `customers/schemas.py` |
| Accès SQL | `app/repositories/client.py`, `site.py` | `customers/repository.py` |
| Règles métier | `app/services/client.py`, `site.py` | `customers/service.py` |
| HTTP | `app/api/v1/clients.py`, `sites.py` | `customers/api.py` |

Les dix anciens fichiers sont supprimés, pas transformés en wrappers de compatibilité. Les consommateurs applicatifs, imports Excel et tests importent maintenant les nouvelles classes directement.

Une seule implémentation active existe pour chaque classe. Le package `app.models` conserve uniquement ses exports transitoires de `Client` et `Site`, vers ces mêmes objets, pour les appelants legacy du registre global. Cette compatibilité sera retirée avec la structure horizontale en R11.

Le `__init__.py` de customers ne réexporte ni API, ni service, ni repository : importer un modèle ne doit pas charger FastAPI ou un engine.

## 4. ORM : déplacer les classes ne déplace pas les tables

Le modèle Client garde la même définition, notamment :

```python
class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=False, index=True)
```

Le modèle Site garde sa vraie FK et ses relations aval :

```python
client_id = Column(
    Integer, ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True
)

# Relations conservées dans Site
client = relationship("Client", backref="sites")
equipment = relationship("Equipment", back_populates="site", passive_deletes="all")
installations = relationship("Installation", back_populates="site", passive_deletes="all")
```

`Base` vient toujours de `app.core.base`. Les relations vers les domaines encore legacy sont déclarées par noms de classes ; `customers.models` ne les importe pas pour résoudre les relations au chargement de son fichier.

Dans un processus neuf, l'import de `customers.models` enregistre seulement `client` et `site`. Celui de `customers.schemas` n'enregistre aucune table. Les relations aval sont ensuite résolues après le chargement du registre complet.

Le registre est adapté explicitement :

```python
from app.modules.customers.models import Client, Site  # noqa: F401
```

Cet import se trouve dans `load_models()`, avec les modèles legacy restants. Le registre final compte toujours **17 tables et 17 mappers**. La réimportation ne crée pas de seconde classe Client ou Site.

## 5. Schémas et contrats publics : aucun nouveau champ

Les classes Pydantic conservent leurs noms, validations et configurations. Exemple du contrat existant :

```python
class SiteCreate(BaseModel):
    client_id: int
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=500)
```

Un corps de création valide reste donc :

```json
{
  "client_id": 1,
  "name": "Domicile",
  "address": "12 rue Exemple",
  "city": "Paris"
}
```

Les schémas de réponse utilisent toujours `model_config = {"from_attributes": True}`. Les services produisent les mêmes réponses via `model_validate()` ; le regroupement des fichiers ne transforme pas les classes ORM en contrats HTTP.

Leur `__module__` Python change, mais les noms des composants OpenAPI et leurs références restent identiques. Ce point a été vérifié par égalité du document **complet**, et non déduit des seuls comptes de routes.

## 6. Repository, service et transactions : aucune réécriture cachée

Les repositories conservent leurs requêtes, tris et commits. Par exemple :

```python
async def create(self, data: dict) -> Client:
    client = Client(**data)
    self.db.add(client)
    await self.db.commit()
    await self.db.refresh(client)
    return client
```

Le service conserve la validation et la construction de la réponse :

```python
async def create_client(self, data: ClientCreate) -> ClientResponse:
    client = await self.repo.create(data.model_dump())
    return ClientResponse.model_validate(client)
```

Le service Site vérifie toujours l'existence du client avant sa création. Les limites de pagination restent celles de R1, et les mises à jour continuent à filtrer les valeurs `None` selon le comportement actuel. Le refactor ne change pas ces choix, même si une autre conception pourrait être discutée ultérieurement.

R2 n'ajoute pas de transaction extérieure, de rollback généralisé ou de UnitOfWork. Les commits CRUD Client/Site restent dans leurs repositories. Les services Installation et Import conservent leurs propres mécanismes transactionnels ; seuls leurs imports de Client/Site ou des schémas changent.

### Protection des historiques

Le refus de supprimer un site lié à une installation reste identique :

```python
if await self.db.scalar(
    select(Installation.id).where(Installation.site_id == site_id).limit(1)
):
    raise HTTPException(409, "Ce site possède des installations : conserver leur historique")
```

Le service Client effectue la même protection via la jointure aux sites. Les refus liés aux équipements restent également en place.

Le nouveau test crée une installation **sans équipement**, tente les deux suppressions et vérifie :

- réponse `409` pour le site ;
- réponse `409` pour son client ;
- Client, Site et Installation toujours présents ;
- suppression possible d'un autre site sans ces dépendances ;
- réponse de l'installation inchangée après les refus.

Aucun commit de suppression n'est atteint dans ces branches de refus.

## 7. Dépendances transverses conservées, pas masquées

Le domaine customers n'est pas rendu artificiellement indépendant de tout le backend : il possède déjà des lectures/protections historiques transverses.

Les statistiques Client restent calculées via les sites :

```python
stats_query = (
    select(func.count(Intervention.id), func.max(Intervention.created_at))
    .join(Site, Intervention.site_id == Site.id)
    .where(Site.client_id == client_id)
)
```

Les routes `/sites/{id}/interventions` et `/sites/{id}/equipment` continuent à appeler les services aval actuels. Une nouvelle façade locale aurait changé le chemin d'appel sans bénéfice nécessaire au déplacement : elle n'a pas été introduite.

R2 adapte les consommateurs dans :

- le registre et les exports legacy ;
- `InterventionRepository` et `InterventionService` ;
- `EquipmentService` et `SaleService` ;
- `ImportPlanner`, `ImportService` et le seed ;
- les fixtures et scénarios de tests existants.

Les imports Excel utilisent les mêmes classes Client/Site et les mêmes validations de schémas ; la normalisation, les arbitrages, la provenance, les transactions et les sources du pack ne changent pas.

## 8. Deux routeurs locaux pour préserver l'ordre global

`customers/api.py` expose :

```python
clients_router = APIRouter(prefix="/clients", tags=["clients"])
sites_router = APIRouter(prefix="/sites", tags=["sites"])
```

La composition globale importe ces deux objets depuis le même module. Elle les inclut aux positions historiques : clients avant interventions, sites après reviews. Le préfixe global `/api/v1` reste appliqué une fois par `main`.

Un routeur customers agrégateur unique aurait placé toutes les routes sites immédiatement à côté des clients, modifiant inutilement l'ordre global. La frontière métier n'impose pas un seul objet APIRouter : conserver deux exports explicites est plus précis pour ce déplacement.

| Méthode | Chemin sous `/api/v1` | Contrat conservé |
|---|---|---|
| GET / POST | `/clients` | Liste paginée/recherche ; création 201 |
| GET / PUT / DELETE | `/clients/{client_id}` | Détail/statistiques ; modification ; suppression 204 |
| GET | `/clients/{client_id}/sites` | Liste des sites ; client inconnu 404 |
| GET / POST | `/sites` | Liste filtrée par client ; création 201 |
| GET / PATCH / DELETE | `/sites/{site_id}` | Lecture ; modification partielle ; suppression 204 |
| GET | `/sites/{site_id}/interventions` | Historique paginé ; site inconnu 404 |
| GET | `/sites/{site_id}/equipment` | Équipements du site ; site inconnu 404 |

Cela représente **13 opérations customers** parmi les **63 opérations globales**. Les dépendances `get_current_user` et `get_db`, les fonctions endpoints et les noms d'opérations restent inchangés.

## 9. Preuve structurelle : comparaison des définitions

Les définitions de premier niveau des dix anciens fichiers ont été lues dans le commit R1. Elles ont été comparées aux définitions consolidées par `ast.dump(..., include_attributes=False)`.

Résultat : **28 définitions identiques**, méthodes incluses. Pour les fonctions API, la comparaison ne normalise que le nom de la variable ciblée par les décorateurs : `router` devient `clients_router` ou `sites_router`.

Ce contrôle couvre les déclarations de colonnes, index, enums/defaults éventuels, méthodes, signatures, validations, branches, messages d'erreur et commits. Les docstrings de module et les imports, nécessairement regroupés, ne sont pas dans cette comparaison des définitions.

Les fichiers de révisions Alembic sont également inchangés par rapport au parent R1. Aucun déplacement Python ne justifie ici une migration SQL.

## 10. Tests : nouveau module et parcours conservés

`tests/test_customers_module.py` ajoute **7 cas pytest** :

- structure du package, pureté du `__init__`, suppression des anciens chemins et scan AST des imports dans `app`/`tests` ;
- imports purs de `models` et `schemas` — deux cas ;
- ordres customers-first et legacy-first — deux cas, avec identité des objets, configuration des 17 mappers, résolution des FK et relations ;
- refus de suppression avec installation autonome et conservation des données ;
- statistiques multi-sites et routes historiques interventions/equipment, incluant les sites vides et inconnus.

Le test de statistiques crée trois interventions chez le client suivi et une chez un autre client. La réponse doit compter **3**, pas 4, et retenir la dernière date pertinente. L'historique d'un site ne retourne que les interventions de ce site ; la liste d'équipements retrouve le matériel créé sur ce même site.

Les deux tests API réutilisent la fixture isolée d'INT-103, avec vrai JWT et base temporaire. Leur variante PostgreSQL est volontairement désactivée : **ces deux nouveaux scénarios ont été exécutés sur SQLite**, pas présentés comme des tests PostgreSQL.

Les tests de bootstrap R1 sont conservés, avec adaptation du routeur témoin aux nouveaux exports customers. Ils vérifient toujours l'OpenAPI et la metadata R0, ainsi que le registre sans l'initialisation legacy qui pourrait masquer un import manquant.

Un premier essai parallèle pendant la bascule a échoué parce que les anciens fichiers et imports étaient encore présents. Il n'a pas donné lieu à un contournement : les classes dupliquées et références périmées ont disparu une fois le cutover achevé. Tous les résultats annoncés ci-dessous viennent des exécutions **après** ce cutover.

## 11. Résultats réellement observés

| Vérification | Résultat |
|---|---|
| Bootstrap + customers + clients + sites | **43 passed**, 1 warning, 19,13 s |
| Suite backend complète SQLite isolée | **292 passed**, 5 warnings, 68,94 s |
| PostgreSQL 17.4 : ventes/installations/migrations | **56 passed**, 1 warning, 34,34 s |
| PostgreSQL 17.4 : service import et API admin | **39 passed**, 1 warning, 29,27 s |
| Migrations PostgreSQL `upgrade head → downgrade -1 → upgrade head` | Réussite |
| `alembic check` + opérations autogenerate structurées | Seulement les deux opérations FK connues de R0/R1 |
| OpenAPI complète R2 / R0 / R1 | Égales : 46 chemins, 63 opérations |
| Metadata complète R2 / R0 / R1 | Égales : 17 tables |
| Démarrage/arrêt Uvicorn réels | Startup et shutdown ASGI complets |
| HTTP `/docs` et `/openapi.json` | 200 ; OpenAPI servie égale aux snapshots |
| Recherche des anciennes références dans le backend | Aucune référence active aux dix modules supprimés |

La suite compte **285 tests R1 + 7 nouveaux cas R2**. Les groupes PostgreSQL sont des réexécutions ciblées, pas des tests supplémentaires à ajouter au compte de 292.

Les commandes ont utilisé l'interpréteur installé `backend/.venv/bin/python`, avec cwd SQLite/uploads temporaires, `PYTHONPATH` pointant sur le backend source et `-p no:cacheprovider`. Exécutions applicatives :

```text
python -m pytest tests/test_modular_bootstrap.py tests/test_customers_module.py tests/test_clients.py tests/test_sites.py -q -p no:cacheprovider
python -m pytest <backend>/tests -q -p no:cacheprovider
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini downgrade -1
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini check
python -m pytest tests/test_installations.py tests/test_sales.py tests/test_installation_migration.py -q -p no:cacheprovider
python -m pytest tests/test_import_service_v2.py tests/test_import_api_v2.py -q -p no:cacheprovider
```

Les chemins des tests/config étaient absolus dans les sous-processus lancés depuis les répertoires temporaires. Les groupes PostgreSQL ont reçu leurs variables `TERVO_*` habituelles, vers une instance **17.4** jetable dédiée. Son port local était `32770` ; l'image existante a été utilisée avec `--pull never`, sans volume nommé.

### Interprétation d'Alembic

`alembic check` reste non nul : la FK SQL historique `job_technician_id_fkey` ne possède pas le `ON DELETE SET NULL` déclaré par l'ORM. La comparaison structurée retourne exactement le même `remove_fk` / `add_fk` que R1, sans nouvelle modification de table, colonne ou contrainte.

Il serait incorrect de dire « Alembic entièrement sans diff ». La preuve R2 est **aucune nouvelle différence par rapport à la baseline** ; aucune correction de FK ni migration générée.

## 12. Preuves et limites

Les preuves R2 sont conservées séparément dans ce dossier :

- `R2-targeted-results.json` et `R2-sqlite-results.json` ;
- `R2-postgresql-results.json`, avec opérations normalisées ;
- `R2-openapi.json` et `R2-metadata.json` ;
- `R2-runtime-results.json`, avec log startup/shutdown et arrêt par SIGTERM ;
- `R2-source-invariants.json`, avec correspondance des 28 définitions ;
- `R2-validation.json`, avec synthèse et empreintes.

Les captures R0/R1 et les empreintes du pack Excel restent intactes. Le conteneur PostgreSQL et Uvicorn ont été arrêtés et nettoyés. Aucune base locale ou déployée n'a été migrée ; aucun service existant n'a été redémarré.

Limites explicites :

- validation locale sur Python **3.12.0**, pas un run CI distant sur Python 3.11 ;
- aucun build frontend, E2E navigateur, déploiement ou push ;
- seed adapté par ses imports mais **non exécuté**, pour ne pas déclencher son nettoyage ;
- warnings hérités sur `Depends`, imports inutilisés et pagination conservés, sans simplifier le métier pour satisfaire le linter ;
- ancienne chaîne Alembic SQLite incompatible avec `ALTER TYPE` inchangée ;
- mesure d'import représentatif TD-B016, nouveaux rôles TD-B013 et frontend TD-F007 toujours hors périmètre ; aucun todo métier débloqué par ce move ;
- comparaison complète des journaux d'import avant/après réservée à R9 ;
- R2 n'était pas committé lors de la capture des preuves JSON. L'utilisateur a ensuite validé sa clôture et demandé le commit INT-114, puis autorisé R3 / INT-115 séparément. Les captures historiques restent intactes.

### Vérification avant commit après validation utilisateur

Les empreintes SHA-256 des sources et des sept artefacts référencés dans `R2-validation.json` ont été revérifiées : elles correspondent à la livraison validée. Dans le worktree Delta neuf, `uv sync --frozen` a recréé le venv à partir du lockfile inchangé (Python 3.12.0). La suite ciblée bootstrap/customers/clients/sites a été réexécutée depuis un répertoire temporaire : **43 passed, 1 warning, 21,29 s**. `git diff --check` ne signale aucune erreur. Les résultats PostgreSQL ci-dessus restent ceux de la capture R2 ; ils n'ont pas été réexécutés pour ce commit. Aucun push ni déploiement.
