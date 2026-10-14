# VPS — Caddy : état actuel et suite

**Caddy est installé et sert le VPS. INT-131 est terminée.**
Ce guide remplace le journal détaillé de préparation et de bascule.

## 1. Où nous en sommes

| Élément | État vérifié |
|---|---|
| Caddy v2.11.7 | Service natif systemd, actif et activé au démarrage |
| HTTP public | Port 80, réponse `INT-131 bootstrap OK` |
| Administration Caddy | `127.0.0.1:2019`, pas d'écoute publique |
| 1Panel | Désinstallé : dossiers, anciennes unités et binaires absents |
| OpenResty | Conteneur et image supprimés |
| SSH / Docker / UFW | Actifs ; règles du pare-feu inchangées |
| Dockge | À installer en INT-132, accès privé prévu sur 127.0.0.1:5001 |
| Application / PostgreSQL / HTTPS Tervo | Pas encore déployés sur le VPS |

Le serveur affiche une **page de contrôle**, pas l'application Tervo.
Le port 443 est autorisé par UFW pour la suite, mais aucun service n'y
écoute actuellement. Aucun port UDP 443 n'est ouvert dans les règles relevées.
Les contrôles extérieurs ont été faits en IPv4 ; aucune adresse IPv6 globale
n'a été relevée.

## 2. Pourquoi ce choix

Caddy s'occupe uniquement du proxy HTTP/HTTPS, sous systemd.
Les applications resteront dans Docker Compose. Dockge sera une console
Compose privée accessible par tunnel SSH, pas un panneau public.

1Panel/OpenResty ont d'abord été conservés pour tester le retour arrière,
puis retirés avec confirmation. La sauvegarde privée reste conservée.

## 3. Ce qui est déjà validé

- Binaire officiel vérifié et installation native.
- Sauvegarde privée de l'ancien panneau/proxy sur le VPS.
- Passage temporaire sur Caddy puis retour à OpenResty/1Panel testé.
- Bascule finale sur Caddy confirmée, avec démarrage automatique activé.
- Marqueur HTTP public vérifié avant et après confirmation.
- Pas d'écoute 7410, 443 TCP/UDP ; administration Caddy locale uniquement.
- Validation et reload du bootstrap vérifiés : même PID, service actif/activé et réponse HTTP conservée.
- Reboot vérifié : Caddy revient seul, anciens services arrêtés ; HTTP public IPv4 et ports d'administration revérifiés.
- Conteneur et dossiers 1Panel supprimés avec confirmation ; Caddy/Docker et réponse HTTP préservés.
- Nettoyage final : image OpenResty supprimée, unités 1Panel absentes et aucun ancien binaire trouvé.
- État privé sans certificat ; journal Caddy fourni sans tentative ACME, HTTPS automatique désactivé.
- Aucun seed ni transfert/suppression de données applicatives Tervo.

Les scripts/tests temporaires de préparation ont été retirés du dépôt.
L'exploitation utilise les commandes standard ci-dessous ; les résultats
déjà obtenus restent enregistrés dans le suivi du sprint.

## 4. Commandes utiles

À exécuter **sur le VPS**, uniquement pour vérifier :

```bash
sudo systemctl status caddy --no-pager
sudo journalctl -u caddy -b --no-pager
curl --noproxy "*" http://127.0.0.1/
```

Après un changement volontaire de configuration, valider **avant** de recharger :

```bash
sudo /usr/local/bin/caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile \
  && sudo systemctl reload caddy
```

| Fichier | Rôle |
|---|---|
| `/etc/caddy/Caddyfile` | Configuration active, HTTP seul pour le moment |
| `/etc/systemd/system/caddy.service` | Service natif Caddy |
| `/var/lib/caddy` | État persistant de Caddy |
| `deploy/caddy/production.Caddyfile.example` | Exemple HTTPS, **non activé** |

Un message de maintenance `tls` n'est pas, à lui seul, une demande de
certificat. Caddy crée aussi des métadonnées de nettoyage en HTTP seul.

## 5. La suite, dans l'ordre

1. Installer Dockge privé et vérifier son accès par tunnel (INT-132).
2. Préparer bootstrap, DB, backups et release avant INT-111.

Le déploiement de Tervo et le HTTPS des vrais domaines restent en INT-111.
Le warning de journal tronqué reste à diagnostiquer séparément : ne pas
supprimer les journaux pour le masquer.

## 6. Sauvegarde et ancien retour arrière

La sauvegarde ancienne reste privée sous `/root/tervo-backups/`.
**Ne plus lancer l'ancien script de rollback vers 1Panel/OpenResty :**
les composants nécessaires ont été supprimés. Un retour à cet ancien état
demanderait une reconstruction depuis la sauvegarde, pas un simple redémarrage.
Le nettoyage des fichiers temporaires sur le VPS est distinct de cette sauvegarde
et ne doit pas toucher au binaire, à l'unité ou à l'état persistant de Caddy.
Les copies de préparation INT-131 et l'archive/installateur 1Panel dans
`/home/tervo` ont été supprimés ; Caddy/Docker et HTTP ont été revérifiés.
Les six dossiers temporaires INT-131 sous `/root` ont aussi été retirés.
Sauvegardes métier/configuration et sauvegarde APT conservées.
Le dernier binaire inactif `1panel-kvm` reste à supprimer.

Suivi : [INT-131 dans le sprint 7.6](../../../../docs/stages/stage7/sprint7.6/tasks.md).
