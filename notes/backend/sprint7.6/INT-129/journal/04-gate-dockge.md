# Journal 04 — Comparaison CLI/Dockge et Stop/Start réel

[Retour](03-garde-fous-et-echecs.md) · [Sommaire](../README.md) · [État et limites](05-etat-et-limites.md)

Cette page conserve aussi le **blocage intermédiaire**, son diagnostic et
la preuve utilisée pour le résoudre. On n'a pas rendu un contrôle vert en
ignorant arbitrairement les différences.

## 1. Premier contrôle de l'état A : pas encore une preuve UI

### Bloc de contrôle envoyé

Ce bloc a été exécuté une première fois sans confirmation du Stop/Start UI,
puis à nouveau après celui-ci. Il est reproduit ici une fois ; les deux
sorties sont conservées dans cette page.

```sh
(
set -eu
PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"

test -z "$(git -C "$CHECKOUT" status --porcelain)"
test ! -s "$CHECKOUT/.env"

docker ps -a \
  --format '{{.Names}} | {{.Label "com.docker.compose.project"}} | {{.Status}}'

docker inspect --format \
  '{{.Name}} image={{.Image}} compose={{index .Config.Labels "com.docker.compose.project.config_files"}}' \
  "$PROJECT-backend-1" "$PROJECT-frontend-1" "$PROJECT-postgres-1"

curl -fsS http://127.0.0.1:19829/health/ready
printf '\n'
curl -fsS http://127.0.0.1:19830/recipe-marker.txt
docker exec "$PROJECT-backend-1" \
  cat /app/uploads/photos/int129-fixture.txt

docker exec -i "$PROJECT-postgres-1" sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
SELECT count(*) FROM public.client
WHERE full_name = 'INT129 VPS fictif';
SQL
)
```

### Première sortie envoyée

```text
int129-vps-33c350b23010-backend-1 | int129-vps-33c350b23010 | Up 4 hours (healthy)
int129-vps-33c350b23010-frontend-1 | int129-vps-33c350b23010 | Up 4 hours (healthy)
int129-vps-33c350b23010-postgres-1 | int129-vps-33c350b23010 | Up 5 hours (healthy)
dockge-dockge-1 | dockge | Up 4 hours (healthy)
/int129-vps-33c350b23010-backend-1 image=sha256:24e9377d6247214c568109cd30165b971eeccf1866853f8d73381a8a1b2bd5a0 compose=/var/lib/tervo-int129/int129-vps-33c350b23010/9111a2a1ecbb-79b422c7d71f/compose.json
/int129-vps-33c350b23010-frontend-1 image=sha256:29a397ebb78b6d3cb76b039f1fd341e18c41b7727f9432fde917021d9b871103 compose=/var/lib/tervo-int129/int129-vps-33c350b23010/9111a2a1ecbb-79b422c7d71f/compose.json
/int129-vps-33c350b23010-postgres-1 image=sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3 compose=/opt/stacks/int129-vps-33c350b23010/deploy/docker-compose.yml
{"status":"ready"}
release A
INT129 VPS upload fictif
1
root@22565:~#
```

### But et usage

| Contrôle | But | Interprétation à ce stade |
|---|---|---|
| `git status --porcelain` vide | Détecter une modification suivie cachée depuis l'UI | Le bloc a continué : contrôle passé |
| `test ! -s .env` racine | Refuser une deuxième source d'environnement non vide | Silence normal, code 0 |
| Labels projet | Vérifier qu'il n'y a pas deux orchestrations concurrentes avec des noms différents | Un projet de recette et Dockge |
| `.Image` | Vérifier l'artefact réellement démarré | Images A exactes |
| `config_files` | Identifier le modèle ayant servi à créer les conteneurs | Encore le modèle de secours pour HTTP, normal après rollback |
| HTTP et données témoins | Vérifier disponibilité et persistance | A saine ; cela **ne démontrait pas encore** une action UI |

## 2. Comparaison stricte des deux modèles

### Commande envoyée puis exécutée — terminal root

```sh
python3 - <<'PY'
import json
import subprocess

project = "int129-vps-33c350b23010"
root = "/opt/stacks/" + project
commands = [
    ["docker", "compose", "--env-file", root + "/deploy/.env",
     "-p", project, "-f", root + "/deploy/docker-compose.yml",
     "--profile", "tools", "config", "--format", "json"],
    ["docker", "exec", "-w", root, "dockge-dockge-1",
     "docker", "compose", "-p", project, "-f", root + "/compose.yaml",
     "--profile", "tools", "config", "--format", "json"],
]
models = []
for number, command in enumerate(commands, 1):
    result = subprocess.run(command, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SystemExit(
            f"GATE BLOQUE : configuration {number} refusée, code {result.returncode}")
    model = json.loads(result.stdout)
    models.append({k: v for k, v in model.items() if not k.startswith("x-")})

if models[0] != models[1]:
    raise SystemExit("GATE BLOQUE : configurations CLI et Dockge différentes.")
print("PASS: configurations CLI et Dockge identiques.")
PY
```

### Résultat envoyé

```text
GATE BLOQUE : configurations CLI et Dockge différentes.
root@22565:~#
```

### But et usage

| Commande / mécanisme | But | Conséquence |
|---|---|---|
| Premier `docker compose … config` | Résoudre le modèle par la CLI hôte, env explicite | Aucun service lancé |
| `docker exec -w … dockge … compose` | Utiliser le Compose réellement installé dans la console, au même chemin absolu | Ne pas présumer les deux versions équivalentes |
| `--profile tools` | Inclure `migrate` dans le modèle comparé | Ne le démarre pas |
| `--format json` capturé dans `PIPE` | Comparer sans exposer les secrets interpolés | Aucun JSON complet imprimé ou committé |
| Retrait des seules extensions `x-*` | Écarter les éléments d'écriture YAML qui ne sont pas des ressources runtime | Pas de retrait des flags de sécurité |
| Refus si différence | Ne pas adopter une configuration non qualifiée dans l'UI | Stop/Start différé, stack A laissée saine |

## 3. Localiser la différence sans afficher les secrets

### Commande envoyée et exécutée

```sh
python3 - <<'PY'
import json
import subprocess

project = "int129-vps-33c350b23010"
root = "/opt/stacks/" + project
commands = [
    ["docker", "compose", "--env-file", root + "/deploy/.env",
     "-p", project, "-f", root + "/deploy/docker-compose.yml",
     "--profile", "tools", "config", "--format", "json"],
    ["docker", "exec", "-w", root, "dockge-dockge-1",
     "docker", "compose", "-p", project, "-f", root + "/compose.yaml",
     "--profile", "tools", "config", "--format", "json"],
]

models = []
for number, command in enumerate(commands, 1):
    result = subprocess.run(command, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SystemExit(
            f"Configuration {number} refusée, code {result.returncode}")
    model = json.loads(result.stdout)
    models.append({k: v for k, v in model.items() if not k.startswith("x-")})

def differences(a, b, path=""):
    if a == b:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            location = f"{path}.{key}" if path else key
            if key not in a:
                print(location + " : présent seulement côté Dockge")
            elif key not in b:
                print(location + " : présent seulement côté CLI")
            else:
                differences(a[key], b[key], location)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            print(path + " : nombres d'éléments différents")
        for index, (left, right) in enumerate(zip(a, b)):
            differences(left, right, f"{path}[{index}]")
    else:
        print(f"{path} : valeurs différentes "
              f"(CLI={type(a).__name__}, Dockge={type(b).__name__})")

differences(*models)
PY
```

### Résultat envoyé

```text
services.postgres.volumes[1].bind.create_host_path : présent seulement côté CLI
services.postgres.volumes[2].bind.create_host_path : présent seulement côté CLI
```

### But et usage

| Élément | But | Ce qu'on peut conclure |
|---|---|---|
| Parcours récursif des modèles | Identifier les chemins qui diffèrent, y compris les listes | Deux flags seulement |
| Pas de valeurs affichées | Protéger notamment `SECRET_KEY` et mots de passe DB | Les noms/type/présence suffisent pour le premier diagnostic |
| `create_host_path: false` dans le source | Refuser un bind si le fichier SQL source manque | L'omission JSON ne prouve pas encore le même comportement runtime |

L'utilisateur a demandé si ce diagnostic était possible avec les services
actifs : oui, ces deux commandes `config` lisent les modèles et ne modifient
aucun service. Aucune nouvelle action UI n'a été demandée à ce stade.

## 4. Vérifier réellement le garde-fou du bind

### Bloc envoyé et exécuté

Projet distinct, image frontend A déjà présente, aucun port ni réseau
applicatif, aucun build ou téléchargement. La commande du conteneur était
`true` ; le montage devait être refusé avant de pouvoir l'exécuter.

```sh
(
set -eu
umask 077

PROBE="int129-bind-$(openssl rand -hex 6)"
DIR="/opt/stacks/.$PROBE"
install -d -m 700 "$DIR"

cat > "$DIR/compose.yaml" <<'YAML'
include:
  - path: ./probe.yaml
YAML

cat > "$DIR/probe.yaml" <<'YAML'
services:
  probe:
    image: sha256:29a397ebb78b6d3cb76b039f1fd341e18c41b7727f9432fde917021d9b871103
    command: ["true"]
    network_mode: none
    volumes:
      - type: bind
        source: ./source-absente.sql
        target: /probe.sql
        read_only: true
        bind:
          create_host_path: false
YAML

RC=0
docker exec -w "$DIR" dockge-dockge-1 \
  docker compose -p "$PROBE" -f "$DIR/compose.yaml" \
  run --rm --no-deps --pull never probe \
  > "$DIR/resultat.log" 2>&1 || RC=$?

cat "$DIR/resultat.log"
printf 'Code observé : %s\n' "$RC"

test "$RC" -ne 0
grep -qF 'bind source path does not exist' "$DIR/resultat.log"
test ! -e "$DIR/source-absente.sql"

# Nettoyage limité à ce contrôle jetable.
docker compose -p "$PROBE" -f "$DIR/compose.yaml" down --volumes
rm -- "$DIR/compose.yaml" "$DIR/probe.yaml" "$DIR/resultat.log"
rmdir "$DIR"

echo "PASS: Dockge refuse la source absente sans créer de dossier."
)
```

### Résultat envoyé

```text
Error response from daemon: invalid mount config for type "bind": bind source path does not exist: /opt/stacks/.int129-bind-a732f9e4dd02/source-absente.sql
Code observé : 1
WARN[0000] Warning: No resource found to remove for project "int129-bind-a732f9e4dd02".
PASS: Dockge refuse la source absente sans créer de dossier.
root@22565:~#
```

### But et usage

| Commande / option | But | Résultat |
|---|---|---|
| Projet aléatoire distinct | Ne pas toucher à la stack A | `int129-bind-a732f9e4dd02` |
| `include` | Exercer le mécanisme utilisé par l'entrée Dockge de Tervo | Pas seulement un montage direct d'un fichier isolé |
| Image par ID, `--pull never` | Réutiliser un artefact présent, sans dépendre d'un téléchargement | Aucun nouveau build/pull |
| `network_mode: none`, aucun `ports` | Ne pas ouvrir de service | Pas d'impact réseau applicatif |
| `run --rm --no-deps` | Lancer le seul service de sonde et supprimer son conteneur après usage | Le daemon refuse le montage absent |
| Code non nul + message précis + `test ! -e` | Vérifier la cause **et** l'absence de création du dossier | Les trois contrôles ont passé |
| `down --volumes` du projet de sonde | Nettoyage limité à cette identité | Le WARN signifie qu'aucune ressource ne restait à supprimer |
| `rm` ciblé / `rmdir` | Retirer uniquement les fichiers de sonde puis le dossier vide | Sonde nettoyée ; ce n'est pas le nettoyage de la recette principale |

## 5. Comparaison ajustée, sans altérer le Compose

### Commande envoyée et exécutée

```sh
python3 - <<'PY'
import json
import subprocess

project = "int129-vps-33c350b23010"
root = "/opt/stacks/" + project
image = subprocess.check_output(
    ["docker", "inspect", "--format", "{{.Config.Image}}", "dockge-dockge-1"],
    text=True).strip()
if image != "louislam/dockge:1.5.0@sha256:335c6368b880ecc203236ed89e6e5232e0d6578e8ef5920e4a502390451502bf":
    raise SystemExit("GATE BLOQUE : version Dockge changée, qualification à refaire.")

commands = [
    ["docker", "compose", "--env-file", root + "/deploy/.env",
     "-p", project, "-f", root + "/deploy/docker-compose.yml",
     "--profile", "tools", "config", "--format", "json"],
    ["docker", "exec", "-w", root, "dockge-dockge-1",
     "docker", "compose", "-p", project, "-f", root + "/compose.yaml",
     "--profile", "tools", "config", "--format", "json"],
]
models = []
for number, command in enumerate(commands, 1):
    result = subprocess.run(command, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SystemExit(f"GATE BLOQUE : configuration {number} refusée.")
    model = json.loads(result.stdout)
    models.append({k: v for k, v in model.items() if not k.startswith("x-")})

for index, target in (
    (1, "/docker-entrypoint-initdb.d/10-app.sql"),
    (2, "/opt/tervo/app-grants.sql"),
):
    a = models[0]["services"]["postgres"]["volumes"][index]
    b = models[1]["services"]["postgres"]["volumes"][index]
    if (a.get("type") != "bind" or b.get("type") != "bind"
        or a.get("target") != target or b.get("target") != target
        or a.get("bind", {}).get("create_host_path") is not False):
        raise SystemExit("GATE BLOQUE : montage différent du cas qualifié.")
    b.setdefault("bind", {}).setdefault("create_host_path", False)

if models[0] != models[1]:
    raise SystemExit("GATE BLOQUE : autre différence de configuration.")
print("PASS: modèles équivalents, seules les deux omissions false qualifiées.")
PY
```

### Résultat envoyé

```text
PASS: modèles équivalents, seules les deux omissions false qualifiées.
```

### But et usage

| Règle | Justification | Limite |
|---|---|---|
| Vérifier la référence Dockge épinglée | Relier la tolérance au runtime effectivement testé | Une nouvelle version nécessite une nouvelle qualification |
| Vérifier type, cible et false source | Restreindre le traitement aux deux binds SQL identifiés | Pas de normalisation générale de tous les champs absents |
| `setdefault` en mémoire | Compléter l'omission ; ne pas écraser un éventuel true | Un true ou toute autre différence reste bloquant |
| Comparaison finale complète | Vérifier qu'il ne reste aucun autre écart | Les secrets restent en mémoire |
| Aucun fichier réécrit | Garder les garde-fous dans les fichiers opérationnels | **Ne jamais retirer false du Compose ou des artefacts de secours** |

## 6. Logs, Stop/Start depuis l'UI, puis contrôle terminal

### Actions demandées et effectuées

Après le PASS uniquement, via l'accès privé habituel à Dockge :

1. Ouvrir `int129-vps-33c350b23010`.
2. Consulter les logs.
3. Faire Stop/Arrêter, puis Start/Démarrer.
4. Attendre les services healthy ; ne pas utiliser Update/Edit/Delete.
5. Réexécuter le bloc de contrôle terminal de la section 1.

L'accès par tunnel est documenté dans le
[guide Dockge](../../../../../deploy/dockge/README.md#L28).
Il ne s'agissait ni d'une route Caddy publique ni d'une nouvelle installation
de console. Aucun mot de passe de l'interface n'a été partagé.

### Logs envoyés

Les séparateurs « after stop » / « after start » ci-dessous sont ceux du
compte rendu de l'opérateur, pas des lignes émises par Docker.

```text
backend-1   | INFO:     127.0.0.1:44072 - "GET /health/ready HTTP/1.1" 200 OK
backend-1   | INFO:     127.0.0.1:52168 - "GET /health/ready HTTP/1.1" 200 OK
backend-1   | INFO:     127.0.0.1:47576 - "GET /health/ready HTTP/1.1" 200 OK
backend-1   | INFO:     127.0.0.1:54752 - "GET /health/ready HTTP/1.1" 200 OK
backend-1   | INFO:     127.0.0.1:41810 - "GET /health/ready HTTP/1.1" 200 OK
backend-1   | INFO:     127.0.0.1:60332 - "GET /health/ready HTTP/1.1" 200 OK
backend-1   | INFO:     127.0.0.1:60002 - "GET /health/ready HTTP/1.1" 200 OK

---
## after stop
frontend-1 exited with code 0
backend-1 exited with code 0
postgres-1  | 2026-10-15 15:54:50.609 UTC [1] LOG:  received fast shutdown request
postgres-1  | 2026-10-15 15:54:50.612 UTC [1] LOG:  aborting any active transactions
postgres-1  | 2026-10-15 15:54:50.620 UTC [1] LOG:  background worker "logical replication launcher" (PID 70) exited with exit code 1
postgres-1  | 2026-10-15 15:54:50.622 UTC [65] LOG:  shutting down
postgres-1  | 2026-10-15 15:54:50.627 UTC [65] LOG:  checkpoint starting: shutdown immediate
postgres-1  | 2026-10-15 15:54:50.643 UTC [65] LOG:  checkpoint complete: wrote 0 buffers (0.0%); 0 WAL file(s) added, 0 removed, 0 recycled; write=0.006 s, sync=0.001 s, total=0.021 s; sync files=0, longest=0.000 s, average=0.000 s; distance=0 kB, estimate=872 kB; lsn=0/1AE3E68, redo lsn=0/1AE3E68
postgres-1  | 2026-10-15 15:54:50.660 UTC [1] LOG:  database system is shut down
postgres-1 exited with code 0

----
## after start
at 2026-10-15 15:54:50 UTC
postgres-1  | 2026-10-15 15:55:39.646 UTC [1] LOG:  database system is ready to accept connections
backend-1   | INFO:     Started server process [1]
backend-1   | INFO:     Waiting for application startup.
backend-1   | INFO:     Application startup complete.
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
backend-1   | INFO:     127.0.0.1:46540 - "GET /health/ready HTTP/1.1" 200 OK
```

### Résultat terminal envoyé après Stop/Start

```text
int129-vps-33c350b23010-backend-1 | int129-vps-33c350b23010 | Up About a minute (healthy)
int129-vps-33c350b23010-postgres-1 | int129-vps-33c350b23010 | Up About a minute (healthy)
int129-vps-33c350b23010-frontend-1 | int129-vps-33c350b23010 | Up About a minute (healthy)
dockge-dockge-1 | dockge | Up 5 hours (healthy)
/int129-vps-33c350b23010-backend-1 image=sha256:24e9377d6247214c568109cd30165b971eeccf1866853f8d73381a8a1b2bd5a0 compose=/opt/stacks/int129-vps-33c350b23010/compose.yaml
/int129-vps-33c350b23010-frontend-1 image=sha256:29a397ebb78b6d3cb76b039f1fd341e18c41b7727f9432fde917021d9b871103 compose=/opt/stacks/int129-vps-33c350b23010/compose.yaml
/int129-vps-33c350b23010-postgres-1 image=sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3 compose=/opt/stacks/int129-vps-33c350b23010/compose.yaml
{"status":"ready"}
release A
INT129 VPS upload fictif
1
root@22565:~#
```

### But et usage

| Observation | Interprétation correcte | Ce qu'elle ne prouve pas |
|---|---|---|
| Logs visibles dans Dockge | La console consulte la vraie stack Tervo de recette | Pas une simple démo étrangère sans volumes |
| PostgreSQL parent exit 0 après checkpoint | Arrêt propre | Le worker arrêté avec exit 1 pendant la fermeture n'est pas à lui seul une panne du serveur |
| `ready to accept connections`, API 200 | Reprise fonctionnelle après Start | Pas une preuve de restauration après perte du serveur |
| Trois `config_files` sur le wrapper racine | Les services sont désormais associés à l'entrée réellement utilisée par Dockge | Les anciennes lectures du modèle de secours ne suffisaient pas |
| Images A inchangées | Pas de rebuild présenté comme identique | Pas une preuve universelle pour toute version future de Compose |
| Client `1`, upload et marqueur A | Données et contenu conservés dans ce parcours | Pas une validation de données de production inexistantes |
| Uvicorn `0.0.0.0:8000` | Écoute dans le conteneur ; les publications hôte restent loopback dans le modèle | Ne signifie pas que le port 8000 du VPS a été ouvert publiquement |

**Conclusion fonctionnelle : gate Dockge validé pour la configuration/version
qualifiée.** Aucun nouveau test fonctionnel n'a été demandé après ces résultats.
À la fin de ce contrôle UI, le nettoyage restait à effectuer ; sa clôture
sur retour opérateur est consignée dans le [journal 05](05-etat-et-limites.md).
