# Refactor monolithe modulaire — Tâches techniques

> **Chantier transverse du Stage 7, avant 7.4 ; pas un sprint de features.**
> **Branche :** `refactor/modular-monolith`, déjà créée. **R0 :** validé, sans nouvel INT.
> **Autorisation :** R1/R2/R3 validés par l'utilisateur et committés ; R3 : `29f034e`, naming documentaire : `8f3e876`. R4 autorisé et vérifié localement, clôture soumise, non committé dans les deux checkouts. R5 à R11 non commencées, feu vert distinct par tâche.
> **Références :** [cadrage et baseline](README.md) · [plan](../../../../notes/backend/extras/tervo_plan_refactor_monolithe_modulaire.md) · [DAT](../../../DAT/new/00-sommaire.md).
> **Estimations :** estimation à confirmer pour chaque tâche.
> **Notes futures :** `notes/backend/refactor-monolithe-modulaire/`. La preuve R0 reste dans `notes/backend/extras/refactor-monolithe-modulaire/`.

Les critères d'INT-113 à INT-115 sont cochés après validation locale et acceptation utilisateur. Les critères techniques INT-116 sont cochés après vérification locale sur le checkout principal ; son acceptation reste attendue. Les captures historiques restent intactes. R5 à R11 restent ouverts et non commencés ; la création du planning ne prouve ni livraison ni exécution de ces vagues. Les cas correspondants et leurs preuves sont dans [test-cases.json](test-cases.json).

## Garde-fous communs à toutes les tâches

- Refactor structurel : contrats HTTP/OpenAPI, comportement, auth actuelle, statuts, schéma et migrations préservés ; aucun changement métier caché.
- Une Base et un registre explicite complet ; mêmes 17 tables et mêmes définitions que R0 après chaque vague. Comparer les snapshots complets, pas seulement les comptes.
- Contrôle Alembic sur PostgreSQL jetable : uniquement la différence préexistante `intervention.technician_id → user.id` (`job_technician_id_fkey` sans `ondelete` côté SQL, `SET NULL` côté ORM). Aucune nouvelle diff ni migration ; ne pas corriger cette FK ici.
- SQLite : suite sur données temporaires ; la chaîne complète Alembic spécifique PostgreSQL n'est pas rendue portable. Aucun test destructeur sur les bases existantes.
- Préserver les appels transverses utiles, propriétaires des transactions, commits et `AsyncSession` partagée. Ne pas réécrire toutes les requêtes pour imposer un graphe théorique.
- Une seule implémentation active après cutover, pas de repository artificiel, de bus/listener, de CQRS ou de UnitOfWork généralisé. Composition des routeurs explicite.
- Clôture de chaque vague : tests ciblés puis suite applicable, snapshots OpenAPI/ORM égaux à R0, contrôle PostgreSQL sans nouvelle différence, note pédagogique avec résultats réels et validation utilisateur. La vague suivante attend son propre feu vert.
- Les adaptations ultérieures du DAT, des tâches de features et des chemins de déploiement devront être autorisées dans leur scope propre ; elles ne sont pas effectuées par la rédaction de ce planning. Le suivi historique PostgreSQL 7.3 reste intact.

---

## INT-113 — R1 — Créer le squelette modulaire

**Statut :** validé par l'utilisateur et committé localement (`73e5ac9`) ; R2 autorisé séparément.
**Dépendance :** R0 validé ; branche dédiée déjà créée.

**User Story**
En tant que **mainteneur backend**,
Je veux **introduire le socle modulaire sans déplacer les domaines métier**,
Afin de **préparer des déplacements progressifs en conservant une application exécutable et une référence SQL unique**.

**Acceptance Criteria**
- [x] Créer seulement le squelette `app/modules/`, `app/router.py` et `app/model_registry.py`, avec les adaptations techniques nécessaires ; aucun domaine déplacé, aucun ensemble de dix modules vides.
- [x] Définir une Base SQLAlchemy unique dans un module technique pur, importable en processus neuf sans charger modèles métier, registre, routers ou application FastAPI.
- [x] Garder la compatibilité `app.models.base.Base` par réexport du même objet (`is`) et de la même metadata ; aucune seconde Base, Table ou classe ORM.
- [x] Le registre charge explicitement les 17 modèles/tables de R0 hors API, y compris ChecklistItem, InterventionPhoto, Material, Review et les quatre modèles d'import ; `configure_mappers()` réussit.
- [x] Importer/réimporter le registre ne change ni les tables, ni leurs objets, ni les mappers ; pas de double déclaration ou de cycle, pas de dépendance à `app.main` ou aux routers.
- [x] `alembic/env.py` charge explicitement le registre avant de lire `Base.metadata` ; son exécution ne dépend pas de l'import préalable de FastAPI.
- [x] `app/router.py` compose explicitement tous les routers existants ; `main` utilise cette composition sans découverte dynamique, doublon ni changement de préfixe ou de contrat.
- [x] Snapshot OpenAPI complet identique à R0 (46 chemins, 63 opérations) et snapshot metadata complet identique à R0 (17 tables), avec contrôle complémentaire des index/enums/defaults non couverts par le snapshot.
- [x] PostgreSQL jetable 17.4 : `upgrade head`, `downgrade -1`, `upgrade head` réussissent jusqu'à `f102e0010001` ; `alembic check` ne propose que la différence FK technicien connue. Aucune migration ni correction de FK.
- [x] Suite SQLite isolée sans régression des 271 tests R0, nouveaux tests du bootstrap réussis, groupes PostgreSQL R0 ventes/installations/migration et imports sans régression (56 et 39 tests de référence).
- [x] Startup/shutdown ASGI réels sans erreur, `/openapi.json` et `/docs` HTTP 200 ; OpenAPI HTTP égale à `app.openapi()` et à R0. Nettoyer processus et ressources jetables.
- [x] Produire la note pédagogique R1 et les preuves après modification distinctes de R0 ; soumettre la clôture sans lancer R2.

**Technical Notes**
- Touchpoints prévus à l'implémentation : `backend/app/modules/`, `backend/app/router.py`, `backend/app/model_registry.py`, module technique propriétaire de Base, `backend/app/models/base.py`, `backend/app/main.py`, `backend/alembic/env.py` et tests de bootstrap. Ces chemins ne sont pas modifiés par ce planning.
- Base est définie dans `app/core/base.py` ; son import seul reste pur. L'import legacy peut conserver temporairement les effets du package `app.models`, mais il doit réexporter le même objet ; isoler les tests de pureté dans des processus neufs.
- Le registre utilise encore les modèles legacy pendant R1. Les exemples de modèles du plan ne sont pas exhaustifs : l'inventaire des 17 tables vient de `R0-metadata.json`.
- Tester les ordres d'import technique → registre et legacy → registre, puis la réimportation du registre sans recharger les modules définissant les classes ORM.
- Références : `R0-openapi.json`, `R0-metadata.json`, `R0-postgresql-results.json` et manifeste sous `notes/backend/extras/refactor-monolithe-modulaire/`. Ne pas les écraser.
- Cas : `TC-INT-113-01` à `TC-INT-113-09`, vérifiés localement. Note et preuves : [INT-113 — R1](../../../../notes/backend/refactor-monolithe-modulaire/INT-113-R1-socle-modulaire.md). Suite finale : 285 tests ; groupes PostgreSQL : 56 + 39 ; contrôle Alembic limité à l'écart FK connu.

---

## INT-114 — R2 — Déplacer `customers`

**Statut :** implémenté, validé localement et accepté par l'utilisateur ; committé sous `ed67168`. R3 autorisé séparément après ce commit.

**User Story**
En tant que **mainteneur backend**,
Je veux **regrouper Client et Site dans le module customers**,
Afin de **isoler la racine du modèle métier et éprouver les relations inter-modules sans changer les parcours existants**.

**Acceptance Criteria**
- [x] Déplacer les modèles, schémas, repositories, services et APIs Client/Site existants vers `app/modules/customers/` ; adapter imports, registre et composition.
- [x] Conserver CRUD, contrats, pagination/filtres, erreurs et protections historiques Client/Site ; relations aux ventes, installations, équipements et interventions résolues.
- [x] Préserver les accès transverses nécessaires sans refonte SQL silencieuse ; supprimer les fichiers source devenus inutiles après cutover, sans double implémentation.
- [x] Tests Client/Site et relations aval sans régression ; garde-fous communs OpenAPI/ORM/PostgreSQL/suite satisfaits.
- [x] Produire la note R2 et soumettre sa clôture à l'utilisateur ; attendre le feu vert R3.

**Technical Notes**
- Source : `models/{client,site}.py`, `schemas/{client,site}.py`, `repositories/{client,site}.py`, `services/{client,site}.py`, `api/v1/{clients,sites}.py`, sous `backend/app/`.
- Les deux entités appartiennent au même contexte ; aucune nouvelle façade générale obligatoire. Les modèles encore legacy doivent continuer à résoudre leurs FK et relations vers customers.
- Cible livrée : `customers/{models,schemas,repository,service,api}.py` ; `api.py` exporte `clients_router` et `sites_router`, inclus aux positions historiques. Les dix anciens fichiers sont supprimés, sans wrappers. Les exports globaux `app.models.Client/Site` réutilisent les mêmes classes pendant la transition.
- Cas : `TC-INT-114-01` et `TC-INT-114-02`, vérifiés localement. [Note et preuves INT-114](../../../../notes/backend/refactor-monolithe-modulaire/INT-114-R2-customers.md) : 43 tests ciblés, 292 dans la suite SQLite, groupes PostgreSQL 56 + 39, OpenAPI/metadata identiques à R0/R1, seule diff FK connue.

---

## INT-115 — R3 — Déplacer `catalog`

**Statut :** R3 accepté par l'utilisateur et committé sous `29f034e`, après le commit de naming documentaire `8f3e876`. R4 a reçu son feu vert distinct.

**User Story**
En tant que **mainteneur backend**,
Je veux **regrouper Product et ses couches existantes dans `catalog`**,
Afin de **rendre explicite la responsabilité de la référence commerciale distincte de l'équipement physique**.

**Acceptance Criteria**
- [x] Déplacer Product, schémas, repository, service et API vers `app/modules/catalog/` ; adapter consommateurs, registre et router.
- [x] Conserver CRUD, unicité, désactivation et liens Product → SaleLine/Equipment ; aucune notion de stock ajoutée, Product ne devient pas Equipment.
- [x] Tests catalogue et consommateurs sans régression ; anciens fichiers retirés après cutover ; garde-fous communs satisfaits.
- [x] Produire la note R3 et soumettre sa clôture avec les preuves locales.
- [x] Faire valider la clôture R3 par l'utilisateur ; commit demandé.
- [x] Vérifier après naming et compléter le manifeste R3 avec les résultats et empreintes des sources finales.

**Technical Notes**
- Source : `models/product.py`, `schemas/product.py`, `repositories/product.py`, `services/product.py`, `api/v1/products.py`, sous `backend/app/`.
- Préserver les FK et contraintes de la référence produit, sans cascade destructrice ni réécriture des équipements historiques.
- Cible après naming : `catalog/{models,schemas,repository,service,api}.py` et init pur ; cinq fichiers source supprimés, pas de wrappers. Le réexport `app.models.Product` garde l'identité de classe pendant la transition.
- Le déplacement ne modifie pas la politique d'activité : les services actuels autorisent un produit inactif pour une nouvelle vente et un nouvel équipement.
- Cas : `TC-INT-115-01`, vérifié localement avant et après naming. [Note et preuve R3](../../../../notes/backend/refactor-monolithe-modulaire/INT-115-R3-catalogue.md) : 128 tests ciblés, 299 SQLite, groupes PostgreSQL 56 + 39 ; OpenAPI/metadata identiques à R0/R1/R2, seul écart FK connu ; 13 définitions et AST des modules hors imports identiques au parent R2. Le nouveau test est `tests/test_catalog_module.py` ; résultats finaux dans `R3-validation.json → post_naming`. R4 attend son propre feu vert.

---

## INT-116 — R4 — Déplacer `sales`

**Statut :** implémenté, vérifié localement et accepté par l'utilisateur ; commit INT-116 demandé dans le checkout principal. R5 autorisé distinctement après ce commit.

**User Story**
En tant que **mainteneur backend**,
Je veux **regrouper Sale, SaleLine et leur workflow dans sales**,
Afin de **isoler la vente tout en préservant le raccordement commercial des installations**.

**Acceptance Criteria**
- [x] Déplacer les modèles Sale/SaleLine, schémas, SaleService et API vers `app/modules/sales/` ; adapter imports, registre et composition, sans ajouter de repository artificiel.
- [x] Conserver création DRAFT, confirmation avec au moins une ligne, annulation, `quantity > 0`, prix Decimal/Numeric et vérifications Client/Site/Product.
- [x] Le lien `SaleLine 1 → N Installation` et sa limite de quantité restent identiques ; aucun rôle ni workflow commercial futur ajouté.
- [x] Tests ventes et raccordement commercial sans régression ; cutover et garde-fous communs satisfaits.
- [x] Produire la note R4 et soumettre sa clôture avec les preuves locales.
- [x] Faire valider la clôture R4 par l'utilisateur avant commit ; feu vert distinct R5 reçu.

**Technical Notes**
- Source : `models/sale.py`, `schemas/sale.py`, `services/sale.py`, `api/v1/sales.py`, sous `backend/app/`. Aucun repository sales n'existe dans le périmètre de départ.
- Garder les calculs/valeurs monétaires sans conversion flottante ; ne pas transformer le move en refonte des accès SQL ou de TD-B013.
- Cible livrée : `sales/{models,schemas,service,api}.py` et init pur ; quatre anciens fichiers supprimés, aucun repository. Réexports globaux Sale/SaleLine/SaleStatus identiques.
- Cas : `TC-INT-116-01` et `TC-INT-116-02`, vérifiés localement. [Note et preuve INT-116](../../../../notes/backend/refactor-monolithe-modulaire/INT-116-R4-sales.md) : 100 tests ciblés, 315 SQLite, groupes PostgreSQL 56 + 39 ; OpenAPI/metadata identiques à R0 et références suivantes, seul écart FK connu. AST des quatre couches égal hors imports : 11 définitions. Auth ADMIN/TECHNICIAN conservée et testée.

---

## INT-117 — R5 — Déplacer `equipment`

**Statut :** non commencé — feu vert distinct requis après validation d'INT-116.

**User Story**
En tant que **mainteneur backend**,
Je veux **regrouper le cycle de vie de l'équipement physique dans equipment**,
Afin de **préparer le déplacement d'Installation sans perdre l'historique physique**.

**Acceptance Criteria**
- [ ] Déplacer modèle, schémas, repository, service et API vers `app/modules/equipment/` ; adapter registre, router et consommateurs.
- [ ] Préserver FK Site/Product, `installation_id` nullable et unique, remplacement ancien → nouveau et historiques ; aucun statut PLANNED ni installation fictive.
- [ ] Conserver ACTIVE / OUT_OF_SERVICE / REPLACED / RETIRED, validations et protections existantes ; tests équipement/remplacement sans régression.
- [ ] Cutover et garde-fous communs satisfaits ; produire la note R5 et obtenir validation avant tout feu vert R6.

**Technical Notes**
- Source : `models/equipment.py`, `schemas/equipment.py`, `repositories/equipment.py`, `services/equipment.py`, `api/v1/equipment.py`, sous `backend/app/`.
- Ne pas réimplémenter le remplacement amorcé par INT-97 ni anticiper INT-110. Un équipement historique reste valide sans installation enregistrée.
- Cas : `TC-INT-117-01`.

---

## INT-118 — R6 — Déplacer `installations`

**Statut :** non commencé — feu vert distinct requis après validation d'INT-117.

**User Story**
En tant que **mainteneur backend**,
Je veux **regrouper Installation et son orchestration dans installations**,
Afin de **préserver les parcours autonomes et commerciaux avec leur atomicité actuelle**.

**Acceptance Criteria**
- [ ] Déplacer modèle, schémas, repository, service et API vers `app/modules/installations/` ; adapter imports, registre et router.
- [ ] Parcours autonome inchangé : site requis, `sale_line_id` absent/null accepté, aucune vente fictive ; create/attach explicitement conservés.
- [ ] Parcours commercial inchangé : vente confirmée, ligne connue, limite de quantité, cohérence site/produit et provenance.
- [ ] Installation + Equipment restent dans la même transaction/session : rollback après écriture, clôture répétée et concurrence sans doublon ni écriture partielle.
- [ ] Transitions, dates, métadonnées, auth et protections des historiques identiques ; tests SQLite et PostgreSQL critiques sans régression.
- [ ] Cutover et garde-fous communs satisfaits ; note R6 et validation de clôture avant feu vert R7.

**Technical Notes**
- Source : `models/installation.py`, `schemas/installation.py`, `repositories/installation.py`, `services/installation.py`, `api/v1/installations.py`, sous `backend/app/`.
- Les appels Python vers equipment sont autorisés ; pas de bus ni d'UnitOfWork ajouté. Conserver le propriétaire des commits et les verrouillages.
- Cas : `TC-INT-118-01` à `TC-INT-118-03` ; reprendre les scénarios détaillés INT-103/INT-102 sans modifier leur suivi historique.

---

## INT-119 — R7 — Déplacer `interventions`

**Statut :** non commencé — feu vert distinct requis après validation d'INT-118.

**User Story**
En tant que **mainteneur backend**,
Je veux **rapprocher le contexte terrain existant dans interventions**,
Afin de **donner une frontière cohérente à 7.4 sans implémenter ses évolutions métier pendant le déplacement**.

**Acceptance Criteria**
- [ ] Déplacer ensemble Intervention, ChecklistItem, InterventionPhoto, Material, Review et leurs schémas/repositories/services/APIs existants vers `app/modules/interventions/`.
- [ ] Conserver les cinq familles de routes, règles, pièces jointes, auth, historique et relations ; aucun modèle renommé ou transformé.
- [ ] Ne livrer aucune évolution INT-104 à INT-108 : ni snapshots de checklist, ni nouveaux Photo/MaterialUsage, ni clôture ou rapport versionné futur.
- [ ] Tests terrain et consommateurs reports/imports sans régression ; cutover et garde-fous communs satisfaits.
- [ ] Documenter les nouveaux chemins à reprendre dans le planning 7.4 avant ses features, dans une mise à jour ultérieure autorisée ; note R7, validation puis attente du feu vert R8.

**Technical Notes**
- Source sous `backend/app/` : modèles `intervention`, `checklist_item`, `intervention_photo`, `material`, `review` ; couches associées aux routes `interventions`, `checklist`, `photos`, `materials`, `reviews`.
- Le schéma réellement livré, pas le modèle futur du DAT, est la cible de non-régression. Conserver la FK technicien connue telle quelle.
- Cas : `TC-INT-119-01` et `TC-INT-119-02`.

---

## INT-120 — R8 — Déplacer `reports`

**Statut :** non commencé — feu vert distinct requis après validation d'INT-119.

**User Story**
En tant que **mainteneur backend**,
Je veux **regrouper l'API rapport, le rendu PDF et le template dans reports**,
Afin de **rendre la génération existante autonome dans son package sans changer son contenu fonctionnel**.

**Acceptance Criteria**
- [ ] Déplacer API, ReportExporter/rendu et template existants vers `app/modules/reports/` ; adapter imports, composition et résolution du chemin du template.
- [ ] Rapport existant généré avec les mêmes données métier et contrat HTTP ; chargement du template indépendant d'un ancien chemin ou du répertoire courant.
- [ ] Aucun modèle Report/ReportVersion créé : versionnement réservé à INT-107 ; aucun nouveau service vide.
- [ ] Tests rendu/route sans régression ; cutover et garde-fous communs satisfaits ; note R8, validation puis attente du feu vert R9.

**Technical Notes**
- Source : `backend/app/api/v1/reports.py`, `backend/app/exporters/report.py`, `backend/app/exporters/report_template.html`.
- Cible : `modules/reports/api.py`, rendu et `templates/` ; créer les couches uniquement si elles ont une responsabilité réelle. Comparer le contenu métier du PDF, pas une identité binaire artificielle liée aux métadonnées temporelles.
- Cas : `TC-INT-120-01`.

---

## INT-121 — R9 — Déplacer `imports`

**Statut :** non commencé — feu vert distinct requis après validation d'INT-120.

**User Story**
En tant que **mainteneur backend**,
Je veux **regrouper le pipeline d'import et son cycle de vie dans imports**,
Afin de **préserver le différenciateur Excel avec une preuve fonctionnelle avant/après sur les mêmes sources**.

**Acceptance Criteria**
- [ ] Avant le déplacement R9, vérifier les empreintes R0 du pack fixe et capturer ses résultats fonctionnels sur une base jetable avec état initial documenté.
- [ ] Déplacer ImportBatch/ImportRecord/ImportReference/ImportError, schémas, APIs, planner, service et pipeline vers `app/modules/imports/` et `pipeline/`, sans devenir propriétaire des entités métier importées.
- [ ] Rejouer exactement le même pack, mapping, décisions et état métier initial après déplacement ; comparer Batch/Record/Reference/Error et clients/sites/équipements/interventions créés ou rattachés (produits lorsqu'utilisés).
- [ ] Résultats identiques : provenance fichier/feuille/ligne, brut/normalisé, anomalies, rapprochements, décisions, plans, compteurs, statuts, liens et erreurs/orphelins ; toute normalisation de champs volatils est documentée et n'efface aucune différence métier.
- [ ] Préserver SHA-256, plan validé sans recalcul, reprise/idempotence, bail/verrouillage/sérialisation et transactions par sous-lots ; rollback sans perte des sous-lots déjà commitées.
- [ ] Préserver `.xlsx`/`.csv`, multi-feuilles et sources intactes ; équipements historiques sans installation et interventions sans équipement acceptés selon le contrat existant ; aucune vente/installation fictive.
- [ ] Tests pipeline/API SQLite et PostgreSQL sans régression ; cutover et garde-fous communs satisfaits ; note R9 avec preuves avant/après, validation puis attente du feu vert R10.

**Technical Notes**
- Source : `backend/app/api/v1/imports.py`, `models/import_batch.py`, `schemas/imports.py`, `services/import_planner.py`, `services/import_service.py` et `importers/*` sous `backend/app/`.
- Pack : `backend/tests/fixtures/excel/`, empreintes dans le manifeste R0. R0 a validé les tests existants et figé les sources, pas livré la comparaison complète des résultats ; capturer le « avant » avant le move R9.
- Comparer les identifiants directement si les états initiaux déterministes le permettent ; sinon utiliser une correspondance stable conservant les relations. Exclure seulement les identifiants techniques/horodatages/jetons volatils justifiés, jamais les décisions ou liens métier.
- Ne pas convertir les transactions en « un commit par fichier », ni supprimer les erreurs ou rendre Sale/Installation obligatoires. La mesure sur volume représentatif TD-B016 reste distincte.
- Cas : `TC-INT-121-01` à `TC-INT-121-03`.

---

## INT-122 — R10 — Déplacer `identity`, `dashboard` et finaliser la composition

**Statut :** non commencé — feu vert distinct requis après validation d'INT-121.

**User Story**
En tant que **mainteneur backend**,
Je veux **isoler l'identité et les lectures transverses puis finaliser le wiring**,
Afin de **conserver une authentification unique et une composition FastAPI explicite après les déplacements métier**.

**Acceptance Criteria**
- [ ] Déplacer User/Auth et leurs couches existantes vers `app/modules/identity/` ; garder JWT/hash/primitives génériques dans `core` et adapter deps sans cycle.
- [ ] Auth et autorisations actuelles inchangées : utilisateur actif requis ; aucun rôle MANAGER/COMMERCIAL ni nouvelle règle d'affectation introduit.
- [ ] Déplacer dashboard vers `app/modules/dashboard/` comme agrégation de lecture uniquement ; réponses inchangées, aucune écriture ou règle propriétaire absorbée.
- [ ] Adapter imports et entrypoint du seed si nécessaire ; conserver `app/seed.py` si le déplacement n'apporte rien, sinon une seule implémentation sous `backend/scripts/seed.py` avec contrat d'exécution documenté.
- [ ] Registre complet et composition finale explicite ; tests auth/dashboard/seed et garde-fous communs satisfaits, aucune seconde implémentation active.
- [ ] Produire la note R10, faire valider la clôture puis attendre le feu vert R11.

**Technical Notes**
- Source : `backend/app/models/user.py`, `schemas/auth.py`, `api/v1/auth.py`, `api/v1/dashboard.py` et couches d'agrégation réellement présentes ; seed existant et `core/deps.py` à vérifier avant déplacement.
- Aucun service/repository imposé à identity ou dashboard pour la symétrie. Le seed réutilise les règles existantes au lieu de les dupliquer.
- Cas : `TC-INT-122-01` et `TC-INT-122-02`.

---

## INT-123 — R11 — Retirer les couches horizontales legacy

**Statut :** non commencé — feu vert distinct requis après validation d'INT-122.

**User Story**
En tant que **mainteneur backend**,
Je veux **retirer les packages horizontaux devenus inutiles après tous les cutovers**,
Afin de **terminer le monolithe modulaire sans références cassées et avec une validation globale traçable**.

**Acceptance Criteria**
- [ ] Vérifier toutes les références legacy dans runtime, tests, Alembic, seed, scripts et configuration ; résoudre les références exécutables avant suppression, sans réécrire les preuves historiques.
- [ ] Supprimer `app/models`, `repositories`, `schemas`, `services`, `api/v1`, `importers`, `exporters` uniquement lorsqu'ils sont devenus inutiles/vides ; retirer le shim Base devenu inutile sans changer l'objet Base technique.
- [ ] Aucun import exécutable legacy ni double implémentation métier restante ; chaque domaine actif possède sa frontière, `core` reste technique.
- [ ] Suite backend et groupes PostgreSQL critiques sans régression ; migrations complètes et aller-retour PostgreSQL réussis avec uniquement la différence FK connue.
- [ ] Snapshots OpenAPI/metadata identiques à R0 ; startup/shutdown et documentation HTTP valides ; parcours frontend critiques existants Client/Site, vente/installation autonome/commerciale, import et rapport sans régression.
- [ ] Preuve d'import avant/après R9 conservée ; chemins des documents Stage 7 concernés repris avant les features 7.4 dans une scope ultérieure autorisée, sans changer leur historique de validation.
- [ ] Note R11 et bilan global produits avec limites réelles ; clôture soumise à validation utilisateur, sans annoncer déploiement ou features futures livrés.

**Technical Notes**
- Recherche finale : `app.models`, `app.repositories`, `app.schemas`, `app.services`, `app.api.v1`, `app.importers`, `app.exporters`. Distinguer référence exécutable et citation historique légitime.
- Ne pas effacer un package encore requis par une migration historique : résoudre le chargement sans modifier les opérations SQL ni masquer la différence FK connue.
- Les tests frontend concernent les parcours actuellement livrés ; aucun écran futur de 7.4/7.5 n'est créé dans le refactor.
- Cas : `TC-INT-123-01` et `TC-INT-123-02`.
