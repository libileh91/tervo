# Cours 04 — PostgreSQL, migrations, privilèges et sauvegardes

[Précédent](03-reseau-caddy-dockge.md) · [Sommaire](README.md) · [Suivant](05-release-rollback-entretien.md)

## Objectif

Comprendre pourquoi un déploiement ne se réduit pas à démarrer une API :
il faut préserver les données, faire évoluer leur structure et donner
les bons droits au bon processus. Les commandes pédagogiques sont des
exemples à adapter, **non exécutés pour écrire ce cours**.

Les observations réelles sont dans [le journal des releases](../../notes/backend/sprint7.6/INT-129/journal/02-releases-sauvegarde-rollback.md)
et [celui des garde-fous](../../notes/backend/sprint7.6/INT-129/journal/03-garde-fous-et-echecs.md).

## 1. Serveur, base, schéma, table et rôle

| Notion | Image mentale | Application à Tervo |
|---|---|---|
| Serveur PostgreSQL | Processus qui accepte les connexions et gère le stockage | Service Compose `postgres` |
| Base | Ensemble logique de données dans le serveur | `tervo_db` |
| Schéma SQL | Espace de noms dans une base | Principalement `public` |
| Table | Structure contenant des lignes | `client`, `site`, équipements, interventions, etc. |
| Rôle | Identité et privilèges SQL | `tervo_admin`, `tervo_app` |
| Schéma au sens migration | Structure globale : tables, colonnes, contraintes… | Évolution suivie par Alembic |

Le mot « schéma » a donc deux usages : namespace PostgreSQL et structure
de la base. Quand le helper compare le schéma avant rollback, il parle
de la structure exportée, complétée par la tête Alembic.

## 2. Initialiser n'est pas migrer

L'image PostgreSQL initialise un **nouveau** répertoire de données.
Les scripts de `/docker-entrypoint-initdb.d` servent lors de cette initialisation,
pas à chaque redémarrage.

Dans [init-app.sql](../postgres/init-app.sql#L1),
Tervo crée le rôle applicatif limité et prépare ses accès de base.
Une fois le volume rempli, redémarrer le conteneur ne rejoue pas ce script.

Conséquence pratique : changer `POSTGRES_PASSWORD` dans le `.env` ne modifie
pas automatiquement le mot de passe d'un rôle déjà existant. De même,
un script d'initialisation corrigé après un échec n'est pas automatiquement
rejoué sur un volume partiellement initialisé.

La première fixture locale a illustré ce piège : SQL illisible en mode 600,
serveur ensuite disponible, mais rôle applicatif absent. `pg_isready`
indiquait qu'un serveur répondait ; les grants ont révélé l'absence du rôle.
On a corrigé et recréé **uniquement la fixture autorisée**, pas prescrit
une réinitialisation d'une vraie base.

## 3. Séparer administration et fonctionnement quotidien

```text
tervo_admin → initialisation, migrations, grants
tervo_app   → requêtes métier du backend
```

Pourquoi ? Une API exposée peut contenir des erreurs. Son compte DB ne
doit pas pouvoir tout administrer par défaut.

| Besoin | Compte prévu |
|---|---|
| Créer/faire évoluer les tables | Administration/migration |
| Lire et modifier les lignes métier autorisées | Application |
| Modifier l'historique Alembic | Pas le compte de l'API |
| Créer des rôles ou des bases | Pas le compte de l'API |

Le [service migrate](../docker-compose.yml#L91) utilise
l'image backend, mais des identifiants administratifs. Le backend runtime
utilise le rôle applicatif. Il ne s'agit pas de deux applications métier.

Les mots de passe viennent de l'environnement privé. Sur une connexion
locale dans le conteneur, la méthode d'authentification peut différer de
la connexion réseau backend → PostgreSQL. Une commande `psql` root dans
le conteneur ne prouve donc pas à elle seule les privilèges du rôle API.

## 4. Une migration Alembic, étape par étape

Une migration versionnée décrit une évolution. Elle a notamment :

- un identifiant `revision` ;
- un ou plusieurs prédécesseurs `down_revision` ;
- une opération `upgrade()` ;
- éventuellement une opération inverse `downgrade()`.

La table `alembic_version` indique la révision appliquée. `alembic upgrade head`
cherche le chemin depuis l'état courant vers la tête connue du code.

### Commandes de migration — exemples contrôlés, pas à lancer maintenant

Préconditions : checkout propre choisi, image construite, DB prête,
maintenance autorisée et backup préalable si la base contient déjà des données.

```sh
CHECKOUT=/chemin/absolu/du/checkout
ENV_FILE="$CHECKOUT/deploy/.env"
PROJECT=projet_autorise
docker compose --env-file "$ENV_FILE" -p "$PROJECT" \
  -f "$CHECKOUT/deploy/docker-compose.yml" \
  run --rm -T --no-deps migrate
```

| Option | But | Retour attendu |
|---|---|---|
| `run` | Créer une exécution ponctuelle du service | Processus Alembic, pas API permanente |
| `--rm` | Retirer le conteneur ponctuel après usage | Ne supprime pas les volumes de données du projet |
| `-T` | Désactiver le pseudo-terminal | Adapté aux scripts et journaux non interactifs |
| `--no-deps` | Ne pas démarrer les dépendances implicitement | La DB doit déjà être prête |
| `migrate` | Service à commande Alembic, avec rôle admin | Code 0 si migration réussie ; erreur = ne pas démarrer le candidat HTTP |

Dans la recette, les migrations initiales ont atteint la tête
`m109e0010001`. L'upgrade de marqueurs A → B ne contenait pas de nouvelle
migration métier. Un test distinct a ajouté une migration qui levait une
erreur avant DDL pour contrôler le chemin d'échec.

PostgreSQL supporte beaucoup de DDL transactionnel ; cela ne permet pas
d'affirmer que **toute** migration possible sera automatiquement et totalement
annulée en cas d'erreur. Certaines opérations et certains choix de code
exigent des précautions particulières. Ne pas généraliser le test effectué.

## 5. Les grants après la migration

Créer une table ne suffit pas : l'application doit avoir les droits adaptés.
[app-grants.sql](../postgres/app-grants.sql#L1) accorde
SELECT/INSERT/UPDATE/DELETE sur les tables métier, les droits d'usage sur les
séquences, et exclut explicitement `alembic_version`.

```sh
docker compose --env-file "$ENV_FILE" -p "$PROJECT" \
  -f "$CHECKOUT/deploy/docker-compose.yml" exec -T postgres sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /opt/tervo/app-grants.sql'
```

Attendu illustratif : `BEGIN`, des `GRANT`, `REVOKE`, `COMMIT`, code 0.
Ces éléments ont réellement été reçus dans les journaux VPS.

| Élément | Sens |
|---|---|
| `exec -T postgres` | Exécuter dans le conteneur DB déjà démarré, sans terminal interactif |
| `sh -c '… "$POSTGRES_USER" …'` | Faire l'expansion dans le conteneur, pas dans le shell hôte |
| `ON_ERROR_STOP=1` | Faire échouer psql en cas d'erreur SQL, au lieu de continuer le fichier |
| `-f` | Lire le script SQL monté depuis la source versionnée |
| `COMMIT` | Fin réussie de la transaction de grants |

Si les grants échouent, « PostgreSQL healthy » ne rend pas la release valide.
Il faut diagnostiquer le rôle, la base, le script et les permissions.

## 6. Migration, bootstrap et seed : trois opérations différentes

| Opération | Ce qu'elle fait | Ce qu'il ne faut pas confondre |
|---|---|---|
| Migration | Fait évoluer la structure | Ne crée pas nécessairement un utilisateur métier |
| Bootstrap admin | Crée de façon contrôlée le premier administrateur | Pas une réinitialisation de données |
| Seed de démonstration | Charge des données d'exemple, potentiellement destructives | Pas une procédure de production |

Tervo possède [un bootstrap séparé](../../backend/app/bootstrap_admin.py#L1).
La note [INT-126](../../notes/backend/sprint7.6/INT-126-bootstrap-admin.md) détaille ses protections.
Aucun admin production VPS n'a été créé par les recettes INT-129.
Un endpoint readiness 200 n'est donc pas une preuve de login métier.

## 7. Sauvegarder : quels éléments doivent aller ensemble ?

Sauvegarder seulement la DB serait insuffisant si elle référence des photos
sur disque. Sauvegarder seulement les fichiers ne conserve pas leurs relations.
Il faut également pouvoir reconstruire la configuration nécessaire au service.

| Élément du bundle | Pourquoi |
|---|---|
| Dump PostgreSQL | Données et structures SQL |
| Archive uploads | Octets des fichiers référencés par l'application |
| Env privé | Paramètres nécessaires à la reconstruction |
| Paramètres/état Caddy et Dockge | Reconstituer les services hôte et leur administration |
| Manifeste/checksums et projet source | Vérifier l'intégrité et l'origine attendue |

Les formats et commandes complets sont dans la
[procédure INT-128](../../notes/backend/sprint7.6/INT-128-sauvegarde-restauration.md).
Le point important n'est pas le nom du script : c'est la **cohérence de la capture**.

### Pourquoi arrêter les écritures ?

Supposons :

1. la DB est exportée ;
2. un utilisateur ajoute ou supprime une photo ;
3. les fichiers sont archivés.

Les deux captures peuvent décrire deux états incompatibles. La procédure
met donc les écritures en pause et prend un verrou partagé. Ce verrou ne
bloque que les outils qui l'utilisent ; il ne remplace pas la discipline
d'administration ni un contrôle d'accès.

Dans la release, HTTP est arrêté avant la capture. Dockge est déjà gelé ;
la capture pilote aussi Caddy selon son état initial. L'autorisation
`--maintenance-confirmed` reste une confirmation humaine, pas une barrière
magique contre tous les accès SQL externes.

## 8. Lire un dump et une archive sans confondre sauvegarde et restauration

`pg_dump --format=custom` produit un dump utilisable par `pg_restore`.
Une archive tar regroupe les fichiers. SHA-256 sert ici à détecter une
corruption ou une incohérence par rapport au manifeste attendu.

### Vérification d'un bundle privé existant — exemple à adapter

```sh
CHECKOUT=/chemin/absolu/du/checkout
BUNDLE=/chemin/prive/hors-git/before-migration.tar
python3 "$CHECKOUT/deploy/scripts/snapshot.py" verify --bundle "$BUNDLE"
stat -c 'permissions=%a octets=%s' "$BUNDLE"
```

Attendu : code 0, `Bundle checksums valid.`, fichier privé non vide.
Observation VPS réelle : **600, 204 800 octets**. En cas de refus, conserver
le fichier pour diagnostic privé ; ne pas fabriquer un manifeste pour
« réparer » la preuve.

Ce contrôle ne prouve pas :

- qu'un administrateur saura restaurer le service complet ;
- que le backup survivra à la perte du VPS ;
- que les données représentent vingt ans d'activité ;
- que le dump est chiffré.

Dans cette recette le tar local est protégé par les permissions, pas par
un chiffrement ajouté par `verify`. INT-128 prépare aussi restic et une
destination mini-s1, mais aucune copie régulière réelle ni timer actif
n'est déduite des tests INT-129.

## 9. Restaurer demande une autre décision

Un rollback applicatif remplace du code. Une restauration DB remplace
ou réimporte des données. Cela peut perdre les écritures plus récentes
que le backup : ce n'est pas une action automatique anodine.

La preuve de restauration doit se faire sur une destination isolée,
avec vérification des relations, fichiers et paramètres, avant toute
substitution d'une source réelle. Le restore isolé INT-128 a utilisé des
données fictives, dont une photo et un PDF BYTEA ; il ne prouve pas la
restauration des vrais services hôte à partir du bundle VPS actuel.

**RPO** : quantité de données qu'on accepte potentiellement de perdre,
souvent exprimée en temps depuis la dernière sauvegarde exploitable.
**RTO** : délai de remise en service visé. Ce sont des objectifs à mesurer,
pas des propriétés garanties par l'existence d'un fichier tar.

## 10. Questions d'entretien et exercices

**Pourquoi un rôle de migration différent du rôle API ?**

Les privilèges nécessaires à l'évolution du schéma sont plus larges que
ceux des requêtes métier. La séparation limite les capacités de l'API,
même si elle ne constitue pas à elle seule toute la sécurité de la base.

**Pourquoi ne pas faire un downgrade automatique quand B échoue ?**

Une évolution inverse peut être destructive ou ne pas restaurer les données.
Le parcours validé compare schéma/tête et préfère refuser un retour risqué.

**Pourquoi le backup comprend-il les uploads ?**

Parce que la cohérence métier traverse la DB et le filesystem. Un dump
SQL sans les octets des photos ne suffit pas à restituer ces références.

Exercices sans mutation :

1. `pg_isready` réussit mais les grants disent « rôle absent » : contradiction ?
2. Changer le `.env` suffit-il à changer un mot de passe SQL existant ?
3. Un checksum valide prouve-t-il que le backup est chiffré et restaurable ?

Réponses : 1. Non, disponibilité du serveur et initialisation applicative
sont distinctes. 2. Non, il faut une opération SQL contrôlée.
3. Non, intégrité, confidentialité et restauration sont trois propriétés.
