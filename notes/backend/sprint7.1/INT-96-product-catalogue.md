# INT-96 — Catalogue Product

Le catalogue représente une référence commerciale réutilisable. Le numéro de série et le lieu d’installation appartiennent à Equipment (INT-97).

## Modèle et validation

`product` possède un identifiant entier, une référence unique, `name`, `description`, `brand`, `model`, `category`, `characteristics` (objet JSON) et `active` (true par défaut), plus les dates de création/modification. `name` et `description` reprennent la DAT ; `model` et `characteristics` complètent les besoins explicites du sprint. Les chaînes obligatoires sont nettoyées et les valeurs vides refusées. Les catégories restent libres, comme prévu par la DAT.

La contrainte SQL protège l’unicité même en cas de créations concurrentes. Le service contrôle aussi la référence avant écriture ; un conflit renvoie 409 et la transaction est annulée. La référence est sensible à la casse.

## API et architecture

Le routeur gère HTTP et les droits, le service les règles, le repository les accès SQL. Les routes exposées sont :

- `GET /api/v1/products` : recherche sur référence, nom, marque et modèle ; filtres exacts brand/category/active ; pagination page/page_size (alias limit).
- `POST /api/v1/products` : création (201).
- `GET /api/v1/products/{id}` : détail (404 si absent).
- `PATCH /api/v1/products/{id}` : modification partielle et réactivation possible.
- `POST /api/v1/products/{id}/deactivate` : désactivation idempotente.

Aucune suppression physique n’est exposée. Sans filtre active, la liste conserve les produits inactifs. `exclude_unset=True` distingue un champ absent d’un champ explicitement null : description et characteristics peuvent être effacés, les champs obligatoires refusent null.

Les utilisateurs authentifiés consultent. ADMIN gère le catalogue ; TECHNICIAN ne peut pas écrire. MANAGER et COMMERCIAL n’existent pas encore dans le modèle User : TD-B013 suit cette extension.

## Migration et vérifications

La révision `8d431c2a9601` suit `06c3c51d3e72`. Elle crée la table, la contrainte unique et les index ; le downgrade supprime cette nouvelle table. Aucune base applicative n’a été migrée pendant cette tâche.

```bash
cd backend
uv run pytest tests/test_products.py tests/test_sites.py -q
uv run pytest tests/ -q
```

Les tests Product utilisent une base SQLite en mémoire indépendante. Ils couvrent le cycle CRUD sans suppression, les filtres, la pagination, les doublons, les valeurs null, les accès interdits et les ressources absentes. Un test séparé exerce upgrade/downgrade de la nouvelle révision ; il ne valide pas la chaîne historique de migrations sur PostgreSQL.

## Suivi après INT-97

[TD-B012](../../../docs/todos/backend.md#td-b012--relation-product--equipment-et-test-multi-instances) est résolu : Equipment.product_id est une FK non unique et les relations ORM sont bidirectionnelles. Le test `test_replacement_preserves_history_and_product_instances` vérifie deux appareils d’un même produit et la conservation des liens après désactivation. Les critères INT-96 sont désormais cochés.

TD-B013 reste en attente de l’introduction des rôles MANAGER et COMMERCIAL. La revue des todos a été effectuée à la fin d’INT-97.

## Du schéma Python à la modification persistée

Extrait du fichier [product.py](../../../backend/app/models/product.py), lignes 7 à 22 :

```python
class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    brand = Column(String(255), nullable=False, index=True)
    model = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    characteristics = Column(JSON, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    equipment = relationship("Equipment", back_populates="product")
```

`unique=True` protège la référence en base. Le type JSON conserve un dictionnaire de caractéristiques, tandis que `equipment` représente la collection des appareils qui utilisent cette référence. Aucun numéro de série n’est stocké dans Product : il appartient aux instances Equipment.

Le schéma de modification distingue une clé absente d’une clé présente avec la valeur null :

Extrait du fichier [product.py](../../../backend/app/schemas/product.py), lignes 22 à 38 :

```python
class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: Text100 | None = None
    name: Text255 | None = None
    brand: Text255 | None = None
    model: Text255 | None = None
    category: Text100 | None = None
    description: str | None = None
    characteristics: dict | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in self.model_fields_set - {"description", "characteristics"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} ne peut pas être null")
        return self
```

`model_fields_set` contient uniquement les champs envoyés. Le validateur accepte donc `{}` mais rejette `{"name": null}`. Les deux champs volontairement effaçables, `description` et `characteristics`, sont exclus du contrôle.

Extrait du fichier [product.py](../../../backend/app/services/product.py), lignes 42 à 49 :

```python
async def update_product(self, product_id, data):
    product = await self.get_product(product_id)
    values = data.model_dump(exclude_unset=True)
    if "reference" in values:
        await self._check_reference(values["reference"], product_id)
    for key, value in values.items():
        setattr(product, key, value)
    return await self._save(product)
```

`exclude_unset=True` est essentiel : sans lui, les valeurs par défaut du schéma pourraient écraser des champs non fournis. La vérification de référence ignore le produit lui-même grâce à son identifiant. `setattr` applique uniquement les changements demandés.

Extrait du fichier [product.py](../../../backend/app/services/product.py), lignes 26 à 31 :

```python
async def _save(self, product):
    try:
        return await self.repo.save(product)
    except IntegrityError:
        await self.db.rollback()
        raise HTTPException(409, "Référence produit déjà utilisée") from None
```

Une vérification préalable ne suffit pas face à deux requêtes concurrentes : toutes deux pourraient lire « référence disponible ». La contrainte SQL tranche au moment de l’écriture. Le rollback remet la session dans un état utilisable avant la réponse 409. Dans cette implémentation, toute IntegrityError interceptée ici est présentée comme un conflit de référence.

La désactivation conserve les relations aux appareils :

Extrait du fichier [product.py](../../../backend/app/services/product.py), lignes 51 à 54 :

```python
async def deactivate_product(self, product_id):
    product = await self.get_product(product_id)
    product.active = False
    return await self._save(product)
```

Le service change un booléen ; il ne supprime ni Product ni Equipment. Répéter l’appel laisse le produit inactif.
