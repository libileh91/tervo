# 03 — Préparer une installation 1Panel privée

> **Tâche :** INT-124, extraite du chantier INT-111 sans changement du
> périmètre technique ; préparation puis installation 1Panel/OpenResty.
> **État :** installation effectuée par l'utilisateur, puis panneau
> arrêté après échec du contrôle d'isolation : 7410 répondait depuis Internet.
> Core et agent désormais actifs, bind 127.0.0.1:7410 contrôlé à distance,
> HTTP local 200 et connexion TCP publique IPv4 sans succès.
> Fin du 502 et affichage des informations VPS confirmés par l'utilisateur ;
> DENY UFW conservés, aucun nouvel ALLOW 7410/443 UDP dans la sortie fournie.
> Bind privé maintenu après restart des deux services ; les deux unités
> sont désormais enabled au boot, confirmé par la sortie utilisateur.
> Aucun reboot réel ni contrôle après mise à jour effectué à ce stade.
> OpenResty installé et HTTP public 200 ; mode réel et recette proxy
> sur cible jetable encore à contrôler.
> Suite de [la préparation système](02-preparation-securite-systeme.md).

> [!WARNING] Isolation finale non validée
> Le patch de l'installateur ne désactive pas la synchronisation firewall
> des binaires 1Panel. Le bloc d'installation ci-dessous est une trace
> historique, **pas une procédure validée à rejouer** sans corriger ce point.

## 1. Périmètre et décision

Cette note couvre le panneau de gestion, puis la préparation et
l'installation OpenResty en sections 12/13 ; elle ne déploie ni Tervo
ni PostgreSQL. Les applications Tervo resteront
pilotées par Git/Compose, pas créées comme une seconde stack dans 1Panel.
L'usage visé est le socle gratuit ; aucune licence Pro n'est activée.

Le panneau devra utiliser le Docker existant et garder son administration
sur le port 7410 **privé**, accessible par tunnel SSH. L'état final ne
sera validé qu'après mesures des binds, règles et connexions réelles.

Lancer directement un installateur générique puis refermer son port
après coup créerait une fenêtre d'exposition évitable. On choisit une
adaptation minimale, attachée à une archive/version précise, qui saute
l'ouverture automatique du port.

## 2. Sources et intégrité vérifiées localement

Sources publiques consultées par l'agent :

- [Bootstrap officiel v2](https://resource.1panel.pro/v2/quick_start.sh)
- [Version stable annoncée](https://resource.1panel.pro/v2/stable/latest)
- [Checksums de v2.3.2](https://resource.1panel.pro/v2/stable/v2.3.2/release/checksums.txt)
- [Archive amd64](https://resource.1panel.pro/v2/stable/v2.3.2/release/1panel-v2.3.2-linux-amd64.tar.gz)

La version stable annoncée lors de cette lecture est **v2.3.2**.
L'architecture amd64 correspond à l'inventaire x86_64 du VPS.
L'archive a été téléchargée dans le scratch local avec vérification TLS,
sans `curl -k` et sans exécution de code téléchargé.

SHA-256 publié et vérifié :

```text
f1265a4fadeaab3d7066dd71e3c6904ac54bb687baab1b205a23c369abb61cac
```

`sha256sum --check` a retourné `OK`. Cela établit la concordance avec
l'empreinte publiée via HTTPS, pas une signature indépendante ni un
audit des exécutables binaires.

Le bootstrap officiel observé appelle `curl -LOk` pour l'archive et ne
revérifie pas le hash après un premier téléchargement neuf. Notre
préparation ne l'exécute donc pas : version explicite, TLS vérifié,
checksum avant extraction, puis lecture du script sont préférables.
Cette observation concerne le script consulté, pas toutes ses versions.

## 3. Lecture de l'installateur : ce qu'il fait réellement

Le package contient notamment `install.sh`, `1pctl`, les exécutables
core/agent, leurs unités systemd et les fichiers de langue.
Les textes ont été extraits dans le scratch pour lecture, sans lancer
les binaires ni l'installateur.

### Ouverture automatique du pare-feu

Dans `install.sh` v2.3.2 :

```bash
function Set_Firewall(){
    # Entre autres branches :
    ufw allow "$PANEL_PORT"/tcp
    ufw reload
}
```

Le flux `main` appelle cette fonction juste après `Set_Port`.
Il peut également ouvrir le port via firewalld si cet outil est présent.
Aucun argument `--skip-firewall` n'a été trouvé dans le parser de cette
version. Choisir 7410 sans autre mesure ne suffirait donc pas à respecter
la doctrine Tervo.

### Docker et configuration

Le script détecte Docker et possède des options pour éviter une nouvelle
installation, les miroirs de registre et le remplacement de daemon.json :

```text
--install-docker n
--configure-accelerator n
--replace-daemon-json n
```

La branche Docker existant reste à contrôler sur le VPS : les options
et leur lecture dans le code ne remplacent pas un contrôle après
exécution des versions, services et configuration.

Le chemin de base proposé sera `/opt` : les données du panneau seront
dans `/opt/1panel`, distinctes du futur `/opt/tervo`.
Avant tout lancement, vérifier l'absence d'une installation ou de données
1Panel préexistantes ; l'installateur possède un chemin d'initialisation
qui nettoie le répertoire quand il ne reconnaît pas une base existante.
Ne jamais le relancer aveuglément sur un état partiel.

### Identifiants et distribution

Le bootstrap international écrit `.selected_edition` avec la valeur `intl`.
Cette sélection de distribution doit être reproduite en préparant
manuellement le package ; elle n'est pas une activation de licence Pro.
La langue `en` est disponible dans cette version.

On gardera la saisie des identifiants dans le terminal privé de
l'administrateur, pas dans des arguments CLI, un fichier du dépôt ou
un message du chat. Le mode non interactif peut générer un mot de passe
initial court ; on ne l'utilisera pas sans politique explicite de secret.
L'installateur affiche les informations d'accès en fin de parcours :
ne pas recopier sa sortie complète dans la conversation et ne pas
demander `1pctl user-info` pour l'afficher dans les outils de l'agent.

## 4. Adaptation Tervo minimale et testée

Le correctif est conservé dans :
[1panel-v2.3.2-private-admin.patch](../../../../deploy/patches/1panel-v2.3.2-private-admin.patch).

Son seul changement :

```diff
     Set_Port
-    Set_Firewall
+    # Tervo manages UFW separately: do not open the administration port.
     Set_Entrance
```

La fonction d'ouverture reste dans le fichier fournisseur mais n'est
plus appelée par le flux principal. Aucun binaire, réglage Docker,
port choisi ou mécanisme d'authentification n'est changé par le patch.
Le bind loopback éventuel dépendra des possibilités réelles du panneau ;
il n'est pas prétendu obtenu par ce correctif.

Tests réellement exécutés localement :

1. Application à blanc de `patch --batch --fuzz=0 --dry-run`.
2. Application sur une copie de `install.sh`, original conservé.
3. `bash -n` sur la copie adaptée : syntaxe valide.
4. Comparaison complète en Python : la copie est exactement l'original
   avec cet unique appel remplacé ; aucun autre changement.

Ces contrôles ont réussi. Ils ne constituent pas une installation de
1Panel, un test d'UFW sur le VPS ni une validation de ses binaires.
Pour une autre version, revérifier archive, script, patch et comportement ;
ne pas accepter un patch appliqué avec fuzz ou à un emplacement inattendu.

## 5. Accès rétabli et préparation vérifiée sur le VPS

Au début de cette préparation, `ssh-add -l` retourne que l'agent courant
ne contient aucune identité. La tentative avec `BatchMode=yes`,
`StrictHostKeyChecking=yes` et la clé nommée est refusée.
Cela ne démontre pas une panne du serveur : la clé locale chiffrée ne
peut pas être déverrouillée sans interaction quand l'agent est vide.

L'utilisateur a ensuite chargé la clé dans l'agent accessible au terminal de
l'agent, en saisissant la passphrase **localement**. Le socket exact est
temporaire et doit être relu à chaque environnement ; ne pas recopier
un chemin `/tmp/ssh-...` ancien comme une configuration permanente.

L'agent a repris uniquement INT-124 après le découpage du chantier :

| Lecture/opération de préparation | Résultat |
|---|---|
| Connexion neuve | `tervo`, noyau Security 6.12.111 ; SSH/Docker/UFW actifs, `ENABLED=yes` |
| Installation existante | `/opt/1panel` et les binaires core/agent/1pctl absents |
| Port 7410 | Aucune écoute TCP constatée |
| Docker/Compose | 29.8.2 / v5.6.0 avant installation |
| `/etc/docker/daemon.json` | Absent avant installation |
| Préparation | `/home/tervo/1panel-preparation/v2.3.2`, répertoires mode 700 |
| Archive sur VPS | Même URL/version/empreinte, `sha256sum --check` retourne OK |
| Copie corrigée | Patch sans fuzz, `bash -n`, comparaison complète d'unique remplacement et marqueur `intl` validés |
| Script corrigé | `install-tervo.sh`, mode 600, propriétaire `tervo` |
| Sudo agent | Mot de passe requis ; aucun contournement ajouté |

Empreintes des textes contrôlés sur le VPS :

```text
install.sh:
3faa744fd158283470b48b3a971dc98cc390c7f291d4287b170416ae862dd28f
install-tervo.sh:
1f837c58eaf22c6230b25c6dda0c152d540007db145448009cbd4eb4f8c897f0
```

À cette étape de préparation, seuls téléchargement/extraction et fichiers
publics avaient été traités sous `tervo`, sans exécution de l'installateur.
Les scripts ne sont pas modifiés au-delà de l'unique appel pare-feu.

## 6. Installation exécutée par l'utilisateur, puis suspendue

L'installation reste interactive pour la saisie privée des identifiants.
Le bloc ci-dessous vérifie la copie préparée, refuse un état 1Panel
préexistant, utilise un umask restrictif et conserve le Docker/config
existant. Il a été fourni au terminal VPS privé de l'utilisateur.
Ne pas le rejouer : le contrôle suivant a révélé une exposition du panneau.

```bash
sudo bash -c '
set -eu
umask 077
if [ -e /opt/1panel ] || [ -L /opt/1panel ] || [ -e /usr/local/bin/1panel-core ]; then
  echo "Arrêt : installation ou données 1Panel préexistantes."
  exit 1
fi
cd /home/tervo/1panel-preparation/v2.3.2/1panel-v2.3.2-linux-amd64
printf "%s  %s\n" 1f837c58eaf22c6230b25c6dda0c152d540007db145448009cbd4eb4f8c897f0 install-tervo.sh | sha256sum --check -
exec bash install-tervo.sh --lang en --install-dir /opt --port 7410 \
  --install-docker n --configure-accelerator n --replace-daemon-json n
'
```

Prompts restant à traiter : entrée privée, nom du compte panneau et
mot de passe. Dans cette version, entrée/nom acceptent 3 à 30 caractères
alphanumériques/underscore ; le mot de passe 8 à 30 caractères dans
l'alphabet validé par l'installateur. Utiliser par exemple un secret
alphanumérique aléatoire de 24 caractères créé dans le gestionnaire
de mots de passe, distinct de SSH/sudo ; ne pas accepter le secret court
généré par défaut.

Ne pas ouvrir 7410 malgré une consigne générique affichée en fin
d'installation. Conserver les identifiants et l'entrée dans le gestionnaire
privé et ne pas partager le dernier écran ou le journal intégral.
Si un état préexistant ou une erreur est rencontré, arrêter et diagnostiquer
plutôt que relancer l'installateur ou effacer `/opt/1panel`.

## 7. Incident : port d'administration public malgré le patch

Après confirmation « installé » de l'utilisateur, l'agent a contrôlé
uniquement métadonnées et réseau, sans lire les identifiants ni le journal
privé. Core/agent étaient actifs et activés au démarrage, les binaires
root en mode 700 et le journal root en mode 600. Docker/Compose restaient
29.8.2 / v5.6.0, daemon.json toujours absent.

Le socket du panneau écoutait sur **0.0.0.0:7410**. L'accès local HTTP
répondait 200, puis la connexion TCP **extérieure** et un GET anonyme sur
la racine publique ont réussi avec HTTP 200. L'isolation a donc échoué :
`ENABLED=yes` et service UFW actif ne suffisaient pas à prouver les règles
attendues. Aucun login authentifié ou accès aux données du panneau n'a
été effectué dans ces tests ; ils ne prouvent ni absence ni présence
d'une compromission extérieure.

L'utilisateur a immédiatement exécuté :

```bash
sudo systemctl stop 1panel-core 1panel-agent &&
sudo ss -lntp 'sport = :7410'
sudo ufw status verbose
```

Plus d'écoute 7410. L'agent a confirmé core/agent inactifs et connexion
extérieure refusée, SSH/Docker/UFW restant actifs.
Les règles reçues comportent des ALLOW **7410/tcp et 443/udp** en IPv4
et IPv6, commentés `1panel-rule:<uuid>`, en plus des règles humaines
22/80/443 TCP. Les unités du panneau restent encore activées au démarrage
à ce contrôle : éviter tout reboot tant que le confinement n'est pas complet.
Aucune adresse IPv6 globale n'a été trouvée sur ce VPS.

### Cause confirmée par lecture du code public v2.3.2

L'agent 1Panel synchronise au démarrage une whitelist persistante :

- [Démarrage de l'agent](https://github.com/1Panel-dev/1Panel/blob/v2.3.2/agent/server/server.go#L117-L123)
  appelle `firewall.Init`.
- [Synchronisation](https://github.com/1Panel-dev/1Panel/blob/v2.3.2/agent/app/service/firewall_sync.go#L33-L49)
  charge `FirewallPortWhiteList` et réconcilie le backend sélectionné.
- [Valeurs par défaut](https://github.com/1Panel-dev/1Panel/blob/v2.3.2/agent/constant/firewall.go#L25-L30)
  incluent 443/udp ; l'administration est enregistrée comme port de type `panel`.
- [Adaptateur UFW](https://github.com/1Panel-dev/1Panel/blob/v2.3.2/agent/utils/firewall/filter/providers/ufw/adapter.go#L344-L360)
  génère le marqueur `1panel-rule:<uuid>`.

Ces observations concordent avec les règles de la distribution installée.
Retirer seulement l'appel `Set_Firewall` du shell ne supprime pas ce second
mécanisme. Supprimer les ALLOW puis redémarrer l'agent peut les recréer.
Aucun commutateur global supporté de désactivation n'a été trouvé dans
ce code public ; ne pas inventer une option CLI ou modifier sa DB interne.

Le core dispose d'un
[réglage authentifié d'adresse d'écoute](https://github.com/1Panel-dev/1Panel/blob/v2.3.2/core/app/service/setting.go#L337-L348)
qui permet de demander `BindAddress=127.0.0.1` avec IPv6 désactivé.
Il reste à vérifier sur la distribution internationale installée.
`1pctl listen-ip ipv4` force au contraire 0.0.0.0 : ce n'est pas une
commande pour obtenir le loopback.

## 8. Confinement persistant effectué et contrôlé

Le panneau était arrêté mais son démarrage automatique restait activé.
L'utilisateur a exécuté les commandes suivantes ; elles ne
suppriment ni données du panneau ni configuration Docker :

```bash
sudo systemctl disable --now 1panel-core 1panel-agent
sudo ufw delete allow 7410/tcp
sudo ufw delete allow 443/udp
sudo ufw insert 1 deny 7410/tcp comment 'Administration 1Panel privee'
sudo ufw status verbose
```

Si une règle n'est pas supprimée, inspecter le statut numéroté avant toute
suppression par numéro ; ne pas supposer un ordre ni toucher aux règles SSH.
Le DENY est une protection de confinement, **pas** une preuve que la
synchronisation future de 1Panel est désactivée. La reprise contrôlée du
core seul est décrite en section 10 ; elle ne valide pas la reprise de l'agent.

Les sorties de l'utilisateur confirment les suppressions IPv4/IPv6,
un DENY 7410 en tête et seulement les ALLOW 22/80/443 TCP.
L'agent a contrôlé core/agent `inactive` et `disabled`, aucune écoute
7410 et SSH/Docker/UFW actifs. Ce contrôle valide le confinement,
pas l'isolation d'un panneau en cours de fonctionnement.

## 9. Décision approuvée, mise en œuvre encore partielle

Le réglage supporté du core permet de lier l'administration à 127.0.0.1.
Le frontend public de v2.3.2 comporte un formulaire Security / bind avec
IPv6 désactivable et saisie manuelle d'une adresse IPv4 :
[formulaire bind](https://github.com/1Panel-dev/1Panel/blob/v2.3.2/frontend/src/views/setting/safe/bind/index.vue).
Cette voie devra être testée sur la distribution installée, sans lire
les identifiants de l'utilisateur.

La doctrine « aucune règle UFW gérée par 1Panel » n'est pas compatible
avec la synchronisation automatique stock identifiée dans cette version.
Les possibilités discutées :

- conserver 1Panel, rendre le bind loopback obligatoire et accepter/
  inventorier ses règles obligatoires comme exception explicite, avec
  tests de non-exposition après restart/upgrade et filtre fournisseur
  indépendant si disponible ;
- conserver une séparation firewall stricte : évaluer des restrictions
  OS avec tests de régression ou choisir un autre outil ; ne pas inventer
  une option de désactivation ni éditer sa DB interne sans support.

L'utilisateur a approuvé la première voie dans la conversation de reprise.
Ce choix évite un fork et utilise le réglage applicatif prévu. Il autorise
une exception documentée pour les règles automatiques, **pas une administration
publique**. Chaque règle réellement recréée devra être inventoriée ; le cas
443/UDP reste distinct de l'accès administratif sur 7410/TCP.
La reprise de l'agent n'a été proposée qu'après contrôle du bind privé ;
les observations après reprise figurent en section 11.

**Non validés :** version CLI, persistance après reboot réel,
contrôle après mise à jour, mode réel/recette de routage OpenResty et
déploiement Tervo.
INT-124 reste ouverte : préparation, accès privé en fonctionnement et
installation du proxy sont cochés, pas la recette de routage ni la
persistance après reboot/mise à jour.

## 10. Incident d'accès SSH : tunnel ouvert, panneau arrêté

### Symptômes et diagnostic

Après saisie de la passphrase, la commande `ssh -N` restait silencieuse.
Ce comportement est normal : `-N` n'ouvre pas de shell et maintient le tunnel.
Le navigateur affichait ensuite « This site can't be reached » et SSH :

```text
channel 1: open failed: connect failed: Connection refused
```

Cette erreur signifie que SSH n'a pas pu établir la connexion vers la cible
du tunnel sur le VPS. Les lectures fournies par l'utilisateur ont confirmé
core/agent `inactive` et aucune écoute TCP sur 7410. Le panneau avait été
arrêté volontairement après l'incident d'exposition ; le tunnel ne le démarre
pas. Le chemin d'entrée et les identifiants n'étaient pas encore examinés.

Le poste possède aussi un 1Panel local. Réutiliser le même chemin d'entrée
ne confond pas les panneaux : adresse et port déterminent la destination,
et les comptes des deux installations restent indépendants.

### Comprendre les deux ports

Commande sur **le poste local**, laissée ouverte pendant la navigation :

```bash
ssh -N \
  -o IdentitiesOnly=yes \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -i "$HOME/.ssh/tervo_ed25519" \
  -L 127.0.0.1:17410:127.0.0.1:7410 \
  tervo@151.241.228.152
```

| Élément | Rôle |
|---|---|
| `127.0.0.1:17410` à gauche | Écoute SSH sur le poste ; port choisi pour éviter un conflit avec le panneau local |
| `127.0.0.1:7410` à droite | Destination sur le VPS ; port réel du panneau, non modifié par le tunnel |
| URL du navigateur | `http://127.0.0.1:17410/<entree-privee>` dans la configuration HTTP utilisée |
| `ExitOnForwardFailure` | Échec si l'écoute locale ne peut pas être créée ; ne garantit pas la disponibilité du panneau distant |

Le tunnel transporte les échanges dans SSH : aucun navigateur sur le VPS
n'est nécessaire. Le chemin privé, les mots de passe et la passphrase ne sont
pas consignés ici. `Ctrl+C` ferme le tunnel, pas le panneau.

### Reprise contrôlée observée

Avant démarrage, l'utilisateur a fourni UFW actif, DENY 7410/TCP IPv4 et IPv6
en tête des règles de chaque famille, et seulement ALLOW 22/80/443 TCP.
`systemctl show 1panel-core -p Requires -p Wants -p After` ne déclarait
aucune dépendance vers l'agent. Le core a donc été démarré seul :

```bash
sudo systemctl start 1panel-core
systemctl is-active 1panel-core 1panel-agent
sudo ss -lntp 'sport = :7410'
sudo ufw status numbered
```

Résultats transmis : core `active`, agent `inactive`, règles UFW inchangées.
La première lecture `ss` ne montrait pas encore d'écoute ; une lecture
ultérieure montrait `1panel-core` sur **0.0.0.0:7410**. Cela illustre que
le statut systemd `active` ne prouve pas à lui seul la disponibilité HTTP.
L'utilisateur a ensuite confirmé l'accès et la connexion au panneau via
le tunnel. Aucun contrôle extérieur nouveau n'a été exécuté dans cette reprise.

### Plan de correction après la reprise du core seul

1. Dans le panneau VPS, régler l'adresse d'écoute sur `127.0.0.1` et
   désactiver IPv6 pour cette écoute ; ne pas confondre ce champ avec
   une liste d'IP autorisées ou un domaine.
2. Vérifier `ss` : uniquement `127.0.0.1:7410`, sans écoute `0.0.0.0` ou `[::]`.
3. Vérifier que le tunnel fonctionne toujours et que l'accès extérieur échoue.
4. Reprendre l'agent de manière contrôlée, inventorier ses règles et
   recontrôler le bind et la non-exposition après redémarrage.
5. Valider la persistance avant réactivation au boot ; contrôler à nouveau
   après chaque mise à jour. Le pare-feu fournisseur reste non inventorié.

À ce stade historique, le DENY UFW protégeait un core encore lié à toutes
les interfaces IPv4, **pas la configuration finale approuvée**. La suite
ci-dessous actualise le diagnostic et le bind. OpenResty reste à traiter
dans INT-124 ; passer à INT-125 serait prématuré.

## 11. Erreur 502 après login : agent arrêté, puis reprise sous bind privé

La requête `POST /api/v2/settings/search` échouait avec :

```text
Bad Gateway: dial unix /etc/1panel/agent.sock: connect: connection refused
```

Ce diagnostic concerne le proxy vers l'agent local, pas le tunnel SSH ni
les identifiants. Le core seul permet le login, mais ne suffit pas aux
pages appelant les API de l'agent. Ne pas confondre cette route avec
`/api/v2/core/settings/bind/update`, traitée par le core.

Le réglage anglais recherché est **Bind info**, puis **Listen address**,
sur `/settings/safe`. Le paramètre `?uncached=1` permet d'éviter le retour
automatique vers un onglet mémorisé. **System address** sert aux redirections
et liens applicatifs ; ce n'est pas l'adresse d'écoute du panneau.

L'utilisateur a appliqué `127.0.0.1` via le réglage officiel et transmis
une écoute loopback après redémarrage du core. La reprise proposée était
alors `sudo systemctl start 1panel-agent`, sans réactivation au boot.
Cette commande a été proposée à l'utilisateur, **pas exécutée par Delta** :
l'agent était déjà actif au premier contrôle SSH réussi. Le résultat
confirme sa reprise, mais aucune trace d'exécution du démarrage n'a été
fournie pour en attribuer l'auteur avec certitude.
L'utilisateur a autorisé les contrôles distants et chargé sa clé dans
l'agent SSH local avec une durée limitée. Aucune passphrase ni cookie
de session n'a été utilisé ou consigné par l'agent Delta.

### Contrôles exécutés à distance après reprise

| Lecture | Résultat réellement observé |
|---|---|
| `systemctl is-active 1panel-core 1panel-agent` | Les deux `active` |
| `systemctl is-enabled 1panel-core 1panel-agent` | Les deux `disabled` |
| `ss -lnt 'sport = :7410'` | Uniquement `127.0.0.1:7410`, sans écoute IPv6 |
| `ss -lx` filtré sur 1Panel | Socket `/etc/1panel/agent.sock` en LISTEN |
| `systemctl show` core/agent | `running`, `NRestarts=0` pour les deux |
| GET anonyme `http://127.0.0.1:7410/` sur le VPS | HTTP 200 ; ne valide pas une requête authentifiée vers l'agent |
| Connexion TCP à l'IPv4 publique, port 7410, depuis le poste de l'agent Delta | Timeout après 5 secondes, aucune connexion établie |
| `sudo -n true` | Mot de passe requis ; aucune élévation ni modification distante effectuée par Delta |

Le répertoire `/etc/1panel` est root-only (700) : un `test -S` exécuté
comme `tervo` ne pouvait pas confirmer le fichier. `ss -lx` a permis
de vérifier l'écoute sans modifier les permissions. Le timeout extérieur
prouve seulement l'échec depuis ce poste à cet instant, pas son mécanisme
exact ni la politique du pare-feu fournisseur.

La dépendance manquante est désormais active et son socket écoute.
L'utilisateur a ensuite confirmé l'affichage des informations VPS et
l'absence de 502 dans le navigateur. Sa sortie `sudo ufw status numbered`
confirme UFW actif, DENY 7410/TCP IPv4/IPv6 et uniquement ALLOW 22/80/443 TCP.
Aucun ALLOW automatique 7410/TCP ou 443/UDP n'est visible à ce contrôle ;
cela ne garantit pas le comportement d'un prochain redémarrage ou upgrade.
Les cookies partagés n'ont pas été réutilisés pour le test.
Une déconnexion/reconnexion a été recommandée
pour invalider la session partagée, sans prétendre que cette action a eu lieu.

### Persistance après redémarrage des deux services

L'utilisateur a exécuté :

```bash
sudo systemctl restart 1panel-core 1panel-agent &&
sudo ss -lntp 'sport = :7410' &&
sudo ufw status numbered
```

La lecture immédiate `ss` était vide. Un contrôle ultérieur, sans nouveau
restart entre les deux lectures, a confirmé core/agent `active` et
**127.0.0.1:7410 uniquement**, core PID 12322. Le retour de la commande
systemd n'est donc pas une preuve de readiness : attendre la disponibilité
et relire l'écoute plutôt que répéter les redémarrages.

UFW reste actif avec les mêmes DENY 7410 IPv4/IPv6 et ALLOW 22/80/443 TCP.
Delta a répété le test TCP public IPv4 après cette reprise : timeout
après 5 secondes, aucune connexion établie. Le bind privé a donc résisté
au restart des deux services ; cela ne vaut pas validation d'un reboot VPS.

L'utilisateur a ensuite exécuté :

```bash
sudo systemctl enable 1panel-core 1panel-agent &&
systemctl is-enabled 1panel-core 1panel-agent
```

La sortie confirme la création des deux liens sous
`multi-user.target.wants`, puis `enabled` pour chaque unité. L'activation
au boot est donc configurée ; `enable` n'effectue ni restart ni reboot.
Cela ne prouve pas encore le bon fonctionnement après un démarrage réel du VPS.

**Suite nécessaire :** confirmer le panneau dans le navigateur après le
dernier restart, puis inventorier et préparer OpenResty sans créer une
seconde stack Tervo. Pas de nouveau test IPv6 externe, mise à jour, reboot
ou déploiement Tervo effectué dans cette vérification.

## 12. Inventaire avant installation OpenResty

L'utilisateur a exécuté les lectures suivantes sur le VPS :

```bash
sudo docker ps -a \
  --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
sudo ss -lntp '( sport = :80 or sport = :443 )'
```

Les sorties ne contiennent que les en-têtes : aucun conteneur, y compris
arrêté, n'est présent dans le daemon interrogé et aucune écoute TCP sur
80/443 n'est constatée à cet instant. Cela permet de préparer le proxy
sans remplacer un conteneur existant ; ce n'est pas une installation
OpenResty ni un test de trafic HTTP/HTTPS public.

Étape proposée : ouvrir le formulaire d'installation OpenResty dans
1Panel, relever la version et les options réseau/ports avant confirmation.
Le mode effectif devra ensuite être contrôlé par `docker inspect` :
host permet les upstreams loopback du VPS ; bridge exige un réseau partagé
et des noms Docker, jamais une IP statique de conteneur. Aucune stratégie
n'est déclarée installée sur la seule base de cet inventaire.

### Formulaire relevé avant confirmation

L'utilisateur a fourni les paramètres suivants :

| Champ | Valeur proposée |
|---|---|
| Version | `1.31.1.1-2-4-noble` |
| HTTP / HTTPS | `80` / `443` |
| Website directory | `/opt/1panel/www` |
| Restart policy | `always` |
| CPU / mémoire | `0` / `0`, sans quota explicite |
| Pull image | Coché |

Ces valeurs sont retenues pour l'installation proposée, **pas déclarées
installées**. `noble` désigne la base de l'image, pas un changement de
distribution du VPS Debian. Le modèle public correspondant utilise
`network_mode: host` :
[Compose du catalogue 1Panel](https://github.com/1Panel-dev/appstore/blob/dev/apps/openresty/1.31.1.1-2-4-noble/docker-compose.yml).
Le mode effectif, l'image, les ports et la disponibilité devront être
contrôlés sur le conteneur créé. Les quotas à zéro ne signifient pas
absence de consommation ; des limites éventuelles nécessiteront une mesure.

## 13. Installation OpenResty effectuée, routage encore à valider

L'utilisateur a confirmé l'installation depuis le catalogue 1Panel.
Le journal fourni indique le téléchargement de l'archive de version,
le succès du script init, le pull de l'image, puis :

```text
2026/10/07 18:52:02 Start Application Success
2026/10/07 18:52:02 InstallApplication [openresty] succeeded
```

Ces horaires proviennent du journal transmis, pas d'une mesure de durée
ou d'une validation du fuseau horaire par Delta.

| Observation | Résultat |
|---|---|
| Conteneur | `1Panel-openresty-wTu3` |
| Image affichée par `docker ps -a` | `1panel/openresty:1.31.1.1-2-4-noble` |
| État transmis | `Up About a minute` |
| Écoutes `ss` utilisateur | `0.0.0.0:80`, `0.0.0.0:443`, `[::]:80`, `[::]:443`, processus OpenResty |
| GET HTTP sur l'IPv4 publique depuis Delta | HTTP 200 |
| Tentative TCP publique 7410 depuis Delta après installation | Timeout 5 secondes ; aucune connexion établie |

L'écoute publique 80/443 est attendue pour le proxy. Elle ne doit pas
être confondue avec celle de l'administration 7410, qui doit rester
loopback. La colonne Docker PORTS vide est compatible avec le mode host,
mais `docker inspect` reste nécessaire pour le confirmer.

**Pas encore validés :** configuration `nginx -t`, mode réseau réel,
règles UFW et bind 7410 relus après installation, routage/rechargement
sur cible jetable, résolution après recréation si bridge. HTTP 200 sur
la racine du proxy ne signifie ni déploiement Tervo ni certificat HTTPS
valide ; aucun site Tervo ou certificat n'est déclaré livré.
