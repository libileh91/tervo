# INT-101 — Suivre une requête de l’API jusqu’au service

Le routeur [imports.py](../../../backend/app/api/v1/imports.py) est enregistré dans [app/main.py](../../../backend/app/main.py). Les réponses et requêtes sont typées dans [schemas/imports.py](../../../backend/app/schemas/imports.py).

| Route sous `/api/v1/admin/import` | Résultat |
| --- | --- |
| `POST /preview` | Source conservée, aperçu de dix lignes maximum |
| `POST /validate` | Plan, compteurs et nouveau jeton d’approbation |
| `POST /execute` | Exécution du plan et rapport |
| `GET /batches` | Historique paginé |
| `GET /batches/{id}` | Lignes du plan et manifeste |
| `GET /batches/{id}/errors` | Journal des anomalies par révision |

## 1. Refuser un technicien avant toute opération d’import

Extrait réel de [imports.py](../../../backend/app/api/v1/imports.py), à partir de la ligne 20 :

```python
async def import_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(403, 'Import réservé aux administrateurs')
    return user
```

`Depends(get_current_user)` vérifie le JWT et l’utilisateur actif. `import_admin` ajoute la règle métier ADMIN. Chaque endpoint utilise cette dépendance ; les tests appellent les six routes sans jeton et en TECHNICIAN.

## 2. Lire le manifeste multipart et borner le fichier

Extrait réel de [imports.py](../../../backend/app/api/v1/imports.py), à partir de la ligne 34 :

```python
try:
    manifest = SELECTIONS.validate_json(selections)
except ValidationError as exc:
    raise HTTPException(422, 'Sélections invalides : liste JSON de feuilles attendue') from exc
content = await file.read(MAX_UPLOAD_BYTES + 1)
if len(content) > MAX_UPLOAD_BYTES:
    raise HTTPException(413, 'Fichier supérieur à 10 Mio')
if not file.filename:
    raise HTTPException(422, 'Nom de fichier requis')
```

`SELECTIONS` est un `TypeAdapter(list[SheetSelection])`. Il valide le JSON d’un champ texte multipart. Lire **limite + 1** permet de détecter un dépassement et de répondre `413`.

Exemple de requête à lancer depuis la racine du dépôt, sur ton API locale, avec un jeton ADMIN :

```bash
curl -X POST http://localhost:8000/api/v1/admin/import/preview \
  -H "Authorization: Bearer $TERVO_ADMIN_TOKEN" \
  -F 'source_namespace=archives-dg' \
  -F 'selections=[{"sheet":"Clients","kind":"clients"}]' \
  -F 'file=@backend/tests/fixtures/excel/01_clients_sites_equipements.xlsx'
```

Le retour contient `id`, `items`, `selections` et `total`. Chaque ligne expose `key`, `source`, `mapping`, `original`, `normalized`, `proposals` et `anomalies`. Les octets bruts ne sont jamais renvoyés.

## 3. Rendre les décisions explicites

Extrait réel de [imports.py](../../../backend/app/schemas/imports.py), à partir de la ligne 18 :

```python
class ImportDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    action: Literal['create','associate','ignore','review']
    entity_id: int | None = Field(None, gt=0)
    associate_source_id: str | None = Field(None, min_length=1, max_length=255)
    corrections: dict[str, JsonValue] = Field(default_factory=dict)
    note: str = Field(min_length=1, max_length=2000)


    @model_validator(mode='after')
    def check_association_target(self):
        targets = int(self.entity_id is not None) + int(self.associate_source_id is not None)
        if self.action == 'associate' and targets != 1:
            raise ValueError('Choisir exactement une cible : entity_id ou associate_source_id')
        if self.action != 'associate' and targets:
            raise ValueError('Une cible est réservée à une association')
        return self
```

`extra="forbid"` refuse les champs inconnus ; `str_strip_whitespace` empêche un motif rempli uniquement d’espaces. Le validateur exige une seule cible pour `associate`.

Exemple de corps JSON pour `POST /validate` — adapter l’ID à celui de l’aperçu :

```json
{
  "batch_id": 1,
  "decisions": {
    "Clients:6:clients": {
      "action": "associate",
      "associate_source_id": "C001",
      "note": "Doublon C005 confirmé dans les archives"
    },
    "Clients:7:clients": {
      "action": "ignore",
      "note": "Téléphone et adresse à retrouver avant création"
    }
  }
}
```

`create` confirme la création, `associate` choisit une cible, `ignore` exclut avec motif. `review` applique les corrections puis relance le rapprochement sans forcer une création. L’API ne permet pas d’effacer les coordonnées existantes en associant une ligne incomplète.

## 4. Exécuter seulement ce qui a été validé

Extrait réel de [imports.py](../../../backend/app/schemas/imports.py), à partir de la ligne 44 :

```python
class ExecuteImport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    batch_id: int = Field(gt=0)
    plan_token: str = Field(pattern=r'^[a-f0-9]{64}$')
```

Extrait réel de [imports.py](../../../backend/app/api/v1/imports.py), à partir de la ligne 65 :

```python
@router.post('/execute', response_model=ImportBatchResponse)
async def execute_import(
    body: ExecuteImport,
    user: User = Depends(import_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ImportService(db).execute(body.batch_id, body.plan_token)
```

Le contrat ne permet que `batch_id` et `plan_token`. Ajouter `decisions` ici donne `422` ; un ancien jeton ou un référentiel modifié donne `409`.

Réponse illustrative, réduite aux champs utiles :

```json
{
  "status": "partial",
  "counts": {"committed": 4, "pending": 1, "ready": 0}
}
```

Un HTTP `200` signifie que le rapport est disponible ; il faut lire `status` pour savoir si des lignes restent en attente. Les erreurs historiques restent consultables, même après correction.

## 5. Pourquoi le service ouvre ses propres sessions

L’authentification a déjà effectué un SELECT, donc la session de requête a une transaction ouverte. Le service crée une fabrique de sessions sur le même moteur :
Extrait réel de [import_service.py](../../../backend/app/services/import_service.py), à partir de la ligne 44 :

```python
def __init__(self, db):
    self.sessions = async_sessionmaker(db.bind, expire_on_commit=False)
```

Chaque sous-lot peut ainsi ouvrir son propre `db.begin()`. `expire_on_commit=False` permet de continuer à lire les attributs déjà chargés après le commit. Les tests API PostgreSQL vérifient ce parcours avec authentification réelle.

## 6. Ce que les tests et la CI prouvent

Extrait réel de [test_import_api_v2.py](../../../backend/tests/test_import_api_v2.py), à partir de la ligne 118 :

```python
old = await client.post(PREFIX+'/execute',headers=tokens['admin'],json={'batch_id':batch['id'],'plan_token':first['plan_token']})
assert old.status_code==409
result = await client.post(PREFIX+'/execute',headers=tokens['admin'],json={'batch_id':batch['id'],'plan_token':plan['plan_token']})
assert result.json()['status']=='success'
```

La première exécution emploie l’ancien jeton et reçoit `409`. La suivante utilise celui du plan corrigé et réussit. Le test vérifie ensuite que l’original vide et le téléphone corrigé coexistent dans la trace.

```bash
cd backend
uv run pytest tests/test_import_api_v2.py -q
TERVO_IMPORT_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/TEST_DB \
  uv run pytest tests/test_import_service_v2.py tests/test_import_api_v2.py -q
```

Le [workflow CI](../../../.github/workflows/ci.yml) exécute la suite SQLite, les migrations PostgreSQL aller/retour et les tests service/API import dans des schémas isolés. À la livraison : 214 tests backend, dont 28 API import ; 39 tests service/API rejoués sur PostgreSQL, et CI verte.

TD-B011 et TD-B015 sont clôturés. TD-B016 garde la mesure sur volume réel. Cette tâche ne livre ni écran frontend d’import, ni worker, ni OCR.
