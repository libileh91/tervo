# Tervo — Réalisation guidée du déploiement VPS

Ce dossier rassemble les **notes de réalisation pas à pas** du VPS, avec les
commandes exécutées, leurs explications, les erreurs et les preuves obtenues.
Il complète les procédures de [déploiement](../README.md), sans créer un second
DAT ni remplacer le [planning du sprint 7.6](../../../../docs/stages/stage7/sprint7.6/tasks.md).
Le bilan de livraison du sprint restera dans `notes/backend/sprint7.6/`.

## Notes disponibles

| Note | Contenu | État |
|---|---|---|
| [01 — Inventaire et accès SSH](01-inventaire-et-acces-ssh.md) | Choix du VPS, inventaire Debian, compte `tervo`, clés, `sudo`, durcissement SSH et correction client/serveur | Accès SSH confirmé ; sécurité système poursuivie dans la note 02 |
| [02 — Préparation de la sécurité système](02-preparation-securite-systeme.md) | PATH administrateur, Docker, APT, reboot et outils de sécurité | UFW actif, jail SSH chargée, noyau Security actif ; mises à jour quotidiennes configurées et dry-run vérifié |
| [03 — Préparer 1Panel privé](03-preparation-1panel-prive.md) | Préparation, incidents firewall/502, reprise privée et installation OpenResty | Bind loopback maintenu après restart, services enabled ; OpenResty installé, mode réel et recette proxy en attente |

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
| Docker et Compose | Versions et service actif confirmés ; conteneur OpenResty actif, mode réseau encore à inspecter |
| 1Panel | Bind 127.0.0.1:7410, tunnel sans 502 confirmé, isolation conservée après restart ; core/agent enabled, aucun reboot après cette activation |
| OpenResty et HTTPS | OpenResty installé, 80/443 en écoute et HTTP public 200 ; mode réel/configuration/recette upstream en attente, aucun certificat Tervo validé |
| Déploiement Tervo, secrets et données | Pas encore réalisé sur ce VPS |
| Sauvegarde/restauration et automatisation du déploiement | À préparer et valider |

**Règle de travail :** une étape, ses résultats, puis la suivante. Ne pas
enchaîner ces procédures comme un script global. Les notes distinguent une
commande proposée d'un résultat effectivement reçu ; une configuration de
sécurité ne vaut pas preuve de disponibilité de l'application.
