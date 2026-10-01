# Chantier technique — Refactor monolithe modulaire

> **Stage 7 · chantier transverse avant 7.4, hors sprints fonctionnels**
> **Branche :** `refactor/modular-monolith` (déjà créée).
> **Décision utilisateur :** R0 à R4 validés et committés ; R4 : `93be411`. R5 accepté, commit autorisé ; feu vert distinct R6 reçu. R7 à R11 restent non commencées et nécessitent chacune un feu vert distinct.

## Références et suivi

- [Plan de refactorisation](../../../../notes/backend/extras/tervo_plan_refactor_monolithe_modulaire.md) : périmètre et ordre des vagues.
- [Preuve R0](../../../../notes/backend/extras/refactor-monolithe-modulaire/R0-baseline.md) et [manifeste R0](../../../../notes/backend/extras/refactor-monolithe-modulaire/R0-baseline.json) : résultats réellement observés avant déplacement.
- [Tâches](tasks.md) : user stories, critères d'acceptation et notes techniques.
- [Cas de test](test-cases.json) : scénarios à exécuter, résultats attendus explicites et rattachement aux tâches.
- [Stage 7](../README.md) · [DAT unique](../../../DAT/new/00-sommaire.md).

Les mentions « validation/branche encore attendues » dans le manifeste JSON R0 décrivent sa date de capture. **Le présent planning et la note R0 enregistrent la décision ultérieure : R0 validé, branche créée, feu vert R1 donné et écart FK technicien conservé sans correction.** Les captures JSON historiques restent intactes.

R0 et R1 sont committés localement : `6754a50` et `73e5ac9`. [Note et preuves INT-113](../../../../notes/backend/refactor-monolithe-modulaire/INT-113-R1-socle-modulaire.md).

R2 est accepté par l'utilisateur et committé localement sous `ed67168` : [note pédagogique et preuves INT-114](../../../../notes/backend/refactor-monolithe-modulaire/INT-114-R2-customers.md). Les captures R2 restent inchangées.

R3 est accepté et committé sous `29f034e` : [note pédagogique et preuve INT-115](../../../../notes/backend/refactor-monolithe-modulaire/INT-115-R3-catalogue.md). Sa capture après naming conserve **128 tests ciblés**, **299 tests SQLite**, groupes PostgreSQL **56 + 39**, OpenAPI/metadata identiques à R0/R1/R2. `app/modules` et `catalog` sont conservés ; cette capture précède le feu vert distinct R4 et n'est pas réécrite.

R4 est accepté et committé directement dans le checkout principal sous `93be411`, puis reporté par fast-forward dans le worktree agent. Sa [note et preuve INT-116](../../../../notes/backend/refactor-monolithe-modulaire/INT-116-R4-sales.md) conserve la capture de validation initiale, sans réécriture des JSON.

R5 est implémenté et vérifié sur le checkout principal : [note et preuve INT-117](../../../../notes/backend/refactor-monolithe-modulaire/INT-117-R5-equipment.md), **155 ciblés**, **324 SQLite**, groupes PostgreSQL **56 + 39**, contrats/schéma inchangés et revue sans finding. Clôture acceptée ; avant commit, 23 empreintes conformes et 76 tests ciblés rejoués. R6 a reçu son propre feu vert.

## Ordre et attribution

R0 reste un checkpoint sans nouvel identifiant INT. Les identifiants INT-113 à INT-123 sont réservés à ce chantier ; ils ne renumérotent ni ne remplacent INT-94 à INT-112 dans les sprints de features.

| Vague | Tâche | Périmètre | Statut / autorisation |
|---|---|---|---|
| R0 | Checkpoint | Baseline et preuves | Validé ; branche créée |
| R1 | [INT-113](tasks.md#int-113--r1--créer-le-squelette-modulaire) | Squelette, Base pure, registre et composition | Validé par l'utilisateur ; commit local `73e5ac9` |
| R2 | [INT-114](tasks.md#int-114--r2--déplacer-customers) | Client + Site | Validé par l'utilisateur ; commit local `ed67168` |
| R3 | [INT-115](tasks.md#int-115--r3--déplacer-catalog) | Product | Validé par l'utilisateur ; commit `29f034e` |
| R4 | [INT-116](tasks.md#int-116--r4--déplacer-sales) | Sale + SaleLine | Validé par l'utilisateur ; commit `93be411` |
| R5 | [INT-117](tasks.md#int-117--r5--déplacer-equipment) | Équipement physique | Validé par l'utilisateur ; commit autorisé |
| R6 | [INT-118](tasks.md#int-118--r6--déplacer-installations) | Installation autonome et commerciale | Autorisé ; à démarrer après commit R5 |
| R7 | [INT-119](tasks.md#int-119--r7--déplacer-interventions) | Terrain existant, sans features 7.4 | Non commencé ; feu vert distinct requis après R6 |
| R8 | [INT-120](tasks.md#int-120--r8--déplacer-reports) | Rapport/PDF/template existants | Non commencé ; feu vert distinct requis après R7 |
| R9 | [INT-121](tasks.md#int-121--r9--déplacer-imports) | Pipeline Excel et comparaison avant/après | Non commencé ; feu vert distinct requis après R8 |
| R10 | [INT-122](tasks.md#int-122--r10--déplacer-identity-dashboard-et-finaliser-la-composition) | Auth, dashboard, seed, composition | Non commencé ; feu vert distinct requis après R9 |
| R11 | [INT-123](tasks.md#int-123--r11--retirer-les-couches-horizontales-legacy) | Nettoyage legacy et validation globale | Non commencé ; feu vert distinct requis après R10 |

**Estimations :** estimation à confirmer pour chaque tâche ; aucun nombre de points arbitraire n'est attribué.

## Invariants du chantier

- Un backend FastAPI, un processus applicatif, une base PostgreSQL et un déploiement ; pas de microservice, bus, CQRS, HTTP interne ou UnitOfWork généralisé.
- Déplacement structurel uniquement : URLs, payloads, statuts, autorisations actuelles, tables, colonnes, FK, contraintes et migrations restent inchangés.
- Base SQLAlchemy unique, définie dans un module technique pur qui ne charge ni domaines ni API. Pendant la transition, `app.models.base.Base` réexporte le **même objet**, pas une deuxième Base.
- Registre explicite complet, utilisable hors API et idempotent : **17 tables** présentes en R0, y compris checklist, photos, matériel, avis et les quatre tables d'import.
- Pas de couches artificielles : en particulier **aucun repository ajouté à `sales` pour obtenir une symétrie de dossiers**. Aucun module futur vide.
- Propriétaires des transactions, commits et `AsyncSession` partagée conservés : clôture Installation + Equipment atomique ; imports transactionnels par sous-lots avec reprise et verrouillage existants.
- Aucune migration générée pour un déplacement Python. Supprimer les anciens fichiers après cutover sans garder deux implémentations actives ; supprimer les dossiers legacy uniquement après résolution de leurs références.
- INT-104 à INT-108 restent dans 7.4 ; Report/ReportVersion, nouveaux modèles de checklist/photo/matériel et futurs rôles ne sont pas livrés ici. Showroom reste 7.5.
- Le suivi historique PostgreSQL de 7.3 n'est pas corrigé dans ce chantier documentaire.

## Référence R0 et interprétation des validations futures

Baseline source : `544a23d6cb2cbe878fbc8ddf2d962c7adf76c000`, après réécriture de l'historique. Révision Alembic : `f102e0010001`. Ne pas utiliser d'anciens SHA comme référence et ne pas réécrire l'historique sans demande explicite.

| Mesure R0 déjà exécutée | Résultat de référence |
|---|---|
| Suite backend SQLite | 271 passed ; 5 warnings |
| Groupes PostgreSQL ventes/installations/migration | 56 passed |
| Groupes PostgreSQL imports | 39 passed |
| PostgreSQL 17.4 neuf, upgrade / downgrade -1 / upgrade | Réussite |
| `alembic check` PostgreSQL | Échec préexistant : différence FK technicien uniquement |
| Démarrage / arrêt FastAPI, `/openapi.json`, `/docs` | Sans erreur ; HTTP 200 |
| OpenAPI / metadata ORM | 46 chemins, 63 opérations / 17 tables |

**Exception connue et conservée :** le schéma migré contient `job_technician_id_fkey` sur `intervention.technician_id → user.id` sans `ondelete`, alors que l'ORM déclare `ondelete="SET NULL"`. Le contrôle futur doit retrouver uniquement le couple `remove_fk` / `add_fk` connu, sans aucune nouvelle différence. Un code de retour non nul d'`alembic check` n'est donc pas une nouvelle régression à lui seul ; ne pas annoncer ce contrôle strictement vert, ne pas générer de correctif ou de migration pour le faire passer.

La chaîne Alembic complète sur SQLite neuve échoue déjà sur `ALTER TYPE` PostgreSQL. Ce défaut de portabilité n'est pas corrigé ici : utiliser PostgreSQL jetable pour la chaîne complète, SQLite isolée pour la suite applicable. Ne jamais viser les bases locales ou déployées avec des fixtures destructrices.

Les snapshots R0 restent intacts. Produire des sorties après vague distinctes puis comparer à `R0-openapi.json` et `R0-metadata.json`. Les seuls comptes de routes/tables ne suffisent pas ; comparer les contenus. Le snapshot ORM ne couvre pas tous les index, séquences, valeurs d'enums natifs ou defaults Python : contrôler aussi ces invariants sans inventer leur correction.

## Tests et clôture par vague

Le JSON reprend le format de 7.3 (`test_cases`, `id`, `task`, `title`, `type`, `preconditions`, `steps`, `expected_result`, `status`), avec un champ `wave` pour distinguer les vagues des sprints. `status: "not_run"` signifie **non exécuté** ; aucun résultat R0 n'est reporté comme réussite d'une tâche R1 à R11.

À chaque vague autorisée : tests ciblés puis suite, comparaison OpenAPI/metadata et contrôle Alembic PostgreSQL sans nouvelle diff ; conserver les preuves réelles, faire valider la clôture, puis attendre le feu vert de la suivante. Les critères R1 à R5 sont validés et acceptés. Ceux de R6 à R11 restent ouverts.

R9 doit exécuter le même pack d'import avant et après son déplacement avec des états initiaux équivalents. R0 conserve les empreintes des fixtures, **pas encore une comparaison complète des journaux et entités**. La capture fonctionnelle « avant R9 » fait donc partie d'INT-121 ; elle ne doit pas être inventée à partir des hashes.

## Notes pédagogiques futures

Les notes d'INT-113 à INT-123 seront produites dans **`notes/backend/refactor-monolithe-modulaire/`**, en reprenant exactement le nom du dossier de planning. Chaque note expliquera les changements réellement livrés, invariants, commandes et résultats observés, limites et dépendances ; pas un simple résumé ni une validation supposée.

**Exception historique :** la preuve R0 et ses artefacts restent dans `notes/backend/extras/refactor-monolithe-modulaire/`. Aucun dossier de notes futures ni aucune note d'implémentation n'est créé par ce planning.
