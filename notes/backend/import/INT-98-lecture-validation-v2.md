# INT-98 — Lire et valider les archives sans écrire en base

## Pourquoi cette tâche dépasse un renommage

INT-71 avait défini les interfaces du pipeline, mais la lecture, le mapping, la normalisation et la validation levaient encore NotImplementedError. INT-98 les implémente sur les fichiers fictifs fournis. La DAT et INT-98–101 ont d’abord été actualisés avec les décisions validées. Le matching, les transactions et l’API restent dans les tâches suivantes.

## Lecture et provenance

ExcelReader lit `.xlsx` avec openpyxl en lecture seule et `.csv` avec le module csv ; pandas sert de conteneur tabulaire. `sheets()` liste les onglets. UTF-8 est essayé avant Latin-1 ; l’encodage et le séparateur peuvent être imposés. Le choix détecté est affiché, car un décodage Latin-1 réussi n’est pas une preuve de l’encodage réel.

Les trente premières lignes servent à repérer l’en-tête à partir des alias connus. En cas d’égalité ou de reconnaissance insuffisante, l’administrateur doit fournir header_row. Des en-têtes vides/dupliqués et des valeurs sans en-tête sont refusés pour ne pas perdre de colonnes.

Les numéros de lignes sont physiques : titre, en-tête et lignes vides comptent. Pour un enregistrement CSV multiligne, la première ligne physique est conservée. Les attrs du DataFrame contiennent fichier, feuille, namespace, en-tête et coordonnées des lignes. Les formules sont conservées puis signalées ; aucune exécution ni utilisation silencieuse d’un cache Excel périmé.

## Mapping prudent

ImportKind distingue clients, sites, equipment, interventions, products et mixed. Les alias sont normalisés pour les accents, séparateurs et majuscules. `Type` signifie catégorie de produit dans une feuille équipements, type d’intervention dans une feuille interventions ; en mode mixed, ce titre ambigu reste non mappé.

Pas de rapprochement approximatif des en-têtes dans cette première version : les alias connus et le mapping manuel contrôlé couvrent les formats observés. Deux colonnes visant le même champ exigent un choix explicite. Les colonnes inconnues restent dans les valeurs originales et remontent en revue.

## Normalisation et validation

Les noms prennent une forme de comparaison sans accents ; les adresses conservent leurs accents. Nom et prénom sont assemblés, avec conservation des deux valeurs sources. Le numéro de série conserve sa ponctuation. Les dates explicites deviennent ISO ; une année sur deux chiffres demande un siècle configuré, sans supposer 1924 ou 2024.

Les téléphones français sont nettoyés et +33/0033 ramenés au format national. Un numéro numérique ayant perdu son zéro initial est signalé, pas réparé par supposition. Les valeurs manquantes restent absentes.

Chaque record contient `source`, `original`, `normalized`, `proposals`, `anomalies` et `disposition`. `candidate` signifie uniquement que la validation structurelle ne bloque plus : le rapprochement reste nécessaire. `pending` signale une erreur ou une décision à obtenir. Les avertissements restent visibles sans gonfler le nombre de lignes bloquées.

### Téléphone absent

- Nouveau client : MISSING_PHONE bloque la création ; MISSING_ADDRESS est distinct.
- Client déjà identifié avec certitude : avertissement, association proposée et conservation du téléphone existant.

`confirmed_existing_clients` est une entrée interne pour le futur matcher, jamais un drapeau fourni par un fichier ou librement accepté par l’API. Le validator ne consulte pas la base et ne prouve pas lui-même cette identité. Les valeurs null de normalized ne sont pas un ordre d’effacer les champs existants.

### Cas du pack

C001/C005 déclenche une revue grâce à l’indication source « doublon » ; INT-99 couvrira la comparaison réelle. C006 produit téléphone et adresse manquants. E003 garde sa série absente avec avertissement. E004/E005 demandent confirmation du remplacement. Les références produits absentes proposent product_id=NULL et conservent marque/modèle sources.

INT-2023-010 accepte l’absence de référence équipement ; la résolution du site arrive ensuite. INT-2022-999 signale la date impossible et l’absence de site ; C999 reste une référence à résoudre, sans simuler une interrogation de la base. Type, résultat, technicien et référence documentaire sont préservés et attendent un mapping historique validé.

## Utilisation sans base

```python
from app.importers import ExcelReader, FormatDetector, ImportKind, Validator

reader = ExcelReader()
frame = reader.read("archives.xlsx", sheet="Clients", source_namespace="archives-dg")
mapping = FormatDetector().detect(list(frame.columns), ImportKind.CLIENTS)
preview = reader.preview(frame).to_dict()
validation = Validator().validate(frame, mapping, ImportKind.CLIENTS).to_dict()
```

## Vérifications et limites

```bash
cd backend
uv run pytest tests/test_importers_structure.py tests/test_importers_v2.py -q
uv run pytest tests/ -q
```

Résultat : **162 tests backend réussis**, dont **38 tests structure/import v2**.

Les tests utilisent des copies autonomes du pack dans tests/fixtures/excel et créent les variantes dans un répertoire temporaire. Ils couvrent cinq entités, trois formats Excel, Latin-1, en-têtes décalés, lignes physiques, valeurs brutes, formules, dates, garanties, doublons signalés et absence de téléphone.

`.xls`, OCR, PDF et écriture métier ne sont pas implémentés. Les fichiers sont chargés en mémoire ; les transactions de 500 lignes prévues ne constituent pas encore une lecture en flux. Aucun volume réel n’a été évalué.

## Suivi

[TD-B015](../../../docs/todos/backend.md#td-b015--consommer-les-candidats-et-arbitrages-int-98) centralise les raccordements INT-99–101. Les autres todos ont été relus : aucune dépendance antérieure n’est débloquée par la seule lecture/validation.
