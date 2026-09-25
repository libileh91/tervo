# INT-100 — Import en deux passes, transactions et reprise

## Le problème résolu

Un fichier peut contenir un client, ses sites et ses équipements ; les interventions arrivent dans un autre fichier. Les identifiants Excel ne sont pas les clés primaires de Tervo. Le pipeline prépare donc un plan explicite puis conserve les correspondances historiques après chaque écriture réussie.

Les fichiers de référence sont fictifs. Les tests démontrent les mécanismes sur ce pack et sur 502 lignes synthétiques, pas la capacité à traiter vingt ans d’archives en production.

## Du fichier au plan

`app/importers/ingestion.py` conserve les octets du fichier, le choix des feuilles, l’en-tête, le mapping, les valeurs originales et les valeurs normalisées. Le fichier source n’est jamais modifié. La limite actuelle est de 10 Mio par fichier ; la lecture reste en mémoire.

`app/services/import_planner.py` travaille sur une copie du référentiel. Il ordonne les produits éventuels, clients, sites et équipements, puis les interventions. Les créations reçoivent temporairement des identifiants négatifs : un site peut ainsi désigner le client qui sera créé dans le même import. L’exécution remplace ces références par les vrais IDs PostgreSQL.

Une dépendance vers une ligne placée plus bas est réessayée lorsque le plan progresse. C’est le cas d’E004, remplacé par E005 après confirmation humaine. Une référence introuvable reste en attente et produit une anomalie ; aucun parent fictif n’est créé.

`ImportReference` mémorise `(namespace, type, référence source) → ID Tervo`. Plusieurs références historiques peuvent désigner le même client, par exemple C001/C005 après arbitrage. Une référence déjà attribuée ne peut pas être silencieusement déplacée.

## Décisions humaines

Une décision comporte une action, un motif et éventuellement des corrections ou une cible. `associate_source_id` permet de choisir une entité créée dans le même fichier, avant de connaître son ID Tervo. `review` applique les corrections puis relance le rapprochement sans autoriser une création forcée.

L’ancien export présente des adresses composées. Si elles ne permettent pas une association certaine, l’administrateur confirme d’abord le site ; il arbitre ensuite les interventions de même date proposées comme doublons. Confirmer le site ne confirme pas automatiquement le doublon.

Sans téléphone, créer un client reste interdit. Une association prouvée avec un client existant conserve `MISSING_PHONE` comme avertissement et ne modifie aucune de ses coordonnées. Les corrections sont conservées séparément des valeurs originales. Les attributs marque/modèle sans produit fiable restent dans la provenance ; aucun produit n’est inventé.

## Pourquoi un plan approuvé ?

`ImportBatch` garde le fichier, le plan et sa révision. Le jeton SHA-256 lie cette révision au fichier, au mapping et aux décisions. `execute` ne reçoit pas de nouveaux choix et ne recalcule pas le plan. Si le référentiel métier a changé, une nouvelle validation est nécessaire.

La même paire namespace/empreinte de fichier retrouve le même import. Un import réussi retourne son rapport existant. Pour un réexport différent, le rapprochement et les références historiques évitent les doublons.

## Une transaction par 500 lignes

`app/services/import_service.py` ouvre une session indépendante de la session d’authentification. Chaque sous-lot utilise `async with db.begin()` : entités métier, références source et `ImportRecord` sont commités ensemble.

Dans le test à 502 lignes, une exception arrive après une écriture du deuxième sous-lot. Résultat : 500 clients, 500 références, 500 traces ; aucune ligne du deuxième sous-lot ne subsiste. La reprise saute les 500 clés déjà enregistrées et termine les deux dernières.

Un lot annulé donne `failed` ; des lignes laissées en attente donnent `partial`. `success` signifie que toutes les lignes sont traitées, y compris les exclusions explicitement motivées. Les erreurs restent consultables même après une correction.

## Concurrence et limites

Un emplacement unique `execution_slot=1` sérialise les imports. Un bail de quinze minutes renouvelé à chaque sous-lot et un jeton d’exécution permettent la reprise après arrêt d’un processus sans autoriser un ancien processus à finaliser la nouvelle exécution. PostgreSQL verrouille la ligne d’import et les tables du référentiel pendant un sous-lot pour maintenir la cohérence entre le contrôle d’empreinte et les écritures.

Ces verrous peuvent attendre une transaction métier concurrente et retarder temporairement les écritures métier. Le référentiel entier est chargé pour le matching et l’empreinte ; ce choix conservateur doit être mesuré sur un volume représentatif avant une migration réelle. L’exécution reste synchrone ; un worker asynchrone et la lecture en flux sont des évolutions, pas des fonctionnalités livrées.

## Vérification

```bash
cd backend
uv run pytest tests/test_import_service_v2.py -q
# Sur une base PostgreSQL de test uniquement :
TERVO_IMPORT_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/TEST_DB \
  uv run pytest tests/test_import_service_v2.py -q
```

Le mode PostgreSQL crée un schéma isolé par test, puis le supprime. La migration `d100e0010001` est également vérifiée en montée, retour à `c197e0010001` et remontée sur PostgreSQL 17.4 jetable.
