# INT-111 — Mise en service publique manuelle

**Livraison d'une démo publique avec sauvegardes manuelles.**
HTTPS, admin et recette navigateur validés ; snapshot mini-s1 `03aca082`
acquis, archive récupérée et données SQL/relations/photos restaurées en cible
isolée sur le VPS, cible arrêtée puis supprimée avec les ressources de recette.
Fichiers privés récupérés intègres, pas de reconstruction complète du
proxy/console ou d'un clone HTTP.
Automatisation reportée avant clientèle réelle dans TD-B024 ; cache Docker
mini-s1 suivi dans TD-B025, remplacement local toujours ouvert dans TD-B010.
Reboot réel et retour services/HTTPS/ports/certificats vérifiés. Le nettoyage
ciblé a été exécuté par l'opérateur ; ses sorties sont consignées en section 23
et préservent la stack `tervo`, ses données, Dockge, les images et le dépôt
restic. La clôture documentaire reste le commit de livraison ; le bilan de
sprint dépend d'INT-112 (INT-130 a été livrée depuis). Aucun timer ni élargissement SSH activé.
Feu vert reçu après INT-129 `291f7ea`. Le `.gitignore` IDE local reste hors périmètre.

Le [parcours opérateur](../deploy/vps/05-tervo-release-et-exploitation.md)
explique les commandes et leurs limites. Cette note conserve les résultats
chronologiques : ne pas rejouer ses premières vérifications ou nettoyages
comme si le VPS était encore vide.

## Parcours retenu

1. Confirmer les noms publics, la source à publier et l'accès opérateur.
2. Préparer le vrai checkout/env privé, vérifier l'absence de collision,
   puis utiliser `release.py` avec une base neuve conformément à INT-127.
   Ne pas promouvoir les anciennes données de recette comme données métier réelles.
3. Bootstrap admin sans seed, contrôles loopback, puis bascule DNS/Caddy/TLS
   et recette navigateur. Pas d'exposition du candidat avant les prérequis.
4. Vérifier les sauvegardes/récupération et l'exploitation réelle prévues par
   INT-111, puis noter uniquement les preuves effectivement acquises.

Réutiliser le code/procédures existants ; pas de nouveau harness ni de nouvelle
matrice de pannes. Le contrôle fonctionnel INT-129 n'est pas à refaire intégralement.
INT-130 reste une autre tâche, après mise en service manuelle validée.

## 1. Préflight SSH — lecture seule

Commande exécutée depuis le poste de l'agent :

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 \
  -o ControlPath=none tervo@151.241.228.152 \
  'id; hostname; systemctl is-active caddy docker; sudo -n true'
```

Résultat observé, code global 1 :

```text
uid=1000(tervo) gid=1000(tervo) groups=1000(tervo),27(sudo),100(users)
22565
active
active
sudo: a password is required
```

| Commande | But | Résultat / limite |
|---|---|---|
| SSH batch / clé d'hôte stricte | Tester l'accès sans saisie ni acceptation aveugle | Connexion réussie |
| `id`, `hostname` | Identifier hôte/compte | `tervo`, pas root, sur `22565` |
| `systemctl is-active caddy docker` | Lire les services hôte | Les deux actifs ; pas un inventaire Docker privilégié |
| `sudo -n true` | Tester les droits non interactifs | Refus ; les opérations administrateur restent à faire via le terminal root opérateur, pas par une nouvelle règle large |

## 2. DNS des noms candidats — lecture seule

Ces noms provenaient du fichier `.env.example` et du profil Caddy inactif :
ils ont ensuite été confirmés par l'utilisateur, avant publication du code.

```sh
dig +noall +answer tervoapp.com A
dig +noall +answer tervoapp.com AAAA
dig +noall +answer api.tervoapp.com A
dig +noall +answer api.tervoapp.com AAAA
dig +noall +answer tervoapp.com CAA
```

Réponses observées, code 0 :

```text
tervoapp.com.       300 IN A    104.21.27.9
tervoapp.com.       300 IN A    172.67.140.74
tervoapp.com.       300 IN AAAA 2606:4700:3036::6815:1b09
tervoapp.com.       300 IN AAAA 2606:4700:3034::ac43:8c4a
api.tervoapp.com.   300 IN A    104.21.27.9
api.tervoapp.com.   300 IN A    172.67.140.74
api.tervoapp.com.   300 IN AAAA 2606:4700:3036::6815:1b09
api.tervoapp.com.   300 IN AAAA 2606:4700:3034::ac43:8c4a
```

CAA : aucune ligne de réponse retournée pour la requête effectuée, pas une
validation générale de l'émission de certificat.

| Élément | But / interprétation |
|---|---|
| `A`, `AAAA` | Lire séparément IPv4 et IPv6, sans modifier le DNS |
| `+noall +answer` | Afficher les réponses utiles, pas un dump complet |
| Adresses Cloudflare | Ne montrent pas directement l'IP d'origine ; ne prouvent ni l'état du tunnel historique ni l'origine derrière le proxy |
| Cible recommandée | Pour le VPS direct validé au cadrage : DNS seul vers `151.241.228.152`, sans AAAA d'origine non validée |

À ce stade initial, aucun enregistrement n'avait été modifié. La réception
email a ensuite été configurée séparément (section 8) ; elle ne prouve pas
la bascule DNS web ni l'activation HTTPS.

## 3. Source Git à rendre disponible

```sh
git ls-remote origin refs/heads/main
```

Réponse observée :

```text
0c1269ab7e4d3020ddea347db13715a5b2e09f1a refs/heads/main
```

L'objet étant présent localement, les contrôles de lecture ont été :

```sh
git show -s --format='%h %s' 0c1269ab7e4d3020ddea347db13715a5b2e09f1a
git merge-base --is-ancestor 291f7ea 0c1269ab7e4d3020ddea347db13715a5b2e09f1a
git merge-base --is-ancestor 0c1269ab7e4d3020ddea347db13715a5b2e09f1a 291f7ea
```

Résultat : commit distant `0c1269a [DOC] Fuliyeh — Aligner le contexte Caddy et
Dockge`, descendant de `291f7ea` **non**, ancêtre de `291f7ea` **oui**.
`git show` a réussi ; les deux tests `merge-base --is-ancestor` étaient
silencieux, avec codes 1 puis 0 respectivement.
Le code livré INT-129 n'était donc pas encore publié sur `origin/main`.

### Publication effectuée (feu vert utilisateur)

```sh
git merge-base --is-ancestor 0c1269ab7e4d3020ddea347db13715a5b2e09f1a 291f7ead24822cf8f9c0164aaf9dc3420d351647
git push origin 291f7ead24822cf8f9c0164aaf9dc3420d351647:refs/heads/main
git ls-remote origin refs/heads/main
```

Résultat observé, code 0 : `origin/main` est désormais
`291f7ead24822cf8f9c0164aaf9dc3420d351647` (`[DEV]INT-129 — Livrer la release
traçable et le rollback contrôlé`), avance rapide depuis `0c1269a`, sans force.
Aucun autre fetch/merge/rebase n'a été effectué.

Le dépôt est **public** (`visibility: PUBLIC`) : le clone depuis le VPS ne
nécessite pas de jeton d'accès. La CI a été déclenchée pour ce commit (run
`39025284922`) : le job `Frontend — build` est concluant, le job
`Backend — tests` était encore en cours lors de la publication. La relecture
documentaire a vérifié le résultat final :

```sh
gh run view 39025284922 --repo libileh91/tervo --json status,conclusion,url
```

Résultat observé, code 0 : `status: completed`, `conclusion: success`,
[run CI](https://github.com/libileh91/tervo/actions/runs/39025284922).
La CI vérifie, elle ne déploie pas ; aucun job de déploiement n'existe
dans ce workflow.

## 4. Inventaire préalable — historique avant création de la stack

Avant toute mutation, l'opérateur exécute dans son **terminal root** un bloc
lecture seule qui confirme que le chemin de production est libre et identifie
la console Dockge que `release.py` gèlera. Aucun fichier ni conteneur modifié.

```sh
set -eu
id -u
hostname
ls -ld /opt/stacks/tervo 2>/dev/null || echo 'absent: /opt/stacks/tervo'
ls -ld /var/lib/tervo/state 2>/dev/null || echo 'absent: /var/lib/tervo/state'
docker compose -p tervo ps -a 2>/dev/null || true
docker volume  ls -q --filter 'label=com.docker.compose.project=tervo'
docker network ls -q --filter 'label=com.docker.compose.project=tervo'
docker ps -a --filter 'name=dockge-dockge-1' --format '{{.Names}} {{.Image}} {{.Status}}'
ss -ltn '( sport = :8000 or sport = :3000 or sport = :5001 )'
```

Résultat attendu : UID `0`, hostname `22565`, `/opt/stacks/tervo` et l'état
absents, aucun conteneur/volume/réseau du projet `tervo`, le conteneur
`dockge-dockge-1` présent sur l'image Dockge épinglée, et seuls les ports
loopback attendus (5001 pour Dockge) éventuellement visibles. Tout résultat
différent doit être analysé avant de créer le checkout.

**Résultats transmis :** le premier bloc, lancé comme `tervo` (UID 1000),
a échoué sur Docker et fermé le shell à cause de `set -e`. Ses messages
« absent » masquaient les erreurs de `ls` : ils ne prouvaient pas l'absence
des chemins. La préparation suivante a réussi ses gardes avant création.
Dans le terminal root, hostname `22565` ;
`docker compose -p tervo ps -a` ne liste aucun conteneur ; aucun volume ni réseau du projet
`tervo` ; `dockge-dockge-1` actif sur `louislam/dockge:1.5.0` (healthy, 47 h) ;
`ss` ne montre que `127.0.0.1:5001` (Dockge). Les ports `8000`/`3000` sont
libres à cet instant. Pas de code global explicitement fourni pour ce bloc.
Pour les nouveaux diagnostics, ne pas masquer les erreurs Compose ;
utiliser les commandes ciblées du parcours opérateur.

## 5. Préparation du checkout et de l'env privé

Le checkout `/opt/stacks/tervo` a été cloné depuis GitHub et verrouillé sur
`291f7ead24822cf8f9c0164aaf9dc3420d351647` (HEAD détaché, statut git propre).
`deploy/.env` est créé en mode `600` avec des secrets générés sur le VPS
(`openssl rand`), jamais collés ; `FRONTEND_ORIGIN=https://tervoapp.com` et
`VITE_API_BASE_URL=https://api.tervoapp.com/api/v1`. L'état de release est
`/var/lib/tervo/state` (mode `700`, hors checkout).

Résultat observé : `Dockge image: louislam/dockge:1.5.0@sha256:335c6368…`
(empreinte épinglée), `Environment permissions and Compose configuration
valid.`, `git status --porcelain` vide, `PREPARED: …`. Aucun conteneur
construit ni démarré à ce stade.

## 6. Premier essai de release — échec sur l'init PostgreSQL

La release a construit les deux images puis échoué sur
`docker compose up --wait postgres` : `tervo-postgres-1` est passé `unhealthy`.
Dockge a été laissé arrêté par `release.py`, puis relancé par l'opérateur.
Le helper s'est arrêté avant les migrations et avant tout record de succès ;
un dossier de tentative et des tags d'images de secours avaient pu être créés.
Pas de données métier préexistantes dans ce projet neuf ; cela ne constitue
pas une règle de redémarrage automatique de Dockge après tout échec.

Cause relevée dans les logs PostgreSQL :

```text
/docker-entrypoint-initdb.d/10-app.sql: Permission denied
PostgreSQL Database directory appears to contain a database; Skipping initialization
```

Le bloc de préparation appliquait `umask 077` pendant `git clone`, ce qui
restreint les permissions des nouveaux fichiers. Le refus de lecture de
`init-app.sql` est prouvé ; les modes exacts avant correction et l'UID du
processus n'ont pas été mesurés dans la sortie fournie. L'init a échoué avant
la création du rôle applicatif, puis l'entrypoint a repris en sautant
l'initialisation. `healthy` ne prouvait alors que la disponibilité PostgreSQL.

Correction demandée et suivie d'une release réussie : remettre les deux SQL
en `644`, recréer le projet neuf (`down -v`) et relancer. La sortie détaillée
du chmod/nettoyage n'a pas été fournie. **Ne pas rejouer cette suppression :
un compte admin existe désormais.** Pour un futur clone, sources non secrètes
sous `umask 022`, puis création des secrets sous `umask 077` et `.env` en `600`.

## 7. Release production réussie (loopback)

Après correction, `release.py deploy` a réussi : `PASS: release
291f7ead2482-ca71c575091e`, `PASS: backend readiness, frontend health and
login page`. Les migrations ont tourné avant démarrage HTTP ; `app-grants.sql`
a appliqué `GRANT`/`REVOKE`/`COMMIT`.

Contrôle observé : `tervo-postgres-1` (`5432/tcp`, aucun port hôte publié),
`tervo-backend-1` (`127.0.0.1:8000->8000/tcp`), `tervo-frontend-1`
(`80/tcp, 127.0.0.1:3000->3000/tcp`), tous `healthy` ; `ss` ne montre que
`127.0.0.1:8000` et `127.0.0.1:3000` ; Dockge relancé. Aucun port public
applicatif exposé : l'instance reste loopback jusqu'à la bascule DNS/Caddy.

Dockge était `Up (health: starting)` juste après sa reprise : son état
healthy final n'a pas été retranscrit dans ce retour.

## 8. Réception email et bootstrap administrateur

L'opérateur a confirmé les tests de réception pour `admin@tervoapp.com` et
`contact@tervoapp.com`, puis « admin créé — Tervo actif ». Le
[cours réseau/messagerie](../../../deploy/cours/03-reseau-caddy-dockge.md) distingue réception et envoi différé.

Commande interactive fournie pour le terminal root du VPS :

```sh
docker exec -it tervo-backend-1 python -m app.bootstrap_admin --confirm-db-name tervo_db
```

Attendu : saisies locales, mot de passe masqué (12–72 octets UTF-8), puis
`Administrator created.`, code 0. **Résultat communiqué : création confirmée,
sortie détaillée et code de retour non consignés.** Aucun identifiant privé
ni mot de passe n'est conservé dans cette note. Pas de seed ni d'envoi d'email
dans ce parcours. Le compte SQL `tervo_admin` n'est pas le compte applicatif.

À cet instant, « actif » ne prouvait pas encore le login public ni la
délivrance d'un certificat. La section suivante consigne la bascule ultérieure.

## 9. DNS direct et activation HTTPS — 19 octobre 2026

L'ancienne publication utilisait un tunnel Cloudflare **géré localement** sur
`mini-s1` : API vers `http://localhost:8000`, frontend vers
`http://localhost:3000`. Ajouter un réplica au même tunnel n'aurait pas isolé
le VPS. La bascule porte sur les enregistrements DNS web, pas sur les MX/TXT
de réception email. Aucun retrait du tunnel ou du connecteur n'est prouvé ici.

Depuis le poste agent, contrôle DNS autoritatif exécuté :

```sh
for name in tervoapp.com api.tervoapp.com; do
  for type in A AAAA CAA; do
    dig @elisa.ns.cloudflare.com +noall +answer "$name" "$type"
  done
done
```

Résultat : chaque `A` vaut `151.241.228.152` (TTL 300), aucune réponse
AAAA/CAA ; commandes code 0. L'ancienne réponse Cloudflare du domaine racine
était encore visible dans le cache du poste opérateur (TTL restant 24 s).

Le contrôle root fourni par l'opérateur confirme UID `0`, hôte `22565`,
bootstrap HTTP actif, application/admin/Dockge en loopback et frontend local
`HTTP 200`. Le profil candidat est celui du dépôt : deux reverse proxies,
admin `127.0.0.1:2019`, protocoles HTTPS `h1 h2`.

Bloc exécuté par l'opérateur, dans son terminal root :

```sh
(
  set -eu
  umask 077
  ACTIVE=/etc/caddy/Caddyfile
  CANDIDATE=/opt/stacks/tervo/deploy/caddy/production.Caddyfile.example
  BACKUP_DIR="$(mktemp -d /root/tervo-caddy-http.XXXXXX)"
  cp -p "$ACTIVE" "$BACKUP_DIR/Caddyfile"
  printf 'Sauvegarde bootstrap : %s/Caddyfile\n' "$BACKUP_DIR"
  /usr/local/bin/caddy validate --config "$CANDIDATE" --adapter caddyfile
  install -o root -g root -m 644 "$CANDIDATE" "$ACTIVE"
  if systemctl reload caddy; then
    printf 'Profil HTTPS chargé ; émission des certificats à vérifier.\n'
  else
    printf 'Échec du reload : restauration du bootstrap.\n' >&2
    cp -p "$BACKUP_DIR/Caddyfile" "$ACTIVE"
    systemctl reload caddy
    exit 1
  fi
)
```

| Commande | But et succès attendu | Résultat fourni |
|---|---|---|
| `mktemp`, `cp -p` | Conserver le bootstrap dans un dossier root privé ; code 0, `cp` silencieux | Chemin `/root/tervo-caddy-http.MUcPcg/Caddyfile` affiché |
| `caddy validate` | Vérifier avant remplacement ; code 0, `Valid configuration` | Message observé |
| `install`, `systemctl reload` | Charger le profil sans redémarrer Docker ; code 0, normalement silencieux | Message de branche succès observé ; code global non explicitement transmis |

Le profil ne contient plus `auto_https off` : le reload active ACME.
La copie de bootstrap permet un retour HTTP, **pas** un retour complet de
l'application publique. Elle ne sauvegarde pas les données ni l'état TLS.

Contrôles exécutés par l'opérateur :

```sh
systemctl is-active caddy
ss -ltn '( sport = :80 or sport = :443 or sport = :2019 )'
journalctl -u caddy --since '5 minutes ago' -n 60 --no-pager
```

Sortie transmise : `active`, TCP `*:80` / `*:443`, admin
`127.0.0.1:2019`. Journaux : `certificate obtained successfully` pour
`tervoapp.com` et `api.tervoapp.com`, émetteur Let's Encrypt, vers
16:35:33–34 UTC. Les logs hôte sont affichés en UTC+2.
Codes de ces trois commandes non explicitement transmis.

Le warning `Journal file /var/log/journal/system.journal is truncated,
ignoring file.` persiste : ne pas effacer les journaux pour le masquer.
Les avertissements h2/h3 sur le listener HTTP `:80` n'établissent pas une
écoute HTTP/3 ; le serveur HTTPS annonce bien `h1 h2`.

### Contrôle extérieur réellement exécuté par l'agent

```sh
for url in http://tervoapp.com/login \
  http://api.tervoapp.com/health/ready \
  https://tervoapp.com/login \
  https://api.tervoapp.com/health/ready; do
  printf '\n--- %s ---\n' "$url"
  curl --noproxy '*' --fail --silent --show-error \
    --connect-timeout 10 --max-time 20 \
    --dump-header - --output /dev/null \
    --write-out 'remote_ip=%{remote_ip} http_code=%{http_code} ssl_verify_result=%{ssl_verify_result}\n' \
    "$url"
  printf 'curl exit=%s\n' "$?"
done
```

Résultats observés à 16:37:38 UTC, chaque `curl` code 0 :

| URL | Réponse réelle |
|---|---|
| `http://tervoapp.com/login` | 308, `Location: https://tervoapp.com/login` |
| `http://api.tervoapp.com/health/ready` | 308, `Location: https://api.tervoapp.com/health/ready` |
| `https://tervoapp.com/login` | HTTP/2 200, `text/html`, `via: 1.1 Caddy` |
| `https://api.tervoapp.com/health/ready` | HTTP/2 200, `application/json`, `via: 1.1 Caddy` |

Toutes les connexions atteignent `151.241.228.152`. Les deux requêtes HTTPS
ont `ssl_verify_result=0`, sans `-k` : chaîne et hostname acceptés par curl.
Le corps readiness n'a pas été consigné par ces commandes.

**Limites :** ces GET seuls ne prouvent ni l'exécution du JavaScript, ni le login,
ni l'upload ; la confirmation opérateur est consignée ci-dessous.
Le renouvellement est géré automatiquement par Caddy, mais aucun renouvellement
effectif ni sauvegarde/restauration de son état TLS n'est encore prouvé.
Restent reboot/ports et exploitation/sauvegardes.

## 10. Recette navigateur — confirmation opérateur

Après la demande de vérification login, dashboard et upload/récupération photo,
l'opérateur confirme : « test de bout en bout avec succès », avec quelques
améliorations frontend qualifiées de mineures. Le critère fonctionnel INT-111
est coché sur cette déclaration, pas sur une nouvelle exécution par l'agent.
Aucune capture réseau, liste détaillée des étapes ou réponse HTTP authentifiée
n'a été transmise ; aucune revue indépendante de la politique CORS n'est déduite.

Les améliorations frontend ne sont pas détaillées : demander la liste avant
de créer des corrections ciblées ; ne pas les confondre avec les interfaces V2
déjà suivies dans TD-F007. Aucun correctif frontend ni nouvelle release effectué.
INT-111 reste ouverte pour les critères d'exploitation non encore validés.

## 11. Préparation de la destination hors VPS — mini-s1

Contrôles transmis par l'opérateur : hôte `mini-s1`, UID 0, 236 Go disponibles
sur `/` ; `/srv/backups`, `/srv/backups/tervo` et `/etc/tervo` initialement
absents. Un premier contrôle avait été exécuté par erreur sur `22565` :
il ne constituait pas un inventaire du mini-s1 et ne modifiait rien.

Installation native via apt : `restic 0.18.0`, Go `1.24.4`, linux/amd64.
Le premier essai d'initialisation a échoué sur une option contenant un
marqueur de masquage au lieu du nom réel de l'option ; le fichier privé
existait déjà en `600 root:root`. Il n'a pas été régénéré. La reprise utilise
les variables natives `RESTIC_REPOSITORY` et `RESTIC_PASSWORD_FILE`, avec
refus si plusieurs fichiers candidats existent ou si le dépôt est déjà créé.

Sortie opérateur après `restic init`, puis `restic snapshots` :

```text
created restic repository 4f50c482e6 at /srv/backups/tervo
repository 4f50c482 opened (version 2, compression level auto)
created new cache in /root/.cache/restic
```

Aucun snapshot listé ; codes numériques non explicitement transmis.
**Dépôt créé et ouvert, pas encore de sauvegarde réelle.**

### Accès de transfert — résultats opérateur

- Empreinte ED25519 d'hôte comparée par l'opérateur entre sa session VPS
  existante et la clé candidate obtenue sur mini-s1, puis entrée ajoutée dans
  `/root/.ssh/known_hosts`. Valeurs masquées dans la conversation.
- Clé dédiée `/root/.ssh/tervo-vps-backup` créée sur mini-s1 sans passphrase,
  privée `600 root:root` ; seule la clé publique ajoutée au compte VPS `tervo`.
  Refus initial `Permission denied (publickey)` : clé non reconnue dans
  `authorized_keys`, puis empreintes dédiées concordantes selon les sorties.
- Test SFTP réussi : `Remote working directory: /home/tervo`. La restriction
  initialement sur une ligne séparée n'était pas appliquée. Correction par
  raccordement des lignes, après copie
  `/home/tervo/.ssh/authorized_keys.before-sftp.Fe9gua`.
- Dernière sortie : ligne 2 commençant par
  `restrict,command="internal-sftp -R" ssh-ed25519`, deux clés reconnues,
  clé d'administration conservée. Le commentaire dédié apparaît deux fois,
  sans effet sur la clé ou ses options. Pas de nouveau test SFTP retranscrit
  après ce raccordement.

Cette clé doit forcer SFTP en lecture seule, sans shell ni forwarding ; elle
n'enferme pas la lecture dans un dossier et conserve les droits de lecture du
compte `tervo`. Aucun droit sudo ni accès SSH root ajouté. Garder le contrôle de
sa conservation/révocation avant planification.

Copie de secours du secret restic hors mini-s1 ensuite confirmée par l'opérateur,
avec autorisation explicite de la courte interruption pour la capture.
Capture cohérente, transfert de données réelles, chiffrement, restauration
isolée et planification restent à vérifier. Pas de capture ni de timer
exécutés au moment de cette confirmation.

### Inventaire de la base avant capture — lecture seule

L'opérateur a interrogé `tervo_db` depuis `tervo-postgres-1`, via psql avec
`ON_ERROR_STOP=1` et transaction `BEGIN READ ONLY` / `COMMIT`.
Les trois services Tervo sont affichés `Up 3 days (healthy)`.
Résultats transmis, sans données personnelles :

| Table / élément | Nombre de lignes |
|---|---|
| Comptes (`user`) | 1 |
| Clients | 1 |
| Sites | 1 |
| Équipements | 0 |
| Interventions | 1 |
| Photos | 0 |

La base n'est donc pas vide. Ces compteurs ne distinguent pas les données
réelles des données de test. La capture doit conserver cet état sans seed
ni nettoyage. Aucune photo n'est référencée en base à cet instant ; cela
ne prouve ni l'absence de fichiers dans le volume uploads ni l'échec d'un
ancien test suivi d'une suppression. Ce jeu ne suffira pas à démontrer une
restauration de photo référencée. Aucun dump ni transfert réalisé par ce contrôle.

L'opérateur précise ensuite que ces enregistrements proviennent de sa recette
frontend, et demande que l'agent génère le petit jeu complémentaire.

### Précontrôle des sources de capture — résultats opérateur

SHA confirmé `291f7ead24822cf8f9c0164aaf9dc3420d351647`, validation env réussie.
Backend actif, volume `tervo_uploads_data` monté sur `/app/uploads` ;
Dockge actif, données `/opt/dockge/data` montées sur `/app/data`.
Caddy actif, unité `/etc/systemd/system/caddy.service`.
Sources relevées : `/etc/caddy` en `750 root:caddy`, `/var/lib/caddy` en
`700 caddy:caddy`, unité et Compose Dockge en `644 root:root`, données Dockge
en `700 root:root`. Espace `/var/tmp` : 98 Go disponibles. Aucun arrêt effectué.

## 12. Jeu complémentaire de recette — exécuté sur le VPS

L'agent vérifie de nouveau son accès réel :

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 \
  -o ControlPath=none tervo@151.241.228.152 \
  'hostname; id; sudo -n true'
```

Observé : hôte `22565`, UID 1000 `tervo`, groupe sudo ; refus sudo non
interactif, code global 1. SSH fonctionne, mais ne permet pas de lancer Docker.
L'agent prend en charge la préparation et le transfert ; seul le lancement
privilégié doit passer par l'opérateur. Aucune règle sudo élargie.

Le [peuplement ponctuel](../../../deploy/scripts/populate-backup-recipe.py)
appelle les services métier existants, pas le seed de démonstration :
un client et un site marqués `TEST`, deux interventions attribuées à l'admin
actif existant, une image PNG synthétique par intervention et leurs miniatures.
Il vérifie les fichiers et affiche les IDs et SHA-256, jamais de secret.
Le nom réel de DB doit être confirmé ; il faut exactement un admin actif.
Les reprises réutilisent les objets marqués ; une collision non marquée est
refusée. Chaque création suit le commit normal de son service : un échec
tardif ne supprime pas les créations déjà réussies.

Validation réellement exécutée en SQLite isolé avec `uv run --project backend
--offline --frozen python` : base/uploads temporaires, un admin et un jeu initial.
Après deux appels, les comptes restent `1 user / 2 clients / 2 sites /
3 interventions / 2 photos`, quatre fichiers (originaux et miniatures) inchangés.
Existant et hash utilisateur préservés ; mauvaise confirmation DB et collision
refusées. Le premier contrôle local a échoué sur une erreur de comptage dans
le code de vérification, corrigée avant le run final concluant, code 0.
Les onze sources applicatives utilisées ont été comparées byte-à-byte :
identiques à la révision déployée `291f7ea`.
Cette validation locale ne prouve pas à elle seule une exécution PostgreSQL
ou une nouvelle recette HTTP/navigateur ; l'exécution VPS est consignée ensuite.

Fichier non secret copié par l'agent sur le VPS, sans modifier le checkout :
`/var/tmp/tervo-int111-fixture.WO21M3Pa/populate-backup-recipe.py`,
dossier `700 tervo:tervo`. SHA-256 :
`1eb496f13521b1138c39ee5b7c8cf99a48e80eb41c3ee0b854356d5d6cbeddb6`.
Copie réussie, suivie de l'exécution opérateur ci-dessous.

Lancement fourni pour le terminal root VPS, non exécuté par l'agent :

```sh
(
  set -eu
  test "$(hostname)" = 22565
  test "$(id -u)" = 0
  RECIPE=/var/tmp/tervo-int111-fixture.WO21M3Pa/populate-backup-recipe.py
  printf '1eb496f13521b1138c39ee5b7c8cf99a48e80eb41c3ee0b854356d5d6cbeddb6  %s\n' "$RECIPE" \
    | sha256sum --check -
  flock -n /run/lock/tervo-operations.lock \
    docker exec -i tervo-backend-1 python - --confirm-db tervo_db < "$RECIPE"
)
```

Attendu : checksum `OK`, IDs client/site/interventions/photos, deux empreintes
d'originaux puis `Fixture ready; originals and thumbnails verified.`, code 0.
`flock -n` refuse une opération concurrente au lieu d'attendre ; `-i` transmet
le programme sur stdin. Aucun build, changement d'admin ou arrêt des services.
Si le bloc échoue, conserver la sortie pour diagnostic avant toute reprise.
Copie du secret restic hors mini-s1 et capture restent des étapes distinctes,
non confirmées par ce peuplement.

### Résultat PostgreSQL/VPS transmis par l'opérateur

```text
/var/tmp/tervo-int111-fixture.WO21M3Pa/populate-backup-recipe.py: OK
Fixture client=2 site=2
intervention=2 photo=1 sha256=d1e4e8f58c6086d14895b00a43ccb728c77b07be59604fd8615885728cdee2ed
intervention=3 photo=2 sha256=d64936e3ac130903e7fe72fcf04ba81401330ad58863ec876a2fed4f0af505bd
Fixture ready; originals and thumbnails verified.
```

Le programme a atteint le résultat final et vérifié les originaux et miniatures.
Les empreintes des deux images sont identiques à celles de la recette locale.
Les IDs ci-dessus constituent des repères pour la future restauration ;
les totaux globaux de la base n'ont pas été recomptés après ce lancement.
Pas de nouvelle preuve de consultation HTTP/navigateur à partir de cette sortie.

L'opérateur a également collé le texte d'invite `tervo@22565:~$` devant la
parenthèse ouvrante : erreur de syntaxe Bash au début, puis parenthèse fermante
isolée à la fin. Les commandes intermédiaires ont néanmoins été exécutées et
le programme a réussi. Code numérique du programme non retranscrit ; le bloc
shell complet n'a pas été exécuté proprement. **Ne pas le relancer pour corriger
ces seules erreurs d'emballage.** À l'avenir, copier uniquement le contenu du
bloc de commandes, jamais les invites ni les délimiteurs Markdown.

## 13. Capture locale réussie — contrôle de reprise interrompu

Après confirmation opérateur de la copie du secret restic hors mini-s1 et
de la fenêtre de maintenance, lancement de l'outil INT-128 existant :
`snapshot.py capture`, Compose/env explicites du checkout `/opt/stacks/tervo`,
projet `tervo`, verrou `/run/lock/tervo-operations.lock`, sortie privée hors Git.
L'outil utilise les chemins Caddy/Dockge déjà relevés ; aucun nouveau script
de capture ni nouvelle release.

Sortie opérateur :

```text
Capture privée dans : /var/tmp/tervo-backup.haPfNpxv
Bundle checksums valid.
curl: (56) Recv failure: Connection reset by peer
Backend prêt : HTTP 000
```

**La capture et sa vérification ont réussi.** L'archive est
`/var/tmp/tervo-backup.haPfNpxv/tervo.tar`.
L'échec intervient ensuite dans le GET de disponibilité ; le sous-shell
avec `set -e` s'arrête avant les contrôles suivants et l'ouverture de lecture
pour le compte de transfert. Ne pas refaire la capture pour cette erreur.
`HTTP 000` n'est pas une réponse HTTP du serveur : curl n'en a pas reçu.
Le reset est compatible avec une API encore en démarrage, sans preuve de sa
cause exacte faute de logs privilégiés à cet instant.

La commande utilisait `--retry-connrefused`, qui ne couvre pas ce reset.
Pour ce GET de readiness uniquement, la reprise ajoute `--retry-all-errors`
avec nombre de tentatives et durée bornés. Ne pas généraliser la répétition
automatique aux écritures POST ni à la commande de capture.

Vérifications réellement exécutées par l'agent :

- SSH `tervo@151.241.228.152` désormais refusé (`Permission denied (publickey)`,
  code 255) sur le poste d'exécution courant ; aucune conclusion sur la cause.
- Frontend `https://tervoapp.com/login` : 200, IP `151.241.228.152`,
  vérification TLS 0 et code curl 0.
- Premier GET API extérieur : refus de connexion, code curl 7. Lecture DNS :
  deux A vers `151.241.228.152`, aucune réponse AAAA.
- Contrôle API fixant explicitement cette origine avec `--resolve` :
  200 avec TLS vérifié, puis nouveau GET normal sans `--resolve` :
  `https://api.tervoapp.com/health/ready`, 200, même IP, TLS 0, code curl 0.

Frontend et API sont donc revenus disponibles lors de ces contrôles.
Le contrôle Docker/Dockge privilégié et la préparation de lecture du fichier
restent à finaliser dans le terminal root opérateur, sans nouvelle capture :

```sh
(
  set -eu
  test "$(hostname)" = 22565
  test "$(id -u)" = 0
  BACKUP_DIR=/var/tmp/tervo-backup.haPfNpxv
  BUNDLE="$BACKUP_DIR/tervo.tar"
  test -s "$BUNDLE"
  curl --noproxy '*' --fail --silent --show-error \
    --retry 10 --retry-all-errors --retry-delay 2 --retry-max-time 45 \
    --max-time 5 --output /dev/null \
    --write-out 'Backend prêt : HTTP %{http_code}\n' \
    http://127.0.0.1:8000/health/ready
  systemctl is-active caddy.service
  test "$(docker inspect --format '{{.State.Running}}' dockge-dockge-1)" = true
  docker ps --filter 'label=com.docker.compose.project=tervo' \
    --format '{{.Names}}  {{.Status}}'
  chown root:tervo "$BACKUP_DIR" "$BUNDLE"
  chmod 750 "$BACKUP_DIR"
  chmod 640 "$BUNDLE"
  printf '\nBUNDLE=%s\n' "$BUNDLE"
  stat -c '%a %U:%G %s octets %n' "$BUNDLE"
  sha256sum "$BUNDLE"
)
```

Commande de reprise exécutée par l'opérateur : backend HTTP 200, Caddy actif,
test Dockge franchi, trois conteneurs Tervo `healthy`. Archive confirmée :

```text
BUNDLE=/var/tmp/tervo-backup.haPfNpxv/tervo.tar
640 root:tervo 286720 octets /var/tmp/tervo-backup.haPfNpxv/tervo.tar
f833b896eab77eb17e235d9b7b83b7516bd911bca7be6002092c9465ee144d7b  /var/tmp/tervo-backup.haPfNpxv/tervo.tar
```

Sortie sans erreur ; code numérique global non retranscrit. Aucune nouvelle
capture. Le dossier est configuré `750 root:tervo` par le bloc de reprise.
Le groupe du compte `tervo` obtient la lecture, pas l'écriture ; les autres
utilisateurs n'y ont pas accès. L'archive contient encore des secrets en clair.
À cet instant, transfert vers mini-s1, snapshot restic et restauration
n'étaient pas encore prouvés ; la suite est consignée ci-dessous.

## 14. Téléchargement et restic — snapshot 03aca082 enregistré

Sur **mini-s1 root**, pas sur le VPS. Le chemin source et le checksum sont
ceux du retour opérateur précédent ; aucun nouveau dump ni arrêt de service.
Le fichier privé restic existant est réutilisé, aucun `init` ou nouveau secret.
Bloc exécuté par l'opérateur ; ne pas le relancer pour poursuivre la restauration.

```sh
(
  set -eu
  umask 077
  test "$(hostname)" = mini-s1
  test "$(id -u)" = 0
  test -f /srv/backups/tervo/config
  test -s /root/.ssh/tervo-vps-backup
  set -- /etc/tervo/restic-*
  test "$#" -eq 1
  test -f "$1"
  test -s "$1"
  test "$(stat -c '%a:%u' "$1")" = '600:0'
  unset RESTIC_PASSWORD RESTIC_PASSWORD_COMMAND RESTIC_REPOSITORY_FILE
  export RESTIC_REPOSITORY=/srv/backups/tervo
  export RESTIC_PASSWORD_FILE="$1"
  RECEIVE_DIR="$(mktemp -d /var/tmp/tervo-receive.XXXXXXXX)"
  printf 'Réception privée : %s\n' "$RECEIVE_DIR"
  sftp -b - -i /root/.ssh/tervo-vps-backup \
    -o IdentitiesOnly=yes \
    -o UserKnownHostsFile=/root/.ssh/known_hosts \
    -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=10 \
    tervo@151.241.228.152 <<SFTP
get /var/tmp/tervo-backup.haPfNpxv/tervo.tar "$RECEIVE_DIR/tervo.tar"
bye
SFTP
  chmod 600 "$RECEIVE_DIR/tervo.tar"
  printf 'f833b896eab77eb17e235d9b7b83b7516bd911bca7be6002092c9465ee144d7b  %s\n' \
    "$RECEIVE_DIR/tervo.tar" | sha256sum --check -
  restic backup --stdin --stdin-filename tervo.tar \
    --host tervo-vps --tag tervo --tag int111 < "$RECEIVE_DIR/tervo.tar"
  restic check --read-data
  restic snapshots --host tervo-vps --tag int111
  printf '\nARCHIVE_LOCALE=%s\n' "$RECEIVE_DIR/tervo.tar"
)
```

Le délimiteur `<<SFTP` est volontairement non cité pour substituer le chemin
local de réception ; aucune valeur secrète n'est interpolée dans ce bloc SFTP.
Attendu : téléchargement puis checksum `OK`, snapshot enregistré avec un ID,
contrôle restic sans erreur et liste du snapshot, chaque commande code 0.
Une erreur arrête le bloc ; ne pas compter une copie comme acquise sur la
seule ouverture SFTP. Les copies temporaires en clair restent privées et ne
sont pas supprimées avant vérification de restauration et accord de nettoyage.
Un `restic check` réussi ne prouvera pas à lui seul la restauration applicative.

### Résultats réellement transmis

Réception privée `/var/tmp/tervo-receive.xiND9EiH/tervo.tar`, checksum `OK`
contre l'empreinte de l'archive VPS. Dépôt `4f50c482`, format 2.
Extraits observés :

```text
processed 1 files, 280.000 KiB in 0:00
snapshot 03aca082 saved
read all data
[0:00] 100.00%  2 / 2 packs
no errors were found
```

Liste : un snapshot `03aca082`, heure affichée `2026-10-22 19:51:57`
(fuseau non consigné), hôte `tervo-vps`, tags `tervo,int111`, chemin `/tervo.tar`,
taille logique 280 KiB ; ajout stocké annoncé 48,762 KiB.
Fin du bloc atteinte sans erreur ; codes numériques non explicitement transmis.
**Première copie chiffrée hors VPS acquise, intégrité du dépôt relue.**
Cette preuve concerne le petit jeu de recette et les paramètres réels capturés,
pas un volume métier représentatif ni une restauration PostgreSQL déjà exécutée.
Copies temporaires en clair conservées aux deux emplacements privés connus.

## 15. Restauration de l'archive depuis restic

Sur mini-s1 root : lire précisément le snapshot `03aca082`, pas un `latest`
qui pourrait changer. L'archive est déchiffrée dans un nouveau dossier privé
hors Git, comparée à l'empreinte VPS, puis extraite sans appliquer ses propriétaires
ou permissions d'origine. Les configurations restent dans ce dossier, jamais
sur `/etc/caddy` ou `/opt/dockge`. Aucun conteneur de restauration encore démarré.

```sh
(
  set -eu
  umask 077
  test "$(hostname)" = mini-s1
  test "$(id -u)" = 0
  set -- /etc/tervo/restic-*
  test "$#" -eq 1
  test -f "$1"
  test -s "$1"
  test "$(stat -c '%a:%u' "$1")" = '600:0'
  unset RESTIC_PASSWORD RESTIC_PASSWORD_COMMAND RESTIC_REPOSITORY_FILE
  export RESTIC_REPOSITORY=/srv/backups/tervo
  export RESTIC_PASSWORD_FILE="$1"
  RESTORE_DIR="$(mktemp -d /var/tmp/tervo-restore.XXXXXXXX)"
  printf 'RESTORE_DIR=%s\n' "$RESTORE_DIR"
  restic dump 03aca082 /tervo.tar > "$RESTORE_DIR/tervo.tar"
  printf 'f833b896eab77eb17e235d9b7b83b7516bd911bca7be6002092c9465ee144d7b  %s\n' \
    "$RESTORE_DIR/tervo.tar" | sha256sum --check -
  tar -tf "$RESTORE_DIR/tervo.tar"
  tar -xf "$RESTORE_DIR/tervo.tar" -C "$RESTORE_DIR" \
    --no-same-owner --no-same-permissions
  (cd "$RESTORE_DIR" && sha256sum --check SHA256SUMS)
  printf '\n--- Docker disponible pour la suite ---\n'
  docker version --format '{{.Server.Version}}'
  docker image ls --digests \
    --format '{{.Repository}}:{{.Tag}} {{.Digest}}' postgres
)
```

Attendu : archive restaurée `OK`, dix noms listés (neuf composants et manifeste),
neuf checksums `OK`, version serveur Docker. La liste d'images PostgreSQL peut
être vide, code 0 : cela signale un téléchargement à prévoir, pas un échec du
dump restauré. Une erreur Docker n'annule pas une extraction déjà faite.
Résultats opérateur reçus : dossier `/var/tmp/tervo-restore.F7RXfxl8`,
empreinte de l'archive `OK`, dix fichiers listés, neuf checksums `OK`.
Serveur Docker `29.8.0` ; images présentes `postgres:18` et `postgres:17.4`.
La récupération fidèle depuis le dépôt chiffré est donc prouvée.
La preuve de restauration des tables/liens et des photos viendra ensuite dans
une cible PostgreSQL neuve et isolée, sans remplacer les bases existantes.

## 16. Restauration PostgreSQL sur mini-s1

Commande fournie puis tentée par l'opérateur, **bloquée avant pg_restore**
(diagnostic section 17). On reprend l'image 17.11 épinglée
dans le Compose source, pas un serveur 18 ni une ancienne mineure 17.4.
Téléchargement explicite unique ; en cas d'échec, arrêter plutôt que multiplier
les sources ou contourner avec une autre version.

Un nouveau conteneur et un nouveau volume UUID, réseau `none`, aucun port
publié. Le compte SQL `restore_admin` et la base `tervo_restore` sont propres
à cette cible ; les secrets de production du `.env` extrait ne sont pas chargés.
Le fichier de credentials de test reste privé sous le dossier de restauration.
Ni image/backend HTTP ni migration/seed ne sont lancés.

```sh
(
  set -eu
  umask 077
  test "$(hostname)" = mini-s1
  test "$(id -u)" = 0
  RESTORE_DIR=/var/tmp/tervo-restore.F7RXfxl8
  test -s "$RESTORE_DIR/database.dump"
  test ! -e "$RESTORE_DIR/restore-container.txt"
  test ! -e "$RESTORE_DIR/restore-postgres.env"
  IMAGE=postgres:17.11@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
  docker pull "$IMAGE"
  PG_CONTAINER="tervo-restore-$(cat /proc/sys/kernel/random/uuid)"
  PG_VOLUME="$PG_CONTAINER-data"
  printf '%s\n' "$PG_CONTAINER" > "$RESTORE_DIR/restore-container.txt"
  printf '%s\n' "$PG_VOLUME" > "$RESTORE_DIR/restore-volume.txt"
  printf 'POSTGRES_DB=tervo_restore\nPOSTGRES_USER=restore_admin\nPOSTGRES_PASSWORD=%s\n' \
    "$(openssl rand -hex 24)" > "$RESTORE_DIR/restore-postgres.env"
  printf 'Conteneur : %s\nVolume : %s\n' "$PG_CONTAINER" "$PG_VOLUME"
  docker volume create "$PG_VOLUME"
  docker run -d --name "$PG_CONTAINER" --network none \
    --env-file "$RESTORE_DIR/restore-postgres.env" \
    --mount "type=volume,src=$PG_VOLUME,dst=/var/lib/postgresql/data" \
    "$IMAGE"
  docker exec -i "$PG_CONTAINER" sh -c '
    for attempt in $(seq 1 60); do
      if [ "$(cat /proc/1/comm)" = postgres ] &&
         pg_isready -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
        exec pg_restore --exit-on-error --no-owner --no-acl \
          -U "$POSTGRES_USER" -d "$POSTGRES_DB"
      fi
      sleep 1
    done
    echo "PostgreSQL de restauration non pret apres attente bornee." >&2
    exit 1
  ' < "$RESTORE_DIR/database.dump"
  printf '\n--- Données restaurées ---\n'
  docker exec -i "$PG_CONTAINER" psql -X -v ON_ERROR_STOP=1 \
    -U restore_admin -d tervo_restore <<'SQL'
BEGIN READ ONLY;
SELECT current_database() AS base;
SELECT 'comptes' AS element, count(*) AS nombre FROM public."user"
UNION ALL SELECT 'clients', count(*) FROM public.client
UNION ALL SELECT 'sites', count(*) FROM public.site
UNION ALL SELECT 'equipements', count(*) FROM public.equipment
UNION ALL SELECT 'interventions', count(*) FROM public.intervention
UNION ALL SELECT 'photos', count(*) FROM public.photo;
SELECT c.id AS client, s.id AS site, i.id AS intervention, p.id AS photo
FROM public.client c JOIN public.site s ON s.client_id=c.id
JOIN public.intervention i ON i.site_id=s.id
JOIN public.photo p ON p.intervention_id=i.id
WHERE p.id IN (1, 2) ORDER BY p.id;
COMMIT;
SQL
  printf '\n--- Isolation ---\n'
  docker inspect --format \
    '{{.Name}} network={{.HostConfig.NetworkMode}} ports={{json .HostConfig.PortBindings}}' \
    "$PG_CONTAINER"
)
```

`pg_restore` est normalement silencieux, code 0 attendu. L'attente bornée
vérifie le vrai processus PostgreSQL PID 1 : ne pas confondre le serveur
temporaire d'initialisation avec celui prêt à recevoir la restauration.
Le dump est transmis sur stdin, jamais affiché.

Attendu d'après le jeu préparé : base `tervo_restore`, compte 1, clients 2,
sites 2, équipements 0, interventions 3, photos 2 ; liens
`client 2 → site 2 → intervention 2 → photo 1` et
`client 2 → site 2 → intervention 3 → photo 2`.
Inspection : réseau `none`, ports publiés vides (`{}` ou `null`).
Une différence doit être examinée, pas corrigée en supprimant des données.
En cas d'échec, ne pas relancer tout le bloc : le nouveau conteneur/volume
peuvent déjà exister, leurs noms sont conservés dans les deux fichiers privés.
Ne supprimer aucune ressource existante. Vérification des fichiers photos
restaurés encore à faire après cette étape.

## 17. Blocage de l'image PostgreSQL locale — aucune restauration SQL exécutée

Sortie opérateur : image 17.11 au digest attendu annoncée à jour ; création de
`tervo-restore-57c3a02a-7fe7-4ce6-9b39-0be182306569` et de son volume
`tervo-restore-57c3a02a-7fe7-4ce6-9b39-0be182306569-data`, puis :

```text
OCI runtime exec failed: exec failed: unable to start container process: procReady not received
```

L'exécution `docker exec` a échoué avant le shell d'attente et `pg_restore`.
Ne pas réimporter le dump ni recréer une cible en relançant le bloc complet.

### Diagnostic directement exécuté par l'agent sur mini-s1

Le terminal agent est sur `mini-s1`, compte `lob`, membre du groupe Docker.
L'accès Docker local est donc disponible sans sudo, contrairement à l'accès
SSH distant du compte `tervo` sur le VPS. Cet accès permet le diagnostic ciblé
et la suite de la recette locale, sans changement de groupes ou de droits sudo.

```sh
docker inspect --format \
  '{{.Name}} status={{.State.Status}} running={{.State.Running}} exit={{.State.ExitCode}} error={{json .State.Error}}' \
  tervo-restore-57c3a02a-7fe7-4ce6-9b39-0be182306569
docker logs --tail 80 tervo-restore-57c3a02a-7fe7-4ce6-9b39-0be182306569
```

Observé : conteneur `exited`, `running=false`, code de sortie 1.
Journal :

```text
error: exec: "/usr/local/bin/docker-entrypoint.sh": stat /usr/local/bin/docker-entrypoint.sh: permission denied
```

La configuration du conteneur est root par défaut, profil `docker-default`,
sans option de sécurité ajoutée. Les métadonnées des fichiers ont été contrôlées
dans un conteneur temporaire en lecture seule, sans réseau et sans montage
de données existantes :

```sh
docker run --rm --network none --read-only --entrypoint /usr/bin/stat \
  postgres:17.11@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3 \
  -c '%a %u:%g %n' / /usr /usr/local /usr/local/bin \
  /usr/local/bin/docker-entrypoint.sh /usr/lib/postgresql \
  /usr/lib/postgresql/17/bin/postgres /tmp
```

Résultat, code 0 : `/` en `755 0:0` ; tous les autres chemins demandés en
`770 1000:1000`. Ces permissions de la copie locale empêchent l'utilisateur
non-root PostgreSQL de traverser `/usr` et d'exécuter l'entrypoint.
Le dump n'est pas impliqué dans cet échec. Origine et étendue de l'altération
des métadonnées non établies ; ne pas les attribuer sans preuve au bloc courant.

`docker ps -a --filter ancestor=sha256:327daa8fae7178d61f93142f146b098467b345e10997b9eb79f63bd58e5c8f3c`
ne liste que la cible de recette échouée. Son volume monté est bien le nouveau
volume UUID ci-dessus ; aucun volume de base existante n'est utilisé.

**Arrêt avant correction destructive.** Pas de `chmod -R` du stockage Docker,
pas de désactivation AppArmor/seccomp, pas de changement de version majeure
pour masquer le problème. Retrait de cette cible/volume jetables et de sa
référence d'image locale, puis réacquisition officielle proposés à l'opérateur :
accord explicite requis avant suppression. Une réacquisition peut conserver
des couches partagées ; si l'anomalie persiste, arrêter et traiter le stockage
Docker plutôt que multiplier les images de contournement.
Snapshot restic `03aca082`, archives privées et services existants conservés.

## 18. Nettoyage autorisé et réacquisition — anomalie de base persistante

Accord opérateur reçu pour supprimer uniquement la cible de recette échouée,
son volume neuf et la référence locale de l'image 17.11, puis la réacquérir.
Avant suppression, l'agent a vérifié : cible arrêtée, image attendue, unique
conteneur référençant cette image et ce volume, montage conforme.

Commandes de retrait/réacquisition exécutées sur mini-s1 après ces gardes :

```sh
docker rm tervo-restore-57c3a02a-7fe7-4ce6-9b39-0be182306569
docker volume rm tervo-restore-57c3a02a-7fe7-4ce6-9b39-0be182306569-data
docker image rm postgres:17.11@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
docker pull postgres:17.11@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
```

Résultat : ressources nommées supprimées, digest réacquis conforme, code 0.
Docker a conservé une couche déjà présente (`ecc510c1e359: Already exists`).
Les images 17.4/18 n'ont pas été ciblées ; aucun prune, redémarrage ou changement
de sécurité des services existants. Aucun fichier de sauvegarde supprimé.

Contrôle en conteneur temporaire lecture seule, sans réseau, même commande
`stat` que précédemment : `/usr`, `/usr/local/bin`, l'entrypoint et les binaires
PG sont revenus en `755 0:0`, **mais `/tmp` reste en `770 1000:1000`**.
Un contrôle complémentaire de métadonnées, sans lancement de PostgreSQL, donne :

| Chemin | Mode | UID:GID |
|---|---|---|
| `/usr/bin` | 755 | 0:0 |
| `/usr/bin/env` | 770 | 1000:1000 |
| `/usr/bin/bash` | 770 | 1000:1000 |
| `/etc` | 755 | 0:0 |
| `/etc/passwd` | 644 | 0:0 |
| `/var` | 755 | 0:0 |
| `/var/tmp` | 770 | 1000:1000 |
| `/var/run` | 777 | 1000:1000 |
| `/lib/x86_64-linux-gnu/libc.so.6` | 770 | 1000:1000 |

**Arrêt des essais sur ce cache local**, conformément au périmètre annoncé.
Aucun deuxième démarrage PG ni tentative de restauration SQL ; pas de réparation
globale des permissions. La restauration des données reste non prouvée.
Les fichiers de repérage dans `/var/tmp/tervo-restore.F7RXfxl8` désignent
désormais une cible supprimée : ne pas relancer le bloc de la section 16.

Pour réduire le chemin critique demandé par l'opérateur, déplacement de la
recette SQL/photos vers une cible isolée sur le VPS proposé, pas encore effectué.
La chaîne de preuve reste possible sans nouveau transfert : l'archive récupérée
de restic et celle conservée sur le VPS ont le même SHA-256
`f833b896eab77eb17e235d9b7b83b7516bd911bca7be6002092c9465ee144d7b`.
Toute cible VPS devrait garder réseau `none`, aucun port et volume UUID propre,
avec ressources bornées ; aucune base existante ne doit être remplacée.
Les opérations root VPS restent via l'opérateur tant que l'accès agent n'est
pas explicitement rétabli et qualifié.

## 19. Recette isolée sur le VPS

Déplacement validé, puis bloc ci-dessous **exécuté par l'opérateur**
dans son terminal root sur `22565`. Il vérifie à nouveau l'empreinte de
l'archive VPS, identique à celle récupérée de restic, puis extrait les mêmes
octets dans un nouveau répertoire privé. Ne pas relancer le bloc pour poursuivre.

La production continue de fonctionner. Cible de recette : nouveau conteneur
et volume UUID, réseau `none`, aucun port publié, mémoire 128 MiB sans swap,
CPU 0,5 et limite de processus. Arrêt préalable si moins de 256 MiB de RAM
disponible. L'image est utilisée sans téléchargement et vérifiée en lecture
comme utilisateur PostgreSQL non-root avant création de la cible.
Un verrou commun exclut les opérations de release/capture concurrentes.

```sh
(
  set -eu
  umask 077
  test "$(hostname)" = 22565
  test "$(id -u)" = 0
  exec 9>/run/lock/tervo-operations.lock
  flock -n 9
  awk '/^MemAvailable:/ {printf "RAM disponible : %.0f MiB\n", $2/1024; exit($2 < 262144)}' /proc/meminfo
  BUNDLE=/var/tmp/tervo-backup.haPfNpxv/tervo.tar
  printf 'f833b896eab77eb17e235d9b7b83b7516bd911bca7be6002092c9465ee144d7b  %s\n' \
    "$BUNDLE" | sha256sum --check -
  IMAGE=postgres:17.11@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
  docker run --rm --pull=never --network none --read-only \
    --user postgres --entrypoint /bin/sh "$IMAGE" -c \
    'set -e; test -r /usr/local/bin/docker-entrypoint.sh; test -x /usr/bin/env; test -x /usr/bin/bash; postgres --version'
  RESTORE_DIR="$(mktemp -d /var/tmp/tervo-restore-vps.XXXXXXXX)"
  printf 'RESTORE_DIR=%s\n' "$RESTORE_DIR"
  tar -xf "$BUNDLE" -C "$RESTORE_DIR" --no-same-owner --no-same-permissions
  (cd "$RESTORE_DIR" && sha256sum --check SHA256SUMS)
  PG_CONTAINER="tervo-restore-vps-$(cat /proc/sys/kernel/random/uuid)"
  PG_VOLUME="${PG_CONTAINER}-data"
  printf '%s\n' "$PG_CONTAINER" > "$RESTORE_DIR/restore-container.txt"
  printf '%s\n' "$PG_VOLUME" > "$RESTORE_DIR/restore-volume.txt"
  printf 'POSTGRES_DB=tervo_restore\nPOSTGRES_USER=restore_admin\nPOSTGRES_PASSWORD=%s\n' \
    "$(openssl rand -hex 24)" > "$RESTORE_DIR/restore-postgres.env"
  printf 'Conteneur : %s\nVolume : %s\n' "$PG_CONTAINER" "$PG_VOLUME"
  docker volume create "$PG_VOLUME" >/dev/null
  docker run -d --pull=never --name "$PG_CONTAINER" --network none \
    --memory 128m --memory-swap 128m --cpus 0.5 --pids-limit 128 \
    --env-file "$RESTORE_DIR/restore-postgres.env" \
    --mount "type=volume,src=$PG_VOLUME,dst=/var/lib/postgresql/data" \
    "$IMAGE" postgres -c shared_buffers=16MB -c max_connections=10 \
    -c maintenance_work_mem=16MB >/dev/null
  trap 'docker stop "$PG_CONTAINER" >/dev/null' EXIT
  docker exec -i "$PG_CONTAINER" sh -c '
    for attempt in $(seq 1 60); do
      if [ "$(cat /proc/1/comm)" = postgres ] &&
         pg_isready -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
        exec pg_restore --exit-on-error --no-owner --no-acl \
          -U "$POSTGRES_USER" -d "$POSTGRES_DB"
      fi
      sleep 1
    done
    echo "PostgreSQL de restauration non pret apres attente bornee." >&2
    exit 1
  ' < "$RESTORE_DIR/database.dump"
  docker exec -i "$PG_CONTAINER" psql -X -v ON_ERROR_STOP=1 \
    -U restore_admin -d tervo_restore <<'SQL'
BEGIN READ ONLY;
SELECT current_database() AS base;
SELECT 'comptes' AS element, count(*) AS nombre FROM public."user"
UNION ALL SELECT 'clients', count(*) FROM public.client
UNION ALL SELECT 'sites', count(*) FROM public.site
UNION ALL SELECT 'equipements', count(*) FROM public.equipment
UNION ALL SELECT 'interventions', count(*) FROM public.intervention
UNION ALL SELECT 'photos', count(*) FROM public.photo;
SELECT c.id AS client, s.id AS site, i.id AS intervention, p.id AS photo
FROM public.client c JOIN public.site s ON s.client_id=c.id
JOIN public.intervention i ON i.site_id=s.id
JOIN public.photo p ON p.intervention_id=i.id
WHERE p.id IN (1, 2) ORDER BY p.id;
COMMIT;
SQL
  mkdir "$RESTORE_DIR/files"
  tar -xf "$RESTORE_DIR/uploads.tar" -C "$RESTORE_DIR/files" \
    --no-same-owner --no-same-permissions
  for ID in 1 2; do
    ROW="$(docker exec "$PG_CONTAINER" psql -X -At -F '|' \
      -U restore_admin -d tervo_restore \
      -c "SELECT file_path, thumbnail_path FROM public.photo WHERE id=$ID")"
    ORIGINAL="${ROW%%|*}"
    THUMB="${ROW#*|}"
    test -n "$ORIGINAL"
    test -n "$THUMB"
    test "$ROW" != "$THUMB"
    case "$ID" in
      1) HASH=d1e4e8f58c6086d14895b00a43ccb728c77b07be59604fd8615885728cdee2ed ;;
      2) HASH=d64936e3ac130903e7fe72fcf04ba81401330ad58863ec876a2fed4f0af505bd ;;
    esac
    printf '%s  %s\n' "$HASH" "$RESTORE_DIR/files/uploads/photos/${ORIGINAL##*/}" \
      | sha256sum --check -
    test -s "$RESTORE_DIR/files/uploads/photos/${THUMB##*/}"
    printf 'Photo %s : miniature présente\n' "$ID"
  done
  docker inspect --format \
    '{{.Name}} network={{.HostConfig.NetworkMode}} ports={{json .HostConfig.PortBindings}} memory={{.HostConfig.Memory}}' \
    "$PG_CONTAINER"
  docker stop "$PG_CONTAINER" >/dev/null
  trap - EXIT
  printf '\nRecette SQL et photos terminée, cible arrêtée.\nRESTORE_DIR=%s\n' "$RESTORE_DIR"
)
```

### Résultats opérateur reçus

RAM disponible affichée : 4 516 MiB. Archive et neuf composants `OK`.
Exécution non-root : `postgres (PostgreSQL) 17.11 (Debian 17.11-1.pgdg13+2)`.
Dossier `/var/tmp/tervo-restore-vps.B6flfaiz`, conteneur
`tervo-restore-vps-8fc7aaf9-18f7-48b7-8cb9-f4450b4bfec6`, volume de même
nom suivi de `-data`. Base `tervo_restore`.

| Élément restauré | Nombre constaté |
|---|---|
| Comptes | 1 |
| Clients | 2 |
| Sites | 2 |
| Équipements | 0 |
| Interventions | 3 |
| Photos | 2 |

Relations constatées : client 2 → site 2 → intervention 2 → photo 1 ;
client 2 → site 2 → intervention 3 → photo 2.
Originaux `41ad4c83cca7443e8235076248bd329c.png` et
`f510225ee6ba444fb5c041b0a63fb039.png` : deux checksums `OK` contre les
empreintes source de la section 12. Deux miniatures présentes et non vides.
Inspection `network=none ports={} memory=134217728`.
Message final reçu : `Recette SQL et photos terminée, cible arrêtée.`
Pas de code numérique global retranscrit, fin du bloc atteinte sans erreur.

**Récupération des données, relations et photos de ce snapshot validée.**
La chaîne de preuve combine récupération réelle depuis restic sur mini-s1,
égalité SHA-256 avec l'archive VPS, puis restauration de ces mêmes octets.
Ce n'est pas une réplication de l'état courant ni une mesure sur gros volume.
Contrôles extérieurs post-recette exécutés par l'agent : `/login` frontend et
`/health/ready` API en HTTPS, HTTP 200, IP `151.241.228.152`, vérification TLS 0
et code curl 0 pour les deux.
Deux téléchargements HTTPS des originaux synthétiques par l'agent ont aussi
réussi, avec vérification SHA-256 contre les mêmes empreintes source.
Ils confirment l'accès aux fichiers sur l'instance publique, pas un clone HTTP
restauré. Aucun token ni mot de passe n'a été utilisé pour ces GET statiques.

Le trap tente seulement l'arrêt de cette cible lors d'une erreur ordinaire,
pas une récupération universelle après SIGKILL/panne. Aucune suppression
automatique : volume et fichiers privés restent disponibles pour diagnostic
et nettoyage ultérieurement autorisé. Le test ne remplace pas la reconstruction
du rôle applicatif, un login sur clone HTTP ou l'activation de Caddy/Dockge à
partir de leurs fichiers restaurés ; ne pas surévaluer cette preuve.

### Proposition initiale d'automatisation — non retenue pour la démo

L'outillage INT-128 existe : `pull-backup.sh`, service et timer mini-s1.
Le timer livré vise 03:00 heure locale, décalage aléatoire 0–5 minutes,
`Persistent=false` pour éviter un rattrapage avec coupure en journée.
Proposition : rendre l'horaire explicitement 03:00 UTC, garder ce non-rattrapage
et exécuter une recette immédiate avant activation.

Le pull existant demande une capture via SSH, alors que la clé actuelle force
uniquement SFTP lecture seule. Ne pas activer le timer tel quel.
Raccordement proposé, **pas encore autorisé ni installé** : réutiliser la clé
dédiée en lui imposant une commande de capture fixe, wrapper/config root-owned
et droit sudo non interactif limité à cette commande sans arguments, jamais
`NOPASSWD: ALL`, shell libre ou accès SSH root. Le wrapper doit contrôler la
reprise sans écrire de texte sur le flux binaire de l'archive.
Ce changement de droits et les brèves coupures régulières nécessitent l'accord
opérateur. Aucune purge de rétention automatique proposée à ce stade.

## 20. Périmètre de démo et sauvegardes manuelles — arbitrage validé

Le mini-s1 ne sera pas allumé en permanence. L'opérateur valide donc la
livraison publique de démonstration avec sauvegarde **manuelle**, et le report
explicite de l'automatisation vers une destination externe permanente avant
usage clientèle réel. La piste 03:00 UTC/commande SSH de capture fixe n'est
pas mise en œuvre ; aucun wrapper, droit sudo ou changement de clé installé.

Le point bloquant avant de vraies données est suivi dans TD-B024.
La réparation globale du cache mini-s1 est suivie dans TD-B025. Le volet VPS
de TD-B010 est prouvé, mais le remplacement de l'ancienne base locale reste
ouvert hors lot démo : ne pas effacer ni substituer cette base pour clôturer.
Les critères du sprint distinguent maintenant ces reports du périmètre livré.

Contrôle natif exécuté par l'agent sur mini-s1 :

```sh
systemctl show tervo-backup-mini.timer tervo-backup-mini.service \
  -p Id -p LoadState -p ActiveState -p UnitFileState --no-pager
```

Observé, code 0 : les deux unités sont `LoadState=not-found`,
`ActiveState=inactive`, sans `UnitFileState`. Aucun timer de ce parcours activé.
La clé dédiée reste en SFTP lecture seule ; on ne prétend pas que
`pull-backup.sh` soit déjà raccordé à une capture distante non interactive.
La procédure manuelle validée reste la référence ; pour un nouveau backup,
créer une nouvelle capture et reprendre ses nouveaux chemin/hash, pas réutiliser
l'archive `03aca082` pour prétendre sauvegarder des écritures plus récentes.

Restent pour la clôture démo : reboot contrôlé du VPS, contrôles services/
ports/TLS/ressources, nettoyage des seules copies et ressources de recette
après accord ciblé, procédures finales et commit. Aucun reboot ni nettoyage
supplémentaire effectué par cet arbitrage.

### Contrôle courant reçu — ne prouve pas un reboot récent

L'opérateur a exécuté le bloc de lecture : nouveau champ intitulé « Nouveau
démarrage », mais boot ID `9bdbc910-09a1-4eb2-93e6-84a9c25daf2d` et démarrage
affiché `2026-10-12 21:56:37`, noyau `6.12.111+deb13-amd64`.
Conteneurs source actifs depuis 29 heures à 6 jours. Ce retour valide l'état
courant, **pas le test après un reboot récent** ; aucun boot ID avant/après
différent n'est reçu. Ne pas cocher ce critère sur le seul titre du bloc.

Observé : readiness locale et deux GET HTTPS à 200, TLS 0 ; Caddy/Docker/
fail2ban actifs ; services `tervo` healthy, backend/frontend `127.0.0.1:8000`
et `127.0.0.1:3000`, Dockge `127.0.0.1:5001`, admin Caddy `127.0.0.1:2019`,
PostgreSQL sans publication hôte. Seuls SSH et Caddy écoutent publiquement
en TCP 22/80/443. Chrony 323 UDP et Exim4 25 TCP restent loopback :
cela ne prouve pas un serveur mail public ou un envoi applicatif configuré.
UFW actif, défaut incoming/routed deny ; seules règles allow 22/80/443 TCP
IPv4/IPv6, anciennes règles deny 7410 conservées.

Disque : 98 Go libres, 11 % utilisés ; RAM disponible : 4 519 MiB, swap non
utilisé. Les compteurs de `tervo_db` restent `1/2/2/0/3/2`.
Ces mesures valident le contrôle manuel de ressources ; pas de monitoring auto.

Le retour montre aussi trois conteneurs encore actifs du projet de recette
`int129-vps-33c350b23010`, avec frontend/backend sur `127.0.0.1:19830/19829`.
Ils ne sont pas des publications Internet mais restent des ressources à
inventorier et nettoyer après accord ciblé. La déclaration historique de
nettoyage INT-129 n'est donc pas une preuve de leur suppression effective.
Ne pas retirer les volumes/images sur la seule ressemblance du nom.

### Accès agent rétabli, sudo inchangé

L'agent SSH mini-s1 était vide ; après chargement temporaire de la clé par
l'opérateur, connexion agent réussie comme `tervo` sur `22565`. Même boot ID
et même date de démarrage confirmés, Caddy et Docker `enabled`. `sudo -n true`
reste refusé avec demande de mot de passe (code global 1). Pas de règle sudo
ou de groupe Docker ajouté sur le VPS. Reboot demandé via la commande native
dans le terminal de l'opérateur, pas lancé par l'agent.

Certificats publics relevés par l'agent avant ce reboot attendu :

| Domaine | Série | SHA-256 |
|---|---|---|
| `tervoapp.com` | `05C8E96C8D4F15F316F05204530D24341772` | `6F:7B:19:71:0E:B0:38:02:03:6E:E1:32:FC:CE:74:23:DD:08:97:D5:19:FA:16:5B:6D:A3:EC:59:E6:89:14:0E` |
| `api.tervoapp.com` | `05FDE36198BB26D6CCB09435C6F826D165CD` | `6C:A6:06:F2:26:B6:E1:F4:9D:42:30:15:E1:86:B9:3F:F4:33:54:EF:0F:C3:F7:8A:5D:D6:FE:55:18:94:EC:57` |

Validité affichée : 19 octobre 2026 → 17 janvier 2027. Ces métadonnées sont
publiques, aucune clé privée lue. La comparaison après reboot permettra de
vérifier la conservation du certificat, pas d'inventer un renouvellement déjà
effectué. Dernier contrôle SSH : boot ID toujours identique, services actifs,
adresses privées inchangées ; le reboot reste à exécuter.

La prochaine étape est un reboot contrôlé du **VPS seulement**, après vérification
de l'activation au démarrage de Caddy/Docker et des politiques de redémarrage
des trois services Tervo et de Dockge. Relever le boot ID avant/après, puis
contrôler disponibilité, persistance des données, ports, UFW et ressources.
La coupure SSH est normale pendant le reboot. Cette étape reste à exécuter
par l'opérateur ; aucun reboot n'a été lancé par l'agent.

## 21. Reboot réel confirmé et contrôles après démarrage

L'opérateur a exécuté sur le VPS :

```sh
test "$(hostname)" = 22565 && sudo systemctl reboot
```

Coupure SSH reçue, puis accès agent rétabli après retour du serveur.
Vérification SSH exécutée par l'agent, code 0 :

| Propriété | Avant | Après |
|---|---|---|
| Boot ID | `9bdbc910-09a1-4eb2-93e6-84a9c25daf2d` | `b82ade6e-b9ad-44a7-97c9-4eef4bf95dfa` |
| Démarrage affiché | `2026-10-12 21:56:37` | `2026-10-24 00:55:05` |
| Noyau | `6.12.111+deb13-amd64` | `6.12.113+deb13-amd64` |
| Caddy / Docker / fail2ban / UFW | Actifs | Actifs |
| Disque | 98 Go libres, 11 % utilisés | Identique |
| RAM disponible | Environ 4 519 MiB | 4 910 MiB |
| Swap utilisé | 0 | 0 |

Horaires locaux affichés, pas de fuseau déduit d'`uptime -s`.
`ss -lntu` confirme les mêmes adresses : 8000/3000/5001/2019 et les ports
de recette 19829/19830 uniquement loopback ; aucun 5432 hôte ni UDP 443.
Seuls TCP 22/80/443 écoutent publiquement. SMTP 25 et chrony 323 restent locaux.
Le contrôle externe depuis mini-s1 ne peut joindre aucun des sept ports
2019/3000/5001/5432/8000/19829/19830, code du contrôle 0.

Requêtes agent après reboot, sans `-k` :

| URL | Résultat |
|---|---|
| `https://tervoapp.com/login` | 200, IP `151.241.228.152`, TLS 0 |
| `https://api.tervoapp.com/health/ready` | 200, même IP, TLS 0 |
| `http://tervoapp.com/login` | 308 vers le même chemin en HTTPS |
| `http://api.tervoapp.com/health/ready` | 308 vers le même chemin en HTTPS |

Les deux séries et empreintes de certificats sont **strictement identiques**
à la table précédente ; dates de validité inchangées, code de lecture 0.
L'état certificat a donc survécu au reboot. La gestion automatique Caddy est
configurée/active ; aucun renouvellement effectif n'est inventé.
Les deux originaux PNG récupérés en HTTPS après reboot donnent toujours
les SHA-256 source attendus, code 0.

Le dernier comptage SQL privilégié transmis par l'opérateur était le contrôle
à chaud précédent (`1/2/2/0/3/2`) ; ne pas le présenter comme un nouveau comptage
après ce reboot. Readiness PostgreSQL et octets des photos sont contrôlés
après le reboot par l'agent. La recette de restauration SQL/photos reste
validée indépendamment en section 19.

Les ports de la recette INT-129 restent actifs en loopback à cet instant :
nettoyage encore à autoriser. Il a depuis été exécuté par l'opérateur ; les
sorties sont en section 23. Ne supprimer ni images de secours, ni stack `tervo`,
ni dépôt restic pour « finir ». Le commit final de livraison reste à effectuer
après la dernière clôture documentaire.

## 22. Nettoyage ciblé autorisé — blocs root exécutés par l'opérateur

Accord explicite de l'opérateur : retirer la stack
`int129-vps-33c350b23010` et ses volumes/réseaux exclusifs, la cible de
restauration VPS arrêtée et son volume, trois dossiers temporaires VPS et
deux copies en clair mini-s1. Préserver `tervo`, ses données de démo, Dockge,
les images de secours, le dépôt restic/`03aca082`, son secret et les clés.

Derniers droits contrôlés : SSH agent VPS refusé par clé à cet instant ;
sudo local mini-s1 non interactif refusé. Les opérations ci-dessous restent
donc à exécuter par l'opérateur en root, sans nouvel élargissement de droits.
Les blocs sont bornés aux ressources nommées, pas des recettes de nettoyage
générique à réutiliser ailleurs.

### VPS 22565 — données et propriété Docker contrôlées avant suppression

La définition Compose de `tervo` est utilisée avec le **projet de recette
explicitement différent**. `down --volumes` ne doit jamais viser `-p tervo`.
HEAD et absence de modification du Compose sont vérifiés pour ne pas lire
une définition de volumes inconnue. Aucun `--rmi` ni prune.

```sh
(
  set -eu
  test "$(hostname)" = 22565
  test "$(id -u)" = 0
  exec 9>/run/lock/tervo-operations.lock
  flock -n 9
  P=int129-vps-33c350b23010
  R=tervo-restore-vps-8fc7aaf9-18f7-48b7-8cb9-f4450b4bfec6
  V="${R}-data"
  CHECKOUT=/opt/stacks/tervo
  test "$P" != tervo
  test "$(git -C "$CHECKOUT" rev-parse HEAD)" = 291f7ead24822cf8f9c0164aaf9dc3420d351647
  git -C "$CHECKOUT" diff --quiet HEAD -- deploy/docker-compose.yml
  docker exec -i tervo-postgres-1 sh -c \
    'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
BEGIN READ ONLY;
SELECT current_database() AS base;
SELECT 'comptes' AS element, count(*) AS nombre FROM public."user"
UNION ALL SELECT 'clients', count(*) FROM public.client
UNION ALL SELECT 'sites', count(*) FROM public.site
UNION ALL SELECT 'equipements', count(*) FROM public.equipment
UNION ALL SELECT 'interventions', count(*) FROM public.intervention
UNION ALL SELECT 'photos', count(*) FROM public.photo;
COMMIT;
SQL
  for C in $(docker ps -aq --filter "label=com.docker.compose.project=$P"); do
    NAME="$(docker inspect --format '{{.Name}}' "$C")"
    case "$NAME" in "/${P}-"*) ;; *) echo "Nom inattendu : arrêt." >&2; exit 1 ;; esac
    printf 'Recette : %s\n' "$NAME"
  done
  for VOL in $(docker volume ls -q --filter "label=com.docker.compose.project=$P"); do
    case "$VOL" in "${P}_"*) ;; *) echo "Volume inattendu : arrêt." >&2; exit 1 ;; esac
    for C in $(docker ps -aq --filter "volume=$VOL"); do
      test "$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$C")" = "$P"
    done
  done
  RCID="$(docker ps -aq --filter "name=^/${R}$")"
  if [ -n "$RCID" ]; then
    test "$(docker inspect --format '{{.State.Running}}' "$R")" = false
    test "$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$R")" = "$V"
  fi
  for C in $(docker ps -aq --filter "volume=$V"); do
    test "$(docker inspect --format '{{.Name}}' "$C")" = "/$R"
  done
  for D in /var/tmp/tervo-backup.haPfNpxv /var/tmp/tervo-restore-vps.B6flfaiz /var/tmp/tervo-int111-fixture.WO21M3Pa; do
    test ! -L "$D"
    if [ -e "$D" ]; then
      test -d "$D"
      test "$(realpath -e "$D")" = "$D"
    fi
  done
  docker compose --env-file "$CHECKOUT/deploy/.env" \
    -f "$CHECKOUT/deploy/docker-compose.yml" -p "$P" \
    down --volumes --remove-orphans
  test -z "$(docker ps -aq --filter "label=com.docker.compose.project=$P")"
  test -z "$(docker volume ls -q --filter "label=com.docker.compose.project=$P")"
  test -z "$(docker network ls -q --filter "label=com.docker.compose.project=$P")"
  if [ -n "$RCID" ]; then docker rm "$R"; fi
  if [ -n "$(docker volume ls -q --filter "name=^${V}$")" ]; then docker volume rm "$V"; fi
  rm -rf -- /var/tmp/tervo-backup.haPfNpxv \
    /var/tmp/tervo-restore-vps.B6flfaiz \
    /var/tmp/tervo-int111-fixture.WO21M3Pa
  printf '\n--- Services conservés ---\n'
  docker ps --format '{{.Names}}  {{.Status}}  {{.Ports}}'
  printf '\nNettoyage VPS ciblé terminé.\n'
)
```

Le SELECT est un nouveau relevé après reboot, pas une écriture. Toute
propriété ou référence inattendue arrête le bloc. Les retraits Docker n'ont
pas de force : un volume encore utilisé ne doit pas être arraché. Une erreur
après une première suppression ne l'annule pas ; transmettre la sortie avant
toute reprise. Les anciens dossiers de configuration non nommés et toutes
les images sont préservés.

### Mini-s1 — vérifier la récupération depuis restic, puis retirer deux copies

```sh
(
  set -eu
  test "$(hostname)" = mini-s1
  test "$(id -u)" = 0
  set -- /etc/tervo/restic-*
  test "$#" -eq 1
  test -f "$1"
  test "$(stat -c '%a:%u' "$1")" = '600:0'
  unset RESTIC_PASSWORD RESTIC_PASSWORD_COMMAND RESTIC_REPOSITORY_FILE
  export RESTIC_REPOSITORY=/srv/backups/tervo
  export RESTIC_PASSWORD_FILE="$1"
  CHECK="$(restic dump 03aca082 /tervo.tar | sha256sum)"
  test "${CHECK%% *}" = f833b896eab77eb17e235d9b7b83b7516bd911bca7be6002092c9465ee144d7b
  for D in /var/tmp/tervo-receive.xiND9EiH /var/tmp/tervo-restore.F7RXfxl8; do
    test ! -L "$D"
    if [ -e "$D" ]; then
      test -d "$D"
      test "$(realpath -e "$D")" = "$D"
    fi
  done
  rm -rf -- /var/tmp/tervo-receive.xiND9EiH /var/tmp/tervo-restore.F7RXfxl8
  restic snapshots --host tervo-vps --tag int111
  printf '\nCopies temporaires retirées, dépôt et secret conservés.\n'
)
```

La récupération vérifiée par SHA-256 précède les suppressions. Même sans
`pipefail`, un dump échoué/vide ne peut satisfaire le checksum attendu.
Le secret n'est pas affiché et aucun nouveau snapshot n'est créé.
L'opérateur a ensuite exécuté les deux blocs ; les sorties reçues sont
consignées en section 23.

## 23. Nettoyage exécuté — sorties reçues le 24 octobre 2026

L'opérateur a exécuté les deux blocs root de la section 22. Sorties
transmises telles quelles, sans erreur visible, puis session root
quittée (`root@22565:~# exit`, retour au prompt `tervo@22565:~$`).

### Mini-s1 — copies en clair retirées, dépôt et secret conservés

```text
repository 4f50c482 opened (version 2, compression level auto)
ID        Time                 Host        Tags          Paths       Size
--------------------------------------------------------------------------------
03aca082  2026-10-22 19:51:57  tervo-vps   tervo,int111  /tervo.tar  280.000 KiB
--------------------------------------------------------------------------------
1 snapshots

Copies temporaires retirées, dépôt et secret conservés.
```

`restic dump` comparé au SHA-256 attendu est silencieux en cas de succès :
le bloc n'a pu atteindre `Copies temporaires retirées…` qu'avec le checksum
conforme, sous `set -eu`. Les deux dossiers `/var/tmp/tervo-receive.xiND9EiH`
et `/var/tmp/tervo-restore.F7RXfxl8` sont supprimés ; le dépôt
`/srv/backups/tervo` et le fichier `/etc/tervo/restic-*` restent en place.
La clé SFTP de transfert en lecture seule n'est pas modifiée.

### VPS 22565 — recette et cible supprimées, production préservée

```text
BEGIN
   base
----------
 tervo_db
(1 row)

    element    | nombre
---------------+--------
 comptes       |      1
 clients       |      2
 sites         |      2
 equipements   |      0
 interventions |      3
 photos        |      2
(6 rows)

COMMIT
Recette : /int129-vps-33c350b23010-backend-1
Recette : /int129-vps-33c350b23010-postgres-1
Recette : /int129-vps-33c350b23010-frontend-1
[+] down 7/7
 ✔ Container int129-vps-33c350b23010-frontend-1 Removed
 ✔ Container int129-vps-33c350b23010-backend-1  Removed
 ✔ Container int129-vps-33c350b23010-postgres-1 Removed
 ✔ Volume int129-vps-33c350b23010_postgres_data Removed
 ✔ Network int129-vps-33c350b23010_frontend     Removed
 ✔ Network int129-vps-33c350b23010_database     Removed
 ✔ Volume int129-vps-33c350b23010_uploads_data  Removed
tervo-restore-vps-8fc7aaf9-18f7-48b7-8cb9-f4450b4bfec6
tervo-restore-vps-8fc7aaf9-18f7-48b7-8cb9-f4450b4bfec6-data

--- Services conservés ---
tervo-backend-1  Up 10 hours (healthy)  127.0.0.1:8000->8000/tcp
tervo-frontend-1  Up 10 hours (healthy)  80/tcp, 127.0.0.1:3000->3000/tcp
tervo-postgres-1  Up 10 hours (healthy)  5432/tcp
dockge-dockge-1  Up 10 hours (healthy)  127.0.0.1:5001->5001/tcp

Nettoyage VPS ciblé terminé.
```

| Sortie | Ce qu'elle prouve |
|---|---|
| `BEGIN` … `COMMIT` | Relevé en lecture seule (`BEGIN READ ONLY` dans le bloc) de `tervo_db` `1/2/2/0/3/2`, aucune écriture |
| Trois lignes `Recette : /int129-vps-…` | Les conteneurs visés portent bien les noms du projet de recette |
| `down 7/7` | 3 conteneurs, 2 volumes et 2 réseaux de la recette supprimés sous `-p int129-vps-33c350b23010` |
| `tervo-restore-vps-…` puis `…-data` | Conteneur de restauration (arrêté et propriété contrôlés) et son volume retirés |
| Quatre services `(healthy)` | `tervo` et Dockge restent seuls actifs, avec leurs ports loopback |

Les contrôles `docker ps/volume ls/network ls` vides après `down` et les
`rm -rf` des trois dossiers temporaires `/var/tmp/tervo-*` sont silencieux en
cas de succès ; `docker rm` et `docker volume rm` impriment seulement le nom
retiré, comme observé. La réussite des étapes muettes est déduite de l'arrivée
au message final `Nettoyage VPS ciblé terminé.` sous `set -eu`.

**Limites de traçabilité.** L'agent n'a pas exécuté ces commandes et n'a pas
exécuté d'inventaire Docker privilégié : son accès SSH `tervo` est refusé par
clé après le reboot (`Permission denied (publickey)`, contrôle du 24 octobre
2026). La vérification externe faite par l'agent après le nettoyage donne
`https://tervoapp.com/login` 200, `https://api.tervoapp.com/health/ready` 200,
`http://tervoapp.com/login` 308, TLS 0 ; TCP 19829/19830 refuse depuis mini-s1,
ce qui ne prouve pas à soi seul leur suppression puisque ces ports n'étaient
déjà joignables que sur loopback. Les images, la stack `tervo`, ses volumes,
`/var/lib/tervo/state`, la configuration/état Caddy, les sauvegardes privées
et le dépôt restic ne sont pas touchés par ces blocs.

## Périmètre à garder explicite avant publication

- Les prérequis INT-125 à INT-129 et INT-131/132 sont livrés avec leurs limites.
- Les écrans catalogue/showroom V2 restent dans TD-F007 ; les rôles
  MANAGER/COMMERCIAL dans TD-B013. Ne pas les annoncer livrés avec cette mise
  en service ni les développer implicitement pendant le déploiement.
- Le souhait de compte Linux `lb11` est conservé dans INT-127 ; aucune transition
  depuis l'accès `tervo` n'est encore effectuée. Ne pas supprimer l'accès valide
  avant d'avoir vérifié tout nouvel accès.
- La stack et HTTPS public sont en place, la recette navigateur est confirmée
  par l'opérateur ; les sauvegardes régulières mini-s1 restent à valider.
- Le nettoyage déclaré d'INT-129 n'avait pas de sortie détaillée. La section 23
  documente le retrait réel des ressources de recette et de la cible de
  restauration le 24 octobre 2026, sur sortie opérateur, sans inventaire
  privilégié indépendant de l'agent (SSH `tervo` refusé par clé après reboot).
- Restent le commit de livraison d'INT-111, le bilan de sprint porté par
  INT-112 (INT-130 livrée le 24 octobre 2026) et les retouches frontend
  mineures à préciser.
