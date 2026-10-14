# INT-131/132 — Choix Caddy et Dockge

## La décision

| Responsabilité | Outil retenu |
|---|---|
| Proxy HTTP/HTTPS public | Caddy natif, géré par systemd |
| Applications et PostgreSQL | Docker Compose, défini dans Git |
| Console Compose | Dockge privé, tunnel SSH et login |
| Administration système et secours | SSH |

Le but est de séparer les responsabilités et de garder une architecture
simple à expliquer. Ce n'est pas un changement de modèle métier.
Le différenciateur de Tervo reste la migration Excel.

## État réel

- **INT-131 terminée :** Caddy actif, reload et reboot vérifiés ; ancien
  panneau/proxy retiré après test du retour arrière.
- **INT-132 à démarrer :** Dockge privé à installer ; aucune adoption Tervo.
- Pas encore de déploiement applicatif, PostgreSQL Tervo ou HTTPS public sur le VPS.
- Les preuves historiques 1Panel/OpenResty restent distinctes de celles de Caddy.

Pour l'état du proxy, lire [le guide Caddy](../deploy/vps/04-transition-caddy.md).

## Règles à conserver

### Caddy

- Bootstrap HTTP sans vrais hostnames ni automatic HTTPS.
- API d'administration locale, pas de port 2019 public.
- Pas d'HTTP/3 ou d'ouverture UDP 443 sans décision explicite.
- Profil HTTPS réel inactif jusqu'à INT-111.

### Dockge

- Écoute sur `127.0.0.1:5001`, accès par tunnel SSH et login.
- Aucun domaine public ni route Caddy vers la console.
- Le socket Docker donne des droits administrateur : `:ro` ne rend pas
  son API read-only.
- Git reste la source de vérité ; pas de copie autonome ou d'édition
  du Compose non tracée dans l'interface.
- Avant adoption de Tervo, vérifier sur une stack jetable les chemins,
  l'environnement, le nom du projet et les volumes.

Une tâche à la fois : INT-131 terminée, INT-132 à démarrer.
Les critères détaillés restent dans
[le planning](../../../docs/stages/stage7/sprint7.6/tasks.md),
pas dans une seconde procédure.

## Livraison INT-131 — l'essentiel à comprendre

L'unité native sépare l'exploitation du proxy de Docker :

```ini
User=caddy
Group=caddy
ExecStart=/usr/local/bin/caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
```

Le compte dédié possède `/var/lib/caddy`, pas la configuration root.
`validate` vérifie le fichier ; `reload` l'applique sans changer de PID.
Le routage A/B et le refus invalide ont été testés en local isolé avec le
vrai binaire ; le bootstrap, le reload, l'extérieur IPv4 et le reboot sur VPS.
Les dernières lectures montrent uniquement de la maintenance interne,
aucun certificat et aucune tentative ACME visible.

Limites : aucun upstream applicatif VPS ni TLS public livré ; journal global
tronqué à diagnostiquer séparément. L'ancien rollback ne doit plus être lancé
après désinstallation ; sauvegarde conservée.
