# INT-98 — Du fichier Excel à une ligne vérifiable

> **Chemins actualisés par R9 / INT-121 :** le pipeline est dans `app/modules/imports/pipeline/`. Les résultats de cette note restent ceux de la livraison INT-98 ; la [note R9](../refactor-monolithe-modulaire/INT-121-R9-imports.md#L1) documente la comparaison fonctionnelle avant/après, sans nouveau déploiement.

Cette tâche implémente la lecture, le mapping, la normalisation et la validation. Les extraits ci-dessous viennent du code du projet ; les exemples d’utilisation sont indiqués séparément.

| Fichier | Ce qui a été implémenté |
| --- | --- |
| [excel_reader.py](../../../backend/app/modules/imports/pipeline/excel_reader.py#L36) | Lecture XLSX/CSV et coordonnées des lignes |
| [format_detector.py](../../../backend/app/modules/imports/pipeline/format_detector.py#L114) | Colonne source → champ interne, selon la nature de la feuille |
| [normalizer.py](../../../backend/app/modules/imports/pipeline/normalizer.py#L9) | Téléphones, noms, dates, numéros de série |
| [validators.py](../../../backend/app/modules/imports/pipeline/validators.py#L123) | Anomalies et propositions par ligne |

```text
fichier → DataFrame + provenance → mapping → valeurs normalisées + anomalies
```

Aucune entité métier n’est écrite à cette étape.

## 1. Lire sans perdre la position dans le fichier

Extrait réel de [excel_reader.py](../../../backend/app/modules/imports/pipeline/excel_reader.py#L128), à partir de la ligne 128 :

```python
frame = pd.DataFrame(data, columns=columns, dtype=object)
source['header_row'] = physical[index]
frame.attrs.update(source=source, source_rows=numbers)
return frame
```

`dtype=object` évite une conversion globale imposée par pandas. `source_rows` conserve le numéro physique : une ligne vide ou un titre ne décale pas la référence affichée à l’administrateur. `attrs` transporte les métadonnées à côté du tableau.

Pour XLSX, `openpyxl` utilise `read_only=True, data_only=False` : les formules restent visibles. Pour CSV, UTF-8 est essayé avant Latin-1 ; le choix reste explicite dans la provenance. L’en-tête est recherché dans les trente premières lignes ; une ambiguïté exige `header_row`.

## 2. Voir le mapping obtenu

Exemple exécutable depuis `backend/` :

```python
from app.importers.format_detector import FormatDetector, ImportKind

mapping = FormatDetector().detect(
    ["Nom", "Telephone", "Adresse_facturation"],
    ImportKind.CLIENTS,
)
assert mapping.fields["phone"] == "Telephone"
assert mapping.fields["address"] == "Adresse_facturation"
```

Le dictionnaire va du **champ interne vers la colonne source**. Le mot `Type` dépend de la nature choisie : catégorie pour un produit, type pour une intervention. Un mapping ambigu ne doit pas devenir une supposition silencieuse.

## 3. Normaliser un téléphone sans inventer un chiffre

Extrait réel de [normalizer.py](../../../backend/app/modules/imports/pipeline/normalizer.py#L30), à partir de la ligne 30 :

```python
def phone(value: object) -> str:
    raw = Normalizer.text(value)
    if not raw:
        return ""
    phone = re.sub(r"[\s.()\-]", "", raw)
    # Never silently strip letters or reconstruct a lost leading zero.
    if not re.fullmatch(r"\+?\d+", phone):
        raise ValueError("Téléphone invalide")
    for prefix in Normalizer.COUNTRY_PREFIXES:
        if phone.startswith(prefix) and len(phone[len(prefix):]) == 9:
            phone = "0" + phone[len(prefix):]
            break
    if not re.fullmatch(r"0\d{9}|\+[1-9]\d{7,14}", phone):
        raise ValueError("Téléphone incomplet ou format non reconnu")
    return phone
```

La première expression régulière retire les séparateurs usuels. La suivante refuse les lettres. La conversion `+33 → 0` n’est appliquée que si neuf chiffres suivent le préfixe.

Exemples exécutables :

```python
from app.importers.normalizer import Normalizer as N

assert N.phone("+33 6 12 34 56 78") == "0612345678"
assert N.phone(None) == ""
assert N.date("15/09/24", two_digit_year_base=2000) == "2024-09-15"
# N.phone(612345678) lève ValueError : le zéro perdu n’est pas reconstruit.
# N.date("15/09/24") lève ValueError : le siècle doit être confirmé.
```

Les noms sont normalisés sans accents pour la comparaison ; les adresses gardent leurs accents et les séries leur ponctuation. Les valeurs originales sont conservées à part.

## 4. Une ligne produit un résultat, même si elle est invalide

Extrait réel de [validators.py](../../../backend/app/modules/imports/pipeline/validators.py#L269), à partir de la ligne 269 :

```python
blocking = any(e.severity != 'warning' for e in issues)
result.records.append(dict(source={**source, 'row':number}, original=original,
    normalized=values, proposals=proposals, disposition='pending' if blocking else 'candidate',
    anomalies=[e.to_dict() for e in issues]))
```

| Clé | Ce qu’elle permet de comprendre |
| --- | --- |
| `source` | Fichier, feuille, namespace et ligne physique |
| `original` | Valeurs réellement lues, avant modification |
| `normalized` | Valeurs nettoyées, sans effacer l’original |
| `proposals` | Nom de site, titre ou autre décision à confirmer |
| `anomalies` | Code, gravité, colonne et valeur concernées |
| `disposition` | `pending` si bloquée ; sinon `candidate` pour la suite du pipeline |

`candidate` ne veut pas dire « insérer maintenant » : INT-99 recherche encore les doublons.

## 5. Le cas demandé : téléphone absent

Exemple exécutable, sans base de données :

```python
import pandas as pd
from app.importers.format_detector import FormatDetector, ImportKind
from app.importers.validators import Validator

frame = pd.DataFrame([{"Nom": "Luc Bernard", "Telephone": "", "Adresse_facturation": "Paris"}])
mapping = FormatDetector().detect(list(frame.columns), ImportKind.CLIENTS)
record = Validator().validate(frame, mapping, ImportKind.CLIENTS).records[0]

assert record["disposition"] == "pending"
assert record["original"]["Telephone"] == ""
assert any(a["code"] == "MISSING_PHONE" for a in record["anomalies"])
```

Une création est bloquée. Si INT-99/100 prouve l’association à un client existant, l’anomalie devient un avertissement et son téléphone reste intact. `confirmed_existing_clients` est une entrée interne du validator, jamais une preuve fournie librement par le fichier.

## 6. Ce que vérifient les tests

```bash
cd backend
uv run pytest tests/test_importers_structure.py tests/test_importers_v2.py -q
```

Le [pack fictif](../../../backend/tests/fixtures/excel/README.md) couvre notamment : C006 sans téléphone/adresse, E003 sans série, E004/E005 à arbitrer, date impossible, Latin-1, en-têtes décalés, lignes physiques, formules et colonnes inconnues.

Limites : lecture en mémoire, pas de XLS/OCR/PDF. La mesure sur volume réel reste dans [TD-B016](../../../docs/todos/backend.md#td-b016--mesurer-limport-sur-un-volume-représentatif). Le raccordement au matching, à la persistance et à l’API (TD-B015) est désormais terminé.

## Voir comment les étapes sont assemblées

Extrait du fichier [ingestion.py](../../../backend/app/modules/imports/pipeline/ingestion.py#L9-L37), lignes 9 à 37 :

```python
def read_sources(content: bytes, filename: str, namespace: str, selections: list[dict]):
    if not selections:
        raise ValueError('Sélectionner au moins une feuille et sa nature')
    if len(content) > 10 * 1024 * 1024:
        raise ValueError('Fichier supérieur à 10 Mio')
    if Path(filename).suffix.lower() not in {'.xlsx', '.csv'}:
        raise ValueError('Format non supporté')
    results, seen = [], set()
    with TemporaryDirectory(prefix='tervo-import-') as folder:
        path = Path(folder) / ('source' + Path(filename).suffix.lower())
        path.write_bytes(content)
        for selection in selections:
            kind = ImportKind(selection['kind'])
            if kind == ImportKind.MIXED:
                raise ValueError('Choisir une nature explicite par sélection')
            options = {k:selection[k] for k in ('sheet','header_row','encoding','separator') if k in selection}
            frame = ExcelReader().read(path, source_namespace=namespace, **options)
            frame.attrs['source']['file'] = filename
            if path.suffix == '.csv':
                frame.attrs['source']['sheet'] = Path(filename).stem
            mapping = FormatDetector().detect(list(frame.columns), kind, selection.get('mapping'))
            validated = Validator().validate(frame, mapping, kind, two_digit_year_base=selection.get('two_digit_year_base'))
            for record in validated.records:
                key = f"{record['source']['sheet']}:{record['source']['row']}:{kind.value}"
                if key in seen:
                    raise ValueError('Sélection de ligne dupliquée')
                seen.add(key)
                results.append(dict(key=key, kind=kind.value, mapping=mapping.to_dict(), **record))
    return results
```

Cette fonction raccorde les composants détaillés plus haut. Elle reçoit les octets et un manifeste de sélections, pas une session SQL.

Le nom du fichier temporaire est reconstruit à partir de l’extension ; le nom source est conservé dans les métadonnées pour la provenance. Le bloc `TemporaryDirectory` nettoie cette copie à sa sortie. Le fichier fourni par l’utilisateur n’est pas réécrit.

Pour chaque sélection, `ExcelReader` lit une feuille, `FormatDetector` produit le mapping et `Validator` retourne les enregistrements enrichis de leurs anomalies. Une ligne invalide peut donc rester dans `results` : elle doit être visible pour correction, pas disparaître du rapport.

La clé `feuille:ligne:nature` identifie une ligne dans ce fichier. Le set `seen` refuse deux sélections qui capturent la même ligne avec la même nature. Il ne détecte pas les doublons métier entre deux fichiers : cette responsabilité appartient au matching et au journal d’import.

Le retour est une liste de dictionnaires qui conserve mapping, valeurs et coordonnées sources. Le service INT-100 peut ensuite préparer un plan sans dépendre du fichier temporaire.
