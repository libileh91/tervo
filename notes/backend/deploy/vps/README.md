# VPS Tervo — point d'entrée

## À lire maintenant

**[Caddy : état actuel et suite](04-transition-caddy.md)**

C'est le guide de reprise : état du serveur, commandes utiles et prochaines étapes.
Il n'est pas nécessaire de relire les anciennes sessions pour continuer.

### État en bref

- Caddy est actif et activé au démarrage, en HTTP seul.
- 1Panel désinstallé ; conteneur et image OpenResty supprimés.
- Dockge privé est installé ; login par tunnel et logs de démo confirmés.
- L'application, PostgreSQL Tervo et HTTPS ne sont pas encore livrés sur le VPS.
- INT-131 terminée ; INT-132 limitée à la console privée, adoption Tervo reportée à INT-129.

## Références

- [Planning du sprint 7.6](../../../../docs/stages/stage7/sprint7.6/tasks.md)
- [Dockge privé — état et accès](../../../../deploy/dockge/README.md)
- [Décisions Caddy / Dockge](../../sprint7.6/INT-131-132-cadrage-caddy-dockge.md)
- [Stack Tervo — INT-125](../../sprint7.6/INT-125-stack-reproductible.md)

## Historique — pas la procédure actuelle

Ces notes conservent les travaux précédents. Elles ne décrivent pas toutes
l'état présent et ne doivent pas être exécutées comme une recette Caddy :

- [01 — Inventaire et accès SSH](01-inventaire-et-acces-ssh.md)
- [02 — Sécurité du système](02-preparation-securite-systeme.md)
- [03 — Ancien panneau 1Panel / OpenResty](03-preparation-1panel-prive.md)
- [Livraison historique INT-124](../../sprint7.6/INT-124-1panel-openresty-prives.md)
