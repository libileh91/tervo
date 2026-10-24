# Caddy — INT-131

**État : HTTPS actif sur le VPS depuis INT-111, Caddy activé au démarrage.
INT-131 a livré le bootstrap ; INT-111 a ensuite satisfait le gate DNS et chargé
le profil HTTPS (certificats, redirections et GET publics vérifiés).**

Le guide d'exploitation est
[Caddy : état actuel et suite](../../notes/backend/deploy/vps/04-transition-caddy.md).
Ce dossier conserve uniquement les trois fichiers de configuration ci-dessous
et ce README. Les scripts/tests temporaires de préparation ont été retirés.

## Fichiers de référence

| Fichier | Usage |
|---|---|
| `bootstrap.Caddyfile` | HTTP 80, automatic HTTPS off, admin 127.0.0.1:2019, h1/h2 |
| `caddy.service` | Service natif sous le compte système caddy |
| `production.Caddyfile.example` | Cible HTTPS et upstreams loopback ; copiée vers `/etc/caddy/Caddyfile` en INT-111 ; le fichier du dépôt n'est pas importé dynamiquement |

Version installée : **Caddy v2.11.7**, binaire officiel vérifié.
Les anciennes validations 1Panel/OpenResty ne sont pas attribuées à Caddy.

## Utilisation courante sur le VPS

```bash
sudo /usr/local/bin/caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile \
  && sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Toute modification de proxy ou d'upstream passe par ce dépôt, une validation
puis un reload décidé : ne pas éditer les fichiers actifs sans trace.
