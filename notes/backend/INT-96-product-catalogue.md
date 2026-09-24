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

[TD-B012](../../docs/todos/backend.md#td-b012--relation-product--equipment-et-test-multi-instances) est résolu : Equipment.product_id est une FK non unique et les relations ORM sont bidirectionnelles. Le test `test_replacement_preserves_history_and_product_instances` vérifie deux appareils d’un même produit et la conservation des liens après désactivation. Les critères INT-96 sont désormais cochés.

TD-B013 reste en attente de l’introduction des rôles MANAGER et COMMERCIAL. La revue des todos a été effectuée à la fin d’INT-97.
