# INT-109 — Visites showroom et produits présentés

## 1. Pourquoi un nouveau module commercial ?

Une visite est un **événement commercial**, ni une vente ni une installation.
Le socle du sprint 7.1 fournit `Client` et `Product` ; le sprint 7.3 fournit
`Sale`/`SaleLine` ; le cycle terrain 7.4 termine l'intervention et permet
un avis client. INT-109 ajoute l'historique de ce qui a été présenté **avant**
une éventuelle vente, sans déduire un achat d'une simple visite.

Le code est regroupé dans `app/modules/showroom/` : modèle ORM, schémas
Pydantic, repository pour la lecture, service pour les règles et routeur pour
les contrats HTTP. `app/model_registry.py` charge les deux modèles pour
Alembic et les tests, `app/router.py` inclut le routeur une seule fois.
Les chemins horizontaux `app/models/showroom.py` du planning initial
précèdent le refactor monolithe modulaire et ne sont **pas** recréés.

## 2. Identité, cardinalités et contraintes

Une personne peut visiter le showroom avant d'être enregistrée comme client.
Dans `ShowroomVisit`, `client_id` est nullable, tandis que `visited_at`,
`salesperson_id` et `follow_up_status` sont obligatoires. Si `client_id` est
absent, `visitor_name` doit être non blanc. Pydantic contrôle cette règle à
l'entrée et la base la conserve aussi en cas d'écriture SQL directe :

```python
CheckConstraint(
    "client_id IS NOT NULL OR "
    "(visitor_name IS NOT NULL AND length(trim(visitor_name)) > 0)",
    name="ck_showroom_visit_identity",
)
```

Exemples valides : `{"visitor_name":"Sarah", "client_id":null}` ou
`{"visitor_name":null, "client_id":42}`. Une chaîne vide ou composée
d'espaces ne remplace jamais le nom d'un prospect. Une visite peut ensuite
être rattachée à un client via PATCH ; son ID, sa date, son nom d'origine,
ses notes et ses produits restent consultables. Plusieurs visites du même
client restent plusieurs événements, et non un seul « dernier statut »
stocké sur `Client`.

`ShowroomVisitProduct` possède **une clé primaire composée**
`(visit_id, product_id)` : une visite peut présenter plusieurs produits,
un produit peut être présenté à plusieurs visites, mais une même paire ne
peut être enregistrée deux fois. Les FK désignent le catalogue existant
`Product`, pas un appareil installé `Equipment`. La FK produit est
`RESTRICT` : désactiver un produit ne supprime pas les associations passées.
Le service refuse une **nouvelle** présentation d'un produit désactivé.
Le client rattaché et le commercial ne sont pas supprimés en cascade ;
la suppression par l'API d'un client possédant une visite renvoie 409
avant son DELETE pour préserver l'historique. Si une FK devient bloquante
entre cette vérification et le commit (course concurrente), le service
annule la transaction et renvoie aussi 409 plutôt qu'une erreur serveur.

La table showroom ne contient pas de `sale_id`. Le DAT autorise une
visite sans vente et rappelle que plusieurs visites peuvent précéder un
achat ; relier automatiquement une vente à la « dernière visite du client »
invente une provenance non démontrée. Le choix exact de cardinalité et
d'attribution fait l'objet de TD-B023. En particulier, `SOLD` dans le suivi
n'insère aucune ligne `Sale` et ne prouve pas quelle vente s'est conclue.

## 3. Statuts, acteurs et temps

Les sept états V1, partagés entre Pydantic, ORM et migration, sont
`TO_FOLLOW_UP`, `CONSIDERING`, `QUOTE_REQUESTED`, `QUOTE_SENT`, `SOLD`,
`LOST` et `NO_FURTHER_ACTION`. `TO_FOLLOW_UP` est la valeur par défaut
à la création. L'API refuse une autre valeur avec 422 ; la contrainte SQL
`ck_showroom_visit_follow_up_status` empêche aussi une valeur inconnue
injectée directement en base. Les transitions ne constituent **pas**
un automate strict : une visite peut passer de `CONSIDERING` à `LOST`
sans devoir traverser artificiellement un devis.

Le modèle `User` actuel ne connaît que `ADMIN` et `TECHNICIAN`. En
attendant la décision TD-B013, les endpoints showroom exigent un
utilisateur actif et `ADMIN`, y compris pour la consultation des notes
commerciales. `TECHNICIAN` reçoit 403 ; l'absence d'authentification
reçoit 401. À la création, le serveur affecte `salesperson_id` depuis
l'utilisateur authentifié ; un ID arbitraire fourni dans la requête est
refusé avec 403 et PATCH ne permet pas de le changer. Cela évite
d'introduire un rôle `COMMERCIAL` fictif ou d'attribuer silencieusement
une action commerciale à un tiers.

`visited_at` exige une date/heure. Un décalage horaire fourni est normalisé
en UTC avant stockage dans une colonne `DateTime` sans fuseau, conforme
aux autres dates du backend ; une date/heure naïve est traitée comme UTC.
Exemple : `2026-09-21T14:30:00+02:00` est relue sous
`2026-09-21T12:30:00`. Les filtres temporels effectuent la même
normalisation. Les visites sont ordonnées par `visited_at` puis ID,
du plus récent au plus ancien.

## 4. Contrats API

| Route | Comportement | Validation ou refus notable |
|---|---|---|
| `POST /api/v1/showroom/visits` | Crée la visite prospect/client, 201 | Identité absente 422, client inconnu 404, attribution usurpée 403 |
| `GET /api/v1/showroom/visits` | Liste paginée, `total`, `pages`, filtres | `page>=1`, `1<=page_size<=100`, statut enum, intervalle valide |
| `GET /api/v1/showroom/visits/{id}` | Détail et `product_ids` | 404 visite inconnue |
| `PATCH /api/v1/showroom/visits/{id}` | Corrige identité, date, notes, suivi | Ne vide pas l'identité d'un prospect ; statut/date null refusés |
| `POST /api/v1/showroom/visits/{id}/products` | Associe un produit actif, 201 | Visite/produit inconnu 404, produit inactif/doublon 409 |
| `DELETE /api/v1/showroom/visits/{id}/products/{product_id}` | Retire une association erronée, 204 | 404 si elle n'existe pas ; ne supprime ni produit ni visite |

Exemple d'entrée puis de réponse (les IDs et dates serveur sont illustratifs) :

```json
{"visitor_name":"  Sarah Martin  ","visited_at":"2026-09-21T14:30:00+02:00",
 "notes":"Recherche une PAC","follow_up_status":"TO_FOLLOW_UP"}
```

```json
{"id":1,"client_id":null,"visitor_name":"Sarah Martin",
 "visited_at":"2026-09-21T12:30:00","salesperson_id":3,
 "follow_up_status":"TO_FOLLOW_UP","notes":"Recherche une PAC",
 "created_at":"2026-10-03T12:00:00","product_ids":[]}
```

L'ajout d'un produit reçoit `{"product_id":42}` ; la réponse contient
alors `product_ids:[42]`. Il n'y a ni prix catalogue, ni badge « en
exposition », ni vente automatique. Le GET liste peut filtrer par
`client_id`, `salesperson_id`, `visited_from`, `visited_to`,
`follow_up_status` et `product_id`, avec `page`/`page_size`.

## 5. Couches, transaction et erreurs

Le routeur compose `get_current_user` avec la garde de rôle ; Pydantic
valide les champs et interdit les clés supplémentaires. Le service vérifie
les références (`Client`, `Product`) et les règles métier ; le repository
construit la lecture paginée avec `selectinload` des produits présentés.
Le filtre produit utilise un sous-select `EXISTS` plutôt qu'un JOIN :
le `total` compte des **visites**, et non des lignes de présentation.
Le détail recharge les associations avant la validation Pydantic pour
éviter un accès lazy asynchrone hors session.

Pour un ajout, le service valide la visite et le produit, écrit
`ShowroomVisitProduct`, puis commit **une seule transaction**. La clé
primaire composée garde la règle même en cas de deux requêtes concurrentes :

```python
try:
    self.db.add(ShowroomVisitProduct(visit_id=visit_id, product_id=product_id))
    await self.db.commit()
except IntegrityError as exc:
    await self.db.rollback()
    # Une paire déjà enregistrée devient un 409, sans seconde écriture.
```

Le rollback précède toute relecture après une erreur SQL ; sans lui,
la session resterait dans un état transactionnel inutilisable.
La création et le PATCH interceptent aussi les FK invalidées entre la
validation de référence et le commit. Aucun DELETE de visite ni de
prospect n'est exposé. Le DELETE d'une association est destiné à
corriger une présentation saisie par erreur ; il n'apporte **pas**
encore de journal d'audit des modifications.

## 6. Migration et données existantes

La révision `m109e0010001` succède à `k108e0010001`. Elle crée deux
tables avec IDs entiers pour les visites, FK `Client` nullable, FK
`User` non nullable, PK composée pour les présentations, et les
contraintes CHECK d'identité et de statut. Aucune table `Sale`,
`Equipment` ou `Intervention` n'est reconstruite, aucun historique
commercial n'est inventé et aucune ligne existante n'est modifiée.
Le downgrade sur tables vides retire uniquement les nouvelles tables ;
avec une visite enregistrée, il s'arrête **avant tout DDL** pour éviter
de la perdre.

Comme la chaîne historique SQLite complète contient un ancien
`ALTER TYPE` PostgreSQL, la validation ciblée sur SQLite a recréé un
schéma de départ jetable, a retiré les seules nouvelles tables, puis
`alembic stamp k108e0010001`. Ce stamp n'est **jamais** une procédure
pour une base réelle. Upgrade → downgrade vide → re-upgrade ont réussi ;
les CHECK identité/statut rejettent les INSERT invalides et le
downgrade peuplé est refusé, la visite restant en place. Les migrations
complètes PostgreSQL et le comportement sous charge restent à vérifier
au prochain run CI ; le workflow configure le seul scénario API
PostgreSQL sur un schéma isolé, mais **n'a pas été exécuté pour INT-109**.

## 7. Validation réellement effectuée

Les cas `TC-INT-109-01` à `TC-INT-109-04` figurent dans
`docs/stages/stage7/sprint7.5/test-cases.json`, avec les résultats
observés et ce qui demeure ouvert. Une seule recette API teste le
parcours prospect → client, les deux présentations, le doublon et
l'inactif, les sept statuts validés par l'enum/SQL, les filtres,
les réponses 401/403/404/409/422, `SOLD` sans vente, la FK client
et la persistance après désactivation catalogue.

Commandes exécutées localement (depuis `backend/`) :

```sh
uv run pytest tests/test_showroom_api.py tests/test_modular_bootstrap.py \
  tests/test_installation_migration.py -q --tb=short
uv run pytest tests/test_imports_module.py -q \
  -k r0_import_pack_matches_before_snapshot --tb=short
uv run pytest \
  tests/test_equipment_module.py::test_equipment_import_orders_preserve_registry_and_relations \
  tests/test_sales_module.py::test_sales_and_registry_orders_preserve_registry_and_relations \
  tests/test_showroom_api.py -q --tb=short
```

Résultats : **19 réussis**, un warning `passlib/crypt` pour le premier
ensemble ; **1 réussi, 2 non sélectionnés** pour l'oracle d'import
historique ; **5 réussis** pour les quatre gardes d'ordre d'import
ventes/équipements et la recette showroom. La migration ciblée SQLite
sur base jetable a été exécutée
séparément comme décrit ci-dessus. Les gardes
`tests/contract_int109.py` vérifient le delta des tables et de l'OpenAPI
avant de le projeter sur les empreintes R0–R11 inchangées ;
l'import ne doit pas créer de visite fictive.
Pas de suite complète, de tests frontend, de navigateur, de migration
PostgreSQL locale, de CI distante ni de déploiement revendiqués.

## 8. Limites et suite

- **TD-F007** : le backend showroom est disponible ; aucun écran de
  consultation/édition, filtre, navigation ou test E2E frontend n'est livré.
- **TD-B013** : décisions sur les rôles réels MANAGER/COMMERCIAL et leur
  droit d'attribuer les visites à un collègue restent à prendre.
- **TD-B023** : relation précise d'une visite à la vente effective ; éviter
  d'utiliser `client_id` ou `SOLD` comme preuve unique d'origine commerciale.
- Les autres todos (import volumétrique, sécurité du seed, stockage photo
  et PDF) ne sont pas débloqués par INT-109. Depuis sa rédaction, INT-110
  a reçu son feu vert : voir [la note remplacement](INT-110-remplacement-equipement.md).

### Validation distante après le push du sprint

Les résultats locaux ci-dessus restent ceux constatés **avant** le push.
Le code INT-109/110 a ensuite été poussé jusqu'à `624424b` sur `main`.
Le [run CI/CD #37186606561](https://github.com/libileh91/tervo/actions/runs/37186606561)
a réussi : suite backend, migrations PostgreSQL `head → -1 → head`
sur base vide, recette showroom exécutée sur schéma PostgreSQL isolé,
et job frontend (tests, typecheck, build). Le déploiement VPS a été
**sauté**. Cela valide l'aller-retour PostgreSQL vide et la recette
sur son schéma jetable, mais pas le downgrade d'une visite **peuplée**
sur PostgreSQL, ni un écran showroom ou une charge représentative.
