# Tervo — Réalisation guidée du déploiement VPS

Ce dossier rassemble les **notes de réalisation pas à pas** du VPS, avec les
commandes exécutées, leurs explications, les erreurs et les preuves obtenues.
Il complète les procédures de [déploiement](../README.md), sans créer un second
DAT ni remplacer le [planning du sprint 7.6](../../../../docs/stages/stage7/sprint7.6/tasks.md).
Le bilan de livraison du sprint restera dans `notes/backend/sprint7.6/`.

**Nouvelle cible approuvée :** Caddy natif et Dockge privé par tunnel.
Les tâches INT-131/132 sont cadrées, pas exécutées ; les lignes
1Panel/OpenResty ci-dessous conservent le dernier état vérifié.

## Notes disponibles

| Note | Contenu | État |
|---|---|---|
| [01 — Inventaire et accès SSH](01-inventaire-et-acces-ssh.md) | Choix du VPS, inventaire Debian, compte `tervo`, clés, `sudo`, durcissement SSH et correction client/serveur | Accès SSH confirmé ; sécurité système poursuivie dans la note 02 |
| [02 — Préparation de la sécurité système](02-preparation-securite-systeme.md) | PATH administrateur, Docker, APT, reboot et outils de sécurité | UFW actif, jail SSH chargée, noyau Security actif ; mises à jour quotidiennes configurées et dry-run vérifié |
| [03 — Préparer 1Panel privé](03-preparation-1panel-prive.md) | Préparation, incidents firewall/502, reprise privée et installation OpenResty | INT-124 terminée : runtime, routage, nettoyage, reboot et navigateur validés |
| [Livraison INT-124](../../sprint7.6/INT-124-1panel-openresty-prives.md) | Explications techniques, preuves, maintenance et confinement/retour arrière | Livrée ; aucune mise à jour ou restauration complète prétendue |
| [Livraison INT-125](../../sprint7.6/INT-125-stack-reproductible.md) | Packaging, environnement et readiness DB, recette Docker locale | Validée localement ; aucun changement de stack sur le VPS |
| [Cadrage INT-131/132](../../sprint7.6/INT-131-132-cadrage-caddy-dockge.md) | Caddy natif, transition réversible et Dockge privé/gate | Décision approuvée, aucune installation |

Depuis le découpage du chantier, la note 03 accompagne **INT-124**.
Les notes 01/02 conservent les preuves système acquises dans INT-111.
Les autres lots (stack, bootstrap, DB, backup, release, CI/CD) ont chacun
leur tâche INT-125 à INT-130 ; une préparation n'en valide pas la livraison.

## Parcours et points d'arrêt

| Étape | État du parcours documenté |
|---|---|
| Choix et inventaire du VPS | Confirmés par les informations et sorties fournies |
| Compte non-root, accès par clé et `sudo` | Confirmés par une nouvelle connexion |
| Refus des connexions sans clé | Confirmé |
| Configuration du client SSH | Corrigée et validée |
| Pare-feu, fail2ban et mises à jour automatiques | UFW actif, jail SSH chargée ; noyau Security actif, contrôles APT restaurés ; automatisation configurée et dry-run validé, pare-feu fournisseur inconnu |
| Docker et Compose | Versions et service actif confirmés ; conteneur OpenResty actif en mode host avec restart always |
| 1Panel | Bind 127.0.0.1:7410 et UFW conservés après reboot, services actifs ; panneau navigateur confirmé sans 502 via tunnel relancé |
| Caddy / Dockge cible | Non installés/testés par le cadrage ; administration Dockge future 127.0.0.1:5001 par tunnel, aucune route publique |
| OpenResty et HTTPS | OpenResty host, nginx -t/reload et upstream loopback validés localement et sur IPv4 publique ; recette nettoyée, aucun certificat Tervo validé |
| Images/configuration Tervo | INT-125 validée sur export Git et stack Docker jetable locale ; ne vaut pas artefacts construits sur le VPS |
| Déploiement Tervo, secrets et données | Pas encore réalisé sur ce VPS |
| Sauvegarde/restauration et automatisation du déploiement | À préparer et valider |

**Règle de travail :** une étape, ses résultats, puis la suivante. Ne pas
enchaîner ces procédures comme un script global. Les notes distinguent une
commande proposée d'un résultat effectivement reçu ; une configuration de
sécurité ne vaut pas preuve de disponibilité de l'application.
