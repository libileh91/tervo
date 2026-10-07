# Tervo — Best practices 1Panel & VPS production

> **Contexte :** INT-111 — Déploiement VPS
> **Cible :** Hostkey `vm.mini` — 4 vCore / 6 GB RAM / 120 GB SSD
> **OS :** Debian 13
> **Orchestration :** Docker Compose
> **Administration serveur :** 1Panel
> **Reverse proxy :** OpenResty / 1Panel
> **CI/CD :** GitHub Actions → SSH → VPS
> **Statut :** référence opérationnelle à partir d’INT-111

Ce document fixe la doctrine cible, pas un bilan de déploiement réussi.
Les réalisations, écarts et contrôles effectivement observés sont tracés
dans [le parcours VPS](vps/README.md). L'exception firewall d'INT-124
ci-dessous ne permet jamais de publier l'administration.

---

## 1. Décision d'architecture

Pour Tervo, **1Panel est conservé**, mais avec une responsabilité volontairement limitée.

La règle centrale est :

> **Git + `deploy/docker-compose.yml` définissent Tervo.
> 1Panel administre le VPS autour de Tervo.**

1Panel ne doit pas devenir une seconde source de vérité pour le déploiement applicatif.

```text
GitHub
│
├── code
├── Dockerfiles
├── deploy/docker-compose.yml
└── GitHub Actions
        │
        │ SSH
        ▼
/opt/tervo
        │
        ▼
Docker Compose
├── postgres
├── backend
└── frontend
        │
        ▼
1Panel / OpenResty
├── reverse proxy
├── HTTPS / Let's Encrypt
├── monitoring VPS
├── backups / cron
└── administration
        │
        ▼
Internet
```

### Principe

Tervo doit rester déployable même si 1Panel disparaît :

```bash
cd /opt/tervo
docker compose -f deploy/docker-compose.yml up -d
```

La suppression ou la panne de l'interface 1Panel ne doit donc jamais rendre impossible :

- le build de Tervo ;
- le démarrage des conteneurs ;
- les migrations ;
- les sauvegardes manuelles ;
- le diagnostic ;
- la restauration.

---

# 2. Responsabilités : qui gère quoi ?

| Sujet | Source de vérité | Rôle de 1Panel |
|---|---|---|
| Code Tervo | GitHub | aucun |
| Dockerfiles | GitHub | visualisation seulement |
| Docker Compose | `deploy/docker-compose.yml` | observation |
| Variables applicatives | `/opt/tervo/.env` | aucun |
| PostgreSQL Tervo | Docker Compose | observation |
| Volumes Tervo | Docker Compose | observation |
| Déploiement | Commande de release INT-129 ; automatisation GitHub Actions INT-130 | aucun |
| Migrations Alembic | commande de release, avant exposition du nouveau code | aucun |
| Reverse proxy | 1Panel | **responsable** |
| HTTPS / certificats | 1Panel | **responsable** |
| Domaine / routage HTTP | 1Panel | **responsable côté serveur** |
| DNS public | fournisseur DNS | aucun |
| Backups planifiés | scripts Tervo + scheduler 1Panel | **scheduler** |
| Monitoring système | Debian + 1Panel | dashboard |
| Firewall | Debian / UFW | synchronisation automatique limitée à l'exception INT-124 documentée en section 7 |
| Fail2ban | Debian | ne pas installer une seconde instance |
| SSH | Debian | aucun |
| Updates Debian Security | Debian | aucun |

## Règle anti-double-administration

Ne jamais administrer le même composant depuis deux endroits sans nécessité.

Exemples :

```text
UFW        → Debian, avec exception de synchronisation 1Panel contrôlée
Fail2ban   → Debian
Docker     → Docker CLI / Compose
Tervo      → Git + Compose
HTTPS      → 1Panel
Proxy      → 1Panel
Cron backup → 1Panel déclenche un script versionné
```

---

# 3. Ce que 1Panel doit faire pour Tervo

1Panel est utilisé pour :

- OpenResty ;
- reverse proxy frontend/API ;
- certificats Let's Encrypt ;
- renouvellement automatique des certificats ;
- redirection HTTP → HTTPS ;
- monitoring CPU/RAM/disque ;
- visualisation des conteneurs et logs ;
- gestion ponctuelle de fichiers ;
- jobs planifiés ;
- sauvegardes vers stockage externe ;
- diagnostic du VPS.

Il peut également être utilisé pour consulter Docker, mais **pas pour redéfinir la stack Tervo**.

---

# 4. Ce que 1Panel ne doit PAS faire

Pour Tervo, ne pas utiliser :

```text
1Panel App Store → PostgreSQL
1Panel App Store → Redis
1Panel Runtime → Python / FastAPI
1Panel Runtime → Node / Vue
1Panel Compose editor → définition principale de Tervo
1Panel Database → création d'un second PostgreSQL Tervo
```

La stack existe déjà :

```text
deploy/docker-compose.yml
```

Elle contient :

```text
PostgreSQL
   ↓ healthcheck
Backend FastAPI
   ↓
Frontend
```

Créer les mêmes composants depuis 1Panel conduirait à deux architectures concurrentes.

---

# 5. État de départ INT-111

Déjà réalisé :

```text
[x] Debian 13
[x] utilisateur tervo
[x] sudo configuré
[x] SSH clé uniquement
[x] root SSH désactivé
[x] UFW
    ├── 22
    ├── 80
    └── 443
[x] fail2ban
[x] mises à jour Debian Security automatiques
[x] Docker Engine installé
[x] Docker Compose installé
```

À partir de ce document, INT-111 continue avec :

```text
1. 1Panel
2. OpenResty
3. sécurisation accès 1Panel
4. préparation /opt/tervo
5. secrets production
6. PostgreSQL production
7. backups / TD-B010
8. reverse proxy
9. DNS
10. Let's Encrypt
11. CI/CD
12. migrations
13. recette fonctionnelle
14. procédure de restauration
15. clôture INT-111
```

---

# 6. Installation de 1Panel

Utiliser l'installateur officiel 1Panel correspondant à la version stable retenue.

Ne pas lancer un installateur stock puis supposer que refermer le port
après coup suffit : INT-124 a constaté une exposition publique et une
synchronisation firewall supplémentaire par l'agent. La procédure de
[préparation/reprise privée](vps/03-preparation-1panel-prive.md) distingue
le patch shell historique du confinement réel. Préparer la protection
avant démarrage, appliquer le bind officiel loopback, puis vérifier
écoute, règles et refus extérieur avant activation au boot.

Avant installation :

```bash
docker --version
docker compose version
sudo ufw status verbose
sudo ss -lntp
free -h
df -h
```

Documenter dans cette procédure :

```text
Version 1Panel :
Version Docker :
Version Compose :
Date installation :
Chemin installation :
Port administration :
Version OpenResty :
```

## Ne pas réinstaller Docker inutilement

Docker et Compose sont déjà provisionnés dans INT-111.

1Panel doit utiliser le moteur Docker existant.

Après installation :

```bash
docker version
docker compose version
docker ps
docker network ls
```

---

# 7. Accès à 1Panel : jamais public

Le port d'administration retenu pour Tervo est :

```text
7410
```

Il ne fait **pas** partie des ports publics autorisés.

Surface publique attendue :

```text
22/tcp
80/tcp
443/tcp
```

Pas :

```text
7410
3000
8000
5432
```

## Accès normal

Depuis le poste administrateur :

```bash
ssh -N \
  -o IdentitiesOnly=yes \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -i "$HOME/.ssh/tervo_ed25519" \
  -L 127.0.0.1:17410:127.0.0.1:7410 \
  tervo@<VPS>
```

Puis :

```text
http://127.0.0.1:17410/<entree-privee>
```

17410 appartient au poste administrateur ; 7410 reste le port du VPS.
Cela évite un conflit avec un panneau local. `ssh -N` reste silencieux
et ne démarre aucun service distant. Ne jamais partager les cookies,
la passphrase ou l'entrée privée lors d'un diagnostic.

## Défense en profondeur

Le bind privé est obligatoire dans la stratégie approuvée pour INT-124 :

```text
1Panel → bind 127.0.0.1:7410
```

L'état UFW contrôlé après reprise et restart conserve :

```text
UFW → DENY 7410/TCP IPv4 et IPv6, aucun ALLOW 7410 visible
```

**Exception approuvée :** cette version de l'agent 1Panel peut synchroniser
des règles firewall au démarrage. Le patch de l'installateur shell ne
désactive pas ce mécanisme. Ne pas promettre « 1Panel ne touche jamais
UFW » ; inventorier les règles réellement créées et conserver le bind
loopback, puis tester l'accès extérieur après restart et mise à jour.
Une règle ALLOW n'expose pas à elle seule une écoute loopback, mais un
retour à `0.0.0.0`/`[::]` pourrait rendre le panneau accessible.
L'éventuelle règle 443/UDP doit être évaluée séparément ; elle n'est pas
déclarée nécessaire à Tervo. Un filtre fournisseur indépendant apporterait
une protection supplémentaire s'il est disponible.

Incident, correction et limites :
[réalisation INT-124](vps/03-preparation-1panel-prive.md#9-décision-approuvée-mise-en-œuvre-encore-partielle).

## Preuves obligatoires

Sur le VPS :

```bash
sudo ss -lntp
sudo ufw status verbose
```

Depuis une machine extérieure :

```bash
curl --connect-timeout 5 http://<VPS>:7410
```

Résultat attendu :

```text
timeout
ou
connection refused
```

Le tunnel SSH doit simultanément fonctionner.

---

# 8. Docker Compose reste la source de vérité

La production utilise :

```text
/opt/tervo/
└── deploy/docker-compose.yml
```

Ne pas recopier son contenu manuellement dans l'éditeur Compose de 1Panel.

Ne pas maintenir :

```text
compose Git
+
compose 1Panel différent
```

## Workflow normal

```bash
cd /opt/tervo

docker compose \
  --env-file /opt/tervo/.env \
  -f deploy/docker-compose.yml \
  config --quiet
```

Cette commande ne publie pas la stack et n'affiche pas les secrets.
Le lancement réel passe par la commande de release INT-129 à livrer,
avec migration avant exposition ; ne pas remplacer cette étape par
un `compose up --build` direct.

1Panel peut ensuite afficher les conteneurs résultants.

### Important pour Fuliyeh

Une modification faite uniquement depuis l'UI 1Panel n'est **pas** une modification du projet Tervo.

Si une modification applicative doit survivre à un :

```bash
git pull
docker compose up -d
```

elle doit être représentée dans le repository.

---

# 9. Secrets production

Les secrets ne doivent jamais être :

- dans Git ;
- dans `docker-compose.yml` avec une vraie valeur ;
- dans une note Markdown ;
- dans les logs CI ;
- dans un screenshot partagé.

Le repository ignore déjà :

```text
.env
```

La production utilisera :

```text
/opt/tervo/.env
```

Permissions :

```bash
sudo chown tervo:tervo /opt/tervo/.env
chmod 600 /opt/tervo/.env
```

Exemple de variables :

```dotenv
TERVO_DB_NAME=tervo_db
TERVO_DB_USER=tervo
TERVO_DB_PASSWORD=<secret-long>
SECRET_KEY=<secret-long>
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

## À corriger avant passage production

Le Compose contient actuellement des valeurs de fallback adaptées au développement :

```yaml
${TERVO_DB_PASSWORD:-password}
${SECRET_KEY:-change-me-in-production}
```

En production, les secrets critiques doivent échouer explicitement s'ils sont absents :

```yaml
POSTGRES_PASSWORD: ${TERVO_DB_PASSWORD:?TERVO_DB_PASSWORD is required}
SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required}
```

Principe :

> mieux vaut un déploiement qui échoue immédiatement qu'une production démarrée avec `password`.

---

# 10. Réseau Docker

Le modèle de sécurité reste :

```text
Internet
   │
   ▼
80 / 443
   │
   ▼
OpenResty
   │
   ├── frontend
   └── backend
           │
           ▼
       PostgreSQL
```

PostgreSQL :

```yaml
postgres:
  # aucun ports:
```

Backend :

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

Frontend :

```yaml
ports:
  - "127.0.0.1:3000:80"
```

Cela donne deux protections différentes :

```text
PostgreSQL
→ aucun port hôte

Frontend/backend
→ port hôte uniquement sur loopback
```

---

# 11. `1panel-network` : règle Tervo

Le Compose actuel référence :

```yaml
networks:
  1panel-network:
    external: true
    name: 1panel-network
```

Si la stratégie bridge et le Compose retenu utilisent ce réseau externe,
avant le premier déploiement :

```bash
docker network inspect 1panel-network
```

Le réseau doit alors exister et sa création doit être documentée.
En mode host avec upstreams loopback, ne pas créer ni imposer ce bridge
par habitude ; INT-125 adaptera le Compose à la stratégie validée en INT-124.

Ne jamais supprimer :

```text
1panel-network
```

via un nettoyage Docker automatique s'il est utilisé par le déploiement.

## Reverse proxy : ne pas supposer le mode réseau

Avant de configurer OpenResty, déterminer son mode réel :

```bash
docker inspect <openresty-container> \
  --format '{{.HostConfig.NetworkMode}}'
```

### Cas A — OpenResty utilise le réseau host

Le proxy peut joindre :

```text
127.0.0.1:3000
127.0.0.1:8000
```

C'est le scénario le plus simple.

```text
OpenResty
   │
   ├── 127.0.0.1:3000 → frontend
   └── 127.0.0.1:8000 → backend
```

### Cas B — OpenResty utilise un bridge Docker

Le loopback du conteneur OpenResty n'est alors **pas** celui du VPS.

Dans ce cas, utiliser le réseau Docker partagé et la résolution Docker.

Ne jamais utiliser une IP de conteneur statique telle que :

```text
172.18.0.5
```

Une IP Docker peut changer après recréation.

### Règle

> Vérifier le `NetworkMode`, puis choisir une seule stratégie de routage.

Ne pas mélanger au hasard :

```text
host loopback
+
IP statique Docker
+
DNS container
```

---

# 12. Reverse proxy Tervo

Créer deux entrées distinctes :

```text
Frontend
app.<domaine>
    ↓
frontend

API
api.<domaine>
    ↓
backend
```

Les noms exacts des domaines restent une décision d'exploitation.

## Ne jamais exposer directement

```text
https://<VPS>:8000
https://<VPS>:3000
```

Toutes les requêtes publiques doivent passer par OpenResty.

---

# 13. HTTPS

Pour chaque domaine :

```text
DNS
 ↓
1Panel/OpenResty
 ↓
Let's Encrypt
 ↓
HTTPS
```

Configurer :

```text
HTTP → HTTPS
certificat Let's Encrypt
renouvellement automatique
```

Puis vérifier :

```bash
curl -I http://app.<domaine>
curl -I https://app.<domaine>

curl -I http://api.<domaine>
curl -I https://api.<domaine>
```

HTTP doit rediriger vers HTTPS.

HTTPS doit présenter un certificat valide.

Ne pas considérer le critère INT-111 comme terminé uniquement parce que l'UI 1Panel affiche :

```text
Certificate: valid
```

La preuve finale est une requête réelle depuis l'extérieur.

---

# 14. PostgreSQL : une seule instance Tervo

Pour INT-111 utiliser :

```text
deploy/docker-compose.yml
```

et son service :

```text
postgres
```

Ne pas lancer simultanément :

```text
deploy/postgres.docker-compose.yml
```

sauf décision explicite future de passer à un PostgreSQL partagé.

Sinon on risque :

```text
PostgreSQL A → stack Tervo
PostgreSQL B → stack autonome

→ confusion sur les données
→ backups du mauvais volume
→ migrations sur la mauvaise DB
```

---

# 15. Healthchecks

PostgreSQL doit conserver :

```yaml
healthcheck:
  test:
    [
      "CMD-SHELL",
      "pg_isready -U ${TERVO_DB_USER} -d ${TERVO_DB_NAME}"
    ]
```

Backend :

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

Le healthcheck backend cible prévu dans INT-125 doit vérifier la connexion
à PostgreSQL. Un HTTP 200 sur `/openapi.json` ne prouve que le serveur HTTP,
pas la disponibilité de la DB. Le healthcheck actuel ne doit donc pas
être considéré comme une preuve suffisante de readiness métier.
`depends_on` ne vérifie la santé qu'au démarrage ; il ne garantit pas
que la DB reste disponible ensuite.

Vérification cible après livraison d'INT-125, avec les healthchecks backend
et frontend adaptés :

```bash
docker compose -f deploy/docker-compose.yml ps
```

État attendu :

```text
postgres   healthy
backend    healthy
frontend   healthy
```

Dans une stack jetable, rendre la DB indisponible doit faire échouer la
readiness backend, puis son rétablissement doit être observé. Ne pas
effectuer ce test de panne sur une DB persistante utilisée.

Ne pas considérer :

```text
STATUS = Up
```

comme équivalent à :

```text
application prête
```

---

# 16. Uploads

Les photos Tervo sont persistées hors du filesystem éphémère du container :

```yaml
uploads_data:/app/uploads
```

Une recréation :

```bash
docker compose up -d --force-recreate
```

ne doit donc pas supprimer les uploads.

Interdit :

```bash
docker compose down -v
```

en production sauf opération volontaire de destruction.

Le `-v` supprime les volumes.

---

# 17. Backups — TD-B010

Le backup production doit couvrir **deux catégories distinctes** :

```text
1. PostgreSQL
2. fichiers utilisateurs / uploads
```

Un backup du repository Git n'est pas un backup de production.

## PostgreSQL

Utiliser un dump logique PostgreSQL :

```text
pg_dump
```

plutôt qu'une simple copie à chaud des fichiers internes du volume.

Format recommandé :

```text
custom / pg_dump -Fc
```

Il permet notamment une restauration avec :

```text
pg_restore
```

## Uploads

Sauvegarder séparément le contenu :

```text
uploads_data
```

## Stratégie minimale

```text
quotidien
├── PostgreSQL dump
└── uploads

hebdomadaire
└── conservation plus longue
```

Conserver au minimum une copie **hors du VPS**.

Un backup uniquement stocké dans :

```text
/var/backups/tervo/
```

protège d'une erreur applicative mais pas de :

```text
SSD détruit
VPS supprimé
compte hébergeur bloqué
machine compromise
```

## Rôle de 1Panel

1Panel peut **planifier** l'exécution.

La logique du backup doit idéalement vivre dans un script versionné, par exemple :

```text
deploy/scripts/backup-production.sh
```

1Panel exécute ensuite ce script via un cron.

Ainsi :

```text
Git = logique du backup
1Panel = scheduler
```

et non :

```text
script critique uniquement écrit dans un champ de l'UI 1Panel
```

---

# 18. Un backup n'est valide qu'après un restore

Après création de la stratégie :

```text
backup créé
     ↓
backup copié
     ↓
restore test
     ↓
contrôle données
```

TD-B010 ne doit pas être fermé simplement parce qu'un fichier `.dump` existe.

Vérifier au minimum :

```text
tables présentes
migrations présentes
utilisateur test présent
nombre d'entités cohérent
uploads lisibles
```

Documenter :

```text
date
backup utilisé
commande restore
résultat
anomalies éventuelles
```

---

# 19. CI/CD — responsabilité exclusive GitHub Actions

Modèle cible d'INT-130, **après** recette manuelle INT-111 et livraison
de la commande de release INT-129 :

```text
push main
   │
   ▼
GitHub Actions
   ├── backend tests
   ├── PostgreSQL tests
   ├── frontend tests
   ├── typecheck
   └── frontend build
          │
          ▼
       SSH VPS
          │
          └── commande de release versionnée INT-129
                 ├── SHA et images identifiés, ancien artefact conservé
                 ├── maintenance / exposition bloquée
                 ├── migration ponctuelle avec la nouvelle image
                 ├── démarrage, readiness DB et smoke tests
                 └── exposition rétablie seulement après succès
```

Il n'existe pas de second pipeline :

```text
GitHub Actions
+
1Panel Git deployment
```

1Panel ne déploie pas Tervo.

Le push des notes ou une CI de vérification verte ne doivent pas activer
automatiquement le déploiement. Aucun nettoyage d'images de secours ne
fait partie de la release ; leur rétention relève d'une politique explicite.

---

# 20. Un seul build

INT-111 conserve le principe établi en INT-70 :

```text
GitHub Actions → vérifie
VPS            → build
```

La CI ne construit pas une image Docker qui serait ensuite jetée.

La séquence historique `compose up --build`, puis migration dans le backend
déjà démarré, n'est **pas** une procédure sûre à rejouer sur ce VPS.
INT-129 doit construire une fois chaque nouvelle image et lui attribuer
un identifiant immutable, conserver les images/configurations précédentes,
puis effectuer les migrations avant l'exposition des nouveaux services.
La recette manuelle et INT-130 réutiliseront la même commande de release.
Cette commande reste à implémenter et valider ; aucun script de release
n'est déclaré livré par cette note.

Évolution future possible :

```text
CI
 ↓
build images
 ↓
GHCR
 ↓
VPS docker compose pull
```

mais **GHCR n'appartient pas à INT-111**.

---

# 21. Compte SSH CI/CD

GitHub Actions utilise une clé dédiée.

Secrets GitHub :

```text
VPS_HOST
VPS_USER
VPS_SSH_KEY
```

Variable :

```text
DEPLOY_ENABLED=true
```

À activer uniquement dans INT-130 après la recette manuelle et validation
du mécanisme de déploiement. Cette valeur est une cible, pas l'état actuel
du dépôt ni une instruction d'activation immédiate.

Ne pas réutiliser la clé personnelle d'administration.

L'utilisateur de déploiement n'a pas besoin de se connecter en root.

## Important

Un utilisateur membre du groupe :

```text
docker
```

possède en pratique des privilèges très élevés sur le serveur.

La clé CI correspondante doit donc être traitée comme un secret critique.

---

# 22. Pas de seed de démonstration en production

En production :

```text
alembic upgrade head
```

oui.

Mais :

```text
python -m app.seed
```

non.

Les comptes tels que :

```text
admin / admin123
tech1 / password123
```

ne doivent jamais faire partie de la production.

Créer un compte réel dédié via le mécanisme Tervo validé.

Si aucun bootstrap production n'existe encore, INT-111 doit introduire explicitement cette procédure au lieu de réutiliser le seed de développement.

---

# 23. Logs Docker

Sur un VPS de 120 GB, des logs Docker non limités peuvent progressivement remplir le disque.

Ajouter une politique explicite aux services importants, par exemple :

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "5"
```

À appliquer notamment à :

```text
backend
frontend
postgres
```

Éviter de compter uniquement sur :

```bash
docker system prune
```

pour contrôler l'espace disque.

---

# 24. Gestion des ressources — VPS 6 GB

Ne pas multiplier les services d'infrastructure tant qu'ils ne sont pas nécessaires.

Stack cible :

```text
Debian
├── 1Panel
├── OpenResty
├── Docker
│   ├── PostgreSQL
│   ├── FastAPI
│   └── frontend
└── services système
```

Ne pas installer par défaut :

```text
Portainer
Dockge
Coolify
Dokploy
Redis
Prometheus
Grafana
Uptime Kuma
second PostgreSQL
```

Chaque composant supplémentaire doit répondre à un besoin réel.

## Mesures utiles

```bash
free -h
df -h
docker stats --no-stream
docker system df
```

Seuil opérationnel simple :

```text
RAM durablement > 80 %
ou
disque > 80 %

→ analyser avant d'ajouter des services
```

---

# 25. Updates

Trois couches différentes :

```text
Debian
Docker
1Panel / OpenResty
```

Elles ne doivent pas être mises à jour aveuglément en même temps.

## Debian

Les mises à jour de sécurité automatiques sont déjà configurées.

Conserver cette politique.

## 1Panel / OpenResty

Préférer une mise à jour volontaire :

```text
1. lire le changelog
2. vérifier les backups
3. mettre à jour
4. vérifier OpenResty
5. tester frontend/API
```

Ne pas faire une mise à jour importante de 1Panel juste avant un déploiement applicatif critique.

## Images Docker

Éviter :

```yaml
image: postgres:latest
```

Utiliser une version explicitement maîtrisée.

Les patch upgrades PostgreSQL doivent néanmoins être planifiés : une version figée ne doit pas rester indéfiniment sans mises à jour de sécurité.

---

# 26. Docker cleanup

Ne pas pruner les images automatiquement après chaque déploiement.
Un nettoyage doit d'abord inventorier et exclure les artefacts exacts
de secours, les images/configurations nécessaires à la release courante
et les dépendances du proxy. La politique de rétention sera définie avec
INT-129 ; tant qu'elle n'est pas validée, conserver les artefacts de retour.

À ne jamais automatiser sans réflexion :

```bash
docker system prune -a --volumes
```

`--volumes` peut supprimer de la donnée persistante devenue momentanément non attachée.

Principe :

> ne jamais automatiser une commande destructrice sur les volumes Tervo.

---

# 27. Utilisation quotidienne de 1Panel

Usage normal :

```text
Dashboard
→ CPU / RAM / disk

Containers
→ état / logs

Websites
→ reverse proxy

Certificates
→ HTTPS

Cron
→ backup

Files
→ consultation ponctuelle
```

Pas :

```text
"je modifie le compose directement dans 1Panel"
```

ou :

```text
"je corrige un fichier Python directement sur le serveur"
```

Le serveur n'est pas un environnement de développement.

Une correction applicative suit toujours :

```text
local
 ↓
Git
 ↓
CI
 ↓
VPS
```

---

# 28. Modification urgente en production

Si une modification manuelle est absolument nécessaire :

1. documenter le problème ;
2. sauvegarder la configuration précédente ;
3. appliquer le changement minimal ;
4. vérifier le service ;
5. reporter immédiatement le changement dans Git lorsque cela concerne le projet ;
6. supprimer toute divergence temporaire.

Ne jamais laisser durablement :

```text
Git ≠ production
```

sans explication.

---

# 29. Procédure de déploiement normale

Ordre cible de la release INT-129, utilisé manuellement dans INT-111 puis
automatisé sur push `main` dans INT-130 :

```text
Code et tests validés
    ↓
SHA / images exacts et configuration identifiés
    ↓
Ancien artefact conservé, sauvegarde vérifiée, compatibilité évaluée
    ↓
Maintenance / nouveau code non exposé
    ↓
Migration ponctuelle avec la nouvelle image
    ↓
Démarrage des services
    ↓
Readiness DB + smoke tests
    ↓
Exposition rétablie si succès
```

Ce schéma est un contrat à implémenter, pas une suite de commandes validée.
Un échec de migration doit bloquer la publication. Ne pas laisser un
nouveau backend servir le trafic avant son schéma compatible.

Après déploiement :

```bash
cd /opt/tervo

docker compose \
  -f deploy/docker-compose.yml \
  ps

docker compose \
  -f deploy/docker-compose.yml \
  logs --tail=100 backend
```

---

# 30. Smoke tests internes

Après INT-125, définir `TERVO_API_READINESS_URL` avec l'URL locale du
contrat livré (incluant un accès DB réel), puis depuis le VPS :

```bash
: "${TERVO_API_READINESS_URL:?Définir la readiness DB livrée dans INT-125}"

curl --max-time 10 -fsS \
  "$TERVO_API_READINESS_URL" \
  >/dev/null

curl --max-time 10 -fsS \
  http://127.0.0.1:3000/ \
  >/dev/null
```

Résultat :

```text
exit code 0
```

Un GET `/openapi.json` peut compléter le diagnostic HTTP, mais ne remplace
pas cette readiness. Ces commandes n'ont pas été exécutées sur Tervo VPS,
dont la stack n'est pas encore déployée.

---

# 31. Smoke tests externes

Depuis l'extérieur :

```bash
curl --max-time 10 -fsS -o /dev/null https://app.<domaine>/
# URL HTTPS de readiness à définir après choix du domaine et INT-125
curl --max-time 10 -fsS -o /dev/null "$TERVO_PUBLIC_READINESS_URL"
```

Utiliser des GET et la readiness documentée, pas un HEAD sur une racine
API qui peut légitimement répondre 404/405.

Puis effectuer la recette INT-111 :

```text
connexion
   ↓
dashboard
   ↓
navigation
   ↓
upload photo
   ↓
lecture photo
```

Avec un compte production dédié.

---

# 32. Vérification des ports

Sur le serveur :

```bash
sudo ss -lntp
```

Attendu conceptuellement :

```text
0.0.0.0:22
0.0.0.0:80
0.0.0.0:443

127.0.0.1:7410
127.0.0.1:3000
127.0.0.1:8000
```

Et :

```text
aucun 0.0.0.0:5432
```

Pour PostgreSQL :

```bash
docker ps --format \
  'table {{.Names}}\t{{.Ports}}'
```

Aucune publication `5432` ne doit apparaître.

---

# 33. Vérification réseau complète

Le fait que UFW ne montre que :

```text
22
80
443
```

n'est pas suffisant à lui seul.

Docker manipule ses propres règles réseau.

La vraie preuve est donc la combinaison :

```text
UFW
+
docker compose config
+
docker ps
+
ss
+
test depuis Internet
```

C'est pourquoi Tervo utilise :

```text
127.0.0.1:3000
127.0.0.1:8000
```

et aucun mapping PostgreSQL.

---

# 34. Monitoring

1Panel est suffisant pour le monitoring infrastructure initial de Tervo.

Surveiller principalement :

```text
CPU
RAM
load
espace disque
I/O
conteneurs
logs
```

Pour INT-111, ne pas ajouter une stack :

```text
Prometheus + Grafana + Loki
```

sans besoin concret.

L'objectif est une production simple et maintenable.

---

# 35. Procédure d'incident minimale

## Application inaccessible

```bash
docker compose -f deploy/docker-compose.yml ps

docker compose \
  -f deploy/docker-compose.yml \
  logs --tail=200 backend

docker compose \
  -f deploy/docker-compose.yml \
  logs --tail=200 frontend
```

## Base

```bash
docker compose \
  -f deploy/docker-compose.yml \
  logs --tail=200 postgres
```

## Reverse proxy

Vérifier dans 1Panel :

```text
OpenResty
site
target proxy
certificat
logs access/error
```

## Réseau

```bash
sudo ss -lntp
sudo ufw status verbose
docker network ls
docker network inspect 1panel-network
```

## Ressources

```bash
free -h
df -h
docker stats --no-stream
```

---

# 36. Rollback

Le rollback applicatif doit être possible sans utiliser l'historique de modifications de l'UI 1Panel.

Principe :

```text
Images exactes et configuration de la release précédente conservées
   ↓
Vérification de compatibilité avec le schéma courant
   ↓
Réactivation de ces artefacts sans rebuild
   ↓
Readiness et recette avant sortie de maintenance
```

Un checkout/revert suivi d'un rebuild ne garantit pas de retrouver le
même artefact ; les dépendances et images de base peuvent avoir changé.
Le retour applicatif ne rollback pas automatiquement PostgreSQL.
INT-129 doit **bloquer** un rollback incompatible avec le schéma courant,
pas tenter un downgrade destructif à l'aveugle. La restauration DB relève
d'une décision explicite, après backup/restore testé en INT-128.
Ni rollback ni restauration ne sont déclarés validés par ce guide.

---

# 37. Règles spécifiques pour Fuliyeh

Avant toute opération INT-111 liée au VPS, Fuliyeh doit relire :

```text
notes/backend/deploy/vps/
deploy/docker-compose.yml
.github/workflows/ci.yml
docs/stages/stage7/sprint7.6/tasks.md
docs/todos/backend.md
```

## Fuliyeh doit toujours

- inspecter l'état réel avant de modifier ;
- distinguer configuration écrite et configuration réellement exécutée ;
- fournir les commandes de validation ;
- conserver Docker Compose comme source de vérité ;
- documenter toute modification manuelle 1Panel ;
- vérifier les ports après modification réseau ;
- vérifier les healthchecks après déploiement ;
- tester un backup par restauration avant de déclarer TD-B010 terminé ;
- conserver les secrets hors Git ;
- utiliser un compte réel de recette production ;
- mettre à jour les critères INT-111 uniquement après preuve.

## Fuliyeh ne doit jamais

- exposer 7410 publiquement ;
- exposer PostgreSQL ;
- publier backend/frontend sur `0.0.0.0` ;
- installer un second PostgreSQL via 1Panel ;
- créer Tervo comme application 1Panel ;
- modifier le code directement sur le VPS comme solution permanente ;
- utiliser des identifiants de démonstration en production ;
- exécuter `docker compose down -v` sans demande explicite ;
- exécuter `docker system prune --volumes` ;
- considérer un container `Up` comme preuve que l'application fonctionne ;
- inventer un résultat de test ;
- marquer un critère `[x]` sur la seule base d'une configuration théorique.

---

# 38. Journaliser les changements 1Panel

Chaque changement important effectué via l'UI doit être repris dans :

```text
notes/backend/deploy/vps/
```

Format recommandé :

```markdown
## Modification

Date:
Composant:
Paramètre:
Ancienne valeur:
Nouvelle valeur:
Raison:
Validation:
Rollback:
```

Exemples :

```text
création reverse proxy
création certificat
modification target
création cron backup
modification OpenResty
upgrade 1Panel
```

L'objectif est de ne jamais avoir une configuration importante connue uniquement par l'interface graphique.

---

# 39. Ordre recommandé pour terminer INT-111

## Phase A — 1Panel

```text
[ ] Installer 1Panel
[ ] Vérifier version
[ ] Sécuriser 7410
[ ] Valider tunnel SSH
[ ] Installer/configurer OpenResty
[ ] Vérifier 1panel-network
```

## Phase B — production Tervo

```text
[ ] Cloner Tervo dans /opt/tervo
[ ] ownership tervo:tervo
[ ] créer .env production
[ ] supprimer les fallbacks secrets dangereux
[ ] vérifier docker compose config
```

## Phase C — PostgreSQL

```text
[ ] choisir définitivement PostgreSQL Compose
[ ] créer volume
[ ] lancer DB
[ ] vérifier healthcheck
[ ] définir backup
[ ] effectuer restore de test
[ ] traiter TD-B010
```

## Phase D — application

```text
[ ] build backend/frontend
[ ] migrations
[ ] frontend healthy
[ ] backend healthy
[ ] curl localhost
```

## Phase E — exposition Internet

```text
[ ] DNS frontend
[ ] DNS API
[ ] reverse proxy frontend
[ ] reverse proxy API
[ ] Let's Encrypt
[ ] renouvellement automatique
[ ] HTTP → HTTPS
[ ] test extérieur
```

## Phase F — CI/CD

```text
[ ] VPS_HOST
[ ] VPS_USER
[ ] VPS_SSH_KEY
[ ] DEPLOY_ENABLED=true
[ ] push de validation
[ ] pipeline vert
[ ] déploiement réellement exécuté
```

## Phase G — recette

```text
[ ] login production
[ ] dashboard
[ ] upload photo
[ ] récupération photo
[ ] API
[ ] frontend
[ ] logs propres
```

## Phase H — clôture

```text
[ ] mettre à jour INT-111
[ ] compléter notes/backend/deploy/vps/
[ ] documenter erreurs + corrections
[ ] compléter notes/backend/sprint7.6/
[ ] revoir todos
```

---

# 40. Definition of Done INT-111

INT-111 se clôt sur la **mise en service manuelle** et les critères de son
planning, après INT-124 à INT-129. Le déploiement automatisé GitHub Actions
relève d'INT-130 et ne conditionne pas sa propre recette préalable.
Une CI de vérification verte ne prouve ni publication ni disponibilité.

```text
Release manuelle INT-129, artefacts identifiés, migrations contrôlées
   │
   ▼
VPS
   │
   ├── PostgreSQL healthy
   ├── backend prêt, DB réellement joignable
   └── frontend disponible
          │
          ▼
      OpenResty
          │
          ▼
        HTTPS
          │
          ▼
     utilisateur
```

et lorsque les données sont protégées :

```text
PostgreSQL
   ├── volume
   ├── backup
   └── restore vérifié

Uploads
   ├── volume
   ├── backup
   └── restore vérifié
```

et lorsque la surface publique reste :

```text
22
80
443
```

avec :

```text
7410  → privé
3000  → loopback
8000  → loopback
5432  → non publié
```

---

# 41. Résumé de la doctrine Tervo

```text
1Panel n'héberge pas Tervo.
Docker Compose héberge Tervo.

1Panel n'est pas la source de vérité.
Git l'est.

1Panel ne déploie pas Tervo.
GitHub Actions le fait.

1Panel ne possède pas PostgreSQL.
Le Compose Tervo le possède.

1Panel gère l'entrée du serveur :
proxy, HTTPS, monitoring et opérations.

Les données ont toujours :
volume + backup + restore testé.

Tout ce qui est public est volontaire.
Tout le reste reste privé.
```

Cette séparation permet de garder les avantages de 1Panel sans transformer Tervo en application dépendante du panel.