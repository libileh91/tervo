# Journal 03 — Garde-fous et échecs volontaires

[Retour](02-releases-sauvegarde-rollback.md) · [Sommaire](../README.md) · [Suite : Dockge](04-gate-dockge.md)

**Archives de commandes déjà exécutées, pas une liste de tests à refaire.**
Toutes les modifications défaillantes ci-dessous concernent la copie de
recette sur le VPS, jamais le dépôt principal. Les sorties sont celles
envoyées par l'opérateur. Les retours `Release failed` sont attendus dans
ces scénarios ; leur cause et leur code étaient contrôlés.

## 1. Refus sous verrou, refus sur schéma différent et réconciliation A

### Bloc envoyé et exécuté — terminal root

```sh
(
set -eu
umask 077

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
STATE_DIR="/var/lib/tervo-int129/$PROJECT"
LOCK=/run/lock/tervo-operations.lock
SCRIPT="$CHECKOUT/deploy/scripts/release.py"
RELEASE_A=9111a2a1ecbb-79b422c7d71f
REVISION_A=9111a2a1ecbb010cf9033c7300ca49193d0fd34a

# Même cible et mêmes confirmations pour toutes les commandes.
set -- \
  --checkout "$CHECKOUT" \
  --env-file "$CHECKOUT/deploy/.env" \
  --project "$PROJECT" \
  --state-dir "$STATE_DIR" \
  --lock-file "$LOCK" \
  --dockge-container dockge-dockge-1 \
  --console-idle-confirmed \
  --maintenance-confirmed

# 1. Le verrou est tenu par flock : la release doit refuser.
RC=0
flock -n "$LOCK" \
  python3 "$SCRIPT" rollback "$@" --release-id "$RELEASE_A" \
  > "$STATE_DIR/refus-verrou.log" 2>&1 || RC=$?

test "$RC" -eq 1
grep -F 'Release failed: BlockingIOError.' "$STATE_DIR/refus-verrou.log"

# 2. Modification contrôlée du schéma de la DB de recette.
docker exec -i "$PROJECT-postgres-1" sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
CREATE TABLE public.int129_schema_probe (id integer);
SQL

RC=0
python3 "$SCRIPT" rollback "$@" --release-id "$RELEASE_A" \
  > "$STATE_DIR/refus-schema.log" 2>&1 || RC=$?

test "$RC" -eq 1
grep -F 'Schema differs: rollback blocked;' "$STATE_DIR/refus-schema.log"

# Nettoyage explicite de la seule table vide créée pour ce test.
docker exec -i "$PROJECT-postgres-1" sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
DROP TABLE public.int129_schema_probe;
SQL

# Réconcilier les sources et la configuration avec l'application A.
test -z "$(git -C "$CHECKOUT" status --porcelain)"
git -C "$CHECKOUT" switch -c recette-a-reconciliee "$REVISION_A"

sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION_A/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION_A/" \
  "$CHECKOUT/deploy/.env"

# Vérifie notamment le schéma rétabli, sans rebuild ni migration.
python3 "$SCRIPT" deploy "$@" --revision "$REVISION_A"

docker start dockge-dockge-1
systemctl is-active caddy
docker inspect --format '{{.State.Running}}' dockge-dockge-1
)
```

### Résultat envoyé

```text
Release failed: BlockingIOError. No database downgrade or restore performed.
CREATE TABLE
Release failed: Schema differs: rollback blocked; keep maintenance and plan roll-forward.. No database downgrade or restore performed.
DROP TABLE
Switched to a new branch 'recette-a-reconciliee'
STEP: validate the private environment and explicit CLI model
Environment permissions and Compose configuration valid.
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
[+] up 2/2
 ✔ Container int129-vps-33c350b23010-frontend-1 Healthy                                                                                                                0.5s
 ✔ Container int129-vps-33c350b23010-backend-1  Healthy                                                                                                                0.5s
PASS: backend readiness, frontend health and login page
Already released; no rebuild or migration
dockge-dockge-1
active
true
root@22565:~#
```

### But et usage

| Commande / mécanisme | Ce qu'il fait | Résultat / limite |
|---|---|---|
| `set -- …`, `"$@"` | Regroupe les mêmes arguments, conservés comme arguments distincts | Pas de changement involontaire de cible ; variables limitées au sous-shell |
| `flock -n "$LOCK" commande` | Tient le verrou pendant l'appel ; le helper tente de le prendre à son tour | Code 1 et erreur précise `BlockingIOError`, pas seulement un échec quelconque |
| `RC=0 … || RC=$?` | Capture le refus attendu au lieu de laisser `set -e` couper le test trop tôt | `test "$RC" -eq 1` doit ensuite réussir |
| `> journal 2>&1` | Capture stdout et stderr dans un fichier privé | `umask 077` ; pas de journal complet publié |
| `grep -F` | Recherche une chaîne littérale et affiche la ligne de cause | Vérifie que l'échec provient bien du garde-fou recherché |
| `CREATE TABLE` | Introduit une divergence simple, sans modifier les tables métier | Le rollback est bloqué, même si cette table serait probablement compatible avec l'ancien code |
| `DROP TABLE` | Retire **explicitement la seule table de test vide** | Ce n'est pas un downgrade automatique du helper |
| `git status --porcelain`, `test -z` | Exige un checkout sans modification suivie | Silence normal, code 0 ; sinon arrêt |
| `git switch -c … SHA_A` | Crée une branche attachée à A, sans supprimer B de `master` | Nouvelle branche observée ; pas de reset ni de force-push |
| `sed -i` | Réaligne tag et SHA du `.env` sur A | Aucun secret DB changé |
| Rejeu `deploy A` | Contrôle schéma/config/images et réutilise la release existante | `Already released; no rebuild or migration` |
| `docker start dockge…` | Reprend la console **après** réconciliation et contrôle | Caddy active, Dockge true à la fin |

L'égalité de schéma est une règle conservatrice, pas une analyse générale
de compatibilité applicative. Le refus est une protection réussie.

## 2. Migration volontairement défaillante, puis secours automatique

### Bloc envoyé et exécuté — terminal root

La migration lève une erreur **avant tout DDL**. La fenêtre de maintenance
et la courte interruption de Caddy/Dockge pendant la sauvegarde étaient
annoncées ; aucune opération UI concurrente n'était autorisée.

```sh
(
set -eu
umask 077

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
STATE_DIR="/var/lib/tervo-int129/$PROJECT"
SCRIPT="$CHECKOUT/deploy/scripts/release.py"
ENV_FILE="$CHECKOUT/deploy/.env"
REVISION_A=9111a2a1ecbb010cf9033c7300ca49193d0fd34a
LOG="$STATE_DIR/echec-migration.log"

test "$(git -C "$CHECKOUT" rev-parse HEAD)" = "$REVISION_A"
test -z "$(git -C "$CHECKOUT" status --porcelain)"

set -- \
  --checkout "$CHECKOUT" \
  --env-file "$ENV_FILE" \
  --project "$PROJECT" \
  --state-dir "$STATE_DIR" \
  --lock-file /run/lock/tervo-operations.lock \
  --dockge-container dockge-dockge-1 \
  --console-idle-confirmed \
  --maintenance-confirmed

git -C "$CHECKOUT" switch -c recette-echec-migration

cat > "$CHECKOUT/backend/alembic/versions/z129e0010001_recipe_failure.py" <<'PY'
"""Recipe only: fail before any database change."""
revision = "z129e0010001"
down_revision = "m109e0010001"
branch_labels = None
depends_on = None

def upgrade():
    raise RuntimeError("INT129 expected migration failure")

def downgrade():
    raise RuntimeError("Recipe only; no downgrade")
PY

git -C "$CHECKOUT" add \
  backend/alembic/versions/z129e0010001_recipe_failure.py
GIT_EDITOR=true git -C "$CHECKOUT" \
  -c user.name="INT129 recipe" \
  -c user.email="recipe@localhost" \
  commit -q -m "INT129 recipe expected migration failure"

REVISION="$(git -C "$CHECKOUT" rev-parse HEAD)"
sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION/" \
  "$ENV_FILE"

RC=0
python3 "$SCRIPT" deploy "$@" --revision "$REVISION" \
  > "$LOG" 2>&1 || RC=$?

# Afficher uniquement les étapes et résultats utiles, pas le journal complet.
grep -E '^(STEP:|RuntimeError: INT129|Failed candidate record:|PASS:|Release failed:|Console remains frozen)' \
  "$LOG" || true

test "$RC" -eq 1
grep -qF 'RuntimeError: INT129 expected migration failure' "$LOG"
grep -qF 'PASS: exact rescue image IDs restored; database unchanged' "$LOG"

echo "Images actives après le retour automatique :"
docker inspect --format '{{.Name}} {{.Image}}' \
  "$PROJECT-backend-1" "$PROJECT-frontend-1"

# Revenir aux sources/configuration A avant de rendre Dockge disponible.
git -C "$CHECKOUT" switch recette-a-reconciliee
sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION_A/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION_A/" \
  "$ENV_FILE"

python3 "$SCRIPT" deploy "$@" --revision "$REVISION_A"

docker start dockge-dockge-1
systemctl is-active caddy
docker inspect --format '{{.State.Running}}' dockge-dockge-1
)
```

### Résultat envoyé

```text
Switched to a new branch 'recette-echec-migration'

STEP: validate the private environment and explicit CLI model
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
STEP: build once while the previous API is still available
STEP: migrate, grant and check before starting HTTP services
RuntimeError: INT129 expected migration failure
Failed candidate record: 059154f4df98-67d65659567b
PASS: backend readiness, frontend health and login page
PASS: exact rescue image IDs restored; database unchanged
Console remains frozen; reconcile Git/env with the active rescue record before restart.
Release failed: docker compose exited with code 1. No database downgrade or restore performed.
Images actives après le retour automatique :
/int129-vps-33c350b23010-backend-1 sha256:24e9377d6247214c568109cd30165b971eeccf1866853f8d73381a8a1b2bd5a0
/int129-vps-33c350b23010-frontend-1 sha256:29a397ebb78b6d3cb76b039f1fd341e18c41b7727f9432fde917021d9b871103
Switched to branch 'recette-a-reconciliee'
STEP: validate the private environment and explicit CLI model
Environment permissions and Compose configuration valid.
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
[+] up 2/2
 ✔ Container int129-vps-33c350b23010-backend-1  Healthy                                                                                                                0.5s
 ✔ Container int129-vps-33c350b23010-frontend-1 Healthy                                                                                                                0.5s
PASS: backend readiness, frontend health and login page
Already released; no rebuild or migration
dockge-dockge-1
active
true
root@22565:~#
```

### But et usage

| Élément | But | Résultat et interprétation |
|---|---|---|
| Branche dédiée | Garder la panne reproductible sans contaminer A | Le retour à `recette-a-reconciliee` retire la migration défaillante des sources actives |
| `revision` / `down_revision` | Ajouter un maillon après la tête Alembic existante | `z129e0010001` après `m109e0010001` |
| `raise RuntimeError` dans `upgrade()` | Provoquer une vraie erreur Alembic avant toute modification SQL | Cause exacte observée |
| Nouveau commit + env révisé | Tester un candidat traçable, pas un checkout sale | Candidat `059154f4df98-67d65659567b` enregistré échoué |
| `grep -E … || true` | Afficher un extrait sûr du journal | Ce n'est **pas** le contrôle de réussite |
| `test RC` et `grep -qF` | Contrôler le code, la cause et le secours | Silence normal des assertions, code 0 si conformes |
| `PASS` du secours | A est remise en service après l'échec du candidat | Ne transforme pas la release en succès : code global 1 |
| Inspection `.Image` | Comparer le secours réellement démarré au record A | Deux IDs exacts A observés |
| Réconciliation puis `docker start` | Ne pas laisser l'UI relancer le candidat défaillant | A revalidée, Caddy/Dockge actifs à la fin |

## 3. Échecs build, readiness et smoke HTTP

### Bloc envoyé et exécuté — terminal root

Les trois cas étaient regroupés pour limiter les allers-retours. Aucun nouveau
harness permanent n'a été créé. La console restait gelée pendant les cas ;
la sauvegarde des deux derniers impliquait une courte pause Caddy.

```sh
(
set -eu
umask 077

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
STATE_DIR="/var/lib/tervo-int129/$PROJECT"
ENV_FILE="$CHECKOUT/deploy/.env"
SCRIPT="$CHECKOUT/deploy/scripts/release.py"
REVISION_A=9111a2a1ecbb010cf9033c7300ca49193d0fd34a

test "$(git -C "$CHECKOUT" rev-parse HEAD)" = "$REVISION_A"
test -z "$(git -C "$CHECKOUT" status --porcelain)"

# Identité limitée au dépôt de recette, pas de configuration Git globale.
git -C "$CHECKOUT" config user.name "INT129 recipe"
git -C "$CHECKOUT" config user.email "recipe@localhost"

set -- \
  --checkout "$CHECKOUT" \
  --env-file "$ENV_FILE" \
  --project "$PROJECT" \
  --state-dir "$STATE_DIR" \
  --lock-file /run/lock/tervo-operations.lock \
  --dockge-container dockge-dockge-1 \
  --console-idle-confirmed \
  --maintenance-confirmed

# 1. Échec de build : A doit rester en place.
API_BEFORE="$(docker inspect --format '{{.Id}}' "$PROJECT-backend-1")"
git -C "$CHECKOUT" switch -c recette-echec-build "$REVISION_A"
printf '\nRUN echo "INT129 expected build failure" >&2; exit 42\n' \
  >> "$CHECKOUT/backend/Dockerfile"
git -C "$CHECKOUT" add backend/Dockerfile
GIT_EDITOR=true git -C "$CHECKOUT" commit -qm "INT129 expected build failure"

REVISION="$(git -C "$CHECKOUT" rev-parse HEAD)"
echo "Candidat build : $REVISION"
sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION/" "$ENV_FILE"

LOG="$STATE_DIR/echec-build.log"
RC=0
python3 "$SCRIPT" deploy "$@" --revision "$REVISION" > "$LOG" 2>&1 || RC=$?
grep -E 'INT129 expected build failure|exit code: 42|^Release failed:' "$LOG" || true
test "$RC" -eq 1
grep -qF 'exit code: 42' "$LOG"
test "$(docker inspect --format '{{.Id}}' "$PROJECT-backend-1")" = "$API_BEFORE"
test "$(curl -fsS http://127.0.0.1:19830/recipe-marker.txt)" = "release A"

# 2. Échec de readiness : URL du healthcheck inexistante.
git -C "$CHECKOUT" switch -c recette-echec-readiness "$REVISION_A"
sed -i \
  's@http://127.0.0.1:8000/health/ready@http://127.0.0.1:8000/int129-unavailable@' \
  "$CHECKOUT/deploy/docker-compose.yml"
git -C "$CHECKOUT" add deploy/docker-compose.yml
GIT_EDITOR=true git -C "$CHECKOUT" commit -qm "INT129 expected readiness failure"

REVISION="$(git -C "$CHECKOUT" rev-parse HEAD)"
sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION/" "$ENV_FILE"

LOG="$STATE_DIR/echec-readiness.log"
RC=0
python3 "$SCRIPT" deploy "$@" --revision "$REVISION" > "$LOG" 2>&1 || RC=$?
grep -E 'unhealthy|^(Failed candidate record:|PASS:|Release failed:)' "$LOG" || true
test "$RC" -eq 1
grep -qiF 'unhealthy' "$LOG"
grep -qF 'PASS: exact rescue image IDs restored; database unchanged' "$LOG"

# 3. Échec du smoke HTTP : /health reste valide, /login renvoie 503.
git -C "$CHECKOUT" switch -c recette-echec-smoke "$REVISION_A"
sed -i \
  '/    location \/ {/i\    location = /login { return 503; }' \
  "$CHECKOUT/frontend/nginx.conf"
git -C "$CHECKOUT" add frontend/nginx.conf
GIT_EDITOR=true git -C "$CHECKOUT" commit -qm "INT129 expected HTTP smoke failure"

REVISION="$(git -C "$CHECKOUT" rev-parse HEAD)"
sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION/" "$ENV_FILE"

LOG="$STATE_DIR/echec-smoke.log"
RC=0
python3 "$SCRIPT" deploy "$@" --revision "$REVISION" > "$LOG" 2>&1 || RC=$?
grep -E '^(Failed candidate record:|PASS:|Release failed:)' "$LOG" || true
test "$RC" -eq 1
grep -qF 'Release failed: HTTP readiness/smoke failed.' "$LOG"
grep -qF 'PASS: exact rescue image IDs restored; database unchanged' "$LOG"

# Réconcilier A puis rendre la console disponible.
git -C "$CHECKOUT" switch recette-a-reconciliee
sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION_A/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION_A/" "$ENV_FILE"

python3 "$SCRIPT" deploy "$@" --revision "$REVISION_A"
docker start dockge-dockge-1
systemctl is-active caddy
docker inspect --format '{{.State.Running}}' dockge-dockge-1
)
```

### Résultat envoyé

```text
Switched to a new branch 'recette-echec-build'
Candidat build : 7b00252a5e64f796a2835a55c13e3930fe446df9
#38 [backend runtime 10/10] RUN echo "INT129 expected build failure" >&2; exit 42
#38 0.161 INT129 expected build failure
#38 ERROR: process "/bin/sh -c echo \"INT129 expected build failure\" >&2; exit 42" did not complete successfully: exit code: 42
 > [backend runtime 10/10] RUN echo "INT129 expected build failure" >&2; exit 42:
0.161 INT129 expected build failure
  78 | >>> RUN echo "INT129 expected build failure" >&2; exit 42
target backend: failed to solve: process "/bin/sh -c echo \"INT129 expected build failure\" >&2; exit 42" did not complete successfully: exit code: 42
Release failed: docker compose exited with code 1. No database downgrade or restore performed.
Switched to a new branch 'recette-echec-readiness'
container int129-vps-33c350b23010-backend-1 is unhealthy
Failed candidate record: 5c9f9dda77e4-4fd1121a7262
PASS: backend readiness, frontend health and login page
PASS: exact rescue image IDs restored; database unchanged
Release failed: docker compose exited with code 1. No database downgrade or restore performed.
Switched to a new branch 'recette-echec-smoke'
Failed candidate record: b10f5e82d38a-09c6c34210e2
PASS: backend readiness, frontend health and login page
PASS: exact rescue image IDs restored; database unchanged
Release failed: HTTP readiness/smoke failed.. No database downgrade or restore performed.
Switched to branch 'recette-a-reconciliee'
STEP: validate the private environment and explicit CLI model
Environment permissions and Compose configuration valid.
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
[+] up 2/2
 ✔ Container int129-vps-33c350b23010-backend-1  Healthy                                                                                                                0.6s
 ✔ Container int129-vps-33c350b23010-frontend-1 Healthy                                                                                                                0.6s
PASS: backend readiness, frontend health and login page
Already released; no rebuild or migration
dockge-dockge-1
active
true
root@22565:~#
```

### But et usage

| Cas / commande | But | Résultat réellement contrôlé |
|---|---|---|
| `git config` sans `--global` | Définir l'identité des commits dans la seule copie de recette | Pas de modification du profil Git global |
| `git switch -c … "$REVISION_A"` | Partir de la même base saine pour chaque panne | Les pannes précédentes ne se cumulent pas |
| Dockerfile `RUN … exit 42` | Provoquer un échec réel de construction | 42 dans le build, **1** pour la commande de release |
| `.Id` backend avant/après | Vérifier que le build raté n'a pas remplacé A | Assertion passée et marqueur A présent |
| `sed` du healthcheck | Rendre le candidat unhealthy sans inventer un échec du moteur Docker | `unhealthy`, record échoué, secours A |
| `location = /login { return 503; }` | Garder `/health` valide mais faire échouer un GET supplémentaire | `HTTP readiness/smoke failed`, record échoué, secours A |
| `grep -qiF` | Rechercher `unhealthy` littéralement et sans distinction de casse | Silence normal ; code non nul si la cause attendue manque |
| Retour final branche/env A | Éviter de rendre l'UI disponible sur une source défaillante | Rejeu sans build/migration, Caddy active, Dockge true |

**Bilan de cette page :** verrou, divergence de schéma et quatre familles
d'échecs vérifiés. Aucun de ces scénarios n'autorise à déduire un test réussi
de `--recover-from`, d'un arrêt brutal SIGKILL, d'une perte de disque ou d'une
restauration complète des services hôte. Ces événements n'ont pas été exercés.
