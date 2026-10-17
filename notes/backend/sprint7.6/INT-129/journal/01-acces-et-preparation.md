# Journal 01 — Accès au VPS et préparation de la copie

[Sommaire INT-129](../README.md) · [Suite : releases et rollback](02-releases-sauvegarde-rollback.md)

Ce journal archive les commandes d'exploitation et les résultats disponibles,
pas une procédure à rejouer. Les blocs envoyés à l'opérateur sont conservés
avec leur cible. Les prompts ne sont pas des commandes à saisir. Aucune valeur
de mot de passe ou de clé privée n'est reproduite.

## 1. Charger temporairement la clé — poste local

### Commande

```sh
ssh-add -t 2h "$HOME/.ssh/tervo_ed25519"
```

### Résultat envoyé

```text
Enter passphrase for /home/lob/.ssh/tervo_ed25519:
Identity added: /home/lob/.ssh/tervo_ed25519 (tervo-vps)
Lifetime set to 7200 seconds
```

Cette commande a été répétée lorsque l'accès temporaire a été proposé.
Elle n'a pas changé les permissions sudo du compte distant.

### But et usage

| Élément | Explication | Retour / contrôle |
|---|---|---|
| `ssh-add` | Ajoute une identité à l'agent SSH du poste local | Code 0 ; identité disponible pour les nouvelles connexions |
| `-t 2h` | Durée de conservation de cette identité dans l'agent | `7200 seconds` observé |
| `$HOME/.ssh/tervo_ed25519` | Fichier privé du poste local ; on ne le copie pas dans le chat ou sur le VPS | Passphrase saisie uniquement dans le terminal |
| Limite | Authentifier `tervo` n'accorde pas les privilèges root | Le contrôle sudo ci-dessous a encore échoué |

## 2. Préflight effectué par l'agent — lecture seule

### Commande

Depuis le poste où se trouvait l'agent, avec la clé chargée :

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 \
  -o ControlPath=none tervo@151.241.228.152 \
  'printf "=== Identity ===\n"; id;
   printf "=== Host ===\n"; hostname;
   printf "=== Disk ===\n"; df -h / /opt;
   printf "=== Tools ===\n"; command -v python3; command -v git;
   docker compose version;
   printf "=== Privileges ===\n";
   if sudo -n true; then
     printf "sudo noninteractive available\n";
   else
     printf "sudo requires interactive authentication\n";
   fi;
   printf "=== Services ===\n"; systemctl is-active ssh docker caddy;
   printf "=== Containers ===\n";
   docker ps -a --format "{{.Names}} {{.Status}}"'
```

### Résultat observé par l'outil

```text
=== Identity ===
uid=1000(tervo) gid=1000(tervo) groups=1000(tervo),27(sudo),100(users)
=== Host ===
22565
=== Disk ===
Filesystem           Size  Used Avail Use% Mounted on
/dev/mapper/hk-root  115G  8.1G  102G   8% /
/dev/mapper/hk-root  115G  8.1G  102G   8% /
=== Tools ===
/usr/bin/python3
/usr/bin/git
Docker Compose version v5.6.0
=== Privileges ===
sudo: a password is required
sudo requires interactive authentication
=== Services ===
active
active
active
=== Containers ===
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

Code global : **1**, à cause du dernier accès Docker refusé. Le message sudo
est reproduit sans le masquage automatique du mot « password » par l'outil ;
aucune valeur secrète n'avait été affichée.

### But et usage

| Commande / option | But | Interprétation |
|---|---|---|
| `BatchMode=yes` | Refuser une demande interactive dans la session de l'agent | Un besoin de saisie devient une erreur, pas un terminal bloqué |
| `StrictHostKeyChecking=yes` | Exiger une identité d'hôte déjà approuvée | Pas d'acceptation aveugle d'une nouvelle empreinte |
| `ConnectTimeout=10` | Borner l'établissement de la connexion | Ne borne pas toute la durée d'un déploiement |
| `ControlPath=none` | Ne pas réutiliser une connexion multiplexée existante | Vérifie une connexion neuve |
| `id`, `hostname` | Identifier le compte et la machine avant toute action | Compte `tervo`, VPS `22565`, pas root |
| `df -h / /opt` | Vérifier l'espace disponible | 102 Go disponibles ; `/opt` est sur le même filesystem |
| `command -v` | Vérifier la présence d'un exécutable sans l'installer | Python et Git disponibles |
| `sudo -n true` | Tester sudo sans mot de passe interactif | Refus : aucune permission n'a été ajoutée pour contourner cela |
| `systemctl is-active` | Lire l'état des services | SSH, Docker, Caddy actifs |
| `docker ps -a` | Inventorier aussi les conteneurs arrêtés | Refus pour ce compte ; pas une panne Docker |

Une seconde vérification a été faite après rechargement de la clé :

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 \
  -o ControlPath=none tervo@151.241.228.152 \
  'id;
   if sudo -n true; then
     printf "Temporary sudo access available\n";
     sudo -n docker ps -a --format "{{.Names}} | {{.Status}}";
   else
     printf "SSH authenticated; noninteractive sudo unavailable\n";
     exit 1;
   fi'
```

Résultat observé, code 1 :

```text
uid=1000(tervo) gid=1000(tervo) groups=1000(tervo),27(sudo),100(users)
sudo: a password is required
SSH authenticated; noninteractive sudo unavailable
```

Cela a conduit à utiliser le terminal privilégié de l'opérateur, pas à créer
une règle `NOPASSWD` ni à changer les permissions du socket Docker.

## 3. Inventaire privilégié — terminal de l'opérateur

### Commandes envoyées

```sh
ssh tervo@151.241.228.152

sudo docker ps -a \
  --format '{{.Names}} | {{.Image}} | {{.Status}}'

sudo ls -ld \
  /opt/stacks \
  /opt/dockge/compose.yaml \
  /opt/dockge/data \
  /etc/caddy \
  /var/lib/caddy

sudo systemctl show caddy \
  -p ActiveState \
  -p FragmentPath
```

### Résultat envoyé

```text
[sudo] password for tervo:
dockge-dockge-1 | louislam/dockge:1.5.0 | Up 2 days (healthy)
drwxr-x--- 2 root  caddy 4096 Oct 12 15:47 /etc/caddy
-rw-r--r-- 1 root  root   874 Oct 13 11:35 /opt/dockge/compose.yaml
drwx------ 2 root  root  4096 Oct 13 11:36 /opt/dockge/data
drwx------ 2 root  root  4096 Oct 13 23:37 /opt/stacks
drwx------ 3 caddy caddy 4096 Oct 12 16:20 /var/lib/caddy
ActiveState=active
FragmentPath=/etc/systemd/system/caddy.service
```

### But et usage

| Commande | But | Résultat et limite |
|---|---|---|
| `docker ps -a --format …` | Inventaire lisible sans afficher l'environnement des conteneurs | Seul Dockge apparaît, healthy |
| `ls -ld` | Examiner les dossiers eux-mêmes, pas leur contenu privé | Chemins présents et modes visibles ; pas de secret lu |
| `systemctl show … -p` | Lire uniquement les propriétés utiles | Caddy actif, unité dans `/etc/systemd/system` |
| `sudo` | Exécuter ces lectures avec les droits requis | Saisie dans le terminal opérateur ; ne débloque pas automatiquement sudo dans la session de l'agent |

## 4. Obtenir réellement le shell root

### Première tentative envoyée

```sh
ssh tervo@151.241.228.152
sudo -i
```

### Résultat envoyé

```text
Linux 22565 6.12.111+deb13-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.12.111-1 (2026-09-28) x86_64

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Thu Oct 15 12:25:11 2026 from 194.11.196.189
tervo@22565:~$
```

Cette sortie ne démontrait que la connexion SSH : le prompt était encore
celui de `tervo`. La commande suivante a donc été envoyée séparément,
**dans la session déjà connectée** :

```sh
sudo -i
id -u
```

Résultat envoyé :

```text
tervo@22565:~$ sudo -i
[sudo] password for tervo:
root@22565:~# id -u
0
root@22565:~#
```

### But et usage

| Élément | But | Ce qui est réellement prouvé |
|---|---|---|
| `sudo -i` | Ouvrir un shell de connexion administrateur | Le prompt passe à `root` ; `$HOME` devient normalement `/root` |
| `id -u` | Vérifier l'UID, sans se fier uniquement au prompt | `0` observé, succès |
| Commandes séparées | Attendre d'être dans la session distante avant l'élévation | Évite de croire qu'un collage avant l'ouverture SSH a déjà exécuté sudo |

## 5. Préparer et transférer la source — poste de l'agent

### Commandes exécutées

`DELTA_SCRATCH_DIR` désignait le répertoire temporaire de la session locale.
Ce bloc a exporté les sources suivies et les modifications INT-129, pas les
venvs, caches, données locales ou fichiers `.env` privés.

```sh
set -eu
umask 022
project="int129-vps-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
source_dir="$DELTA_SCRATCH_DIR/$project"
mkdir -p "$source_dir"
git archive HEAD .gitignore backend frontend deploy | tar -x -C "$source_dir"
git diff HEAD -- backend/Dockerfile compose.yaml deploy/docker-compose.yml \
  deploy/scripts/release.py deploy/scripts/snapshot.py |
  git -C "$source_dir" apply
mkdir -p "$source_dir/frontend/public"
printf 'release A\n' > "$source_dir/backend/app/recipe_marker.txt"
printf 'release A\n' > "$source_dir/frontend/public/recipe-marker.txt"
python3 - "$source_dir" <<'PY'
import ast
from pathlib import Path
import sys
root=Path(sys.argv[1])
for name in ('deploy/scripts/release.py','deploy/scripts/snapshot.py'):
    ast.parse((root/name).read_text())
assert not list(root.rglob('.env'))
assert not list(root.rglob('.git'))
assert (root/'deploy/postgres/init-app.sql').stat().st_mode & 0o444 == 0o444
print('Recipe source checked: current WIP deployment code, A markers, no private .env or Git metadata.')
PY
tar -C "$source_dir" -cf "$DELTA_SCRATCH_DIR/source.tar" .
sha256sum "$DELTA_SCRATCH_DIR/source.tar"
remote_dir=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ConnectTimeout=10 -o ControlPath=none tervo@151.241.228.152 \
  'umask 077; mktemp -d /home/tervo/int129-incoming.XXXXXXXX')
case "$remote_dir" in
  /home/tervo/int129-incoming.*) ;;
  *) printf 'Unexpected staging directory\n' >&2; exit 1 ;;
esac
scp -q -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ConnectTimeout=10 -o ControlPath=none \
  "$DELTA_SCRATCH_DIR/source.tar" "tervo@151.241.228.152:$remote_dir/source.tar"
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ConnectTimeout=10 -o ControlPath=none tervo@151.241.228.152 \
  "chmod 600 '$remote_dir/source.tar'; sha256sum '$remote_dir/source.tar'; stat -c '%a %s %n' '$remote_dir' '$remote_dir/source.tar'"
printf 'Recipe project: %s\nIncoming directory: %s\n' "$project" "$remote_dir"
```

### Résultat observé par l'outil

```text
Recipe source checked: current WIP deployment code, A markers, no private .env or Git metadata.
03530fc69c867ad46edf8a169ec535ac5751da3fddd9461c802ba33497a3cb6a  /tmp/delta-scratch-.delta-fs-AIlbYx/source.tar
03530fc69c867ad46edf8a169ec535ac5751da3fddd9461c802ba33497a3cb6a  /home/tervo/int129-incoming.xvq02T1h/source.tar
700 4096 /home/tervo/int129-incoming.xvq02T1h
600 2037760 /home/tervo/int129-incoming.xvq02T1h/source.tar
Recipe project: int129-vps-33c350b23010
Incoming directory: /home/tervo/int129-incoming.xvq02T1h
```

Code global observé : 0.

### But et usage

| Commande | But / précaution | Résultat attendu et constaté |
|---|---|---|
| `git archive HEAD …` | Exporter seulement les chemins suivis | Pas de copie de tout le disque de travail |
| `git diff HEAD … \| git … apply` | Ajouter les modifications WIP INT-129 à l'export de recette | Le script testé n'était pas encore dans un commit de livraison |
| `umask 022` | Conserver les fichiers SQL lisibles par PostgreSQL après bind mount | Pas de répétition du problème local de SQL en 600 |
| `ast.parse`, assertions | Contrôle syntaxique et absence `.env`/`.git` privés dans l'export | Message de contrôle, code 0 |
| `tar -cf` / `scp -q` | Construire puis transférer l'archive, sans service lancé | Transfert silencieux, code 0 |
| `mktemp -d`, `umask 077` | Créer une destination distante unique et privée | Dossier 700 |
| `sha256sum` des deux côtés | Contrôler l'identité des octets transportés | Empreintes identiques |
| `chmod 600` / `stat` | Protéger l'archive et vérifier taille/mode | 2 037 760 octets, 600 |

## 6. Installer la copie et vérifier Dockge — terminal root

### Bloc envoyé et exécuté

```sh
(
set -eu
test "$(id -u)" -eq 0

PROJECT=int129-vps-33c350b23010
CHECKOUT="/opt/stacks/$PROJECT"
SOURCE=/home/tervo/int129-incoming.xvq02T1h/source.tar

printf '%s  %s\n' \
  03530fc69c867ad46edf8a169ec535ac5751da3fddd9461c802ba33497a3cb6a \
  "$SOURCE" | sha256sum -c -

if [ -e "$CHECKOUT" ]; then
  echo "Dossier déjà présent : arrêt sans modification."
  exit 1
fi

install -d -m 700 "$CHECKOUT"
tar --extract --file="$SOURCE" \
  --directory="$CHECKOUT" --no-same-owner

git -C "$CHECKOUT" init -q
git -C "$CHECKOUT" add .
GIT_EDITOR=true git -C "$CHECKOUT" \
  -c user.name="INT129 recipe" \
  -c user.email="recipe@localhost" \
  commit -q -m "INT129 VPS recipe A"

echo "Commit source de recette :"
git -C "$CHECKOUT" rev-parse HEAD

echo "Référence exacte de Dockge :"
docker inspect --format '{{.Config.Image}}' dockge-dockge-1

echo "Montages de Dockge :"
docker inspect --format \
  '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' \
  dockge-dockge-1

echo "Ports envisagés pour la recette :"
ss -ltn '( sport = :19829 or sport = :19830 )'
)
```

### Résultat envoyé

```text
/home/tervo/int129-incoming.xvq02T1h/source.tar: OK
Commit source de recette :
9111a2a1ecbb010cf9033c7300ca49193d0fd34a
Référence exacte de Dockge :
louislam/dockge:1.5.0@sha256:335c6368b880ecc203236ed89e6e5232e0d6578e8ef5920e4a502390451502bf
Montages de Dockge :
/opt/dockge/data -> /app/data
/opt/stacks -> /opt/stacks
/var/run/docker.sock -> /var/run/docker.sock

Ports envisagés pour la recette :
State                 Recv-Q                 Send-Q                                 Local Address:Port                                   Peer Address:Port
root@22565:~#
```

### But et usage

| Élément | But | Retour / effet contrôlé |
|---|---|---|
| `( … )`, `set -eu` | Isoler les variables et arrêter ce bloc sur erreur inattendue | La session SSH reste ouverte ; pas de poursuite aveugle |
| `test … id -u` | Refuser un contexte non-root | Silence et code 0 dans la session confirmée |
| `sha256sum -c -` | Vérifier l'archive avant extraction | `OK` observé ; sinon arrêt |
| Refus si `$CHECKOUT` existe | Ne pas écraser une stack existante | Condition non déclenchée |
| `install -d -m 700` | Créer le dossier privé de la nouvelle stack | Silence normal, code 0 |
| `tar --no-same-owner` | Extraire sous le propriétaire opérateur, sans reprendre les UID du poste local | Silence normal ; aucune app démarrée |
| `git -C`, `init`, `add`, `commit` | Créer l'historique de cette seule copie, afin de fournir un SHA propre au helper | SHA A observé ; aucun push ni modification de branche du dépôt principal |
| `GIT_EDITOR=true`, `-m`, `-q` | Fournir le message sans éditeur et réduire le bruit | Silence normal du commit |
| `docker inspect --format` | Lire uniquement l'image et les montages utiles | Image épinglée, mêmes chemins `/opt/stacks` hôte/conteneur |
| `ss -ltn` | Confirmer les deux ports disponibles | En-tête seul ; ne signifie pas erreur |

À ce stade : copie prête, mais aucun `.env` de recette créé ni conteneur Tervo
lancé. La première release est dans le journal suivant.
