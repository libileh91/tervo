# 01 — Inventaire du VPS et sécurisation de l'accès SSH

> **Périmètre :** préparation du serveur pour INT-111, pas déploiement de Tervo.
> **Repère temporel :** sorties du VPS et sauvegarde datées du 5 octobre 2026.
> **Source des vérifications :** sorties de terminal fournies par l'utilisateur
> pendant le parcours guidé. L'agent n'a pas exécuté ces commandes sur le VPS.
> **État :** nouvelle connexion `tervo` par clé, `sudo`, refus sans clé et
> correction du client SSH confirmés ; outillage de sécurité absent,
> règles du pare-feu encore à vérifier.

## 1. Choix de l'hébergement et périmètre réel

Ubuntu Server LTS était prévu dans le planning initial pour faciliter les
procédures, mais Tervo n'a pas de dépendance applicative à Ubuntu. Docker
fait tourner les services ; le système hôte doit fournir les outils,
la maintenance de sécurité et la compatibilité du panneau retenu.
Debian a été choisi pour ce serveur. La version livrée est Debian 13 ;
les commandes doivent partir de cet inventaire, pas d'une hypothèse Ubuntu.

Les options discutées étaient un VPS Hostinger, un laptop réutilisé et
le VPS Hostkey. Le laptop aurait convenu à un laboratoire ou une démo,
mais aurait ajouté la dépendance au courant, à la box et au débit montant
du domicile. Le choix pour ce parcours est finalement un **VPS Hostkey**.

| Information | Valeur communiquée |
|---|---|
| Offre | FR / `vm.mini` |
| Prix annoncé | 13,38 € pour 3 mois, soit 4,46 €/mois sur cette période |
| Ressources annoncées | 4 vCPU, 6 Go de RAM, 120 Go SSD |
| Réseau annoncé | 3 To de trafic, port 1 Gbit/s, une IPv4 |
| Identifiant dans le panneau fournisseur | `165618` |
| IPv4 du VPS | `151.241.228.152` |
| Nom d'hôte observé dans le terminal | `22565` |
| Système effectivement observé | Debian GNU/Linux 13 (trixie), version complète affichée 13.4 |

Le prix de renouvellement, la TVA, les sauvegardes/snapshots inclus, les
limites CPU et le débit garanti **n'ont pas été vérifiés** dans ce parcours.
Le port annoncé à 1 Gbit/s n'est pas une mesure du débit. L'ID du panneau
et le nom d'hôte sont deux identifiants distincts.
Cette note ne contient ni mot de passe, ni token, ni clé privée.

## 2. Repérer le bon terminal avant chaque commande

Deux machines participent au parcours :

| Terminal | Rôle | Exemple observé |
|---|---|---|
| Ordinateur local | Contient la clé privée ; initie les connexions SSH | `$HOME` = `/home/lob` |
| VPS | Héberge le compte distant et le service SSH | Prompt `tervo@22565:~$`, `$HOME` = `/home/tervo` |

`$HOME` désigne le dossier personnel **de la machine et de l'utilisateur
qui exécutent la commande**. Le prompt est donc un indice important.
On utilise un terminal local supplémentaire pour tester une nouvelle
connexion, sans fermer la session distante qui peut encore corriger
une mauvaise configuration.

## 3. Inventaire initial : lectures, sans installation

Dans la session initiale du VPS, alors connectée en `root` :

```bash
cat /etc/os-release
uname -m
id
nproc
free -h
df -h /
ss -lntp
command -v docker || true
```

| Commande | Ce qu'elle vérifie | Résultat reçu |
|---|---|---|
| `cat /etc/os-release` | Distribution/version | Debian 13 (trixie), 13.4 affiché |
| `uname -m` | Architecture | `x86_64` |
| `id` | Compte et groupes | `uid=0(root)` |
| `nproc` | CPU disponibles au processus | 4 |
| `free -h` | Mémoire et swap | 5,8 GiB RAM, 5,3 GiB disponibles ; swap 1,7 GiB, inutilisée |
| `df -h /` | Système de fichiers racine | 115 G, 6,0 G utilisés, 104 G disponibles |
| `ss -lntp` | Sockets TCP en écoute | SSH sur IPv4/IPv6 port 22 ; Exim sur les seules boucles locales port 25 |
| `command -v docker` | Présence de l'exécutable | `/usr/bin/docker` |

Les valeurs mémoire/disque correspondent à l'état au moment de la lecture,
pas à une réservation permanente pour l'application. Une écoute sur
`0.0.0.0` ou `[::]` ne prouve pas à elle seule l'accessibilité depuis
Internet : les pare-feu Debian et fournisseur restent à vérifier.
Exim était uniquement lié à `127.0.0.1` et `::1`, pas aux interfaces publiques.

Un deuxième inventaire a ensuite été exécuté :

```bash
id tervo
command -v sudo || true
docker --version
docker compose version
systemctl is-active docker
```

Résultats reçus : compte `tervo` initialement absent, `sudo` disponible
dans `/usr/bin/sudo`, Docker 29.8.2, Compose v5.6.0, service Docker `active`.
Ces versions viennent des sorties du fournisseur : elles ne sont pas un
choix de version verrouillé par cette note. **Docker n'a pas été réinstallé**.
Le service actif ne prouve pas encore l'existence de projets ou de réseaux
Docker ; leur inventaire est demandé à la fin de la note.

## 4. Clé, utilisateur et mots de passe : trois notions distinctes

Le nom `tervo_ed25519` désigne un **fichier de clé locale**, pas un compte
Linux. L'étiquette `lb91`, avec type ED25519 et indicateur « Default » dans
le panneau Hostkey, ne prouve pas à elle seule que la clé est installée
dans le compte souhaité.

| Élément | Usage |
|---|---|
| `~/.ssh/tervo_ed25519` sur l'ordinateur | Clé privée ; ne jamais copier sur le VPS ou dans Git |
| `~/.ssh/tervo_ed25519.pub` sur l'ordinateur | Clé publique ; peut être installée sur le VPS |
| Compte Linux `tervo` | Utilisateur distant qui reçoit la clé et utilise `sudo` |
| Passphrase de la clé | Déchiffre localement la clé privée ; peut être demandée à chaque connexion |
| Mot de passe Linux de `tervo` | Sert à `sudo` et, avant le durcissement, à l'installation initiale de la clé |
| Mot de passe root fourni | Accès initial de bootstrap ; pas une passphrase SSH |

La commande de génération proposée sur l'ordinateur était :

```bash
ssh-keygen -t ed25519 -a 64 -f "$HOME/.ssh/tervo_ed25519" -C "tervo-vps"
```

`-f` choisit le nom/emplacement ; `-C` ajoute un commentaire ; `-a 64`
augmente le travail de dérivation pour la protection par passphrase.
La génération elle-même n'a pas été accompagnée d'une sortie complète ;
en revanche, les connexions reçues prouvent ensuite l'utilisation de
ce fichier et affichent une demande de passphrase.
Avant toute génération sur une autre machine, vérifier que les fichiers
n'existent pas déjà : ne pas écraser une clé existante.

L'empreinte **du serveur** est une autre clé que la clé utilisateur.
La vérification indépendante avait été proposée via la console fournisseur :

```bash
# Dans une console fournisseur déjà authentifiée, pas par un accès inconnu.
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

La console web a été signalée comme difficilement utilisable.
**Aucune empreinte serveur ni preuve de comparaison indépendante n'a
été fournie dans les sorties retenues.** Les connexions réussies ci-dessous
ne doivent donc pas être présentées comme cette preuve. En cas de
changement d'empreinte ultérieur, vérifier auprès du fournisseur ; ne pas
contourner l'avertissement en désactivant le contrôle de l'identité SSH.

## 5. Bootstrap du compte non-root

Procédure fournie dans la session root initiale du VPS :

```bash
adduser tervo
usermod -aG sudo tervo
id tervo
```

`adduser` crée le compte, son dossier et demande un mot de passe Linux.
`usermod -aG sudo` **ajoute** le groupe sudo sans retirer les autres groupes.
La création interactive n'a pas été retranscrite intégralement ; l'état
final est confirmé par les lectures et connexions suivantes.

Depuis un **deuxième terminal local** :

```bash
ssh-copy-id -i "$HOME/.ssh/tervo_ed25519.pub" tervo@151.241.228.152
```

Cette étape installe la clé publique dans
`/home/tervo/.ssh/authorized_keys`, en utilisant le mot de passe Linux
du nouveau compte pendant le bootstrap. La clé privée reste locale.
Le résultat de `ssh-copy-id` n'a pas été copié dans le fil, mais la
connexion forcée par clé a ensuite réussi.

Test local proposé, puis confirmé :

```bash
ssh -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -i "$HOME/.ssh/tervo_ed25519" \
    tervo@151.241.228.152
```

Une fois connecté sur le VPS :

```bash
id
sudo -v
sudo id
```

Sorties reçues :

```text
uid=1000(tervo) gid=1000(tervo) groups=1000(tervo),27(sudo),100(users)
uid=0(root) gid=0(root) groups=0(root)
```

La première ligne décrit le compte connecté ; la seconde est le résultat
de la seule commande `sudo id`, pas une transformation permanente du
terminal en session root. `sudo -v` valide les droits et peut demander
le mot de passe Linux de `tervo`.

## 6. Inspecter SSH avant de fermer des accès

Le durcissement a été préparé **après** validation de l'accès non-root.
Les sessions existantes ont été conservées comme moyen de correction.

Sur le VPS :

```bash
sudo /usr/sbin/sshd -t
sudo ls -l /etc/ssh/sshd_config.d/
sudo grep -nE '^[[:space:]]*(Include|Match|PermitRootLogin|PubkeyAuthentication|PasswordAuthentication|KbdInteractiveAuthentication|AuthenticationMethods)[[:space:]]' \
    /etc/ssh/sshd_config
sudo grep -RnsE '^[[:space:]]*(Include|Match|PermitRootLogin|PubkeyAuthentication|PasswordAuthentication|KbdInteractiveAuthentication|AuthenticationMethods)[[:space:]]' \
    /etc/ssh/sshd_config.d/
```

`sshd -t` vérifie la syntaxe, sans changer le serveur. Une sortie vide
signifie que cette vérification a réussi.
Les fichiers observés étaient :

- `/etc/ssh/sshd_config` : Include des `*.conf` à la ligne 12,
  `PermitRootLogin yes` à la ligne 33, `PasswordAuthentication yes`
  à la ligne 34, `KbdInteractiveAuthentication no` à la ligne 65 ;
- `/etc/ssh/sshd_config.d/50-cloud-init.conf` :
  `PasswordAuthentication yes`.

Pour regarder les règles effectives dans le contexte de chaque compte :

```bash
CLIENT_IP="${SSH_CONNECTION%% *}"

for USERNAME in tervo root; do
    printf '\n--- SSH : %s ---\n' "$USERNAME"
    sudo /usr/sbin/sshd -T \
        -C "user=$USERNAME,addr=$CLIENT_IP,host=$CLIENT_IP" |
        grep -E '^(permitrootlogin|pubkeyauthentication|pass[w]ordauthentication|kbdinteractiveauthentication|authenticationmethods|usepam) '
done
```

`sshd -T` lit les fichiers et affiche leur configuration effective ;
`-C` applique le contexte fourni aux éventuelles règles `Match`.
`pass[w]ordauthentication` est une expression régulière qui reconnaît
le nom de la directive sans utiliser le placeholder de redaction qui
avait rendu un premier filtre incomplet. Cette lecture **ne recharge
pas** le démon déjà lancé.

Avant modification, pour `tervo` et `root` : root autorisé, clés autorisées,
authentification par mot de passe autorisée, authentification interactive
désactivée, `AuthenticationMethods any`, `UsePAM yes`.

## 7. Durcir le serveur avec un fichier dédié

L'Include est placé avant les directives actives du fichier principal.
Le fichier `00-tervo-hardening.conf` est également chargé avant
`50-cloud-init.conf`. Pour ces options, la première valeur applicable
compte : un simple fichier `99-…` n'aurait pas nécessairement remplacé
les valeurs déjà rencontrées.

Commande exécutée sur le VPS :

```bash
sudo tee /etc/ssh/sshd_config.d/00-tervo-hardening.conf >/dev/null <<'EOF'
# Tervo : accès SSH par clé uniquement.
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
EOF

sudo chmod 644 /etc/ssh/sshd_config.d/00-tervo-hardening.conf
sudo /usr/sbin/sshd -t && echo "Configuration SSH valide"
```

Le nom de fichier était nouveau dans l'inventaire reçu. Sur un autre
serveur, vérifier son existence avant d'utiliser `tee`, qui écrase
le contenu du fichier cible.

| Directive | Effet |
|---|---|
| `PermitRootLogin no` | Interdit les nouvelles connexions SSH directes root, même par clé |
| `PubkeyAuthentication yes` | Conserve la méthode par clé |
| `PasswordAuthentication no` | Retire la méthode de connexion SSH par mot de passe |
| `KbdInteractiveAuthentication no` | Retire une autre méthode interactive pouvant demander un mot de passe |
| `AuthenticationMethods publickey` | Exige la méthode par clé |

La valeur `UsePAM yes` n'a pas été modifiée. Le compte root existe
toujours et `sudo` peut toujours demander le mot de passe de `tervo` :
on interdit une **méthode d'accès SSH**, pas les mots de passe Linux
dans tous les usages.

La syntaxe a été confirmée, puis la boucle `sshd -T -C` a montré,
pour les deux comptes, les valeurs attendues : root `no`, clés `yes`,
mot de passe `no`, interactif `no`, méthodes `publickey`.
Le fichier cloud-init n'a pas été modifié.

## 8. Activer et tester depuis une nouvelle connexion

Après contrôle des fichiers, commandes exécutées sur le VPS :

```bash
sudo /usr/sbin/sshd -t && sudo systemctl reload ssh
systemctl is-active ssh
```

Résultat reçu : `active`. Le rechargement applique les règles aux
nouvelles connexions ; les sessions déjà établies restent ouvertes.
Il ne fallait ni redémarrer le VPS ni fermer le seul accès fonctionnel.

Test depuis un **nouveau terminal de l'ordinateur**, effectivement reçu :

```bash
ssh -o ControlPath=none \
    -o IdentitiesOnly=yes \
    -o PreferredAuthentications=publickey \
    -i "$HOME/.ssh/tervo_ed25519" \
    tervo@151.241.228.152
```

- `-i` sélectionne la clé nommée ;
- `IdentitiesOnly=yes` limite les identités proposées ;
- `PreferredAuthentications=publickey` évite un repli vers le mot
  de passe du serveur ;
- `ControlPath=none` empêche de réutiliser une connexion multiplexée
  existante : c'est bien une nouvelle connexion qui est testée.

La demande de passphrase locale, la connexion et les commandes `id` /
`sudo id` ont été confirmées **après le rechargement**.

Test négatif, toujours sur l'ordinateur :

```bash
ssh -o ControlPath=none \
    -o PubkeyAuthentication=no \
    tervo@151.241.228.152
```

Résultat reçu :

```text
tervo@151.241.228.152: Permission denied (publickey).
```

La connexion sans clé a donc été refusée, sans demande de mot de passe
du serveur. Une connexion root négative n'a pas été retranscrite ;
son interdiction est établie par la configuration effective et son
rechargement, pas par un test de login root prétendument exécuté.

## 9. Incident : terminal distant et configuration client confondus

Une première tentative de test avait été lancée dans le prompt du VPS :

```text
Warning: Identity file /home/tervo/.ssh/tervo_ed25519 not accessible:
No such file or directory.
/etc/ssh/ssh_config: line 26: Bad configuration option: permitrootlogin
```

Il s'agissait de **deux problèmes indépendants** :

1. Le chemin `$HOME/.ssh/tervo_ed25519` était cherché sur le VPS, alors
   que la clé privée était sur l'ordinateur. La correction consiste à
   lancer la connexion depuis le terminal local, pas à transférer la clé.
2. Une directive serveur `PermitRootLogin yes` se trouvait dans le
   fichier **client** `/etc/ssh/ssh_config`. L'origine de cette ligne
   n'est pas établie par les sorties ; elle ne faisait pas partie de
   notre fichier dédié sous `sshd_config.d/`.

| Fichier | Programme | Rôle |
|---|---|---|
| `/etc/ssh/ssh_config` | `ssh` | Réglages des connexions sortantes depuis cette machine |
| `/etc/ssh/sshd_config` et ses Includes | `sshd` | Réglages des connexions entrantes vers cette machine |

Correction exécutée sur le VPS, après lecture des lignes concernées :

```bash
BACKUP="/etc/ssh/ssh_config.before-tervo-$(date +%Y%m%d-%H%M%S)"
sudo cp -a /etc/ssh/ssh_config "$BACKUP"
printf 'Sauvegarde : %s\n' "$BACKUP"

sudo sed -i '/^[[:space:]]*PermitRootLogin[[:space:]]/d' /etc/ssh/ssh_config
ssh -G localhost >/dev/null && echo "Configuration du client SSH valide"
```

La sauvegarde a été confirmée à l'emplacement :
`/etc/ssh/ssh_config.before-tervo-20261005-183349`.
Le message `Configuration du client SSH valide` a été reçu.
`ssh -G` lit la configuration du client sans se connecter à localhost.
Cette correction ne nécessite **aucun rechargement de `sshd`**.

La ligne `PasswordAuthentication yes` du fichier client a été laissée
en place : elle concerne les connexions sortantes du VPS et ne réactive
pas cette méthode sur son serveur SSH.
Certaines commandes proposées dans le fil contenaient un placeholder
de redaction et étaient inutilisables telles quelles ; les commandes
de cette note sont les versions corrigées. Ne pas recopier ces
placeholders comme noms de méthodes ou directives.

## 10. État confirmé, limites et prochaine étape

| Point | État |
|---|---|
| Inventaire OS/ressources | Sorties reçues |
| Docker/Compose et service actif | Sorties reçues ; pas de réinstallation |
| Compte `tervo` avec groupe sudo | Confirmé |
| Nouvelle connexion par clé après reload | Confirmée |
| Refus d'une connexion sans clé | Confirmé |
| Refus root dans la configuration chargée | Confirmé ; test négatif root non retranscrit |
| Vérification indépendante de l'empreinte serveur | Non documentée dans les preuves reçues |
| Configuration du client SSH et sauvegarde | Confirmées |
| UFW, fail2ban, mises à jour automatiques | Les trois commandes restent introuvables dans le PATH administrateur |
| Pare-feu réseau Hostkey | État non communiqué |
| Outils réseau | `nft`, `iptables`, `ip6tables` présents dans `/usr/sbin` ; règles Docker observées |
| Conteneurs/réseaux Docker | `docker ps` vide ; réseaux non inventoriés, conteneurs arrêtés non recherchés |
| 1Panel, HTTPS, déploiement applicatif et sauvegardes | Non réalisés dans ce parcours |

Commandes exécutées sur le VPS, dont les résultats ont ensuite été reçus :

```bash
for TOOL in ufw fail2ban-client unattended-upgrade; do
    if command -v "$TOOL" >/dev/null 2>&1; then
        printf '%s : présent\n' "$TOOL"
    else
        printf '%s : absent\n' "$TOOL"
    fi
done

if command -v ufw >/dev/null 2>&1; then
    sudo ufw status verbose
fi

if command -v nft >/dev/null 2>&1; then
    sudo nft list ruleset
else
    echo "Commande nft absente"
fi

sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
```

Le premier contrôle sous `tervo` indiquait que les commandes étaient
introuvables, avec aucune ligne de conteneur après l'en-tête de `docker ps`.
**Correction du diagnostic :** ce contrôle utilisait le PATH non-root.
Une seconde lecture exécutée par l'utilisateur dans `sudo sh -c`
(PATH incluant `/usr/sbin`) a trouvé `nft`, `iptables` et `ip6tables`.
UFW, fail2ban et unattended-upgrade restent introuvables avec sudo.

Les règles retournées montrent INPUT/OUTPUT ACCEPT en IPv4 et IPv6,
FORWARD DROP en IPv4, FORWARD ACCEPT en IPv6 et les chaînes Docker
(`DOCKER-USER` vide). Docker utilise `iptables-nft` ; les tables affichent
l'avertissement de ne pas les modifier directement avec `nft`.
La NAT IPv4 comporte un MASQUERADE pour `172.17.0.0/16`. Cela décrit les
règles locales reçues, pas les éventuelles restrictions du fournisseur.
Ne pas lancer de flush des règles : ces chaînes appartiennent à Docker.

L'utilisateur a signalé l'actualisation APT terminée sans erreur ;
la sortie de la simulation des mises à jour n'a pas encore été fournie.
Aucune installation ou activation de sécurité n'est validée à ce stade.

La prochaine étape dépend des règles réseau, des mises à jour proposées
par APT et de l'état du pare-feu
fournisseur. **Ne pas activer UFW avant d'avoir autorisé explicitement
SSH**, ne pas réinitialiser les règles réseau, et ne pas considérer
UFW comme une protection automatique de tous les ports publiés par Docker.
Nous vérifierons les binds et réseaux avant la publication applicative.

Le bootstrap SSH ne clôture pas INT-111 : il reste notamment les
mises à jour, le pare-feu, 1Panel, les secrets, les builds reproductibles,
les données, DNS/HTTPS et les sauvegardes avec restauration.
Le seed de démonstration reste interdit sur une base existante dans ce
parcours (TD-B019) ; aucune application, base, migration ou procédure
de seed n'a été exécutée sur le VPS à ce stade.
