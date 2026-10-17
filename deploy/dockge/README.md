# Dockge privé — INT-132

**INT-132 : console privée installée et testée. INT-129 : gate Tervo validé
sur stack de recette VPS ; stack de production non encore déployée.**

Le Compose suit le modèle officiel Dockge 1.5.0, avec image épinglée,
port `127.0.0.1:5001`, données privées dans `/opt/dockge/data` et
répertoire de stacks identique hôte/conteneur : `/opt/stacks`.

## Installation effectuée sur le VPS

L'opérateur a créé les dossiers et installé le fichier versionné en
`/opt/dockge/compose.yaml`. Image épinglée téléchargée, conteneur démarré,
publication loopback confirmée, puis conteneur `healthy`.
Le poste client n'a pas pu joindre TCP5001 public (délai3s).
Le login a ensuite été confirmé via tunnel. À ce stade INT-132, l'adoption
Tervo restait à vérifier ; le gate de recette a depuis été validé dans INT-129.

```bash
sudo docker compose -p dockge --project-directory /opt/dockge \
  -f /opt/dockge/compose.yaml config --quiet
sudo docker compose -p dockge --project-directory /opt/dockge \
  -f /opt/dockge/compose.yaml up -d
```

Pas de modification Caddy/UFW ni de déploiement Tervo dans cette étape.

## Accès depuis l'ordinateur de l'administrateur

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -i "$HOME/.ssh/tervo_ed25519" \
  -L 127.0.0.1:15001:127.0.0.1:5001 \
  tervo@151.241.228.152
```

Ouvrir `http://127.0.0.1:15001`, créer le compte administrateur avec un
mot de passe privé et vérifier le login. Aucun secret dans Git ou le chat.
L'utilisateur a confirmé l'accès au tableau de bord après connexion.
Une fenêtre privée affiche la page de connexion, pas le tableau de bord.

## Vérification de l'interface

L'utilisateur a vu les logs fictifs `Dockge demo OK` et un arrêt avec code 0.
La démo n'avait ni port, ni volume, ni réseau. Sur le VPS, le contrôle
`sudo docker ps -a --filter label=com.docker.compose.project=dockge-demo`
n'a renvoyé aucun conteneur et `/opt/stacks/dockge-demo` était absent.
Cela ne teste pas les chemins de build ou la configuration de Tervo.

## Limites à connaître

- Le socket Docker donne des droits équivalents à root, pas une vue read-only.
- La console générale reste désactivée jusqu'à sécurisation et décision explicite.
- Dockge ne remplace pas SSH, systemd ni Git.
- INT-129 : gate Git/CLI/Compose de la console, logs et Stop/Start validés sur
  la stack jetable `int129-vps-33c350b23010`, images et données conservées.
  Les deux `create_host_path: false` omis du JSON de la console ont été
  qualifiés par un refus réel de bind absent. Tolérance dans la comparaison
  en mémoire seulement, pas dans les fichiers/artefacts runtime ; tout autre
  écart bloque. Requalifier si versions/layout changent.
  Git reste autoritaire, pas d'édition/copie du Compose via l'UI.
  [Commandes root, preuves et limites INT-129](../../notes/backend/sprint7.6/INT-129-release-rollback.md).
- INT-128 : restauration isolée des données d'auth ; INT-111 : recontrôle
  après reboot et recette réelle. Pas de commandes hôte testées dans Dockge.

Sources : [release officielle](https://github.com/louislam/dockge/releases/tag/1.5.0),
[Compose officiel](https://github.com/louislam/dockge/blob/1.5.0/compose.yaml).
