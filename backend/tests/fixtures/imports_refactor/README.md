# R0 — capture fonctionnelle avant INT-121

Référence sources legacy : `bb1fc14c4d8da80e9584eb1ed6de1f69cd96132e`
(R8 ; imports inchangés). Capture via les vrais `ImportService.stage`,
`validate`, `execute`, `detail`, `errors`, sans mocks.

## Recette exacte

Voir `backend/tests/test_imports_module.py` : `RECIPE` est le mapping exact.
SQLite fichier temporaire, `PRAGMA foreign_keys=ON`, toutes les tables
initialement vides, aucun client/site/produit/équipement/utilisateur préchargé.
Même namespace `r0-pack` pour les quatre fichiers, bytes originaux inchangés.
Les six hashes (y compris README et anomalies du pack) sont vérifiés contre
`notes/backend/extras/refactor-monolithe-modulaire/R0-baseline.json`.

1. Le classeur 01 sélectionne Clients, Sites et Equipements. Capture preview
   complète puis première validation sans décisions. Deuxième validation :
   uniquement les quatre sites avec adresse reçoivent `create` et
   `site_name = site_address` source. C'est une convention technique de nommage
   reproductible, pas une confirmation d'identité ou un nouveau lieu inventé.
   Les doublons, données absentes, remplacement et nouvel équipement ambigu
   restent PENDING, sans association arbitraire.
2. Le classeur 02 sélectionne les interventions. Après capture brute et
   validation initiale, seules les lignes `Resultat = RESOLVED` reçoivent
   `create`, titre copié de `Description`, statut opérationnel `COMPLETED`.
   Cette traduction historique explicite est la convention de cette recette ;
   elle ne corrige aucune référence. Elle crée quatre interventions ; celle
   liée à E005 reste orpheline. Les résultats PART_REQUIRED et UNRESOLVED ne
   sont pas assimilés arbitrairement à un statut opérationnel. Le diagnostic
   sans équipement reste donc PENDING, son équipement absent et sa validation
   étant capturés. C999/date invalide restent tracés, non ignorés.
3. Le classeur 03 est lu comme interventions, année sur deux chiffres avec
   base explicite 2000. Les trois lignes restent PENDING : pas de résolution
   humaine inventée pour les candidats fuzzy ou les statuts historiques.
4. Le CSV 04 est lu comme clients, encodage explicite latin-1, séparateur `;`.
   Ses trois associations automatiques sont exécutées et journalisées.

Chaque plan est exécuté avec lots de trois, puis **le même fichier et le même
plan sont réexécutés immédiatement** : même batch ID, détail identique, toutes
les tables inchangées hors normalisation des instants techniques.

Résultats : 01 partial (11 créations, 5 pending), 02 partial (4 créations,
4 pending), 03 partial (3 pending), 04 success (3 associations).
État final : 4 clients, 4 sites, 3 équipements historiques, **0 installation**,
4 interventions, 0 produit/utilisateur, 4 batches, 18 records, 15 références.
Les erreurs/anomalies sont capturées intégralement, aucun succès artificiel.

## Snapshot et normalisation

`before.json` est une enveloppe JSON contenant le snapshot **complet**, compressé
sans perte (LZMA + base64), et son SHA-256 canonique. Ce format évite de dupliquer
des centaines de kilo-octets de plans, previews et erreurs répétés. Le test
décompresse et compare tous les contenus, pas seulement leurs hashes.

Le contenu décodé conserve :

- les hashes du pack, mappings, décisions et état initial ;
- previews complètes, première validation, validation approuvée, exécution,
  erreurs et réexécution pour chaque fichier ;
- chaque colonne de **chaque table ORM**, ordonnée par PK, notamment
  ImportBatch/Record/Reference/Error et toutes les entités métier.

Seuls `created_at`, `updated_at`, `completed_at`, `lease_until` non nuls sont
remplacés par `<instant>` au niveau colonnes SQL, mais `completed_at` et
`lease_until` sont normalisés **uniquement dans `import_batch`**.
Les dates métier `Intervention/Installation.started_at/completed_at` restent
exactes. Un `import_batch.execution_token` non nul est remplacé par
`<lease-token>` (les tokens finaux sont nuls). Les bytes binaires sont
représentés par taille et SHA-256, les fichiers exacts restant dans le pack
hash-vérifié. Aucune normalisation récursive des JSON : dates métier, textes,
erreurs, IDs/FKs, candidats, décisions, tokens de plan et fingerprints restent
exacts. Aucun chemin temporaire n'apparaît dans le snapshot.

Décodage pour inspection, sans dépendance externe :

```python
import base64, json, lzma
from pathlib import Path

artifact = json.loads(Path("backend/tests/fixtures/imports_refactor/before.json").read_text())
snapshot = json.loads(lzma.decompress(base64.b64decode(artifact["lzma_base64"])))
print(json.dumps(snapshot, ensure_ascii=False, indent=2))
```

## Vérification avant

Python existant : `/home/lob/workspace/python/fastapi/Tervo/backend/.venv/bin/python`.
Exécution depuis un cwd temporaire avec `uploads/` temporaire, `PYTHONPATH`
pointant sur le backend attaché et variables héritées `TERVO_*` supprimées :

```sh
python -m pytest /chemin/backend/tests/test_imports_module.py -q -p no:cacheprovider
```

Le mode capture du runner est opt-in via `TERVO_CAPTURE_SCRATCH` et ne modifie
jamais le snapshot durable. Le snapshot avant doit rester figé pendant le
cutover ; seuls les chemins d'import du harness doivent changer si nécessaire.

Le test épingle aussi le commit source, le SHA-256 de l'enveloppe
`6fea24321f71239649f57be88e0270c5e704cce12a23ff1722d3aad0431d6279`
et celui du JSON décodé
`f98dd88686d7efc6446187e5507a8c49be5fe3be66453acc014b1fcbec502db2`
dans son propre code. Régénérer l'enveloppe et son hash interne ne suffit donc
pas à faire passer une comparaison altérée.

Les tables vides sont présentes comme `[]` ; leur structure complète est
vérifiée séparément par le snapshot metadata R0. Les dates de début/clôture
métier sont nulles dans ce pack : le test unitaire de normalisation les
contrôle également avec des valeurs non nulles. Un cas séparé importe une
intervention historique sans équipement ni vente/installation fictive ;
il ne modifie pas la recette ou le snapshot figé du pack.
