# VPS Tervo — point d'entrée

## À lire maintenant

**[Tervo : release, contrôles, admin et publication](05-tervo-release-et-exploitation.md)**

C'est le parcours opérateur actuel. Il explique ce qui se passe entre le
checkout Git et une application utilisable, sans rejouer l'installation du
serveur. [Caddy](04-transition-caddy.md) traite séparément du proxy.

| Je veux… | Lire |
|---|---|
| Voir ce qui fonctionne et ce qui reste | L'état ci-dessous, puis le [journal INT-111](../../sprint7.6/INT-111-deploiement-vps.md) |
| Vérifier les conteneurs, ports, HTTP et la release active | [Parcours opérateur](05-tervo-release-et-exploitation.md) |
| Comprendre le proxy public et HTTPS actif | [Caddy](04-transition-caddy.md) |
| Comprendre SSH, Compose, SQL et la récupération des données | [Cours, dans l'ordre 01 → 06](../../../../deploy/cours/README.md) |

### État en bref

- Caddy est actif et activé au démarrage ; HTTPS et redirections des deux domaines vérifiés.
- 1Panel désinstallé ; conteneur et image OpenResty supprimés.
- Dockge privé est installé ; login par tunnel et logs de démo confirmés.
- INT-111 : release `291f7ead2482-ca71c575091e` réussie sur la stack `tervo` ;
  PostgreSQL sans port hôte, backend/frontend healthy sur `127.0.0.1:8000/3000`.
- Création de l'admin applicatif confirmée par l'opérateur ; aucun seed.
- Réception de `admin@tervoapp.com` et `contact@tervoapp.com` confirmée
  via Cloudflare Email Routing. Cela ne valide pas les DNS web.
- DNS web direct et recette navigateur confirmés. Snapshot mini-s1 `03aca082`
  enregistré et récupéré ; SQL/relations/photos restaurés en cible isolée sur
  le VPS, cible arrêtée. Démo avec sauvegardes manuelles, aucun timer.
- Reboot réel, retour des services, ports et certificats persistants vérifiés.
  Nettoyage ciblé exécuté par l'opérateur le 24 octobre 2026 : stack de recette,
  ses volumes/réseaux et la cible de restauration supprimés ; `tervo`, Dockge,
  les images et le dépôt restic conservés. Sorties dans la
  [section 23 du journal](../../sprint7.6/INT-111-deploiement-vps.md#23-nettoyage-exécuté--sorties-reçues-le-24-octobre-2026).
  Sauvegardes automatiques hors VPS toujours reportées par TD-B024. INT-130
  livrée : release par CI observée (run `40083288592` tentative 2, release
  `fd3a42c87e37-6cc4ef39fc49`), coupe-circuit `DEPLOY_ENABLED` ; le bilan de
  sprint vient avec INT-112.
- INT-131 terminée ; INT-132 a livré la console privée, sans adoption de la
  stack Tervo. Le gate Git/CLI/Dockge a été transféré à INT-129 et validé en recette.
  [Journal opérateur et cours de déploiement INT-129](../../sprint7.6/INT-129/README.md).

## Références

- [Planning du sprint 7.6](../../../../docs/stages/stage7/sprint7.6/tasks.md)
- [Dockge privé — état et accès](../../../../deploy/dockge/README.md)
- [Décisions Caddy / Dockge](../../sprint7.6/INT-131-132-cadrage-caddy-dockge.md)
- [Stack Tervo — INT-125](../../sprint7.6/INT-125-stack-reproductible.md)
- [Cloudflare : DNS, tunnel et réception email](../../../../deploy/cours/03-reseau-caddy-dockge.md)

## Historique — pas la procédure actuelle

Ces notes conservent les travaux précédents. Elles ne décrivent pas toutes
l'état présent et ne doivent pas être exécutées comme une recette Caddy :

- [01 — Inventaire et accès SSH](01-inventaire-et-acces-ssh.md)
- [02 — Sécurité du système](02-preparation-securite-systeme.md)
- [03 — Ancien panneau 1Panel / OpenResty](03-preparation-1panel-prive.md)
- [Livraison historique INT-124](../../sprint7.6/INT-124-1panel-openresty-prives.md)
