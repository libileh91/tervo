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
stade** : directory privé, transfert SSH, puis chiffrement restic. Ni archive,
ni `.env`, ni sorties de dump dans Git/chat. L'extraction est réservée à nos
archives authentifiées, pas à un tar arbitraire reçu d'un tiers.

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

Rétention proposée, à approuver avant suppression :

```bash
restic forget --host tervo-vps --tag tervo --group-by host,tags \
  --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --dry-run
# Après examen et accord, remplacer --dry-run par --prune.
```

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

La recette Docker existante a aussi réussi sur l'arbre Git
`6fd18829bd6edc6240d15891396e7fce8c279261`, avec restic **0.19.1** :

```bash
python3 deploy/check-stack.py --revision 6fd18829bd6edc6240d15891396e7fce8c279261 \
  --backup --restic /chemin/temporaire/restic-verifie
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
