# INT-124 — Administration 1Panel privée et proxy OpenResty

**État : terminé pour le périmètre INT-124.** Installation, accès privé,
routage sur cible jetable, nettoyage et retour après reboot sont vérifiés.
L'utilisateur a confirmé le panneau dans le navigateur après relance du
tunnel, informations VPS affichées sans 502.

Ce résultat ne signifie pas que Tervo est déployé : ni application, ni
PostgreSQL, ni certificat Tervo, ni release automatisée ne sont livrés ici.
Aucune mise à jour 1Panel n'a été exécutée pour fabriquer une validation ;
les contrôles après une mise à jour réelle constituent la procédure de
maintenance décrite ci-dessous.

Références :
- [tâche et critères](../../../docs/stages/stage7/sprint7.6/tasks.md) ;
- [cas TC-INT-111-02, propriétaire INT-124](../../../docs/stages/stage7/sprint7.6/test-cases.json) ;
- [journal de réalisation, incidents et preuves détaillées](../deploy/vps/03-preparation-1panel-prive.md) ;
- [patch historique et avertissement](../../../deploy/patches/README.md).

## 1. Ce que nous avons installé, et ce que nous n'avons pas installé

| Élément | État observé |
|---|---|
| 1Panel | `v2.3.2`, canal `stable`, confirmé par `sudo 1pctl version` |
| Core / agent | Services systemd actifs et activés au démarrage |
| Administration | `127.0.0.1:7410`, pas `0.0.0.0` ni `[::]` |
| Socket de l'agent | `/etc/1panel/agent.sock`, écoute observée avec `ss -lx` |
| Installation panneau | Sous `/opt/1panel`, avec le Docker existant |
| OpenResty | `1Panel-openresty-wTu3`, image `1panel/openresty:1.31.1.1-2-4-noble` |
| Réseau OpenResty | `host`, confirmé par `docker inspect` |
| Politique du conteneur | `always` |
| Répertoire des sites choisi | `/opt/1panel/www` |
| HTTP / HTTPS du proxy | Écoutes TCP 80/443 IPv4 et IPv6 |
| Cible/site de recette | Arrêtés/supprimés après le test |

Le canal `stable` ne décrit pas une licence. Aucune activation Pro n'a
été réalisée dans le parcours accompagné ; cela ne prétend pas à un audit
exhaustif des licences via l'API privée du panneau.

`noble` est la base de l'image OpenResty, pas la distribution du VPS.
Le serveur reste sous Debian. Les limites CPU/mémoire à zéro dans le
formulaire ne signifient pas zéro consommation : aucun quota explicite
n'a été fixé dans cette première installation.

Git/Compose restent la source de vérité des futurs services Tervo.
1Panel gère le proxy et, plus tard, les certificats : aucun second
PostgreSQL ni runtime applicatif n'a été créé dans le panneau.

## 2. Comprendre les couches de cette installation

```text
Administration :
  navigateur du poste → tunnel SSH → core 127.0.0.1:7410
                                      ↓
                              agent via socket Unix

Trafic public :
  Internet → OpenResty 80/443, réseau host → upstream loopback du VPS
```

| Couche | Responsabilité |
|---|---|
| Navigateur | Afficher le panneau et appeler ses API |
| SSH | Authentifier le transport et acheminer les connexions vers le VPS |
| Core 1Panel | Connexion au panneau, interface et réglages tels que le bind |
| Agent 1Panel | Opérations locales, informations système et gestion Docker |
| OpenResty | Recevoir le trafic public et router vers les services |
| systemd / Docker | Faire fonctionner les services indépendamment du terminal SSH |
| UFW | Filtrer le trafic réseau ; ne crée pas une écoute applicative |

Les opérations Docker ont été réalisées avec `sudo` par l'utilisateur.
L'accès Delta n'a pas contourné le mot de passe sudo et aucun
`NOPASSWD: ALL` n'a été ajouté dans ce parcours. Ajouter un compte au
groupe `docker` lui donnerait des privilèges pratiquement root-equivalent ;
ce n'est pas une simple autorisation d'observation à imposer par défaut.

Il n'y a pas ici de route métier FastAPI, de service ORM, de transaction
PostgreSQL ou de migration Alembic. Ces couches applicatives appartiennent
aux tâches suivantes ; il ne faut pas attribuer leur validation à cette
recette d'infrastructure.

## 3. Le vrai correctif : une écoute privée, pas seulement une règle UFW

### Le patch shell ne couvrait qu'un mécanisme

L'archive explicite et son SHA-256 publié ont été vérifiés avant extraction.
Cela établit une concordance avec le checksum reçu via HTTPS, pas une
signature indépendante ni un audit de tous les binaires.

Le [patch archivé](../../../deploy/patches/1panel-v2.3.2-private-admin.patch)
changeait uniquement l'appel suivant de l'installateur :

```diff
     Set_Port
-    Set_Firewall
+    # Tervo manages UFW separately: do not open the administration port.
     Set_Entrance
```

La synchronisation `FirewallPortWhiteList` des binaires était un deuxième
mécanisme. Le premier contrôle a constaté une écoute `0.0.0.0:7410`,
des ALLOW 7410/TCP et 443/UDP, et une réponse HTTP extérieure.
Le commentaire du patch décrit donc une intention historique, pas une
garantie effective. Ne pas rejouer l'installateur comme une procédure sûre.

### Comparaison des stratégies

| Stratégie | Décision |
|---|---|
| Retirer l'appel shell et supposer le panneau privé | Rejetée : l'incident réel l'a invalidée |
| Supprimer les ALLOW sans contrôler le bind | Insuffisante : une synchronisation peut les recréer |
| Modifier les binaires ou la DB interne du panneau | Non retenue : coût de maintenance et mécanisme non supporté |
| Réglage officiel loopback, filtre conservé et tests extérieurs | Retenue et approuvée par l'utilisateur |

Le champ officiel est **Bind info → Listen address**, avec IPv6 désactivé
pour cette écoute. **System address** est un autre réglage : il sert aux
liens/redirections des applications et ne rend pas l'administration privée.

Une règle ALLOW ne rend pas accessible une application liée exclusivement
au loopback. En revanche, le retour à `0.0.0.0` ou `[::]` serait dangereux
si le filtre était permissif. Nous contrôlons donc **bind, règles et accès
extérieur**, pas un seul de ces éléments.

L'exception de gestion firewall est explicite : 1Panel peut synchroniser
des règles, qu'il faut inventorier. Elle n'autorise jamais une administration
publique. Les dernières sorties, y compris après reboot, conservent DENY
7410 IPv4/IPv6 et seulement ALLOW 22/80/443 TCP. Aucune nouvelle règle
443/UDP n'y est visible ; son éventuelle apparition doit être évaluée
séparément, sans la déclarer nécessaire à Tervo.

## 4. Le tunnel : deux ports, deux machines

Commande du poste administrateur :

```bash
ssh -N \
  -o IdentitiesOnly=yes \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -i "$HOME/.ssh/tervo_ed25519" \
  -L 127.0.0.1:17410:127.0.0.1:7410 \
  tervo@151.241.228.152
```

| Partie | Sens |
|---|---|
| `127.0.0.1:17410` à gauche | Écoute SSH sur le poste local |
| `127.0.0.1:7410` à droite | Destination sur le VPS |
| URL utilisée | `http://127.0.0.1:17410/<entree-privee>` |
| `-N` | Aucun shell distant : le terminal silencieux est normal |
| `ExitOnForwardFailure` | Détecte l'échec de création de l'écoute, pas la disponibilité HTTP de la cible |

17410 évite un conflit de port avec le panneau local du poste. Le port
du panneau VPS reste 7410. Un chemin d'entrée identique ne fusionne pas
les deux installations ; les comptes sont indépendants.

Les keepalives peuvent limiter les coupures d'inactivité, pas empêcher une
veille ou une panne réseau, ni reconnecter automatiquement. Leur effet
sur les coupures rapportées n'a pas été mesuré. Après reboot, relancer le
tunnel ; ne pas ouvrir 7410 pour contourner une perte SSH.

La passphrase et les cookies ne sont pas des données de diagnostic à
partager. Les cookies transmis dans la conversation n'ont pas été réutilisés
pour les contrôles ; une déconnexion/reconnexion a été recommandée, sans
prétendre qu'une invalidation de session a été vérifiée.

## 5. Deux erreurs distinctes, deux diagnostics

| Symptôme | Cause établie | Résolution observée |
|---|---|---|
| SSH silencieux après passphrase avec `-N` | Comportement normal sans shell | Laisser le tunnel ouvert |
| `channel ... connect failed: Connection refused` | Aucun panneau n'écoutait sur la cible 7410 | Démarrage du core sous protection UFW |
| HTTP 502, `dial unix /etc/1panel/agent.sock: connect: connection refused` | Agent arrêté | Agent revenu actif après application du bind privé |
| `ss` vide juste après `systemctl restart` | Lecture trop tôt ; l'écoute apparaît ensuite | Recontrôler la readiness sans répéter les restarts |

La requête `/api/v2/settings/search` passait par l'agent.
Le réglage d'écoute `/api/v2/core/settings/bind/update` était géré par
le core. Cela a permis de régler le bind avant la reprise de l'agent.
Ouvrir le login ne prouve donc pas que toutes les fonctions du panneau
sont disponibles.

Les actions privilégiées ont été exécutées par l'utilisateur. Delta a
effectué les contrôles SSH en lecture seule quand sa clé était chargée :
l'agent 1Panel était déjà actif à la première connexion réussie.
Il ne faut pas attribuer son démarrage à Delta. `ssh-add` charge une clé
sur le poste ; il ne démarre pas un service sur le VPS.

## 6. Pourquoi le mode host simplifie le routage

Contrôle réellement transmis :

```bash
sudo docker inspect 1Panel-openresty-wTu3 \
  --format 'NetworkMode={{.HostConfig.NetworkMode}} Restart={{.HostConfig.RestartPolicy.Name}}'
```

Résultat : `NetworkMode=host Restart=always`.

En mode host, OpenResty partage le réseau du VPS : son `127.0.0.1` permet
de joindre les services loopback du serveur. La colonne Docker PORTS vide
n'est pas une preuve d'absence d'écoute ; `ss` montrait bien 80/443.

En mode bridge, le même `127.0.0.1` désignerait le conteneur. Il faudrait
alors un réseau partagé et des noms Docker, avec contrôle après recréation.
Cette variante n'est pas le mode retenu ni une recette déclarée exécutée.
Ne pas coder une IP de conteneur ni ajouter `1panel-network` par habitude.

INT-125 devra adapter la stack applicative au mode **host observé** :
frontend/backend accessibles via des publications loopback, PostgreSQL
non publié. Nous n'avons pas modifié le Compose Tervo dans INT-124.

## 7. Recette utile : comparer un contenu, pas seulement un HTTP 200

La cible Python était liée à `127.0.0.1:18080`. Son handler renvoyait un
texte fixe, pas les fichiers du serveur :

```python
def do_GET(self):
    body = b"TERVO_PROXY_CHECK_OK\n"
    self.send_response(200)
    self.send_header("Content-Type", "text/plain")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)
```

Le site de test utilisait `tervo-proxy-check.invalid`. Le GET envoyait
explicitement l'en-tête Host : aucun DNS ou certificat n'était nécessaire.
Après `nginx -t`, l'utilisateur a effectué :

```bash
sudo docker exec 1Panel-openresty-wTu3 \
  /usr/local/openresty/nginx/sbin/nginx -s reload &&
curl --max-time 5 -fsS \
  -H 'Host: tervo-proxy-check.invalid' \
  http://127.0.0.1/
```

Le marqueur a été reçu après reload. Delta a ensuite comparé le corps
du GET public IPv4 au marqueur exact, avec le même Host. Un simple 200
de la page par défaut n'aurait pas prouvé le routage vers cette cible.

Le site a été supprimé selon confirmation utilisateur. La cible Python,
qui avait survécu à une déconnexion SSH, a été arrêtée ; `ss` ne montrait
plus d'écoute 18080. Pour les futurs tests, arrêter explicitement le
processus identifié. Ne pas utiliser un kill global de tous les Python.

## 8. Preuves de livraison et limites

Le cas propriétaire reste **TC-INT-111-02 → INT-124**, avec son historique
d'échec conservé. Sa réussite finale ne réécrit pas l'incident initial.

| Validation | Source et résultat |
|---|---|
| Archive et patch | Préparation documentée : hash vérifié, patch ciblé sans fuzz |
| CLI panneau | Utilisateur : v2.3.2, stable |
| Bind administratif | Utilisateur et lecture Delta : 127.0.0.1:7410 seulement |
| Tunnel/login et fonctions VPS | Utilisateur : accessibles sans 502, confirmé aussi après reboot |
| Réseau/configuration proxy | Utilisateur : host/always, nginx -t réussi |
| Upstream direct et après reload | Utilisateur : marqueur attendu |
| Upstream public IPv4 | Delta : HTTP 200 et corps exact |
| Nettoyage | Site supprimé confirmé, écoute 18080 absente |
| Retour après reboot | Utilisateur : SSH/Docker/UFW/core/agent actifs, OpenResty Up, bind/UFW conservés |
| Extérieur après reboot | Delta : HTTP 200 sans marqueur, TCP 7410/18080 en timeout |

`uptime -s` après reboot a affiché `2026-10-07 21:16:41`. La sortie avant
reboot n'a pas été reçue : aucune comparaison de deux dates n'est inventée.
Le refus TCP par timeout vaut échec d'accès depuis le poste de contrôle
à cet instant ; il ne prouve pas le mécanisme exact du filtre fournisseur.

Aucune IPv6 publique n'avait été trouvée dans l'inventaire initial :
aucun test extérieur IPv6 nouveau n'est revendiqué. Si une IPv6 publique
est attribuée ultérieurement, elle entre obligatoirement dans les contrôles.
La présence de `[::]:80/443` n'est pas à elle seule une preuve d'adresse
IPv6 globale ni de certificat HTTPS valide.

La recette ne vérifie pas la readiness DB, les workflows métier ou la
tenue sous charge. Aucune suite backend/frontend, migration PostgreSQL,
restauration de données, CI distante ou publication Tervo n'a été exécutée
au titre de cette clôture.

## 9. Maintenance obligatoire après restart ou mise à jour

Cette section est une **procédure**, pas un compte rendu d'upgrade réussi.
Ne pas mettre à jour artificiellement 1Panel pour cocher un test.

### Avant une mise à jour

1. Identifier version, conteneur/image et montage réels, sans afficher
   l'environnement complet avec ses secrets.
2. Préparer une sauvegarde privée des configurations/données concernées,
   avec les permissions et le mécanisme de restauration appropriés.
3. Conserver les références exactes des artefacts de retour ; un ancien
   tag ou un rebuild n'est pas automatiquement le même artefact.
4. Garder SSH et le secours fournisseur disponibles.

Lectures proposées pour identifier les sources, non exécutées ici comme
une sauvegarde :

```bash
sudo docker inspect 1Panel-openresty-wTu3 \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
sudo docker image inspect 1panel/openresty:1.31.1.1-2-4-noble \
  --format '{{json .RepoDigests}}'
```

Les noms peuvent changer lors d'une recréation : les relever à nouveau,
ne pas appliquer ces commandes à un conteneur supposé. Les archives de
sauvegarde peuvent contenir des secrets et ne doivent pas entrer dans Git.
La sauvegarde/restauration complète reste à vérifier dans INT-128.

### Après l'opération

Sur le VPS, relever services, bind administratif et règles :

```bash
systemctl is-active ssh docker ufw 1panel-core 1panel-agent
sudo ss -lntp 'sport = :7410'
sudo ufw status numbered
sudo docker ps -a \
  --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

Attendre la disponibilité réelle avant conclusion ; le retour systemd
ne garantit pas encore l'écoute HTTP. Contrôler le mode du proxy si le
conteneur est recréé et exécuter `nginx -t` avant tout reload.

Depuis un autre poste, vérifier un service public attendu puis tenter
une connexion TCP 7410 vers l'IPv4 et toute IPv6 publique. Un test depuis
le VPS seul ne remplace pas le contrôle extérieur. Exiger absence d'accès
administratif direct et succès du tunnel avec le panneau fonctionnel.

Chaque règle automatique doit être inventoriée : ne pas supprimer par
numéro sans relire UFW et ne pas toucher aux règles SSH. Si une règle
443/UDP apparaît, décider explicitement de son besoin et de sa protection.

## 10. Confinement et retour arrière

### Si l'administration devient publique

Le confinement suivant a été utilisé lors de l'incident initial :

```bash
sudo systemctl disable --now 1panel-core 1panel-agent
sudo ss -lntp 'sport = :7410'
sudo ufw status numbered
```

L'objectif est d'obtenir aucune écoute 7410, sans couper SSH ou Docker.
Inspecter les règles ; si le DENY manque, le rétablir de manière contrôlée
en IPv4/IPv6 avant toute reprise. Ne pas réinstaller, supprimer la DB
interne ou ouvrir le port public pour retrouver l'interface.

La reprise doit appliquer le réglage officiel loopback sous protection,
puis retester services/règles/extérieur/tunnel avant activation au boot.
Ce confinement d'administration est distinct d'une restauration complète
des données du panneau, qui n'a pas été testée.

### Si une configuration OpenResty est invalide

Ne pas recharger une configuration qui échoue à `nginx -t`.
Restaurer une version identifiée et sauvegardée via le mécanisme prévu,
tester sa syntaxe, puis seulement recharger et vérifier le routage.
En l'absence de sauvegarde exploitable, arrêter et diagnostiquer plutôt
qu'effacer des répertoires de sites. Aucun rollback d'upgrade complet
1Panel/OpenResty n'est déclaré exécuté dans INT-124.

## 11. Reprise du sprint

Les todos ont été relus : aucun todo explicite dépendant d'INT-124 n'est
débloqué à exécuter. TD-B010 et TD-B022 restent liés aux tâches DB/backup
et au déploiement réel ; ils ne sont pas clôturés par un proxy fonctionnel.

**Prochaine tâche : INT-125**, après feu vert distinct, pour une stack
de production reproductible et cohérente avec le mode host observé.
INT-126 à INT-130 et la mise en service INT-111 restent non livrés.
Ne pas activer `DEPLOY_ENABLED`, créer la DB, lancer un seed ou publier
les domaines applicatifs en prétendant prolonger simplement INT-124.
