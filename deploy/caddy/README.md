# Caddy — INT-131

**État : bootstrap HTTP actif sur le VPS, Caddy activé au démarrage.
INT-131 terminée : reload/reboot/public IPv4 et état vérifiés.**

Le guide d'exploitation est
[Caddy : état actuel et suite](../../notes/backend/deploy/vps/04-transition-caddy.md).
Ce dossier conserve uniquement les trois fichiers de configuration ci-dessous
et ce README. Les scripts/tests temporaires de préparation ont été retirés.

## Fichiers de référence

| Fichier | Usage |
|---|---|
| `bootstrap.Caddyfile` | HTTP 80, automatic HTTPS off, admin 127.0.0.1:2019, h1/h2 |
| `caddy.service` | Service natif sous le compte système caddy |
| `production.Caddyfile.example` | Cible HTTPS et upstreams loopback ; **non activée avant INT-111** |

Version installée : **Caddy v2.11.7**, binaire officiel vérifié.
Les anciennes validations 1Panel/OpenResty ne sont pas attribuées à Caddy.

## Utilisation courante sur le VPS

```bash
sudo /usr/local/bin/caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile \
  && sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Pas de reboot, de suppression d'ancien composant ni d'activation HTTPS
sans l'étape et le feu vert correspondants.
