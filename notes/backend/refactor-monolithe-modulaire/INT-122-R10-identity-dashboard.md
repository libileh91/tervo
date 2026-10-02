# INT-122 — R10 : identité, lecture dashboard et composition finale

> **Planning :** [INT-122](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md#int-122--r10--déplacer-identity-dashboard-et-finaliser-la-composition).
> **Parent :** `17dfc1195527b023e5c2762fae79b693ccbfc95d` (nettoyage après R9 `205969a`).
> **État :** implémenté, vérifié et accepté par l'utilisateur ; commit autorisé dans le worktree Delta attaché. Feu vert distinct R11 reçu.
> **Preuve :** [R10-validation.json](R10-validation.json). Les captures R0 à R9 et l'oracle import restent intacts.

## 1. Reprise : ne pas confondre fin des moves et retrait des façades

R9 est accepté et committé sous `205969a`. Le nettoyage demandé par l'utilisateur
a ensuite retiré caches et namespaces sans code actif dans un commit distinct,
`17dfc11`. Les 28 empreintes R9 étaient conformes ; 115 ciblés et 371 SQLite
avaient été rejoués après nettoyage. Aucun changement métier issu de ce nettoyage.

Le feu vert présent porte sur **R10 seulement**. Les derniers routeurs et le
modèle User changent de propriétaire, mais les réexports legacy `app.models`,
`app.models.base` et `app.api` restent jusqu'à R11. Leur présence temporaire
ne signifie pas une seconde définition de modèle ou de router.

R10 n'introduit ni MANAGER/COMMERCIAL, ni règle d'affectation, ni nouveau
dashboard métier. Les contrats HTTP, SQL et comportements existants sont la
référence ; les anomalies ou limites préexistantes ne sont pas corrigées en
cachette pendant le déplacement.

## 2. Identity : quatre responsabilités existantes, pas de couches factices

```text
app/modules/identity/
├── __init__.py
├── models.py
├── schemas.py
├── dependencies.py
└── api.py
```

| Source précédente sous `backend/app/` | Destination |
|---|---|
| `models/user.py` | `modules/identity/models.py` |
| `schemas/auth.py` | `modules/identity/schemas.py` |
| `core/deps.py` | `modules/identity/dependencies.py` |
| `api/v1/auth.py` | `modules/identity/api.py` |

Ces quatre anciennes sources sont retirées. L'init est une docstring seule.
Les API auth réalisaient déjà leurs requêtes et le commit du profil :
aucun service/repository vide n'est ajouté pour les rendre symétriques aux
autres domaines.

Le [modèle User](../../../backend/app/modules/identity/models.py#L19) garde
table `"user"`, ID entier, username/email uniques, hash, nom optionnel,
role, activation et timestamps. L'enum reste :

```python
class Role(str, enum.Enum):
    TECHNICIAN = "technician"
    ADMIN = "admin"
```

La Base est toujours `app.core.base.Base`. `app.models.User` réexporte la même
classe, et le registre importe sa nouvelle feuille explicitement. Les tests
chargent modèle identity puis façade legacy, et l'ordre inverse :
un seul mapper User, 17 tables/mappers au registre complet, mêmes relations/FK.
Le nom du module Python ne renomme ni table, ni type enum SQL.

## 3. Pourquoi le guard quitte core

`get_current_user` ne fait pas seulement du décodage JWT : il charge **User**,
vérifie son existence/activation et décide du refus HTTP. C'est une politique
d'identité, tandis que signer/décoder un token ou hasher une valeur est une
primitive technique réutilisable.

| Élément | Propriétaire après R10 |
|---|---|
| Base, engine, sessions et `get_db` | `core` |
| JWT/bcrypt, création access/refresh, décodage | `core.security`, fichier inchangé |
| Modèle et contrats de profil/auth | `identity` |
| HTTPBearer, chargement du compte actif | `identity.dependencies` |

Le [guard](../../../backend/app/modules/identity/dependencies.py#L19) est
déplacé entièrement, sans wrapper restant dans `core/deps.py`.
Tous les consommateurs importent le **même objet fonction** depuis identity :
auth, catalogue, clients/sites, installations, ventes, terrain, rapports,
imports et dashboard. Les tests de `dependency_overrides` sont adaptés à ce
nouveau chemin ; ils n'utilisent pas une seconde fonction équivalente.

Sens des dépendances :

```text
routes métier ──► identity.dependencies ──► core.database / core.security
                          └──────────────► identity.models ──► core.base
```

Identity n'importe pas les API métier pour trouver ses utilisateurs.
Les primitives core n'importent aucun domaine, donc le déplacement ne crée
pas un cycle core → identity API → core.

Le guard conserve décodage, type `access`, conversion du `sub`, recherche SQL,
compte actif et headers de refus existants. Les tests vérifient notamment
qu'un compte désactivé **après émission** est refusé lors d'une nouvelle
requête : le token seul ne dispense pas de relire le compte.

## 4. Contrats auth : quatre routes inchangées

| Route sous `/api/v1/auth` | Comportement existant |
|---|---|
| `POST /login` | Username et valeur client, vérification bcrypt, compte actif, access + refresh |
| `POST /refresh` | Token de type refresh, compte existant/actif, nouvel access |
| `GET /me` | Profil du compte authentifié |
| `PUT /me` | Email/nom du profil, commit et refresh ORM |

Username reste borné à 1–100 caractères, valeur d'auth à 1–255, refresh token
non vide. Les types/forms Pydantic ne sont pas durcis dans R10.
Le profil ne contient pas le hash ; il expose id, username, email, nom, rôle
et activation selon le contrat actuel.

Exemple de modification autorisée :

```json
{"email": "profil-exemple@test.invalid", "full_name": "Nom de démonstration"}
```

Une tentative d'envoyer `role` ou `is_active` ne change pas ces champs via
cette route. R10 ne transforme pas ce comportement en nouvelle validation
`extra="forbid"` : les scénarios vérifient le contrat réellement conservé.
ADMIN n'obtient pas un endpoint d'administration supplémentaire.

Les types de tokens ne sont pas interchangeables :

- access utilisé comme refresh : refus 401 ;
- refresh utilisé sur une route exigeant access : refus 401 ;
- token invalide/expiré ou utilisateur désactivé : refus existant.

Les primitives conservent leurs durées configurées. L'API retourne toujours
`expires_in=1800`, valeur littérale préexistante. R10 ne corrige pas ce
couplage/configuration ni n'ajoute rotation, store de refresh ou révocation
nouvelle. Les mots de passe/jetons réels ne sont pas écrits dans les notes
ou les fixtures ; les nouvelles recettes emploient seulement des valeurs fictives.

## 5. Dashboard : déplacer la projection, pas le workflow terrain

```text
app/modules/dashboard/
├── __init__.py
├── schemas.py
├── service.py
└── api.py
```

Le routeur `api/v1/dashboard.py` est déplacé. Les cinq DTO de fin du fichier
terrain passent dans `dashboard/schemas.py` :

- TodaySummary ;
- NextInterventionRef ;
- InProgressInterventionRef ;
- OverdueInterventionRef ;
- DashboardSummaryResponse.

Le corps exact de `InterventionService.get_dashboard_summary` passe dans
[DashboardService](../../../backend/app/modules/dashboard/service.py#L20).
L'ancien corps et les DTO terrain sont supprimés, pas redéfinis en parallèle.
Les imports devenus inutiles du service terrain sont retirés ; toutes ses
autres méthodes restent identiques.

Le nouveau constructeur reprend la session et le repository existants :

```python
def __init__(self, db: AsyncSession):
    self.repo = InterventionRepository(db)
    self.db = db
```

Il ne faut pas inventer un DashboardRepository contenant la copie des mêmes
requêtes. Le service agrège des SELECT et utilise `list_overdue`, lecture du
repository terrain ; il ne crée ni Intervention, ni équipement, ni vente.
Même session partagée ne signifie pas absence de transaction SQL : les
lectures peuvent ouvrir une transaction, mais dashboard n'en committe pas
et ne possède pas de règle d'écriture.

L'API conserve :

```text
GET /api/v1/dashboard/summary
```

Elle injecte le compte actif, instancie DashboardService et retourne le même
DashboardSummaryResponse. Le rôle ADMIN est filtré par son propre ID comme
avant ; le déplacement n'ajoute pas une vue globale de tous les techniciens.

## 6. Les compteurs actuels sont volontairement conservés

Le nom `today` ne garantit pas que tous les champs représentent le seul jour :

| Champ | Règle réelle conservée |
|---|---|
| `next_intervention` | Première PLANNED parmi les interventions du technicien **aujourd'hui**, triées par heure |
| `in_progress_intervention` | IN_PROGRESS du technicien, même si planifiée un autre jour, avec started_at non null |
| `today.interventions_total` | Lignes planifiées aujourd'hui, plus l'intervention en cours trouvée hors de cette liste |
| `today.interventions_in_progress` | En cours aujourd'hui, plus celle hors jour si applicable |
| `today.interventions_completed` | **Toutes** les COMPLETED du technicien, sans filtre de date |
| `overdue_interventions` | PLANNED du technicien avant aujourd'hui |

Extrait conservé :

```python
completed_result = await self.repo.db.execute(
    select(func.count(Intervention.id)).where(
        Intervention.technician_id == current_user.id,
        Intervention.status == InterventionStatus.COMPLETED,
    )
)
```

Ajouter un filtre de date semblerait plus conforme au libellé, mais changerait
les réponses existantes. Ce serait une tâche métier distincte, pas un move R10.
Le calcul `elapsed_minutes`, les dates naïves et `datetime.utcnow()` restent
ceux du parent ; R10 ne change pas la politique de fuseau ou les warnings.

Les tests peuplent des données de deux utilisateurs, une intervention en cours
depuis hier, completions historiques, planifiées aujourd'hui/demain et retards.
Ils attendent total 4, en cours 1 et completions 2 pour le technicien.
Le compte ADMIN ne voit que ses propres données.

Le parent a également chargé la méthode et les cinq DTO **originaux** depuis
`git show 17dfc11` dans un namespace temporaire en mémoire. Sur les mêmes
bases vide/multiutilisateur et la même horloge, six retours JSON complets
(service direct et réponses HTTP, technicien/admin) sont identiques au
code extrait. Les gardes SQL de lecture et d'absence de commit restent
actives pendant ces comparaisons. Aucune seconde implémentation persistante
n'a été ajoutée à l'application.

## 7. Seed : entrypoint conservé et exécution strictement isolée

Déplacer `app/seed.py` n'apporterait pas de nouvelle responsabilité.
La commande reste `python -m app.seed`. Le seul changement est l'import
User/Role depuis identity ; le corps et le contrat d'exécution sont identiques.
Le registre est toujours chargé explicitement avant l'utilisation de metadata.

Deux nouveaux tests font la distinction :

1. **Importer le module** peut créer l'engine comme avant, mais ne doit
   ni se connecter ni exécuter SQL. Des gardes SQL détectent toute tentative.
2. **Exécuter la CLI** sur sa propre SQLite inexistante au départ, deux fois,
   doit produire 2 User, 8 Client, 8 Site et 7 Intervention, rôles attendus,
   hashes bcrypt et `foreign_key_check` sans erreur.

Les processus ont un cwd et un UPLOAD_DIR temporaires, un DATABASE_URL unique,
PYTHONPATH vers ce worktree, timeout et bytecode désactivé. La sortie qui
contient les identifiants de démonstration est capturée, pas réimprimée dans
les diagnostics de réussite. Aucune base existante n'a été seedée.

**Cette vérification ne prouve pas un seed sûr en production.** Le script
existant effectue des DELETE et ne nettoie pas toutes les tables V2.
Le test de répétition porte seulement sur les données démo créées par le
premier passage, pas sur une base contenant ventes, équipements ou imports.
TD-B019 trace le cadrage de sécurité avant toute utilisation sur un
environnement portant des données, sans modifier furtivement la CLI dans R10.

## 8. Composition et preuves structurelles

Le router global importe maintenant toutes les API depuis `app.modules`.
L'ordre des quinze inclusions reste identique. Les exports legacy API/Base/models
ne sont pas retirés avant le feu vert R11.

Les comparaisons AST contre `17dfc11` ont vérifié :

- quatre modules identity complets, seules substitutions de chemins d'import ;
- méthode d'agrégation et constructeur exacts dans DashboardService ;
- cinq DTO exacts, mêmes noms/bases/annotations/defaults ;
- service/schémas terrain restants exacts après retrait des blocs déplacés/imports ;
- route dashboard exacte après substitution des imports et du constructeur ;
- seed exact hors un import, primitives core et fichiers de configuration inchangés ;
- consommateurs adaptés, pas de seconde définition du guard ou des classes.

La comparaison de méthode ne normalise ni corps, nom, signature ni décorateur.
Les quatorze classes/modules d'import déplacés en R9 ne sont pas réécrits ;
le seul consommateur service concerné change le chemin User.
Le replay R9 reste intégralement égal, **560 268 octets**, au même oracle figé.

## 9. Tests ajoutés, défauts de tests corrigés et résultats

| Famille | Nouveaux cas | Preuve |
|---|---:|---|
| Identity | 12 | Pureté, modèle/DTO, ordres d'import/Base/Role, routes/guard commun, crypto et JWT réels, activation/profil |
| Dashboard | 4 | Layout et cinq DTO exacts, imports sans SQL, service/HTTP vide et multiutilisateur |
| Seed | 2 | Import sans SQL, vraie CLI répétée sur sa propre démo jetable |

Les gardes autour du vrai dashboard n'acceptent que SELECT/PRAGMA et interdisent
le commit. L'API et le service lisent réellement SQLite ; les résultats de
requêtes ne sont pas remplacés par des mocks.

Un premier run ciblé donnait **90 passed, 2 failed** :

- le nouveau test identity parcourait seulement les APIRoute directs ;
  il suit désormais les contextes effectifs d'inclusion FastAPI 0.138,
  comme le bootstrap existant ;
- le nouveau test dashboard figeait le service au 28 septembre mais le
  repository lisait `date.today()` localement. Les données sont maintenant
  alignées sur le même calendrier système, et seule l'heure UTC utilisée
  pour elapsed est contrôlée. Les 1470 minutes attendues restent vérifiées.

Ces deux corrections touchent **les tests**, pas les règles de l'application.
La construction des nouveaux fichiers a aussi vérifié l'import `time`
nécessaire au DTO NextInterventionRef. Aucun problème n'est masqué par
suppression d'assertion métier ou adaptation du rendu attendu.

| Vérification finale | Résultat |
|---|---|
| Neuf fichiers ciblés | **92 passed**, 3 warnings, 36,63 s |
| Suite SQLite complète | **389 passed**, 7 warnings, 93,54 s |
| PostgreSQL canonique | **95 passed**, 1 warning, 41,31 s : 56 + 39 |
| OpenAPI/metadata R0 | Identiques octet pour octet ; 46 paths, 63 opérations, 17 tables |
| Oracle import R9 | Identique octet pour octet, SHA `f98dd886…` |
| Alembic | Round-trip réussi ; seules deux opérations de la FK technicien historique |
| Runtime | `/docs` et `/openapi.json` 200 ; startup/shutdown complets |

**389 = 371 avant R10 + 18 nouveaux cas.** La revue indépendante a exécuté
ces 18 nouveaux tests puis 38 régressions/contrats existants : 56 ciblés verts.
Elle confirme l'équivalence AST et ne relève aucun problème bloquant ou métier.
Elle n'a pas répété PostgreSQL ou la suite entière.

## 10. Commandes réellement exécutées et limites des preuves

```text
python -m pytest <9 fichiers ciblés absolus> -q -p no:cacheprovider
python -m pytest <backend/tests absolu> -q -p no:cacheprovider
python -B -m app.seed   # seulement depuis le test, DATABASE_URL démo temporaire
python -m alembic -c <backend/alembic.ini absolu> upgrade head
python -m alembic -c <backend/alembic.ini absolu> downgrade -1
python -m alembic -c <backend/alembic.ini absolu> upgrade head
python -m alembic -c <backend/alembic.ini absolu> check
python -m pytest <5 fichiers PostgreSQL canoniques absolus> -q -p no:cacheprovider
python -m uvicorn app.main:app --host 127.0.0.1 --port <port libre>
git diff --check
```

Python 3.12.0 est l'interpréteur préexistant
`/home/lob/workspace/python/fastapi/Tervo/backend/.venv/bin/python`.
PYTHONPATH pointe les sources du **worktree attaché**, pas du checkout
principal. SQLite/cwd/uploads sont temporaires, TERVO_* neutralisées pour
SQLite, bytecode/cache pytest désactivés.

La délégation initiale de validation PostgreSQL n'a rapporté qu'un contrôle
statique/compilation : elle n'est pas comptée comme preuve PostgreSQL.
Le parent a réellement démarré PostgreSQL 17.4 local `--pull never`, à port
loopback éphémère, sans volume nommé, puis exécuté les cinq fichiers
canoniques et les migrations. Son conteneur et volume anonyme sont supprimés.
Aucune base ou ressource existante n'est modifiée.

Head reste `f102e0010001`, downgrade `e103e0010001`, reupgrade réussi.
Check retourne 255 attendu : remove_fk `intervention.technician_id → user.id`,
`job_technician_id_fkey` sans ondelete SQL historique, puis add_fk avec
`SET NULL` ORM. Une comparaison structurée `compare_metadata` confirme
exactement ces deux opérations, aucune nouvelle différence ni migration.

Les nouvelles recettes identity/dashboard/seed sont SQLite ou crypto/imports
isolés. Les 95 cas PostgreSQL couvrent les scénarios canoniques existants,
pas une campagne HTTP identity/dashboard ou seed PostgreSQL.
Le serveur docs a été arrêté par SIGTERM et attendu, code `-15` avec
shutdown complet, pas un processus oublié.

## 11. Todos, notes dépendantes et prochaine étape

TD-B013 pointe désormais vers le modèle identity, mais reste ouvert :
aucun rôle MANAGER/COMMERCIAL livré. TD-B019 cadre le seed destructif avant
déploiement sans modifier sa logique dans ce move. La note R7 explicite
désormais que sa projection dashboard et son guard ont changé de propriétaire
en R10 ; ses résultats restent historiques.

TD-B016 (volume d'archives représentatif), TD-F007 (interfaces V2), TD-B010
(migration/déploiement) et TD-B018 (reprise documentaire 7.4) ne sont pas
débloqués par ce déplacement. La demande de validation R10 n'autorise
pas automatiquement le retrait des façades ou la clôture globale R11.

Limites :

- commit R10 autorisé après acceptation ; feu vert distinct R11 reçu ;
- aucun nouveau rôle, workflow métier, privilège admin global ou correction de compteur ;
- aucun nouveau schéma SQL, migration, changement de primitives JWT/bcrypt ou de TTL ;
- seed uniquement sur ses propres SQLite démo, jamais base V2 peuplée/production ;
- aucune campagne HTTP identity/dashboard/seed PostgreSQL, de charge ou de sécurité complète ;
- aucun build Docker/frontend, CI distante, déploiement, push ou E2E navigateur ;
- preuves JSON R0 à R9, snapshots et oracle import inchangés.

### Acceptation et vérification avant commit

L'utilisateur a demandé « commit & start R11 ». Les 45 empreintes sources/tests
du manifeste R10 sont conformes. Les neuf fichiers ciblés ont été rejoués
dans un cwd SQLite/uploads temporaire avec le Python préexistant :
**92 passed, 3 warnings, 42,51 s**. Ce contrôle ne prétend pas répéter
PostgreSQL. Le commit regroupe R10 seul, sans retrait des façades de R11,
et conserve le manifeste JSON initial.
