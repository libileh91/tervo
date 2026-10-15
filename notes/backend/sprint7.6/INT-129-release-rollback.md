# INT-129 — release et rollback : preuve locale partielle

**INT-129 non livrée ; script encore en brouillon non commité. Aucun déploiement VPS.** Une seule stack UUID,
des identifiants fictifs et un seul build utile ; aucun pytest/harness ajouté.

## Commandes natives d'abord

Depuis un checkout propre explicite, avec `deploy/.env` privé (600), sans
variables TERVO exportées ni `.env` racine concurrent :

```sh
# Hôte Docker de recette, depuis le checkout choisi ; pas le VPS aujourd'hui.
root="$(pwd)"
project="$(basename "$root")"
ENV_FILE="$root/deploy/.env"
dc() { docker compose --env-file "$ENV_FILE" -p "$project" -f "$root/deploy/docker-compose.yml" "$@"; }
dc config --quiet
dc build backend frontend
```

`dc` garde le même env/Compose/projet dans chaque commande. Attendu pour
`config --quiet` : silence et code 0. Pour `build` : fin d'export des deux images,
code 0 ; aucune application n'est démarrée. En cas de refus, ne pas poursuivre.

Le backend utilise `build.network: host` pour les téléchargements Linux.
Ce n'est pas un réseau runtime : PostgreSQL reste non publié, les HTTP restent
sur `127.0.0.1` et les services sur leurs bridges privés. Le label VCS final
du Dockerfile ne réinvalide plus APT à chaque SHA.

Avant toute migration : accès public/autres écrivains maintenus hors service,
console Dockge sans opération en cours puis arrêtée, verrou commun au backup.
Sur installation existante, capture INT-128 avant migration. Ne jamais faire
de seed, downgrade, restore ou effacement implicite.

Sur la stack locale vide uniquement, après le build :

```sh
dc up -d --wait --wait-timeout 120 postgres
dc stop backend frontend
dc create --no-build backend frontend
dc run --rm -T --no-deps migrate
dc exec -T postgres sh -c \
  'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /opt/tervo/app-grants.sql'
# Lancer uniquement après succès des migrations et des droits.
dc up -d --no-build --no-deps --wait --wait-timeout 120 backend frontend
# Les ports ci-dessous sont ceux de la recette fictive observée, pas du VPS.
curl --fail http://127.0.0.1:19829/health/ready
curl --fail --output /dev/null http://127.0.0.1:19830/health
curl --fail --output /dev/null http://127.0.0.1:19830/login
```

Retours utiles **observés localement** : build terminé en 16 s, PostgreSQL puis
backend/frontend `Healthy`, tête Alembic `m109e0010001`, grants suivis de `COMMIT`.
Forme du retour readiness (également observée) :

```text
{"status":"ready"}
```

Les deux curls frontend ont reçu HTTP 200 ; leur corps est redirigé vers
`/dev/null`, donc leur succès est silencieux avec code 0. Aucun de ces retours
n'est une exécution sur le VPS. Une erreur de migration/grants/HTTP interdit
de continuer ou de déclarer une release réussie.

Un retour à l'ancienne source suivi d'un rebuild ne constitue pas un rollback :
conserver les images exactes et le modèle résolu privé. Le helper compare
l'empreinte du schéma et la tête Alembic avant rollback ; PostgreSQL et ses
volumes ne sont pas remplacés. Une différence exige un roll-forward contrôlé.

## Le script `release.py` — usage et limites actuelles

Ce script regroupe les commandes précédentes pour un futur appel manuel/CI.
**Le documenter ne le rend pas validé : ne pas le lancer en production aujourd'hui.**
Les exemples suivants sont des usages à préparer, pas des commandes rejouées
sur le VPS. La recette native réussie reste distincte de celle du helper complet.

### Préparer les arguments — sur l'hôte Docker choisi

```sh
CHECKOUT=/chemin/du/checkout/tervo
ENV_FILE="$CHECKOUT/deploy/.env"
PROJECT="$(basename "$CHECKOUT")"
STATE_DIR=/chemin/prive/hors-git/releases-tervo
LOCK_FILE=/run/lock/tervo-operations.lock
DOCKGE_ID="$(docker compose -p dockge -f /opt/dockge/compose.yaml ps -a -q dockge)"
REVISION="$(git -C "$CHECKOUT" rev-parse HEAD)"
```

Ces affectations sont silencieuses : elles ne prouvent pas que les chemins
ou services sont corrects. Vérifier la cible avant toute opération.

| Argument | Sens et précondition |
|---|---|
| `--checkout` | Checkout complet, propre et positionné sur le commit demandé. Le script ne change pas de branche. |
| `--env-file` | Chemin absolu du `deploy/.env` de ce checkout, privé ; pas de mot de passe dans les arguments. |
| `--project` | Même nom que le dossier du stack, pour que CLI et entrée Dockge désignent le même projet. |
| `--state-dir` | Répertoire privé `700`, propriétaire opérateur, hors Git ; il contient des configurations résolues **avec secrets**. |
| `--lock-file` | Verrou partagé avec le backup ; refus immédiat s'il est déjà tenu. |
| `--dockge-container` | ID exact de la console officielle, voyant le checkout au même chemin absolu. |
| `--console-idle-confirmed` | Confirmation humaine qu'aucune opération Compose n'est en cours. Ce n'est pas un RBAC. |
| `--maintenance-confirmed` | Accès public et autres écritures SQL/Docker gelés **avant** la commande ; le flag ne configure pas Caddy à votre place. |
| `--revision` | Pour `deploy` : commit Git cible, également attendu dans `TERVO_VCS_REF`. |
| `--release-id` | Pour `rollback` : ID d'un record de secours existant, pas un tag d'image ni un SHA Git seul. |

### Lancer une release

```sh
python3 "$CHECKOUT/deploy/scripts/release.py" deploy \
  --checkout "$CHECKOUT" --env-file "$ENV_FILE" --project "$PROJECT" \
  --state-dir "$STATE_DIR" --lock-file "$LOCK_FILE" \
  --dockge-container "$DOCKGE_ID" \
  --console-idle-confirmed --maintenance-confirmed \
  --revision "$REVISION"
```

Ordre prévu par le code :

1. Verrou, validation env et comparaison des deux entrées Compose en mémoire.
2. Gel de Dockge en conservant son état initial.
3. Checkout/SHA contrôlés, build backend/frontend une fois, borné à 180 s.
4. Images identifiées par leurs IDs exacts et retenues par des tags de secours.
5. PostgreSQL prêt, HTTP arrêté/créé sans démarrage ; backup INT-128 avant
   migration pour une installation déjà enregistrée.
6. Migration, grants, empreinte du schéma **et** de la tête Alembic.
7. Démarrage sans rebuild, attente, trois GET puis publication du record réussi.

Forme **attendue**, non observée jusqu'au bout après correction :

```text
STEP: validate the private environment and explicit CLI model
Environment permissions and Compose configuration valid.
STEP: compare the local include and explicit CLI models in memory
STEP: check and freeze the private Dockge console
STEP: build once while the previous API is still available
STEP: migrate, grant and check before starting HTTP services
PASS: backend readiness, frontend health and login page
PASS: release ID_RELEASE
```

Les logs Docker/SQL s'intercalent entre ces lignes. Le succès global est le
code 0 **après** les GET et l'enregistrement, pas la seule fin du build.
La première release exige un projet sans conteneur/volume existant ; le script
ne transforme pas silencieusement une base présente en « base vide ».

### Retrouver les artefacts et faire un rollback

Sous `STATE_DIR`, les fichiers restent privés :

| Fichier | Utilité |
|---|---|
| `current.json` | Pointeur vers la dernière release enregistrée comme réussie. |
| `ID_RELEASE/record.json` | SHA Git, IDs des images, empreintes de schéma/configuration et projet. |
| `ID_RELEASE/compose.json` | Modèle résolu sans build, avec images par ID ; **ne pas afficher ni committer** car il contient les secrets. |
| `ID_RELEASE/before-migration.tar` | Backup local avant migration lors d'un upgrade ; ce n'est pas une copie hors VPS. |
| `ID_RELEASE/failed.json` | Candidat échoué et état disponible pour diagnostic ; ne signifie pas release réussie. |

Un record fabriqué manuellement pour une recette ne prouve pas que `deploy`
sait le produire automatiquement. Ne pas modifier un record pour forcer un
rollback accepté.

```sh
RELEASE_ID=ID_RELEASE_DE_SECOURS_VALIDE
python3 "$CHECKOUT/deploy/scripts/release.py" rollback \
  --checkout "$CHECKOUT" --env-file "$ENV_FILE" --project "$PROJECT" \
  --state-dir "$STATE_DIR" --lock-file "$LOCK_FILE" \
  --dockge-container "$DOCKGE_ID" \
  --console-idle-confirmed --maintenance-confirmed \
  --release-id "$RELEASE_ID"
```

Le modèle sauvegardé et les images doivent exister et rester intacts.
Le rollback ne remplace que backend/frontend, sans rebuild ni changement de
checkout, pas PostgreSQL ou ses volumes. L'égalité schéma/tête est un garde-fou
conservateur : **pas une preuve générale de compatibilité applicative**.

Retour **observé dans la recette avec record manuel des mêmes artefacts** :

```text
PASS: backend readiness, frontend health and login page
PASS: exact rescue image IDs restored; database unchanged
```

Cela ne démontre pas encore un retour entre deux releases distinctes.

### Si une étape échoue

- Code global non-zéro ; ne pas annoncer la release réussie.
- Une erreur avant migration n'autorise pas un seed ou un effacement.
- Après échec dans la phase de mise à jour, le code tente d'arrêter HTTP et
  peut reprendre la release précédente si son schéma/tête correspondent.
  Cette branche automatique reste non démontrée ici.
- Si le schéma diffère, le rollback est bloqué : garder la maintenance et
  décider d'un roll-forward. Aucun downgrade/restore implicite.
- Dockge reste gelé après échec ou rollback : réconcilier Git/env avec le record
  actif avant de le redémarrer, pour ne pas relancer le candidat défaillant depuis l'UI.

Forme **attendue** d'un refus de schéma, non exercé dans cette recette :

```text
Release failed: Schema differs: rollback blocked; keep maintenance and plan roll-forward. No database downgrade or restore performed.
```

`--recover-from ID_ECHEC` est une option de reprise explicite du brouillon :
elle exige l'état enregistré et les candidats arrêtés. Elle n'a pas été
validée dans ce parcours ; elle ne doit pas être utilisée comme bouton « force ».
`--snapshot-tool` pointe normalement vers `snapshot.py` voisin : ne pas le
remplacer pour contourner le backup. Ne pas partager les JSON privés pour
diagnostiquer un refus.

## Attendu et observé

- Image diagnostic fournie par l'utilisateur :
  `sha256:f0d49c6bded68e4a93e7793f2419fec3fcd82b583b823e5e4bdbe29e3543d0e1`,
  présence vérifiée localement. Aucun nouveau build APT bridge.
- Fixture Git propre dans scratch, projet
  `int129-16f2d470527c46fdaa53070213971e96`.
- Première invocation réelle du helper : environnement et modèles CLI/include
  valides, console gelée, build unique terminé en **16 s** (limite 180 s,
  APT en cache), PostgreSQL healthy. Échec propagé sur
  `create --no-deps` : option inexistante. Aucun début de migration.
- Correction : `create --no-build`, qui ne démarre aucun service.
  Pas de seconde invocation deploy/build : la preuve complète du helper
  après correction reste absente.
- Suite **native sur la même stack**, sans rebuild : création réussie,
  migrations jusqu'à `m109e0010001`, grants réussis, backend/frontend healthy,
  readiness `{"status":"ready"}`, health frontend et login HTTP 200.
- Record privé de secours constitué **manuellement**, à partir des IDs exacts
  du candidat construit, du modèle sans build et du schéma courant, avec les
  primitives existantes du helper. Invocation CLI `rollback --release-id`
  réussie : IDs exacts, schéma inchangé et trois GET réussis. C'est un retour
  vers les mêmes artefacts, **pas** une preuve de rollback entre deux releases
  ni de génération automatique du record par deploy.
- Le gate Dockge réel antérieur sur l'arbre
  `8399aad83a02bded7e264807e8e151f48ed493db` était PASS
  (setup/login/getStack/start/stop, chemins/env/projet/volumes). Il ne vaut pas
  compatibilité générale entre versions Compose. L'égalité locale des modèles
  du helper n'est pas une preuve générale Dockge.

## Limites et nettoyage

INT-129 reste ouverte : deploy corrigé non exécuté de bout en bout, upgrade
avec backup et retour vers une release antérieure non démontrés ici ; refus
sur changement de schéma/tête non exercé dans cette recette bornée. La commande
est réutilisable par un futur appel CI, mais aucune CI n'a été exécutée.

Conteneurs, deux réseaux, deux volumes et quatre tags d'images de cette UUID
supprimés explicitement après recette. Aucun prune global, aucun service/volume
préexistant touché. Console antérieure stoppée `int129-console-d79e93ce7708`
inspectée seulement, laissée intacte ; image diagnostic utilisateur conservée.
Ni VPS, mini-s1, comptes réels, secrets réels, sauvegardes réelles ou déploiement
public utilisés.
