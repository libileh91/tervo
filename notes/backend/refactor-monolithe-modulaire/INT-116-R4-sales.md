# INT-116 — R4 : extraction du domaine sales et provenance commerciale

> **Planning :** [refactor monolithe modulaire](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md#L109).
> **Parent R3 :** `29f034e4597a33c65fcbf9a4afe15440a1a1e18e`, branche `refactor/modular-monolith`.
> **État :** R4 accepté et committé sous `93be411` dans le checkout principal, puis worktree agent aligné par fast-forward. R5 a reçu son feu vert distinct ; voir la [note INT-117](INT-117-R5-equipment.md). Le manifeste JSON conserve sa capture avant acceptation.
> **Preuve :** [R4-validation.json](R4-validation.json), avec résultats observés et empreintes des sources.

## 1. Reprise : R3 livré, checkout principal et stash R2

R3 est accepté et committé sous `29f034e`, après le choix documentaire de naming `8f3e876`. `app/modules` est conservé et la référence produit appartient à `catalog`.

Le checkout principal `/home/lob/workspace/python/fastapi/Tervo` avait été synchronisé avec les commits R2/R3. Son stash R2 n'était pas du travail à committer, mais la sauvegarde d'une ancienne copie de changements déjà intégrés. Sur demande explicite, l'entrée identifiée `9445318` et sa référence dédiée de sauvegarde ont été supprimées ; la branche de secours R1 et les copies des anciens fichiers non suivis restent conservées. Aucun `stash pop` ni nettoyage récursif n'est exécuté pour R4.

Le feu vert utilisateur porte sur **R4 uniquement**. Les changements sont présents dans le worktree agent **et** dans le checkout principal, avec comparaison des contenus avant transfert pour détecter des modifications concurrentes. Les tests et le runtime décrits ici ont été exécutés sur le backend du **checkout principal**, depuis des répertoires de travail temporaires. Les fichiers SQLite existants n'ont pas servi aux tests.

R4 n'était pas committé lors de la capture des preuves ; l'utilisateur a ensuite accepté la livraison et demandé son commit dans le checkout principal, puis autorisé R5 distinctement. Les captures JSON historiques ne sont pas réécrites.

Le commit `93be411` a ensuite été créé après contrôle des 13 empreintes sources/tests et réexécution bootstrap/sales/module : **33 passed, 1 warning, 16,52 s**. Les développements, tests, note et suivi R4 y sont regroupés ; aucun fichier R5 inclus. Ce contrôle avant commit ne remplace pas les validations complètes capturées plus bas.

## 2. Une extraction verticale sans repository inventé

```text
app/modules/sales/
├── __init__.py
├── models.py
├── schemas.py
├── service.py
└── api.py
```

| Source précédente sous `backend/app/` | Propriétaire actuel |
|---|---|
| `models/sale.py` | `modules/sales/models.py` |
| `schemas/sale.py` | `modules/sales/schemas.py` |
| `services/sale.py` | `modules/sales/service.py` |
| `api/v1/sales.py` | `modules/sales/api.py` |

Les quatre sources précédentes sont retirées. `__init__.py` ne contient qu'une docstring : aucun import implicite de service, router, engine ou registre global.

Le service ventes réalisait déjà ses requêtes SQL et possédait ses commits. Ajouter un repository uniquement pour ressembler à customers ou catalog augmenterait le périmètre sans apporter de responsabilité nouvelle. Le module reprend donc le découpage **réel**, pas une symétrie artificielle.

| Couche | Responsabilité conservée |
|---|---|
| API | Auth, injection de session, routage, statuts et réponse |
| Schémas | Validation des corps, Decimal et sérialisation ORM |
| Service | Références commerciales, création et transitions, requêtes et commit |
| ORM | Tables, contraintes, valeurs par défaut et relations |

## 3. Sale, SaleLine et Installation sont trois concepts distincts

Une vente désigne l'événement commercial ; une ligne précise le produit, la quantité et le prix contractuel. Une installation désigne une unité de travail terrain.

```text
Client ──► Site
  └────────► Sale ──► SaleLine ──► Installation ──► Equipment
                         │
                         └──► Product
```

Une ligne de quantité 3 ne devient ni trois lignes de vente, ni un stock. Elle autorise jusqu'à trois installations non annulées, selon la règle existante d'InstallationService. L'équipement installé reste un objet distinct de Product.

### Identité et contraintes SQL

Le [modèle déplacé](../../../backend/app/modules/sales/models.py#L15) conserve la Base technique unique, les noms `sale`/`sale_line` et les IDs entiers :

```python
client_id = Column(Integer, ForeignKey("client.id", ondelete="RESTRICT"), nullable=False, index=True)
site_id = Column(Integer, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False, index=True)
```

`RESTRICT` protège la provenance client/site contre une suppression qui casserait les ventes historiques. Le lien de ligne vers le produit garde également `RESTRICT`.

```python
__table_args__ = (
    CheckConstraint("quantity > 0", name="ck_sale_line_quantity_positive"),
    CheckConstraint("unit_price >= 0", name="ck_sale_line_price_nonnegative"),
)
```

Les validations API ne remplacent pas ces contraintes SQL : les écritures hors API sont soumises aux mêmes règles. `unit_price` reste `Numeric(12, 2)`, pas un Float.

### Relations conservées

- Sale → Client et Site, avec les backrefs `sales` existantes ;
- Sale → SaleLine, tri par ID et cascade ORM `all, delete-orphan` ;
- SaleLine → Sale, Product et installations ;
- Installation → SaleLine, nullable pour le parcours autonome et les historiques.

La FK `sale_line.sale_id` garde `ON DELETE CASCADE`. La collection `SaleLine.installations` garde `passive_deletes="all"` : R4 ne réécrit pas la politique de suppression des historiques et n'ajoute pas de nouvelle cascade.

Le réexport temporaire `app.models.Sale/SaleLine/SaleStatus` renvoie les **mêmes objets** que `app.modules.sales.models`, pas des wrappers. Le registre charge explicitement les deux modèles déplacés. Il n'y a toujours que **17 tables et 17 mappers**.

## 4. Statuts et transitions : préserver la machine existante

```python
class SaleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
```

Le mapping SQL conserve l'enum non natif et sa contrainte `sale_status`, avec le défaut `DRAFT` côté ORM et SQL. Aucun statut de devis, paiement ou facturation n'est introduit.

| Action | État d'entrée | Condition | Résultat |
|---|---|---|---|
| Créer | Nouvelle vente | Références cohérentes | DRAFT |
| Confirmer | DRAFT | Au moins une ligne | CONFIRMED |
| Annuler | DRAFT | Aucune condition de ligne supplémentaire | CANCELLED |
| Confirmer une vente vide | DRAFT | Absence de ligne | 409 |
| Confirmer/annuler une vente non brouillon | CONFIRMED ou CANCELLED | État final existant | 409 |

Extrait du [service déplacé](../../../backend/app/modules/sales/service.py#L43) :

```python
if sale.status != SaleStatus.DRAFT:
    raise HTTPException(409, "Seule une vente brouillon peut changer de statut")
if target == SaleStatus.CONFIRMED and not sale.lines:
    raise HTTPException(409, "Une vente confirmée doit contenir au moins une ligne")
sale.status = target
await self.db.commit()
return await self.get(sale_id)
```

Ce code lit puis modifie l'état ; R4 n'ajoute pas un `UPDATE` conditionnel ni une règle de concurrence nouvelle. Les garde-fous de clôture atomique d'installation ne sont pas transposés artificiellement à SaleService.

## 5. Contrats API : trois routes, pas un CRUD supplémentaire

Préfixe effectif `/api/v1/sales`, tag `sales`, position du router conservée en fin de composition.

| Route | Succès | Accès actuel |
|---|---|---|
| `POST /sales` | 201, SaleResponse | Utilisateur authentifié |
| `POST /sales/{sale_id}/confirm` | 200, SaleResponse | Utilisateur authentifié |
| `POST /sales/{sale_id}/cancel` | 200, SaleResponse | Utilisateur authentifié |

**Il n'y a pas de GET détail/list ni de DELETE ventes.** `SaleService.get()` est une lecture interne utilisée après les écritures et dans les tests, pas un endpoint public.

Les trois routes utilisent `get_current_user` et `get_db`. Contrairement aux écritures catalog, elles ne sont pas ADMIN-only. Le refactor conserve cette auth existante ; aucun nouveau rôle ni contrôle MANAGER/COMMERCIAL n'est ajouté. Les nouveaux tests utilisent de vrais JWT ADMIN et TECHNICIAN : création/confirmation/provenance sous TECHNICIAN et annulation paramétrée sous les deux rôles. Ils verrouillent le contrat non-ADMIN en complément de l'égalité AST de l'API.

Exemple de création :

```json
{
  "client_id": 1,
  "site_id": 2,
  "sale_date": "2026-10-01",
  "notes": "Provenance R4",
  "lines": [
    {
      "product_id": 3,
      "quantity": 3,
      "unit_price": "1250.50",
      "description": "Prix contractuel"
    }
  ]
}
```

Les identifiants doivent être positifs. `lines` vaut une liste vide par défaut : la création d'un brouillon vide est autorisée, sa confirmation ne l'est pas. `extra="forbid"` interdit les champs non prévus.

### Decimal de bout en bout

```python
quantity: int = Field(gt=0)
unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
```

Le schéma valide la valeur avant le service ; l'ORM conserve `Numeric(12, 2)` et le prix est relu comme `Decimal("1250.50")`. Il n'existe ni multiplication implicite de total, ni conversion en float, ni enrichissement d'un prix catalogue.

Les tests refusent quantité 0/-1, prix négatif et précision excessive (`"1250.501"`) avec **422**, puis relisent les comptes Sale/SaleLine : aucune ligne ou vente invalide n'a été écrite.

Importer les schémas importe l'enum local SaleStatus et donc les déclarations des deux tables. Le test de pureté attend **sale et sale_line**, pas zéro table ; il interdit toutefois les modules web, l'engine et le package global legacy.

## 6. Service et transactions : aucune frontière déplacée

La route transmet le corps validé à une instance de service utilisant la session injectée. La création conserve cet ordre :

1. Lire Client : **404** si absent.
2. Lire Site : **404** si absent ; **422** s'il appartient à un autre client.
3. Lire chaque Product : **404** si absent.
4. Construire Sale et ses SaleLine.
5. Ajouter à la session, commit, puis relire avec les lignes chargées.

```python
sale = Sale(client_id=data.client_id, site_id=data.site_id, sale_date=data.sale_date, notes=data.notes)
sale.lines = [SaleLine(**line.model_dump()) for line in data.lines]
self.db.add(sale)
await self.db.commit()
return await self.get(sale.id)
```

Les contrôles de références sont **avant** la construction/persistance. Les nouveaux tests client inconnu, site inconnu, produit inconnu et site d'un autre client vérifient les messages exacts et l'absence de nouvelles écritures.

Product est lu depuis `catalog` ; les produits inactifs restent acceptés par la vente, comme avant R4. Le test historique de désactivation catalog reste exécuté et ses imports Sale/SaleLine sont simplement adaptés.

### Chargement explicite, pas de lazy loading async pendant la réponse

```python
sale = await self.db.scalar(
    select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.lines))
)
```

La réponse a besoin des lignes. `selectinload` les charge explicitement pour éviter de déclencher une lecture async implicite au moment où Pydantic sérialise l'objet.

Le service conserve ses deux points de commit (create et transition), sans repository et sans nouvelle session. **Il ne possède pas de bloc explicite de rollback/conversion d'IntegrityError**, contrairement à d'autres domaines : R4 n'en invente pas et ne prétend pas tester un rollback métier ajouté. Aucun UnitOfWork, event bus ou nettoyage de requêtes n'est inclus.

## 7. Consommateur aval : la capacité reste dans InstallationService

InstallationService importe désormais `SaleLine` et `SaleStatus` depuis le module sales. Son code métier ne change pas :

```python
line = await self.db.scalar(select(SaleLine).where(SaleLine.id == sale_line_id)
    .options(selectinload(SaleLine.sale)).with_for_update())
```

Il vérifie la ligne, la vente confirmée, le site et le nombre d'installations non annulées. Le verrou PostgreSQL sur la ligne, la limite de quantité et les règles de produit à la clôture sont conservés. Le simple changement d'import ne crée ni commit intermédiaire ni session distincte.

Le test existant de quantité 3 est rejoué : une seule ligne, trois installations, clôture de l'une avec équipement cohérent, puis quatrième installation refusée avec **409**. R4 ne le copie pas dans un nouveau test.

Le nouveau scénario complète cette preuve : après un rejet **422** d'installation sur un autre site, une nouvelle session traverse les liens Sale → Client/Site/Line → Product/Installation, vérifie le prix exact et les IDs préservés. Il utilise `selectinload` pour lire ces relations et constate une seule installation, sans donnée issue du refus.

## 8. Tests de frontière et preuve source

`tests/test_sales_module.py` ajoute **16 cas collectables** :

| Groupe | Nombre | Vérification |
|---|---|---|
| Structure et scan AST | 1 | Cinq fichiers locaux, init pur, pas de repository ni d'import legacy actif |
| Imports modèles/schémas isolés | 2 | Deux tables locales, aucun web/engine/legacy |
| Ordres sales-first/legacy-first | 2 | Identité des exports, Base, FK, relations, 17 mappers et idempotence |
| Provenance après refus de site | 1 | JWT, Decimal et traversée ORM depuis une session neuve |
| Valeurs commerciales invalides | 4 | 422, aucun Sale/SaleLine écrit |
| Références invalides/incohérentes | 4 | 404/422 exacts, aucun Sale/SaleLine écrit |
| Annulation et état final | 2 | ADMIN et TECHNICIAN : CANCELLED, transitions suivantes 409, ligne/prix conservés |

Les scénarios API réutilisent la fixture installations SQLite avec FK actives et JWT réels ; sa variante PostgreSQL est explicitement neutralisée pour ces nouveaux cas.

Une comparaison des quatre modules au parent `29f034e`, par `ast.dump(..., include_attributes=False)`, retire seulement les imports de premier niveau. Le reste est égal : **11 définitions**, enums, champs, contraintes, décorateurs, fonctions, signatures, requêtes, commits et messages. Aucune normalisation d'identifiant n'est nécessaire.

Ce contrôle complète les snapshots : l'égalité des comptes de tables seule ne prouverait pas la conservation de l'enum, des index ou du comportement transactionnel.

## 9. Résultats observés sur le checkout principal

| Vérification | Résultat |
|---|---|
| Bootstrap/customers/catalog/sales module + ventes/installations/migration | **100 passed**, 1 warning, 33,58 s |
| Suite complète SQLite | **315 passed**, 5 warnings, 64,56 s |
| PostgreSQL 17.4 ventes/installations/migrations | **56 passed**, 1 warning, 27,79 s |
| PostgreSQL 17.4 imports service/API | **39 passed**, 1 warning, 32,79 s |
| Migrations PostgreSQL aller/retour | Réussite jusqu'à `f102e0010001` |
| `alembic check` | Code 255, seulement l'écart FK technicien connu |
| Comparaison structurée Alembic | `remove_fk`/`add_fk` exactement égaux à R2, aucune nouvelle opération |
| OpenAPI/metadata | Octet pour octet comme R0/R1/R2 et références R3 : 46 chemins, 63 opérations, 17 tables |
| Runtime Uvicorn réel | Startup/shutdown complets ; `/docs` et `/openapi.json` : 200 |

**315 = 299 R3 + 16 nouveaux cas R4.** Les groupes PostgreSQL sont des réexécutions existantes, pas 95 nouveaux tests ni une exécution des 16 nouveaux cas sous PostgreSQL.

La revue indépendante n'a trouvé aucun défaut fonctionnel/ORM bloquant et a exécuté **5 tests structurels/imports**, sans répéter les tests d'intégration. Elle a signalé un trou de couverture faible : les scénarios HTTP n'utilisaient que ADMIN. Le scénario de provenance a été passé sous TECHNICIAN et l'annulation paramétrée sur les deux rôles ; les trois routes sont ainsi exercées par un technicien. Les premiers runs de **99 tests ciblés / 314 SQLite** précédaient ce renforcement ; les résultats finaux du tableau sont ceux réexécutés après correction, sans changement applicatif.

Les commandes utilisent l'interpréteur installé du checkout principal, avec chemins absolus :

```text
python -m pytest <7 fichiers ciblés> -q -p no:cacheprovider
python -m pytest <backend>/tests -q -p no:cacheprovider
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini downgrade -1
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini check
python -m pytest <installations/ventes/migration> -q -p no:cacheprovider
python -m pytest <imports service/API> -q -p no:cacheprovider
python -m uvicorn app.main:app --host 127.0.0.1 --port <port libre>
git diff --check
```

Enveloppe SQLite représentative des commandes exécutées :

```python
backend = Path("/home/lob/workspace/python/fastapi/Tervo/backend")
files = [
    "test_modular_bootstrap.py", "test_customers_module.py", "test_catalog_module.py",
    "test_sales_module.py", "test_sales.py", "test_installations.py",
    "test_installation_migration.py",
]
with tempfile.TemporaryDirectory(prefix="tervo-r4-tests-") as work:
    env = {k: v for k, v in os.environ.items() if not k.startswith("TERVO_")}
    env.update(
        PYTHONPATH=str(backend),
        DATABASE_URL="sqlite:///./tervo.db",
        UPLOAD_DIR=str(Path(work) / "uploads"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    for paths in ([str(backend / "tests" / file) for file in files],
                  [str(backend / "tests")]):
        subprocess.run(
            [str(backend / ".venv/bin/python"), "-m", "pytest",
             *paths, "-q", "-p", "no:cacheprovider"],
            cwd=work, env=env, check=True, timeout=240,
        )
```

L'extrait omet la capture des sorties pour le manifeste. Il utilise `Path`, `os`, `tempfile` et `subprocess`. Le chemin absolu correspond au checkout effectivement testé, pas une nouvelle convention de déploiement.

Le scout PostgreSQL a utilisé une instance jetable `postgres:17.4`, `--pull never`, sans volume nommé et avec port éphémère sur 127.0.0.1. Il a attendu une vraie connexion SQL TCP et supprimé son conteneur. Les variables `TERVO_*` ont sélectionné les fixtures PostgreSQL ; `DATABASE_URL` applicatif est resté une SQLite temporaire. Uvicorn a été terminé puis attendu : code `-15` après SIGTERM et shutdown complet.

L'écart SQL historique sur `job_technician_id_fkey` est conservé : `remove_fk` sans ondelete, puis `add_fk` avec `SET NULL`, sur `intervention.technician_id → user.id`. Ce n'est pas un check entièrement vert : c'est **aucune nouvelle différence**. Aucune migration n'est générée. La chaîne complète SQLite demeure non portable sur l'ancien `ALTER TYPE` PostgreSQL.

## 10. Preuves, todos et limites

Le manifeste R4 conserve les comptes/durées, commandes, opérations normalisées, résultats HTTP et les empreintes des **13 sources/tests** finaux. Les snapshots identiques ne sont pas dupliqués ; leurs références et hashes sont conservés. Les révisions Alembic, fichiers de dépendances, captures JSON R0/R1/R2/R3 et fixtures d'import restent inchangés.

Les todos backend/frontend ont été relus. Ce déplacement ne débloque aucun todo métier : rôles TD-B013, mesure représentative TD-B016 et interfaces TD-F007 restent hors scope. TD-B017 demeure réalisé ; son ancien « contrat intermédiaire » est explicitement marqué historique pour ne pas le confondre avec le champ nullable `sale_line_id` actuel.

Limites explicites :

- validation locale Python 3.12.0, pas un run CI distant Python 3.11 ;
- nouveaux tests de module/API sur SQLite, pas PostgreSQL ;
- les règles de concurrence des ventes ne sont pas réécrites ni présentées comme renforcées ;
- aucune exécution du seed, aucun nettoyage de base existante ;
- aucun build frontend, test navigateur, push, déploiement ou commit R4 ;
- comparaison complète des journaux d'import avant/après réservée à R9 ;
- clôture R4 soumise à l'utilisateur ; **R5 / INT-117 non commencé**.
