# INT-128 — Comprendre la sauvegarde et prouver la restauration

## 1. Périmètre réel

**Destination autorisée : mini-s1.** Le VPS fournit une copie cohérente ;
le mini-s1 la récupère par SSH et la stocke dans un dépôt restic chiffré.
La clé restic reste privée sur le mini-s1, avec une copie de secours distincte
du dépôt : perdre le mot de passe signifie perdre l'accès aux sauvegardes.

La recette a été vérifiée sur Docker local jetable, avec données fictives.
**Aucune sauvegarde réelle sur mini-s1, aucun timer activé, aucune restauration
VPS ou remplacement de la base locale.** Les commandes ci-dessous expliquent
les opérations à préparer pour INT-111 ; les chemins et accès restent à valider.
`lb11` est le compte Linux cible demandé, pas un accès déjà établi.

| À conserver | Pourquoi |
|---|---|
| Dump PostgreSQL | Clients/sites/interventions, comptes, versions PDF `BYTEA` et empreintes |
| Archive uploads | Photos et miniatures ; le dump seul ne contient pas leurs fichiers |
| `.env` privé | Noms de rôles, secrets, SHA/tag et configuration de la release |
| Caddy : configuration, unité et état | Reconstruire le proxy et récupérer son état TLS |
| Dockge : Compose et données | Récupérer paramètres et authentification |

Restic fournit chiffrement, authentification, publication atomique des snapshots
et rétention. `sha256sum` vérifie les fichiers du bundle. Pas de crypto maison.
Les scripts sont un support facultatif : les opérations utiles sont ci-dessous.

### Comment lire les résultats

Les tableaux des sections 2 à 6 donnent les **résultats attendus**, pas des
captures d'une exécution VPS/mini-s1. Les observations réellement acquises
sont identifiées comme **recette locale** et détaillées en section 8.
Les identifiants, chemins temporaires, tailles et durées varient : aucune
valeur d'exemple n'est une preuve d'exécution.

Une commande silencieuse peut réussir : **code 0 + état/fichier contrôlé**,
pas forcément une ligne `OK`. Les affectations (`VAR=...`), `export`, `unset`,
définitions de fonctions, `set -e`, `umask` et `trap` n'affichent normalement
rien. Une affectation avec `$(commande)` capture sa sortie dans la variable,
elle ne l'affiche pas. Ne jamais imprimer les secrets pour « vérifier ».

Les blocs **« retour terminal »** complètent les tableaux. Un bloc marqué
**attendu** est une illustration, pas une capture VPS ; les mots
`ID_DEPOT`, `ID_SNAPSHOT`, `CHEMIN_DEPOT` sont des placeholders. Les commandes
complètes restent dans les blocs `bash`. `echo "$?"` rend visible le code de
la commande immédiatement précédente ; sous `set -e`, une erreur peut quitter
la session avant cet affichage.

## 2. Choisir explicitement le projet — sur le VPS

Après déploiement validé, dans un terminal d'administration :

```bash
sudo -i
set -e
umask 077
COMPOSE_FILE=/chemin/valide/deploy/docker-compose.yml
ENV_FILE=/chemin/prive/tervo.env
PROJECT=tervo
dc() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -p "$PROJECT" "$@"; }
sh "$(dirname "$COMPOSE_FILE")/validate-env.sh" "$ENV_FILE" "$COMPOSE_FILE"
dc config --quiet
dc ps
```

`dc` n'est qu'un raccourci pour garder **les mêmes fichier env, Compose et projet**
dans chaque commande. `config --quiet` ne montre pas les secrets.
Attendu : configuration valide et les services identifiés. Un refus ou un
projet inattendu impose l'arrêt, pas une purge ou une réinitialisation.

| Commande | Résultat attendu |
|---|---|
| `sudo -i` | Session root ouverte ; peut demander le mot de passe sudo. Ne valide ni Docker ni la DB. |
| `sh …/validate-env.sh …` | Code 0 et `Environment permissions and Compose configuration valid.` Ce message a été observé en recette locale, pas sur le VPS pour INT-128. |
| `dc config --quiet` | Code 0, aucune sortie standard ; une erreur de configuration doit interrompre la suite. |
| `dc ps` | Tableau des conteneurs du projet choisi ; PostgreSQL/backend/frontend doivent être présents et leurs healthchecks vérifiés. Leurs noms et IDs ne sont pas constants. |

Si le fichier choisi est `deploy/.env`, à côté du Compose, l'affectation
peut être `ENV_FILE="$(dirname "$COMPOSE_FILE")/.env"`. Elle reste silencieuse
et donne un chemin absolu si `COMPOSE_FILE` est absolu ; elle ne prouve pas
que le fichier existe ou est valide.

**Retour terminal attendu** (le message du validateur a été observé localement,
mais ce n'est pas une capture de commandes exécutées sur le VPS) :

```text
Environment permissions and Compose configuration valid.

# dc config --quiet
# echo "$?"
0
```

```bash
BACKEND_ID=$(dc ps -a -q backend)
DOCKGE_ID=$(docker compose -p dockge -f /opt/dockge/compose.yaml ps -a -q dockge)
test "$(docker inspect --format '{{.State.Running}}' "$BACKEND_ID")" = true
test "$(docker inspect --format '{{.State.Running}}' "$DOCKGE_ID")" = true
systemctl is-active --quiet caddy.service
UPLOADS_VOLUME=$(docker inspect --format \
  '{{range .Mounts}}{{if eq .Destination "/app/uploads"}}{{.Name}}{{end}}{{end}}' "$BACKEND_ID")
test -n "$UPLOADS_VOLUME"
```

On découvre le volume via le conteneur, sans supposer un nom issu du mini-s1.
Cette recette manuelle exige les trois services initialement actifs ; sinon,
examiner l'état et adapter la reprise. Ne pas démarrer un service volontairement
arrêté. PostgreSQL reste actif pour fournir le dump.

| Commande | Résultat attendu |
|---|---|
| `BACKEND_ID=$(dc ps -a -q backend)` | Variable contenant un seul ID de conteneur ; rien à l'écran. Absence ou multiplicité : ne pas poursuivre. |
| `DOCKGE_ID=$(docker compose … ps -a -q dockge)` | Un seul ID du projet Dockge, sans publication de données d'auth. |
| Les deux `test "$(docker inspect …)" = true` | Code 0, aucune sortie ; l'inspection sous-jacente doit donner `true` pour chaque conteneur. |
| `systemctl is-active --quiet caddy.service` | Code 0, aucune sortie si actif ; non-zéro sinon. |
| `UPLOADS_VOLUME=$(docker inspect …)` | Nom effectif du volume monté sur `/app/uploads`, capturé sans l'afficher. |
| `test -n "$UPLOADS_VOLUME"` | Code 0, aucune sortie ; variable vide = refus de continuer. |

## 3. Une courte fenêtre cohérente

`pg_dump` est cohérent pour la DB, mais un upload peut changer entre le dump
et l'archive. On suspend donc l'API pendant les deux captures. Dockge et Caddy
sont arrêtés pendant la copie de leurs données privées. **Cette coupure devra
être approuvée avant l'activation réelle**, aucun autre opérateur SQL/Docker
ne doit écrire pendant cette fenêtre.

```bash
exec 9>/run/lock/tervo-operations.lock
flock -n 9
resume_services() {
  rc=0
  systemctl start caddy.service || rc=1
  docker start "$DOCKGE_ID" "$BACKEND_ID" >/dev/null || rc=1
  return "$rc"
}
trap 'resume_services' EXIT
trap 'exit 1' HUP INT TERM
docker stop "$BACKEND_ID" "$DOCKGE_ID" >/dev/null
systemctl stop caddy.service
SNAPSHOT_DIR=$(mktemp -d /var/tmp/tervo-backup.XXXXXXXX)
```

`flock -n` refuse une opération concurrente ; INT-129 devra réutiliser ce verrou.
C'est une coordination entre outils, pas un RBAC qui empêcherait root de la
contourner. Le `trap` tente la reprise en cas d'erreur ou d'interruption normale.
**SIGKILL et perte de courant ne sont pas couverts** : inspecter puis reprendre
les services. Ne jamais annoncer une récupération automatique universelle.

| Commande | Résultat attendu |
|---|---|
| `exec 9>…` | Descripteur 9 ouvert sur le fichier de verrou, aucune sortie. Ce n'est pas encore l'acquisition du verrou. |
| `flock -n 9` | Code 0 si acquis ; non-zéro immédiatement si déjà tenu. Pas d'attente ni de capture concurrente. |
| `docker stop … >/dev/null` | Code 0 ; les IDs normalement retournés sont masqués. Backend et Dockge doivent être arrêtés. |
| `systemctl stop caddy.service` | Code 0, normalement silencieux ; Caddy doit être arrêté. |
| `SNAPSHOT_DIR=$(mktemp -d …)` | Chemin unique capturé dans la variable, dossier privé créé ; aucune sortie visible. |

**Observé localement :** refus du verrou concurrent et reprise après échec
testés. Les contrôles systemd/Dockge sont simulés ; ce tableau n'est pas une
preuve que les services du VPS ont été arrêtés.

**Retour terminal attendu** pour une commande d'arrêt silencieuse :

```text
# systemctl stop caddy.service
# echo "$?"
0
```

## 4. Dump, uploads et paramètres — toujours sur le VPS

```bash
dc exec -T postgres sh -c \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' \
  > "$SNAPSHOT_DIR/database.dump"
dc run --rm -T --no-deps -v "$UPLOADS_VOLUME:/app/uploads:ro" backend \
  tar -C /app -cf - uploads > "$SNAPSHOT_DIR/uploads.tar"
cp --preserve=mode "$ENV_FILE" "$SNAPSHOT_DIR/private.env"
cp /etc/systemd/system/caddy.service "$SNAPSHOT_DIR/caddy.service"
cp /opt/dockge/compose.yaml "$SNAPSHOT_DIR/dockge-compose.yaml"
tar -C /etc -cf "$SNAPSHOT_DIR/caddy-config.tar" caddy
tar -C /var/lib -cf "$SNAPSHOT_DIR/caddy-state.tar" caddy
tar -C /opt/dockge -cf "$SNAPSHOT_DIR/dockge-data.tar" data
printf '%s\n' "$PROJECT" > "$SNAPSHOT_DIR/source-project.txt"
resume_services
trap - EXIT HUP INT TERM
dc ps
systemctl is-active --quiet caddy.service
curl --fail --show-error --silent --noproxy "*" \
  "http://$(dc port backend 8000)/health/ready"
```

- `exec -T` évite un pseudo-terminal qui corromprait les flux binaires.
- Les variables entre apostrophes sont lues **dans le conteneur PostgreSQL** ;
  aucun mot de passe SQL dans les arguments.
- `--format=custom` produit un dump pour `pg_restore`. `--no-owner --no-acl`
  permet de reconstruire les droits via les rôles/grants d'INT-127.
- `run --rm --no-deps` utilise un conteneur ponctuel, sans démarrer des dépendances ;
  le volume uploads y est **read-only** (`:ro`).
- La reprise précède le transfert : on ne maintient pas la coupure durant tout
  le téléchargement. Si capture ou reprise échoue, ne pas publier le backup.
  Attendre aussi les healthchecks `healthy` : un `docker start` avec code 0
  ne suffit pas à prouver la disponibilité. Recontrôler plutôt que masquer l'erreur.

| Commande | Résultat attendu |
|---|---|
| `dc exec … pg_dump … > database.dump` | Code 0 ; flux binaire dans un fichier non vide, pas de dump affiché. Une erreur apparaît sur stderr. |
| `dc run … tar … > uploads.tar` | Code 0 ; archive uploads créée. Compose peut afficher une progression sur stderr, pas les octets du tar dans le terminal. |
| `cp --preserve=mode … private.env` | Code 0, silencieux ; copie privée avec le mode du fichier source conservé. Ne pas afficher son contenu. |
| Les deux `cp` de l'unité et du Compose Dockge | Code 0, silencieux ; les deux fichiers existent dans le dossier de capture. |
| Les trois `tar` des paramètres | Code 0, silencieux sans `-v` ; une archive par répertoire source, aucune restauration sur la machine. |
| `printf … > source-project.txt` | Code 0 ; le nom du projet est écrit dans le fichier, pas à l'écran. |
| `resume_services` | Code 0 seulement si les commandes de reprise réussissent ; les healthchecks restent à contrôler. |
| `dc ps` après reprise | Conteneurs retrouvés ; attendre `healthy`, pas seulement `Up` ou `starting`. |
| `systemctl is-active --quiet …` après reprise | Code 0 si Caddy est actif. |
| `dc port backend 8000` dans le curl | Adresse publiée utilisée pour l'URL, normalement `127.0.0.1:8000` selon le port configuré. |
| `curl … /health/ready` | HTTP 200, corps `{"status":"ready"}` et code 0. En cas d'indisponibilité DB : HTTP 503 et curl non-zéro avec `--fail`. |

**Observé en recette locale :** dump/restauration et archives réussis ;
le contrôle HTTP a donné 200 avec la DB disponible et 503 pendant sa panne.
Le curl manuel de reprise sur le VPS n'a pas été exécuté.

**Retours terminal attendus** pour un dump redirigé et un contrôle HTTP réussi :

```text
# dc exec -T postgres sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' > "$SNAPSHOT_DIR/database.dump"
# echo "$?"
0
# test -s "$SNAPSHOT_DIR/database.dump"
# echo "$?"
0
```

Le premier code se lit immédiatement après le `pg_dump` du bloc précédent ;
le second contrôle que son fichier n'est pas vide. Il n'existe pas de ligne
`dump OK` produite automatiquement par cette commande.

```text
{"status":"ready"}
```

Cette dernière ligne est la forme du corps HTTP attendu, pas une capture VPS.

```bash
(
  cd "$SNAPSHOT_DIR"
  sha256sum database.dump uploads.tar private.env caddy.service dockge-compose.yaml \
    caddy-config.tar caddy-state.tar dockge-data.tar source-project.txt > SHA256SUMS
  sha256sum --check SHA256SUMS
)
tar -C "$SNAPSHOT_DIR" -cf "$SNAPSHOT_DIR/tervo.tar" \
  database.dump uploads.tar private.env caddy.service dockge-compose.yaml \
  caddy-config.tar caddy-state.tar dockge-data.tar source-project.txt SHA256SUMS
flock -u 9
exec 9>&-
```

Attendu : neuf checksums `OK`. L'archive contient des secrets **en clair à ce
stade** : répertoire privé, transfert SSH, puis chiffrement restic. Ni archive,
ni `.env`, ni sorties de dump dans Git/chat. L'extraction est réservée à nos
archives authentifiées, pas à un tar arbitraire reçu d'un tiers.

| Commande | Résultat attendu |
|---|---|
| `cd "$SNAPSHOT_DIR"` dans le sous-shell | Code 0, pas d'affichage ; seul ce sous-shell change de dossier. |
| `sha256sum … > SHA256SUMS` | Fichier contenant neuf lignes `HASH  NOM`, aucune sortie visible. |
| `sha256sum --check SHA256SUMS` | Neuf lignes `NOM: OK`, code 0 ; `FAILED` ou fichier manquant interdit la suite. |
| `tar … -cf …/tervo.tar …` | Code 0, bundle créé sans sortie standard ; cela ne le chiffre pas. |
| `flock -u 9` puis `exec 9>&-` | Verrou libéré puis descripteur fermé, aucune sortie. |

Forme **attendue**, non capturée sur le VPS :

```text
database.dump: OK
uploads.tar: OK
private.env: OK
caddy.service: OK
dockge-compose.yaml: OK
caddy-config.tar: OK
caddy-state.tar: OK
dockge-data.tar: OK
source-project.txt: OK
```

## 5. Réception et chiffrement — sur mini-s1

Prérequis : restic installé, SSH avec hostkey vérifiée, compte autorisé à lire
l'archive dans un emplacement privé. Ne pas résoudre un refus par `chmod 777`
ou `NOPASSWD: ALL`. Les chemins ci-dessous sont à renseigner, pas des accès
déjà installés :

```bash
umask 077
export RESTIC_REPOSITORY=/srv/backups/tervo
export RESTIC_PASSWORD_FILE=/etc/tervo/restic-password
unset RESTIC_PASSWORD RESTIC_PASSWORD_COMMAND RESTIC_REPOSITORY_FILE
restic version
# Une seule fois, sur un dépôt neuf choisi explicitement :
restic init
RECEIVE_DIR=$(mktemp -d /var/tmp/tervo-receive.XXXXXXXX)
scp -F /etc/tervo/backup-ssh.conf \
  "tervo-vps-backup:/chemin/prive/accessible/tervo.tar" "$RECEIVE_DIR/tervo.tar"
restic backup --stdin --stdin-filename tervo.tar --host tervo-vps --tag tervo \
  < "$RECEIVE_DIR/tervo.tar"
restic check --read-data
restic snapshots --host tervo-vps --tag tervo
```

Le mot de passe vient d'un fichier privé `600`, jamais de la ligne de commande.
`init` ne doit pas être relancé pour contourner une mauvaise clé ou une erreur
d'accès. `backup --stdin` reçoit les octets de l'archive ; `check --read-data`
relit les données chiffrées du dépôt. Attendre tous les codes 0 avant de compter
la sauvegarde comme exploitable. Retirer ensuite les copies temporaires en clair,
uniquement aux emplacements créés pour cette capture.

| Commande | Résultat attendu et preuve disponible |
|---|---|
| `restic version` | Version/Go/architecture affichés. Version **observée sur le poste de recette : 0.19.1** ; rien n'est encore relevé sur mini-s1. |
| `restic init` | Dépôt chiffré créé et identifiant affiché, code 0. Réussi sur un dépôt local fictif ; son ID n'est pas celui du futur dépôt mini-s1. |
| `RECEIVE_DIR=$(mktemp …)` | Nouveau dossier privé, chemin capturé sans affichage. |
| `scp …` | Code 0, archive reçue ; une barre de progression peut apparaître. **Transfert réel non exécuté** : SSH était simulé dans les tests. |
| `restic backup …` | Code 0 et confirmation d'un snapshot enregistré avec un ID variable. Sauvegarde chiffrée réussie localement ; sortie détaillée/ID non consignés. |
| `restic check --read-data` | Code 0 après vérification du dépôt et lecture des packs ; des erreurs d'intégrité interdisent de compter le backup comme exploitable. Réussi en recette locale. |
| `restic snapshots …` | Liste des snapshots correspondant à `tervo-vps`/`tervo`, avec IDs et dates ; ne prouve pas à elle seule qu'un restore fonctionne. |

**Retour terminal observé sur le poste de recette** pour `restic version` :

```text
restic 0.19.1 compiled with go1.26.4 on linux/amd64
```

**Forme attendue des lignes utiles** de `restic init`, `backup` et `check`
(extraits illustratifs, pas des IDs ni une capture du dépôt mini-s1) :

```text
created restic repository ID_DEPOT at CHEMIN_DEPOT
snapshot ID_SNAPSHOT saved
no errors were found
```

Les commandes peuvent aussi afficher statistiques et progression ; les
tableaux ci-dessus restent les contrôles de réussite, pas seulement ces lignes.

Rétention proposée, à approuver avant suppression :

```bash
restic forget --host tervo-vps --tag tervo --group-by host,tags \
  --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --dry-run
# Après examen et accord, remplacer --dry-run par --prune.
```

**Résultat attendu :** liste des snapshots qui seraient conservés/supprimés,
sans suppression avec `--dry-run`. En recette locale, la politique a été appliquée
sur un dépôt fictif et le snapshot de test est resté restaurable. Le dry-run
manuel ci-dessus et une purge sur mini-s1 n'ont pas été exécutés.

## 6. Restaurer ailleurs, jamais sur la source

Sur l'hôte de recette : Compose et image backend compatibles disponibles,
accès au dépôt restic, **nouveau projet UUID**, aucune DB/volume à conserver.
Un rebuild ne prouve pas l'identité de l'ancien artefact de release (INT-129).

```bash
umask 077
COMPOSE_FILE=/chemin/source-compatible/deploy/docker-compose.yml
export RESTIC_REPOSITORY=/chemin/du/depot/chiffre-accessible
export RESTIC_PASSWORD_FILE=/chemin/prive/restic-password
unset RESTIC_PASSWORD RESTIC_PASSWORD_COMMAND RESTIC_REPOSITORY_FILE
RESTORE_DIR=$(mktemp -d /var/tmp/tervo-restore.XXXXXXXX)
restic dump ID_SNAPSHOT_VALIDE /tervo.tar > "$RESTORE_DIR/tervo.tar"
tar -tf "$RESTORE_DIR/tervo.tar"
tar -xf "$RESTORE_DIR/tervo.tar" -C "$RESTORE_DIR" --no-same-owner
(cd "$RESTORE_DIR" && sha256sum --check SHA256SUMS)
RESTORE_PROJECT="tervo-restore-$(cat /proc/sys/kernel/random/uuid)"
ENV_FILE="$RESTORE_DIR/private.env"
rdc() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -p "$RESTORE_PROJECT" "$@"; }
rdc up -d --wait postgres
rdc exec -T postgres sh -c \
  'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$RESTORE_DIR/database.dump"
rdc exec -T postgres sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /opt/tervo/app-grants.sql'
rdc run --rm -T --no-deps backend \
  tar -C /app -xf - --no-same-owner < "$RESTORE_DIR/uploads.tar"
```

Pas de `--clean`, `DROP`, downgrade ni réutilisation de volume existant.
`--exit-on-error` et `ON_ERROR_STOP=1` empêchent de poursuivre sur un restore
partiel. Ne pas lancer les services HTTP avec les ports du VPS dans ce projet
de recette. Le remplacement local demandé reste une opération finale distincte.

| Commande | Résultat attendu |
|---|---|
| `RESTORE_DIR=$(mktemp …)` | Nouveau dossier privé ; aucune réutilisation d'un dossier de données. |
| `restic dump … > …/tervo.tar` | Code 0 et bundle déchiffré écrit dans le fichier ; aucun contenu affiché. Mauvaise clé = échec. |
| `tar -tf …` | Dix noms de fichiers : les neuf données listées ci-dessus plus `SHA256SUMS`, pas leurs contenus. |
| `tar -xf … -C … --no-same-owner` | Code 0, fichiers extraits dans le dossier isolé ; pas de reprise des propriétaires de la source. |
| `sha256sum --check …` après extraction | Les neuf `OK` ci-dessus ; corruption ou absence = arrêt. |
| `RESTORE_PROJECT=…` | Nom unique `tervo-restore-UUID`, capturé sans affichage. |
| `rdc up -d --wait postgres` | PostgreSQL du **nouveau** projet créé et healthy, code 0 ; ne doit pas utiliser les volumes du projet source. |
| `rdc exec … pg_restore …` | Code 0, normalement silencieux sans `--verbose` ; schéma/données chargés. Les erreurs doivent interrompre la suite. |
| `rdc exec … psql … app-grants.sql` | Code 0, messages `BEGIN`, plusieurs `GRANT`, `REVOKE`, `COMMIT`. Leur nombre dépend du schéma. |
| `rdc run … tar … < uploads.tar` | Code 0, fichiers uploads restaurés dans le volume du projet isolé ; aucun serveur HTTP lancé par cette commande. |

**Observé localement :** mauvaise clé refusée, bundle déchiffré identique,
nouveau PostgreSQL healthy, restore/grants et uploads réussis. La source de
recette n'a pas été remplacée.

**Retour terminal attendu**, exemple de forme des messages psql des grants :

```text
BEGIN
GRANT
GRANT
...
REVOKE
COMMIT
```

Le `...` remplace les autres lignes `GRANT` ; ce n'est pas une ligne émise
par psql. `pg_restore` sans `--verbose` est normalement silencieux : son code
0 puis les contrôles SQL/bytes sont nécessaires, pas un message inventé.

Contrôler les relations, chemins photo et métadonnées PDF sous cette cible :

```bash
rdc exec -T postgres sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' <<'SQL'
SELECT c.id, s.id, i.id, p.file_path
FROM client c JOIN site s ON s.client_id=c.id
JOIN intervention i ON i.site_id=s.id JOIN photo p ON p.intervention_id=i.id;
SELECT id, sha256, size, octet_length(pdf), generated_at, transmitted_at
FROM report_version;
SQL
```

**Résultat attendu :** deux tableaux SQL avec les lignes du jeu restauré.
Les IDs/liens et chemins photo doivent correspondre à la source ; pour chaque
PDF, `size` doit égaler `octet_length(pdf)`, avec le même SHA et les mêmes dates.
Une base vide peut produire zéro ligne : ce n'est pas une preuve de restauration.
En recette locale, une chaîne Client/Site/Intervention/Photo/Report et une
version PDF fictives ont été comparées à la source avec succès ; les sorties
SQL détaillées n'ont pas été consignées dans cette note.

Comparer au jeu source autorisé. `size = octet_length(pdf)` ne suffit pas à
prouver l'identité des octets. Pour **une version de test identifiée** :

```bash
REPORT_VERSION_ID=ID_NUMERIQUE_DE_TEST
case "$REPORT_VERSION_ID" in ''|*[!0-9]*) exit 1 ;; esac
rdc exec -T postgres sh -c \
  'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At' \
  > "$RESTORE_DIR/pdf.base64" <<SQL
SELECT encode(pdf, 'base64') FROM report_version WHERE id=$REPORT_VERSION_ID;
SQL
base64 --decode "$RESTORE_DIR/pdf.base64" > "$RESTORE_DIR/report.pdf"
sha256sum "$RESTORE_DIR/report.pdf"
```

| Commande | Résultat attendu |
|---|---|
| Affectation de l'ID et `case` | Aucun affichage ; ID non numérique = sortie immédiate avec code 1. |
| `psql … > pdf.base64` | Code 0, une version identifiée exportée vers le fichier ; aucun PDF/base64 affiché. Un ID absent peut donner un fichier vide : contrôler la ligne SQL avant l'export. |
| `base64 --decode … > report.pdf` | Code 0, fichier PDF reconstitué ; contenu base64 invalide = échec. |
| `sha256sum …/report.pdf` | Une ligne `HASH  CHEMIN`, le hash devant égaler le `sha256` enregistré. Cette commande ne compare pas automatiquement les deux valeurs. |

**Retour terminal attendu**, avec valeurs volontairement non renseignées :

```text
SHA256_STOCKE_DANS_REPORT_VERSION  CHEMIN_PRIVE/report.pdf
```

Attendre le hash stocké pour cette version et les mêmes octets qu'avant backup.
Ne pas afficher le PDF/base64 dans le terminal partagé. Pour une photo choisie,
extraire l'archive uploads dans un dossier privé puis comparer `sha256sum` au
fichier source du jeu autorisé. La recette interne compare aussi exactement
ces octets, pas seulement l'existence d'un fichier.

Pour les paramètres, extraire chaque archive séparément dans un nouveau
répertoire privé. Ne pas recopier directement sur `/etc/caddy`, `/var/lib/caddy`
ou `/opt/dockge/data`. Vérifier contenu et droits, puis adapter les propriétaires
aux comptes de la cible, pas aux UID numériques de la source. Login Dockge,
service Caddy et état TLS réels seront recontrôlés en INT-111.

**Résultat attendu de ces contrôles de paramètres :** mêmes octets que les
sources autorisées, fichiers encore privés, aucune copie sur les répertoires
actifs. La recette locale a confirmé cela pour des fixtures ; elle n'a pas
rejoué login Dockge, démarrage Caddy ou émission/renouvellement TLS réels.

## 7. Automatisation facultative et limites

`snapshot.py` exécute les mêmes opérations, préserve les états actif/inactif
et refuse un flux privé vers un terminal. `pull-backup.sh` reçoit le bundle,
vérifie les checksums avant restic et ne publie rien si SSH échoue.
Le format reste lisible avec **tar + SHA256SUMS**, sans lecteur Python imposé.

Un seul timer Tervo est prévu **sur mini-s1**, pas un cron en plus sur le VPS.
03:00 avec délai aléatoire maximal 5 minutes ; pas de rattrapage de maintenance
en journée si mini-s1 était éteint. Timer non installé/activé. Rétention automatique
désactivée par défaut (`APPLY_RETENTION=0`).

Avant activation : approuver la fenêtre, valider accès SSH/sudo limité,
installer les fichiers privilégiés root-owned et non modifiables par l'utilisateur,
tester une vraie récupération hors VPS et examiner les jobs déjà présents.
Le verrou partagé devra être respecté par INT-129 ; il ne remplace pas la
discipline d'administration. Un échec doit être suivi dans le journal du service.

La validation locale couvre PostgreSQL/restic réels, une photo, un PDF BYTEA
et des configurations fictives, pas le login d'un Dockge restauré ni un certificat
TLS réel. Pas de mesure sur vingt ans de données, de SLA ou de stratégie 3-2-1
revendiquée. Une seule copie sur mini-s1 ne couvre pas sa propre perte.

## 8. Ce qui a effectivement été exécuté

Sur le poste de recette, pas le VPS :

```bash
cd backend
uv run pytest ../deploy/test_snapshot.py tests/test_production_config.py -q
```

**14 tests réussis** : checksums, refus d'archives inattendues/corrompues,
refus d'écrasement et de dépôt Git, verrou concurrent, reprise des services
simulés et refus de publication après échec SSH, plus configuration backend.

Sortie de synthèse **observée lors de la livraison INT-128**, pas une nouvelle
exécution pour cette correction documentaire :

```text
14 passed in 0.52s
```

La recette Docker existante a aussi réussi sur l'arbre Git
`6fd18829bd6edc6240d15891396e7fce8c279261`, avec restic **0.19.1** :

```bash
python3 deploy/check-stack.py --revision 6fd18829bd6edc6240d15891396e7fce8c279261 \
  --backup --restic /chemin/temporaire/restic-verifie
```

L'exécution locale a terminé avec **code 0**. Parmi les lignes réellement
émises :

```text
PASS: encrypted restic bundle, wrong-key refusal, relationships/photo/PDF BYTEA and private config restore; source unchanged
PASS: image revision labels match exported source object
```

| Contrôle | Résultat observé |
|---|---|
| PostgreSQL et restauration dans un second projet UUID | Dump/restore complets, relations Client → Site → Intervention → Photo/Report conservées |
| PDF `BYTEA` | Octets, taille, SHA-256 et dates générée/transmise identiques |
| Photo | Octets identiques au fichier de fixture |
| Bundle restic | Copie déchiffrée identique, contrôle des packs réussi, mauvaise clé refusée |
| Paramètres privés | `.env` et fixtures Caddy/Dockge restitués byte-identiques |
| Source et nettoyage | Source de recette inchangée par le restore ; ressources UUID supprimées |

Le transfert SSH était **simulé**, les contrôles systemd/Dockge natifs étaient
mockés ou remplacés par des configurations offline fictives. Les commandes
manuelles de ce guide ne constituent donc pas une recette complète déjà jouée
sur VPS/mini-s1. Ces preuves ne valident pas une restauration d'auth Dockge réelle,
des certificats actifs, la fenêtre de coupure réelle ou une volumétrie représentative.
