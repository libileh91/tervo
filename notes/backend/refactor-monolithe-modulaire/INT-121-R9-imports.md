# INT-121 — R9 : déplacer les imports avec une preuve fonctionnelle avant/après

> **Planning :** [INT-121](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md#int-121--r9--déplacer-imports).
> **Parent R8 :** `bb1fc14c4d8da80e9584eb1ed6de1f69cd96132e`, branche `refactor/modular-monolith`.
> **État :** accepté et committé sous `205969a` dans le worktree Delta attaché. R10 non autorisé/non commencé. Le manifeste conserve sa capture avant acceptation.
> **Preuves :** [R9-validation.json](R9-validation.json) et [oracle fonctionnel avant](../../../backend/tests/fixtures/imports_refactor/README.md).

## 1. Reprise de R8 et ordre des opérations

L'utilisateur a accepté R8 et demandé « commit R8 & passe R9 ». Les neuf
empreintes sources/tests/fixtures R8 correspondent au manifeste. Avant commit,
bootstrap, reports et `test_api.py` ont été rejoués en isolation :
**49 passed, 2 warnings, 24,53 s**.

Le commit `[DEV]INT-120 — Refactor : isoler le domaine reports` est `bb1fc14`.
Il ne contient aucun déplacement R9. Le commit est créé dans le worktree
attaché, sans push ni écriture directe du checkout principal.

R9 est la vague la plus sensible : imports orchestre plusieurs domaines et
persiste aussi les décisions de migration. Une suite verte et des fichiers
Excel inchangés ne suffisent pas à démontrer que les mêmes données sont écrites.
L'ordre a donc été :

1. relire le service, le planner, les modèles et les tests existants ;
2. vérifier les six empreintes du pack contre R0 ;
3. capturer un replay fonctionnel **avant** tout déplacement ;
4. rejouer et vérifier cette capture sur les sources legacy du parent R8 ;
5. borner la normalisation aux champs techniques, sans changer l'oracle ;
6. déplacer les sources et adapter les imports ;
7. rejouer exactement la même recette et comparer tout le contenu ;
8. vérifier les suites, PostgreSQL, contrats et revue.

Une interruption de quota de l'agent chargé de la capture a suivi son rapport
de réussite. À la reprise, le parent a vérifié les fichiers effectivement
présents et réexécuté le replay legacy : **1 passed, 2,84 s**. Il ne s'est pas
fondé uniquement sur un message de fin.

Avant cutover, le normaliseur de preuve a été limité par table et un test
synthétique ajouté : **2 passed, 2,11 s**, avec le même snapshot figé.
Les cinq fichiers historiques d'import passaient déjà : **90 passed,
1 warning, 15,58 s**. Cette capture appartient à R9 ; R0 avait figé les sources
et exécuté des tests, mais n'avait pas produit cet oracle fonctionnel complet.

## 2. Organisation choisie et frontière du pipeline

```text
app/modules/imports/
├── __init__.py
├── models.py
├── schemas.py
├── planner.py
├── service.py
├── api.py
└── pipeline/
    ├── __init__.py
    ├── excel_reader.py
    ├── format_detector.py
    ├── ingestion.py
    ├── normalizer.py
    ├── validators.py
    ├── matcher.py
    ├── multi_matcher.py
    └── report.py
```

**14 sources déplacées**, plus un nouvel init racine pur. Les anciennes sources
sont absentes ; aucune façade legacy ne conserve une seconde implémentation.
Le pipeline garde les exports historiques d'INT-71 dans son propre init.
Importer `app.modules.imports` seul ne charge pas automatiquement ce pipeline.

| Source sous `backend/app/` | Propriétaire actuel |
|---|---|
| `models/import_batch.py` | `modules/imports/models.py` |
| `schemas/imports.py` | `modules/imports/schemas.py` |
| `services/import_planner.py` | `modules/imports/planner.py` |
| `services/import_service.py` | `modules/imports/service.py` |
| `api/v1/imports.py` | `modules/imports/api.py` |
| `importers/*.py`, init compris | `modules/imports/pipeline/`, mêmes noms |

### Pourquoi le planner est à la racine

Le diagramme initial proposait `pipeline/planner.py`. Le code réel du planner
importe les schémas Client/Site/Product/Equipment/Intervention pour valider
les écritures proposées ; certains de ces schémas chargent des modèles ORM.
Le mettre dans le sous-package bas niveau obligerait à affaiblir le contrat
historique « pipeline sans framework ni base » ou à créer une exception artificielle.

Le choix retenu est **planner à la racine**, auprès de l'orchestration :
pipeline bas niveau indépendant, planner adaptateur des contrats métier,
service propriétaire des opérations SQL. La règle historique de dépendance
du pipeline reste entière ; seul son préfixe Python change.
Aucun algorithme de matching ou de planification n'est réécrit.

Le module imports possède son journal technique, **pas** les entités métier
Client/Site/Product/Equipment/Intervention. Ses appels Python vers leurs modèles
et schémas sont conservés, sans HTTP interne, bus ou UnitOfWork généralisé.

## 3. Le journal SQL n'est pas un deuxième modèle métier

Les [quatre modèles](../../../backend/app/modules/imports/models.py#L6)
conservent la Base technique commune, leurs tables, types et contraintes :

| Modèle | Rôle |
|---|---|
| ImportBatch | Bytes source, manifeste, lignes capturées, plan, décisions, approbation, révision, statut et bail |
| ImportRecord | Ligne effectivement commitée, cible métier, action, brut/normalisé et décision |
| ImportReference | Référence historique dans son namespace → ID métier interne |
| ImportError | Anomalie/erreur par batch et révision, provenance et valeurs originales |

```python
__table_args__ = (UniqueConstraint('source_namespace', 'file_hash', name='uq_import_file'),)
```

Deux mêmes fichiers binaires dans le même namespace désignent un seul batch.
Le nom de fichier seul n'est pas une clé d'idempotence.
ImportRecord garde l'unicité `(import_batch_id, row_key)`.
ImportReference garde `(source_namespace, entity_type, source_id)`.
La référence C001 de deux archives distinctes n'est donc pas automatiquement
le même client.

Les IDs métier restent des entiers. Les IDs virtuels négatifs utilisés par
le planner ne sont pas des IDs SQL persistés : ils représentent des créations
qui n'ont pas encore été exécutées.

Les quatre réexports dans `app.models` conservent les mêmes classes déplacées.
Le registre les charge explicitement. Les tests vérifient les deux ordres
d'import, les FK et l'idempotence du registre : **17 tables, 17 mappers,
une seule Base**. Aucune migration n'est ajoutée.

## 4. Du fichier source au plan : lecture et décisions explicites

Le pipeline conserve lecture XLSX/CSV, choix des feuilles/en-têtes, mapping
par nature d'entité, normalisation et anomalies. Le CSV du pack est Latin-1
avec séparateur `;`, déclaré explicitement dans la recette.

Le [service de capture](../../../backend/app/modules/imports/service.py#L82)
conserve les bytes en base et appelle `read_sources`. Il ne remplace pas le
brut par les corrections. Les lignes gardent fichier, feuille, ligne, mapping,
valeurs originales, valeurs normalisées, propositions et anomalies.
Une source illisible ou vide est refusée, pas transformée en import réussi.

### Références et rapprochement

Le planner travaille sur une copie des pools et références. Il cherche le
parent avant de rapprocher une entité enfant : un équipement ressemblant à
un autre mais situé sur un autre site n'est pas associé par simple score.
Les seuils bas niveau restent **95 / 80**, avec trois zones :
association fiable, revue humaine, nouvelle entité.

Une référence source non résolue devient `ORPHAN`. Un doute d'identité devient
`DUPLICATE_AMBIGUOUS`/revue, pas une création silencieuse.
Une association prouvée de client peut réduire certaines anomalies de données
absentes à des warnings, mais ne vide pas les champs historiques du client.

### Le planner respecte les dépendances

```python
order = {'products':0,'clients':1,'sites':2,'equipment':3,'interventions':4}
queue = sorted(enumerate(deepcopy(records)),key=lambda pair:order[pair[1]['kind']])
```

Il construit d'abord les entités parentes, puis les interventions. Les lignes
qui échouent sont réessayées tant qu'une autre ligne fait progresser les
références disponibles. Sans progression, elles restent `pending`.
Il ne s'agit pas de deux commits globaux : les deux niveaux de traitement
logique sont distincts des transactions d'exécution par sous-lots.

### Une correction est une décision, pas un nettoyage invisible

```json
{
  "action": "create",
  "corrections": {"site_name": "12 rue Exemple"},
  "note": "Nom technique repris de l'adresse source"
}
```

ImportDecision exige une action `create / associate / ignore / review` et une
note non vide, maximum 2000 caractères. `associate` demande exactement une
cible : ID interne positif **ou** référence source. Les autres actions
n'acceptent pas une cible d'association.
Les corrections ne peuvent pas introduire un champ inconnu ; les valeurs
invalides brutes ne deviennent pas valides par le seul choix de `create`.

Pour une création, les IDs virtuels sont provisoirement rendus positifs lors
de la validation Pydantic, puis restaurés dans le plan. Leur résolution SQL
réelle n'arrive qu'à l'exécution.

## 5. Approbation, SHA-256 et API administrative

| Route sous `/api/v1/admin/import` | Contrat actuel |
|---|---|
| `POST /preview` | Multipart file, namespace et sélections JSON ; capture/aperçu |
| `POST /validate` | Mapping/décisions, nouvelle révision et plan approuvé |
| `POST /execute` | Batch ID positif et jeton hexadécimal SHA-256 de 64 caractères |
| `GET /batches` | Historique paginé |
| `GET /batches/{id}` | Plan/manifeste/lignes paginés |
| `GET /batches/{id}/errors` | Erreurs/anomalies paginées |

Les six routes sont toujours **ADMIN uniquement**, via un vrai utilisateur
actif authentifié. TECHNICIAN est refusé en 403. Les sources/plans ne sont pas
publiés aux autres rôles par le déplacement. La limite upload reste 10 Mio,
avec lecture d'un octet supplémentaire pour détecter le dépassement (413).
Une liste de sélections invalide, un fichier sans nom ou une source invalide
gardent leur refus 422.

Le jeton d'approbation dépend des bytes source, namespace, plan, décisions,
sélections et nouvelle révision. Le snapshot de base dépend des pools métier
et références. Ces deux hashes **restent comparés exactement** dans l'oracle.
Ils ne sont pas traités comme des UUID d'exécution volatils.

La validation verrouille le batch et protège aussi la révision par UPDATE
conditionnel. Une validation concurrente ne doit pas écraser l'approbation.
Après un premier sous-lot commité, le mapping est figé ; une ligne déjà commitée
ne peut pas recevoir une autre décision.

## 6. Exécution : le plan validé n'est pas recalculé

Le [service](../../../backend/app/modules/imports/service.py#L202) crée ses
sessions depuis le bind injecté, comme avant R9. Il reste propriétaire des
transactions. Le déplacement n'introduit pas une nouvelle session par domaine
ou un commit automatique par fichier.

L'exécution vérifie batch, jeton et fingerprint, réclame un slot global unique,
puis utilise le plan persisté. Les opérations exécutables sont `create`,
`associate`, `ignore`, hors lignes déjà journalisées. Les `pending` ne sont
pas présentées comme réalisées.

```python
entries = [e for e in batch.plan if e['op'] in {'create','associate','ignore'} and e['key'] not in done]
ids = {r.decision['plan_target']:r.entity_id for r in records if isinstance(r.decision.get('plan_target'),int)
       and r.decision['plan_target'] < 0}
```

La reprise reconstruit donc les correspondances ID virtuel → ID réel à partir
des ImportRecord déjà commités. Elle ne réinsère pas ces lignes.
Le plan approuvé ne repasse pas par le fuzzy matcher au moment de l'écriture.

### Transactions de 500 lignes maximum

La taille par défaut reste 500, avec taille explicite autorisée de 1 à 500
pour les tests. Chaque sous-lot utilise `async with db.begin()`.
Le service relit le batch, contrôle token/statut/plan/fingerprint, écrit les
entités et références, ajoute les ImportRecord, puis actualise le fingerprint.
Le commit du context manager valide l'ensemble de ce sous-lot.

Un échec annule **tout le sous-lot courant**. Les sous-lots déjà commités
restent conservés. Une transaction séparée marque le batch `failed` et écrit
`BATCH_ROLLBACK` pour chaque ligne annulée.
Reprendre ne signifie ni effacer l'audit ni recommencer le fichier de zéro.

### Bail et sérialisation

Le slot `execution_slot = 1` est unique entre fichiers. `execution_token`
identifie le processus détenteur, avec bail de 15 minutes renouvelé.
Un processus ancien ne peut pas continuer après reprise par un autre.
Un bail expiré permet de récupérer l'exécution selon la règle actuelle.

Sur PostgreSQL, `_lock_domain` conserve son `LOCK TABLE ... IN SHARE ROW
EXCLUSIVE MODE`, afin de garder stable le référentiel contrôlé jusqu'au commit
du sous-lot. Les tests canoniques PostgreSQL ont été rejoués avec ces mêmes
verrous. R9 ne remplace pas le mécanisme par un verrou Python local.

## 7. La recette figée : des résultats partiels honnêtes

L'oracle utilise une base SQLite jetable, FK actives, **toutes tables vides**,
sans utilisateur ou produit préchargé. Même namespace `r0-pack`, mêmes bytes,
mêmes sélections et ordre des quatre fichiers, sous-lots de trois.
Les six empreintes du pack sont vérifiées contre R0, y compris README et
inventaire d'anomalies, qui ne sont pas des sources métier exécutées.

| Source | Décisions de la recette | Résultat |
|---|---|---|
| 01, trois feuilles Clients/Sites/Equipements | Noms des quatre sites copiés de leur adresse ; aucune identité/remplacement arbitré | 11 créations, 5 pending, `partial` |
| 02, interventions historiques | Titre = Description et `RESOLVED → COMPLETED`, explicitement approuvés | 4 créations, 4 pending, `partial` |
| 03, ancien format | Années à deux chiffres, base 2000 explicite ; aucune ambiguïté résolue | 3 pending, `partial` |
| 04, CSV Latin-1 | Trois rapprochements automatiques fiables | 3 associations, `success` |

Cinq lignes RESOLVED reçoivent une décision ; une reste orpheline sur E005,
donc seules quatre interventions sont créées. PART_REQUIRED/UNRESOLVED ne
sont pas traduits arbitrairement en statut opérationnel. Le diagnostic sans
équipement reste pending dans **cette recette**, à cause de son statut/titre
à confirmer ; cela ne signifie pas que le modèle exige un équipement.

État final : **4 clients, 4 sites, 3 équipements historiques, 4 interventions**,
**0 installation**, 0 vente/ligne de vente, 0 produit/utilisateur ; journal :
**4 batches, 18 records, 15 références, 111 erreurs/anomalies**.
Les 111 entrées incluent les validations/révisions : ce ne sont pas 111 lignes
source distinctes. Aucun BATCH_ROLLBACK n'est injecté dans la recette du pack ;
les tests transactionnels séparés couvrent ce scénario.

Chaque source est restagée puis le même plan est réexécuté immédiatement.
Le batch ID est identique et toutes les tables restent inchangées après
normalisation des instants techniques. Les erreurs et ambiguïtés ne sont pas
ignorées pour rendre le résultat artificiellement vert.

## 8. Ce qui est comparé et ce qui est normalisé

L'oracle conserve chaque preview complète, validation initiale, décision,
plan approuvé, exécution, erreur et réexécution. Les pages utilisent 1000 :
les 16 / 8 / 3 / 3 lignes source sont donc présentes intégralement.

Le dump parcourt les **17 tables**, ordonnées par nom et PK, et chaque colonne
de chaque ligne existante : journal, entités métier et liens. Les neuf tables
vides apparaissent comme `[]`. Leur structure SQL est vérifiée séparément
par le snapshot metadata R0, pas déduite de ces listes vides.

| Champ | Règle de preuve |
|---|---|
| `created_at`, `updated_at` SQL | Instant technique non null remplacé par `<instant>` |
| `import_batch.completed_at`, `lease_until` | Instant d'exécution/bail non null remplacé par `<instant>` |
| `import_batch.execution_token` | Token non null remplacé par `<lease-token>` |
| `Intervention/Installation.started_at/completed_at` | Valeur exacte conservée, même non nulle |
| Dates source/pose/garantie/planification | Exactes |
| `plan_token`, `database_snapshot` | Hashes exacts |
| IDs/FK/références/textes/erreurs/JSON internes | Exacts, aucune normalisation récursive |
| Bytes source | Taille et SHA-256 ; bytes originaux présents dans le pack hash-vérifié |

Le premier helper de capture normalisait les noms de colonnes d'instant trop
largement. Le parent a corrigé la règle **avant le move** : completion/bail
seulement dans ImportBatch. Les quatre `completed_at` métier étaient nulls ;
le snapshot reste donc identique. Un test synthétique vérifie aussi des dates
de début/clôture non nulles, sans les masquer.

Un cas service supplémentaire crée une Intervention historique sans appareil,
avec site connu et statut explicitement approuvé : équipement null, date
historique exacte, aucun Equipment/Installation/Sale/SaleLine inventé.
Il ne change pas la recette ou l'oracle figé du pack.

### Une capture durable, pas seulement un hash annoncé

`before.json` conserve l'intégralité du JSON compact UTF-8 dans une enveloppe
LZMA/base64 **sans perte** : environ 15 Ko de fichier au lieu de 560 Ko de
plans/audits répétés. Le test décode et compare les valeurs entières.
La [README de recette](../../../backend/tests/fixtures/imports_refactor/README.md)
contient la procédure de décodage pour inspection, sans dépendance externe.

- fichier enveloppe : `6fea24321f71239649f57be88e0270c5e704cce12a23ff1722d3aad0431d6279` ;
- JSON décodé : **560 268 octets**, `f98dd88686d7efc6446187e5507a8c49be5fe3be66453acc014b1fcbec502db2`.

Le parent a aussi sérialisé le replay après en JSON compact, ordre d'insertion
conservé, et comparé les **octets complets** au JSON avant : égalité exacte.
Il n'a pas annoncé l'égalité depuis le seul hash des Excel.
Le payload après étant identique, il n'est pas dupliqué en deuxième gros
artefact ; manifeste, test de replay et SHA référencent l'oracle unique.

La revue a demandé de renforcer le gel de l'oracle : son hash interne seul
pouvait être régénéré avec le contenu. Le test épingle maintenant dans son
code indépendant le commit source, le hash de l'enveloppe et celui du JSON.
La fixture n'a pas été réécrite après déplacement.
Le mode capture écrit seulement dans la destination scratch explicite, pas
automatiquement dans l'oracle committable.

## 9. Résultats, tests et commandes

| Vérification finale | Résultat observé |
|---|---|
| Huit fichiers ciblés | **115 passed**, 1 warning, 30,33 s |
| Suite SQLite entière | **371 passed**, 7 warnings, 83,67 s |
| Groupe canonique PostgreSQL | **95 passed**, 1 warning, 51,34 s : 56 + 39 |
| Pack avant/après | JSON complet égal, 560 268 octets, même SHA |
| AST de 14 modules | Égaux après seuls chemins d'import et référence documentaire de l'init pipeline |
| OpenAPI/metadata | Identiques octet pour octet à R0, 46 paths, 63 opérations, 17 tables |
| Alembic | Round-trip réussi ; seule différence FK technicien historique |
| Runtime | `/docs` et `/openapi.json` 200, startup/shutdown complets |

**371 = 360 R8 + 11 nouveaux cas** : 8 frontières/bootstrap, 1 replay du pack,
1 normalisation, 1 import historique sans appareil. Les premiers runs après
cutover, avant le dernier cas et les pins, comptaient 114 ciblés et 370 SQLite.
Ils ne sont pas additionnés aux comptes finaux.

La revue indépendante a vérifié les 14 AST, l'oracle décodé et ses limites,
les frontières et les contrats sensibles. Elle a rejoué **114 ciblés,
1 warning, 31,91 s**, avant les pins et le dernier cas historique.
Sa seule réserve, le gel cryptographique insuffisant, est corrigée par le
parent et validée dans la suite finale ; aucun écart métier/SQL/transactionnel
détecté. Elle n'a pas répété PostgreSQL ni la suite globale.

```text
python -m pytest <test_imports_module.py absolu avant move> -q -p no:cacheprovider
python -m pytest <8 fichiers ciblés absolus après move> -q -p no:cacheprovider
python -m pytest <backend/tests absolu> -q -p no:cacheprovider
python -m alembic -c <backend/alembic.ini absolu> upgrade head
python -m alembic -c <backend/alembic.ini absolu> downgrade -1
python -m alembic -c <backend/alembic.ini absolu> upgrade head
python -m alembic -c <backend/alembic.ini absolu> check
python -m pytest <5 fichiers PostgreSQL canoniques absolus> -q -p no:cacheprovider
python -m uvicorn app.main:app --host 127.0.0.1 --port <port libre>
git diff --check
```

Python 3.12.0 vient de l'interpréteur préexistant
`/home/lob/workspace/python/fastapi/Tervo/backend/.venv/bin/python`.
PYTHONPATH pointe les sources **du worktree attaché**, pas le checkout
principal. Cwd, SQLite et uploads sont temporaires, variables TERVO_* retirées
pour SQLite, timeout pytest 240 s.

PostgreSQL 17.4 a été démarré depuis l'image locale `--pull never`, port
loopback éphémère, sans volume nommé. Le parent a exécuté les cinq fichiers
canoniques : installations/ventes/migration Installation (56) et service/API
imports (39). Le conteneur et son volume anonyme ont été supprimés, aucun
conteneur ou base existante touché.

Alembic head reste `f102e0010001`, downgrade à `e103e0010001` puis reupgrade.
Check retourne 255 : remove_fk `intervention.technician_id → user.id` sans
ondelete SQL historique, add_fk avec `SET NULL` ORM. Une comparaison structurée
indépendante via `compare_metadata` confirme **exactement ces deux opérations**,
aucune nouvelle différence. Aucune migration générée.

Le runtime HTTP compare aussi son OpenAPI à R0. SIGTERM puis attente du
serveur donne `-15`, avec shutdown complet ; aucun serveur laissé actif.
Le golden replay complet est SQLite-only ; les 95 cas PostgreSQL ne sont pas
présentés comme une comparaison golden du pack sur PostgreSQL.

## 10. Suivi, documentation dépendante et crédibilité

Les notes INT-98 à INT-101 gardent leurs résultats historiques mais dirigent
vers les sources actuelles et cette note. Les todos TD-B015/TD-B016 pointent
vers le pipeline et l'orchestration déplacés. TD-B015 reste réalisé ; TD-B016
reste **ouvert** : un pack fictif de 30 lignes et un test de 502 lignes ne
mesurent pas vingt ans d'archives réelles.

Les données sources sont fictives, pas les archives d'un client.
Le différenciateur démontré est la chaîne de migration : mapping, normalisation,
matching multi-niveaux, validation humaine, plan figé, transactions, reprise
et audit. R9 ne prouve ni la performance sur un volume représentatif ni
la migration d'une base de production.

Le scan backend/frontend ne débloque pas les rôles TD-B013, les interfaces
TD-F007, le déploiement TD-B010 ou la reprise documentaire 7.4 TD-B018,
qui nécessite son scope autorisé distinct. R10 attend son propre feu vert.

Limites explicites :

- commit R9 autorisé après acceptation, R10 non autorisé/non commencé ;
- aucun push, CI distante Python 3.11, build Docker, déploiement ou seed ;
- aucune entité métier nouvelle, source modifiée, migration ou correction FK ;
- pas de mesure sur des archives réelles ou garantie de passage à l'échelle ;
- captures avant/après normalisées seulement sur les champs techniques listés ;
- dates métier non nulles et bail/token non nuls vérifiés par cas spécifiques,
  pas prétendus présents dans l'état final du pack ;
- produits et utilisateurs absents du pack : structures vérifiées par metadata,
  comportement catalogue import testé séparément dans les suites existantes.

### Acceptation et contrôle avant commit

L'utilisateur a demandé le nettoyage des dossiers vides et le commit R9, sans
feu vert R10. Les 28 empreintes sources/tests/fixtures sont conformes au
manifeste. Après retrait des caches et namespaces sans code actif dans le
worktree, les tests ont été rejoués avec le même interpréteur, un cwd et des
SQLite/uploads temporaires, bytecode et cache pytest désactivés :

- **115 passed, 1 warning, 34,32 s** sur les huit fichiers ciblés ;
- **371 passed, 7 warnings, 88,34 s** sur la suite SQLite complète.

L'oracle avant reste intact et le replay est inclus dans ces deux runs.
Les validations PostgreSQL précédentes ne sont pas présentées comme répétées.
Le commit R9 regroupe sa livraison uniquement ; la suppression des trois
init de namespaces devenus vides est isolée dans un commit de nettoyage.
Les captures JSON historiques ne sont pas réécrites.

Le commit R9 est `205969a`. Le [compte rendu du nettoyage](nettoyage-apres-R9.md#L1)
décrit les caches/dossiers retirés et les éléments protégés, sans anticiper
les derniers déplacements et la validation globale R10/R11.
