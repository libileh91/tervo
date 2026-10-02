# INT-123 — R11 : retirer les façades, vérifier le monolithe final

**État de capture : implémenté et vérifié localement ; commit R11 autorisé par
l'utilisateur après les derniers contrôles.** Cette note et le JSON sont
préparés avant ce commit ; aucun push, CI distante ou déploiement.
R10 a déjà été accepté et committé sous
`2f9e0c3530bdc5493c79b1c5a2d3e82fa722e732` : il n'a pas été recommitté.

Références : [tâche INT-123](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md#int-123--r11--retirer-les-couches-horizontales-legacy),
[cas de test](../../../docs/stages/stage7/refactor-monolithe-modulaire/test-cases.json),
[preuve structurée R11](R11-validation.json), [bilan global](bilan-R0-R11.md),
[note R10](INT-122-R10-identity-dashboard.md).

## 1. Une reprise explicite, pas une continuité supposée

Le nouveau worktree attaché était propre, sur `main` à R0 `544a23d`.
Le checkout source de l'ancien fil était accessible en lecture, sur R10 avec
28 fichiers de diff R11. La branche locale `refactor/modular-monolith` pointait
encore sur R4 `93be411`. Elle a été avancée ici, sans divergence ni nouveau
commit, par fast-forward jusqu'au commit R10 déjà existant.

Le diff non committé de l'ancien checkout a ensuite été transféré uniquement
dans ce worktree, avec `apply_patch`. Un `cmp` des deux diffs a confirmé leur
identité octet par octet **avant** le renforcement supplémentaire du garde-fou
final décrit plus bas. Aucun fichier de l'ancien checkout n'a été édité.

Le skill projet `fuliyeh` a été chargé. Aucun `AGENT.md`/`AGENTS.md` n'a été
trouvé dans le worktree. Le feu vert « commit R10 & start R11 » était déjà
effectif ; cette reprise ne l'étend ni aux features 7.4 ni au commit R11.

## 2. Pourquoi supprimer une façade apparemment inoffensive ?

Une façade d'import donne une API Python de compatibilité :

```python
# Ancien appelant, avant R11 :
from app.models import Base
```

Ce chemin avait deux effets confondus : fournir la Base technique **et** importer
implicitement toutes les classes métier. Un test qui faisait `create_all`
fonctionnait alors parfois grâce à ce chargement global, pas grâce à une
précondition explicitement déclarée. Le risque n'était pas une nouvelle colonne
SQL, mais un couplage invisible à l'ordre des imports.

Deux options étaient possibles :

| Option | Bénéfice | Coût |
|---|---|---|
| Garder indéfiniment les réexports | Compatibilité des anciens appelants | Deux chemins publics, chargement implicite et dépendance cachée |
| Supprimer après adaptation de tous les appelants | Un chemin canonique, bootstrap lisible | Vérifier les tests standalone et les vrais entrypoints |

R11 retient la seconde. Les cutovers R2–R10 avaient déjà déplacé les règles
métier ; cette vague termine leur transition sans les réécrire.

### Diff runtime volontairement réduit

Seuls cinq fichiers runtime encore présents en R10 sont supprimés :

```text
backend/app/models/__init__.py    # réexports globaux des modèles
backend/app/models/base.py        # shim de la Base technique
backend/app/schemas/__init__.py   # vide
backend/app/api/__init__.py       # vide
backend/app/api/v1/__init__.py    # vide
```

Les autres couches horizontales (`repositories`, `services`, `importers`,
`exporters`) étaient déjà retirées par les vagues précédentes/nettoyage R9.
Les dossiers réellement vides `models`, `schemas`, `api/v1`, puis `api` ont été
retirés par `rmdir` ; cette commande échoue si du contenu demeure. Aucune
suppression de dossier uploads, venv, base existante, dépendances ou source
active n'a été faite. Les sept racines legacy sont absentes au contrôle final.

Il n'y a aucun changement de corps de fonction métier, route, DTO, modèle,
transaction, template ou opération Alembic dans R11.

## 3. Base pure et registre explicite : deux responsabilités

Le chemin canonique reste :

```python
from app.core.base import Base
from app.model_registry import load_models

load_models()
# Utiliser ensuite Base.metadata : migrations, création de schéma de test, etc.
```

Importer `Base` fournit **un objet technique unique**, sans découvrir les
domaines. Appeler `load_models()` enregistre les classes connues sur cet objet,
sans créer d'engine ni accéder à SQL. Le registre utilise des imports locaux
explicites et le cache des modules Python, pas un second registre ni un flag
global qui cacherait un chargement incomplet.

Extrait fidèle du registre inchangé :

```python
def load_models() -> None:
    """Register all current models on the shared Base, without creating an engine."""
    # Local imports keep importing this registry independent of loading domains.
    # Python's module cache makes repeated calls safe without a second registry.
    from app.modules.interventions.models.checklist_item import ChecklistItem  # noqa: F401
    from app.modules.customers.models import Client, Site  # noqa: F401
    from app.modules.equipment.models import Equipment  # noqa: F401
```

La liste complète conserve les **17 tables / 17 mappers** :
Client, Site, Product, Sale, SaleLine, Equipment, Installation, User,
Intervention, ChecklistItem, InterventionPhoto, Material, Review et les quatre
classes du journal d'import. `dashboard` et `reports` n'ajoutent pas de modèle
pour obtenir une symétrie de dossiers.

Les entrypoints étaient déjà corrects depuis R1 :

| Entry point | Barrière de chargement vérifiée |
|---|---|
| `app/main.py` | `load_models()` avant inclusion des routers |
| `alembic/env.py` | `load_models()` avant `target_metadata = Base.metadata` |
| `app/seed.py` | `load_models()` avant création du schéma de démonstration |

Le seed n'est pas lancé manuellement par cette reprise sur une base existante.
Les tests de seed de la suite ne visent que leur propre SQLite de démonstration.
Sa sûreté sur une base V2 peuplée n'est pas acquise : TD-B019 reste ouvert.

### Corriger les préconditions des tests, pas le métier

Les imports ordinaires de Base passent à `app.core.base`. Deux fixtures qui
doivent fonctionner seules chargent explicitement le registre :

```python
# backend/tests/test_import_service_v2.py
@pytest_asyncio.fixture
async def environment():
    load_models()
    url = os.environ.get('TERVO_IMPORT_TEST_DATABASE_URL')
    schema = 'import_test_' + uuid4().hex
```

```python
# backend/tests/test_installation_migration.py
@pytest.fixture
def migration(tmp_path, monkeypatch):
    load_models()
    postgres = os.environ.get("TERVO_INSTALLATION_MIGRATION_TEST_URL")
    schema = "installation_migration_" + uuid4().hex
```

Le rejeu golden d'import appelle aussi `load_models()` avant `create_all`.
Cela évite qu'un test vert dépende de la collecte préalable de `app.main`.
La migration conserve ses assertions et ses opérations SQL.

## 4. Les tests ne doivent plus simuler une compatibilité supprimée

Les tests de domaine qui opposaient « legacy-first » et « domain-first »
opposent désormais « registry-first » et « domain-first ». Dans les deux cas :

1. Les tables et mappers déjà chargés sont mémorisés.
2. Le registre complète le chargement.
3. `configure_mappers()` réussit avec exactement les 17 mappers attendus.
4. Un second chargement conserve les mêmes objets `Table`, classes et mappers.
5. Toutes les FK résolvent leur vraie table dans la même metadata.
6. Les relations inter-domaines pointent vers les classes canoniques.

L'identité compte ici plus que le seul nombre : deux classes différentes
portant le même nom ne constituent pas une preuve d'unicité.

Le faux package `ModuleType("app.models")` du test de transition a été retiré.
Il était utile pendant le cutover ; le conserver après suppression des façades
aurait validé un monde qui n'existe plus.

### Garde-fou permanent final

Le helper de subprocess ajoute systématiquement les sept racines interdites :

```python
RETIRED_PACKAGES = (
    "app.models", "app.repositories", "app.schemas", "app.services",
    "app.api", "app.importers", "app.exporters",
)
```

Même un scénario qui autorise l'import de FastAPI, du router ou la création
d'engine ne peut donc autoriser le retour des packages legacy. Les tentatives
d'import sont enregistrées avant d'être rejetées ; un `try/except` applicatif
ne peut les masquer. Les protections contre engine/connexion/SQL des tests
de pureté sont conservées.

Le nouveau test AST parcourt les sources Python runtime, tests, Alembic,
scripts backend et racine. Il traite les imports absolus/relatifs ainsi que les
appels `import_module`/`__import__` à cible absolue littérale, et refuse tout
fichier Python revenu sous une des racines retirées. Il n'efface pas les citations
historiques ni les chaînes d'interdiction des tests.

Un contrôle ponctuel complémentaire a scanné **148 fichiers Python**, y compris
les appels d'import dynamique avec argument littéral : aucune référence legacy
exécutable. Une recherche textuelle dans backend, frontend, CI et deploy ne
trouve que les assertions/chaînes de garde des tests. Le test AST n'est pas
présenté comme une analyse statique exhaustive des imports construits
dynamiquement ; les gardes des vrais subprocess complètent cette limite.

## 5. Contrats et règles métier préservés

Les couches conservent leur rôle : routes HTTP, validation Pydantic, règles et
transactions dans les services existants, accès aux données dans les
repositories lorsqu'ils existent, mapping dans les modèles de domaine.
Il n'y a pas de repository artificiel ajouté à `sales`, de bus, d'HTTP interne,
de nouvelle UnitOfWork ou de migration liée aux chemins Python.

| Parcours existant | Contrat conservé et exercé |
|---|---|
| Auth / profil | JWT réel, utilisateur actif, rôles ADMIN/TECHNICIAN actuels |
| Client / Site | CRUD et protections de références, liens physiques conservés |
| Vente | Lignes et `Decimal`, confirmation/annulation et erreurs existantes |
| Installation autonome | Site obligatoire, `sale_line_id` absent/null possible |
| Installation commerciale | Ligne confirmée, cohérence site/produit et quantité |
| Clôture installation | Equipment lié, transaction atomique, aucune duplication |
| Import | Plan validé, SHA/idempotence, erreurs tracées, reprise et lease |
| Terrain / rapport / avis | Transitions existantes, PDF réel, avis public existant |

Par exemple, une installation autonome peut toujours être créée avec :

```json
{"site_id": 1, "sale_line_id": null}
```

La pose ne crée pas de vente fictive. Les transitions terminales et les erreurs
404/409/422 restent celles des services existants. R11 n'ajoute ni écran ni
permission ni validation métier pour modifier ces contrats.

## 6. Validations réellement exécutées dans ce fil

Toutes les validations Python utilisent le venv préexistant :

```bash
PYTHON=/home/lob/workspace/python/fastapi/Tervo/backend/.venv/bin/python
# ROOT = worktree attaché ; cwd/SQLite/uploads de la suite dans le scratch.
PYTHONPATH="$ROOT/backend" PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 \
DATABASE_URL=sqlite:///./runtime.db UPLOAD_DIR="$SCRATCH/uploads" \
"$PYTHON" -m pytest "$ROOT/backend/tests" -q -p no:cacheprovider
```

Cette commande décrit le run exécuté depuis un répertoire temporaire, pas
l'installation de nouvelles dépendances. Le venv s'appuie sur la bibliothèque
standard de son Python de base ; cela ne signifie pas que les paquets utilisateur
du pyenv incident ont été utilisés.

| Run | Résultat observé |
|---|---|
| Suite après transfert exact | **390 passed**, 7 warnings, 99,43 s |
| Suite après garde renforcée aux sept racines | **390 passed**, 7 warnings, 103,00 s |
| Suite finale précommit, garde d'import dynamique incluse | **390 passed**, 7 warnings, 95,49 s |
| Import service lancé seul | **11 passed**, 10,62 s |
| Migration installation lancée seule | **3 passed**, 1,43 s |
| Bootstrap + identity + imports bootstrap + golden | **38 passed**, 1 warning, 30,51 s |
| PostgreSQL canonique | **95 passed**, 1 warning, 50,08 s |

Les 390 cas correspondent aux 389 de R10 plus le nouveau garde-fou AST.
Les warnings concernent `crypt`/passlib et `datetime.utcnow()` dans le terrain
existant ; ils ne sont pas corrigés par une vague structurelle.
La suite entière interrompue dans l'ancien fil n'est pas comptée comme un succès.

Le scanner final a aussi été exercé sur six sources synthétiques en scratch :
imports absolus/relatifs et `importlib.import_module`, `import_module`,
`__import__` littéraux sont rejetés ; une simple citation `"app.models"` est
permise. Ces probes ne sont pas ajoutées artificiellement au compte des 390.

Le reviewer a transmis un rapport intermédiaire : **103 tests de frontières**
et **17 tests import/migration** réussis, audit indépendant des 148 fichiers
Python sans référence exécutable legacy. Son snapshot isolé précédait le
renforcement final. Sa remarque sur les imports dynamiques littéraux a été
traitée dans le scanner ; la recherche de configuration non-Python reste un
contrôle ponctuel, pas une analyse AST de YAML/Dockerfile. La sous-tâche de revue
a ensuite été interrompue par une limite de quota : **pas d'approbation finale
de reviewer revendiquée**. Le parent a exécuté la suite finale et les probes
sur le code réellement committable.

### PostgreSQL jetable, pas la base de travail

Le scout dédié a exécuté uniquement cette partie, avec le même venv et les
sources du worktree attaché. PostgreSQL local `postgres:17.4 --pull never`,
port `127.0.0.1:32771`, conteneur `tervo-r11-pg-97271`, aucun volume nommé.
Les commandes Alembic/tests utilisaient le cwd `backend` ; les uploads/logs
étaient temporaires et les fixtures ciblaient exclusivement la base jetable.

```bash
"$PYTHON" -m alembic -c alembic.ini upgrade head
"$PYTHON" -m alembic -c alembic.ini downgrade e103e0010001
"$PYTHON" -m alembic -c alembic.ini upgrade head
"$PYTHON" -m alembic -c alembic.ini check
"$PYTHON" -m pytest -q \
  tests/test_installations.py tests/test_sales.py \
  tests/test_installation_migration.py \
  tests/test_import_service_v2.py tests/test_import_api_v2.py
```

Les quatre variables de fixtures CI étaient renseignées :
`TERVO_INSTALLATION_TEST_DATABASE_URL`, `TERVO_SALE_TEST_DATABASE_URL`,
`TERVO_INSTALLATION_MIGRATION_TEST_URL`, `TERVO_IMPORT_TEST_DATABASE_URL`.
Elles ne visent jamais une base existante.

Upgrade complet vers `f102e0010001`, dernier downgrade vers `e103e0010001`,
puis re-upgrade : **succès**. `alembic check` retourne **255**, pas zéro.
La comparaison structurée `compare_metadata` confirme exactement :

```text
remove_fk intervention.technician_id -> user.id, ondelete=None
add_fk    intervention.technician_id -> user.id, ondelete=SET NULL
```

C'est l'écart historique `job_technician_id_fkey`, déjà accepté en R0 :
aucune autre opération, correction FK ou nouvelle migration. Le `finally`
a supprimé le seul conteneur et son volume anonyme avec `docker rm -f -v`.
Le parent a confirmé l'absence de conteneur `tervo-r11-pg-*` restant.
Les nouveaux parcours HTTP identity/dashboard/seed ne sont pas revendiqués
comme exécutés sur PostgreSQL.

### Snapshots et vraie documentation HTTP

- Metadata complète égale à R0, sérialisation **42 080 octets**, même SHA
  `e86c52bc02519708beb34a3dd587ca566a222f54a04a3fe0b62bdd742ca2089a`.
- OpenAPI complète égale à R0 dans les tests et via HTTP :
  **46 chemins / 63 opérations**, pas seulement un comptage de routes.
- Référence OpenAPI inchangée, **185 215 octets**, SHA
  `dcabfd245b80cbf3989f71049669c3a65e9766b3ed9512bbf58e22acea942fd7`.
- Uvicorn réel sur `127.0.0.1:35945`, `/openapi.json` et `/docs` **200**,
  startup/shutdown complets, processus arrêté après SIGTERM (code `-15`).

Un premier script ponctuel metadata a échoué parce qu'il omettait `import json`.
Le script scratch a été corrigé puis la comparaison a réussi ; aucun fichier
applicatif n'a été changé pour résoudre cet échec d'outillage.

### Oracle R9 conservé, pas recapturé après refactor

Le fichier `backend/tests/fixtures/imports_refactor/before.json` est inchangé :
SHA fichier `6fea24321f71239649f57be88e0270c5e704cce12a23ff1722d3aad0431d6279`.
Le test golden garde ses assertions de provenance et SHA décodé :
**560 268 octets**, `f98dd88686d7efc6446187e5507a8c49be5fe3be66453acc014b1fcbec502db2`.
Le payload complet est égal après rejeu ; ce n'est pas un résumé de compteurs.
Les fixtures Excel/CSV, snapshots et JSON R0–R10 n'ont pas été réécrits.

## 7. Frontend : construire l'existant, ne pas inventer des écrans

Tous les fichiers frontend suivis, y compris les locks, sont identiques à
R0 `544a23d`. Le workflow CI utilise **Bun**, pas `npm ci`.
Une copie temporaire des fichiers suivis a été validée dans ce fil :

```bash
bun --version                  # 1.2.20
bun install --frozen-lockfile   # succès
bun run typecheck              # succès
bun run build                  # Vite 6.4.3, 450 modules, succès
```

Les dépendances et le build sont restés dans cette copie. Le `package-lock.json`
npm obsolète est un défaut préexistant signalé dans la reprise : son échec
`npm ci` dans l'ancien fil n'est ni réparé silencieusement ni présenté comme
un échec du workflow Bun.

### Preuve navigateur transmise, distincte du rejeu de ce fil

La demande de reprise fournit une preuve de smoke réel du parent, **après**
retrait des cinq façades. Le diff runtime transféré ici est le même ; le seul
renforcement ultérieur touche les tests. Ce smoke n'a pas été relancé dans ce
fil et aucun script durable de l'ancien scratch n'est disponible.

Résultats transmis : Playwright **1.63.0**, Chrome Headless Shell
**153.0.8010.12**, backend dans le bon venv, frontend Bun frozen, données jetables :

- Login et dashboard ; création de client UI **201**, détail et site readonly.
- Intervention COMPLETED préparée par un setup ORM fictif, pas par `app.seed`.
- Aperçu PDF blob et vrai téléchargement **15 464 octets**, signature `%PDF-`,
  fichier `rapport-intervention-1.pdf`.
- Nouveau contexte sans login : avis public **4 étoiles**, commentaire,
  POST **200** et confirmation « Merci! ».
- Zéro erreur console/page/HTTP sur les pages authentifiées ; submit public
  explicitement confirmé.
- Routage Playwright `/api/v1/**` vers le backend loopback, sans modifier Vite.
- Serveurs/browser arrêtés, DB/uploads et copie frontend supprimés selon le
  compte rendu transmis.

Il n'existe **pas** d'UI vente, installation ou import. Ces trois parcours ont
été vérifiés par les API/tests existants, sur SQLite et les groupes canoniques
PostgreSQL, et sont documentés **backend-only**. Aucun écran fictif n'est annoncé.
Login/Dashboard/Clients/détail+sites/Interventions/détail/inspection/Profile/avis
public constituent l'UI actuelle ; tous ne font pas partie du smoke transmis.

## 8. Incident environnement : traçabilité et absence de réparation cachée

Dans l'ancien fil, un scout navigateur a utilisé par erreur
`/home/lob/.pyenv/versions/3.12.0/bin/python` puis `pip install --user`, modifiant
`/home/lob/.local/lib/python3.12/site-packages`. L'utilisateur avait déjà été
averti. Il n'y a pas de snapshot avant permettant de distinguer ajout/upgrade.

Paquets rapportés installés (versions issues de la reprise, non réauditées ici ;
ne pas utiliser cette liste comme inventaire de désinstallation) :
aiosqlite 0.22.1, ecdsa 0.19.2, passlib 1.7.4, pyasn1 0.6.4,
python-jose 3.5.0, rsa 4.9.1, et-xmlfile 2.0.0, numpy 2.5.3,
openpyxl 3.1.5, pandas 3.0.6, rapidfuzz 3.14.6, python-multipart 0.0.32,
MarkupSafe 3.0.3, Pyphen 0.18.1, brotli 1.2.0, cssselect2 0.10.1,
fonttools 4.66.1, jinja2 3.1.6, pydyf 0.12.1, tinycss2 1.5.1,
tinyhtml5 2.1.0, weasyprint 70, zopfli 0.4.3.
La version de webencodings est transmise sous la notation `webencodings.6.1` ;
elle n'est pas résolue ici sans inventaire read-only fiable.
`bcrypt 4.2.1` était déjà présent dans ce pyenv, non installé par le scout.

Un `package.json` racine créé accidentellement par `npm init` avait été
confirmé puis supprimé par le parent ; il n'a pas été transféré. Pas d'apt ni
de npm global. Des `frontend/node_modules`/`dist` ignored avaient été installés
dans l'ancien checkout sans modification de source/lock ; ils n'ont pas été
transférés non plus.

**Aucune installation/désinstallation dans cet environnement utilisateur dans
ce fil.** Ne pas tenter de le « nettoyer » sans accord et sans inventaire fiable.
Les validations Python décrites ici utilisent exclusivement le venv existant ;
le build frontend installe uniquement dans une copie temporaire.

## 9. Limites et feu vert suivant

R11 clôt techniquement le retrait legacy, pas le produit Tervo V2 entier.
Restent ouverts :

- **TD-B013** : nouveaux rôles MANAGER/COMMERCIAL et permissions.
- **TD-B016** : import mesuré sur volume réel représentatif.
- **TD-B018** : reprise documentaire des chemins 7.4, dans son scope autorisé
  distinct avant les features, sans changer leurs statuts historiques.
- **TD-B019** : protection/cadrage du seed destructif sur une base avec données.
- **TD-F007** : besoins UI V2 catalogue/showroom et parcours futurs.

Aucun test de migration complète SQLite n'est revendiqué : la chaîne contient
`ALTER TYPE` PostgreSQL. Aucun résultat local ne vaut CI distante, performance
sur vingt ans d'Excel, sécurité de seed en production, push ou déploiement.
L'utilisateur a ensuite demandé « si t'as fini commit R11 & passe au suivant ».
Ce feu vert autorise le commit après contrôle final. R11 étant la dernière vague,
la prochaine scope recommandée est TD-B018 ; aucune feature 7.4 ne démarre
automatiquement sous cette autorisation générale.
