# VPS Tervo — synthèse du choix Caddy / Dockge

Cette note conserve le résultat de la réflexion initiale, **pas une RFC encore
ouverte ni un second DAT**. Références : [planning 7.6](../docs/stages/stage7/sprint7.6/tasks.md),
[DAT](../docs/DAT/new/00-sommaire.md) et [état du VPS](backend/deploy/vps/README.md).

## Choix retenu

| Responsabilité | Outil |
|---|---|
| Entrée HTTP/HTTPS | Caddy natif sous systemd |
| Application et PostgreSQL | Docker Compose défini dans Git |
| Console Compose | Dockge privé, tunnel SSH et login |
| Système et secours | SSH |

Caddy et 1Panel ne sont pas deux produits équivalents : Caddy est un serveur
web/proxy ; 1Panel est un panneau général utilisant OpenResty. Le choix retenu
sépare les responsabilités plutôt que de rechercher une GUI unique.

Un proxy natif peut joindre les ports loopback des applications. Un proxy
conteneurisé doit avoir une connectivité explicite : `127.0.0.1` désigne son
propre conteneur, sauf mode host. Les IP statiques des anciennes recettes
1Panel ne sont donc pas une obligation pour Caddy.

Dockge réintroduit une console administrative ciblée, **pas un accès read-only** :
le socket Docker lui donne des privilèges équivalents à root. Git reste
autoritaire ; sauvegardes, restauration et release ne sont pas remplacées
par les boutons de l'interface.

## État réel et limites

- INT-131 : Caddy HTTP actif ; 1Panel/OpenResty retirés après retour arrière testé.
- INT-132 : Dockge privé installé ; login et logs fictifs vérifiés, démo nettoyée.
  **Aucune adoption de la stack Tervo** : gate chemins/env/projet/volumes en INT-129.
- INT-126 : bootstrap admin testé localement sur SQLite ; pas d'admin VPS créé.
- Application, PostgreSQL Tervo, TLS public et release réelle restent à livrer.

## Règles à garder

Application sur loopback, PostgreSQL sans port publié, aucune route Caddy vers
Dockge. Pas de seed production ni de stack copiée avec un environnement implicite.
La migration Excel reste le différenciateur du projet ; le déploiement n'est
pas présenté comme une architecture distribuée ou une chaîne CI/CD déjà validée.
