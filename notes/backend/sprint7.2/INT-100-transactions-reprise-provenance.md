# INT-100 — Lire les transactions et la reprise dans le code

| Fichier | Responsabilité |
| --- | --- |
| [ingestion.py](../../../backend/app/importers/ingestion.py) | Capturer les sources et le manifeste |
| [import_planner.py](../../../backend/app/services/import_planner.py) | Préparer les opérations et résoudre les dépendances |
| [import_service.py](../../../backend/app/services/import_service.py) | Approuver, exécuter, reprendre et produire le rapport |
| [import_batch.py](../../../backend/app/models/import_batch.py) | Conserver plans, références, traces et anomalies |
| [migration d100e0010001](../../../backend/alembic/versions/d100e0010001_add_import_journal.py) | Créer les quatre tables techniques |

```text
stage → validate → execute
source   plan      transactions de 500 lignes maximum
```

## 1. Persister les correspondances entre fichiers

Extrait réel de [import_batch.py](../../../backend/app/models/import_batch.py), à partir de la ligne 47 :

```python
class ImportReference(Base):
    __tablename__ = 'import_reference'
    __table_args__ = (UniqueConstraint('source_namespace','entity_type','source_id', name='uq_import_reference'),)
    id = Column(Integer, primary_key=True)
    source_namespace = Column(String(100), nullable=False)
    entity_type = Column(String(30), nullable=False)
    source_id = Column(String(255), nullable=False)
    entity_id = Column(Integer, nullable=False)
```

`UniqueConstraint` garantit qu’une référence source possède une seule cible pour ce namespace/type. Plusieurs références, comme C001 et C005, peuvent désigner le même client après confirmation.

| Table | Ce qu’elle conserve |
| --- | --- |
| `ImportBatch` | Octets originaux, hash, sélections, décisions, plan et révision |
| `ImportReference` | Référence historique → ID canonique réutilisable entre fichiers |
| `ImportRecord` | Ligne traitée, action, original, normalisé, cible, motif et validateur |
| `ImportError` | Anomalies par révision, y compris après correction |

Les cibles techniques sont polymorphes : leur validité est contrôlée dans le service, pas par une FK unique vers cinq tables différentes.

## 2. Préparer les parents avant les enfants

Extrait réel de [import_planner.py](../../../backend/app/services/import_planner.py), à partir de la ligne 203 :

```python
order = {'products':0,'clients':1,'sites':2,'equipment':3,'interventions':4}
queue = sorted(enumerate(deepcopy(records)),key=lambda pair:order[pair[1]['kind']])
```

Le planner attribue des IDs temporaires négatifs (`-index-1`) aux futures créations. Exemple illustratif :

```python
# Plan avant écriture : le site vise le client qui n’existe pas encore.
client_plan = {"target_id": -1, "body": {"full_name": "jean dupont"}}
site_plan = {"target_id": -2, "body": {"client_id": -1}}
# Après création du client : ids[-1] = 42, donc le site reçoit client_id=42.
```

Les produits éventuels précèdent les équipements ; les interventions suivent la chaîne physique. Une dépendance non résolue est réessayée si une autre ligne a débloqué le plan. E004 peut ainsi attendre E005 pour son remplacement. Sans progrès possible, la ligne reste `pending` avec son erreur.

## 3. Obtenir les vrais IDs sans commiter chaque ligne

Extrait réel de [import_service.py](../../../backend/app/services/import_service.py), à partir de la ligne 181 :

```python
entity = MODELS[kind](**values)
db.add(entity)
await db.flush()
ids[target] = entity.id
target = entity.id
```

`flush()` envoie l’INSERT et récupère l’ID, mais **ne valide pas la transaction**. Le dictionnaire `ids` traduit ensuite les références négatives des enfants. Une exception ultérieure peut encore annuler cet INSERT.

## 4. Ouvrir une transaction pour chaque sous-lot

Extrait réel de [import_service.py](../../../backend/app/services/import_service.py), à partir de la ligne 237 :

```python
for index in range(0,len(entries),size):
    chunk = entries[index:index+size]
    try:
        async with self.sessions() as db:
            async with db.begin():
                batch = await self._get(db,batch_id,lock=True)
                await self._lock_domain(db)
                _,_,fingerprint = await self._load(db)
                if batch.execution_token != execution_token or batch.status != 'running' or batch.plan_token != plan_token or fingerprint != batch.database_snapshot:
                    raise ValueError('Référentiel ou plan modifié')
                await self._before_chunk(index // size)
                for entry in chunk:
                    await self._write(db,batch,entry,ids)
                await db.flush()
                _,_,batch.database_snapshot = await self._load(db)
                batch.lease_until = now()+timedelta(minutes=self.LEASE_MINUTES)
```

- `chunk` contient au maximum 500 opérations.
- `db.begin()` commite à la sortie normale et annule la transaction en cas d’exception.
- `_write()` ajoute l’entité, sa référence source et son `ImportRecord` dans cette même transaction.
- Le contrôle d’empreinte refuse un référentiel modifié depuis la validation.

L’erreur `BATCH_ROLLBACK` est ensuite enregistrée dans une **nouvelle transaction**, car celle du sous-lot vient d’être annulée.

## 5. Reprendre sans rejouer les lignes commitées

Extrait réel de [import_service.py](../../../backend/app/services/import_service.py), à partir de la ligne 234 :

```python
done = {r.row_key for r in records}
entries = [e for e in batch.plan if e['op'] in {'create','associate','ignore'} and e['key'] not in done]
ids = {r.decision['plan_target']:r.entity_id for r in records if isinstance(r.decision.get('plan_target'),int) and r.decision['plan_target'] < 0}
```

`done` vient des traces réellement commitées. La liste `entries` retire ces clés ; `ids` reconstruit les correspondances temporaires nécessaires aux enfants restants.

| Protection | Problème évité |
| --- | --- |
| SHA-256 + unicité namespace/hash | Réimport du même fichier |
| `ImportReference` + matching | Doublons dans un réexport différent |
| `ImportRecord` unique par import/ligne | Rejeu d’une ligne déjà commitée |
| `plan_token` + révision | Exécution d’anciennes décisions |
| Empreinte du référentiel | Exécution après changement des données métier |

Le mapping est figé après le premier sous-lot commité. Une correction d’une ligne encore en attente impose une nouvelle validation.

## 6. La preuve du rollback : une exception après INSERT

Extrait réel de [test_import_service_v2.py](../../../backend/tests/test_import_service_v2.py), à partir de la ligne 178 :

```python
async def fail_after_write(db,batch,entry,ids):
    await original_write(db,batch,entry,ids)
    if entry['source']['row'] == 503:
        raise RuntimeError('Failure after a database flush')
service._write = fail_after_write
result = await service.execute(plan['id'],plan['plan_token'])
assert result['status'] == 'failed'
assert result['counts']['committed'] == 500
async with factory() as db:
    for model in (Client,ImportRecord,ImportReference):
        assert await db.scalar(select(func.count()).select_from(model)) == 500
service._write = original_write
assert (await service.execute(plan['id'],plan['plan_token']))['counts']['committed'] == 502
```

Le test prépare 502 clients. La ligne physique 503 appartient au deuxième sous-lot. L’exception est levée **après** `_write()` : vérifier 500 clients, références et traces prouve que les écritures du second lot ont été annulées. La reprise finit à 502 sans doublon.

## 7. Lire les états et les limites

```text
staged → ready → running → success : toutes les lignes traitées
                         → partial : lignes encore en attente
                         → failed  : sous-lot annulé, reprise possible
```

Une exclusion humaine motivée compte comme traitée. Une association n’écrase aucune coordonnée du client existant : `MISSING_PHONE` reste un avertissement si l’identité est confirmée.

Un emplacement unique sérialise les imports. Le bail de quinze minutes est renouvelé par sous-lot ; `execution_token` empêche un ancien processus de finaliser une reprise qui ne lui appartient plus. Sur PostgreSQL, le verrou du référentiel peut retarder les écritures métier.

```bash
cd backend
uv run pytest tests/test_import_service_v2.py -q
# Uniquement sur une base de test : chaque test crée et supprime son schéma.
TERVO_IMPORT_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/TEST_DB \
  uv run pytest tests/test_import_service_v2.py -q
```

Validation initiale : 11 tests sur SQLite et PostgreSQL 17.4, migration montée/descente/remontée et comparaison ORM sans écart. Source et référentiel restent chargés en mémoire ; exécution synchrone, 10 Mio maximum par fichier. [TD-B016](../../../docs/todos/backend.md#td-b016--mesurer-limport-sur-un-volume-représentatif) conserve la mesure sur volume réel ; 502 lignes ne prouvent pas la capacité à importer vingt ans d’archives.
