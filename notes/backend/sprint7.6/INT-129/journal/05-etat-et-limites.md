# Journal 05 — État final connu, historique local et limites

[Sommaire](../README.md) · [Gate Dockge](04-gate-dockge.md)

## Ce qui est terminé

Les commandes et résultats VPS des pages 01 à 04 couvrent :

| Preuve | État |
|---|---|
| Première release A avec record automatique | Réussie |
| Upgrade B et vraie capture préalable | Réussis |
| Vérification du bundle, 204 800 octets en 600 | Réussie |
| Rollback exact A sans restauration de DB | Réussi |
| Client fictif et upload conservés | Vérifiés après rollback puis UI |
| Refus sous verrou tenu et sur schéma différent | Réussis |
| Échecs build, migration, readiness et smoke | Codes d'échec contrôlés ; secours automatique quand applicable |
| Réconciliation Git/env avant reprise de la console | Réussie |
| Comparaison CLI/Dockge, omission JSON qualifiée, logs et Stop/Start UI | Réussis |

À la fin du gate, avant nettoyage, l'état fourni était A healthy, Caddy actif
et Dockge healthy, sur la branche `recette-a-reconciliee`. Les candidats,
images de secours et bundles privés étaient encore présents à ce stade.

## Nettoyage : déclaration opérateur et limites de preuve

**L'utilisateur déclare avoir exécuté le bloc final.** Il confirme ensuite
Dockge « active & green » puis le résultat attendu du contrôle Caddy.
La sortie détaillée du nettoyage n'a pas été fournie : pas de capture des
tags retirés, du déplacement de source ou des listes Docker filtrées.
La clôture repose sur ce retour opérateur, pas sur une inspection indépendante.

Il était prévu de :

1. supprimer seulement les conteneurs/réseaux/volumes de
   `int129-vps-33c350b23010` ;
2. retirer uniquement les tags d'images de cette recette, sans prune global ;
3. conserver les sources/état privés hors du dossier scanné par Dockge ;
4. vérifier l'absence des ressources de recette et la présence de Caddy/Dockge.

Le récapitulatif ci-dessus n'est **pas** un ordre de suppression à exécuter.
Le bloc de clôture archivé ci-dessous ne doit pas être rejoué.
Les bundles contiennent de vrais paramètres hôte ; leur traitement doit
rester explicite. Le nettoyage de la petite sonde `int129-bind-a732f9e4dd02`
est, lui, confirmé dans le journal 04.

La livraison regroupe le code, les résultats et la documentation dans le commit
INT-129. Aucun nouveau test de panne ou accès privilégié n'est présenté comme
réalisé par l'agent pour compléter cette confirmation.

### Reprise de clôture — accès SSH refusé

Depuis le poste de l'agent, contrôle en lecture seule :

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 \
  -o ControlPath=none tervo@151.241.228.152 'id; sudo -n true'
```

Résultat observé par l'outil, code 255 :

```text
tervo@151.241.228.152: Permission denied (publickey).
```

L'authentification a échoué avant les commandes distantes : aucun `id`, sudo
ou nettoyage n'a été exécuté sur le VPS. Cela ne permet pas de conclure à
l'état actuel de sudo ni à une expiration certaine de la clé. Renouveler
l'accès temporaire ou utiliser le terminal root opérateur déjà autorisé.

L'utilisateur a demandé une nouvelle tentative de la même commande. Cette
fois SSH a réussi, mais sudo non interactif a refusé, code global 1 :

```text
uid=1000(tervo) gid=1000(tervo) groups=1000(tervo),27(sudo),100(users)
sudo: a password is required
```

Aucun nettoyage distant n'a été exécuté par ces contrôles de l'agent.

### Bloc final — exécution déclarée par l'opérateur

Ce bloc était destiné **au shell root du VPS `22565`**, avec avertissement de
destruction des seuls volumes/données fictifs et refus d'un autre hôte,
d'une source modifiée ou d'une archive préexistante. Il est reproduit comme
commande envoyée ; ne pas le relancer sur une recette déjà nettoyée.

```sh
(
set -eu
umask 077
test "$(id -u)" -eq 0
test "$(hostname)" = 22565
exec 9>/run/lock/tervo-operations.lock
flock -n 9

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
STATE_DIR="/var/lib/tervo-int129/$PROJECT"
ENV_FILE="$CHECKOUT/deploy/.env"
ARCHIVE="$STATE_DIR/source-recette"

test ! -L "$CHECKOUT"
test "$(git -C "$CHECKOUT" rev-parse --show-toplevel)" = "$CHECKOUT"
test "$(git -C "$CHECKOUT" rev-parse HEAD)" = 9111a2a1ecbb010cf9033c7300ca49193d0fd34a
test -z "$(git -C "$CHECKOUT" status --porcelain)"
test -d "$STATE_DIR"
test "$(stat -c '%a' "$STATE_DIR")" = 700
test ! -e "$ARCHIVE"
test ! -L "$ARCHIVE"
grep -qxF 'FRONTEND_ORIGIN=https://recipe.invalid' "$ENV_FILE"
REVISIONS="$(git -C "$CHECKOUT" for-each-ref --format='%(objectname)' refs/heads/)"
test -n "$REVISIONS"

echo "1/3 : supprimer uniquement les ressources de la recette."
docker compose --env-file "$ENV_FILE" -p "$PROJECT" \
  -f "$CHECKOUT/deploy/docker-compose.yml" \
  down --volumes --remove-orphans

echo "2/3 : retirer les tags des images de cette recette, sans prune global."
for REV in $REVISIONS; do
  TAGS="$(docker image ls \
    --filter "label=org.opencontainers.image.revision=$REV" \
    --format '{{.Repository}}:{{.Tag}}')"
  for TAG in $TAGS; do
    case "$TAG" in
      tervo-backend:*|tervo-frontend:*) docker image rm "$TAG" ;;
    esac
  done
done

echo "3/3 : archiver la source hors Dockge et vérifier le nettoyage."
mv -- "$CHECKOUT" "$ARCHIVE"
test -z "$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT")"
test -z "$(docker network ls -q --filter "label=com.docker.compose.project=$PROJECT")"
test -z "$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")"
test ! -e "$CHECKOUT"
systemctl is-active caddy
docker ps -a --format '{{.Names}} | {{.Status}}'
printf 'Archives privées conservées : %s\n' "$STATE_DIR"
)
```

**Retour reçu : exécution déclarée, sortie détaillée non consignée.**
L'utilisateur a écrit « j'ai executé le bloc », puis confirmé Dockge actif/
vert. Ne pas reconstruire un journal `Removed`, `Untagged` ou `Archives privées
conservées` comme s'il avait été collé. Le code global du bloc n'a pas été
fourni. Les assertions étaient conçues pour rester silencieuses en cas de succès.

### Contrôle Caddy demandé ensuite

Commandes envoyées pour le terminal VPS, en lecture seule :

```sh
systemctl is-active caddy

curl --noproxy '*' --fail --silent --show-error \
  --write-out '\nHTTP %{http_code}\n' \
  http://127.0.0.1/
```

Le résultat attendu communiqué était `active`, `INT-131 bootstrap OK` et
`HTTP 200`. L'utilisateur a répondu « yes same result vu » : ces valeurs
sont donc **confirmées par lui, sans collage brut du terminal**.

| Commande / option | But | Interprétation du retour |
|---|---|---|
| `systemctl is-active caddy` | Lire l'état du service | `active` confirmé |
| `curl http://127.0.0.1/` | Vérifier le bootstrap HTTP local | Marqueur `INT-131 bootstrap OK` et 200 confirmés |
| `--noproxy '*'` | Ne pas passer par un proxy ambiant | Le test cible bien le loopback du VPS |
| `--fail --silent --show-error` | Échouer sur erreur HTTP, sans progression, en gardant les erreurs | Pas une preuve de TLS ou d'accès public Tervo |
| `--write-out` | Ajouter le code HTTP au retour | Aucun certificat HTTPS validé par ce contrôle HTTP |

### Interprétation des commandes du bloc de nettoyage

| Commande / contrôle | But | Limite de sécurité |
|---|---|---|
| `exec 9>…`, `flock -n 9` | Tenir le verrou partagé release/backup jusqu'à la fin du bloc | Refus si une opération coopérante est en cours ; fermer aussi les opérations UI |
| UID, hostname, racine Git, SHA, checkout propre | Vérifier la bonne copie de recette avant toute suppression | Un refus laisse le bloc arrêté avant les mutations |
| Mode 700, archive absente, origine `.invalid` | Préserver l'état privé et éviter un écrasement ou une cible devenue production | Aucun contenu secret n'est affiché |
| `down --volumes --remove-orphans` avec `-p` explicite | Supprimer conteneurs, réseaux, volumes et auxiliaires du seul projet | Destruction des données fictives ; pas des services/dossiers Caddy/Dockge |
| SHA des branches + label VCS + préfixes des deux images | Retirer seulement les tags rattachés à cette copie Git | Pas de prune global, pas de suppression forcée ; images de base et caches conservés |
| `mv` vers `$STATE_DIR/source-recette` | Sortir les sources/env de la zone scannée par Dockge sans les effacer | Les bundles et historiques privés restent sur le VPS |
| Lectures Docker filtrées et état Caddy/Dockge | Vérifier le résultat du nettoyage | Ce n'est pas une nouvelle recette fonctionnelle |

Le bloc prévoit de conserver les traces privées mais de retirer les images
et déplacer les sources : les records ne doivent donc pas être présentés
comme un secours applicatif immédiatement exploitable après nettoyage.
Leur conservation et le chemin d'archive n'ont pas fait l'objet d'un retour
terminal détaillé. Aucun de ces éléments ne vaut mise en production ou
preuve de restauration du VPS.

## Historique local antérieur — preuve résumée, pas transcript inventé

Les preuves locales antérieures ont été conservées dans la note initiale et
dans [les cas JSON](../../../../../docs/stages/stage7/sprint7.6/test-cases.json).
La version initiale committée peut être relue depuis la racine du dépôt,
sans changer les fichiers ni la branche :

```sh
git show cf3a772:notes/backend/sprint7.6/INT-129-release-rollback.md
```

C'est une commande de consultation proposée au lecteur, pas une étape de
recette VPS. Attendu : ancien Markdown sur stdout, code 0. Cette version est
antérieure aux preuves VPS ; ce n'est pas la procédure actuelle.
Les pages 01 à 04 reproduisent les blocs VPS et retours opérateur de cette
conversation ; elles ne prétendent pas reconstruire chaque ligne manquante
d'un ancien terminal local ou du contexte précédent.

| Recette locale | Résultat réellement consigné | Limite |
|---|---|---|
| `int129-16f2d470527c46fdaa53070213971e96` | Build 16 s ; `create --no-deps` refusé ; correction `create --no-build`, suite native réussie | Record alors manuel, rollback vers les mêmes artefacts, pas une preuve de deux releases |
| `int129-a3e3b3e35185` | Fixture SQL en 600, rôle app absent, grants refusés ; SQL de fixture corrigés en 644, nouveau volume jetable explicite ; release `33b53d1e82de-d9339820cf4a`, rejeu réussi | La première erreur concernait les permissions de la fixture, pas un scénario de migration/readiness |
| `int129-dee9431509a7` | A `150520d411cf-9e922ac31856`, B `89aa49d30c4d-52046d448936`, build 16,9/5,9 s ; backup 153 600 octets, vrais contenus A/B, retour aux IDs A, données inchangées | Paramètres hôte fictifs via un adaptateur temporaire explicitement autorisé |

L'adaptateur local réutilisait la vraie capture DB/uploads et le verrou hérité,
avec des paramètres hôte hors ligne. Il n'est pas livré. Les recettes locales
ont été nettoyées de façon ciblée ; aucune de ces preuves n'était à elle seule
une validation sudo/systemd sur le VPS. Les résultats VPS ont ensuite levé
cette limite pour la capture et les opérations effectivement décrites.

## Ce qui reste hors preuve

- À la clôture d'INT-129 : aucun déploiement public INT-111, DNS/HTTPS Tervo,
  navigateur métier complet ou nouvel administrateur production bootstrapé.
  INT-111 a depuis publié HTTPS et la recette navigateur ; ses preuves propres
  sont dans [son journal](../../INT-111-deploiement-vps.md).
- Aucune nouvelle exécution de CI/CD INT-130 ni publication GHCR.
- Pour INT-129 : pas de transfert réel de backup vers mini-s1, de timer activé
  ou de restauration des paramètres/services hôte réels. Depuis, INT-111 a
  réalisé une copie chiffrée sur mini-s1 (`03aca082`) et une récupération SQL/
  photos isolée ; la reconstruction complète des services hôte reste non exécutée.
- `--recover-from` non exercé : hors parcours validé.
- Pas de démonstration de reprise après SIGKILL, perte de courant/disque, ni
  mesure sur un volume représentatif de vingt ans de données.
- La comparaison Dockge qualifie la version/configuration testée, pas toutes
  les versions futures. Un vrai changement de layout ou de versions impose
  de reconsidérer cette qualification.

## Comment lire les résultats sans les survendre

| Formulation juste | Formulation à éviter |
|---|---|
| « J'ai validé une recette de release et de rollback sur un VPS avec des données fictives. » | « La production publique est déployée. » |
| « Les retours opérateur sont archivés ; les erreurs attendues étaient contrôlées. » | « Tous les cas imaginables ont été testés. » |
| « Le bundle a été capturé et vérifié ; le restore réel des paramètres hôte reste à faire. » | « La reprise après sinistre du VPS est garantie. » |
| « Dockge et la CLI utilisent le même projet et une configuration qualifiée. » | « Dockge fournit un RBAC read-only sur Docker. » |
| « Les images exactes A ont été réutilisées. » | « Rebuilder l'ancien commit donne forcément l'ancien artefact. » |
