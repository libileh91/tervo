# INT-125 — Comprendre CORS, images, configuration, drivers et readiness

Cette note répond aux questions de compréhension après INT-125.
Elle complète la [note de livraison](INT-125-stack-reproductible.md) :
la première décrit ce qui a été livré et testé ; celle-ci explique
**pourquoi**, avec les différences entre développement et production.

**Périmètre de cette note : documentation seulement.** Aucun Compose dev
n'est créé, aucun code/runtime modifié et aucun déploiement effectué.
Les options dev/prod de la section 6 sont des recommandations à valider.

## 1. Pourquoi CORS autorise localhost et 127.0.0.1 sur 5173 ?

### Une origine est celle de la page, pas celle de l'API

Pour le navigateur, une origine est le triplet :

```text
protocole + nom d'hôte + port
```

Par exemple :

| URL de la page | Origine |
|---|---|
| `http://localhost:5173/clients` | `http://localhost:5173` |
| `http://127.0.0.1:5173/login` | `http://127.0.0.1:5173` |
| `https://tervoapp.com/clients` | `https://tervoapp.com` — port HTTPS standard |

Le chemin `/clients` n'entre pas dans l'origine. HTTP et HTTPS ne sont
pas interchangeables, et deux ports différents font deux origines.
`localhost` et `127.0.0.1` sont également deux hôtes différents pour cette
règle, même s'ils désignent généralement le même ordinateur.

### D'où vient 5173 ?

C'est le port demandé par le serveur **Vite de développement**, dans
[vite.config.ts](../../../frontend/vite.config.ts#L12). Il ne s'agit pas
d'un port spécialement choisi pour la sécurité ou PostgreSQL.

Dans [Settings](../../../backend/app/config.py#L46), les defaults sont :

```python
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

Cela signifie :

> « Si une page de développement chargée depuis l'une de ces origines
> appelle directement l'API depuis le navigateur, autoriser la lecture
> de sa réponse. »

Cela **ne signifie pas** « faire écouter le backend sur 5173 ».
Le backend reste habituellement sur 8000.

```text
Page chargée depuis localhost:5173
             ↓ fetch direct
API localhost:8000
             ↓ réponse CORS
Access-Control-Allow-Origin: http://localhost:5173
```

La liste contient l'origine **frontend** parce que c'est la page frontend
qui demande l'accès. Ajouter seulement l'adresse de l'API à cette liste
ne résout pas l'autorisation du frontend.

### Nuance importante : notre proxy Vite

Par défaut en dev, sans URL API explicitement configurée, le client
utilise `/api/v1`. Le navigateur contacte alors son propre serveur Vite,
qui transmet la requête au backend :

```text
Navigateur → localhost:5173/api/v1/... → proxy Vite → localhost:8000
```

Pour le navigateur, c'est une requête **same-origin**. Ce parcours n'a
donc pas besoin de CORS pour franchir deux origines côté navigateur.
Les defaults 5173 servent notamment aux appels directs à 8000 depuis
une page de dev ; ils ne sont pas une obligation de chaque appel proxifié.

Le helper frontend livré exige actuellement HTTPS pour une URL API
explicitement configurée, même en dev. Le parcours local usuel est donc
la base relative avec proxy, pas `VITE_API_BASE_URL=http://localhost:8000`.
L'exemple d'appel direct ci-dessus explique CORS, pas une configuration
que ce helper accepterait.

Si Vite utilise un autre port, vérifier son URL réellement affichée.
Le port demandé peut changer si 5173 est occupé. Pour un appel direct
cross-origin, autoriser la nouvelle origine exacte ; pour le proxy,
adapter sa cible si le port backend change.

### En production, ces defaults ne sont pas conservés

Le [Compose](../../../deploy/docker-compose.yml#L46) impose
`APP_ENV=production` et fournit :

```yaml
CORS_ORIGINS: '["${FRONTEND_ORIGIN:?Set the HTTPS frontend origin}"]'
```

Avec le domaine confirmé :

```text
FRONTEND_ORIGIN=https://tervoapp.com
```

Le validator refuse des CORS implicites ou des origines HTTP en production.
Il ne laisse pas simplement les deux defaults locaux actifs.
Le port interne Nginx 3000 n'est pas l'origine publique de la page :
OpenResty la sert en HTTPS sous `tervoapp.com`.

### CORS n'est ni un firewall ni une authentification

CORS est une politique de navigateur. `curl` et un programme serveur ne
deviennent pas interdits d'accès grâce à cette liste. Certaines requêtes
cross-origin peuvent être émises même si le navigateur ne laisse pas lire
la réponse ; d'autres nécessitent un preflight.

Les routes privées exigent toujours leur JWT et leurs droits métier.
Le firewall contrôle le trafic réseau ; le bind loopback contrôle l'écoute.
La liste CORS ne remplace aucun de ces mécanismes.

Le tunnel 1Panel sur 17410 est un autre usage : ce n'est pas le frontend
Tervo à ajouter dans ses CORS.

## 2. Tag, SHA Git et digest Docker : trois informations différentes

**Correction de vocabulaire : le code actuel n'oblige pas le tag à être
un SHA.** INT-125 sépare ces deux variables :

```text
TERVO_IMAGE_TAG → nom/version de l'image
TERVO_VCS_REF   → SHA complet de la source
```

Dans le [Compose](../../../deploy/docker-compose.yml#L36) :

```yaml
image: tervo-backend:${TERVO_IMAGE_TAG:?Set TERVO_IMAGE_TAG to the source revision}
build:
  context: ../backend
  dockerfile: Dockerfile
  args:
    VCS_REF: ${TERVO_VCS_REF:?Set TERVO_VCS_REF to the full source SHA}
```

Le message d'erreur du tag recommande une révision, mais sa syntaxe
n'impose pas un SHA. Le validateur vérifie le SHA de **TERVO_VCS_REF**.

### Le tag : une étiquette pratique

Dans `tervo-backend:release-demo`, `release-demo` est un tag.
On peut choisir un numéro de version, une date ou un SHA Git comme tag.
C'est utile pour retrouver une version, mais un tag peut être réaffecté
à une autre image.

Même un tag qui ressemble à un SHA n'est pas techniquement immutable :
Docker ne vérifie pas qu'il correspond à ce code.

### Le SHA Git : l'identité de la source

Un SHA Git identifie un objet Git. Un commit identifie notamment l'état
du code et ses métadonnées ; un arbre identifie un ensemble de fichiers.
Nos builds de recette ont exporté un arbre explicite pour inclure les
modifications en cours, sans prétendre tester un ancien HEAD.

Le SHA source est transmis au Dockerfile et stocké dans :

```text
org.opencontainers.image.revision
```

Ce label permet de répondre à « avec quelle source a-t-on construit ? ».
Mais c'est une **annotation**, pas une signature : un constructeur pourrait
y mettre une valeur mensongère. La recette compare le label à l'objet
qu'elle a réellement exporté.

### Le digest : l'identité du contenu d'image distribué

Une référence `image@sha256:...` pointe par contenu, pas par étiquette.
Les bases des Dockerfiles et PostgreSQL sont ainsi épinglés : un changement
futur du tag du fournisseur ne suffit pas à changer la base téléchargée.

Précision : une référence peut identifier un manifeste ou un index
multiarchitecture, qui sélectionne ensuite le manifeste de plateforme.
L'ID d'image local montré par Docker peut aussi différer du digest de
manifeste d'un registre. Tous les `sha256:` ne désignent pas le même objet.

### Pourquoi les combiner ?

| Question | Information utile |
|---|---|
| Quelle version lisible ai-je lancée ? | Tag |
| Avec quelle source a-t-elle été construite ? | SHA Git / label |
| Quel artefact exact distribué dois-je reprendre ? | Digest/identité exacte d'image |

Un même commit peut produire deux images différentes si les dépendances
système ou arguments de build changent. Exemple Tervo : modifier
`VITE_API_BASE_URL` change le JavaScript compilé même sans modifier les
fichiers source. APT reste aussi mutable dans le build.

Le SHA Git ne remplace donc pas le digest. Les digests de base, locks et
labels améliorent la traçabilité, sans promettre une build bit-identique.
La conservation et le rollback de l'artefact exact relèvent d'INT-129.

## 3. Qu'est-ce qu'une « source explicite » ? Que fait validate-env.sh ?

Le fichier réel s'appelle
[deploy/validate-env.sh](../../../deploy/validate-env.sh#L1).
Le problème n'était pas seulement « avons-nous une variable ? », mais :

> « D'où vient la valeur effectivement utilisée, et est-ce bien celle
> du fichier privé que l'opérateur vient de choisir ? »

### Pourquoi --env-file ne suffit pas à lui seul

Pour l'interpolation de Compose, une variable exportée dans le shell
peut prendre priorité sur celle du fichier passé à `--env-file`.

Exemple conceptuel, valeurs fictives :

```text
Fichier choisi : SECRET_KEY absent ou différent
Shell courant  : SECRET_KEY déjà exporté
Résultat sans garde : Compose peut utiliser le shell
```

On pourrait donc « valider » un fichier incomplet, ou utiliser une ancienne
valeur sans le savoir. Deux personnes pourraient avoir des résultats
différents en lançant apparemment la même commande.

Le script **refuse cette ambiguïté** : il n'efface pas discrètement les
exports. Il demande de les retirer avant validation. Les variables
nécessaires au client Docker ne sont pas toutes supprimées.

### Les contrôles, dans l'ordre

| Contrôle | Raison |
|---|---|
| Un argument : chemin du fichier | Pas de découverte implicite du « bon » `.env` |
| Fichier régulier, pas un symlink final | Ne pas valider silencieusement un autre fichier |
| Mode 400 ou 600 | Pas de lecture accordée au groupe/autres par les bits Unix |
| Aucun des dix exports Compose ambiants | Le fichier doit être la source choisie |
| `docker compose ... config --quiet` | Vérifier syntaxe et valeurs obligatoires sans afficher le rendu |
| JSON résolu capturé en mémoire | Contrôler le SHA sans publier les environnements |
| SHA complet hexadécimal minuscule de 40 ou 64 caractères | Refuser une révision telle que `manual` ou `latest` |

Commande normale :

```bash
sh deploy/validate-env.sh /chemin/absolu/deploy/.env
```

Dans Compose, `${VARIABLE:?message}` signifie « refuser absent ou vide »,
contrairement à `${VARIABLE:-default}` qui peut permettre un fallback.

Le mode 600 autorise le propriétaire à lire/écrire ; 400 à lire seulement.
Ce contrôle n'est pas un audit des ACL, des sauvegardes, des droits Docker
ou de tous les composants du chemin. Un opérateur root reste privilégié.

### Ce que ce script ne prouve pas

Il ne démarre pas les services, ne se connecte pas à PostgreSQL et ne
vérifie pas un certificat. Le format d'un SHA ne prouve pas l'existence
de son commit ni que l'image a été construite avec celui-ci.

Il ne remplace pas les validators `Settings` au démarrage :
ceux-ci imposent longueurs minimales, CORS HTTPS, PostgreSQL authentifié
et sources DB non ambiguës. Il ne remplace pas non plus la validation
frontend de son URL API au build.

Les couches se complètent :

```text
Fichier/Compose valide → configuration applicative valide → runtime disponible
```

« Sources explicites » désigne aussi le choix DB : composants
nom/utilisateur/mot de passe **ou** une URI complète `DATABASE_URL`.
Fournir les deux laisse une priorité à deviner ; le mode production refuse.

## 4. Pourquoi remplacer les replace de chaînes par database_url ?

### Les trois étages de connexion

```text
Code Python → SQLAlchemy → driver Python → base de données
```

SQLite et PostgreSQL sont des bases. SQLAlchemy est la couche d'accès,
pas le driver qui parle directement à PostgreSQL.

| URL / driver | Consommateur Tervo |
|---|---|
| `sqlite+aiosqlite` | Sessions async SQLite de dev/test |
| `postgresql+asyncpg` | Sessions async FastAPI |
| `sqlite` | Migrations sync SQLite |
| `postgresql+psycopg2` | Migrations sync PostgreSQL |

Async et sync ne signifient pas deux bases : ils décrivent deux façons
d'effectuer les opérations Python sur une même base.

### L'ancien code fonctionnait pour les URI simples

L'ancien helper utilisait `startswith` puis un remplacement ciblé :

```python
if settings.DATABASE_URL.startswith("postgresql"):
    return settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
```

Cela fonctionne pour `postgresql://...`. Mais pour une URI déjà
`postgresql+psycopg2://...`, le test `startswith` est vrai tandis que la
chaîne `postgresql://` n'existe pas : on renvoie le driver sync inchangé.
Un engine async ne peut pas utiliser ce driver sync.

Il ne faut pas prétendre que tout `replace` corrompt les secrets :
ce remplacement ciblé ne faisait pas cela sur une URI bien formée.
Le besoin était de **sélectionner structurellement le driver**, et de
partager cette règle entre runtime et migrations.

### Le nouveau helper, étape par étape

Extrait fidèle de
[database_urls.py](../../../backend/app/core/database_urls.py#L6) :

```python
def database_url(raw_url: str, *, asynchronous: bool) -> URL:
    url = make_url(raw_url)
    backend = url.get_backend_name()
    if backend == "sqlite":
        return url.set(drivername="sqlite+aiosqlite" if asynchronous else "sqlite")
    if backend == "postgresql":
        return url.set(drivername="postgresql+asyncpg" if asynchronous else "postgresql+psycopg2")
    return url
```

1. `make_url` transforme le texte en objet structuré : driver, utilisateur,
   mot de passe, hôte, port, nom de DB et paramètres.
2. `get_backend_name()` donne `postgresql` même avec le suffixe `+psycopg2`.
3. `set(drivername=...)` retourne une URL avec le driver approprié, en
   conservant les autres composants ; il ne modifie pas une chaîne au hasard.
4. `asynchronous=True` sélectionne le runtime, `False` les migrations.
5. `*` impose un argument nommé : écrire `asynchronous=True` est plus clair
   qu'un booléen positionnel sans nom.

Les autres schémas sont renvoyés sans sélection spéciale ; ce n'est pas
une promesse que le projet fournit leurs drivers ou les accepte en production.

### Pourquoi garder _get_async_database_url et retourner str ?

[Le wrapper](../../../backend/app/core/database.py#L13) garde son ancienne
interface, réutilisée notamment par les tests :

```python
def _get_async_database_url() -> str:
    """Retain the historical string interface with structurally selected drivers."""
    return database_url(settings.DATABASE_URL, asynchronous=True).render_as_string(
        hide_password=False
    )
```

Il sélectionne le driver async, puis sérialise l'objet. SQLAlchemy peut
aussi recevoir un objet `URL` directement : retourner du texte ici est
un choix de compatibilité, pas une obligation fondamentale.

`hide_password=False` ne désactive pas une authentification. Cela demande
une URI complète pour la connexion. Une représentation masquée avec `***`
ne contient pas le vrai mot de passe et ne convient pas comme URI réelle.
**Ne pas logger ni afficher la chaîne retournée.**

### Ne pas confondre trois corrections

| Correction | Problème résolu |
|---|---|
| `URL.create` avec composants DB | Construire/encoder des identifiants avec `@`, `/`, `%`, etc. sans concaténation fragile |
| `make_url` / `set(drivername=...)` | Choisir sync/async en conservant la même connexion |
| Objet `URL` transmis à Alembic | Éviter l'interprétation des `%` par `ConfigParser` |

Le problème `ConfigParser` ne provenait pas du `replace` : il provenait
de l'injection d'une URI percent-encodée dans le fichier/configuration INI.
Ces responsabilités sont liées, mais distinctes.

## 5. Readiness : « vivant » n'est pas toujours « prêt à servir »

Un serveur peut répondre en HTTP alors que sa DB est arrêtée.
`/openapi.json` décrit l'API ; il peut être disponible sans que les routes
métier puissent lire ou écrire leurs données.

La **readiness** est un contrôle de préparation au service :
« les dépendances essentielles à ce que je dois faire sont-elles disponibles ? »

Dans Tervo, [GET /health/ready](../../../backend/app/core/health.py#L16) :

1. essaie de prendre une connexion au moteur DB existant ;
2. exécute `SELECT 1`, sans lire de dossier client ni modifier de table ;
3. borne le probe à deux secondes ;
4. renvoie une réponse minimale.

```json
{"status": "ready"}
```

HTTP 200 si réussi ; HTTP 503 avec `{"status":"not_ready"}` sinon.
Aucune exception, adresse DB ou credential n'est renvoyé.

| Concept | Question | Exemple |
|---|---|---|
| Processus running | Le programme est-il lancé ? | `docker ps` |
| Liveness | Répond-il encore / est-il vivant ? | Ping HTTP sans dépendance métier |
| Readiness | Peut-il utiliser sa dépendance nécessaire ? | Connexion DB + SELECT 1 |
| Test métier | Fonctionne-t-il pour un vrai scénario ? | Connexion utilisateur, clôture, photo |

**Nous n'avons pas ajouté un endpoint liveness séparé.** Cette distinction
explique les termes, pas une fonctionnalité supplémentaire livrée.

Le healthcheck Docker utilise la readiness ; la recette a réellement
observé DB arrêtée → API 503 → backend `unhealthy`, puis reprise →
API 200 et `healthy`.

Le statut unhealthy ne redémarre pas automatiquement le conteneur.
`restart: unless-stopped` réagit à la fin du processus, pas à la seule
dégradation de santé. Nous n'avons pas installé d'auto-healer.
Un orchestrateur/proxy peut exploiter la readiness, mais le routage 1Panel
ne devient pas automatiquement conditionnel grâce à ce seul endpoint.

Ce test ne prouve pas que les migrations sont terminées ou que toutes
les permissions métier sont suffisantes. `SELECT 1` peut réussir sur une
DB sans tables applicatives. La release doit donc aussi contrôler le
schéma et les scénarios avant exposition, dans les tâches suivantes.

## 6. Pourquoi remplacer le Compose ? Un dev/prod séparé serait-il mieux ?

**Oui, des Compose dev/prod distincts sont une option pertinente.**
Ce n'est pas incompatible avec les correctifs INT-125.

Le fichier a été **actualisé au même chemin**, pas supprimé de l'historique.
Sa version avant INT-125 est consultable dans Git au commit `8504e1c`.
Nous n'avons pas arrêté ou supprimé une stack existante avec ce changement.

### L'ancien fichier n'était pas vraiment un environnement de dev complet

Il lançait une stack orientée déploiement : PostgreSQL, API et frontend
statique. Il ne livrait ni Vite hot reload ni montage source/reload backend.
Il avait aussi :
- des fallbacks de secrets ;
- une URI DB concaténée ;
- un frontend dépendant de `dist/` déjà présent sur le poste ;
- un réseau externe 1Panel ;
- une santé backend basée sur OpenAPI.

Le garder inchangé aurait conservé ces ambiguïtés. On peut réutiliser
ses idées ou les ports utiles, pas ses valeurs de secours dangereuses
comme si elles étaient une configuration de production sûre.

### Les trois approches possibles

| Approche | Avantage | Limite |
|---|---|---|
| Un seul fichier production utilisé localement | Tester fidèlement les images de production | Pas confortable pour éditer avec hot reload |
| Deux fichiers indépendants dev/prod | Intentions claires, outils/volumes séparés | Quelques paramètres à maintenir dans les deux |
| Base commune + overrides dev/prod | Réduire une duplication réellement commune | Héritages subtils, ports/variables à inspecter après merge |

Le fichier actuel peut servir **localement** à une recette de production,
comme celle que nous avons exécutée en isolation. « Local » désigne le
lieu d'exécution ; « dev » désigne le mode de travail. Ce n'est pas la
même distinction.

Le mode production exige CORS/API HTTPS explicites. Une stack lancée
localement ne transforme pas ces contraintes en mode dev, ni ne fournit
automatiquement DNS/certificats pour le navigateur.

### Ma recommandation pour Tervo

Conserver la stack actuelle comme source de production, et ajouter, si
tu le souhaites, une configuration **dev dédiée** :
- Vite sur 5173 avec hot reload ;
- Uvicorn avec reload, sources montées ;
- SQLite de dev ou PostgreSQL local selon les tests voulus ;
- nom de projet et volumes distincts des données de production ;
- ports publiés uniquement sur loopback ;
- credentials de test, jamais les secrets de production.

Les noms que tu proposes sont valables. Organisation **proposée, non créée** :

```text
deploy/
  dev.docker-compose.yml
  prod.docker-compose.yml
```

Renommer le fichier production nécessiterait aussi d'adapter les helpers
et documents qui utilisent `deploy/docker-compose.yml`. On peut éviter
ce coût initial en gardant ce nom et en ajoutant seulement le fichier dev.

Une base commune n'est intéressante que si ses options sont vraiment
communes. Compose interpole chaque fichier avant de fusionner les
overrides : hériter d'un fichier prod contenant `${SECRET_KEY:?…}` peut
forcer des secrets prod même si l'override veut une configuration dev.

Nous n'avons donc pas livré un Compose dev dans INT-125. C'est une
amélioration possible à cadrer avec ton accord, pas une raison de
réactiver l'ancien fichier tel quel.

## 7. dist : le résultat de la compilation frontend

Les sources comprennent des fichiers Vue, TypeScript et styles. Le
navigateur ne consomme pas directement tous ces fichiers comme le
serveur de développement les voit.

Vite transforme et assemble le frontend :

```text
src/*.vue + TypeScript + styles + dépendances
                    ↓ build
dist/index.html + JavaScript + CSS + images/polices
                    ↓ Nginx
                 navigateur
```

Les noms d'assets avec hash aident notamment à gérer le cache lors d'une
nouvelle version. `dist/` est **généré**, pas une deuxième source de code.
On peut le reconstruire à partir des sources, locks et configuration.

### Avant INT-125

L'ancien Dockerfile faisait :

```dockerfile
COPY dist/ /usr/share/nginx/html
```

Il fallait compiler sur le poste avant Docker. Un clone neuf sans
`dist/` échouait ; un `dist/` ancien pouvait embarquer un frontend qui
ne correspondait plus à la source actuelle.

### Maintenant

[Le Dockerfile](../../../frontend/Dockerfile#L1) utilise deux stages :

```text
Builder Bun : installe les dépendances et génère /app/dist
Runtime Nginx : reçoit uniquement les fichiers construits
```

Extrait livré :

```dockerfile
RUN bun run build
```

Puis :

```dockerfile
COPY --from=builder /app/dist/ /usr/share/nginx/html/
```

Bun sert à construire ; le Nginx final sert les fichiers. Il n'a pas
besoin du serveur Vite ou de tout `node_modules` pour servir ce résultat.
`dist/` reste utile ; c'est sa **construction manuelle préalable** qui a
été supprimée.

`dist/` n'est ni PostgreSQL, ni les photos utilisateurs, ni leurs backups.
Les uploads sont dans un volume dédié. Supprimer un `dist/` de travail
ne doit pas effacer les données métier.

### Une dernière conséquence : les variables VITE sont publiques et compilées

`VITE_API_BASE_URL` est incorporée dans les assets lors du build.
Changer seulement l'environnement du conteneur Nginx ne réécrit pas le
JavaScript déjà construit : il faut reconstruire l'image avec la nouvelle
valeur, dans le workflow de release prévu.

Cette valeur est une adresse publique, pas un secret. Ne jamais mettre
la clé JWT ou un password DB dans une variable frontend `VITE_*`.

## À retenir

- **CORS** : autorisation de lecture cross-origin côté navigateur, pas auth/firewall.
- **5173** : frontend Vite de dev ; production utilise l'origine publique HTTPS.
- **Tag** : étiquette ; **SHA Git** : source ; **digest** : artefact distribué.
- **validate-env.sh** : choix explicite du fichier et garde avant Compose, pas test DB.
- **database_url** : une règle de driver sync/async, sans manipulation fragile du texte.
- **Readiness** : vérification DB bornée, pas une preuve de tout le métier.
- **Compose dev/prod** : séparation utile à prévoir, non implémentée par cette note.
- **dist** : frontend compilé, désormais généré dans le build Docker.
