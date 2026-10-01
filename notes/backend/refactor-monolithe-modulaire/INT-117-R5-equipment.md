# INT-117 — R5 : équipement physique et remplacement atomique

> **Planning :** [refactor monolithe modulaire](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md).
> **Parent R4 :** `93be411b09b736df967bd22bd8f85b8bea1a5203`, branche `refactor/modular-monolith`.
> **État :** R5 accepté et committé sous `7a453b8` dans le worktree Delta. R6 autorisé et vérifié localement ; voir la [note INT-118](INT-118-R6-installations.md). Le manifeste conserve sa capture avant acceptation.
> **Preuve :** [R5-validation.json](R5-validation.json), résultats et empreintes des sources.

## 1. Checkpoint R4 et périmètre de R5

L'utilisateur a accepté R4 et demandé son commit, puis autorisé R5 distinctement. Les 13 empreintes R4 et les 26 chemins concernés ont été vérifiés dans les deux checkouts. Le contrôle bootstrap/sales/module a été rejoué avant commit : **33 passed, 1 warning, 16,52 s**.

`[DEV]INT-116 — Refactor : isoler le domaine sales` (`93be411`) a été créé **dans le checkout principal Tervo**, puis reporté par fast-forward dans le worktree agent, avec vérification des arbres Git. Aucun stash ni nettoyage récursif nécessaire ; aucun changement R5 inclus dans ce commit.

R5 déplace le domaine équipement existant. Il ne réimplémente ni INT-97, ni le futur remplacement INT-110, ni l'orchestration Installation de R6. Les modifications sont également présentes dans le checkout principal `/home/lob/workspace/python/fastapi/Tervo`, sans commit. Une comparaison des contenus avant chaque transfert protège contre l'écrasement de changements concurrents.

```text
app/modules/equipment/
├── __init__.py
├── models.py
├── schemas.py
├── repository.py
├── service.py
└── api.py
```

| Ancienne source sous `backend/app/` | Source actuelle |
|---|---|
| `models/equipment.py` | `modules/equipment/models.py` |
| `schemas/equipment.py` | `modules/equipment/schemas.py` |
| `repositories/equipment.py` | `modules/equipment/repository.py` |
| `services/equipment.py` | `modules/equipment/service.py` |
| `api/v1/equipment.py` | `modules/equipment/api.py` |

Les cinq anciennes sources sont supprimées. L'init ne contient qu'une docstring. Aucun wrapper legacy ne maintient une seconde implémentation.

## 2. Un appareil physique, pas un produit catalogue ni une intention de pose

Product représente une référence commerciale ; Equipment une instance sur un Site, avec sa série, ses dates, ses garanties et son historique terrain.

```text
Site ──► Equipment ──► Intervention
             │
             ├──► Product (facultatif)
             ├──► Installation (facultatif, unique)
             └──► nouvel Equipment via replaced_by
```

Un équipement historique peut n'avoir ni produit catalogue ni installation enregistrée. Ces références manquantes ne rendent pas les données invalides et ne justifient pas la création d'une installation fictive.

Extraits du [modèle déplacé](../../../backend/app/modules/equipment/models.py#L15) :

```python
site_id = Column(Integer, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False, index=True)
product_id = Column(Integer, ForeignKey("product.id", ondelete="RESTRICT"), nullable=True, index=True)
installation_id = Column(Integer, ForeignKey("installation.id", ondelete="RESTRICT",
                         name="equipment_installation_id_fkey"), nullable=True, unique=True)
```

- Site est obligatoire.
- Product reste facultatif et sa FK non unique : plusieurs appareils peuvent partager la même référence.
- Installation est nullable mais unique : une installation alimente au maximum un appareil, sans imposer une provenance artificielle aux historiques.
- `RESTRICT` garde les références historiques ; aucune cascade destructrice nouvelle.

La Base reste `app.core.base.Base`. Tables, colonnes, index, défauts, enums et contraintes ne changent pas. Le package global `app.models` réexporte le même Equipment ; il n'exportait pas EquipmentStatus et R5 n'ajoute pas cet export.

## 3. Statuts et direction du remplacement

```python
class EquipmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    REPLACED = "REPLACED"
    RETIRED = "RETIRED"
```

Il n'y a **pas de PLANNED**. La planification appartient à Installation, pas à un appareil qui n'existe pas encore.

Le remplacement accepte un ancien appareil ACTIVE ou OUT_OF_SERVICE, non déjà remplacé. Il crée un **nouvel ID**, sur le même site, et fait pointer l'ancien vers le nouveau :

```python
replaced_by_id = Column(Integer, ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=True)
replaced_by = relationship("Equipment", remote_side=[id])
```

`remote_side=[id]` désigne le côté distant d'une relation auto-référente. Le lien est ancien → nouveau, pas l'inverse ; aucune relation `old_equipment` n'est inventée.

| Ancien état | Remplacement | Résultat |
|---|---|---|
| ACTIVE, non remplacé | Autorisé | Ancien REPLACED, nouvel appareil ACTIVE |
| OUT_OF_SERVICE, non remplacé | Autorisé | Même règle |
| REPLACED ou `replaced_by_id` renseigné | Refus | 409 |
| RETIRED | Refus | 409 |

L'ancien numéro de série, produit, dates, garanties, notes et interventions ne sont pas écrasés. Le nouveau reçoit seulement les valeurs du remplacement et le site de l'ancien. Si `new_product_id` est absent, son produit est `null` : le code ne copie pas implicitement celui de l'ancien. Il reste créé sans installation.

## 4. Contrats API et validation Pydantic

Préfixe effectif `/api/v1/equipment`, tag `equipment`. Le routeur conserve :

```python
router = APIRouter(prefix="/equipment", tags=["equipment"], dependencies=[Depends(get_current_user)])
```

Toutes les routes sont authentifiées, **sans restriction ADMIN-only**. Le nouveau scénario utilise un vrai JWT TECHNICIAN pour remplacer et relire l'historique.

| Route | Succès | Usage |
|---|---|---|
| `GET /equipment` | 200 | Liste filtrée et paginée |
| `POST /equipment` | 201 | Créer un appareil physique |
| `GET /equipment/{equipment_id}` | 200 | Lire un appareil, y compris remplacé |
| `POST /equipment/{equipment_id}/replace` | 201 | Retourner la nouvelle instance |

Aucun PATCH ni DELETE équipement ajouté. DELETE demeure 405. Les routes, noms de fonctions et décorateurs sont identiques, donc aussi les operation IDs OpenAPI.

### Création historique sans installation

```json
{
  "site_id": 1,
  "product_id": null,
  "serial_number": "IMPORT-1999",
  "installed_at": "1999-04-03",
  "commissioned_at": "1999-04-05",
  "lifecycle_status": "OUT_OF_SERVICE",
  "notes": "Historique importé"
}
```

Site et produit fourni doivent avoir des IDs positifs. `installation_id` n'est pas un champ de création : l'orchestrateur installation l'alimente lors de la clôture. `extra="forbid"` interdit de fournir un champ non prévu. Numéro de série : 255 caractères au maximum.

Le statut par défaut est ACTIVE. ACTIVE, OUT_OF_SERVICE et RETIRED restent possibles à la création ; REPLACED est refusé par le validateur :

```python
if self.lifecycle_status == EquipmentStatus.REPLACED:
    raise ValueError("Utiliser l'action replace pour remplacer un équipement")
```

PLANNED et une valeur inconnue sont refusés par l'enum. La fin de garantie ne peut précéder son début lorsque les deux dates existent. R5 ne renforce pas d'autres règles de dates sous couvert de déplacer le schéma.

### Remplacement

```json
{
  "new_product_id": 2,
  "installation_date": "2026-09-28",
  "serial_number": "NEW-2026",
  "notes": "Nouvelle instance"
}
```

Les quatre champs sont facultatifs. `installation_date` est stockée dans `installed_at`, sans créer de ligne Installation. Le produit fourni doit exister mais peut être inactif : l'existence et l'activité restent deux règles distinctes.

### Listes et erreurs

Filtres conservés : `site_id`, `product_id`, `lifecycle_status`. Page commence à 1 ; page_size de 1 à 100, défaut 25. Tri par Equipment.id avant offset/limit. Réponse : `items`, `total`, `page`, `page_size`, `pages`, avec au moins une page même si vide.

Le service conserve les 404 équipement/site/produit inconnus et les 409 d'état ou remplacement concurrent. Un champ invalide reste 422. La liste n'ajoute pas de recherche ou filtre d'installation nouveau.

## 5. Les couches et la propriété des transactions

| Couche | Responsabilité |
|---|---|
| API | Paramètres HTTP, auth et session injectée |
| Schémas | Corps stricts et réponses ORM |
| Service | Références physiques/catalogue et état remplaçable |
| Repository | Requêtes, création et remplacement atomique existants |
| Modèle | Contraintes et relations persistantes |

Le service contrôle l'état puis délègue le remplacement au repository local. Il n'introduit pas un commit propre ou une session supplémentaire. `create()` conserve son commit/refresh.

### Pourquoi flush précède l'UPDATE conditionnel

Dans [EquipmentRepository.replace](../../../backend/app/modules/equipment/repository.py#L28), le nouvel objet est ajouté puis flushé :

```python
new = Equipment(site_id=old.site_id, **values)
self.db.add(new)
try:
    await self.db.flush()
```

`flush()` écrit dans la transaction courante et obtient le nouvel ID, **sans valider la transaction**. Cet ID sert au lien de remplacement.

```python
result = await self.db.execute(update(Equipment).where(
    Equipment.id == old.id, Equipment.replaced_by_id.is_(None),
    Equipment.lifecycle_status.in_([EquipmentStatus.ACTIVE, EquipmentStatus.OUT_OF_SERVICE])
).values(replaced_by_id=new.id, lifecycle_status=EquipmentStatus.REPLACED))
```

La vérification est répétée au moment de l'écriture. Une lecture préalable seule ne protège pas deux remplacements concurrents ; le WHERE conditionnel exige que l'ancien soit encore disponible.

```python
if result.rowcount != 1:
    await self.db.rollback()
    return None
await self.db.commit()
await self.db.refresh(new)
return new
```

Si aucune ligne n'a été modifiée, le rollback annule aussi la création du nouvel objet flushé. Le service transforme `None` en 409. Si l'écriture réussit, le commit valide création du nouveau et mise à jour de l'ancien ensemble.

Le bloc d'erreur existant est conservé :

```python
except Exception:
    await self.db.rollback()
    raise
```

Les nouveaux tests injectent une exception à flush, execute et commit **avant qu'un commit réussisse**, puis relisent une nouvelle session : ancien inchangé et aucun nouvel appareil. Ils ne prouvent ni deux requêtes concurrentes PostgreSQL ni une annulation après un commit déjà réussi. Aucun comportement supplémentaire n'est attribué à R5.

### Installation ne réutilise pas le commit de ce repository

InstallationRepository reste propriétaire de ses écritures sans commit ; InstallationService réalise sa clôture atomique propre. R5 adapte seulement leurs imports modèles/schémas et l'accès à EquipmentService pour les références. Appeler EquipmentRepository.create au milieu d'une clôture introduirait un commit intermédiaire ; le refactor ne fait pas cela.

## 6. Dépendances transverses et conservation de l'historique

Les consommateurs adaptés sont :

- customers : schéma/API de liste des appareils par site et protections de suppression historique ;
- installations : modèle, réponses et contrôle de produit, avec les transactions existantes ;
- interventions : contrôle d'existence et cohérence site/appareil ;
- import planner : EquipmentCreate local pour valider les lignes ;
- import service : même classe Equipment dans MODELS, mêmes verrous et commits par sous-lot ;
- registre/router et tests : nouveaux chemins sans changer leur composition.

Les ORM encore legacy résolvent leurs relations stringifiées après le chargement du registre. Les accès directs existants aux modèles restent autorisés : R5 ne réécrit pas toutes les requêtes à travers une façade artificielle.

Le nouveau scénario part d'un appareil OUT_OF_SERVICE historique, produit connu, série/dates de 1999, notes et intervention liée. Après remplacement par un appareil sans produit :

1. L'ancien est REPLACED et pointe vers le nouveau.
2. Le nouveau est ACTIVE, même site, nouvelle série/date, produit null.
3. L'ancien produit, série, dates et notes restent identiques.
4. L'intervention pointe toujours vers l'ancien ID.
5. Les deux `installation_id` restent null et le nombre d'installations reste zéro.
6. Un second remplacement de l'ancien donne 409 ; un produit nouveau inconnu donne 404, sans troisième appareil.

Les tests antérieurs continuent de vérifier deux instances d'un même produit, les listes par site/produit, la désactivation catalogue sans perte de liens, les protections Client/Site et les interventions autonomes.

## 7. Preuves structurelles et nouveaux tests

Les cinq modules déplacés ont été comparés au commit R4 par AST. On enlève uniquement les imports de premier niveau : les **12 définitions** et tout le reste du module sont égaux, y compris enums, defaults, index, validations, décorateurs, branches, SQL, commits, rollback et messages.

`tests/test_equipment_module.py` ajoute **9 cas collectables** :

| Scénario | Nombre | Preuve |
|---|---|---|
| Layout et scan AST | 1 | Init pur, cinq anciennes sources absentes, imports relatifs inclus |
| Modèles/schémas purs | 2 | Une table locale Equipment, enum partagé, aucun engine/API/legacy |
| Ordres equipment-first/legacy-first | 2 | Même Equipment/Base, 17 mappers, FK/relations et idempotence |
| Historique et JWT TECHNICIAN | 1 | Remplacement et données physiques préservées |
| Échec contrôlé flush/execute/commit | 3 | Rollback réel, ancien persisté intact, aucune instance partielle |

Importer les schémas charge l'enum du modèle : une table equipment est attendue, pas zéro. La configuration complète des mappers est testée après registre, avec Site, Product, Installation, Intervention et la relation auto-référente réels.

Les nouvelles fixtures neutralisent leur variante PostgreSQL et utilisent SQLite avec FK actives. Ces neuf cas ne sont pas annoncés comme exécutés sous PostgreSQL.

## 8. Résultats et commandes exécutées sur le checkout principal

| Vérification | Résultat observé |
|---|---|
| Dix fichiers ciblés, équipement et consommateurs | **155 passed**, 3 warnings, 44,91 s |
| Suite SQLite entière | **324 passed**, 5 warnings, 68,34 s |
| PostgreSQL 17.4 ventes/installations/migrations | **56 passed**, 1 warning, 28,36 s |
| PostgreSQL 17.4 imports service/API | **39 passed**, 1 warning, 32,26 s |
| Alembic `upgrade head → downgrade -1 → upgrade head` | Réussite, head `f102e0010001` |
| `alembic check` | 255 attendu, seul écart FK technicien historique |
| Comparaison structurée Alembic | Deux opérations égales à R2, aucune nouvelle différence |
| OpenAPI/metadata | Octet pour octet comme R0/R1/R2, mêmes références R3/R4 |
| Runtime HTTP et ASGI | `/docs`, `/openapi.json` : 200 ; startup/shutdown complets |

**324 = 315 R4 + 9 nouveaux cas R5.** Les 95 tests PostgreSQL sont des réexécutions ciblées, pas des tests supplémentaires à ajouter au compte de suite.

La revue indépendante contre l'objet `93be411` n'a relevé aucun finding. Elle a vérifié AST, cutover, transactions et tests ainsi que le parsing Python/JSON, sans répéter les suites complètes ou PostgreSQL. Ses contrôles statiques ne sont pas présentés comme une réexécution des résultats du tableau.

Commandes applicatives effectives, avec chemins absolus et cwd temporaire :

```text
python -m pytest <10 fichiers ciblés> -q -p no:cacheprovider
python -m pytest <backend>/tests -q -p no:cacheprovider
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini downgrade -1
python -m alembic -c <backend>/alembic.ini upgrade head
python -m alembic -c <backend>/alembic.ini check
python -m pytest <installations/ventes/migration> -q -p no:cacheprovider
python -m pytest <imports service/API> -q -p no:cacheprovider
python -m uvicorn app.main:app --host 127.0.0.1 --port <port libre>
git diff --check
```

L'interpréteur est `backend/.venv/bin/python` du checkout principal, Python 3.12.0. Les fichiers ciblés exacts sont dans le manifeste R5. L'enveloppe suit :

```python
with tempfile.TemporaryDirectory(prefix="tervo-r5-tests-") as work:
    env = {k: v for k, v in os.environ.items() if not k.startswith("TERVO_")}
    env.update(
        PYTHONPATH=str(backend),
        DATABASE_URL="sqlite:///./tervo.db",
        UPLOAD_DIR=str(Path(work) / "uploads"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    subprocess.run(
        [str(backend / ".venv/bin/python"), "-m", "pytest",
         *absolute_test_paths, "-q", "-p", "no:cacheprovider"],
        cwd=work, env=env, check=True, timeout=240,
    )
```

Le code illustre l'enveloppe réellement exécutée, sans la capture des sorties JSON. Les variables `TERVO_*` sont retirées pour SQLite. Les tests historiques à URL SQLite relative travaillent donc sur des fichiers temporaires, pas sur les bases existantes.

Le scout PostgreSQL utilise une instance 17.4 jetable, image locale `--pull never`, port éphémère limité à 127.0.0.1, sans volume nommé ; la disponibilité est vérifiée par SQL TCP. Les variables des fixtures sélectionnent asyncpg/psycopg2. Le conteneur et le dossier temporaire ont été supprimés. Uvicorn a été terminé et attendu ; code `-15` après SIGTERM avec shutdown complet.

L'écart connu Alembic est toujours `intervention.technician_id → user.id` : remove_fk sans ondelete, add_fk avec `SET NULL`. R5 n'est pas présenté comme un check sans aucune différence ; il ne crée **aucune différence nouvelle**. La chaîne complète SQLite conserve sa limite historique `ALTER TYPE` PostgreSQL.

## 9. Preuves, todos et limites

[R5-validation.json](R5-validation.json) conserve résultats, durées, opérations normalisées, HTTP, comparaison source et hashes des **23 sources/tests** modifiés ou ajoutés. Les gros snapshots égaux sont référencés plutôt que dupliqués.

Les todos backend/frontend ont été relus. TD-B012 et TD-B014 pointent maintenant vers le modèle equipment déplacé ; leurs réalisations INT-97/INT-103 restent acquises. Les rôles TD-B013, mesure représentative TD-B016 et interfaces V2 TD-F007 ne sont pas débloqués par ce changement de package. Le suivi historique et les captures R0/R1/R2/R3/R4 restent conservés.

Limites :

- validation locale Python 3.12.0 ; aucun run CI distant Python 3.11 ;
- nouveaux scénarios sur SQLite, pas un test concurrent de remplacement PostgreSQL ;
- aucun seed, migration générée, backfill ou modification de base existante ;
- aucun build frontend, E2E navigateur, push ou déploiement ;
- comparaison complète des journaux d'import avant/après réservée à R9 ;
- R6 / INT-118 autorisé distinctement après acceptation R5 ; R7 non autorisé.

### Acceptation et contrôle avant commit

L'utilisateur a demandé « commit R5 proprement & passe au next R6 ». Les 23
empreintes sources/tests du manifeste R5 ont été vérifiées dans le worktree Delta.
La capture JSON initiale est conservée intacte : elle décrit la livraison avant
acceptation, pas l'état courant du planning.

Une réexécution isolée de `test_modular_bootstrap.py`, `test_equipment_module.py`,
`test_equipment.py` et `test_installations.py` a donné **76 passed, 1 warning,
20,19 s**, avec le même interpréteur du checkout principal, un cwd SQLite/uploads
temporaire et `-p no:cacheprovider`. Ce contrôle ne remplace ni ne prétend répéter
les groupes PostgreSQL précédents. Le commit `7a453b8` est créé dans le worktree
attaché ; aucune écriture directe du checkout principal n'est effectuée dans ce
fil. Les indications « sans commit » de la capture initiale ci-dessus décrivent
l'état avant cette acceptation, pas l'état courant.
