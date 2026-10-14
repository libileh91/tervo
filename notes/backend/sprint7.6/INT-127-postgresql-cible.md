# INT-127 — PostgreSQL cible et départ sans reprise locale

## Décision et périmètre

L'utilisateur déclare les données locales obsolètes : **VPS avec une base
vide**, sans import du mini-s1. Après validation du VPS, sa nouvelle base
devra remplacer la base locale. Ce remplacement reste différé : préciser
la cible locale, sauvegarder son état et valider la restauration (INT-128)
avant de l'appliquer en fin d'INT-111.

Cette tâche prépare et teste la cible **sur Docker local jetable**. Elle
ne crée aucune DB sur le VPS, ne renomme aucun compte Linux et ne touche
pas à une base existante. Compte Linux cible demandé : `lb11` ; l'accès
SSH précédemment observé utilisait `tervo`, transition non effectuée.

## Une instance, deux rôles SQL

| Élément | Choix |
|---|---|
| Base | `tervo_db` |
| Initialisation et migrations | `tervo_admin` : superuser de l'image officielle, réservé à l'administration |
| API et bootstrap du premier compte | `tervo_app` : login, CONNECT, USAGE du schéma, CRUD des tables métier et USAGE des séquences |
| Données | Volume Compose `postgres_data`, PGDATA `/var/lib/postgresql/data/pgdata` |

Le rôle API n'est ni superuser, ni créateur de bases/rôles, ni réplicateur.
Il ne peut pas créer de table, faire un TRUNCATE, se placer sous le rôle admin
ou modifier `alembic_version`. Deux identifiants suffisent ici ; le rôle de
migration reste **administratif**, pas présenté comme un migrateur à droits
DDL finement restreints.

Les secrets sont distincts et privés :
`TERVO_DB_ADMIN_USER/PASSWORD` pour PostgreSQL et la commande `migrate`,
`TERVO_DB_USER/PASSWORD` pour l'API. Les secrets admin ne sont pas injectés
dans le backend actif. Le validateur refuse rôle commun, noms invalides,
secrets courts/identiques, exports ambiants et fichier env non privé.

## Version et initialisation

PostgreSQL **17.11** remplace le patch 17.7 de la recette historique INT-125.
La [politique officielle](https://www.postgresql.org/support/versioning/)
indique 17.11 comme patch courant de la majeure 17, supportée jusqu'en novembre
2029. L'index OCI officiel a été contrôlé avec
`docker buildx imagetools inspect postgres:17.11`, puis épinglé dans le Compose :

```text
sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
```

`deploy/postgres/init-app.sql` crée le rôle API seulement au premier démarrage
d'un **volume neuf**. Les valeurs sensibles viennent de `\getenv` dans psql,
pas de mots de passe copiés dans le SQL ou dans les arguments de commande.
Le script ne supprime rien et n'altère pas un rôle existant.

**Un nouveau POSTGRES_USER/PASSWORD ne modifie pas un volume initialisé.**
Avant la release réelle, inventorier les volumes du projet choisi. Si un
volume existe déjà, arrêter et l'examiner : pas de `down -v`, purge ou
réinitialisation pour forcer le scénario « base vide ».

## Migrations puis droits applicatifs

Le service ponctuel `migrate` utilise la même image backend sous le profil
`tools`, avec les seuls identifiants SQL administratifs substitués. Il ne
démarre pas lors du `up` normal et ne publie aucun port.

Après chaque migration réussie, `app-grants.sql` attribue les droits sur les
tables métier et séquences. Il exclut explicitement `alembic_version`. Pas de
droits par défaut sur toutes les tables : une nouvelle table n'est accessible
à l'API qu'après cette étape de grants.

Ordre à intégrer dans INT-129 **avant exposition applicative** :

```bash
# Préconditions : image construite, DB prête, env privé explicite et projet contrôlé.
docker compose --env-file CHEMIN_PRIVE -f deploy/docker-compose.yml run --rm --no-deps migrate
docker compose --env-file CHEMIN_PRIVE -f deploy/docker-compose.yml exec -T postgres \
  sh -c 'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /opt/tervo/app-grants.sql'
```

Ce sont les étapes SQL, **pas encore une procédure de production complète**.
En cas d'échec, ne pas exposer l'API ; garder le volume et diagnostiquer.
Pas de transfert source ni de rollback destructif dans INT-127.

### Comprendre et contrôler ces étapes

Les commandes ci-dessus partent de la **racine du dépôt sur l'hôte Docker
ciblé** ; `CHEMIN_PRIVE` est à remplacer par le chemin du fichier env validé.
Le projet et ses volumes doivent être identifiés avant toute écriture.
`run --rm --no-deps migrate` crée un conteneur ponctuel puis le retire,
sans démarrer PostgreSQL à sa place : la DB doit déjà être prête.
Il exécute `alembic upgrade head` avec le rôle admin. Code 0 attendu avant
les grants. `exec -T postgres` lance ensuite psql sans TTY ; les variables
entre apostrophes sont résolues **dans le conteneur**, pas sur l'hôte.
`ON_ERROR_STOP=1` arrête psql à la première erreur ; `-f` applique le fichier
versionné de droits. Un succès ne prouve ni bootstrap ni restauration.

Contrôle SQL lisible, sans modification, avec les mêmes préconditions :

```bash
docker compose --env-file CHEMIN_PRIVE -f deploy/docker-compose.yml exec -T postgres \
  sh -c 'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SHOW server_version;
SELECT current_database(), current_user;
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication
FROM pg_roles WHERE rolname IN ('tervo_admin', 'tervo_app');
SELECT version_num FROM public.alembic_version;
SELECT has_table_privilege('tervo_app', 'public.alembic_version', 'UPDATE')
  AS api_peut_modifier_version;
SQL
```

Pour les noms retenus ici, attendre PostgreSQL 17.11, `tervo_db`,
`tervo_admin`, les quatre flags faux pour `tervo_app`, la tête Alembic de
l'image testée et `false` au dernier contrôle. Cela lit sous admin : ce
n'est pas une preuve de connexion avec le secret API ni de tous ses droits.
Si une valeur diverge ou si une table manque, conserver la sortie non sensible
et examiner cible, migrations et grants ; ne pas purger le volume.
Ces commandes explicitent les contrôles, elles n'ont pas été rejouées sur VPS.

## Recette observée

La recette existante `deploy/check-stack.py --revision OBJET_GIT` a été adaptée,
sans créer un second harness. Elle utilise des secrets fictifs privés, un
projet UUID et uniquement ses volumes jetables :

- validation env, absence de port PostgreSQL et loopback des services HTTP ;
- version SQL 17.11, admin réel et flags du rôle API ;
- chaîne Alembic complète sous admin, puis grants et CRUD/séquences sous API ;
- refus DDL, TRUNCATE, CREATE ROLE, SET ROLE admin et modification de version ;
- donnée fictive préservée après recréation du conteneur PostgreSQL avec son volume ;
- non-régression readiness/panne/reprise DB, frontend, CORS, PDF et uploads ;
- nettoyage des conteneurs, réseaux, volumes et images propres à cette recette.

Les objets Git testés et résultats sont enregistrés dans le cas
`TC-INT-127-01`. Dernière commande réussie :

```bash
PYTHONDONTWRITEBYTECODE=1 python3 deploy/check-stack.py \
  --revision a7228a1ff2ce8e14e621cab102d7ea4a8bc45542
```

Ce SHA désigne un arbre Git de recette, pas une release de production.
`uv run pytest tests/test_production_config.py tests/test_bootstrap_admin.py -q`
a aussi donné **9 tests réussis** ; aucune suite backend complète revendiquée.
Aucune version, santé, migration, permission ou restauration
**sur le VPS** n'est déduite de cette recette locale. TD-B008/009 restent à
recontrôler lors de la création réelle ; TD-B010 suit désormais le remplacement
local final, pas un import d'anciennes données.
