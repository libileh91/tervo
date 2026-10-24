# Déploiement Tervo — références utiles

## VPS : parcours actuel

Entrée unique : [état du VPS et ordre de lecture](vps/README.md).
Pour comprendre une opération, suivre le
[parcours Tervo : release, contrôles, admin et publication](vps/05-tervo-release-et-exploitation.md).
Les commandes de ce parcours indiquent la machine, les droits, les résultats
attendus et ce qu'il faut faire en cas d'échec.

| Sujet | Référence |
|---|---|
| Cours progressif de déploiement Tervo (Linux, Docker/Compose, réseau, PostgreSQL, release) | [Cours](../../../deploy/cours/README.md) |
| Caddy natif HTTPS, ancien proxy retiré | [Guide Caddy](vps/04-transition-caddy.md) |
| Dockge privé : tunnel, login, logs et gate Tervo validé en recette | [Guide Dockge](../../../deploy/dockge/README.md) |
| Stack reproductible, Compose/env explicites | [INT-125](../sprint7.6/INT-125-stack-reproductible.md) |
| Premier admin sans seed : mécanisme livré, création VPS confirmée en INT-111 | [INT-126](../sprint7.6/INT-126-bootstrap-admin.md), [journal INT-111](../sprint7.6/INT-111-deploiement-vps.md) |
| PostgreSQL : rôles SQL distincts, initialisation et migrations avant HTTP | [INT-127](../sprint7.6/INT-127-postgresql-cible.md) |
| Sauvegarde manuelle chiffrée sur mini-s1 et récupération SQL/photos isolée sur le VPS | [Journal INT-111](../sprint7.6/INT-111-deploiement-vps.md), [procédure INT-128](../sprint7.6/INT-128-sauvegarde-restauration.md) |
| Ordre DB → backups → release → publication | [Planning 7.6](../../../docs/stages/stage7/sprint7.6/tasks.md) |

**INT-111 : démo publique HTTPS, admin et recette navigateur confirmés,
sauvegarde manuelle/restauration SQL et photos validées.** Le reboot est
vérifié et le nettoyage ciblé exécuté, sorties consignées. Aucun timer ; TD-B024 reporte
l'automatisation avant clientèle réelle. Réception des alias email confirmée,
pas l'envoi applicatif : voir les
[fonctions distinctes de Cloudflare](../../../deploy/cours/03-reseau-caddy-dockge.md).
Git reste autoritaire : ne pas copier/éditer le Compose dans l'interface.
Le seed n'est pas une procédure de production. La base contient maintenant
un compte réel : ne pas rejouer le nettoyage de la première initialisation.

**Trois types de documents, trois usages :**
- `deploy/cours/` explique les concepts et les choix ;
- ce dossier décrit les opérations et sépare les environnements ;
- `notes/backend/sprint7.6/` conserve les preuves et incidents des tâches.
Une sortie « attendue » dans un guide n'est pas une preuve d'exécution.

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
