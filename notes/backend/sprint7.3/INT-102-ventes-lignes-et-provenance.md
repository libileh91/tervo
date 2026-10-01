# INT-102 — Vente, lignes commerciales et provenance d'installation

**29 septembre 2026 — INT-102 implémentée ; le raccordement différé d'INT-103 (TD-B017) est livré avec elle.** Le parcours d'installation sans vente reste pris en charge. La suite backend locale passe, mais PostgreSQL n'a pas été relancé pour INT-102 et aucune base de déploiement n'a été migrée.

> **Capture historique :** ces résultats décrivent INT-102 au 29 septembre. Depuis R4 et R6, les couches Sale/SaleLine et Installation sont respectivement dans `app/modules/sales/` et `app/modules/installations/`, avec composition explicite dans `app/router.py`. Le contrat commercial nullable et les transactions sont inchangés. Les validations ultérieures sont documentées dans la [note R6 / INT-118](../refactor-monolithe-modulaire/INT-118-R6-installations.md), sans réécrire cette capture ni annoncer un déploiement.

Références : [tâches sprint 7.3](../../../docs/stages/stage7/sprint7.3/tasks.md), [cas de test](../../../docs/stages/stage7/sprint7.3/test-cases.json), [DAT — modèle de données](../../../docs/DAT/new/02-techniques/02-data-model.md), [todo backend](../../../docs/todos/backend.md#td-b017--raccorder-les-installations-autonomes-à-saleline).

## 1. Ce que représente une vente

Une `Sale` est l'événement commercial pour un client et un site. Ses `SaleLine` décrivent les références de catalogue vendues, la quantité et le prix unitaire convenu à la vente. La vente ne représente ni un équipement physique, ni une installation déjà faite, ni un mouvement de stock.

```text
Client ──► Site ──► Sale (DRAFT → CONFIRMED ou CANCELLED)
                         └── 1..N SaleLine ──► Product catalogue
                                  └── 0..N Installation ──► 0..1 Equipment
```

La séparation garde deux parcours possibles :

- **Matériel vendu par Tervo :** Sale → SaleLine → Installation(s) → Equipment.
- **Matériel fourni par le client :** Installation autonome → Equipment ; aucune Sale ou SaleLine artificielle n'est créée.

Une `quantity = 3` est une quantité commerciale, pas trois lignes de vente et pas trois équipements créés lors de la confirmation. Elle autorise jusqu'à trois installations rattachées à cette même ligne. Chaque équipement n'est créé ou lié qu'à la clôture de son installation.

## 2. Modèles ORM et choix de persistance

Fichier : `backend/app/models/sale.py`.

### 2.1 Statut et vente

```python
class SaleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Sale(Base):
    __tablename__ = "sale"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        Integer, ForeignKey("client.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    site_id = Column(
        Integer, ForeignKey("site.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    sale_date = Column(Date, nullable=False)
    status = Column(
        Enum(SaleStatus, native_enum=False, create_constraint=True,
             name="sale_status"),
        nullable=False, default=SaleStatus.DRAFT, server_default="DRAFT",
        index=True,
    )
    lines = relationship(
        "SaleLine", back_populates="sale",
        cascade="all, delete-orphan", order_by="SaleLine.id",
    )
```

`site_id` est requis dans le contrat INT-102. Le service vérifie également que ce site appartient au `client_id` fourni : deux FK valides ne suffiraient pas à garantir cette cohérence métier.

L'énumération SQL est stockée comme chaîne et une contrainte `CHECK` limite les valeurs autorisées. Le statut initial est `DRAFT` en Python et possède aussi un défaut serveur pour les insertions hors ORM.

### 2.2 Ligne de vente et prix

```python
class SaleLine(Base):
    __tablename__ = "sale_line"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_line_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_sale_line_price_nonnegative"),
    )

    sale_id = Column(
        Integer, ForeignKey("sale.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    product_id = Column(
        Integer, ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    description = Column(String(500))
```

`Numeric(12, 2)` et `Decimal` représentent les montants sans arrondi binaire de `float`. `unit_price` est une valeur de vente historisée ; modifier ultérieurement le catalogue ne recalcule pas le prix de la ligne. Les contraintes `CHECK` protègent aussi les écritures qui contourneraient Pydantic.

Les FK de vente vers client/site et de ligne vers produit utilisent `RESTRICT` : l'historique commercial ne doit pas devenir orphelin par suppression d'une référence. SaleLine dépend de sa vente ; la suppression de la vente cascade vers ses lignes en base, tandis qu'aucun endpoint DELETE vente n'est exposé.

## 3. Contrats Pydantic : validation à la frontière HTTP

Fichier : `backend/app/schemas/sale.py`. Tous les corps ont `extra="forbid"` : les champs inconnus ne sont pas ignorés silencieusement.

```python
class SaleLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)


class SaleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: int = Field(gt=0)
    site_id: int = Field(gt=0)
    sale_date: date
    notes: str | None = None
    lines: list[SaleLineCreate] = Field(default_factory=list)
```

Une vente brouillon vide est autorisée afin de saisir l'événement avant ses lignes ; seule la confirmation impose au moins une ligne. `default_factory=list` crée une liste distincte par payload.

Les schémas de réponse sont séparés des schémas d'entrée : ils ajoutent les identifiants et timestamps DB, et exposent les lignes sans permettre au client de choisir leur `sale_id` ou leur identifiant.

```python
class SaleLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    description: str | None
```

`from_attributes=True` permet à Pydantic de sérialiser les objets ORM. Le service charge explicitement `Sale.lines` (`selectinload`) pour éviter une lecture lazy asynchrone au moment de construire la réponse.

## 4. Routes et dépendances API

Fichiers : `backend/app/api/v1/sales.py`, inclusion dans `backend/app/main.py`. Le préfixe configuré donne `/api/v1/sales`.

| Méthode | Route | Résultat |
| --- | --- | --- |
| `POST` | `/sales` | `201`, vente brouillon créée et lignes fournies dans le payload |
| `POST` | `/sales/{sale_id}/confirm` | `200`, confirmation si au moins une ligne |
| `POST` | `/sales/{sale_id}/cancel` | `200`, annulation d'un brouillon |

Exemple de création avec une seule ligne vendant trois unités :

```json
{
  "client_id": 12,
  "site_id": 42,
  "sale_date": "2026-09-29",
  "notes": "Remplacement prévu cet automne",
  "lines": [
    {
      "product_id": 7,
      "quantity": 3,
      "unit_price": "1250.00",
      "description": "PAC modèle convenu au devis"
    }
  ]
}
```

Les routes dépendent de `get_current_user`, comme les routes catalogue déjà existantes. L'utilisateur doit être authentifié et actif selon le garde global. Les rôles `COMMERCIAL` et `MANAGER` ne sont pas ajoutés par INT-102 ; TD-B013 reste ouvert. Il ne faut donc pas présenter cette livraison comme une matrice de permissions commerciales complète.

## 5. Service de vente : validations et transitions

Fichier : `backend/app/services/sale.py`. Le service valide les références métier avant d'ajouter la vente : client existant, site existant et appartenant à ce client, produits existants. Les identifiants inconnus donnent `404`, la discordance client/site donne `422`.

```python
if site.client_id != data.client_id:
    raise HTTPException(422, "Le site ne dépend pas du client indiqué")

for line in data.lines:
    product = await self.db.get(Product, line.product_id)
    if product is None:
        raise HTTPException(404, "Produit non trouvé")
```

Le service construit les lignes avec les champs validés par Pydantic, puis persiste la vente et ses lignes dans la même session. Le chargement de détail utilise `selectinload` :

```python
sale = await self.db.scalar(
    select(Sale)
    .where(Sale.id == sale_id)
    .options(selectinload(Sale.lines))
)
```

### Machine à états commerciale

```text
               ┌── confirm (≥ 1 ligne) ──► CONFIRMED
DRAFT ──────────┤
               └── cancel ───────────────► CANCELLED
```

`CONFIRMED` et `CANCELLED` sont terminaux dans cette version. Toute nouvelle transition depuis un état autre que `DRAFT` retourne `409`. La confirmation d'une vente sans ligne retourne également `409` :

```python
if sale.status != SaleStatus.DRAFT:
    raise HTTPException(409, "Seule une vente brouillon peut changer de statut")
if target == SaleStatus.CONFIRMED and not sale.lines:
    raise HTTPException(409, "Une vente confirmée doit contenir au moins une ligne")
sale.status = target
await self.db.commit()
```

La règle « confirmée = au moins une ligne » est appliquée au moment de la transition. Une vente créée vide reste un brouillon valide, ce qui distingue le brouillon incomplet d'une commande confirmée exploitable par une installation.

## 6. Raccordement à Installation (TD-B017)

Le lien a été livré en même temps que SaleLine existe réellement ; il n'y a pas de colonne entier libre. Les fichiers concernés sont désormais `backend/app/modules/installations/models.py`, `backend/app/modules/installations/schemas.py`, `backend/app/modules/installations/service.py` (chemins actualisés par INT-118) et la migration INT-102 inchangée.

```python
sale_line_id = Column(
    Integer,
    ForeignKey("sale_line.id", ondelete="RESTRICT"),
    nullable=True,
    index=True,
)
```

L'absence de lien est un état métier normal : l'installation autonome et le matériel du client restent valides. `sale_line_id` absent ou `null` est accepté ; la réponse expose alors `null`. Une référence non nulle suit les validations suivantes :

1. SaleLine existe (`404` sinon).
2. Sa vente est `CONFIRMED` (`409` sinon).
3. Le `site_id` d'installation est celui de la vente (`422` sinon).
4. Le nombre d'installations non annulées liées ne dépasse pas `SaleLine.quantity` (`409` sinon).
5. Au `complete`, le produit du nouvel équipement ou de l'équipement rattaché correspond à `SaleLine.product_id` (`422` sinon).

Le verrou de la ligne et le calcul de quantité sont visibles dans le service :

```python
line = await self.db.scalar(
    select(SaleLine)
    .where(SaleLine.id == sale_line_id)
    .options(selectinload(SaleLine.sale))
    .with_for_update()
)
if line is None:
    raise HTTPException(404, "Ligne de vente non trouvée")
if line.sale.status != SaleStatus.CONFIRMED:
    raise HTTPException(409, "La vente doit être confirmée")
if line.sale.site_id != site_id:
    raise HTTPException(422, "Le site doit correspondre à la vente")
```

À la clôture, la vérification exclut l'installation en cours du décompte : elle a déjà été comptée à la planification, et la finalisation ne doit pas consommer une deuxième unité. C'est un détail important : une ligne de quantité trois permet de planifier trois installations, puis de terminer chacune de ces trois installations.

```python
if exclude_installation_id is not None:
    count_query = count_query.where(Installation.id != exclude_installation_id)
```

Un rattachement d'un équipement existant conserve les contrôles INT-103 : site identique, équipement ACTIVE et sans installation antérieure, dates/métadonnées conservées. La provenance commerciale n'autorise donc ni à écraser un équipement ni à l'associer à un site différent.

## 7. Migration Alembic et intégrité historique

Révision `f102e0010001_add_sales.py`, après `e103e0010001` (INT-103). Elle crée `sale` puis `sale_line`, leurs FK/index/contraintes, et enfin ajoute `installation.sale_line_id` avec nullabilité et FK réelle.

```python
with op.batch_alter_table("installation") as batch:
    batch.add_column(sa.Column("sale_line_id", sa.Integer(), nullable=True))
    batch.create_foreign_key(
        "fk_installation_sale_line",
        "sale_line",
        ["sale_line_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    batch.create_index("ix_installation_sale_line_id", ["sale_line_id"])
```

La colonne nullable est ajoutée sans backfill : les installations INT-103 déjà enregistrées restent autonomes. On ne déduit jamais une vente à partir du produit, du site, du prix ou d'une date. Le test de migration vérifie explicitement que l'installation historique ressort avec `sale_line_id IS NULL`.

Le downgrade refuse de supprimer le lien si des installations ont une provenance renseignée :

```python
if op.get_bind().execute(
    sa.text(
        "SELECT id FROM installation "
        "WHERE sale_line_id IS NOT NULL LIMIT 1"
    )
).first():
    raise RuntimeError("Installations commerciales présentes : downgrade destructif refusé")
```

Sur un schéma sans provenance commerciale, le test exerce aussi le downgrade puis contrôle le retrait des tables/colonne de cette révision. Les migrations anciennes ont des particularités SQLite/PostgreSQL : les tests INT-102 couvrent la révision ciblée sur schéma SQLite jetable. La migration complète de l'environnement local n'a pas été validée pour cette tâche.

## 8. Tests et scénarios métier

Fichiers : `backend/tests/test_sales.py`, `backend/tests/test_sale_migration.py`, ainsi que les régressions mises à jour dans `backend/tests/test_installations.py` et `backend/tests/test_installation_migration.py`.

### Cas `quantity = 3`

1. Créer une vente avec une ligne `quantity=3` et un prix décimal.
2. Confirmer la vente ; la réponse est `CONFIRMED`.
3. Créer trois installations sur le même site et liées à la SaleLine.
4. Démarrer puis clôturer l'une d'elles avec `equipment.mode=create` et le produit vendu.
5. Vérifier que `sale_line_id` reste dans la réponse et que l'équipement utilise le bon `product_id`.
6. Tenter une quatrième installation : `409` car les trois unités sont déjà planifiées.

### Cas négatifs et autonomie

- Confirmer une vente vide : `409`.
- Utiliser un produit ou une SaleLine inconnus : `404`.
- Créer une installation avec `sale_line_id: null` : `201`, réponse `sale_line_id: null`.
- Le service refuse une ligne dont la vente n'est pas confirmée et une incohérence site/produit ; ces branches ne disposent pas encore de tests dédiés dans `test_sales.py`.
- Les tests INT-103 existants confirment que le parcours d'installation sans vente fonctionne toujours jusqu'à la création/rattachement d'Equipment.

### Migration

- Création de la FK nullable et vérification que les installations préexistantes restent à `NULL`.
- Contrôle en test de la contrainte `quantity > 0` ; la contrainte de prix non négatif figure dans la migration mais ne dispose pas d'un test direct spécifique.
- Aller-retour de la révision sur schéma temporaire ne contenant pas de provenance commerciale.
- La migration complète est également couverte par la fixture INT-103 mise à jour pour tenir compte du nouveau head Alembic.

## 9. Commandes et résultats de validation

Depuis `backend/` :

```bash
uv run pytest tests/test_sales.py tests/test_installations.py tests/test_sale_migration.py -q
uv run pytest tests/
```

Résultats observés :

| Vérification | Résultat |
| --- | --- |
| Tests ventes + installations + migration ciblée | **54 passed** |
| Suite backend complète | **271 passed**, avertissements de dépréciation préexistants |
| `python -m json.tool docs/stages/stage7/sprint7.3/test-cases.json` | Valide |
| `git diff --check` | Valide |
| PostgreSQL pour INT-102 | Non exécuté |
| `uv run alembic upgrade head` sur la base locale configurée | Échec avant INT-102 : ancienne migration, table `user` déjà existante |

La commande Alembic n'a pas pu atteindre la nouvelle révision ; la validation migration est donc celle du schéma temporaire dédié, pas celle de la base locale déjà existante. Aucun déploiement, commit ni migration de données réelles n'a été effectué. Les avertissements du test complet incluent la dépréciation `crypt` dans passlib et `datetime.utcnow()` dans l'ancien service Intervention ; ils ne proviennent pas d'INT-102.

## 10. Limites et suite

- Pas d'écran frontend de vente livré dans INT-102.
- Pas de rôles `COMMERCIAL`/`MANAGER` (TD-B013), de facturation, de paiement, de stock ou d'achat fournisseur.
- Pas de génération automatique d'équipement à partir de `SaleLine.quantity` : les équipements n'existent qu'à la clôture de chaque installation.
- INT-103 autonome est maintenue ; sa provenance commerciale facultative est désormais raccordée et testée.
- Les tests de permissions JWT propres aux routes de vente, les cas dédiés vente non confirmée/site/produit incohérent, les vérifications PostgreSQL d'INT-102 et la migration sur une base de déploiement restent à exécuter séparément ; ne pas les confondre avec les tests existants d'installation autonome.
