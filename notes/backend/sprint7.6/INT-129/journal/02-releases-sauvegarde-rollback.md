# Journal 02 — Release A, upgrade B, sauvegarde et rollback

[Préparation](01-acces-et-preparation.md) · [Sommaire](../README.md) · [Suite : garde-fous](03-garde-fous-et-echecs.md)

Tous les blocs ci-dessous ont été envoyés pour le **terminal root du VPS**,
sur la copie jetable `int129-vps-33c350b23010`. Ne pas les rejouer : ils
modifient la recette. Les `...` des sorties ci-dessous étaient déjà présents
dans les retours de l'utilisateur ; les lignes manquantes ne sont pas inventées.

## 1. Première release A

### Bloc envoyé et exécuté

Précondition annoncée : aucune opération Dockge concurrente, interface fermée.
Dockge allait être arrêté pendant la release, puis repris en cas de succès.
Caddy n'était pas arrêté pour cette première installation vide.

```sh
(
set -eu
umask 077

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
ENV_FILE="$CHECKOUT/deploy/.env"
STATE_DIR="/var/lib/tervo-int129/$PROJECT"
REVISION="$(git -C "$CHECKOUT" rev-parse HEAD)"

test "$REVISION" = 9111a2a1ecbb010cf9033c7300ca49193d0fd34a

if [ -e "$ENV_FILE" ] || [ -L "$ENV_FILE" ] || [ -e "$STATE_DIR" ]; then
  echo "Configuration ou état déjà présent : arrêt sans écrasement."
  exit 1
fi

ADMIN_PASSWORD="$(openssl rand -hex 24)"
APP_PASSWORD="$(openssl rand -hex 24)"
APP_SECRET="$(openssl rand -hex 32)"

cat > "$ENV_FILE" <<EOF
TERVO_IMAGE_TAG=$REVISION
TERVO_VCS_REF=$REVISION
TERVO_DB_NAME=tervo_db
TERVO_DB_ADMIN_USER=tervo_admin
TERVO_DB_ADMIN_PASSWORD=$ADMIN_PASSWORD
TERVO_DB_USER=tervo_app
TERVO_DB_PASSWORD=$APP_PASSWORD
SECRET_KEY=$APP_SECRET
FRONTEND_ORIGIN=https://recipe.invalid
VITE_API_BASE_URL=https://api.recipe.invalid/api/v1
BACKEND_PORT=19829
FRONTEND_PORT=19830
EOF

chmod 600 "$ENV_FILE"
install -d -m 700 "$STATE_DIR"

python3 "$CHECKOUT/deploy/scripts/release.py" deploy \
  --checkout "$CHECKOUT" \
  --env-file "$ENV_FILE" \
  --project "$PROJECT" \
  --state-dir "$STATE_DIR" \
  --lock-file /run/lock/tervo-operations.lock \
  --dockge-container dockge-dockge-1 \
  --console-idle-confirmed \
  --maintenance-confirmed \
  --revision "$REVISION"
)
```

### Résultat envoyé — extrait abrégé par l'opérateur

```text
STEP: validate the private environment and explicit CLI model
Environment permissions and Compose configuration valid.
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
STEP: build once while the previous API is still available
[+] Building 105.8s (39/39) FINISHED
 => [internal] load local bake definitions                                                                                                                            0.0s
 => => reading from stdin 1.38kB                                                                                                                                      0.0s
 => [backend internal] load build defini
...
...
 => [frontend] resolving provenance for metadata file                                                                                                                 0.0s
 => [backend] resolving provenance for metadata file                                                                                                                  0.0s
[+] build 2/2
 ✔ Image tervo-frontend:9111a2a1ecbb010cf9033c7300ca49193d0fd34a Built                                                                                               106.4s
 ✔ Image tervo-backend:9111a2a1ecbb010cf9033c7300ca49193d0fd34a  Built                                                                                               106.3s
[+] up 19/19
 ✔ Image postgres:17.11@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3 Pulled                                                                18.3s
 ✔ Network int129-vps-33c350b23010_database                                                     Created                                                                0.2s
 ✔ Volume int129-vps-33c350b23010_postgres_data                                                 Created                                                                0.0s
 ✔ Container int129-vps-33c350b23010-postgres-1                                                 Healthy                                                                7.6s
[+] create 5/5
 ✔ Container int129-vps-33c350b23010-postgres-1 Running                                                                                                                0.0s
 ✔ Network int129-vps-33c350b23010_frontend     Created                                                                                                                0.2s
 ✔ Volume int129-vps-33c350b23010_uploads_data  Created                                                                                                                0.0s
 ✔ Container int129-vps-33c350b23010-backend-1  Created                                                                                                                0.3s
 ✔ Container int129-vps-33c350b23010-frontend-1 Created                                                                                                                0.2s
STEP: migrate, grant and check before starting HTTP services
Container int129-vps-33c350b23010-migrate-run-f4dc00d3346b Creating
Container int129-vps-33c350b23010-migrate-run-f4dc00d3346b Created
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 9b55bf942f2a, initial empty schema
INFO  [alembic.runtime.migration] Running upgrade 9b55bf942f2a -> 24b96d6f9dfa, add user table
...
...
GRANT
GRANT
GRANT
GRANT
GRANT
GRANT
REVOKE
COMMIT
[+] up 2/2
 ✔ Container int129-vps-33c350b23010-backend-1  Healthy                                                                                                               27.0s
 ✔ Container int129-vps-33c350b23010-frontend-1 Healthy                                                                                                                6.5s
PASS: backend readiness, frontend health and login page
PASS: release 9111a2a1ecbb-79b422c7d71f
root@22565:~#
```

### But et usage

| Commande / argument | But et précaution | Retour / fichier contrôlé |
|---|---|---|
| `umask 077` | Protéger les nouveaux fichiers et dossiers | Silence normal ; env 600 et état 700 |
| `test "$REVISION" = …` | Refuser un checkout différent de celui préparé | Silence, code 0 attendu ; sinon arrêt du bloc |
| Refus env/état préexistants | Ne pas écraser des secrets ou prétendre qu'une base existante est neuve | Aucune écriture si le garde-fou échoue |
| `openssl rand -hex 24` deux fois | Générer deux mots de passe DB distincts, 24 octets chacun | Valeurs capturées dans des variables, jamais consignées |
| `openssl rand -hex 32` | Générer le secret applicatif | 32 octets aléatoires ; aucune valeur affichée |
| Heredoc `<<EOF` | Écrire le fichier en substituant les variables | Ce n'est pas un `.env` avec `$APP_PASSWORD` littéral |
| `--checkout`, `--revision` | Associer le build à une source Git propre et explicite | SHA complet, contrôlé aussi dans le label des images |
| `--env-file`, `--project` | Garder la même configuration et le même espace de noms partout | Pas de projet `tervo` implicite ni de `.env` concurrent |
| `--state-dir` | Conserver records, modèles résolus et backups privés hors Git | Contient des secrets ; ne pas partager les JSON |
| `--lock-file` | Partager le verrou avec le backup | Coordination coopérative, pas un RBAC contre root |
| `--dockge-container` | Identifier la console à geler | Référence d'image et chemins contrôlés |
| Deux confirmations | Déclarer la fenêtre sans écrivains/opération concurrente | Elles ne configurent pas automatiquement Caddy ni les permissions |
| `deploy` | Build → DB prête → migration/grants → HTTP → GET → record | Les deux `PASS` finaux, pas seulement la fin du build |

Les domaines `.invalid` étaient fictifs. Les ports hôte étaient loopback.
Cette première release ne sauvegardait pas une DB inexistante et ne créait
aucun compte admin métier par seed.

## 2. Ajouter des données fictives et déployer B

### Bloc envoyé et exécuté

Interruption de Dockge pendant la release et de Caddy pendant la capture
annoncée avant l'exécution. B ne changeait que les marqueurs, pas le schéma.

```sh
(
set -eu
umask 077

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
ENV_FILE="$CHECKOUT/deploy/.env"
STATE_DIR="/var/lib/tervo-int129/$PROJECT"

test "$(git -C "$CHECKOUT" rev-parse HEAD)" = \
  9111a2a1ecbb010cf9033c7300ca49193d0fd34a
test "$(docker inspect --format '{{.State.Running}}' dockge-dockge-1)" = true
systemctl is-active --quiet caddy

# Données fictives à conserver pendant l'upgrade et le rollback.
docker exec -i "$PROJECT-postgres-1" sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
INSERT INTO public.client (full_name, phone, address)
VALUES ('INT129 VPS fictif', '0000000000', 'Recette uniquement');
SQL

printf 'INT129 VPS upload fictif\n' |
  docker exec -i "$PROJECT-backend-1" sh -c \
    'cat > /app/uploads/photos/int129-fixture.txt'

# B change seulement les marqueurs de recette.
printf 'release B\n' > "$CHECKOUT/backend/app/recipe_marker.txt"
printf 'release B\n' > "$CHECKOUT/frontend/public/recipe-marker.txt"

git -C "$CHECKOUT" add \
  backend/app/recipe_marker.txt frontend/public/recipe-marker.txt
GIT_EDITOR=true git -C "$CHECKOUT" \
  -c user.name="INT129 recipe" \
  -c user.email="recipe@localhost" \
  commit -q -m "INT129 VPS recipe B"

REVISION="$(git -C "$CHECKOUT" rev-parse HEAD)"
sed -i \
  -e "s/^TERVO_IMAGE_TAG=.*/TERVO_IMAGE_TAG=$REVISION/" \
  -e "s/^TERVO_VCS_REF=.*/TERVO_VCS_REF=$REVISION/" \
  "$ENV_FILE"
chmod 600 "$ENV_FILE"

python3 "$CHECKOUT/deploy/scripts/release.py" deploy \
  --checkout "$CHECKOUT" \
  --env-file "$ENV_FILE" \
  --project "$PROJECT" \
  --state-dir "$STATE_DIR" \
  --lock-file /run/lock/tervo-operations.lock \
  --dockge-container dockge-dockge-1 \
  --console-idle-confirmed \
  --maintenance-confirmed \
  --revision "$REVISION"

systemctl is-active caddy
docker inspect --format '{{.State.Running}}' dockge-dockge-1
curl --fail --silent --show-error \
  http://127.0.0.1:19830/recipe-marker.txt
)
```

### Résultat envoyé — extrait abrégé par l'opérateur

Les chevrons de citation Markdown de certaines lignes ont été retirés.

```text
INSERT 0 1
STEP: validate the private environment and explicit CLI model
Environment permissions and Compose configuration valid.
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
STEP: build once while the previous API is still available
[+] Building 26.3s (39/39) FINISHED
 => [internal] load local bake definitions
...
...
[+] build 2/2
 ✔ Image tervo-backend:da8cfb3bd9f2a9efefe283b20edf905e1518e1b1  Built                                                                                                26.6s
 ✔ Image tervo-frontend:da8cfb3bd9f2a9efefe283b20edf905e1518e1b1 Built                                                                                                26.6s
[+] up 1/1
 ✔ Container int129-vps-33c350b23010-postgres-1 Healthy                                                                                                                0.5s
[+] stop 2/2
 ✔ Container int129-vps-33c350b23010-frontend-1 Stopped                                                                                                                0.5s
 ✔ Container int129-vps-33c350b23010-backend-1  Stopped                                                                                                                1.7s
[+] create 3/3
 ✔ Container int129-vps-33c350b23010-postgres-1 Running                                                                                                                0.0s
 ✔ Container int129-vps-33c350b23010-frontend-1 Recreated                                                                                                              0.2s
 ✔ Container int129-vps-33c350b23010-backend-1  Recreated                                                                                                              0.4s
STEP: migrate, grant and check before starting HTTP services
Container int129-vps-33c350b23010-migrate-run-6e2212570cf7 Creating
Container int129-vps-33c350b23010-migrate-run-6e2212570cf7 Created
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
BEGIN
GRANT
GRANT
GRANT
GRANT
GRANT
...
...
GRANT
GRANT
GRANT
REVOKE
COMMIT
[+] up 2/2
 ✔ Container int129-vps-33c350b23010-backend-1  Healthy                                                                                                               27.2s
 ✔ Container int129-vps-33c350b23010-frontend-1 Healthy                                                                                                                5.7s
PASS: backend readiness, frontend health and login page
PASS: release da8cfb3bd9f2-b84d560c73d5
active
true
release B
```

### But et usage

| Commande / option | But | Observation / conduite en cas d'erreur |
|---|---|---|
| `systemctl … --quiet` | Vérifier Caddy actif sans sortie | Silence normal avant la recette ; un code non nul arrêtait le bloc |
| `docker exec -i … psql` | Transmettre le SQL à la DB de recette | `INSERT 0 1` : une ligne insérée |
| `ON_ERROR_STOP=1` | Refuser une poursuite silencieuse après erreur SQL | Une erreur aurait arrêté le bloc |
| `<<'SQL'` | Empêcher le shell hôte de substituer le contenu SQL | Les identifiants DB du `sh -c` sont lus dans le conteneur |
| `printf … \| docker exec -i … cat > fichier` | Créer un upload témoin dans le volume, pas dans le checkout | Silence normal ; contenu contrôlé plus tard |
| Deux marqueurs + commit | Rendre les contenus A et B réellement différents | Pas seulement deux labels sur un contenu identique |
| `sed -i` | Modifier uniquement tag et SHA de l'env privé | Silence normal, secrets DB inchangés |
| `deploy` sans adaptateur | Utiliser le vrai backup privilégié avant migration | Le code a vérifié le bundle avant de poursuivre |
| `active`, `true` | Contrôler la reprise des services hôte | Caddy actif, conteneur Dockge démarré |
| `curl --fail --silent --show-error` | Lire le marqueur HTTP et échouer sur erreur HTTP | `release B`, pas un succès supposé parce qu'un conteneur tourne |

## 3. Vérifier le backup et revenir exactement à A

### Bloc envoyé et exécuté

```sh
(
set -eu

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
STATE_DIR="/var/lib/tervo-int129/$PROJECT"
RELEASE_A=9111a2a1ecbb-79b422c7d71f
RELEASE_B=da8cfb3bd9f2-b84d560c73d5
BUNDLE="$STATE_DIR/$RELEASE_B/before-migration.tar"

PG_BEFORE="$(docker inspect --format '{{.Id}}' "$PROJECT-postgres-1")"

# Vérification du bundle, sans afficher son contenu privé.
python3 "$CHECKOUT/deploy/scripts/snapshot.py" verify --bundle "$BUNDLE"
stat -c 'Backup : permissions=%a octets=%s' "$BUNDLE"

python3 "$CHECKOUT/deploy/scripts/release.py" rollback \
  --checkout "$CHECKOUT" \
  --env-file "$CHECKOUT/deploy/.env" \
  --project "$PROJECT" \
  --state-dir "$STATE_DIR" \
  --lock-file /run/lock/tervo-operations.lock \
  --dockge-container dockge-dockge-1 \
  --console-idle-confirmed \
  --maintenance-confirmed \
  --release-id "$RELEASE_A"

# Comparer les images réellement utilisées aux IDs du record A.
python3 -c '
import json, sys
r = json.load(open(sys.argv[1]))
for service in ("backend", "frontend"):
    print(service, "attendu :", r["images"][service])
' "$STATE_DIR/$RELEASE_A/record.json"

docker inspect --format '{{.Name}} {{.Image}}' \
  "$PROJECT-backend-1" "$PROJECT-frontend-1"

test "$(docker inspect --format '{{.Id}}' "$PROJECT-postgres-1")" = "$PG_BEFORE"
echo "Conteneur PostgreSQL inchangé."

echo "Client fictif présent — attendu : 1"
docker exec -i "$PROJECT-postgres-1" sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
SELECT count(*) FROM public.client
WHERE full_name = 'INT129 VPS fictif'
  AND phone = '0000000000'
  AND address = 'Recette uniquement';
SQL

echo "Upload conservé :"
docker exec "$PROJECT-backend-1" \
  cat /app/uploads/photos/int129-fixture.txt

echo "Version servie :"
curl --fail --silent --show-error \
  http://127.0.0.1:19830/recipe-marker.txt

echo "Branche Git toujours attachée :"
git -C "$CHECKOUT" symbolic-ref --short HEAD

echo "État Caddy puis Dockge :"
systemctl is-active caddy
docker inspect --format '{{.State.Running}}' dockge-dockge-1
)
```

### Résultat envoyé

```text
Bundle checksums valid.
Backup : permissions=600 octets=204800
STEP: validate the private environment and explicit CLI model
Environment permissions and Compose configuration valid.
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
[+] up 2/2
 ✔ Container int129-vps-33c350b23010-backend-1  Healthy                                                                                                               18.2s
 ✔ Container int129-vps-33c350b23010-frontend-1 Healthy                                                                                                                7.7s
PASS: backend readiness, frontend health and login page
PASS: exact rescue image IDs restored; database unchanged
Console remains frozen; reconcile Git/env with the active rescue record before restart.
backend attendu : sha256:24e9377d6247214c568109cd30165b971eeccf1866853f8d73381a8a1b2bd5a0
frontend attendu : sha256:29a397ebb78b6d3cb76b039f1fd341e18c41b7727f9432fde917021d9b871103
/int129-vps-33c350b23010-backend-1 sha256:24e9377d6247214c568109cd30165b971eeccf1866853f8d73381a8a1b2bd5a0
/int129-vps-33c350b23010-frontend-1 sha256:29a397ebb78b6d3cb76b039f1fd341e18c41b7727f9432fde917021d9b871103
Conteneur PostgreSQL inchangé.
Client fictif présent — attendu : 1
1
Upload conservé :
INT129 VPS upload fictif
Version servie :
release A
Branche Git toujours attachée :
master
État Caddy puis Dockge :
active
false
root@22565:~#
```

### But et usage

| Commande / donnée | But | Résultat et limite |
|---|---|---|
| `snapshot.py verify` | Vérifier les membres du bundle et leurs checksums | Succès observé ; **pas** un test de restauration des services hôte |
| `stat -c %a/%s` | Lire permissions et taille sans ouvrir le contenu | 600, 204 800 octets |
| `rollback --release-id` | Reprendre le record A et ses images exactes | Aucun rebuild ni restauration de DB |
| Lecture ciblée de `record.json` | Afficher seulement les IDs attendus | Ne pas afficher `compose.json`, qui contient les secrets |
| `.Image` | Identifier l'image réellement utilisée par un conteneur | IDs complets égaux aux valeurs attendues |
| `.Id` PostgreSQL avant/après | Distinguer persistance du conteneur et simple nom identique | Conteneur PostgreSQL inchangé lors de ce rollback |
| `psql -At` | Sortie sans tableau ni en-tête pour le contrôle de ligne | `1` observé |
| `symbolic-ref --short HEAD` | Vérifier que Git reste sur une branche | `master`, encore B ; le rollback ne change pas Git |
| Dockge `false` | Prévenir une relance de B par l'UI alors que les services sont A | Arrêt volontaire, pas panne ; réconciliation dans le journal suivant |

Le bundle contient des paramètres Caddy/Dockge réels et reste privé sur le VPS.
Il n'a été ni publié, ni copié sur mini-s1, ni utilisé pour une restauration
réelle des services hôte dans cette recette.
