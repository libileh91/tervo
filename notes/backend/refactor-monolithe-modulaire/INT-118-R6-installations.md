# INT-118 — R6 : installations et transaction physique/commerciale

> **Planning :** [INT-118](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md#int-118--r6--déplacer-installations).
> **Parent R5 :** `7a453b8efcadd42c5a693a8c42956a5610d59163`, branche `refactor/modular-monolith`.
> **État :** implémenté, vérifié et accepté par l'utilisateur ; commit autorisé dans le worktree Delta attaché. Feu vert distinct R7 reçu.
> **Preuve :** [R6-validation.json](R6-validation.json). Les captures R0 à R5 restent intactes.

## 1. Reprise de R5 et périmètre strict de R6

L'utilisateur a accepté R5 et demandé son commit, puis donné le feu vert distinct
R6. Avant le commit, les 23 empreintes sources/tests de R5 ont été comparées au
manifeste. Les quatre fichiers bootstrap/module équipement/équipement/installations
ont été rejoués sur SQLite isolé : **76 passed, 1 warning, 20,19 s**.

Le commit `[DEV]INT-117 — Refactor : isoler le domaine equipment` est `7a453b8`.
Il regroupe le déplacement, les consommateurs, les neuf tests R5, la note,
le suivi et sa preuve historique ; aucune implémentation R6 n'y est incluse.
Le commit est créé dans le worktree attaché, sans écriture directe du checkout
principal et sans push.

R6 est un **déplacement structurel**, pas une nouvelle implémentation d'INT-103
ou du raccordement commercial INT-102. Les contrats autonomes et commerciaux
sont déjà présents dans le parent. Les anciens commentaires introductifs parlant
de références commerciales « futures » ne changent pas ce contrat ; les modèles
et validations effectifs, décrits ici, font foi.

```text
app/modules/installations/
├── __init__.py
├── models.py
├── schemas.py
├── repository.py
├── service.py
└── api.py
```

| Ancienne source sous `backend/app/` | Source après cutover |
|---|---|
| `models/installation.py` | `modules/installations/models.py` |
| `schemas/installation.py` | `modules/installations/schemas.py` |
| `repositories/installation.py` | `modules/installations/repository.py` |
| `services/installation.py` | `modules/installations/service.py` |
| `api/v1/installations.py` | `modules/installations/api.py` |

Les cinq anciennes sources sont supprimées. L'init contient seulement une
docstring. Les consommateurs existants changent leurs imports ; aucune
implémentation parallèle, façade legacy, migration, bus ou UnitOfWork n'est ajouté.

## 2. Installation, Equipment et SaleLine : trois responsabilités

Une installation représente **la pose d'une unité sur un site**. Equipment
représente l'appareil physique après pose, ou un appareil historique déjà connu.
SaleLine représente une ligne de vente, éventuellement de quantité supérieure à 1.

```text
Site ───────────────────► Installation ──► Equipment
                              ▲
Sale ──► SaleLine ─────────────┘
             └──► Product
```

Le parcours autonome n'a aucune vente fictive. Le parcours commercial ajoute
une provenance, pas une autre classe Installation ni une autre transaction.
Une ligne de quantité 3 peut être référencée par trois installations non annulées.
Un Equipment importé peut toujours avoir `installation_id = null`.

Le [modèle déplacé](../../../backend/app/modules/installations/models.py#L15)
conserve les colonnes et contraintes :

```python
site_id = Column(Integer, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False, index=True)
sale_line_id = Column(Integer, ForeignKey("sale_line.id", ondelete="RESTRICT"), nullable=True, index=True)
```

- `site_id` est requis en SQL comme en API.
- `sale_line_id` est une vraie FK nullable, pas un identifiant libre.
- Les FK `RESTRICT` protègent les historiques contre une suppression de référence.
- `Installation.equipment` est une relation `uselist=False`, avec
  `passive_deletes="all"`.
- L'unicité de `Equipment.installation_id` impose au plus un appareil par
  installation, même si une écriture contourne l'API.
- Le modèle Equipment n'est pas modifié dans R6 : nullable, remplacement,
  série, garanties et historiques restent ceux de R5.

Le registre charge désormais `app.modules.installations.models.Installation`.
Le réexport `app.models.Installation` conserve **la même classe**, pas un wrapper.
Le réexport global d'InstallationStatus n'est pas ajouté : R6 ne crée pas de
nouveau contrat Python. Les tests chargent module et réexports dans les deux
ordres, configurent tous les mappers, puis rappellent le registre :
**17 tables, 17 mappers, une Base**, mêmes objets à chaque appel.

## 3. API inchangée et validations à la frontière

Le [routeur](../../../backend/app/modules/installations/api.py#L12) conserve :

```python
router = APIRouter(prefix="/installations", tags=["installations"],
                   dependencies=[Depends(get_current_user)])
```

Le préfixe `/api/v1` reste apporté par la composition globale.

| Méthode et route | Réponse normale | Rôle de la route |
|---|---|---|
| `GET /api/v1/installations` | 200, liste paginée | Filtres `site_id`, `status`, pagination |
| `POST /api/v1/installations` | 201 | Création SCHEDULED |
| `GET /api/v1/installations/{id}` | 200 | Installation et équipement éventuel |
| `POST /api/v1/installations/{id}/start` | 200 | SCHEDULED → IN_PROGRESS |
| `POST /api/v1/installations/{id}/cancel` | 200 | SCHEDULED/IN_PROGRESS → CANCELLED |
| `POST /api/v1/installations/{id}/complete` | 200 | IN_PROGRESS → COMPLETED + appareil |

Auth : JWT réel et utilisateur actif, comportement existant ADMIN/TECHNICIAN.
R6 n'anticipe pas les rôles MANAGER/COMMERCIAL de TD-B013 et ne durcit pas les
endpoints. Les tests existants rejouent absence de token, token invalide et
utilisateur désactivé sur les six routes.

### Créer avec ou sans provenance

```json
{
  "site_id": 12,
  "sale_line_id": null,
  "scheduled_start": "2026-09-28T10:00:00+02:00",
  "scheduled_end": "2026-09-28T09:00:00Z",
  "technician_notes": "Matériel fourni par le client"
}
```

Dans le [schéma](../../../backend/app/modules/installations/schemas.py#L9),
`site_id > 0`, `sale_line_id` absent ou null est accepté et un identifiant non
null doit être positif. `extra="forbid"` empêche d'injecter directement le statut.
Les dates avec offset sont converties en UTC **naïf**, convention SQL existante :
`10:00+02:00` devient `08:00`. La fin nécessite un début et ne peut le précéder ;
l'égalité est acceptée. Il ne s'agit pas d'une conversion nouvelle de la base.

La présence d'une ligne déclenche les vérifications métier. Le simple parsing
Pydantic ne peut pas savoir si la vente est confirmée ou si le site correspond.

### Clôturer : intention create ou attach explicite

```json
{
  "installation_date": "2026-09-28",
  "commissioning_date": "2026-09-29",
  "equipment": {
    "mode": "create",
    "product_id": 8,
    "serial_number": "CUSTOMER-1",
    "notes": "Appareil posé"
  }
}
```

Ou :

```json
{
  "installation_date": "2026-09-28",
  "commissioning_date": "2026-09-29",
  "equipment": {"mode": "attach", "equipment_id": 41}
}
```

Le discriminateur `mode` sélectionne deux schémas, sans interprétation implicite
d'un identifiant ou d'une série. `attach` interdit notamment `product_id` et
`serial_number` dans le corps : la pose ne doit pas écraser un appareil historique.
La date de pose est requise ; la mise en service est optionnelle et ne peut
précéder la pose. En autonome, `create` reste valide sans produit catalogue.
La réponse garde `sale_line_id`, dates, notes et `equipment` imbriqué.

## 4. Transitions et provenance commerciale

Les quatre statuts restent `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`.
Aucun état PLANNED, aucun report versionné ou nouveau workflow terrain n'est ajouté.

| Action | États autorisés | Écriture | Refus |
|---|---|---|---|
| create | Nouvelle installation | SCHEDULED | Référence invalide |
| start | SCHEDULED | IN_PROGRESS, `started_at` | 409 sinon |
| cancel | SCHEDULED, IN_PROGRESS | CANCELLED | 409 sinon |
| complete | IN_PROGRESS | COMPLETED, dates + équipement | 409 sinon |

Annuler ne supprime pas la ligne historique. Le contrôle de quantité exclut les
installations CANCELLED, mais compte SCHEDULED, IN_PROGRESS et COMPLETED.
Une clôture répétée est un **409**, pas un succès idempotent : elle ne crée pas
un second Equipment.

Le [service](../../../backend/app/modules/installations/service.py#L25)
verrouille la ligne et recharge sa vente :

```python
line = await self.db.scalar(select(SaleLine).where(SaleLine.id == sale_line_id)
    .options(selectinload(SaleLine.sale)).with_for_update())
```

Il conserve les règles suivantes :

1. ligne inconnue : 404 ;
2. vente non CONFIRMED : 409 ;
3. site différent de celui de la vente : 422 ;
4. installations non annulées déjà à hauteur de la quantité : 409 ;
5. clôture commerciale : produit créé ou produit de l'appareil attaché égal à
   celui de la ligne vendue, sinon 422.

La clôture exclut l'installation courante du comptage pour ne pas se compter
deux fois. `with_for_update()` sérialise les décisions concurrentes sur la ligne
avec PostgreSQL. R6 ne remplace pas ce verrou par un calcul hors transaction.
Il ne promet pas à SQLite les mêmes verrous de ligne que PostgreSQL.

## 5. Les couches et le propriétaire de la transaction

| Couche | Responsabilité conservée |
|---|---|
| API | Auth, session injectée, corps et réponse, routage |
| Schémas | Validation des formes/dates, sérialisation ORM |
| Service | Références, orchestration, transitions, commit/rollback |
| Repository | Lectures et écritures conditionnelles, flush, aucun commit |
| ORM | Contraintes SQL, valeurs par défaut et relations |

Le [constructeur](../../../backend/app/modules/installations/service.py#L19)
est inchangé :

```python
def __init__(self, db):
    self.db = db
    self.repo = InstallationRepository(db)
    self.references = EquipmentService(db)
```

La route, InstallationService, InstallationRepository et EquipmentService
partagent **la même AsyncSession**. EquipmentService sert ici aux contrôles de
site et de produit, pas à appeler le `commit` d'EquipmentRepository.create().
Cela distingue la réutilisation d'un contrôle de référence de celle d'une
opération autonome qui validerait sa transaction trop tôt.

### La clôture réclame d'abord la transition

Dans le [repository](../../../backend/app/modules/installations/repository.py#L32) :

```python
result = await self.db.execute(update(Installation).where(
    Installation.id == installation_id, Installation.status.in_(allowed)
).values(**values).execution_options(synchronize_session=False))
return result.rowcount == 1
```

Le service demande cette écriture avec `allowed=[IN_PROGRESS]` **avant** de
toucher Equipment. Si un autre complete/cancel a déjà gagné, `rowcount` vaut 0
et l'action échoue en 409. Si une validation ultérieure échoue, le rollback
annule aussi cette transition provisoire.

`synchronize_session=False` évite une synchronisation ORM implicite ; les lectures
du repository utilisent `populate_existing=True` et chargent Equipment avec
`selectinload`, afin de rendre l'état SQL effectif dans la réponse.

### Create : écrire sans valider prématurément

```python
async def create_equipment(self, values):
    self.db.add(Equipment(**values))
    await self.db.flush()
```

Le flush exécute l'INSERT et révèle les conflits de FK/unicité, mais **n'est pas**
un commit. Le service ne valide qu'après les contrôles et les deux écritures.
Une lecture d'auth ou de référence peut avoir démarré une transaction via
`autobegin` ; on réutilise celle-ci, sans introduire un `db.begin()` imbriqué.

### Attach : protéger l'appareil et ses métadonnées

Le service charge Equipment avec `with_for_update()`, vérifie le site, le produit
vendu si nécessaire, l'état ACTIVE, l'absence de remplacement et de lien existant.
Les dates historiques non nulles doivent être reprises à l'identique : une pose
ne les efface pas. Série, notes, produit et garanties ne sont pas écrasés.

L'UPDATE du repository reprend dans son WHERE les conditions de site, lien null,
non-remplacement et état ACTIVE. Le verrou PostgreSQL protège les lectures ;
l'écriture conditionnelle protège aussi les lectures devenues obsolètes.

### Les erreurs ne laissent pas d'écriture partielle

Le [service de clôture](../../../backend/app/modules/installations/service.py#L89)
termine avec :

```python
await self.db.commit()
```

Son traitement d'erreurs est conservé :

```python
except IntegrityError as exc:
    await self.db.rollback()
    raise HTTPException(409, "Conflit de référence ou équipement déjà lié à cette installation") from exc
except Exception:
    await self.db.rollback()
    raise
```

Une IntegrityError devient le conflit métier existant. Une autre erreur est
relancée après rollback. On ne transforme pas toute erreur technique en 409
et on ne masque pas les exceptions injectées par les tests.

## 6. Tests : distinguer invariant structurel et parcours réel

Les [14 nouveaux cas](../../../backend/tests/test_installations_module.py#L21)
complètent les scénarios existants plutôt que de les remplacer.

| Famille nouvelle | Cas paramétrés | Preuve |
|---|---:|---|
| Layout/cutover, init pur | 2 | Sources legacy absentes, AST des imports, aucun chargement implicite |
| Imports models/schemas | 2 | Aucun engine/SQL/API/service chargé ; tables attendues uniquement |
| Registre et relations dans deux ordres | 2 | Une Base, identité des classes, bidirectionnalité, idempotence |
| Composition des six routes | 1 | Une occurrence de chaque path/méthode/endpoint |
| Contrat des schémas | 1 | UTC, ligne optionnelle, create sans produit, extras refusés |
| Clôture commerciale create/attach | 4 | Préparation JWT admin/technician, session partagée, commit unique |
| Échec commercial après les deux écritures | 2 | État SQL provisoire observé, rollback relu dans une nouvelle session |

Les quatre cas de succès préparent vente confirmée, installation et appareil
éventuel via l'API avec JWT réels, puis appellent directement le service pour
observer la session et ses commits. Ils relisent ensuite la réponse via l'API.
Ils ne sont pas présentés comme quatre tests JWT du endpoint complete :
ces contrôles HTTP restent ceux de la suite existante.

Les deux injections au commit vérifient **avant** l'exception que SQL contient
COMPLETED et un Equipment lié. Après rollback et nouvelle session :
IN_PROGRESS, dates de clôture nulles, aucun appareil créé/lien partiel, vente
toujours CONFIRMED ; en attach, série et notes historiques conservées.
Ce n'est pas un mock qui retourne un objet factice : les deux écritures ont
réellement eu lieu dans une base SQLite temporaire.

Les nouvelles fixtures neutralisent la variable PostgreSQL du contexte réutilisé.
Ces 14 cas sont **SQLite-only**, pas une nouvelle preuve de concurrence PostgreSQL.
La concurrence et les injections autonomes existantes ont été rejouées sur les
deux moteurs via `test_installations.py`.

### Ajustement du test de composition, pas de l'application

Le premier run avec le nouveau module donnait **131 passed, 1 failed** :
le test cherchait seulement des APIRoute directs dans `app.routes`.
FastAPI 0.138 garde des inclusions différées. Le bootstrap avait déjà une règle
adaptée : utiliser `_iter_routes_with_context` s'il existe, sinon parcourir les
routes classiques. Le nouveau test suit cette même règle et compare les chemins
effectifs ; aucun code de routing applicatif n'est modifié pour faire passer le test.

## 7. Résultats observés et commandes

| Vérification finale | Résultat |
|---|---|
| Onze fichiers ciblés, nouveaux cas inclus | **132 passed**, 1 warning, 36,19 s |
| Suite SQLite entière | **338 passed**, 5 warnings, 62,54 s |
| Groupe installations/ventes/migrations | **57 passed** (56 PostgreSQL + 1 migration SQLite), 1 warning, 24,02 s |
| PostgreSQL import service/API | **39 passed**, 1 warning, 25,56 s |
| Alembic upgrade → downgrade -1 → upgrade | Réussite, head `f102e0010001` |
| Alembic check | 255 attendu : les deux opérations de la seule FK historique |
| OpenAPI et metadata | Octet pour octet comme R0, 46 paths, 63 opérations, 17 tables |
| Runtime uvicorn | `/docs` et `/openapi.json` : 200 ; startup/shutdown complets |
| AST des cinq couches hors imports | Identique au parent R5, 17 définitions top-level |

Avant l'intégration des nouveaux tests : **118 ciblés** (30,81 s) et **324 SQLite**
(61,44 s), tous verts. Le résultat final est **324 + 14 = 338**, sans double-compter
les réexécutions ou les groupes PostgreSQL.

**Précision de décompte PostgreSQL :** la sélection historique à trois fichiers
(`test_installations.py`, `test_sales.py`, `test_installation_migration.py`)
contient 56 cas. Le runner R6 y a ajouté `test_sale_migration.py`, un cas
existant qui utilise sa propre base SQLite en mémoire, même dans ce groupe.
Le total observé est donc **56 PostgreSQL + 1 migration SQLite = 57**, pas
57 cas PostgreSQL ni un nouveau test R6. Aucune définition n'a changé dans
ces fichiers, seuls trois imports ont changé. Le scout a retiré son attribution
initiale erronée « +1 nouveau test R6 ». Les captures historiques sont conservées.

Enveloppe SQLite réellement utilisée :

```python
with tempfile.TemporaryDirectory(prefix="tervo-r6-final-") as work:
    env = {k: v for k, v in os.environ.items() if not k.startswith("TERVO_")}
    env.update(
        PYTHONPATH=str(backend),
        DATABASE_URL="sqlite:///./tervo.db",
        UPLOAD_DIR=work + "/uploads",
        PYTHONDONTWRITEBYTECODE="1",
    )
    subprocess.run(
        [python, "-m", "pytest", *absolute_test_paths, "-q", "-p", "no:cacheprovider"],
        cwd=work, env=env, timeout=240,
    )
```

`python` est l'interpréteur préexistant
`/home/lob/workspace/python/fastapi/Tervo/backend/.venv/bin/python` (3.12.0).
Le code importé est celui du **worktree attaché** via PYTHONPATH ; l'utilisation
de cet interpréteur n'est ni un transfert ni une validation des sources du
checkout principal. SQLite/uploads sont temporaires, sans toucher les bases existantes.

Commandes PostgreSQL exécutées par le scout indépendant dans un cwd temporaire,
avec URL sync pour Alembic et variables asyncpg des fixtures :

```text
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic check
python -m pytest <test_installations.py test_sales.py test_installation_migration.py test_sale_migration.py> -q -p no:cacheprovider
python -m pytest <test_import_service_v2.py test_import_api_v2.py> -q -p no:cacheprovider
```

PostgreSQL 17.4 provient de l'image locale `postgres:17.4`, `--pull never`,
conteneur jetable, port éphémère limité à loopback, aucun volume nommé.
Le scout a confirmé la suppression de son conteneur et l'absence de modifications
de sources. Les durées du round-trip sont 1,16 / 0,90 / 1,00 s ;
check : 1,07 s. Le parent conserve les résultats rapportés, pas des logs temporaires
présentés comme artefacts durables.

L'écart Alembic reste `intervention.technician_id → user.id` :
remove_fk historique sans `ondelete`, add_fk avec `SET NULL` ORM.
**Aucune différence nouvelle**, mais pas un check vide ; aucune migration générée.

Pour les snapshots, même sérialisation UTF-8 R0 : JSON trié, indent 2,
`ensure_ascii=False`, newline finale. Une première comparaison binaire du script
utilisait le défaut ASCII ; la comparaison finale avec le format R0 est égale.
Les grands fichiers identiques sont référencés, pas recopiés.

Le serveur a été lancé par `python -m uvicorn app.main:app --host 127.0.0.1
--port <port libre>`, puis arrêté et attendu. Le code `-15` après SIGTERM
s'accompagne des logs de shutdown complet ; aucun serveur n'est laissé actif.

### Revue indépendante

La revue contre `7a453b8` confirme les cinq AST hors imports, les 17 définitions,
le cutover, la Base unique et les transactions inchangées. Elle a rejoué
**2 tests snapshots** et **11 cas SQLite ciblés** (rollback, concurrence, auth).
Son snapshot précédait la correction du test de composition : elle a retrouvé
le même défaut, désormais corrigé et couvert par la suite finale du parent.
Aucun finding structurel ou métier restant. Elle n'a pas répété PostgreSQL
ni la suite globale ; ses vérifications ne sont pas additionnées aux comptes.

## 8. Todos, notes dépendantes et limites

TD-B014 et TD-B017 pointent maintenant vers `modules/installations` ; leurs
réalisations INT-103/INT-102 et le contrat commercial nullable restent acquis.
Les notes INT-103 et INT-102 conservent leurs captures historiques, avec chemins
actuels et renvoi vers R6. La note R5 précise son commit et renvoie ici. Les autres captures
JSON historiques, fixtures d'import, migrations et lockfile restent intacts.

Le scan backend/frontend ne débloque aucun todo métier : TD-B013 (rôles),
TD-B016 (volume représentatif) et TD-F007 (interfaces V2) restent ouverts.
Pas de mesure d'archives réelles déduite des tests d'import existants.

Limites explicites :

- commit R6 autorisé après acceptation utilisateur, feu vert distinct R7 reçu ;
- aucun push, CI distante Python 3.11, déploiement, build frontend ou E2E navigateur ;
- nouveaux tests de frontière/commercials SQLite-only ; concurrence PostgreSQL
  vérifiée par les scénarios existants, pas par une nouvelle campagne de charge ;
- aucune migration, backfill, seed ou correction de la FK technicien ;
- aucune modification métier de la politique create/attach, des rôles ou des dates ;
- comparaison complète des journaux d'import avant/après réservée à R9.

### Acceptation et vérification avant commit

L'utilisateur a demandé « commit & passe au R7 ». Les 17 empreintes sources/tests
R6 sont conformes au manifeste. `test_modular_bootstrap.py`,
`test_installations_module.py`, `test_installations.py` et `test_sales.py` ont
été rejoués dans un cwd SQLite/uploads temporaire, avec l'interpréteur et
PYTHONPATH décrits plus haut : **81 passed, 1 warning, 21,27 s**.
La capture JSON initiale est conservée intacte ; ce contrôle ne prétend pas
répéter PostgreSQL. Le commit regroupe la livraison R6, ses tests, notes et suivi,
sans implémentation R7 ni écriture directe du checkout principal.
