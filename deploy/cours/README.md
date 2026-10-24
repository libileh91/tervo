# Cours de déploiement Tervo

Parcours pédagogique débutant, du poste local aux services VPS. Ces chapitres
expliquent les principes et commandes ; ils distinguent les exemples à adapter
des opérations réellement observées.

## À lire dans l'ordre

1. [Linux, SSH, sudo et shell](01-du-poste-local-au-vps.md)
2. [Images, conteneurs et Compose](02-images-conteneurs-compose.md)
3. [Réseau, Caddy et Dockge](03-reseau-caddy-dockge.md)
4. [PostgreSQL, migrations et sauvegardes](04-postgresql-migrations-sauvegardes.md)
5. [Release, rollback et entretien](05-release-rollback-entretien.md)
6. [Après la recette : sauvegardes, restic et SSH depuis les bases](06-apres-la-recette-sauvegardes-restic-et-ssh.md)

## Comment utiliser ces documents

| Besoin | Document |
|---|---|
| Comprendre pourquoi et comment | Les six chapitres ci-dessus |
| Reprendre ce qui a été fait après les tests frontend | [Cours 06 : préparation des sauvegardes et accès SFTP](06-apres-la-recette-sauvegardes-restic-et-ssh.md) |
| Exécuter une opération sur la bonne cible | [Parcours opérateur VPS](../../notes/backend/deploy/vps/05-tervo-release-et-exploitation.md) |
| Savoir ce qui a réellement réussi ou échoué | [Journal INT-111](../../notes/backend/sprint7.6/INT-111-deploiement-vps.md) et [recette INT-129](../../notes/backend/sprint7.6/INT-129/README.md) |
| Savoir ce qu'il reste à valider | [Critères du sprint](../../docs/stages/stage7/sprint7.6/tasks.md) |

**Fil conducteur actuel :** Tervo est publié sur le VPS en HTTPS ; les GET
publics et certificats ont été vérifiés, l'admin et la recette de bout en bout
sont confirmés par l'opérateur. La préparation des sauvegardes vient ensuite :
capture VPS réalisée, transfert SFTP vérifié et premier snapshot restic
`03aca082` enregistré sur mini-s1, avec lecture intégrale sans erreur.
Les données SQL et photos ont ensuite été restaurées dans une cible isolée
sur le VPS. Le périmètre validé reste une démo avec sauvegardes manuelles :
TD-B024 reporte l'automatisation vers un stockage externe permanent avant
clientèle réelle. Le reboot réel, les services, ports et certificats persistants
sont vérifiés ; le nettoyage ciblé a été exécuté et ses sorties consignées, le
commit de livraison clôt INT-111. La CI/CD reste INT-130, non automatisée.
Le cache Docker défectueux du mini-s1 est documenté, pas réparé globalement,
et aucun serveur mail n'a été installé.

Les exemples `int129-vps-…` et ports `19829/19830` appartiennent à la recette
jetable, désormais supprimée. La stack actuelle s'appelle `tervo` et utilise
`8000/3000` en loopback.
Ne pas copier les données fictives ou bundles de recette en production.
Les [anciennes procédures mini-s1/1Panel](../../notes/backend/deploy/README.md)
restent des archives, pas des étapes préalables à rejouer.

### Six questions pour vérifier la compréhension

1. Pourquoi SSH peut-il fonctionner alors que Docker est refusé ? → chapitre 01.
2. Pourquoi un build réussi ne suffit-il pas à livrer l'application ? → chapitre 02.
3. Pourquoi `admin@tervoapp.com` peut-il recevoir sans que le site soit public ? → chapitre 03.
4. Pourquoi PostgreSQL peut-il être healthy après un échec d'initialisation ? → chapitre 04.
5. Pourquoi ne pas relancer aveuglément une première release échouée ? → chapitre 05.
6. Pourquoi SFTP peut-il réussir alors que la restriction lecture seule est mal configurée ? → chapitre 06.

Les réponses et commandes sont dans les chapitres ; ces questions ne demandent
aucun nouveau déploiement ni test de panne.
