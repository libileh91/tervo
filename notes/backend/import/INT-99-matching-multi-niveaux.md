# INT-99 — Rapprochement hiérarchique

Le matcher est pur : ni SQL ni écriture. Il reçoit les valeurs normalisées, les candidats du référentiel, le parent déjà résolu et les correspondances source connues.

## Ordre des preuves

Une clé `(namespace, nature, référence historique)` fiable prime sur la similarité. Une cible absente, un parent différent ou des informations contradictoires imposent une revue. Une note source signalant un doublon impose aussi une revue, même à 100.

Sans référence connue, rapidfuzz.token_sort_ratio compare noms et adresses. Les téléphones, numéros de série et références sont comparés exactement. Les seuils restent 95 (automatique), 80 (revue), puis nouveau candidat sous 80. Les poids ne prennent en compte que les champs renseignés ; cela ne transforme pas un nom seul en preuve d’identité.

L’automatique exige des indices concordants : nom et téléphone pour un client, adresse et localisation pour un site, série pour un équipement. Plusieurs candidats plausibles empêchent le choix arbitraire du premier. Un numéro de série différent représente une autre instance, même avec le même produit.

## Hiérarchie et interventions

Site est recherché uniquement dans son client, Equipment dans son site. Un parent non résolu bloque le rapprochement. Les interventions d’un même site et jour sont des candidates à examiner, jamais des doublons automatiques sur leur description seule. Deux visites à des dates différentes (diagnostic puis réparation) restent distinctes.

Le résultat expose zone, score, cible éventuelle, candidats, justification et type de preuve. ClientMatcher conserve son contrat public pour les tests et appelants historiques ; MultiLevelMatcher porte les cinq natures v2.

## Validation

`uv run pytest tests/test_matching_v2.py tests/test_importers_structure.py -q`

Tests : exact/proche/distinct, absence de téléphone, doublon explicite C001/C005, homonymes, namespace, parent erroné, conflits de références, numéros de série et diagnostic/réparation. L’arrondi flottant du score exact est plafonné à 100.

## Suite

TD-B015 : le calcul des correspondances est réalisé ; INT-100 persiste les références et INT-101 recueille les décisions humaines. Un résultat « nouveau » n’autorise pas à ignorer les erreurs de validation INT-98.
