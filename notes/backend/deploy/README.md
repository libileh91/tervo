# Déploiement Tervo — références utiles

## VPS : parcours actuel

Entrée unique : [état du VPS et références](vps/README.md).

| Sujet | Référence |
|---|---|
| Cours progressif de déploiement Tervo (Linux, Docker/Compose, réseau, PostgreSQL, release) | [Cours](../../../deploy/cours/README.md) |
| Caddy natif, HTTP seul, ancien proxy retiré | [Guide Caddy](vps/04-transition-caddy.md) |
| Dockge privé : tunnel, login, logs et gate Tervo validé en recette | [Guide Dockge](../../../deploy/dockge/README.md) |
| Stack reproductible, Compose/env explicites | [INT-125](../sprint7.6/INT-125-stack-reproductible.md) |
| Premier admin sans seed destructif, tests locaux SQLite | [INT-126](../sprint7.6/INT-126-bootstrap-admin.md) |
| DB vide, séparation admin/API et droits testés localement | [INT-127](../sprint7.6/INT-127-postgresql-cible.md) |
| Sauvegarde/restauration : commandes expliquées, preuve locale, mini-s1 à préparer | [INT-128](../sprint7.6/INT-128-sauvegarde-restauration.md) |
| Ordre DB → backups → release → publication | [Planning 7.6](../../../docs/stages/stage7/sprint7.6/tasks.md) |

**La mise en service publique et HTTPS Tervo restent à INT-111.** INT-129 a
validé une stack jetable et le gate Dockge ; nettoyage déclaré par l'opérateur,
Caddy/Dockge actifs confirmés, détails de nettoyage non consignés.
Git reste autoritaire : ne pas copier/éditer le Compose dans l'interface.
Le seed n'est pas une procédure de production.

## Mini-s1 : historique distinct

Le mini-s1 (`192.168.10.192`) utilisait Cloudflare Tunnel et 1Panel.
Les anciennes recettes ne doivent être appliquées ni au VPS ni à une base
peuplée sans nouvelle validation.

- [Cloudflare Tunnel](cloudflare-tunnel-deploy.md) : installation et incidents
  historiques ; remplace les anciens brouillons de première installation,
  réseau et DNS.
- [Incident 502 OpenResty](incident-502-nginx-upstream.md) : limites du DNS Docker
  en mode host ; ne prescrit pas les IP statiques pour Caddy.
- [Registre des erreurs](errors.md) et
  [correction des dates timezone-aware](fix-timezone-aware-datetime-500.md).
- [Ports loopback](../sprint-6.1/ports-securises.md) et
  [healthchecks](../sprint-6.1/healthchecks.md) : notes pédagogiques historiques.

## Archives et hors périmètre

- [Inventaire SSH](vps/01-inventaire-et-acces-ssh.md),
  [sécurité système](vps/02-preparation-securite-systeme.md) et
  [ancien 1Panel](vps/03-preparation-1panel-prive.md) conservent les preuves
  acquises ; ce ne sont pas des recettes à rejouer.
- [Paperless-ngx](paperless-ngx.md) reste une étude de phase 2, pas un service livré.

Les guides supprimés restent dans Git. Ils ne constituent plus une seconde
procédure de déploiement ; versions et configuration exécutables vivent dans
les fichiers du projet, pas dans une copie sous `notes/`.
