# INT-129 — Journal de recette et cours de déploiement

Deux usages, deux parcours :

- **Retrouver ce qui a été fait** : lire le journal. Chaque étape présente
  les commandes, les sorties reçues, puis le tableau but/usage/interprétation.
- **Comprendre et préparer l'entretien** : lire les
  [cours de déploiement](../../../../deploy/cours/README.md) dans l'ordre.
  Les exemples pédagogiques ne sont pas présentés comme des exécutions réelles.

## État à la dernière preuve reçue

Les recettes fonctionnelles INT-129 sont terminées : releases A/B, backup,
rollback exact, garde-fous, échecs contrôlés et compatibilité Dockge validés.
**INT-129 clôturée sur les preuves fonctionnelles et la confirmation opérateur
du nettoyage.** Dockge vert et Caddy bootstrap HTTP 200 confirmés ; sorties
détaillées de suppression/archivage non consignées, pas de contrôle indépendant.
Aucun nouveau test ni aucune opération VPS n'est lancé pour écrire ces notes.

La recette n'est pas la mise en service publique INT-111. Les backups VPS
contiennent des paramètres hôte réels et restent privés ; la DB et les uploads
de la recette sont fictifs.

## 1. Journal : commandes → résultats → explications

| Page | Contenu |
|---|---|
| [01 — Accès et préparation](journal/01-acces-et-preparation.md) | Clé temporaire, SSH/sudo, inventaire, transfert vérifié, préparation root |
| [02 — Releases, sauvegarde, rollback](journal/02-releases-sauvegarde-rollback.md) | Création env privé, release A, données fictives, B, vérification du backup et retour A |
| [03 — Garde-fous et échecs](journal/03-garde-fous-et-echecs.md) | Blocs complets de refus verrou/schéma et échecs migration/build/readiness/smoke |
| [04 — Gate Dockge](journal/04-gate-dockge.md) | Différence des modèles, diagnostic sans secrets, sonde bind, comparaison qualifiée, logs/Stop/Start UI et données |
| [05 — État et limites](journal/05-etat-et-limites.md) | Clôture, nettoyage déclaré, contrôle Caddy, historique local et limites de preuve |

### Convention de fidélité

Le journal reproduit les blocs d'exploitation VPS de cette conversation et
les retours disponibles, y compris les refus et étapes intermédiaires.
Lorsqu'un bloc identique a été rejoué, sa réexécution et son résultat sont
signalés sans inventer une autre commande. Les prompts et chevrons de citation
ne sont pas des commandes supplémentaires.

Les `...` présents dans certaines sorties viennent du retour de l'opérateur :
on ne reconstitue pas les lignes absentes. Les journaux privés complets,
secrets, fichiers `.env` et configurations résolues ne sont pas publiés.
Les recherches de fichiers, éditions de documentation et validations locales
de Markdown ne sont pas des étapes d'exploitation du VPS.

L'historique local antérieur est identifié comme résumé de preuves, pas comme
un faux verbatim exhaustif. Les notes historiques de préparation du VPS
restent accessibles ci-dessous.
Le [journal 05](journal/05-etat-et-limites.md) indique aussi comment retrouver
la version initiale committée dans Git, antérieure aux preuves VPS.

## 2. Cours progressif : comprendre avant de réciter

| Ordre | Chapitre | À savoir expliquer après lecture |
|---|---|---|
| 1 | [Poste local, VPS, SSH, sudo, shell](../../../../deploy/cours/01-du-poste-local-au-vps.md) | Où une commande tourne, avec quels droits, comment lire permissions et codes de sortie |
| 2 | [Images, conteneurs et Compose](../../../../deploy/cours/02-images-conteneurs-compose.md) | Build/cache, artefact exact, volume, bind, identité de projet, disponibilité |
| 3 | [Réseau, Caddy et Dockge](../../../../deploy/cours/03-reseau-caddy-dockge.md) | Trajet HTTP, loopback, tunnel SSH, proxy versus console, historique des choix |
| 4 | [PostgreSQL, migrations et sauvegardes](../../../../deploy/cours/04-postgresql-migrations-sauvegardes.md) | Initialisation versus migration, rôles SQL, cohérence DB/fichiers, backup versus restore |
| 5 | [Release, rollback et entretien](../../../../deploy/cours/05-release-rollback-entretien.md) | Parcours complet, records, erreurs et secours, réconciliation, limites et pitch crédible |

Chaque chapitre comporte des commandes expliquées, des pièges, des questions
d'entretien et des exercices de compréhension. Ces exercices sont facultatifs :
ils n'ajoutent aucun travail requis pour clôturer INT-129.

## 3. Références du déploiement déjà documenté

Le cours explique le parcours global jusqu'à la recette actuelle ; il ne
réécrit pas les anciennes opérations comme si elles avaient été faites dans
INT-129. Pour les historiques détaillés :

- [Inventaire du VPS et accès SSH](../../deploy/vps/01-inventaire-et-acces-ssh.md).
- [Préparation et sécurité système](../../deploy/vps/02-preparation-securite-systeme.md).
- [Évaluation historique 1Panel/OpenResty](../../deploy/vps/03-preparation-1panel-prive.md).
- [Transition vers Caddy](../../deploy/vps/04-transition-caddy.md).
- [Mini-s1 et Cloudflare Tunnel : environnement historique distinct](../../deploy/cloudflare-tunnel-deploy.md).
- [INT-125 : stack reproductible](../INT-125-stack-reproductible.md).
- [INT-126 : bootstrap admin](../INT-126-bootstrap-admin.md).
- [INT-127 : PostgreSQL et privilèges](../INT-127-postgresql-cible.md).
- [INT-128 : commandes complètes de backup/restore](../INT-128-sauvegarde-restauration.md).
- [INT-131/132 : décisions Caddy/Dockge](../INT-131-132-cadrage-caddy-dockge.md).
- [Critères du sprint](../../../../docs/stages/stage7/sprint7.6/tasks.md#L378) et
  [cas de test](../../../../docs/stages/stage7/sprint7.6/test-cases.json).

## 4. Ne pas confondre les niveaux de preuve

| Énoncé | État correct |
|---|---|
| CLI et Dockge compatibles | Qualifiés sur la configuration/version testée, avec traitement ciblé d'une omission JSON prouvée |
| Backup VPS | Capture et checksums validés ; paramètres hôte privés réels |
| Reprise après sinistre complète | Non démontrée par INT-129 |
| Application publique avec TLS et login métier | Réalisée en INT-111 après cette recette ; non prouvée par INT-129 elle-même |
| CI/CD de production | Livrée par INT-130 le 24 octobre 2026 ; non exécutée par cette recette |
| Nettoyage de la recette principale | Déclaré exécuté par l'opérateur ; santé Caddy/Dockge confirmée, détail terminal non consigné. Retrait effectif prouvé plus tard par la sortie du nettoyage INT-111 (section 23 du journal) |
| Nettoyage de la sonde bind | Confirmé dans le journal 04 |

En entretien, le bon niveau de précision est : **« voici ce que j'ai construit,
voici comment je l'ai vérifié, voici ce que je ne prétends pas avoir validé »**.
