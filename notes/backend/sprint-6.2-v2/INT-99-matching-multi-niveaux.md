# INT-99 — Comment le code décide d’associer ou de demander une revue

Le code principal est [MultiLevelMatcher](../../../backend/app/importers/multi_matcher.py). Il reçoit des dictionnaires et retourne un `EntityMatch` ; il ne lit ni n’écrit la base. [ClientMatcher](../../../backend/app/importers/matcher.py) conserve le contrat historique.

```text
parent résolu → référence historique → score → contrôle de cohérence → décision
```

Le score mesure une ressemblance. Le contrôle suivant décide si cette ressemblance suffit.

## 1. Comparer dans le bon parent

Extrait réel de [multi_matcher.py](../../../backend/app/importers/multi_matcher.py), à partir de la ligne 106 :

```python
parent = PARENTS.get(kind)
if parent and parent_id is None:
    return EntityMatch('human_review', reason='Parent à résoudre avant rapprochement')
pool = [e for e in existing if not parent or e.get(parent) == parent_id]
```

`PARENTS` associe `sites` à `client_id`, et `equipment`/`interventions` à `site_id`. La liste `pool` exclut donc les objets d’un autre parent avant de calculer le moindre score.

## 2. Chercher d’abord la référence historique

Extrait réel de [multi_matcher.py](../../../backend/app/importers/multi_matcher.py), à partir de la ligne 111 :

```python
key = (namespace, kind, N.text(incoming.get(SOURCE_FIELDS[kind])))
target = (references or {}).get(key) if namespace and key[2] else None
if target is not None:
    found = next((e for e in pool if e['id'] == target), None)
    if found is None:
        return EntityMatch('human_review', reason='Référence source vers une cible absente ou un autre parent')
    candidate = dict(entity_id=target, score=100.0)
    if flagged or self.conflict(kind, incoming, found):
        return EntityMatch('human_review', 100, reason='Référence source contradictoire ou revue demandée', candidates=[candidate])
    return EntityMatch('auto', 100, target, 'Référence source fiable', [candidate], 'source_reference')
```

Exemple de correspondance déjà connue :

```python
references = {("archives-dg", "clients", "C001"): 42}
# C001 est un identifiant de l’archive ; 42 est l’ID de Client dans Tervo.
```

Le namespace empêche de confondre deux systèmes utilisant tous deux `C001`. Même avec cette référence, un téléphone contradictoire ou un parent incorrect impose une revue.

## 3. Comprendre le score pondéré

Extrait réel de [multi_matcher.py](../../../backend/app/importers/multi_matcher.py), à partir de la ligne 71 :

```python
total, weights = 0.0, 0.0
for key, weight, exact in fields:
    normalize = self.phone if key == 'phone' else N.serial_number if key == 'serial_number' else N.name
    a, b = normalize(incoming.get(key)), normalize(existing.get(key))
    if not a or not b:
        continue
    similarity = (100 if a == b else 0) if exact else token_sort_ratio(a, b)
    total += weight * similarity
    weights += weight
return min(100.0, total / weights) if weights else 0.0
```

Pour un client, les poids par défaut sont **nom 0,6 ; téléphone 0,3 ; ville 0,1**. RapidFuzz compare les mots des noms/villes ; le téléphone exige une égalité exacte.

Calcul illustratif : nom à 90, téléphone identique, ville absente.

```text
(0,6 × 90 + 0,3 × 100) / (0,6 + 0,3) = 93,33 → revue humaine
```

Les champs absents sont exclus du dénominateur. C’est pourquoi un nom seul peut obtenir 100 : le contrôle d’identité qui suit est indispensable.

## 4. Un score élevé ne suffit pas

Extrait réel de [multi_matcher.py](../../../backend/app/importers/multi_matcher.py), à partir de la ligne 129 :

```python
strong = {
    'clients': bool(incoming.get('full_name') and self.phone(incoming.get('phone')) and
                    self.phone(incoming.get('phone')) == self.phone(found.get('phone'))),
    'sites': bool(incoming.get('address') and (incoming.get('city') or incoming.get('postal_code'))),
    'equipment': bool(incoming.get('serial_number') and found.get('serial_number')),
    'interventions': False,
    'products': True,
}[kind]
tied = len(scored) > 1 and scored[1][0] >= self.review_threshold
if not strong or tied or self.conflict(kind, incoming, found):
    zone, reason = 'human_review', 'Identité insuffisante, conflit ou plusieurs candidats'
else:
    return EntityMatch('auto', best, found['id'], 'Identité corroborée', candidates, 'corroborated')
```

`strong` impose les indices nécessaires à chaque nature. `tied` détecte un deuxième candidat plausible. Pour une intervention sans référence fiable, `strong` vaut toujours `False` : même date et même texte ne prouvent pas une seule visite.

| Situation | Décision |
| --- | --- |
| Score ≥ 95 + preuve suffisante + absence de conflit/ambiguïté | `auto` |
| Score entre 80 et 95, ou identité insuffisante/conflit | `human_review` |
| Score < 80 sans référence ou demande de revue | `new` |
| Note contenant « doublon » | Revue imposée, même à 100 |

Deux séries renseignées et différentes obtiennent un score nul : ce sont deux instances physiques, même avec le même produit.

## 5. Appeler le matcher et lire sa réponse

Exemple exécutable depuis `backend/` :

```python
from app.importers.multi_matcher import MultiLevelMatcher

matcher = MultiLevelMatcher()
existing = [{"id": 42, "full_name": "Jean Dupont", "phone": "0612345678"}]
incoming = {"full_name": "Dupont Jean", "phone": "+33 6 12 34 56 78"}

certain = matcher.match("clients", incoming, existing)
assert certain.zone == "auto"
assert certain.entity_id == 42

uncertain = matcher.match("clients", {"full_name": "Jean Dupont"}, existing)
assert uncertain.zone == "human_review"
assert uncertain.entity_id is None
```

`candidates` contient les cibles proposées, `reason` explique la décision et `evidence` précise la preuve utilisée. Le planner INT-100 consomme ce résultat ; une zone `new` ne dispense jamais de la validation des champs requis.

## 6. Vérifier les cas métier

```bash
cd backend
uv run pytest tests/test_matching_v2.py tests/test_importers_structure.py -q
```

Les [tests](../../../backend/tests/test_matching_v2.py) couvrent homonymes, C001/C005, téléphone absent, conflit de référence, parent différent et séries distinctes. Deux interventions à des dates différentes restent distinctes. L’ancien export recouvrant le récent est aussi testé de bout en bout dans [test_import_service_v2.py](../../../backend/tests/test_import_service_v2.py).
