# INT-131/132 — Cadrage Caddy natif et Dockge privé

**Décision approuvée, implémentation non démarrée.** Ce document traduit
l'arbitrage de l'utilisateur dans le DAT et le sprint 7.6. Il ne prouve
ni installation, ni bascule réseau, ni adoption Dockge de Tervo.

Références : [DAT architecture](../../../docs/DAT/new/02-techniques/01-architecture.md),
[sécurité](../../../docs/DAT/new/02-techniques/04-securite.md),
[planning](../../../docs/stages/stage7/sprint7.6/tasks.md),
[cas](../../../docs/stages/stage7/sprint7.6/test-cases.json).

## 1. Décision et non-décisions

| Sujet | Décision |
|---|---|
| Proxy public cible | Caddy natif sous systemd, unique propriétaire 80/443 |
| Console privée | Dockge sur 127.0.0.1:5001, tunnel SSH et login |
| Applications | Git/Docker Compose, publications loopback INT-125 conservées |
| Domaines | `tervoapp.com` et `api.tervoapp.com`, API `/api/v1` |
| CI/build | CI vérifie, VPS construit ; pas de GHCR ajouté |
| Backups/scheduler | Scripts versionnés et scheduler système unique à livrer |
| Projet/identité | Tervo inchangé, pas de changement métier |

Ce choix vise une architecture simple à expliquer en entretien, pas une
preuve de performance ou de sécurité absolue. Le différenciateur reste
la migration Excel, pas la maîtrise supposée des outils d'administration.

La GUI Dockge est retenue pour faciliter la consultation de logs et de
sorties Compose. Elle peut aussi modifier les stacks : la traiter comme
un accès administrateur, pas comme une visionneuse techniquement read-only.
Ajouter Dockge réintroduit donc une interface web privilégiée : ce choix
ne permet plus de dire « Caddy supprime toute console administrative ».
Le gain visé est une responsabilité plus ciblée sur Compose, pas une
garantie de moindre privilège ou de meilleure sécurité sans tests.

## 2. Conserver les preuves sans annoncer une migration faite

Dernier état documenté :
- INT-124 : 1Panel privé, OpenResty **host**, proxy/reload/reboot validés ;
- INT-125 : packaging et disponibilité validés sur stack locale jetable ;
- aucune application/DB/certificat Tervo déployés par ces validations ;
- aucun Caddy/Dockge installé ou testé dans ce cadrage.

OpenResty sait déjà joindre le loopback. La bascule ne corrige donc pas
un problème de réseau encore ouvert : elle change la responsabilité du
proxy et le mode d'exploitation. Les cases cochées et les résultats
historiques ne sont pas effacés ni attribués au nouveau proxy.

## 3. INT-131 : transition sans perte et sans collision

1. Inventorier live avant changement, conserver les paramètres privés
   utiles du panneau/proxy et les politiques de restart.
2. Préparer Caddy vérifié, empêchant un démarrage package surprise sur
   les ports actuellement détenus par OpenResty.
3. Valider deux profils : bootstrap actif HTTP seulement, automatic
   HTTPS désactivé et sans vrais hostnames ; production conservé inactif
   jusqu'à INT-111. Tester une cible jetable et prouver qu'aucune tentative
   ACME ni état de certificat Tervo n'est créé pendant INT-131.
4. Faire autoriser la bascule ; neutraliser l'ancien proxy **et son
   redémarrage automatique Docker**, ainsi que core/agent au boot.
5. Contrôler un seul proxy public selon profil (:80 bootstrap, 80/443
   en production), admin Caddy locale et aucune administration publique,
   avec profil TCP h1/h2 initial.
6. Tester reload, extérieur, reboot et retour à l'état ancien sans
   suppression des données du panneau ni réinstallation.

L'émission/renouvellement TLS des domaines réels attend la recette
publique INT-111. Une configuration cible versionnée ne doit pas être
confondue avec une configuration active validée.

Caddy a une API admin locale (2019 par défaut) ; pas une absence totale
de surface d'administration. HTTP/3 ajouterait UDP443 : ne pas ouvrir
ce port sans nouvelle exception approuvée.

## 4. INT-132 : ce que Dockge apporte et ce qu'il n'apporte pas

Sources officielles étudiées :
[Dockge README](https://github.com/louislam/dockge),
[Compose officiel](https://github.com/louislam/dockge/blob/master/compose.yaml),
[release 1.5.0](https://github.com/louislam/dockge/releases/tag/1.5.0).

La version 1.5.0 est une référence documentaire à revérifier à
l'implémentation, pas une image déjà téléchargée/pinnée/testée.
Le port interne documenté est 5001. La console principale est désactivée
par défaut dans cette version ; son activation nécessite une option
explicite après authentification et protection.

Dockge peut gérer Compose, éditer, démarrer/arrêter, mettre à jour, lire
logs et sorties et proposer un terminal. Cela ne remplace pas :
- SSH pour le système et le secours ;
- systemd/journald pour Caddy et les services hôte ;
- le plan de backup et les tests de restauration ;
- la commande de release/rollback ni un monitoring extérieur.

Le socket Docker donne un pouvoir root-equivalent sur le daemon.
Monter le socket `:ro` ne rend pas son API read-only. Un compte qui voit
la console ne doit pas être décrit comme isolé des commandes de
modification faute de RBAC démontré. Ne pas activer `disableAuth`.

**Pas de domaine public Dockge, pas de reverse proxy Caddy vers la console.**
Le parcours est navigateur local → tunnel SSH → 127.0.0.1:5001 → login.

## 5. Gate d'adoption : ne pas inventer une compatibilité

Le modèle officiel utilise :

```text
/opt/stacks/<nom>/compose.yaml
DOCKGE_STACKS_DIR absolu, même chemin hôte/conteneur
```

Le projet livré utilise :

```text
deploy/docker-compose.yml
contexts ../backend et ../frontend
--env-file explicite, exports ambiants refusés
nom projet/volumes et labels à conserver
```

Déplacer ou copier le YAML change potentiellement les chemins, le
répertoire de projet, la résolution de `.env`, les volumes et les
arguments de build. Un symlink « pratique » ne prouve pas ces invariants.

La tâche commence donc sur une stack jetable : démontrer une adoption
source versionnée et reproductible, comparer la configuration effective
en mémoire sans afficher les secrets, puis tester logs et commandes.
La méthode n'est pas décidée ni revendiquée fonctionnelle ici.

Si le gate exige une adaptation d'INT-125, elle doit être versionnée et
retestée avant exploitation Tervo. Si le gate échoue, demander un arbitrage ;
ne pas présenter une démo indépendante comme l'adoption de Tervo réussie.

## 6. Gouvernance : une console n'est pas une seconde source de vérité

Git reste la définition autoritaire. Pas de copie indépendante du
Compose, d'édition UI non tracée ou de rebuild avec un autre checkout.
La convention de consultation ne réduit pas les privilèges techniques.

INT-129 devra assurer l'exclusivité des opérations : Dockge ne doit pas
concurrencer migration, restart ou rollback. Un bouton de la GUI qui
contourne la commande de release n'est pas un nouveau workflow validé.
Une action de secours doit être identifiée, tracée et réconciliée.
INT-132 peut prouver l'absence d'édition/opération concurrente dans son
gate et définir cette gouvernance, pas tester une commande INT-129 encore
inexistante. Le test du verrou réel et du gel de l'administration pendant
release appartiendra à INT-129, avec recontrôle en INT-111.

Les backups devront couvrir Caddy (configuration/état TLS), Dockge
(auth/configuration) et les données Tervo. Aucune commande de backup
n'est ajoutée ou prétendue exécutée par ce document.

## 7. Ordre et feu vert

Le cadrage ajoute deux tâches distinctes, pour éviter un nouveau lot
monolithique : INT-131 proxy, puis INT-132 console/gate.
Chaque implémentation exige son feu vert et ses preuves avant clôture.
Le bootstrap INT-126 et les étapes DB/backup/release restent non démarrés.

Avant publication des commits, inspecter la branche distante et garder
un découpage lisible. Le jalon INT-125 était déjà committé ; aucun push
n'est autorisé automatiquement par une question « faut-il pousser ? ».
