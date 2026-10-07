# 02 — Préparer les mises à jour et la sécurité système

> **État :** mise à jour effectuée par l'utilisateur et contrôlée à distance ;
> redémarrage contrôlé, nouveau noyau actif. UFW actif et secours annulé ;
> jail SSH fail2ban chargée. Dépôt Debian Security réactivé ;
> correctifs supplémentaires installés, noyau Security actif après
> le second redémarrage ; automatisation configurée et dry-run contrôlé.
> Suite de [l'inventaire et de la sécurisation SSH](01-inventaire-et-acces-ssh.md).

## 1. Le piège du PATH

Les premiers `command -v` s'exécutaient dans le shell non-root, avant
`sudo`. Ils ne suffisaient donc pas à conclure à l'absence d'un paquet.
Le contrôle dans `sudo sh -c`, exécuté par l'utilisateur, a trouvé
`nft`, `iptables` et `ip6tables` dans `/usr/sbin`.

À l'inventaire initial, UFW, fail2ban-client et unattended-upgrade étaient
introuvables avec le PATH administrateur. Le `docker ps` reçu ne comporte aucune ligne
de conteneur actif ; il n'inventorie pas les conteneurs arrêtés.

Les règles fournies par l'utilisateur montrent :

- INPUT et OUTPUT ACCEPT en IPv4 et IPv6 ;
- FORWARD DROP en IPv4, FORWARD ACCEPT en IPv6 ;
- les chaînes Docker, avec `DOCKER-USER` vide ;
- du MASQUERADE IPv4 pour le réseau `172.17.0.0/16` ;
- les tables gérées par `iptables-nft`, avec l'avertissement de ne pas
  les modifier directement avec `nft`.

Cela ne renseigne pas le pare-feu externe Hostkey, dont l'état reste
inconnu. On ne doit pas vider ces tables ni déduire du seul statut UFW
la protection des ports publiés par Docker.

## 2. Passage aux lectures effectuées par l'agent

L'utilisateur a autorisé l'agent à effectuer les contrôles de cette
phase afin de ne plus recopier de longues sorties. La clé privée
locale est protégée par une passphrase. La première tentative en
`BatchMode=yes` a été refusée car l'agent SSH local ne contenait pas
de clé.

L'utilisateur a alors chargé la clé avec `ssh-add -t 1h` dans l'agent
SSH accessible au terminal de l'agent. Le message `Identity added`
et une durée de 3600 secondes ont été reçus. La passphrase n'a été
transmise ni dans le chat ni dans un fichier du dépôt.

L'agent a ensuite pu se connecter à `tervo@151.241.228.152` avec la
clé, `StrictHostKeyChecking=yes` et sans réutiliser une session
multiplexée. Cette politique vérifie la clé serveur déjà connue du
client ; elle ne remplace pas une vérification indépendante auprès
du fournisseur, qui n'est pas documentée dans les preuves initiales.

`sudo -n true` a indiqué que l'élévation non interactive était
indisponible : l'autorisation de l'utilisateur ne remplace pas
l'authentification exigée par le système. Aucun mot de passe n'a
été demandé à l'utilisateur dans le chat. Aucun `NOPASSWD: ALL`
n'a été ajouté pour contourner cette protection.

## 3. Simulations APT : ce qui est établi

L'utilisateur a signalé l'actualisation APT terminée sans erreur.
Les simulations suivantes ont été exécutées **par l'agent sur le
VPS**, sous le compte non-root `tervo` :

```bash
apt-get -s upgrade
apt-get -s --with-new-pkgs upgrade
```

| Simulation | Résultat observé |
|---|---|
| `upgrade` | 99 paquets mis à jour, aucun nouveau paquet, aucune suppression ; `linux-image-amd64` retenu |
| `--with-new-pkgs upgrade` | 100 paquets mis à jour, 1 nouveau paquet, aucune suppression, aucun paquet retenu |

Le nouveau paquet proposé est
`linux-image-6.12.107+deb13-amd64`. Les propositions comprennent
notamment OpenSSH, `sudo`, `systemd`, OpenSSL et la libc. Les résultats
dépendent des listes APT au moment de la simulation ; ils ne sont
pas une liste de versions à figer.

`-s` n'installe rien et ne nécessite pas les privilèges de la mise
à jour réelle. APT avertit que les verrous sont désactivés pendant
la simulation : il faudra revoir le résumé au moment de l'exécution.
`--with-new-pkgs` autorise les nouveaux paquets nécessaires, notamment
la nouvelle image du noyau, sans autoriser des suppressions comme
le pourrait une résolution avec `full-upgrade`.

## 4. Mise à jour effectuée et contrôle à distance

Pour conserver la protection de `sudo`, l'utilisateur a exécuté
l'étape privilégiée dans sa session VPS, sans devoir recopier la
sortie complète. Après sa confirmation, l'agent a contrôlé l'état à distance.

```bash
sudo apt-get --with-new-pkgs upgrade
```

Pour rejouer cette étape : avant confirmation, vérifier le résumé réel. Si APT demande quoi
faire d'un fichier SSH modifié, conserver la configuration locale
validée ; ne pas accepter automatiquement son remplacement.

Résultats des lectures effectuées par l'agent après la mise à jour :

| Vérification | Résultat |
|---|---|
| Nouvelle connexion par clé | Réussie en `tervo`, sans connexion multiplexée |
| `/etc/debian_version` | 13.7 |
| Paquets clés | OpenSSH `1:10.0p1-7+deb13u4`, sudo `1.9.16p2-3+deb13u2`, systemd `257.13-1~deb13u1` installés |
| Nouvelle simulation APT | 0 mise à jour, 0 nouveau paquet, 0 suppression, 0 paquet retenu dans les listes présentes |
| Services SSH et Docker | `active` et `enabled` au démarrage |
| Docker/Compose | Versions inchangées : 29.8.2 / v5.6.0 |
| Durcissement SSH | Fichier dédié conservé ; Include présent dans le fichier principal |
| Nouveau noyau | `6.12.107+deb13-amd64` et son initramfs présents dans `/boot` |
| Liens `/vmlinuz` et `/initrd.img` | Pointent vers la nouvelle version |
| Noyau actif (`uname -r`) | Toujours `6.12.48+deb13-amd64` |

Les paquets sont à jour dans les listes APT présentes ; cette conclusion
n'est pas une garantie de sécurité définitive ni un contrôle de tous les
logiciels installés hors APT. Aucun marqueur `/run/reboot-required` n'a été
trouvé, mais la différence entre noyau installé et noyau actif suffit à
établir qu'un redémarrage reste nécessaire. L'absence de ce marqueur sur
Debian ne prouve pas le contraire.

## 5. Redémarrage contrôlé à distance

Un nouveau noyau installé ne devient actif qu'après un redémarrage.
Les lectures précédentes confirment la présence du noyau/initramfs et
l'activation des services au démarrage ; elles ne garantissent pas à elles
seules le succès du boot du fournisseur.

Commande proposée à l'utilisateur sur le VPS :

```bash
sudo reboot
```

La fermeture des sessions SSH pendant le reboot est normale. Lors de la
reprise suivante, l'agent a constaté une nouvelle connexion par clé réussie,
`uname -r = 6.12.107+deb13-amd64`, un démarrage daté du
6 octobre 2026 à 10:19:18 selon le VPS, et les services SSH/Docker actifs.
Le passage au nouveau noyau est donc vérifié, sans demander une nouvelle
copie des sorties à l'utilisateur.

## 6. Installation des outils effectuée, services à vérifier

L'agent a simulé :

```bash
apt-get -s install ufw fail2ban unattended-upgrades python3-systemd
```

Résultat : 19 nouveaux paquets avec leurs dépendances/recommandations,
aucune suppression et aucune mise à jour additionnelle. `python3-systemd`
permettra de choisir le backend journal systemd de fail2ban plutôt que de
dépendre uniquement d'un fichier `/var/log/auth.log`.

L'étape privilégiée a été exécutée par l'utilisateur :

```bash
sudo apt-get install ufw fail2ban unattended-upgrades python3-systemd
```

Le contrôle à distance de l'agent a trouvé les quatre paquets installés :
UFW 0.36.2-9, fail2ban 1.1.0-8, unattended-upgrades 2.12 et
python3-systemd 235-1+b6. UFW est `inactive` avec `ENABLED=no` ;
fail2ban et unattended-upgrades sont `active`.

Le fichier Debian `/etc/fail2ban/jail.d/defaults-debian.conf` active déjà
la jail `sshd` avec `backend = systemd` et le journalmatch
`_SYSTEMD_UNIT=ssh.service + _COMM=sshd`, et choisit les actions nftables.
La configuration présente et le service actif ne remplacent pas une
lecture du statut réel de la jail avec `fail2ban-client`.

Installer UFW ne remplace pas la configuration/activation explicite des
règles : ne pas lancer `ufw enable` avant d'avoir autorisé SSH.
Les timers `apt-daily.timer` et `apt-daily-upgrade.timer` sont activés.
L'installation du paquet
unattended-upgrades ne sera pas présentée comme une preuve que les
origines autorisées et la périodicité sont correctes.

## 7. Préparation des règles UFW validée

L'état observé d'UFW est désactivé, avec prise en charge IPv6 (`IPV6=yes`).
L'utilisateur a préparé les règles avant toute activation :

```bash
sudo ufw allow 22/tcp comment 'SSH Tervo'
sudo ufw allow 80/tcp comment 'HTTP et validation HTTPS'
sudo ufw allow 443/tcp comment 'HTTPS Tervo'
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw show added
sudo fail2ban-client status sshd
```

Les sorties reçues confirment les trois règles 22/80/443, leurs
équivalents IPv6 et les politiques entrant refusé/sortant autorisé.
La jail `sshd` est chargée, avec le journalmatch prévu : 3 échecs
actuellement suivis, 6 au total, aucun bannissement. Ces compteurs
ne permettent pas d'attribuer les échecs à un utilisateur précis.

Les ports de PostgreSQL, du backend, du frontend et du panneau 1Panel ne
doivent pas être ouverts publiquement. L'activation se fera séparément,
avec retour arrière programmé et test d'une nouvelle connexion SSH.
Le pare-feu réseau Hostkey reste à inventorier ; les chaînes Docker ne
doivent pas être réinitialisées.

## 8. Activation avec retour arrière vérifiée

L'utilisateur a gardé sa session SSH ouverte et préparé une désactivation
automatique d'UFW après dix minutes. L'activation ne doit avoir lieu que si
la création du timer et son contrôle ont réussi :

```bash
sudo systemd-run \
    --unit=tervo-ufw-rollback \
    --on-active=10m \
    /usr/sbin/ufw disable &&
sudo systemctl is-active tervo-ufw-rollback.timer &&
sudo ufw --force enable &&
sudo ufw status verbose
```

Le timer exécute uniquement `ufw disable` : il ne rouvre pas l'accès root
SSH et ne modifie pas les clés. Si la connexion est perdue, le retour
arrière rétablit le pare-feu hôte désactivé après dix minutes.
L'agent a testé une nouvelle connexion avant de demander l'annulation
du timer. Si celui-ci s'était déjà déclenché, une connexion réussie n'aurait pas
validé l'accessibilité avec UFW actif : il aurait fallu refaire la recette.

Les sorties de l'utilisateur confirment UFW actif et activé au démarrage,
les politiques deny incoming / allow outgoing / deny routed, et les trois
ports autorisés en IPv4 et IPv6. L'agent a ensuite confirmé une connexion
neuve par clé, `ENABLED=yes`, un timer en attente et un service de secours
jamais démarré.

Après confirmation du test, l'utilisateur a exécuté :

```bash
sudo systemctl stop tervo-ufw-rollback.timer &&
sudo ufw status verbose
```

L'agent a revérifié une nouvelle connexion, `ENABLED=yes`, et la disparition
des unités transitoires (`LoadState=not-found`, `ActiveState=inactive`,
aucune date de lancement du service de secours). Le secours n'a donc pas
désactivé le pare-feu. Aucun flush des chaînes Docker n'a été effectué.

## 9. Dépôt Security réactivé et contrôles APT restaurés

Les timers APT sont `enabled` et `active`, mais `apt-config shell` ne
retourne aucun paramètre quotidien `APT::Periodic::Update-Package-Lists`
ou `APT::Periodic::Unattended-Upgrade`. Le service installé/actif n'est
donc pas une preuve suffisante de mises à jour automatiques configurées.

Avant correction et avant de fixer les origines autorisées, l'agent avait
consulté `apt-cache policy`, les sources APT et l'horloge :

- Debian `trixie`, `trixie-updates` et Docker sont actifs ;
- le dépôt `trixie-security` est **commenté** dans `/etc/apt/sources.list` ;
- `/etc/apt/apt.conf.d/99ignore-release-date` contient
  `Acquire::Check-Valid-Until "false";` et `Acquire::Check-Date "false";` ;
- l'horloge est synchronisée (`NTPSynchronized=yes`, fuseau Europe/Paris) ;
- le trousseau Debian existe dans `/usr/share/keyrings`.

L'origine de ces choix du système initial n'est pas établie. Le précédent
résultat « 0 paquet restant » portait seulement sur les dépôts actifs ;
il ne prouvait pas la prise en compte des correctifs du dépôt Security.
Les désactivations de contrôles temporels affaiblissent la protection
contre des métadonnées anciennes ; elles ne doivent pas être conservées
sans une raison explicitement vérifiée.

L'utilisateur a exécuté la correction proposée : sauvegarde sous un
répertoire `/root/tervo-apt-<date>`, sortie de l'override de validation
du répertoire APT actif, création de
`/etc/apt/sources.list.d/tervo-security.sources` et actualisation APT.
Les sauvegardes root n'ont pas été inspectées par l'agent non-root.

Le fichier ajouté, relu par l'agent :

```text
Types: deb
URIs: https://security.debian.org/debian-security
Suites: trixie-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
```

L'agent a confirmé l'absence du fichier `99ignore-release-date` actif,
l'absence des deux valeurs false dans `apt-config shell`, et la présence
de l'origine Debian Security (`codename=trixie-security`,
`label=Debian-Security`) dans `apt-cache policy`. Les dépôts Debian/Docker
existants sont toujours présents et `ENABLED=yes` pour UFW.

La nouvelle simulation `apt-get -s --with-new-pkgs upgrade` propose
12 mises à jour et 1 nouveau paquet, aucune suppression : toutes les
propositions proviennent de Debian Security, dont OpenSSL, Exim,
plusieurs bibliothèques et `linux-image-6.12.111+deb13-amd64`.
Ces correctifs n'étaient pas visibles avant la réactivation du dépôt.

## 10. Correctifs supplémentaires appliqués et contrôlés

Commande exécutée par l'utilisateur, puis contrôlée à distance :

```bash
sudo apt-get --with-new-pkgs upgrade
```

Pour rejouer : vérifier le résumé réel et conserver les configurations
locales validées. Le contrôle de l'agent après confirmation trouve :

- une nouvelle connexion SSH par clé réussie ;
- `linux-image-amd64` et `linux-image-6.12.111+deb13-amd64` en version
  `6.12.111-1`, installés ;
- OpenSSL et libssl3t64 en version `3.5.7-1~deb13u3`, installés ;
- le noyau/initramfs présents dans `/boot`, et les liens `/vmlinuz` /
  `/initrd.img` pointant vers 6.12.111 ;
- SSH/Docker actifs et activés au démarrage, et `ENABLED=yes` pour UFW ;
- 0 mise à jour restante, 0 installation, 0 suppression, 0 paquet retenu
  dans la nouvelle simulation.

`uname -r` est encore `6.12.107+deb13-amd64` : l'installation des correctifs
Security est vérifiée, mais leur nouveau noyau ne deviendra actif qu'après
un **second redémarrage**. Le premier reboot avait activé le noyau des
dépôts initiaux ; le dépôt Security manquant n'a été découvert qu'ensuite.

APT propose par ailleurs de nettoyer l'ancien noyau 6.12.48 comme paquet
automatique inutilisé. Aucun `autoremove` n'a été exécuté : on conserve
les noyaux de secours pendant la vérification du nouveau démarrage.

Prochaine commande proposée à l'utilisateur :

```bash
sudo reboot
```

Le second redémarrage a ensuite été contrôlé par l'agent :
connexion neuve par clé réussie, noyau `6.12.111+deb13-amd64` actif,
démarrage daté du 6 octobre 2026 à 10:48:42 selon le VPS. Les services
SSH, Docker, UFW, fail2ban et unattended-upgrades sont actifs.
UFW conserve `ENABLED=yes` et les deux timers APT sont actifs.

## 11. Mises à jour automatiques : configuration et dry-run validés

Les paramètres quotidiens étaient absents au premier contrôle de l'agent.
L'utilisateur a exécuté la configuration ci-dessous et signalé un code
retour de test égal à 0. L'agent a ensuite relu les paramètres effectifs
et le journal, sans demander sa copie dans le chat :

```bash
sudo tee /etc/apt/apt.conf.d/52-tervo-security-upgrades >/dev/null <<'EOF'
APT::Periodic::Enable "1";
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";

#clear Unattended-Upgrade::Origins-Pattern;
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=trixie-security,label=Debian-Security";
};

Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "false";
Unattended-Upgrade::Remove-New-Unused-Dependencies "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "false";
EOF

(umask 077; sudo unattended-upgrade --dry-run --debug > "$HOME/tervo-unattended-dry-run.log" 2>&1)
printf 'Code retour du test : %s\n' "$?"
```

`#clear` remplace la liste d'origines du fichier Debian 50 plutôt que
d'ajouter une ligne à ses autorisations existantes. Seul `trixie-security`
est autorisé ; la version Debian et le dépôt Docker ne sont pas mis à jour
automatiquement par cette règle. La cadence "1" est quotidienne selon
les contrôles APT et timers, pas une promesse d'exécution à heure fixe.
Le redémarrage de la machine et les suppressions automatiques sont
désactivés. Certains paquets peuvent toutefois recharger/redémarrer leur
propre service lors d'une mise à jour : aucun reboot automatique ne signifie
pas absence de toute interruption.

Le dry-run n'installe pas de paquet. Le journal est créé dans le dossier
personnel de `tervo` avec un umask restrictif pour permettre sa lecture
à distance par le même compte, sans demander à l'utilisateur de le
recopier. Les lectures de l'agent confirment :

| Vérification | Résultat |
|---|---|
| APT périodique activé | `APT::Periodic::Enable = 1` |
| Rafraîchissement et mises à jour | Les deux périodicités valent `1` |
| Reboot automatique | `false` |
| Nettoyage automatique | Les trois paramètres configurés valent `false` |
| Origines réellement autorisées | Seulement `origin=Debian,codename=trixie-security,label=Debian-Security` |
| Exclusions du dry-run | Dépôts Docker, Debian principal et trixie-updates exclus pour cette exécution automatique |
| Résultat du dry-run | `upgrade result: True`, aucun paquet éligible restant, aucune suppression automatique en attente |
| Journal personnel | Mode `600`, propriétaire `tervo` |
| Services et timers | SSH/Docker/UFW/fail2ban/unattended-upgrades et les deux timers APT actifs |

Le message du dry-run sur le contrôle de batterie ignoré faute de
powermgmt-base ne constitue pas un échec pour ce VPS ; aucun paquet
supplémentaire n'a été installé pour le supprimer.
Les restrictions d'origine s'appliquent à unattended-upgrades, pas à
un blocage permanent des mises à jour manuelles APT.

Cela valide la configuration et la simulation, **pas** une exécution
future réussie avec des correctifs nouvellement publiés. Les journaux
devront être suivis, les reboots nécessaires planifiés et les mises à
jour hors Debian Security, notamment Docker, entretenues manuellement.

**Non effectué à ce stade :** recette du pare-feu réseau Hostkey,
nettoyage des anciens noyaux, installation 1Panel ou déploiement applicatif.
