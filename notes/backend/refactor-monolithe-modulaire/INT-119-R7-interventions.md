# INT-119 — R7 : une frontière pour le terrain existant

> **Planning :** [INT-119](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md#int-119--r7--déplacer-interventions).
> **Parent R6 :** `90346f54636d43dfcf3276eb451b960b2137d681`, branche `refactor/modular-monolith`.
> **État :** accepté et committé sous `7a52d03` dans le worktree Delta attaché. R8 autorisé et vérifié localement ; voir la [note INT-120](INT-120-R8-reports.md). Le manifeste conserve sa capture avant acceptation.
> **Preuve :** [R7-validation.json](R7-validation.json). Les captures historiques R0 à R6 restent intactes.

## 1. Reprise de R6 et portée du feu vert

L'utilisateur a accepté R6 et demandé « commit & passe au R7 ». Les 17
empreintes sources/tests R6 correspondent au manifeste. Avant commit, bootstrap,
module installations, installations et ventes ont été rejoués en isolation :
**81 passed, 1 warning, 21,27 s**.

`[DEV]INT-118 — Refactor : isoler le domaine installations` est `90346f5`.
Il regroupe code, tests, notes dépendantes et suivi R6, sans développement R7.
Le commit est créé dans le worktree attaché, sans push ni écriture directe du
checkout principal. Le manifeste R6 conserve sa capture avant acceptation.

R7 déplace le **contexte terrain déjà livré** : Intervention, ChecklistItem,
InterventionPhoto, Material, Review et leurs couches. Il ne réalise pas les
features INT-104 à INT-108 du sprint 7.4 :

- pas de ChecklistTemplate ni d'InterventionChecklist snapshot ;
- pas de renommage InterventionPhoto → Photo ;
- pas de remplacement Material → MaterialUsage ;
- pas de nouveau résultat métier d'intervention ;
- pas de Report/ReportVersion, de versionnement ou d'envoi de rapport.

Le DAT expose une cible métier ; pour ce refactor, l'invariant est le code
actuel. Déplacer et remodeler dans le même changement rendrait la non-régression
beaucoup plus difficile à vérifier.

## 2. Organisation choisie : un domaine, des fichiers locaux conservés

```text
app/modules/interventions/
├── __init__.py
├── models/
│   ├── intervention.py
│   ├── checklist_item.py
│   ├── intervention_photo.py
│   ├── material.py
│   └── review.py
├── schemas/
│   ├── intervention.py
│   └── review.py
├── repositories/
│   ├── intervention.py
│   ├── checklist.py
│   ├── photo.py
│   ├── material.py
│   └── review.py
├── services/
│   ├── intervention.py
│   ├── checklist.py
│   ├── photo.py
│   ├── material.py
│   └── review.py
└── api/
    ├── interventions.py
    ├── checklist.py
    ├── photos.py
    ├── materials.py
    └── reviews.py
```

Chaque sous-package possède également un `__init__.py` à docstring seule :
**six init purs**, **22 modules déplacés**. Les 22 anciennes sources sont retirées.

Deux approches étaient plausibles :

| Approche | Conséquence |
|---|---|
| Fusionner les cinq familles dans `models.py`, `service.py`, `api.py`, etc. | Services et routeurs volumineux, mélange des responsabilités, comparaison source moins directe |
| Garder les fichiers sous des couches locales au domaine | Frontière métier commune, opérations spécialisées lisibles, comparaison fichier par fichier |

La seconde est retenue. Ce n'est pas le retour aux couches horizontales de toute
l'application : ces dossiers vivent **dans le domaine terrain**. Les petits
domaines customers/catalog/installations gardent leurs fichiers plats ; aucune
symétrie artificielle n'est imposée. Il n'y a pas un nouveau module métier
indépendant pour chaque checklist ou photo.

Le mapping est mécanique :

| Source sous `backend/app/` | Destination sous `modules/interventions/` |
|---|---|
| `models/{intervention,checklist_item,intervention_photo,material,review}.py` | `models/`, mêmes noms |
| `schemas/{intervention,review}.py` | `schemas/`, mêmes noms |
| `repositories/{intervention,checklist,photo,material,review}.py` | `repositories/`, mêmes noms |
| `services/{intervention,checklist,photo,material,review}.py` | `services/`, mêmes noms |
| `api/v1/{interventions,checklist,photos,materials,reviews}.py` | `api/`, mêmes noms |

Le registre et le router importent explicitement les **fichiers feuilles**.
Importer `app.modules.interventions.models` seul n'enregistre pas implicitement
les modèles ; importer `api` seul ne compose pas les routeurs.

## 3. Le modèle SQL est conservé, pas remplacé par la cible 7.4

Les cinq modèles utilisent [la Base unique](../../../backend/app/modules/interventions/models/intervention.py#L24).
Leurs tables restent `intervention`, `checklist_item`, `intervention_photo`,
`material` et `review`. Tous les IDs d'entités restent des entiers. Les noms
aléatoires de fichiers et les tokens d'avis ne sont pas des IDs d'entités.

### Intervention et ses références

```python
equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=True, index=True)
equipment = relationship("Equipment", back_populates="interventions")
technician_id = Column(
    Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
)
```

`equipment_id` nullable laisse valides les interventions historiques non
rattachées à un appareil. Un lien non null est vérifié par le service :
appareil existant (404 sinon) et même site (422 sinon).
La relation site et ses règles de suppression SQL/ORM restent inchangées.
R7 ne profite pas du déplacement pour corriger les anciennes politiques de cascade.

Intervention garde `PLANNED / IN_PROGRESS / COMPLETED / CANCELLED`.
**PLANNED reste valable pour une intervention**, contrairement à Equipment.
Les priorités ORM restent `basse / normale / haute / urgente` ;
`under_warranty` reste booléen, sans nouveau résultat métier.

### Checklist, photo, matériel, avis

| Modèle | Données et relation actuelles |
|---|---|
| ChecklistItem | `category`, `label`, `checked`, `note`, `position` ; item directement attaché à Intervention |
| InterventionPhoto | `category`, chemins original/thumbnail, `taken_at` ; URLs calculées |
| Material | `name`, `quantity` texte, `position` ; pas de quantité/unité numériques imposées |
| Review | Une FK Intervention unique, note, commentaire, nom, token et expiration, date de soumission |

Les quatre relations enfant gardent la cascade ORM `all, delete-orphan`.
`Intervention.review` reste `uselist=False` ; l'unicité SQL protège un avis
maximum par intervention. Cela ne crée pas une version de rapport.

Les réexports `app.models.Intervention/ChecklistItem/InterventionPhoto/Material/Review`
pointent sur les **mêmes classes** déplacées, pas sur des copies ou wrappers.
Les tests chargent d'abord terrain puis legacy, et l'ordre inverse ; le registre
est rappelé : **17 tables, 17 mappers, une seule Base** et relations résolues
vers les mêmes objets.

## 4. Contrats HTTP : cinq familles, vingt opérations terrain

Le préfixe `/api/v1` reste appliqué par la composition globale. Les routeurs
conservent leurs préfixes, tags, méthodes, corps et réponses.

| Famille | Routes existantes | Auth/règles à conserver |
|---|---|---|
| Intervention, 8 opérations | GET/POST collection, GET/PUT/DELETE détail, PUT start/cancel/complete | JWT ; création assignée à l'utilisateur, contrôles de workflow |
| Checklist, 4 opérations | GET/POST `/{id}/checklist`, PUT batch, PUT item | JWT ; mutations avec vérification d'assignation |
| Photos, 2 opérations | POST `/{id}/photos`, DELETE `/{id}/photos/{photo_id}` | JWT ; assignation et contrat multipart |
| Matériel, 4 opérations | GET/POST `/{id}/materials`, PUT/DELETE détail matériel | JWT ; règles existantes d'assignation |
| Avis, 2 opérations | GET `/review/{token}`, POST `/review/{token}/submit` | **Public**, validité/expiration du token |

L'API rapport demeure hors module terrain jusqu'à R8. Sa route de téléchargement
et le renderer existants sont seulement adaptés aux nouveaux imports.
La famille avis ne reçoit pas de JWT global « par uniformité » : ce serait
une régression du lien envoyé au client.

### Créer et modifier une intervention

```json
{
  "site_id": 12,
  "equipment_id": null,
  "title": "Entretien PAC",
  "scheduled_date": "2026-09-28",
  "priority": "normale",
  "under_warranty": false
}
```

Les [schémas existants](../../../backend/app/modules/interventions/schemas/intervention.py#L33)
conservent titre non vide/maximum 255 et `equipment_id > 0` quand présent.
Les heures restent des chaînes dans l'entrée, converties par `time.fromisoformat`
dans le service. Pas de nouvelle normalisation de fuseau ou validation de
planning calquée sur Installation.

La priorité est une chaîne côté schéma, pas un enum Pydantic plus strict.
Un test préserve cette forme sans promettre qu'une priorité arbitraire
est valide en base. R7 ne cache pas un durcissement du contrat.

L'update utilise `model_fields_set` pour distinguer un `equipment_id` absent
d'un `equipment_id: null` explicitement envoyé. L'absence ne détache pas
l'appareil ; null explicite peut le détacher, selon le contrat livré.
Les autres traitements de valeurs nulles sont conservés tels quels.

### Formes spécialisées conservées

```json
{"items": [{"id": 7, "checked": true, "note": "Contrôle effectué"}]}
```

La checklist batch ne devient pas un résultat structuré de snapshot.
Material accepte toujours une quantité comme `"2 mètres"`. PhotoRef expose
`file_url` et `thumbnail_url` optionnelle, pas un blob dans la réponse.
ReviewSubmitRequest conserve note 1 à 5, commentaire maximum 2000 et nom
maximum 255. Le lien expiré/inconnu reste 404 ; avis déjà soumis reste 400.

## 5. Workflow et transactions : ne pas confondre terrain et Installation

Le [service Intervention](../../../backend/app/modules/interventions/services/intervention.py#L83)
valide site/appareil, assigne le technicien courant, convertit les heures,
crée l'intervention puis crée les cinq items de checklist par défaut.

| Action | État requis | Contrôles actuels | Résultat |
|---|---|---|---|
| start | PLANNED | Technicien assigné ; aucune autre intervention IN_PROGRESS | IN_PROGRESS, `started_at` |
| cancel | PLANNED | Technicien assigné | CANCELLED |
| complete | IN_PROGRESS | Technicien assigné ; checklist sans item non coché | COMPLETED, observations et dates |

Un statut incompatible donne **400**, un autre technicien **403**.
Ne pas recopier les codes 409 du workflow Installation : la non-régression
porte sur le contrat propre à chaque domaine.
La vérification obligatoire de photos n'est pas ajoutée à complete.

### Où vivent les commits ?

| Opération | Propriétaire existant du commit |
|---|---|
| CRUD Intervention | InterventionRepository |
| start/cancel/complete | InterventionService |
| Seed checklist et ajout custom | ChecklistService |
| Update/batch checklist | ChecklistRepository |
| CRUD photo/matériel/avis | Le repository de la famille |

Les services réutilisent la session injectée ; R7 ne crée pas de session interne
ni de transaction globale artificielle. **Mais session partagée ne signifie
pas commit unique sur tout le parcours.**

Contrairement à Installation, la création d'Intervention committe dans son
repository avant le seed checklist, qui committe ensuite. La complétion
committe l'état COMPLETED **avant** la création de Review :

```python
intervention.status = InterventionStatus.COMPLETED
intervention.completed_at = datetime.utcnow()
await self.repo.db.commit()
await self.repo.db.refresh(intervention)
```

Puis :

```python
review_repo = ReviewRepository(self.repo.db)
share_token = uuid.uuid4().hex
expires_at = intervention.completed_at + timedelta(days=30)
await review_repo.create(
    {
        "intervention_id": intervention.id,
        "rating": 5,  # valeur par défaut, sera écrasée par le client
        "share_token": share_token,
        "share_token_expires_at": expires_at.replace(tzinfo=None),
    }
)
```

Ce code est conservé, pas présenté comme une atomicité Intervention + Review.
Les garanties de rollback/concurrence démontrées pour Installation ne sont pas
transposées par analogie. Une évolution de la clôture relève d'un périmètre
métier ultérieur autorisé, pas d'un déplacement.

Les appels `datetime.utcnow()` restent ceux du parent ; leurs warnings Python
3.12 sont rapportés, pas corrigés furtivement dans R7.

## 6. Photos : déplacement de code, pas déplacement des pièces jointes

Le [PhotoService](../../../backend/app/modules/interventions/services/photo.py#L28)
garde `settings.UPLOAD_DIR / "photos"`, JPEG/PNG/WebP acceptés et maximum 10 Mo.
HEIC reste refusé. Il écrit les octets originaux, génère une miniature Pillow
300 × 300 maximum et enregistre les chemins dans la base.

```python
upload_dir = Path(settings.UPLOAD_DIR) / "photos"
upload_dir.mkdir(parents=True, exist_ok=True)
file_path = upload_dir / filename
thumb_path = upload_dir / thumb_filename
```

La miniature est JPEG ; l'original n'est pas réencodé par ce refactor.
Les noms aléatoires restent ceux du service. Le modèle calcule l'URL à partir
du basename, et le service rend ses URLs selon UPLOAD_URL : ces deux règles
préexistantes sont conservées, pas refondues.

Si la génération de miniature échoue, le service retire l'original et renvoie
400. La suppression retire les fichiers existants puis la ligne SQL.
SQL et filesystem ne forment pas une transaction atomique ; aucune compensation
généralisée n'est ajoutée. Le déplacement ne touche pas les uploads existants.

Le nouveau test crée une vraie image 640 × 480, appelle PhotoService avec
UploadFile, compare les octets de l'original, ouvre la miniature et vérifie
ses dimensions. Il relit ensuite le détail Intervention via HTTP et compare
les IDs/URLs. Ce test est une preuve service + disque + consommateur HTTP,
pas un nouveau test d'auth du endpoint multipart.

## 7. Consommateurs transverses et preuve de déplacement pur

| Consommateur | Adaptation R7 |
|---|---|
| customers API/service | Historique et statistiques Intervention : imports déplacés |
| dashboard API | Schéma résumé et InterventionService dans terrain, route toujours legacy jusqu'à R10 |
| imports planner/service | Validation InterventionCreate et modèle cible déplacés |
| reports API/exporter | Status, repository et modèle déplacés ; renderer/template inchangés hors import |
| seed | Import des modèles/enums déplacé, aucun seed exécuté |
| Tests historiques | Chemins d'import uniquement ; scénarios conservés |

Le schéma `DashboardSummaryResponse` vit encore dans le fichier Intervention
déplacé. Le sortir maintenant ajouterait un autre refactor ; R10 est la vague
prévue pour dashboard. Les appels Python utiles entre domaines restent autorisés.

La comparaison AST couvre **les 22 modules complets**. Dans l'AST du parent,
on substitue seulement les chemins `ImportFrom.module` et `Import.alias.name`
avec le mapping ancien → nouveau, à tous les niveaux. Les imports locaux
de ChecklistService sont donc vérifiés aussi. Les noms importés, alias,
classes, fonctions, décorateurs, corps, constantes et docstrings restent égaux.
**76 définitions top-level** sont conservées.

Le test de cutover scanne les imports Python, y compris relatifs, dans app/tests.
Il vérifie l'absence des anciennes sources. Les chaînes de modules retirés
servent intentionnellement de références dans le test : ce ne sont pas des imports.

## 8. Tests et résultats réellement observés

| Nouveaux cas | Nombre | Preuve |
|---|---:|---|
| Layout/cutover | 1 | 22 anciennes sources absentes ; init purs ; AST imports |
| Entrées registre/router | 2 | Imports explicites des feuilles terrain |
| Pureté des packages | 6 | Pas d'API, engine, SQL ou modèles chargés implicitement |
| Identité ORM dans deux ordres | 2 | Classes/Base uniques et relations bidirectionnelles |
| Composition des cinq routers | 1 | Une occurrence par path/méthode/endpoint effectif |
| Schémas actuels | 1 | Null explicite, textes conservés, limites Review |
| Photo réelle | 1 | Original exact, miniature et détail HTTP |
| Parcours complet | 1 | Checklist/matériel, complete HTTP, PDF et avis sans JWT |

Le [module de tests](../../../backend/tests/test_interventions_module.py#L34)
compte **15 scénarios**, avec fixture SQLite isolée, clés étrangères actives
et utilisateurs/JWT réels. Sa variable de variante PostgreSQL est neutralisée.
Le cycle complet prépare via HTTP, utilise les services checklist/matériel
sur la vraie base, puis clôture et télécharge le PDF via HTTP ; avis GET/POST
sans Authorization. Il ne simule ni Review ni ReportExporter.
Il vérifie le type `application/pdf` et la signature `%PDF`, sans prétendre
comparer les métadonnées binaires d'un ancien PDF.

Le test de composition suit la règle existante du bootstrap FastAPI :
itérateur de contextes effectifs si disponible, fallback aux APIRoutes.
Les inclusions différées de FastAPI 0.138 ne sont pas prises pour des routes absentes.

| Vérification finale | Résultat |
|---|---|
| Douze fichiers ciblés | **154 passed**, 7 warnings, 36,42 s |
| Suite SQLite entière | **353 passed**, 7 warnings, 58,90 s |
| Groupes canoniques PostgreSQL exécutés ensemble | **95 passed**, 1 warning, 30,88 s : 56 + 39 |
| Alembic upgrade → downgrade -1 → upgrade | Réussite, head `f102e0010001` |
| Alembic check | 255 attendu ; seule FK technicien historique |
| OpenAPI/metadata | Octet pour octet comme R0 : 46 paths, 63 opérations, 17 tables |
| Runtime uvicorn | `/docs` et `/openapi.json` 200 ; startup/shutdown complets |
| AST | 22 modules identiques après seuls chemins d'import substitués |

**353 = 338 R6 + 15 nouveaux cas R7.** Un premier run ciblé sans le nouveau
fichier comptait 139 succès (44,46 s). Le worker a été intégré avant la suite
globale de ce premier run, déjà à 353 (67,41 s) ; cette sortie n'est donc pas
annoncée comme une suite « sans nouveaux tests ». La sélection finale stabilisée
est celle du tableau et du manifeste.

### Commandes et isolation

```text
python -m pytest <12 fichiers ciblés absolus> -q -p no:cacheprovider
python -m pytest <backend/tests absolu> -q -p no:cacheprovider
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic check
python -m pytest <5 fichiers PostgreSQL canoniques> -q
python -m uvicorn app.main:app --host 127.0.0.1 --port <port libre>
git diff --check
```

Les chemins exacts des sélections sont dans le manifeste. Le runner PostgreSQL
ne sélectionne ni les nouveaux cas terrain SQLite-only ni `test_sale_migration.py`
(son cas utilise SQLite en mémoire). Le groupe 56 + 39 n'est donc pas brouillé
par une sélection élargie comme lors de R6.

Python 3.12.0 provient de l'interpréteur préexistant
`/home/lob/workspace/python/fastapi/Tervo/backend/.venv/bin/python`.
PYTHONPATH pointe le backend **du worktree attaché**, pas les sources du
checkout principal. Cwd, SQLite et uploads sont temporaires ; les variables
TERVO_* du participant sont retirées pour les runs SQLite.

Le scout PostgreSQL utilise l'image locale `postgres:17.4`, `--pull never`,
un conteneur jetable à port éphémère loopback, sans volume nommé ; cleanup
confirmé. Les tests utilisent leurs schémas temporaires. Le scout n'a exécuté
aucun parcours HTTP terrain PostgreSQL : **cette validation n'est pas revendiquée**.
Les données/domaines d'import et les scénarios Installation/vente sont les
groupes PostgreSQL effectivement rejoués.

Les opérations Alembic restent remove_fk `intervention.technician_id → user.id`
sans ondelete SQL historique (`job_technician_id_fkey`), puis add_fk avec
`SET NULL` côté ORM. Aucun nouvel écart ni migration générée.
Les snapshots R0 sont référencés plutôt que dupliqués. Leur JSON UTF-8 trié,
indenté et terminé par newline est comparé octet pour octet.

Le runtime HTTP compare aussi `/openapi.json` au snapshot. SIGTERM puis attente
du serveur donne `-15` avec shutdown complet, pas un process oublié.
Le runtime de docs n'est pas présenté comme une requête métier PostgreSQL.

### Revue indépendante

La revue contre `90346f5` confirme **22/22 AST égaux**, imports locaux inclus,
et les adaptations des consommateurs. Elle ne relève aucun finding restant.
Elle a rejoué module terrain et bootstrap : **29 passed, 3 warnings, 18,46 s**,
sans répéter la suite globale ni PostgreSQL. Ces vérifications ne s'additionnent
pas aux comptes de tests du tableau.

## 9. Suivi, chemins à reprendre et limites

Les todos backend/frontend ont été relus. Les références terrain des todos
déjà réalisés sont actualisées, sans rouvrir leur réalisation.
TD-B013 (rôles), TD-B016 (volume représentatif), TD-F007 (interfaces V2) restent
ouverts : un changement de package ne livre pas ces fonctionnalités.

**TD-B018** trace la reprise documentaire du sprint 7.4, à effectuer dans une
mise à jour autorisée distincte avant ses features :

| Feature future | Source existante à reprendre |
|---|---|
| INT-104 checklist | `models/checklist_item.py`, `services/checklist.py`, `api/checklist.py` |
| INT-105 photos/matériel | `models/intervention_photo.py`, `models/material.py` et services/APIs locaux |
| INT-106 résultat/clôture | `models/intervention.py`, `services/intervention.py`, `schemas/intervention.py` |
| INT-107 rapport | Renderer/template encore legacy en R7 ; réévaluer chemins après R8 |
| INT-108 avis | `models/review.py`, `schemas/review.py`, `services/review.py`, `api/reviews.py` |

Les chemins non préfixés dans ce tableau sont relatifs à
`backend/app/modules/interventions/`. Le planning de features 7.4 et ses cas
non exécutés ne sont pas modifiés/cochés dans R7. Un point d'entrée technique
pour le prochain développeur ne vaut pas livraison des nouveaux modèles.

Limites explicites :

- commit R7 autorisé après acceptation ; feu vert distinct R8 reçu ;
- aucun push, CI distante, déploiement, build frontend ou E2E navigateur ;
- nouveaux cas terrain SQLite-only ; pas de suite terrain HTTP PostgreSQL ni
  campagne de concurrence terrain ;
- propriétaires de commit historiques préservés, pas d'atomicité globale
  Intervention/checklist/Review ou SQL/filesystem nouvellement garantie ;
- pas de migration, seed, backfill, déplacement des uploads existants ou
  correction de la FK technicien ;
- renderer/template reports non déplacés avant R8 ; dashboard non extrait avant R10 ;
- comparaison complète des journaux d'import avant/après réservée à R9.

### Acceptation et vérification avant commit

L'utilisateur a demandé « commit R7 & passe R8 ». Les 52 empreintes sources/tests
du manifeste R7 sont conformes. Bootstrap, module terrain et `test_api.py` ont été
rejoués sur SQLite/uploads temporaires, avec l'interpréteur et PYTHONPATH décrits
plus haut : **57 passed, 4 warnings, 20,55 s**. Ce contrôle ne prétend pas répéter
PostgreSQL. Le commit regroupe livraison, tests, notes et suivi R7, sans
implémentation R8 ni écriture directe du checkout principal.

Le commit `7a52d03` a ensuite été créé dans le worktree attaché. Les mentions
de renderer/template encore legacy décrivent la capture R7 ; depuis R8,
`ReportExporter` et son template sont dans `app/modules/reports/`, sans
changement métier ni versionnement.
