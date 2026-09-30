# R0 — Baseline vérifiée avant le refactor modulaire

> Chantier technique transverse, indépendant des évolutions métier de Sprint 7.4.
> Référence : [plan du refactor](../tervo_plan_refactor_monolithe_modulaire.md).
> État : R0 validé par l'utilisateur ; branche `refactor/modular-monolith` créée et R1 autorisé. L'écart FK technicien est conservé sans correction. Les artefacts JSON restent ceux de la capture initiale, sans réécriture.

## 1. Pourquoi commencer par une baseline ?

Le refactor doit changer les packages Python, pas les contrats HTTP, le modèle SQL ou les règles métier. Sans mesure initiale, un défaut découvert après un déplacement pourrait être attribué à tort au refactor.

Trois références complémentaires sont donc conservées :

- **Git** : le contenu source avant déplacement ;
- **OpenAPI** : les routes et contrats publics annoncés par FastAPI ;
- **ORM et migrations PostgreSQL** : le chargement des modèles et le comportement du schéma migré.

Les tests fournissent une quatrième référence, comportementale. Une OpenAPI identique ne prouve pas à elle seule que les transactions ou les autorisations sont préservées.

## 2. État source et garde-fous

| Élément | Observation |
|---|---|
| Branche au démarrage | `main` |
| SHA | `544a23d6cb2cbe878fbc8ddf2d962c7adf76c000` |
| Référence distante locale | `origin/main` pointe sur le même SHA ; aucun fetch effectué |
| Modification préalable | Le plan fourni est non suivi par Git |
| Backend | Organisation horizontale encore en place |
| Chaîne commerciale | `Sale`, `SaleLine` et `Installation` présents |
| Révision Alembic head | `f102e0010001` |

Aucun commit, tag, changement de branche, push ou réécriture d'historique n'a été effectué. Aucun fichier applicatif, test existant ou migration n'a été modifié. Les fichiers ajoutés sont uniquement les preuves et cette note.

Les bases `backend/tervo.db` et `backend/test_tervo.db` ne servent pas à ces vérifications. Les conteneurs applicatifs et le PostgreSQL existants ne sont ni migrés ni redémarrés.

## 3. Isolation des vérifications

### SQLite : attention au répertoire courant

Certains tests historiques utilisent cette URL relative :

```python
TEST_DB_URL = "sqlite+aiosqlite:///./test_tervo.db"
```

Leurs fixtures exécutent `create_all()` puis `drop_all()`. Lancer ces tests dans le dossier backend ferait donc travailler la suite sur le fichier local portant ce nom.

L'exécution R0 utilise à la place un répertoire courant temporaire, avec :

- l'interpréteur déjà installé dans `backend/.venv/bin/python` ;
- `PYTHONPATH` pointant sur le backend source ;
- `DATABASE_URL=sqlite:///./tervo.db`, donc temporaire lui aussi ;
- `UPLOAD_DIR` dans le répertoire temporaire ;
- les variables de test PostgreSQL retirées de l'environnement de la première suite ;
- le plugin cache de pytest désactivé pour cette exécution.

La logique d'isolation exécutée correspond à :

```python
with tempfile.TemporaryDirectory(prefix="tervo-r0-tests-") as work:
    env["PYTHONPATH"] = str(backend)
    env["DATABASE_URL"] = "sqlite:///./tervo.db"
    env["UPLOAD_DIR"] = str(Path(work) / "uploads")
    result = subprocess.run(
        [str(backend / ".venv/bin/python"), "-m", "pytest",
         str(backend / "tests"), "-q", "-p", "no:cacheprovider"],
        cwd=work,
        env=env,
        timeout=180,
    )
```

Il s'agit d'un extrait représentatif de l'enveloppe Python exécutée via le terminal, pas d'un nouveau script livré au backend. Les tests et leurs fixtures restent inchangés.

### PostgreSQL : un serveur dédié et jetable

L'image `postgres:17.4` déjà disponible a été utilisée avec `--pull never` : aucun téléchargement d'image requis. Commande exécutée :

```sh
docker run --detach --pull never \
  --name tervo-refactor-r0-postgres \
  --publish 127.0.0.1::5432 \
  --env POSTGRES_USER=tervo_ci \
  --env POSTGRES_PASSWORD=local-ci-only \
  --env POSTGRES_DB=tervo_ci \
  postgres:17.4

docker port tervo-refactor-r0-postgres 5432
```

Docker a attribué le port local `32768` pour ce run. Ces identifiants sont des valeurs de test jetables, pas des secrets du projet. Aucun volume nommé n'a été attaché.

Le serveur a annoncé `17.4 (Debian 17.4-1.pgdg120+2)`. Les tests récents créent leurs propres schémas aléatoires et les suppriment en teardown. Le serveur lui-même a ensuite été supprimé dans un bloc `finally` :

```sh
docker rm --force tervo-refactor-r0-postgres
```

Un contrôle final de `docker ps` ne retrouve plus ce conteneur.

## 4. Commandes applicatives et résultats observés

Les commandes ci-dessous indiquent les opérations réellement exécutées par les sous-processus Python. Leurs chemins backend/tests/config étaient absolus, puisque le répertoire courant était temporaire. Aucune installation de dépendances n'a été nécessaire ; `uv sync` n'a pas été exécuté.

| Vérification | Commande du sous-processus | Résultat |
|---|---|---|
| Suite complète SQLite | `python -m pytest tests/ -q -p no:cacheprovider` | **271 passed**, 5 warnings, 32,94 s |
| PostgreSQL depuis une base neuve | `python -m alembic -c alembic.ini upgrade head` | Réussite jusqu'à `f102e0010001` |
| Retour dernière révision PostgreSQL | `python -m alembic -c alembic.ini downgrade -1` | Réussite vers `e103e0010001` |
| Réapplication PostgreSQL | `python -m alembic -c alembic.ini upgrade head` | Réussite |
| Comparaison schéma migré / ORM | `python -m alembic -c alembic.ini check` | **Échec préexistant**, FK technicien, détaillé ci-dessous |
| APIs/transactions/migrations PostgreSQL | `python -m pytest tests/test_installations.py tests/test_sales.py tests/test_installation_migration.py -q -p no:cacheprovider` | **56 passed**, 1 warning, 22,53 s |
| Imports PostgreSQL | `python -m pytest tests/test_import_service_v2.py tests/test_import_api_v2.py -q -p no:cacheprovider` | **39 passed**, 1 warning, 22,62 s |
| Chaîne complète sur SQLite neuve | `python -m alembic -c alembic.ini upgrade head` | **Échec préexistant**, instruction PostgreSQL `ALTER TYPE` |

Les groupes PostgreSQL ont utilisé les variables prévues par les tests :

```text
TERVO_INSTALLATION_TEST_DATABASE_URL    → PostgreSQL / asyncpg
TERVO_SALE_TEST_DATABASE_URL            → PostgreSQL / asyncpg
TERVO_INSTALLATION_MIGRATION_TEST_URL   → PostgreSQL / psycopg2
TERVO_IMPORT_TEST_DATABASE_URL          → PostgreSQL / asyncpg
```

Pour les commandes Alembic, `DATABASE_URL` pointait sur le serveur jetable avec le driver synchrone. Pour pytest, `DATABASE_URL` restait SQLite temporaire : seules les variables ci-dessus sélectionnaient les connexions PostgreSQL des fixtures concernées.

Ces groupes reprennent le périmètre PostgreSQL de la CI, mais il s'agit d'exécutions **locales**, pas d'une preuve de run GitHub Actions ni d'un déploiement. Les 95 tests PostgreSQL sont des réexécutions ciblées de tests de la suite, pas 95 nouveaux tests ajoutés.

Environnement effectif : Python **3.12.0**, FastAPI **0.138.0**, SQLAlchemy **2.0.51**, Alembic **1.18.4**, pytest **9.1.1**. Les autres versions sont enregistrées dans le manifeste. La CI configure Python 3.11 ; R0 ne prouve donc pas une exécution sur cet interpréteur.

## 5. Les deux écarts de départ à ne pas masquer

### 5.1 L'historique Alembic complet n'est pas portable sur SQLite

Sur une SQLite neuve, les migrations atteignent `9d34b52092ce_rename_job_to_intervention.py`, puis échouent sur :

```sql
ALTER TYPE jobstatus RENAME TO interventionstatus
```

Erreur observée : `sqlite3.OperationalError: near "TYPE": syntax error`.

Ce n'est pas l'ancien incident « table user déjà présente » de la base locale : le run R0 part bien d'une base vide. La suite SQLite teste certaines révisions isolément ou reconstruit un schéma antérieur ; sa réussite ne signifie donc pas que toute la chaîne Alembic est compatible SQLite.

**Décision R0 :** ne pas réécrire les migrations pour rendre SQLite équivalent à PostgreSQL. La chaîne complète a été vérifiée sur PostgreSQL 17.4.

### 5.2 La FK technicien diffère déjà entre ORM et migrations

Le modèle courant contient :

```python
technician_id = Column(
    Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
)
```

Mais `5cc5d1686947_add_job_table.py` crée la FK sans `ondelete`. La révision suivante `7e7c3408ecfb` est un `pass` : une déclaration ORM ne modifie pas rétroactivement une contrainte SQL déjà créée. Le renommage `job → intervention` conserve cette contrainte historique.

`alembic check` constate donc deux opérations proposées :

```text
remove_fk : intervention.technician_id → user.id
            contrainte SQL existante job_technician_id_fkey
add_fk    : même relation, avec ondelete='SET NULL' selon l'ORM
```

**Décision R0 :** aucune migration générée, aucun correctif métier caché. Le déplacement doit préserver les modèles ET les migrations tels qu'ils sont. Les futurs contrôles devront distinguer cette différence connue d'une nouvelle régression. On ne peut pas annoncer « Alembic sans aucune diff » comme acquis à la baseline.

Si l'on exige un `alembic check` strictement vert avant R1, cet écart doit faire l'objet d'un correctif séparé et explicitement validé.

Les warnings de la suite concernent `crypt` dans passlib et `datetime.utcnow()` dans le service d'intervention. Ils n'ont pas été corrigés pendant R0.

## 6. Démarrage réel de FastAPI et référence HTTP

Un processus Uvicorn a été lancé depuis l'interpréteur du backend, sur `127.0.0.1` avec un port libre, une SQLite et un dossier uploads temporaires. Le processus a été terminé puis attendu après les contrôles ; aucun serveur de vérification n'est laissé actif.

Résultats :

- startup ASGI exécuté sans erreur ;
- `GET /openapi.json` → **200** ;
- `GET /docs` → **200** ;
- OpenAPI servie par HTTP égale à celle de `app.openapi()` ;
- shutdown ASGI exécuté sans erreur.

La référence HTTP comprend **46 chemins** et **63 opérations**. Le registre ORM actuel comprend **17 tables**, et `configure_mappers()` a réussi. Ce contrôle vérifie notamment que les relations SQLAlchemy trouvent actuellement leurs modèles cibles.

Il ne valide pas toutes les connexions métier au démarrage : le lifespan crée/dispose l'engine sans imposer une requête SQL. Les connexions sont effectivement exercées par les tests.

## 7. Fichiers de preuve et utilisation future

| Fichier | Rôle |
|---|---|
| [R0-baseline.json](R0-baseline.json) | SHA source, résultats synthétiques, versions, SHA-256 des artefacts et des fixtures d'import |
| [R0-openapi.json](R0-openapi.json) | Document public de référence, sérialisé de manière déterministe |
| [R0-metadata.json](R0-metadata.json) | Instantané ORM : colonnes, types compilés PostgreSQL, nullabilité, PK, server defaults, contraintes et FK |
| [R0-postgresql-results.json](R0-postgresql-results.json) | Codes de retour et sorties des commandes Alembic et groupes PostgreSQL |

`R0-metadata.json` est un instantané des déclarations ORM, **pas un dump du schéma PostgreSQL migré**. Il ne couvre pas tous les détails possibles : index, séquences, valeurs des enums natifs et defaults Python nécessitent aussi des vérifications ciblées. Il ne remplace ni les migrations, ni `alembic check`, ni les tests de contraintes.

Les fichiers du pack `backend/tests/fixtures/excel/` ont leurs empreintes conservées pour que R9 réutilise exactement les mêmes sources. Les tests d'import actuels sont verts avant déplacement. La comparaison complète des journaux et entités avant/après recommandée par R9 n'est pas encore implémentée : les empreintes seules ne prouvent pas l'identité des résultats d'import.

Ne pas remplacer ces fichiers par les sorties « après refactor » : produire un autre instantané puis le comparer à R0.

## 8. Préparation de R1 et décisions validées

L'audit en lecture seule du DAT, du planning et du code ne révèle pas de frontière métier incompatible avec le plan. Points importants pour la suite :

1. Une **Base SQLAlchemy unique**, dans un module technique ne chargeant pas les domaines, évitera les cycles au moment du premier déplacement. L'ancien `app.models.__init__` charge actuellement tous les modèles.
2. Le registre doit inclure les **17 modèles présents**, y compris checklist, photos, matériel et avis ; l'exemple du plan est indicatif, pas exhaustif.
3. Les accès transverses actuels des clients/sites vers les domaines aval doivent être conservés ou explicitement cadrés, pas réécrits silencieusement pour imposer un graphe théorique.
4. La transaction installation/équipement et les transactions par sous-lot d'import gardent leur propriétaire et leurs commits actuels.
5. Le déplacement du template de rapport devra adapter son chemin de chargement.

Proposition validée par l'utilisateur après les vérifications R0 :

- branche : `refactor/modular-monolith` ;
- planning technique : `docs/stages/stage7/refactor-monolithe-modulaire/`, séparé des six sprints fonctionnels ;
- `INT-113` à `INT-123` attribués à R1 à R11 dans le [planning technique](../../../../docs/stages/stage7/refactor-monolithe-modulaire/README.md) ;
- R0 reste ce checkpoint documentaire ;
- pour la FK technicien : conserver l'écart connu pendant le refactor, sans correctif SQL dans les déplacements.

## 9. Checklist de sortie R0

- [x] SHA post-réécriture connu et enregistré.
- [x] Suite backend complète mesurée.
- [x] Groupes PostgreSQL applicables exécutés sur serveur jetable 17.4.
- [x] Chaîne complète Alembic PostgreSQL et aller-retour dernière révision vérifiés.
- [x] Démarrage/arrêt réel FastAPI et documentation HTTP vérifiés.
- [x] Références OpenAPI, ORM et fixtures sauvegardées.
- [x] Écarts initiaux documentés sans modification métier.
- [x] Conteneur de test et processus Uvicorn nettoyés.
- [x] Branche dédiée créée après accord utilisateur.
- [x] Choix explicite concernant la différence préexistante d'`alembic check` : conservation sans correction.
- [x] Validation utilisateur de R0 et feu vert R1.

**R0 est clôturé. Le feu vert R1 n'autorise pas R2 et les vagues suivantes.**
