# INT-125 — Comprendre les choix techniques de la stack de production

> **Objectif**
>
> Cette note explique les concepts utilisés dans INT-125 avant de revenir sur le code.
> Elle complète `INT-125-stack-reproductible.md` : la note de livraison explique **ce qui a été fait** ;
> celle-ci explique **pourquoi**, avec un angle cours + entretien.
>
> **Périmètre : documentation seulement.** Aucun déploiement VPS, DNS, certificat, base réelle ou release n'est effectué ici.

---

# 0. Le problème qu'INT-125 cherche à résoudre

La question centrale est :

> **Peut-on partir d'un checkout Git propre, fournir une configuration explicite, construire Tervo et obtenir une stack logique cohérente sans dépendre de fichiers cachés sur le poste du développeur ?**

INT-125 cherche donc une stack :

- reconstructible depuis les sources ;
- traçable jusqu'à la révision Git utilisée ;
- configurée explicitement ;
- isolée réseau ;
- testable avant production ;
- capable de dire qu'elle n'est pas prête si PostgreSQL est indisponible.

```text
Source Git
   │
   ▼
Docker build
   │
   ├── image backend
   └── image frontend
           │
           ▼
      docker compose
           │
           ├── frontend
           ├── backend
           └── PostgreSQL
                  │
                  ▼
            health/readiness
                  │
                  ▼
     OpenResty / 1Panel
                  │
                  ▼
               Internet
```

Le point important : **chaque étage répond à une question différente**.

---

# 1. Les trois moments à ne jamais confondre

## 1.1 Build time — construction

C'est le moment où l'on fabrique l'image.

Frontend :

```text
Vue + TypeScript + dépendances
            │
            ▼
         Vite build
            │
            ▼
          dist/
            │
            ▼
       image Nginx
```

Certaines valeurs sont déjà figées ici, notamment `VITE_API_BASE_URL`.

Changer ensuite seulement l'environnement du conteneur Nginx ne réécrit pas le JavaScript déjà compilé.

## 1.2 Runtime — exécution

C'est le moment où le conteneur tourne.

```text
image backend
      │
      ▼
conteneur FastAPI
      │
      ├── lit ses variables d'environnement
      ├── ouvre des connexions PostgreSQL
      └── sert des requêtes HTTP
```

Les secrets backend appartiennent principalement à ce niveau : `SECRET_KEY`, credentials DB, paramètres DB.

## 1.3 Deploy time — mise en service

C'est le moment où l'on met réellement les images en production :

```text
images validées
    ↓
variables production
    ↓
migrations DB
    ↓
démarrage services
    ↓
health/readiness
    ↓
reverse proxy / DNS / HTTPS
    ↓
exposition publique
```

**INT-125 ne réalise pas encore cette dernière étape complète.** Il prépare et valide la stack en isolation.

---

# 2. « Reproductible » ne veut pas dire « bit-identique »

Dans Tervo, on veut surtout dire :

> **Un checkout propre contenant les mêmes sources et les mêmes fichiers de verrouillage doit permettre de reconstruire la stack sans dépendre d'artefacts locaux cachés.**

Cela ne promet pas forcément que chaque octet de l'image sera identique dans dix ans.

| Terme             | Idée                                              |
| ----------------- | ------------------------------------------------- |
| Reconstructible   | Je peux reconstruire depuis les sources déclarées |
| Répétable         | Le même processus peut être relancé               |
| Traçable          | Je sais quelle source a produit l'artefact        |
| Bit-reproductible | Le résultat binaire est exactement identique      |

INT-125 améliore surtout les trois premiers points. APT reste par exemple un input mutable.

---

# 3. Pourquoi tester depuis un checkout propre

Un projet peut fonctionner uniquement parce que le poste du développeur contient déjà :

- un `dist/` ancien ;
- un `.env` oublié ;
- une SQLite locale ;
- des dépendances installées ;
- un fichier généré non versionné.

La vraie question est :

```text
git clone / git archive
        │
        ▼
aucun dist
aucun node_modules
aucune DB locale
aucun .env secret
        │
        ▼
build
```

Si le build fonctionne encore, il dépend réellement de ce que le projet déclare.

---

# 4. Image, conteneur et registry

## Image

Une image Docker est un artefact immuable servant de modèle.

```text
tervo-backend:release-demo
```

Elle contient système de fichiers, runtime, dépendances, code, métadonnées et commande de démarrage.

## Conteneur

Un conteneur est une instance créée à partir d'une image. Il peut être
en cours d'exécution ou arrêté : son existence ne garantit pas que le
service est disponible.

```text
image
  │
  ├── container A
  └── container B
```

## Registry

Un registry stocke et distribue les images : Docker Hub, GHCR, registry privé, etc.

INT-125 travaille surtout sur **la construction et l'identification**. La conservation d'un artefact de release exact et son rollback appartiennent aux tâches suivantes.

## OCI : des standards pour les conteneurs, pas un stockage objet

Ici **OCI signifie Open Container Initiative**. C'est une initiative qui
définit des standards pour le format des images, leur exécution et leur
distribution. Ce n'est ni un service de stockage ni un algorithme de hash.
À ne pas confondre avec l'autre acronyme OCI, Oracle Cloud Infrastructure.

| Terme                          | Nature                   | Rôle                                            |
| ------------------------------ | ------------------------ | ----------------------------------------------- |
| OCI Image Specification        | Standard                 | Décrire manifeste, configuration et layers      |
| OCI Runtime Specification      | Standard                 | Décrire l'exécution du bundle d'un conteneur    |
| OCI Distribution Specification | Standard d'API           | Distribuer des manifests et blobs               |
| Registry                       | Service                  | Stocker/distribuer les artefacts via cette API  |
| Object storage                 | Mode/service de stockage | Conserver des objets par bucket et clé          |
| Digest                         | Empreinte de contenu     | Identifier un manifeste, une config ou un blob  |
| Label d'image                  | Métadonnée clé/valeur    | Déclarer une information, par exemple la source |

**OCI ne « correspond » donc pas au digest.** Ses formats et protocoles
utilisent des digests pour référencer certains contenus. C'est comme un
format de document qui peut contenir un identifiant : le format et
l'identifiant ne deviennent pas le même concept.

Dans une image, la configuration contient notamment les paramètres de
lancement et les labels. Le manifeste référence cette configuration et
les layers par digest. Un index multiarchitecture peut référencer
plusieurs manifests de plateforme. C'est un ensemble de contenus reliés,
pas simplement une valeur `sha256`.

Sources officielles :
[présentation OCI](https://opencontainers.org/about/overview/),
[configuration d'image](https://github.com/opencontainers/image-spec/blob/main/config.md),
[clés de métadonnées](https://github.com/opencontainers/image-spec/blob/main/annotations.md).

### De côté : comprendre l'object storage

Un stockage objet conserve habituellement :

```text
bucket / conteneur logique
          ↓
clé de l'objet → octets du fichier + métadonnées
```

Exemple **illustratif, non déployé dans Tervo** :

```text
bucket : tervo-demo
clé    : photos/client-42/avant.jpg
contenu: octets JPEG
meta   : type de contenu, taille, autres informations
```

On récupère ou dépose l'objet via une API, plutôt que d'ouvrir un fichier
sur un disque local. Une clé peut ressembler à un chemin, mais les `/`
peuvent simplement faire partie du nom : ce n'est pas nécessairement
une arborescence de répertoires POSIX.

S3 ou MinIO sont des exemples de services/interfaces de stockage objet.
Ce stockage ne remplace pas la DB relationnelle : la DB porte les relations
et contraintes métier ; le stockage objet porte les bytes. Une application
peut conserver une référence à l'objet dans sa DB.

**Une clé d'objet n'est pas obligatoirement un digest.** Dans l'exemple
ci-dessus, c'est un nom choisi par l'application.

Un registry peut utiliser un stockage objet pour sa persistance interne,
ou un autre backend. Le registry ajoute cependant la gestion des tags,
manifests, blobs et de leur distribution : un bucket seul n'est pas
automatiquement un registry OCI.

Dans Tervo, INT-125 n'a installé ni S3 ni MinIO. Les uploads de la recette
utilisent un volume Docker ; la notion de stockage objet est ici une
explication de concept, pas un changement d'architecture.

---

# 5. Tag, SHA Git et digest Docker

Ces trois valeurs ne répondent pas à la même question :

```text
TAG       → comment j'appelle l'image ?
SHA Git   → avec quelle source l'ai-je construite ?
DIGEST    → quel contenu d'image exact est distribué ?
```

## 5.1 Tag Docker

Exemple :

```text
tervo-backend:release-demo
```

`release-demo` est un tag. On peut utiliser `latest`, `v1.3.0`, une date, un SHA lisible, etc.

Un tag est pratique, mais **mutable** :

```text
tervo-backend:v1 → image A
```

peut plus tard devenir :

```text
tervo-backend:v1 → image B
```

Dans Tervo, `TERVO_IMAGE_TAG` sert à nommer/versionner l'image.

## 5.2 SHA Git

Un SHA Git identifie un objet Git.

Pour un commit :

```text
commit
  ├── tree de fichiers
  ├── parent(s)
  ├── auteur/date
  └── message
```

Tervo stocke la révision source dans le label OCI :

```text
org.opencontainers.image.revision
```

via `TERVO_VCS_REF`.

**Cette valeur peut normalement être le SHA d'un commit Git.** C'est le
choix habituel pour identifier une release issue d'un état committé.
La clé standard `org.opencontainers.image.revision` signifie « identifiant
de révision du contrôle de source » ; elle ne demande pas le digest Docker.

Cela permet de dire : « cette image déclare avoir été construite depuis cette source ».

Mais un label n'est **pas une signature**. La recette compare donc la valeur déclarée à l'objet Git réellement exporté.

## 5.3 Pourquoi un tree Git alors que le code n'était pas encore committé ?

> **L'objectif : tester la stack dans un environnement propre à partir
> d'un snapshot Git (`git write-tree`), pour vérifier qu'elle ne dépend
> pas des fichiers ou artefacts locaux du poste.**

Dans la recette INT-125 exécutée, `TERVO_VCS_REF` était le SHA du **tree**,
pas celui d'un commit. Pour la release de production prévue, la règle
retenue est le SHA du **commit réellement construit**. Aucun des deux
n'est le digest Docker.

Modèle mental :

```text
Working tree
    │ git add
    ▼
Index / staging area
    │ git write-tree
    ▼
Tree object
    │ git commit
    ▼
Commit object
```

Le **tree** représente l'état des fichiers. Le **commit** ajoute notamment parent, auteur, date et message.

INT-125 pouvait donc tester un tree explicite contenant les modifications stagées sans prétendre que l'ancien `HEAD` contenait ces changements.

Cela n'établit **aucune interdiction d'utiliser un commit**. Nous avions
besoin de tester le code avant son commit final : le tree était un choix
de recette adapté à cette situation. Après commit, une release pourra
utiliser la référence du commit sélectionné.

`git rev-parse HEAD` donne le SHA du commit courant, pas celui des
modifications non committées. Le workflow de release devra vérifier que
la source réellement construite correspond à la référence déclarée.
La procédure de release sûre INT-129 reste à implémenter.

## 5.4 Digest Docker

Une référence comme :

```text
python:3.11-slim@sha256:...
```

utilise un digest de contenu.

Le tag :

```text
python:3.11-slim
```

peut être repointé ultérieurement. Le digest, lui, référence un objet OCI précis.

À retenir :

> **tag = nom mutable ; digest = référence par contenu.**

Nuance : un digest peut désigner un index multi-architecture ou un manifest de plateforme. L'`IMAGE ID` local n'est donc pas forcément le même identifiant que le digest d'un registry.

## 5.5 Pourquoi combiner les trois ?

| Question                                          | Information         |
| ------------------------------------------------- | ------------------- |
| Quelle version lisible ai-je lancée ?             | Tag                 |
| Avec quelle source a-t-elle été construite ?      | SHA Git / label OCI |
| Quel artefact exact distribué dois-je reprendre ? | Digest              |

Un même commit peut produire deux images différentes si des arguments de build ou dépendances changent. Exemple Tervo : changer `VITE_API_BASE_URL` change le bundle frontend même sans modifier les fichiers source.

## 5.6 Comment la valeur arrive réellement dans le label de Tervo

**Docker ne calcule pas le SHA Git pour remplir ce label.** On fournit
une référence source ; les instructions de build copient cette valeur
dans une métadonnée de l'image.

```text
Git calcule un identifiant de commit/tree
                 ↓ choix explicite
TERVO_VCS_REF dans le fichier d'environnement
                 ↓ Compose build.args
VCS_REF dans le Dockerfile
                 ↓ instruction LABEL
org.opencontainers.image.revision dans la configuration de l'image
```

Les trois noms ne décrivent pas trois hashes différents :

| Nom                                 | Emplacement                      | Sens                           |
| ----------------------------------- | -------------------------------- | ------------------------------ |
| `TERVO_VCS_REF`                     | Configuration opérateur / helper | Référence source fournie       |
| `VCS_REF`                           | Argument de build Docker         | Même texte transmis au builder |
| `org.opencontainers.image.revision` | Clé du label                     | Même texte stocké dans l'image |

`VCS` signifie Version Control System, ici Git. `REF` désigne la référence.

### Étape 1 — choisir la référence source

Pour un état committé, la lecture suivante donne son identifiant :

```bash
git rev-parse HEAD
```

Elle ne modifie rien et ne construit pas d'image. Sa sortie pourrait
alimenter `TERVO_VCS_REF` dans le fichier privé choisi ; elle ne renseigne
pas automatiquement le fichier à la place de l'opérateur.

Pour les tests INT-125, le helper a fait cette opération lui-même à
partir de **l'argument explicite** reçu. Extraits fidèles de
[check-stack.py](../../../deploy/check-stack.py#L60) :

```python
parser.add_argument("--revision", required=True, help="Explicit Git commit/tree to export")
```

Puis :

```python
revision = run(["git", "-C", str(repo), "rev-parse", args.revision], capture=True).strip()
archive = subprocess.check_output(["git", "-C", str(repo), "archive", revision])
```

Et les deux entrées de son dictionnaire de configuration :

```python
"TERVO_IMAGE_TAG": image_tag,
"TERVO_VCS_REF": revision,
```

Ce dernier bloc est un **fragment du dictionnaire**, pas un programme
Python autonome. `image_tag` était un tag UUID de recette, tandis que
`revision` était le SHA de l'objet réellement exporté. Aucune déduction
« tag UUID → SHA source » n'est faite.

Le [validateur](../../../deploy/validate-env.sh#L29) contrôle le format
hexadécimal de `TERVO_VCS_REF`. Il ne calcule pas cette valeur et ne
prouve pas à lui seul qu'elle décrit le contenu envoyé au build.

### Étape 2 — Compose transmet la valeur

Extrait réel du backend dans
[docker-compose.yml](../../../deploy/docker-compose.yml#L36) :

```yaml
backend:
  image: tervo-backend:${TERVO_IMAGE_TAG:?Set TERVO_IMAGE_TAG to the source revision}
  build:
    context: ../backend
    dockerfile: Dockerfile
    args:
      VCS_REF: ${TERVO_VCS_REF:?Set TERVO_VCS_REF to the full source SHA}
```

`TERVO_IMAGE_TAG` nomme l'image ; `TERVO_VCS_REF` alimente le build arg.
Ces deux valeurs peuvent être identiques si on choisit un SHA comme tag,
mais elles ne sont ni obligatoirement identiques ni calculées l'une depuis
l'autre. Le message du tag recommande une révision ; le code n'impose
le format SHA que sur `TERVO_VCS_REF`.

### Étape 3 — Dockerfile écrit le label

Le [Dockerfile backend](../../../backend/Dockerfile#L40) contient :

```dockerfile
ARG VCS_REF=unknown
LABEL org.opencontainers.image.revision="${VCS_REF}"
```

`ARG` reçoit un paramètre de construction. `LABEL` stocke son texte sous
la clé indiquée. La valeur par défaut `unknown` existe pour un build
manuel sans argument ; la validation du chemin Compose de production
exige une référence source complète, pas cette valeur inconnue.

### Étape 4 — lire uniquement le label, sans afficher les secrets

Commande de lecture **proposée, pas exécutée dans cet enrichissement** :

```bash
: "${IMAGE_REF:?Choisir une image réellement présente à inspecter}"
docker image inspect "$IMAGE_REF" \
  --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
```

Le résultat est la référence source fournie au build. Il n'est pas le
digest de l'image. La commande évite un dump complet de configuration.
Les images UUID de recette ont été nettoyées : ne pas supposer qu'elles
sont encore présentes.

## 5.7 Où est le label par rapport au digest ?

« Label OCI » ne signifie pas « label dont la valeur est forcément un
digest ». La convention propose plusieurs clés avec des sens différents :

| Clé standard                           | Sens de la valeur         |
| -------------------------------------- | ------------------------- |
| `org.opencontainers.image.revision`    | Révision du code source   |
| `org.opencontainers.image.created`     | Date de construction      |
| `org.opencontainers.image.title`       | Nom/titre lisible         |
| `org.opencontainers.image.base.digest` | Digest de l'image de base |

Ces exemples viennent de la convention OCI ; Tervo ne déclare pas
automatiquement toutes ces clés. Ici, notre Dockerfile écrit `revision`.

Structure JSON **simplifiée pour comprendre**, pas une nouvelle config
opérateur :

```json
{
  "config": {
    "Labels": {
      "org.opencontainers.image.revision": "SHA_DE_LA_SOURCE"
    }
  }
}
```

Le label est une entrée du JSON de configuration. Le nom de la clé suit
la convention OCI ; son rôle ici est la révision **source**.
Les annotations de manifest/index et les labels de configuration sont
des emplacements distincts, même si des clés OCI peuvent être employées
dans les deux. `LABEL` ne crée pas automatiquement toutes les annotations
d'un manifest distribué.

La valeur du label entre dans le contenu de configuration :

```text
Code + fichiers de l'image + configuration (dont labels)
                           ↓ hashes des contenus et références
                   identité / digest de l'artefact
```

Modifier un label modifie le JSON de config et donc son ImageID ; le
manifest qui référence cette config change également. Cela ne signifie
pas que la valeur du label **est** ce digest.

En résumé :

```text
SHA Git = hash d'un objet de source
Label revision = texte déclarant ce SHA source
Digest OCI/Docker = hash d'un objet de l'artefact construit
```

## 5.8 Exemple mental : un code, deux builds

Imaginons deux builds du même commit, avec deux URL API compilées
différentes. Ils peuvent déclarer :

```text
Image A : label revision = COMMIT_SOURCE
Image B : label revision = COMMIT_SOURCE
```

Mais le JavaScript frontend n'est pas identique. Les identités d'image
peuvent donc différer :

```text
Image A : digest = DIGEST_A
Image B : digest = DIGEST_B
```

Le label répond « d'où vient le code ? ». Le digest répond « quel artefact
exact ? ». Aucun des deux n'est l'adresse d'un bucket d'object storage.

---

# 6. Docker multi-stage et `dist/`

Le frontend utilise conceptuellement :

```dockerfile
FROM bun AS builder
# install + build → /app/dist

FROM nginx AS runtime
COPY --from=builder /app/dist/ /usr/share/nginx/html/
```

Le builder contient Bun, Vite, TypeScript et les dépendances de compilation.

Le runtime final contient seulement Nginx et les assets statiques.

Avant INT-125 :

```dockerfile
COPY dist/ /usr/share/nginx/html
```

imposait une compilation préalable sur le poste.

Problèmes possibles :

```text
clone neuf → pas de dist → build cassé
```

ou :

```text
source récente + dist ancien → image incohérente
```

Maintenant :

```text
Docker builder → bun run build → dist généré → image Nginx
```

Le `dist/` reste nécessaire ; c'est sa **construction manuelle préalable** qui disparaît.

Extraits réellement livrés dans le
[Dockerfile frontend](../../../frontend/Dockerfile#L4) :

```dockerfile
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN bun run build
```

Puis, dans le stage runtime :

```dockerfile
COPY --from=builder /app/dist/ /usr/share/nginx/html/
```

Le schéma `FROM bun` / `FROM nginx` plus haut reste conceptuel ; le
fichier du projet emploie les références fournisseurs et digests exacts.

---

# 7. Version, lockfile et digest : trois mécanismes différents

| Mécanisme              | Exemple                       | Ce qu'il contrôle                 |
| ---------------------- | ----------------------------- | --------------------------------- |
| Version d'outil        | `uv 0.11.24`, `Bun 1.2.20`    | outil de build                    |
| Lockfile               | `uv.lock`, lock Bun           | versions résolues des dépendances |
| Digest d'image de base | `python:3.11-slim@sha256:...` | objet OCI de base                 |

Ils se complètent. Aucun ne promet seul une build bit-identique.

---

# 8. Pourquoi limiter le contexte Docker

`COPY . .` n'est pas mauvais en soi si `.dockerignore` est strict.

Tervo préfère ici des copies explicites :

```dockerfile
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini main.py ./
```

pour réduire le risque d'embarquer :

- `.env` ;
- SQLite locale ;
- fichiers temporaires ;
- artefacts générés.

La règle générale est :

> **Le contexte de build doit contenir uniquement ce que l'image a besoin de recevoir.**

---

# 9. Configuration explicite et secrets

Une image doit rester générique ; la configuration change selon l'environnement.

```text
même image
  ├── recette
  ├── staging
  └── production
```

Variables Tervo typiques :

```text
SECRET_KEY
TERVO_DB_USER
TERVO_DB_PASSWORD
FRONTEND_ORIGIN
BACKEND_PORT
```

## `.env.example`

Le modèle versionné doit documenter sans publier de vraies valeurs :

```text
SECRET_KEY=
TERVO_DB_PASSWORD=
```

L'absence doit provoquer un échec. C'est du **fail fast** : mieux vaut refuser de démarrer qu'utiliser un default dangereux.

## `${VARIABLE:?message}`

```yaml
SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required}
```

signifie : variable absente ou vide → Compose refuse.

À comparer avec :

```yaml
SECRET_KEY: ${SECRET_KEY:-default}
```

qui introduit un fallback.

Pour un secret de production, le fallback est dangereux.

---

# 10. Pourquoi l'environnement du shell peut casser la reproductibilité

Supposons :

```text
deploy/.env → SECRET_KEY=A
shell       → SECRET_KEY=B
```

Une variable exportée dans le shell peut prendre priorité pendant l'interpolation Compose.

Tu crois alors valider A alors que la stack reçoit B.

Le validateur INT-125 préfère :

```text
configuration ambiguë → erreur
```

plutôt qu'une priorité implicite.

---

# 11. Permissions 600 / 400

```text
600 = propriétaire lecture + écriture
400 = propriétaire lecture seule
```

Groupe et autres n'ont aucun droit.

C'est un contrôle de base utile pour un `.env`, mais pas un gestionnaire de secrets complet : root, Docker, ACL ou sauvegardes restent des sujets séparés.

---

# 12. Secrets backend vs variables `VITE_*`

Règle cruciale :

```text
VITE_* = intégré au bundle frontend = public
```

Donc :

```text
VITE_API_BASE_URL
```

peut être public.

Mais jamais :

```text
VITE_SECRET_KEY
VITE_DB_PASSWORD
```

Tout ce qui arrive dans le navigateur doit être considéré comme exposé.

---

# 13. Pourquoi `URL.create` pour PostgreSQL

Une URI DB ressemble à :

```text
postgresql://user:password@host:5432/database
```

Concaténer manuellement devient fragile si le mot de passe contient `@`, `/`, `%`, `:`, `#`, etc.

SQLAlchemy permet :

```python
URL.create(
    "postgresql",
    username=user,
    password=password,
    host=host,
    port=5432,
    database=name,
)
```

On manipule donc des composants structurés au lieu de bricoler du texte.

Principe général :

> **Quand une donnée possède une syntaxe structurée, préférer une API structurée à la manipulation de chaînes.**

---

# 14. SQLAlchemy, driver et PostgreSQL

```text
code FastAPI
    │
    ▼
SQLAlchemy
    │
    ▼
driver Python
    │
    ▼
PostgreSQL
```

SQLAlchemy fournit ORM, engines, pools, dialectes et construction de requêtes.

Le driver parle réellement à la DB.

Dans Tervo :

| Usage                 | Driver      |
| --------------------- | ----------- |
| FastAPI async         | `asyncpg`   |
| Alembic sync          | `psycopg2`  |
| SQLite async dev/test | `aiosqlite` |

Async/sync ne veut pas dire deux bases différentes.

---

# 15. Pourquoi remplacer le `replace("postgresql://", ...)`

L'ancien code raisonnait sur une chaîne :

```python
url.replace("postgresql://", "postgresql+asyncpg://")
```

Ce n'est pas toujours faux, mais c'est moins robuste qu'une représentation structurée.

Le nouveau helper fait conceptuellement :

```python
url = make_url(raw_url)
backend = url.get_backend_name()
url = url.set(drivername="postgresql+asyncpg")
```

Le bénéfice principal :

> **sélectionner explicitement le driver tout en conservant le reste de la connexion.**

Il ne faut pas dire que tout `replace` détruit automatiquement les mots de passe : ce serait inexact.

Extrait réel de
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

Le code traite aussi une URI déjà munie d'un suffixe sync : il sélectionne
le backend réel puis le driver voulu, plutôt que chercher seulement le
texte exact `postgresql://`.

---

# 16. Le piège `%` avec Alembic / ConfigParser

Une URI peut contenir du percent-encoding :

```text
%40
%2F
```

Mais `%` possède aussi une signification dans l'interpolation `ConfigParser`.

Faire transiter inutilement une URL encodée par une configuration INI peut donc superposer deux syntaxes.

INT-125 transmet directement un objet `URL` au moteur Alembic.

Principe général :

> **Moins on transforme une donnée structurée en texte puis à nouveau en structure, moins on crée de bugs d'échappement.**

---

# 17. Réseau Docker : port interne ≠ port publié

Le backend peut écouter dans son conteneur sur `:8000`.

Compose publie ensuite :

```text
127.0.0.1:8000:8000
```

Donc :

```text
VPS loopback:8000
      │
      ▼
container:8000
```

Le port applicatif n'est pas directement exposé sur toutes les interfaces du VPS.

OpenResty sur l'hôte peut néanmoins joindre `127.0.0.1:8000`.

---

# 18. Pourquoi PostgreSQL n'est pas publié

Backend et PostgreSQL partagent un réseau privé :

```text
backend
   │
   ▼
postgres:5432
```

Aucun besoin de publier :

```text
0.0.0.0:5432
```

Principe :

> **N'exposer que ce qui doit réellement être joint depuis l'extérieur ou l'hôte.**

---

# 19. Pourquoi le frontend n'accède pas au réseau DB

Le frontend Nginx n'a aucune raison de communiquer avec PostgreSQL.

```text
frontend → réseau frontend
backend  → réseau database
postgres → réseau database
```

C'est une application du moindre privilège réseau.

---

# 20. OpenResty / 1Panel : place du reverse proxy

Architecture cible :

```text
Internet
   │ HTTPS
   ▼
OpenResty / 1Panel
   ├── tervoapp.com
   │      ↓
   │  127.0.0.1:3000
   │      ↓
   │   frontend
   │
   └── api.tervoapp.com
          ↓
      127.0.0.1:8000
          ↓
       backend
          ↓
      PostgreSQL privé
```

Le reverse proxy est la porte publique. Les ports applicatifs restent en loopback.

---

# 21. CORS : modèle mental

Une origine est :

```text
scheme + host + port
```

Donc :

```text
http://localhost:5173
http://127.0.0.1:5173
https://tervoapp.com
```

sont trois origines distinctes.

CORS est une politique navigateur permettant ou non au JavaScript d'une origine de lire une réponse cross-origin.

Ce n'est pas :

- un firewall ;
- une authentification ;
- une ACL backend.

Un `curl` n'est pas bloqué par CORS comme un navigateur.

Les routes privées doivent toujours vérifier JWT, rôles et permissions.

---

# 22. Pourquoi 5173 en développement

Vite utilise généralement :

```text
frontend : localhost:5173
backend  : localhost:8000
```

Si le navigateur appelle directement `8000`, c'est cross-origin et le backend doit autoriser l'origine frontend.

Avec un proxy Vite :

```text
browser → localhost:5173/api/v1 → Vite proxy → localhost:8000
```

le navigateur voit une requête same-origin vers `5173`.

Lien avec le code : [vite.config.ts](../../../frontend/vite.config.ts#L12)
demande `port: 5173` et proxifie `/api` vers `http://localhost:8000`.
Les defaults backend de
[Settings](../../../backend/app/config.py#L46) sont :

```python
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

Ils servent au développement, pas à sélectionner le port d'écoute API.
En production, le Compose fournit une liste depuis `FRONTEND_ORIGIN` et
le validator refuse les defaults implicites. Le parcours dev relatif
avec proxy ne nécessite pas de franchir CORS côté navigateur.

En production Tervo :

```text
frontend = https://tervoapp.com
API      = https://api.tervoapp.com/api/v1
```

Les hosts diffèrent, donc CORS doit autoriser explicitement :

```text
https://tervoapp.com
```

---

# 23. Process running, liveness, readiness, test métier

| Niveau          | Question                                       |
| --------------- | ---------------------------------------------- |
| Process running | Le processus existe-t-il ?                     |
| Liveness        | Le service est-il vivant ?                     |
| Readiness       | Peut-il actuellement servir correctement ?     |
| Test métier     | Un vrai parcours utilisateur fonctionne-t-il ? |

Un FastAPI peut répondre HTTP alors que PostgreSQL est arrêté.

Donc `/openapi.json` n'est pas une readiness DB.

---

# 24. Pourquoi `SELECT 1`

Voici le cœur réel de
[readiness()](../../../backend/app/core/health.py#L17), extrait de son
bloc `try` dans une fonction async :

```python
async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
    async with database.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
```

La question testée est :

> **Puis-je ouvrir une connexion et exécuter une requête minimale ?**

On évite une table métier particulière, car la readiness ne doit pas dépendre d'un client ou d'une intervention existante.

---

# 25. Pourquoi un timeout de readiness

Sans timeout :

```text
DB bloquée → probe potentiellement long
```

Avec une limite :

```text
DB indisponible → délai borné → 503
```

Le healthcheck doit lui-même être rapide et prévisible.

---

# 26. Pourquoi HTTP 503

`503 Service Unavailable` signifie :

> le service existe, mais il n'est momentanément pas disponible pour servir normalement.

C'est cohérent avec :

```text
FastAPI vivant + PostgreSQL indisponible
```

---

# 27. `unhealthy` ne signifie pas « redémarré automatiquement »

Docker peut marquer :

```text
healthy
unhealthy
```

Mais `restart: unless-stopped` réagit principalement à la fin du processus.

Un processus peut rester vivant tout en étant `unhealthy`.

C'est un piège classique d'entretien.

---

# 28. Readiness ne prouve pas que les migrations sont à jour

`SELECT 1` peut réussir sur une DB vide.

Donc :

```text
readiness OK
```

ne prouve pas :

```text
tables Tervo présentes
migrations à jour
permissions métier suffisantes
seed effectué
```

Ces vérifications appartiennent au workflow de release.

---

# 29. Health frontend

Un faux endpoint :

```nginx
return 200;
```

pourrait répondre 200 alors que `index.html` est absent.

Tervo vérifie donc la capacité réelle à servir l'asset principal.

```text
index absent → 503
index présent → 200
```

---

# 30. Volumes et persistance

Le système de fichiers d'un conteneur est jetable.

Les données importantes vivent dans des volumes :

```text
PostgreSQL data
uploads
```

La recette vérifie qu'un upload canary survit à la recréation du backend.

---

# 31. Pourquoi `down --volumes` est dangereux hors recette

Sur une vraie stack :

```bash
docker compose down --volumes
```

peut supprimer DB et uploads.

INT-125 ne l'utilise que dans un projet isolé avec :

```text
nom UUID
volumes UUID
tags UUID
```

Principe :

> **Une commande destructive n'est sûre que si l'on peut prouver que les ressources ciblées sont jetables.**

---

# 32. Pourquoi un projet Docker UUID

Il isole :

- conteneurs ;
- volumes ;
- réseaux ;
- tags de test.

Cela réduit collisions et suppressions accidentelles entre recette et environnement réel.

---

# 33. Logs bornés

INT-125 borne les logs Docker :

```text
10 MB × 3 fichiers par service
```

Cela limite une partie de la consommation disque.

Mais cela ne borne pas :

- WAL PostgreSQL ;
- uploads ;
- logs systemd ;
- OpenResty ;
- cache de build ;
- images Docker.

Une politique de logs n'est donc pas une politique complète de capacité.

---

# 34. Seuils disque/RAM : alerte ≠ limite

Exemple :

```text
80 % → alerte
90 % → critique
```

Cela signifie : à ce niveau, on investigue.

Ce n'est pas une limite automatique imposée par Docker.

INT-125 documente des seuils ; il n'installe pas encore un monitoring complet.

---

# 35. `POSTGRES_USER` et moindre privilège

Dans l'image officielle PostgreSQL, `POSTGRES_USER` initialise un compte très privilégié.

Pour une recette isolée, cela peut convenir.

Pour une production mature, on sépare typiquement :

```text
rôle bootstrap / owner
rôle migration
rôle application
```

INT-125 ne prétend pas avoir livré cette séparation.

---

# 36. Pourquoi tester une vraie panne DB

Un test unitaire peut simuler :

```text
raise DatabaseError
```

Mais il ne valide pas :

- réseau Docker ;
- pool SQLAlchemy ;
- driver PostgreSQL ;
- timeout ;
- healthcheck Docker ;
- récupération après reprise.

La recette a testé réellement :

```text
PostgreSQL UP
   ↓
backend ready

PostgreSQL STOP
   ↓
503
   ↓
backend unhealthy

PostgreSQL START
   ↓
200
   ↓
backend healthy
```

C'est un test d'intégration/infrastructure.

---

# 37. Ce qu'INT-125 valide réellement

On peut affirmer que :

- les images se construisent depuis une source exportée propre ;
- le frontend fabrique son propre `dist/` ;
- des images de base utiles sont épinglées par version/digest ;
- l'identité de source est portée par le SHA Git ;
- la configuration production exige des valeurs explicites ;
- PostgreSQL n'est pas publié sur l'hôte ;
- backend/frontend sont publiés en loopback ;
- la readiness backend dépend réellement de PostgreSQL ;
- la panne/reprise DB produit bien 503/unhealthy puis 200/healthy ;
- les uploads persistent après recréation du backend ;
- CORS et URL API sont explicites ;
- les logs Docker sont bornés ;
- la recette destructive est isolée par projet UUID.

---

# 38. Ce qu'INT-125 ne valide pas

INT-125 ne prouve pas :

- qu'un VPS de production est déployé ;
- que le DNS pointe vers le VPS ;
- que Let's Encrypt fonctionne ;
- qu'une DB historique 17.4 a été migrée vers 17.7 ;
- que les rôles SQL de moindre privilège sont prêts ;
- qu'un backup/restore production fonctionne ;
- qu'un compte admin production existe ;
- qu'une release a été publiée dans un registry ;
- qu'un rollback d'artefact exact est opérationnel ;
- que la CI distante a exécuté le pipeline ;
- que toute l'application métier fonctionne en E2E navigateur.

Savoir distinguer **testé**, **configuré**, **prévu** et **déployé** est important en entretien.

---

# 39. Local ≠ dev

Deux phrases différentes :

```text
je lance une stack production localement
```

et :

```text
je lance un environnement de développement
```

Une recette locale de production peut utiliser Nginx, images finales et `APP_ENV=production`.

Un environnement dev cherche plutôt hot reload, Vite, Uvicorn reload et sources montées.

Donc :

```text
local ≠ dev
production ≠ forcément VPS
```

---

# 40. Les principes d'ingénierie derrière INT-125

## Fail fast

```text
secret absent → erreur immédiate
```

## Explicit over implicit

```text
origine CORS explicite
URL API explicite
source env explicite
révision Git explicite
```

## Least exposure

```text
PG non publié
services applicatifs en loopback
```

## Separation of concerns

```text
build ≠ runtime ≠ deployment
```

## Immutable infrastructure

On reconstruit une image plutôt que de patcher manuellement le conteneur en production.

## Traceability

```text
source Git → label OCI → image
```

## Defense in depth

```text
validate-env
    +
Settings validation
    +
Compose
    +
readiness
    +
recette Docker
```

Aucun contrôle unique n'est suffisant.

---

# 41. Architecture mentale complète

```text
                         INTERNET
                            │
                        HTTPS :443
                            │
                            ▼
                 ┌────────────────────┐
                 │ OpenResty / 1Panel │
                 │      sur VPS       │
                 └───────┬──────┬─────┘
                         │      │
             127.0.0.1:3000    127.0.0.1:8000
                         │      │
                         ▼      ▼
                 ┌──────────┐ ┌──────────┐
                 │ Frontend │ │ Backend  │
                 │  Nginx   │ │ FastAPI  │
                 └──────────┘ └────┬─────┘
                                   │
                              réseau Docker
                                database
                                   │
                                   ▼
                              ┌──────────┐
                              │PostgreSQL│
                              │non publié│
                              └──────────┘
```

Construction :

```text
Git tree / commit
       │
       ├───────────────┐
       ▼               ▼
backend Dockerfile   frontend Dockerfile
       │               │
       │             Bun builder
       │               │
       │             Vite build
       │               │
       ▼               ▼
backend image        dist/
                       │
                       ▼
                   Nginx image
```

---

# 42. Questions d'entretien — réponses courtes

## Q1 — Pourquoi pinner une image par digest ?

Parce qu'un tag est mutable. Le digest référence un objet OCI par contenu et évite qu'un même tag fournisse silencieusement une autre base.

## Q2 — Différence tag / SHA Git / digest ?

Tag = nom lisible ; SHA Git = identité de la source ; digest = identité de contenu OCI distribué.

## Q3 — Le SHA Git suffit-il pour reproduire exactement l'image ?

Non. Les arguments de build, les dépendances externes et la configuration de compilation peuvent changer l'artefact.

## Q4 — Pourquoi un multi-stage frontend ?

Pour utiliser Bun/Vite uniquement pendant la compilation et livrer une image runtime plus petite/simple avec Nginx + assets.

## Q5 — Pourquoi ne plus copier `dist/` depuis le poste ?

Parce qu'un checkout neuf peut ne pas l'avoir et qu'un `dist/` local peut être périmé.

## Q6 — Différence liveness / readiness ?

Liveness : le service vit-il ? Readiness : est-il capable de servir correctement avec ses dépendances nécessaires ?

## Q7 — Pourquoi `SELECT 1` ?

Pour tester une vraie connexion DB avec une requête minimale, sans dépendre d'une donnée métier.

## Q8 — Docker redémarre-t-il automatiquement un conteneur unhealthy ?

Pas simplement parce qu'il devient unhealthy. Une restart policy agit surtout quand le processus s'arrête.

## Q9 — Pourquoi PostgreSQL n'est-il pas publié ?

Seul le backend a besoin de le joindre via le réseau Docker privé. Publier 5432 augmenterait inutilement la surface d'exposition.

## Q10 — Pourquoi backend/frontend sur 127.0.0.1 ?

Pour permettre au reverse proxy local de les joindre sans exposer directement leurs ports applicatifs sur toutes les interfaces du VPS.

## Q11 — CORS bloque-t-il curl ?

Non. CORS est principalement une politique navigateur. L'authentification et le firewall restent nécessaires.

## Q12 — Pourquoi asyncpg et psycopg2 ?

FastAPI utilise un moteur async ; Alembic utilise ici une chaîne sync. Les deux parlent à la même base PostgreSQL.

## Q13 — Pourquoi `URL.create` ?

Pour manipuler une URL structurée et laisser SQLAlchemy gérer correctement credentials et encodage.

## Q14 — Pourquoi refuser une variable déjà exportée dans le shell ?

Pour éviter qu'elle écrase silencieusement le `.env` choisi et rende la configuration ambiguë.

## Q15 — Pourquoi `.env.example` vide ?

Pour documenter les variables nécessaires sans publier de secrets et provoquer un échec si elles ne sont pas configurées.

## Q16 — Pourquoi jamais de password dans `VITE_*` ?

Parce que les variables Vite sont compilées dans les assets envoyés au navigateur et sont donc publiques.

## Q17 — Pourquoi tester une panne DB réelle ?

Pour valider réseau, driver, SQLAlchemy, healthcheck Docker et récupération, pas seulement une exception mockée.

## Q18 — Pourquoi un projet Docker UUID ?

Pour isoler conteneurs, volumes, réseaux et nettoyage de recette des ressources persistantes.

## Q19 — Qu'est-ce qu'INT-125 ne fait pas encore ?

Pas de vraie release, pas de VPS modifié, pas de DNS/HTTPS, pas de backup/restore réel, pas de bootstrap admin ni de moindre privilège SQL complet.

---

# 43. Réponse d'entretien en 60 secondes

> « Sur Tervo, j'ai travaillé sur une stack Docker reconstructible à partir d'un checkout propre. Le frontend est construit dans un multi-stage Dockerfile avec Bun/Vite puis servi par Nginx, donc on ne dépend plus d'un `dist/` généré manuellement. J'ai séparé le tag d'image, la révision Git source et les références OCI par digest pour améliorer la traçabilité. En production, la configuration est explicite : pas de fallback critique, PostgreSQL n'est pas publié, et backend/frontend ne sont exposés qu'en loopback derrière OpenResty. J'ai aussi ajouté une readiness FastAPI qui exécute un `SELECT 1` borné sur PostgreSQL ; la recette coupe réellement la DB, vérifie 503/unhealthy, puis le retour à 200/healthy. L'objectif d'INT-125 n'était pas encore de déployer le VPS, mais de disposer d'une stack construisible, testable et traçable avant la release. »

---

# 44. Les cinq phrases à retenir

```text
1. Un tag nomme une image ; un digest identifie son contenu ; un SHA Git identifie la source.

2. Une stack reproductible doit pouvoir être reconstruite depuis une source propre,
   pas depuis des fichiers générés manuellement sur le poste.

3. Build-time, runtime et deploy-time sont trois moments différents.

4. Readiness signifie « prêt à servir », pas seulement « processus démarré ».

5. Une production sûre doit échouer sur une configuration critique absente
   plutôt que démarrer avec un fallback silencieux.
```

---

# 45. Carte mémoire

```text
SOURCE
  Git commit/tree
      ↓
BUILD
  Dockerfile + lockfiles + base image digest
      ↓
IMAGE
  tag + OCI revision
      ↓
CONFIG
  .env privé + validation + secrets obligatoires
      ↓
RUNTIME
  frontend / backend / PostgreSQL
      ↓
NETWORK
  loopback côté hôte + DB privée
      ↓
HEALTH
  readiness DB + health frontend
      ↓
PROXY
  OpenResty / 1Panel
      ↓
RELEASE
  tâches suivantes : vraie mise en production
```

---

# 46. Ordre conseillé pour réviser

1. Image vs conteneur
2. Build-time vs runtime
3. Tag vs SHA Git vs digest
4. Multi-stage + `dist/`
5. `.env`, secrets et `${VAR:?}`
6. Réseau Docker + loopback + PostgreSQL privé
7. CORS
8. SQLAlchemy / asyncpg / psycopg2
9. Liveness vs readiness
10. Volumes / logs / isolation de recette

Une fois ces dix notions comprises, `INT-125-stack-reproductible.md` devient surtout une description de leur application concrète dans Tervo.
