# Bilan du chantier R0–R11 — monolithe modulaire Tervo

**R0–R10 acceptés et committés ; R11 vérifié localement, commit autorisé par
l'utilisateur après contrôle final.** Capture préparée avant commit.
Aucun push, déploiement ou CI distante revendiqué.
Le bilan décrit la structure et les preuves, pas une livraison de Tervo V2 entier.

## Structure finale

```text
backend/app/
├── core/             # Base, DB, primitives JWT/hash techniques
├── config.py
├── model_registry.py # 17 classes ORM, chargement explicite hors API
├── router.py         # composition explicite des quinze routers
├── main.py           # FastAPI/lifespan/static uploads
├── seed.py           # démonstration existante, usage sûr restant à cadrer
└── modules/
    ├── customers/
    ├── catalog/
    ├── sales/
    ├── equipment/
    ├── installations/
    ├── interventions/
    ├── reports/
    ├── imports/      # pipeline, planner, service et journal
    ├── identity/
    └── dashboard/    # lectures transverses, pas de nouveau modèle
```

Les sept racines horizontales legacy sont absentes. Une Base, un registre,
une application, une base et les mêmes transactions : pas de microservices,
bus, CQRS ou couches vides ajoutées pour faire ressembler tous les domaines.

## Vagues et traçabilité

| Vague | Résultat | Référence |
|---|---|---|
| R0 | Baseline avant déplacement : 271 SQLite, PostgreSQL 56 + 39 | [R0](../extras/refactor-monolithe-modulaire/R0-baseline.md) |
| R1 | Socle/Base/registre/composition | [INT-113](INT-113-R1-socle-modulaire.md) |
| R2 | Client/Site | [INT-114](INT-114-R2-customers.md) |
| R3 | Catalogue | [INT-115](INT-115-R3-catalogue.md) |
| R4 | Vente/lignes, sans repository artificiel | [INT-116](INT-116-R4-sales.md) |
| R5 | Équipements physiques | [INT-117](INT-117-R5-equipment.md) |
| R6 | Installations autonomes/commerciales | [INT-118](INT-118-R6-installations.md) |
| R7 | Terrain existant, pas les nouvelles features 7.4 | [INT-119](INT-119-R7-interventions.md) |
| R8 | Rapports/template/PDF existants | [INT-120](INT-120-R8-reports.md) |
| R9 | Pipeline/imports et oracle avant/après | [INT-121](INT-121-R9-imports.md) |
| R10 | Identity/dashboard/seed/composition ; commit `2f9e0c3` | [INT-122](INT-122-R10-identity-dashboard.md) |
| R11 | Retrait des cinq dernières façades et contrôle global | [INT-123](INT-123-R11-retrait-legacy.md), [preuve](R11-validation.json) |

Les captures historiques R0–R10 restent intactes, y compris leurs états
« acceptation/commit à venir » à la date de capture. Les décisions ultérieures
figurent dans le planning courant ; elles ne réécrivent pas les anciennes preuves.

## Ce qui est effectivement démontré au point R11

| Contrôle | Résultat final |
|---|---|
| Suite backend SQLite finale précommit | **390 passed**, 7 warnings, 95,49 s |
| PostgreSQL canonique | **95 passed**, 1 warning, 50,08 s |
| Migration complète / dernier downgrade / re-upgrade | Succès, head `f102e0010001` |
| Écart schéma/ORM | Seulement FK technicien historique ; check retourne 255 |
| Metadata | Identique octet pour octet à R0 ; 17 tables/mappers |
| OpenAPI | Contenu égal à R0 ; 46 chemins, 63 opérations |
| Documentation/runtime | HTTP 200, startup/shutdown réels, serveur arrêté |
| Oracle R9 | Payload complet de 560 268 octets égal, SHA/provenance conservés |
| Références legacy | AST + recherche + subprocess, aucune référence exécutable |
| Frontend CI local | Bun 1.2.20 frozen/typecheck/build réussis sur copie |
| Smoke navigateur | Preuve parent transmise après retrait des façades, non rejouée ici |

Le différentiel de 271 à 390 tests ne mesure pas la valeur métier livrée :
ces ajouts couvrent surtout isolation, identité, contrats et comportements
existants. Une suite complète verte n'efface ni un warning préexistant ni
l'écart SQL accepté. Les nouvelles vérifications de domaine sur SQLite ne
sont pas toutes revendiquées PostgreSQL.

## Périmètre produit et limites

Le backend conserve les règles physiques/commerciales et le pipeline Excel
transactionnel, sa reprise, ses erreurs et ses décisions pending. Le frontend
est inchangé depuis R0 : il ne comporte pas de parcours vente/installation/import.
Ces fonctionnalités sont vérifiées par API, pas par des écrans imaginaires.

Le smoke fourni couvre login/dashboard, client/détail/site readonly, aperçu et
téléchargement PDF, puis avis public sans login. Il ne prouve pas tous les
écrans ni tous les parcours possibles. Scripts de l'ancien scratch indisponibles ;
la provenance de cette preuve est explicite dans la note R11.

L'incident antérieur `pip install --user` hors venv est documenté dans
[la note R11](INT-123-R11-retrait-legacy.md#8-incident-environnement--traçabilité-et-absence-de-réparation-cachée).
Aucune réparation/désinstallation de cet environnement n'a été tentée.

Restent ouverts **TD-B013** (rôles), **TD-B016** (volume représentatif),
**TD-B018** (reprise docs 7.4 séparément autorisée), **TD-B019** (seed destructif),
**TD-F007** (UI V2). Le refactor n'implémente pas INT-104 à INT-112 et ne
modifie pas leurs validations historiques.

## Décision attendue

L'utilisateur a autorisé le commit R11 si le travail est terminé. Le contrôle
final et le commit portent seulement cette tâche. R11 termine le chantier ;
la suite recommandée est TD-B018 avant les features terrain.
Les travaux suivants restent dans leur scope et leur feu vert propres.
