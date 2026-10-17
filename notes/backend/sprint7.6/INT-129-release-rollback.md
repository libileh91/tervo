# INT-129 — Journal complet de la recette VPS et cours de déploiement

La note est désormais organisée en deux parcours complémentaires :
**les commandes et leurs résultats**, puis **les explications progressives
pour comprendre et préparer l'entretien**.

**[Ouvrir le sommaire détaillé](INT-129/README.md)**
**Cours regroupés dans le dossier deploy :**
[Linux/SSH](../../../deploy/cours/01-du-poste-local-au-vps.md),
[Docker/Compose](../../../deploy/cours/02-images-conteneurs-compose.md),
[réseau/Caddy/Dockge](../../../deploy/cours/03-reseau-caddy-dockge.md),
[PostgreSQL/backups](../../../deploy/cours/04-postgresql-migrations-sauvegardes.md),
[release/entretien](../../../deploy/cours/05-release-rollback-entretien.md).

## 1. Commandes lancées, résultats reçus, puis tableaux explicatifs

Chaque étape du journal suit cet ordre. Les blocs VPS sont reproduits avec
leurs variables, options et contrôles ; les sorties reçues, y compris les
échecs, sont placées juste après. Les sorties abrégées par l'opérateur restent
signalées comme telles : aucune ligne manquante n'est inventée.

| Journal | Contenu |
|---|---|
| [01 — Accès et préparation](INT-129/journal/01-acces-et-preparation.md) | SSH, clé temporaire, sudo, inventaire, archive/transfert, installation de la copie |
| [02 — Release A, upgrade B, sauvegarde et rollback](INT-129/journal/02-releases-sauvegarde-rollback.md) | Blocs complets, données fictives, sorties et IDs d'images |
| [03 — Garde-fous et échecs](INT-129/journal/03-garde-fous-et-echecs.md) | Verrou, schéma, migration, build, readiness, smoke et réconciliation |
| [04 — Gate Dockge](INT-129/journal/04-gate-dockge.md) | Comparaison bloquée, diagnostic, sonde bind, comparaison qualifiée, logs et Stop/Start UI |
| [05 — État final et limites](INT-129/journal/05-etat-et-limites.md) | Clôture, nettoyage déclaré par l'opérateur, contrôle Caddy et limites de traçabilité |

## 2. Cours débutant, tutoriels et entretien

| Ordre | Chapitre |
|---|---|
| 1 | [Du poste local au VPS : SSH, sudo, permissions et shell](../../../deploy/cours/01-du-poste-local-au-vps.md) |
| 2 | [Images, conteneurs, volumes et Docker Compose](../../../deploy/cours/02-images-conteneurs-compose.md) |
| 3 | [Réseau, reverse proxy, Caddy et Dockge](../../../deploy/cours/03-reseau-caddy-dockge.md) |
| 4 | [PostgreSQL, migrations, privilèges et sauvegardes](../../../deploy/cours/04-postgresql-migrations-sauvegardes.md) |
| 5 | [Release traçable, rollback, CI/CD et préparation à l'entretien](../../../deploy/cours/05-release-rollback-entretien.md) |

Les cours expliquent les notions avant de demander de lire du code. Ils
contiennent des commandes situées dans leur contexte, des tableaux d'options,
des retours attendus, des pièges, des questions/réponses et des exercices
facultatifs. Un exemple pédagogique n'est jamais présenté comme une capture
réelle de production.

## État de la tâche

- Recettes fonctionnelles et gate Dockge : **validés** sur les preuves décrites.
- Nettoyage de la recette VPS : **déclaré exécuté par l'opérateur** ; Dockge
  vert et Caddy bootstrap HTTP 200 confirmés. Sortie détaillée de nettoyage
  non consignée, sans contrôle indépendant. Livraison regroupée dans INT-129.
- Aucun nouveau test ni accès VPS effectué pour cette refonte documentaire.
- Mise en service publique INT-111, CI/CD INT-130, restauration réelle des
  paramètres hôte et sauvegarde régulière hors VPS : **non validées par INT-129**.
- `--recover-from` : hors parcours exercé.

Les informations techniques ont été réparties entre le journal et les cours.
La version initiale committée reste consultable dans Git ; le journal 05
indique comment la retrouver et distingue ses preuves locales des recettes VPS.
Les historiques SSH/sécurité/1Panel/Caddy du projet sont reliés dans le sommaire,
sans les réattribuer à INT-129.
