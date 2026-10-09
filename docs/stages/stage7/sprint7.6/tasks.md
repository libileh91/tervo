# Sprint 7.6 — Déploiement VPS et documentation entretien

> **Tervo V2** · INT-111/112 + INT-124 à INT-132 · **Statut :** INT-124/125 historiquement validées ; Caddy natif + Dockge privé approuvés, INT-131/132 à implémenter ; prochaine INT-131 après feu vert, application non déployée
> **Dépendances :** Valider le périmètre livré et ses tests avant déploiement ; documenter explicitement le backlog restant.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.6/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

> Reprend et finalise l'ancien sprint 6.4/6.5, sur le modèle v2.

## Découpage du chantier INT-111

INT-111 conserve la mise en service publique et ses preuves système
acquises ; INT-112 reste la documentation entretien. Les prérequis
techniques sont transférés aux identifiants INT-124 à INT-130.
La décision Caddy/Dockge ajoute INT-131/132, vérifiés libres, sans effacer
les preuves précédentes. Aucun cadrage ou transfert de test ne vaut livraison.

| Ordre | Tâche | Livrable | Dépendances |
|---|---|---|---|
| Historique | INT-124 (3 pts) | 1Panel/OpenResty privé, preuves conservées | Livrée, cible remplacée par décision ; bascule non effectuée |
| Historique | INT-125 (5 pts) | Images/configuration reproductibles, publications loopback | Livrée localement ; contrat réutilisé par Caddy |
| 1 | INT-131 (3 pts) | Caddy natif et retrait réversible de l'ancien proxy | Socle VPS + INT-124/125, pas publication Tervo |
| 2 | INT-132 (3 pts) | Dockge privé et gate Git/Compose/env | INT-125/131 ; adoption Tervo à démontrer |
| 3 | INT-126 (2 pts) | Bootstrap sécurisé du premier administrateur | Modèle identité existant |
| 4 | INT-127 (3 pts) | PostgreSQL cible et décision de reprise | INT-125 |
| 5 | INT-128 (5 pts) | Backup/restore vérifié en isolation | INT-125/127, inventaire Caddy/Dockge INT-131/132 |
| 6 | INT-129 (5 pts) | Commande de release et rollback contrôlé | INT-125/127/128 ; pas d'autorité Dockge concurrente |
| 7 | INT-111 (5 pts) | Mise en service manuelle, DNS/HTTPS et recette | INT-125 à INT-129 + INT-131/132 |
| 8 | INT-130 (3 pts) | CI/CD réutilisant la commande de release | INT-111 manuelle validée, INT-129 |
| 9 | INT-112 (3 pts) | Entretien fondé sur les preuves finales | INT-111 et INT-130 pour le bilan final |

Estimations indicatives à réévaluer par tâche : 40 points au total,
contre les 8 points historiques trop larges. Ce n'est pas une mesure du
travail déjà consommé. Le dossier reste `sprint7.6`, sans nouveau sprint.

**Règles communes**
- Feu vert distinct par tâche. Cette mise à jour valide le cadrage
  Caddy/Dockge, pas leur installation ni une bascule du VPS.
- Git/Compose définissent Tervo ; Caddy natif possède le trafic public,
  Dockge fournit une console Compose privée avec privilèges élevés,
  sans duplication de fichiers ni release concurrente. SSH reste le secours.
- CI vérifie, VPS construit les images de production ; GHCR reste hors
  périmètre. Ne pas confondre compilation Vue de vérification et image
  de production, ni rebuild ancien et artefact exact de secours.
- Secrets hors Git/logs partagés, `.env` explicite et `config --quiet`.
  Pannes/restores/rollback en isolation, pas d'opération destructive implicite.
- Commits par tâche ; guides dans `notes/backend/deploy/vps/`, notes de
  livraison dans `notes/backend/sprint7.6/`.
- Cas JSON : `id` et `legacy_id` historiques conservés, `task` indique
  le propriétaire et `origin_task` trace les transferts depuis INT-111.

---

## INT-111 — Déploiement VPS (5 pts)

**User Story**
En tant que **gérant**,
Je veux **déployer Tervo v2 sur un VPS en production**,
Afin de **disposer d'une instance publique avec HTTPS**.

**Acceptance Criteria**
- [x] VPS : Debian 13 (choix utilisateur, remplace Ubuntu 24.04 prévu), SSH clé, ufw (22/80/443), fail2ban
- [x] SSH par clé uniquement, connexion root directe désactivée, utilisateur non-root et mises à jour de sécurité automatiques
- [ ] Prérequis actifs INT-125 à INT-129 et INT-131/132 livrés/vérifiés ; les preuves historiques INT-124 restent conservées, périmètre et backlog explicités avant publication
- [ ] Choix de reprise INT-127 appliqué après backup/restore INT-128 : transfert réel si nécessaire, aucune source présumée ; TD-B010 clôturé sur preuves
- [ ] Release manuelle via INT-129 : SHA/images identifiés, migrations avant exposition et disponibilité effective des services
- [ ] PostgreSQL non publié, services applicatifs loopback, Dockge 5001 privé et API admin Caddy locale ; ancien panneau/proxy neutralisés après INT-131, surface publique 22/80/443 TCP vérifiée
- [ ] DNS frontend/API, Caddy vers les services locaux, certificats Let's Encrypt valides, renouvellement automatique et redirection HTTP vers HTTPS vérifiés ; état TLS persistant sauvegardable
- [ ] GET réels frontend/API et recette navigateur : admin via INT-126, connexion, dashboard, upload/récupération photo sans compte démo
- [ ] Backups planifiés et récupération INT-128 vérifiés sur le déploiement réel, y compris secrets/proxy ; seuils disque/RAM suivis
- [ ] Procédure rejouable dans `notes/backend/deploy/vps/` (dossier demandé par l'utilisateur) : prérequis, commandes, erreurs/corrections, schéma et différences mini-s1/VPS ; bilan du sprint dans `notes/backend/sprint7.6/`

**Technical Notes**
- INT-111 garde son objectif public et ses critères système validés.
  La CI/CD passe à INT-130, après la recette manuelle : clore INT-111
  ne termine pas le sprint et n'active pas `DEPLOY_ENABLED`.
- Socle Hostkey/Debian 13 contrôlé : compte `tervo`, accès SSH par clé,
  sudo, root SSH interdit, UFW actif et retour arrière annulé après
  reconnexion, jail sshd systemd chargée. Docker/Compose préinstallés ;
  noyau Security 6.12.111 actif après mise à jour et reboot.
- Dépôt Debian Security réactivé et overrides de validation temporelle
  APT retirés. Cadence quotidienne configurée pour Security uniquement,
  reboot/nettoyage automatiques désactivés ; dry-run code 0 relu par
  l'agent. La prochaine exécution automatique réelle reste à observer.
- Preuves et limites : [note SSH](../../../../notes/backend/deploy/vps/01-inventaire-et-acces-ssh.md)
  et [note système](../../../../notes/backend/deploy/vps/02-preparation-securite-systeme.md).
  Empreinte serveur indépendante non documentée et pare-feu fournisseur
  non inventorié ; application, HTTPS, données et déploiement CI non validés.
- Cas propriétaires : TC-INT-111-01/04/05/07. Le cas système reste
  partiel sur les vérifications non retranscrites ; les autres ne sont
  pas déclarés réussis.

---

## INT-124 — 1Panel et OpenResty à administration privée (3 pts)

**Statut :** livraison historique validée. La nouvelle cible est Caddy/Dockge ;
INT-131 doit effectuer la transition. Aucun arrêt ou remplacement n'est
déduit de cette décision documentaire, et les critères cochés restent
les preuves de l'installation précédente.

**User Story**
En tant qu'**exploitant**,
Je veux **installer le panneau et son proxy sans exposer l'administration**,
Afin de **gérer le VPS sans créer une seconde stack Tervo**.

**Acceptance Criteria**
- [x] Archive v2.3.2 amd64 et SHA-256 vérifiés localement ; installateur lu, patch supprimant son appel d'ouverture automatique du port testé sans fuzz et avec contrôle d'unique changement
- [x] Inventaire VPS actualisé, absence de données/installation 1Panel préexistantes vérifiée ; paquet exact préparé et hash revérifié sur le VPS
- [x] Installation contrôlée, versions/chemins/services core-agent documentés ; Docker/Compose et daemon.json existants conservés, aucune activation de licence Pro réalisée dans le parcours
- [x] Administration 7410 privée en fonctionnement : bind loopback, tunnel avec clé choisie, bind local explicite et `ExitOnForwardFailure`, refus TCP public IPv4 ; aucune écoute administrative IPv6 ni IPv6 publique constatée dans l'inventaire ; bind et UFW conservés après restart core/agent
- [x] Retour automatique après reboot réel : SSH/Docker/UFW/core-agent actifs, OpenResty Up, bind privé et UFW conservés, aucune écoute 18080 ; HTTP public 200 et accès TCP public 7410 refusé
- [x] Accès navigateur privé après reboot confirmé ; procédure de contrôle après chaque mise à jour documentée (bind, règles automatiques selon exception approuvée, refus extérieur IPv4/IPv6 si présente et tunnel), sans prétendre à une mise à jour non exécutée
- [x] OpenResty 1.31.1.1-2-4-noble installé : conteneur actif, écoutes 80/443 IPv4/IPv6 et HTTP public 200
- [x] Mode OpenResty observé : host, restart always, nginx -t réussi ; upstreams loopback du VPS, aucun bridge externe nécessaire au routage
- [x] Routage et rechargement validés sur cible jetable sans IP statique de conteneur : marqueur renvoyé via OpenResty après reload et depuis l'extérieur ; test de résolution Docker après recréation non applicable au mode host observé
- [x] Changements du panneau journalisés, confinement/retour arrière et note de livraison documentés ; critères/cas mis à jour, restauration complète distincte non déclarée testée

**Technical Notes**
- Dépend du socle système déjà validé, **pas de la clôture d'INT-111**.
- Sources : `deploy/patches/1panel-v2.3.2-private-admin.patch`,
  [note 03](../../../../notes/backend/deploy/vps/03-preparation-1panel-prive.md).
  [Note de livraison](../../../../notes/backend/sprint7.6/INT-124-1panel-openresty-prives.md).
  L'archive/patch seul ne garantit pas le bind ; les critères cochés
  reposent sur les contrôles effectivement reçus.
- Host : upstreams loopback du VPS. Bridge : noms sur réseau partagé et
  résolution/rechargement après recréation ; réseau externe seulement si utile.
- La recette du proxy utilise une cible jetable : elle n'attend pas les
  services Tervo d'INT-125 ni les domaines/HTTPS publics d'INT-111.
- Aucun PostgreSQL, runtime Python/Node ou Compose Tervo créé dans 1Panel.
- Cas TC-INT-111-02 : ID historique conservé, propriétaire INT-124.
- Incident après installation : HTTP 200 extérieur sur 7410, ALLOW
  7410/tcp et 443/udp ajoutés par la synchronisation `FirewallPortWhiteList`
  de l'agent, malgré le patch du shell. Panneau arrêté et refus extérieur
  confirmé, services désactivés et règles nettoyées avec DENY 7410.
  Exception firewall approuvée avec bind loopback obligatoire.
- Reprise contrôlée : login par tunnel puis 502 sur l'API agent arrêté.
  Bind privé appliqué par l'utilisateur ; core/agent désormais actifs et
  disabled au boot, écoute 127.0.0.1:7410 et socket agent LISTEN contrôlés
  par Delta, HTTP local 200 et tentative TCP publique IPv4 en timeout.
  Utilisateur : informations VPS affichées sans 502, DENY UFW conservés,
  seuls ALLOW 22/80/443 TCP visibles. Après restart des deux unités,
  lectures utilisateur : core/agent active, bind loopback maintenu et
  UFW inchangé ; nouveau test public IPv4 Delta en timeout.
  Activation au boot effectuée par l'utilisateur : liens créés et
  `enabled` pour les deux unités. La suite ci-dessous valide reboot et
  recette proxy ; aucune mise à jour 1Panel ni réutilisation de cookie
  partagé n'a été effectuée.
- Inventaire préalable OpenResty fourni par l'utilisateur : aucun conteneur
  actif/arrêté dans le daemon Docker interrogé, aucune écoute TCP 80/443.
  Version puis mode effectif confirmés dans la suite de la recette.
- Installation OpenResty confirmée par journal et sorties utilisateur :
  `1Panel-openresty-wTu3`, image `1panel/openresty:1.31.1.1-2-4-noble`,
  Up et écoutes 80/443 IPv4/IPv6. Delta : HTTP public 200, TCP public
  7410 toujours inaccessible. Utilisateur : NetworkMode=host, restart
  always et nginx -t réussi ; bind 7410 loopback et UFW inchangés après
  installation. Recette jetable : GET direct 18080 et GET via proxy après
  nginx -t/reload renvoient le marqueur ; Delta confirme HTTP public 200
  avec corps exact et Host de test. Nettoyage confirmé ci-dessous.
- Contrôle final utilisateur : CLI 1Panel v2.3.2 stable et nginx -t réussi ;
  cible Python PID 13535 arrêtée avec fuser, aucune écoute 18080 ensuite.
  Suppression du site de test confirmée par l'utilisateur.
- Post-reboot : uptime-s 2026-10-07 21:16:41, cinq services active,
  OpenResty Up, bind 7410 privé, absence 18080 et UFW inchangé.
  Delta : HTTP public 200 sans marqueur temporaire, TCP public 7410
  et 18080 inaccessibles. Utilisateur : panneau accessible après relance
  du tunnel, informations VPS affichées sans 502.
- Clôture sur le périmètre runtime vérifié. Le canal stable ne prouve pas
  une licence ; aucune activation Pro dans le parcours, pas d'audit privé
  exhaustif. IPv6 publique absente de l'inventaire initial, pas de nouveau
  test extérieur IPv6 ; contrôles obligatoires si une adresse est ajoutée.
  Backup/restore complet, upgrade, HTTPS et stack Tervo restent distincts.

---

## INT-125 — Stack de production reproductible (5 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **construire et configurer les services depuis un checkout neuf**,
Afin de **déployer un artefact traçable sans secrets ni fichiers manuels cachés**.

**Acceptance Criteria**
- [x] Dockerfiles construisibles depuis un export Git propre, frontend multi-stage sans `dist/` manuel ; versions/digests utiles fixés et images identifiables par SHA
- [x] Secrets critiques obligatoires, `.env` explicite et modèle sans vraie valeur, permissions et parsing/échappement du DSN vérifiés ; validation Compose `--quiet` refusant les variables ambiantes
- [x] Binds applicatifs loopback, PG non publié, réseaux selon INT-124, volumes persistants et versions d'image explicites
- [x] Healthcheck PostgreSQL, readiness backend vérifiant la DB et santé frontend ; panne DB testée en isolation avec 503/unhealthy puis reprise 200/healthy
- [x] Domaines/transport API choisis, client configurable sans hostname historique, appels API/avis publics/uploads cohérents et CORS limité aux origines nécessaires
- [x] Rotation des logs bornée, seuils disque/RAM et nettoyage documentés ; pas de suppression automatique des volumes/réseaux nécessaires hors ressources de recette UUID
- [x] Scénarios source propre/configuration/disponibilité et note de livraison validés localement ; ne vaut pas build/release sur le VPS

**Technical Notes**
- Dépend d'INT-124 pour le réseau. Sources : Dockerfiles, Compose,
  configuration/main backend et client frontend.
- Une construction par image/version sur VPS ; compilation Vue CI distincte.
  OpenAPI seul ne remplace pas la readiness DB ; le job de déploiement
  historique a été retiré dans INT-125, il ne doit pas être réactivé tel quel.
- Ne pas partager de rendu complet Compose/inspect avec les environnements.
- Cas TC-INT-111-03/08 : propriétaires INT-125, IDs conservés.
- Domaines confirmés : frontend `https://tervoapp.com`, API
  `https://api.tervoapp.com/api/v1` ; pas de bascule DNS dans cette tâche.
- Compose sans réseau externe 1Panel : OpenResty host rejoint 127.0.0.1,
  frontend sur bridge séparé, backend/PG sur réseau database.
- Production : DB components/URL exclusifs, URL.create puis drivers
  asyncpg/psycopg2 communs ; Alembic reçoit un URL sans ConfigParser%.
  `/health/ready` SELECT 1 borné, 200/503 statiques, hors OpenAPI.
- Validation : 27 tests backend ciblés, 20 frontend, typecheck/build ;
  export Git sans dist/deps/DB, build Docker et PG17.7 jetable, migrations
  jusqu'à m109, panne/reprise réelle, uploads persistants après recreate,
  CORS et santé frontend (index absent503 puis200), PDF en mémoire,
  env pollué/secret manquant/mode644 refusés, labels par voie Compose.
- Ancien job deploy retiré mécaniquement, pas simplement commenté.
  CI frontend Bun1.2.20/URL fictive ; aucun run distant revendiqué.
- TD-B008/009 restent ouverts pour DB/rôles réels en INT-127 ; POSTGRES_USER
  initialise un superuser, aucun moindre privilège prétendu ici.
  Aucune vraie DB, bootstrap admin, sauvegarde, release ou VPS modifié.
- [Note pédagogique](../../../../notes/backend/sprint7.6/INT-125-stack-reproductible.md)
  et helper `deploy/check-stack.py --revision <objet Git explicite>`.

---

## INT-131 — Caddy natif et bascule du proxy réversible (3 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **remplacer 1Panel/OpenResty par un proxy natif déclaratif**,
Afin de **réduire les responsabilités implicites sans perdre les protections validées**.

**Acceptance Criteria**
- [ ] Inventaire live actualisé et sauvegarde privée des paramètres nécessaires de l'ancien panneau/proxy ; versions, restart policies, sockets et propriétaires de 80/443 relevés sans secrets
- [ ] Installation Caddy depuis source officielle vérifiée, version/service/utilisateur et état persistant documentés ; aucun démarrage automatique surprise sur les ports déjà occupés
- [ ] Deux profils versionnés : bootstrap actif HTTP seulement avec automatic HTTPS désactivé et sans vrais hostnames ; profil production des domaines choisis conservé inactif jusqu'à INT-111 ; validation avant reload et preuve d'absence de tentative ACME/état de certificat réel
- [ ] Bascule explicitement autorisée, ancien proxy et core/agent neutralisés au boot (restart policy Docker incluse), Caddy seul proxy public selon profil actif (:80 bootstrap, 80/443 production) ; SSH/Docker/UFW et données inchangés
- [ ] API admin locale/socket, aucun accès public 2019 ni administration 7410 ; profil initial TCP seulement, HTTP/3 désactivé sans exception UDP validée
- [ ] Routage/reload sur cible jetable, contrôle extérieur et retour après reboot ; rollback vers état ancien testé sans réinstallation/effacement, toutes ressources de recette nettoyées
- [ ] Note de livraison et inventaire des paramètres/état TLS à sauvegarder ; émission/renouvellement publics réellement testés seulement en INT-111

**Technical Notes**
- Réutilise INT-125 sans changer ses ports/réseaux ni les apps. Pas de
  build en CI/registre ajouté et pas de migrations métier.
- Sources envisagées : `deploy/caddy/`, guide de transition
  `notes/backend/deploy/vps/`, note `notes/backend/sprint7.6/`.
- Le bootstrap ne charge pas les hostnames Tervo et désactive explicitement
  automatic HTTPS : ne pas laisser Caddy tenter ACME parce qu'un profil
  production a été chargé avant l'autorisation DNS/TLS INT-111.
  Le profil production inactif conserve les upstreams 127.0.0.1:3000
  et 127.0.0.1:8000 et les domaines déjà choisis.
- 1Panel installé reste l'état de référence tant que la bascule n'a pas
  été exécutée. Son exception firewall historique n'est pas reconduite
  comme règle cible Caddy. Ne pas faire tourner deux proxies sur 80/443.
- Cas TC-INT-131-01/02, tous non exécutés au cadrage.

---

## INT-132 — Dockge privé et console Compose sans dérive (3 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **consulter logs et sorties Compose dans une console privée**,
Afin de **diagnostiquer Tervo sans créer une seconde source de configuration**.

**Acceptance Criteria**
- [ ] Version/image officielle exacte et digest relevés, publication 127.0.0.1:5001, données d'auth persistantes identifiées ; aucun domaine/route Caddy ni port public pour la console
- [ ] Login administrateur privé sans disableAuth, accès par tunnel ; console principale activée explicitement si nécessaire après sécurisation (désactivée par défaut dans la version étudiée), aucune sortie sensible partagée
- [ ] Accès docker.sock root-equivalent documenté ; ni mount :ro ni convention de lecture présentés comme RBAC read-only, SSH/systemd/journald non remplacés
- [ ] Gate sur stack jetable : layout/chemins identiques hôte-conteneur, contexte build, fichier env explicite, absence d'exports ambiants et identité projet/volumes démontrés ; configuration effective identique au chemin Git/CLI
- [ ] Logs/commandes utiles réellement accessibles, aucune copie de Compose devenue autonome ni édition/rebuild/delete caché ; Git reste autoritaire, aucun opérateur concurrent pendant le gate et contrat de future release documenté, sans prétendre tester INT-129 avant livraison
- [ ] Retour après reboot, refus extérieur 5001, restore isolé des paramètres console et retrait Dockge documentés sans toucher aux volumes Tervo ; pas d'auto-prune
- [ ] Adoption Tervo seulement après gate réussi et autorisation ; échec ou périmètre réduit soumis au développeur, pas clôturé comme besoin satisfait ; note de livraison et cas renseignés

**Technical Notes**
- Layout officiel étudié : `/opt/stacks/<nom>/compose.yaml`,
  `DOCKGE_STACKS_DIR` absolu et identique côté hôte/conteneur.
  Ce n'est pas une preuve d'adoption du fichier actuel
  `deploy/docker-compose.yml` (contexts `../backend`, `../frontend`).
- Aucune copie/symlink fragile, découverte implicite du .env ou réécriture
  des paths n'est retenue sans expérimentation. Une adaptation source
  versionnée peut être nécessaire, à cadrer avant modification d'INT-125.
- Dockge est un manager Compose avec pouvoir d'action, pas un outil
  général de lecture des commandes hôte. La gouvernance des boutons
  start/update/edit ne constitue pas un contrôle de permission technique.
- Le test réel d'interaction avec verrou/release appartient à INT-129,
  puis à la recette INT-111 ; INT-132 ne peut pas le valider par avance.
- Cas TC-INT-132-01/02, non exécutés. Pas de rôle métier ni feature UI Tervo.

---

## INT-126 — Bootstrap sûr du premier administrateur (2 pts)

**User Story**
En tant qu'**administrateur d'exploitation**,
Je veux **créer le premier compte par une commande ponctuelle sécurisée**,
Afin de **valider la production sans seed destructif ni inscription publique**.

**Acceptance Criteria**
- [ ] CLI versionnée, DB explicitement configurée, saisie privée du secret ; rien dans Git/arguments/logs partagés
- [ ] Compte validé et mot de passe haché selon l'identité existante, création transactionnelle
- [ ] Rejeu sans réinitialisation silencieuse du secret/rôle/données d'un compte existant ; conflits explicites
- [ ] Aucun DELETE métier, seed automatique ou endpoint public d'inscription ajouté
- [ ] Création/rejeu/échec/login testés sur DB jetable ; TD-B019 traité pour le bootstrap autorisé et limites de l'ancien seed documentées

**Technical Notes**
- Dépend du modèle identité existant, pas d'une DB de production peuplée.
- Compte Linux, rôle DB et compte applicatif sont distincts. Ne pas modifier
  les comptes existants pour rendre une recette artificiellement verte.
- Sources : module identité, CLI opérateur et procédures. Cas TC-INT-126-01.
  Cette tâche ne démarre pas le registre public historique TD-B002.

---

## INT-127 — PostgreSQL cible et décision de reprise (3 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **préparer une DB dédiée et inventorier les données source**,
Afin de **choisir une reprise sans présumer un ancien conteneur ou rôle**.

**Acceptance Criteria**
- [ ] Patch PostgreSQL supporté retenu, une instance Compose Tervo, healthcheck/volume réels identifiés et aucun port publié
- [ ] Base/rôles/privilèges cadrés et état SQL contrôlé sans supposer `postgres`/`lob` ; rôle applicatif distinct du compte Linux
- [ ] Source réelle (mini-s1 ou aucune donnée) inventoriée : version/schema/volumes/provenance et décision utilisateur enregistrés
- [ ] Plan de reprise ou démarrage vide, préflight et retour arrière établis ; aucun volume existant réinitialisé par facilité
- [ ] Cible/reconstruction testée en isolation, commandes adaptées ; TD-B008/B009/B010 annotés selon la décision

**Technical Notes**
- Dépend d'INT-125. Distinguer les privilèges d'initialisation/migration et
  d'application. Modifier POSTGRES_* ne modifie pas un volume déjà initialisé.
- Prépare la DB et la décision, **pas le transfert réel** : backup/restore
  en INT-128, application du plan en INT-111 ; pas de dépendance circulaire.
  Cette tâche ne clôture pas seule TD-B010.
- Sources : Compose PostgreSQL et procédures SQL/reprise. Cas TC-INT-127-01.

---

## INT-128 — Sauvegarde et restauration cohérentes (5 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **sauvegarder et restaurer DB, uploads et paramètres nécessaires**,
Afin de **prouver la récupération sans détruire la source**.

**Acceptance Criteria**
- [ ] Scripts versionnés dump PG/archive uploads, volumes découverts et cohérence DB/fichiers garantie par une fenêtre contrôlée si nécessaire
- [ ] Archives atomiques, checksum, chiffrement, destination hors VPS explicitement autorisée et rétention ; aucun secret committé
- [ ] Un seul scheduler système (timers/scripts), procédure manuelle possible sans UI ; Dockge ne remplace pas un plan de backup
- [ ] Restore isolé vérifiant relations, photo et octets/empreinte PDF BYTEA, source et volumes réels inchangés
- [ ] Récupération sécurisée `.env`, configuration/état TLS Caddy et données d'auth Dockge ; reconstruction/restore privés documentés sans secrets
- [ ] Preuves enregistrées pour TD-B010/TD-B022 ; limites volume et stockage photo TD-B020 explicites

**Technical Notes**
- Dépend d'INT-125/127. Fixtures autorisées/jetables, jamais seed sur base réelle.
  Dump et archive pris à des instants différents ne sont pas présumés cohérents.
- Scripts futurs dans `deploy/scripts/`, pas considérés déjà livrés.
- La preuve complète de restore utilise un jeu isolé avant INT-111 ;
  la planification/récupération du déploiement réel sera recontrôlée en INT-111.
- Cas TC-INT-111-09, propriétaire INT-128 ; clôture TD-B010 en INT-111
  après application réelle de la décision de reprise.

---

## INT-129 — Release traçable et rollback contrôlé (5 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **une commande de release commune au manuel et à la CI**,
Afin de **maîtriser artefacts, migrations, disponibilité et retour arrière**.

**Acceptance Criteria**
- [ ] Commande versionnée avec Compose/.env explicites, services Compose, verrou de déploiement et SHA enregistré ; interaction réelle avec Dockge testée (fenêtre d'administration gelée/absence d'action en cours), pas de seconde orchestration ni simple promesse de RBAC
- [ ] Build/version des images une fois, backup/maintenance avant migration si nécessaire, migration avant exposition, démarrage/attente puis GET readiness/smoke
- [ ] Échec propagé pour build/migration/readiness/smoke ; conteneur Up ou OpenAPI seul ne rend pas la release verte
- [ ] Images précédentes conservées sans prune immédiat, rollback vers artefact exact testé sans HEAD détaché laissé sur VPS
- [ ] Schéma compatible vérifié, roll-forward/procédure contrôlée sinon ; aucun downgrade/restore/`down -v`/nettoyage de volumes implicite
- [ ] Échec/rollback testés en isolation, commandes de secours et note de livraison documentées

**Technical Notes**
- Dépend d'INT-125/127/128. Script testé sur stack jetable avant sa première
  exécution réelle en INT-111 ; pas besoin de pipeline GitHub pour le clore.
- Sources : `deploy/scripts/`, versions locales, migrations et rollback.
  Rebuild ancien n'est pas ancien artefact.
- Cas TC-INT-111-10, propriétaire INT-129. La CI INT-130 appellera ce script.

---

## INT-130 — CI/CD de production sécurisée (3 pts)

**User Story**
En tant que **mainteneur**,
Je veux **automatiser une release déjà validée manuellement**,
Afin de **déployer les commits testés sans second chemin de déploiement**.

**Acceptance Criteria**
- [ ] INT-111 manuelle validée et INT-129 livrée ; workflow appelle cette commande, pas une seconde orchestration
- [ ] Clé CI distincte de la clé personnelle, compte/permissions documentés, Git lecture si privé ; Docker root-equivalent traité, pas de `NOPASSWD: ALL` par facilité
- [ ] Empreinte SSH vérifiée indépendamment et contrôlée par workflow, secrets GitHub scoped et autorisation production documentée
- [ ] CI tests/build Vue de vérification, `git pull --ff-only`, puis release ; ni image CI jetée, ni nom de conteneur dur, ni prune des images de secours
- [ ] `DEPLOY_ENABLED` activé après recette manuelle seulement, push autorisé et déploiement réellement exécuté/observé avec SHA/smoke
- [ ] Échecs remontés, désactivation de l'automatisation et notes/todos/cas à jour

**Technical Notes**
- Dépend d'INT-111/129 ; la CI n'est pas un prérequis de la recette manuelle.
- Sources : workflow, identité SSH/Git et configuration GitHub. Ne pas
  réutiliser la clé personnelle de l'agent pour les credentials CI.
- Cas TC-INT-111-06, propriétaire INT-130. CI verte avec Deploy sauté ne
  valide pas cette tâche ; anciens runs verts restent historiques.

---

## INT-112 — Doc entretien (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **une fiche d'architecture et un Q/R entretien**,
Afin de **présenter le projet avec crédibilité (profil backend Java/Go)**.

**Acceptance Criteria**
- [ ] Fiche archi : chaîne Client→Site→Equipment→Intervention + migration
- [ ] Q/R : pourquoi la migration est transverse, pourquoi 3 zones, pourquoi transactions par batch
- [ ] Périmètre crédibilité : ne pas survendre Vue/TS, GH Actions, VPS, Caddy/Dockge ; 1Panel présenté comme évaluation historique
- [ ] Fichiers : `notes/interview/`
- [ ] Fiche d’une page présentable en 2–3 minutes : flux réseau, couches Router → Service → Repository, modèle V2, pipeline d’import et déploiement ; choix Caddy natif, console Dockge privée, Compose et PostgreSQL justifiés sans annoncer des tests non exécutés
- [ ] Q/R couvrant healthchecks, idempotence, fuzzy matching, deux passes, transactions, interventions orphelines, CI/CD, ports, versions, modélisation V2 et sécurité VPS ; réponses de 3–5 phrases maximum
- [ ] Seuils 95/80 présentés comme paramètres à calibrer ; réalisations distinguées du backlog et compétences présentées sans survente
- [ ] Formulation adaptée pour chaque limite de compétence et pitch de 5–6 phrases ; livrables `architecture-presentation.md`, `questions-reponses.md`, `perimetre-credibilite.md`

**Technical Notes**
- Le différenciateur = la migration Excel (pandas, fuzzy, 2 passes, transactions)

---

## Cas de test

Voir [test-cases.json](test-cases.json).

Dix-neuf scénarios : dix hérités (avec `legacy_id` conservés), trois issus
de la revue production, deux pour le bootstrap admin/la décision DB,
quatre nouveaux pour Caddy/Dockge (INT-131/132).
Le propriétaire `task` est aligné sur le découpage ; les IDs historiques
ne sont pas renommés et `origin_task` trace les transferts.
TC-INT-111-01 conserve les observations partielles du socle VPS,
TC-INT-111-02 les validations historiques 1Panel/OpenResty,
TC-INT-111-03/08 la recette locale INT-125. Leurs résultats ne sont pas
réattribués à Caddy/Dockge ; tous les cas INT-131/132 restent non exécutés.
Le planning ne vaut pas implémentation ou validation de déploiement.
