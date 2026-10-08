# INT-125 — Stack reproductible, secrets explicites et readiness DB

**État : implémenté et validé localement en isolation.** Les images se
construisent depuis un export Git sans `dist/`, dépendances locales ou DB.
La recette Docker vérifie disponibilité, panne/reprise DB, migrations sur
une DB neuve, CORS, uploads persistants et identité des images.

**Aucun déploiement VPS ni transfert de données.** Aucun seed, compte
administrateur, certificat, DNS ou release automatisée n'est livré ici.
Les tests physiques utilisent un projet Docker UUID et des secrets fictifs.

Références : [tâche](../../../docs/stages/stage7/sprint7.6/tasks.md),
[cas JSON](../../../docs/stages/stage7/sprint7.6/test-cases.json),
[Compose](../../../deploy/docker-compose.yml),
[modèle d'environnement](../../../deploy/.env.example),
[recette isolée](../../../deploy/check-stack.py).

## 1. Le contrat arrêté avec l'utilisateur

| Élément | Contrat |
|---|---|
| Frontend public futur | `https://tervoapp.com` |
| API publique future | `https://api.tervoapp.com/api/v1` |
| Transport interne | HTTP loopback, derrière OpenResty host validé en INT-124 |
| CORS | Origine frontend explicite, pas `*` |
| Authentification | JWT envoyé en `Authorization`, pas de cookies cross-origin |
| PostgreSQL | Aucun port publié |
| Identité image | Tag d'image et SHA source distincts |
| Déploiement | Différé jusqu'à bootstrap/DB/backup/release et recette publique |

```text
OpenResty host, géré par 1Panel
  ├── domaine frontend → VPS 127.0.0.1:3000 → Nginx conteneur :3000
  └── domaine API      → VPS 127.0.0.1:8000 → FastAPI conteneur :8000
                                                 ↓
                                         PostgreSQL réseau privé
```

Les applications écoutent dans leur conteneur pour recevoir le trafic
Docker ; c'est la **publication sur le VPS** qui est limitée à 127.0.0.1.
Ne pas confondre ce cas avec le bind du core 1Panel, directement sur l'hôte.

Le frontend possède un bridge distinct, sans accès direct au réseau DB.
Le backend et PostgreSQL partagent le réseau `database`. OpenResty n'a
besoin d'aucun bridge externe : il rejoint les publications loopback.
Le Compose ne suppose donc plus l'existence de `1panel-network`.

## 2. Construire sans fichiers cachés du poste

### Backend

La base builder/runtime est identique et figée par digest :

```dockerfile
FROM python:3.11-slim@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce AS builder
```

uv est installé en version exacte `0.11.24`. Le sync utilise
`--frozen --no-group dev --no-install-project`. Le projet n'a pas besoin
d'être réinstallé comme un package pour lancer `app.main` depuis `/app`.

Le contexte source est copié par liste :

```dockerfile
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini main.py ./
```

Pas de `COPY . .` backend ni de SQLite du poste. Le runtime reçoit la
venv, le code et les migrations ; les dépendances système WeasyPrint sont
conservées, avec `libharfbuzz-subset0` pour la version verrouillée.
Une génération PDF en mémoire a été effectuée dans le conteneur de test.

### Frontend

Le builder Bun `1.2.20` est épinglé, installe avec le lock frozen et exécute
le build. Le runtime Nginx est également épinglé, puis :

```dockerfile
COPY --from=builder /app/dist/ /usr/share/nginx/html/
```

`dist/` n'est plus une entrée du build. Les `.dockerignore` excluent
environnements, dépendances du poste, assets générés et fichiers sensibles.
Le build normal, Docker et la CI passent par la même validation :

```json
"build": "bun scripts/validate-production-config.ts && vite build"
```

Un build de production sans URL API valide échoue, au lieu de produire
silencieusement un bundle qui ne fonctionnerait qu'au runtime.

### Versions, digests et limites

| Base / outil | Référence retenue |
|---|---|
| Python | `python:3.11-slim` + digest fixe, observé 3.11.17/Trixie |
| uv | `0.11.24` |
| Bun builder | `1.2.20` + digest fixe |
| Nginx runtime | `nginx:alpine` + digest fixe, observé 1.31.6 |
| PostgreSQL de recette/configuration | `17.7` + digest fixe |

Les références complètes vivent dans les Dockerfiles/Compose, pas un
second DAT. Les versions Python et JS sont résolues par les lockfiles.
APT reste mutable : un digest de base et des locks ne promettent pas
une build bit-identique à toute date.

PostgreSQL 17.7 a été validé sur une DB **neuve**. Cela ne prouve pas un
upgrade d'une base existante 17.4, ni une reprise du mini-s1.

## 3. Environnement : une source explicite, pas des valeurs de secours

Le fichier réel est `deploy/.env`, ignoré par Git, avec mode 600 ou 400.
Le modèle contient des secrets **vides** pour provoquer un refus.

| Variable | Rôle |
|---|---|
| `TERVO_IMAGE_TAG` | Version/tag de l'artefact Docker |
| `TERVO_VCS_REF` | SHA source complet, label OCI |
| `TERVO_DB_NAME`, `TERVO_DB_USER`, `TERVO_DB_PASSWORD` | Configuration SQL explicite |
| `SECRET_KEY` | Signature JWT |
| `FRONTEND_ORIGIN` | Origine autorisée par CORS |
| `VITE_API_BASE_URL` | URL publique compilée dans le frontend |
| `BACKEND_PORT`, `FRONTEND_PORT` | Publications loopback |

Commande de validation, sans démarrage ni rendu public des secrets :

```bash
sh deploy/validate-env.sh /chemin/absolu/deploy/.env
```

Le script refuse un symlink, des permissions ouvertes et les variables
Compose déjà exportées dans le shell. **Les exports ont priorité sur
`--env-file`** : un fichier incomplet pourrait sinon paraître valide.
Le refus évite aussi que la validation utilise un secret ambiant différent.

Il appelle `config --quiet`, puis lit le JSON résolu uniquement en mémoire
pour vérifier le format du SHA. Ni le JSON ni les secrets ne sont affichés.
Les paramètres du client Docker ne sont pas supprimés.

Le SHA est distinct du tag : un tag de test peut être UUID, alors que
le label contient le vrai SHA de l'objet exporté. Le validateur vérifie
la forme du SHA ; il ne signe pas le code ni ne prouve à lui seul son
contenu. Le helper vérifie l'identité avec l'objet qu'il exporte ; la release
INT-129 devra vérifier le checkout réel.

Générer les secrets dans le terminal privé/gestionnaire, jamais dans le chat
ou Git. Préférer des valeurs aléatoires hexadécimales pour éviter des erreurs
dotenv. Pour `$`, `#` ou espaces, utiliser les règles de quoting dotenv.
L'alphabet de recette inclut `@`, `#`, `$`, `/`, `%` et `:`.

Le JSON de `docker compose config` **double les dollars littéraux** pour
la sérialisation. Une première assertion naïve l'a pris pour une altération.
La correction compare la représentation sérialisée, puis vérifie séparément
la valeur exacte **dans le conteneur**. Il ne faut pas modifier le mot de
passe sur la seule base d'un JSON de configuration.

## 4. Settings production et URL DB commune aux deux drivers

`APP_ENV=production` est imposé dans Compose. Les valeurs de développement
SQLite restent disponibles pour les tests/dev, pas comme fallback production.

Validation au démarrage :
- secret JWT d'au moins 32 caractères, refus des defaults connus ;
- mot de passe DB d'au moins 16 caractères ;
- CORS explicitement fourni, origines HTTPS sans credentials/path/query/fragment ;
- soit composants DB, soit `DATABASE_URL`, jamais les deux ;
- un `DATABASE_URL` direct production doit être PostgreSQL authentifié.

La longueur ne prouve pas l'entropie : générer les secrets aléatoirement.
Les erreurs Settings masquent les inputs et les champs sensibles ne sont
pas exposés par le repr normal. Ne jamais imprimer un `model_dump` de Settings.

Construction représentative du code :

```python
url = URL.create(
    "postgresql",
    username=self.TERVO_DB_USER,
    password=self.TERVO_DB_PASSWORD.get_secret_value(),
    host=self.TERVO_DB_HOST,
    port=self.TERVO_DB_PORT,
    database=self.TERVO_DB_NAME,
)
```

Le mot de passe n'est pas concaténé dans une URI YAML. SQLAlchemy gère
l'encodage ; le champ dérivé n'est pas traité comme une deuxième source
explicite lors d'une revalidation du modèle.

`database_url(..., asynchronous=True/False)` sélectionne structurellement :

| Usage | Driver |
|---|---|
| FastAPI | `postgresql+asyncpg` |
| Alembic | `postgresql+psycopg2` |
| SQLite test/dev | Async aiosqlite ou sync sqlite selon le consommateur |

Alembic reçoit directement un objet `URL` :

```python
migration_url = database_url(settings.DATABASE_URL, asynchronous=False)
connectable = create_engine(migration_url, poolclass=pool.NullPool)
```

Il n'injecte plus la chaîne percent-encodée dans `ConfigParser`, qui aurait
interprété `%`. Les migrations jusqu'à `m109e0010001` ont réellement réussi
sur le PostgreSQL jetable avec le mot de passe de recette.
Aucune nouvelle migration ni contrainte métier n'a été ajoutée.

## 5. Readiness : une DB joignable, pas seulement un serveur HTTP

`GET /health/ready` est sans authentification et exclu d'OpenAPI métier.
Le router est intégré **après** le registre explicite des modèles, comme
les autres routers ; la garde de bootstrap n'a pas été affaiblie.

```python
async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
    async with database.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
```

Le budget est de deux secondes. Toute exception du probe, y compris une
erreur native du driver avant son wrapping SQLAlchemy, donne 503 statique.
`CancelledError` reste propagée, pas convertie en réponse de santé.

| Situation | HTTP / corps |
|---|---|
| Connexion et SELECT réussis | `200 {"status":"ready"}` |
| DB indisponible, erreur ou timeout | `503 {"status":"not_ready"}` |

Pas de DSN, mot de passe ou exception renvoyée. Pas de création de table,
seed ou lecture de données métier. SQLAlchemy clôt la connexion/contexte ;
la readiness ne valide pas la présence du schéma ni toutes les permissions.
La migration avant exposition reste un gate de release INT-129.

Le healthcheck Docker appelle cet endpoint avec un timeout client borné.
L'arrêt PostgreSQL a donné 503, puis Docker a marqué le backend `unhealthy`.
Le retour de PostgreSQL a rétabli HTTP 200 et `healthy`.

Le frontend vérifie `index.html` avec `try_files ... =503` sur `/health`,
pas un `return 200` indépendant des assets. Le test retire temporairement
l'index dans **son** conteneur : 503, puis 200 après restauration.

## 6. Une source API pour requêtes, uploads et avis publics

`API_BASE` vient du paramètre explicite ; le hostname du navigateur ne
sélectionne plus une branche historique. Le dev conserve `/api/v1` et
les proxies Vite. La production exige HTTPS et le chemin `/api/v1`.

Les photos sont des chemins `/uploads/...`, pas `/api/v1/uploads/...`.
Le resolver utilise l'origine API pour miniatures et prévisualisations,
refuse changement d'origine, backslashes et traversées, y compris encodées.
Il ne change pas le contrat backend `PhotoRef` ni le stockage physique.

La revue a trouvé deux fetch relatifs oubliés dans ReviewPage.
Ils passent désormais par le client commun :

```typescript
export const reviewsApi = {
  get: (token: string) => api.get<PublicReviewResponse>(`/review/${encodeURIComponent(token)}`),
  submit: (body: ReviewSubmission) => api.post<unknown>("/reviews", body),
};
```

Ces routes publiques ne reçoivent pas de JWT. Le test capture GET/POST,
vérifie l'origine API configurée, le token encodé et le corps sans header
Authorization. Aucune règle métier d'avis ni endpoint backend n'est modifié.

La recette sert aussi un fichier canary sur le volume uploads via le
backend et le retrouve après recréation du conteneur. Ce n'est pas une
recette navigateur authentifiée de photo réelle : elle appartient à INT-111.

## 7. Isolation, logs et limites opératoires

`check-stack.py` exige un objet Git explicite :

```bash
: "${SOURCE_SHA:?Définir le commit ou arbre Git explicite à valider}"
python3 deploy/check-stack.py --revision "$SOURCE_SHA"
```

Il exporte l'objet sans `.git`, `dist/`, `node_modules/` ni SQLite locale,
et utilise un daemon Docker Unix local. Pour les modifications en cours,
le parent a stagé les fichiers concernés et exporté `git write-tree` :
un **arbre source**, pas un commit HEAD prétendu identique.

Projet `tervo-int125-<UUID>`, ports loopback libres, deux volumes neufs,
credentials fictifs mode 600. Le helper ne peut pas certifier un ancien
HEAD en oubliant silencieusement les fichiers non committés.

Son `down --volumes` ne concerne que ce projet UUID. Ses suppressions
d'images ne concernent que ses tags UUID ; jamais de prune global.
Il ne s'agit pas d'une procédure à appliquer à une stack persistante.

Les logs des trois services sont bornés à `10m` × `3` fichiers par service.
Cela ne borne pas WAL, uploads, journal systemd, logs OpenResty ou cache
de build. Seuils de départ recommandés pour l'exploitation :

| Mesure | Alerte | Action |
|---|---|---|
| Disque | 80 % ; critique 90 % | Inventorier images/logs/volumes, préserver secours et données |
| RAM VPS | >80 % durable ; >90 % critique | Mesurer charge, OOM/swap, puis adapter limites |
| Swap / OOM | Activité soutenue ou événements OOM | Diagnostiquer avant modification de quotas |

Ce sont des seuils documentés, pas un monitoring installé ou une mesure
de capacité validée. Pas de nettoyage automatique de volumes/réseaux.
Docker agit avec des privilèges élevés ; backend/Nginx conservent leur
utilisateur conteneur existant, sans prétendre à un durcissement non-root.

`POSTGRES_USER` initialise un **superuser**. Le partage de ce rôle dans la
recette ne prouve pas le moindre privilège : TD-B009 attend INT-127 pour
les rôles bootstrap/migration/application avant une release réelle.

## 8. Résultats réellement obtenus

| Validation | Résultat |
|---|---|
| Backend ciblé config/health/drivers/bootstrap | 27 passed, dernier run sans warning |
| Frontend, incluant URLs et avis publics | 20 passed |
| Typecheck et build public configuré | Réussis |
| Export source final de recette | `3600abe840c04c99a95a3776819cb42dc840b633` |
| Build deux images sans assets du poste | Réussi |
| Env ambiant, secret/SHA manquant, mode 644 | Refusés par la recette |
| Mot de passe réservé | Valeur exacte dans le runtime, connexion/migrations réussies |
| Santé/CORS/SPA/logs | Vérifiés sur les conteneurs |
| Dépendances PDF natives | PDF en mémoire généré |
| Panne DB | HTTP 503 et Docker backend unhealthy |
| Reprise DB | HTTP 200 et healthy |
| Recréation backend | Upload canary conservé |
| Labels SHA | Même valeur que l'objet exporté, par le chemin normal Compose |
| Nettoyage | Conteneurs, deux volumes/réseaux et tags de recette supprimés |

Commandes ciblées exécutées :

```bash
cd backend
uv run pytest tests/test_health.py tests/test_production_config.py \
  tests/test_core.py::TestDatabase tests/test_modular_bootstrap.py -q
cd ../frontend
bun test tests
bun run typecheck
VITE_API_BASE_URL=https://api.tervoapp.com/api/v1 bun run build
```

Le helper a été exécuté depuis la racine avec l'arbre exporté explicitement.
Les premiers essais ont révélé l'ordre du router avant registre et la
sérialisation des dollars ; la revue a révélé avis relatifs, env ambiant,
labels et ancien deploy. Ces écarts ont été corrigés puis revalidés,
pas masqués par une modification des preuves historiques.

## 9. CI et reprise

La CI conserve les tests backend et vérifie Bun 1.2.20/typecheck/build.
Son URL `.invalid` est fictive et ne publie aucun artefact de production.
**Le job deploy historique est supprimé**, pas simplement conditionné par
un commentaire : `DEPLOY_ENABLED=true` ne peut pas lancer ce job absent.
INT-130 le réintroduira avec la commande sûre INT-129.

Aucun run distant CI, push ou déploiement VPS n'est revendiqué.
La CI configurée n'est pas une CI exécutée.

TD-B008/009 restent ouverts pour la DB réelle et les privilèges SQL.
TD-B010 attend décision/reprise/backup réels. Aucun todo débloqué n'a été
clôturé sur la seule réussite des conteneurs de recette.

Prochaine tâche après feu vert : **INT-126**, bootstrap administrateur sûr.
Ne pas lancer `app.seed`, créer la DB réelle, basculer le DNS ou publier
Tervo pour prolonger cette tâche. Une stack construisible et disponible
en isolation n'est pas encore une mise en service.
