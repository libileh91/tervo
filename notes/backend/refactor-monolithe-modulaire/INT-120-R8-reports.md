# INT-120 — R8 : rendre le rapport existant autonome dans son package

> **Planning :** [INT-120](../../../docs/stages/stage7/refactor-monolithe-modulaire/tasks.md#int-120--r8--déplacer-reports).
> **Parent R7 :** `7a52d03a8cc42292a8e944284ad31dee4425d4e8`, branche `refactor/modular-monolith`.
> **État :** implémenté, vérifié et accepté par l'utilisateur ; commit autorisé dans le worktree Delta attaché. Feu vert distinct R9 reçu.
> **Preuve :** [R8-validation.json](R8-validation.json), résultats observés et empreintes des sources/tests/fixtures.

## 1. Reprise de R7 et frontière de cette vague

L'utilisateur a accepté R7 et demandé « commit R7 & passe R8 ». Avant le commit,
les 52 empreintes sources/tests du manifeste R7 ont été vérifiées. Bootstrap,
module terrain et `test_api.py` ont été rejoués sur SQLite/uploads temporaires :
**57 passed, 4 warnings, 20,55 s**.

Le commit `[DEV]INT-119 — Refactor : isoler le domaine interventions` est
`7a52d03`. Il regroupe les 22 déplacements terrain, leurs consommateurs,
les 15 nouveaux cas, note et suivi R7. Il n'inclut aucun développement R8.
Le commit est créé dans le worktree attaché, sans push ni écriture directe
du checkout principal. La capture JSON R7 reste intacte.

R8 déplace un **rapport généré à la demande**. Il ne réalise pas INT-107 :
aucune table Report/ReportVersion, aucun document figé après transmission,
aucun envoi ou versionnement. Il ne transforme pas la clôture terrain en
nouvelle transaction métier.

Le contexte de rendu reste l'état courant de l'Intervention chargée. Télécharger
à nouveau peut donc produire un PDF avec une date de génération différente ;
ce n'est pas un document historiquement immuable.

## 2. Une API, un renderer et une ressource

```text
app/modules/reports/
├── __init__.py
├── api.py
├── renderer.py
└── templates/
    └── report_template.html
```

| Source précédente sous `backend/app/` | Destination |
|---|---|
| `api/v1/reports.py` | `modules/reports/api.py` |
| `exporters/report.py` | `modules/reports/renderer.py` |
| `exporters/report_template.html` | `modules/reports/templates/report_template.html` |

`ReportExporter` conserve son nom et ses méthodes. Le renderer n'est pas
rebaptisé « service » : son travail est de transformer des données déjà chargées
en HTML puis en PDF, pas d'orchestrer une nouvelle entité persistante.

Il n'y a ni repository, ni schéma Pydantic, ni modèle SQL dans ce package,
car le contrat renvoie des octets PDF et consulte l'Intervention existante.
Créer ces couches uniquement pour imiter les autres modules ajouterait des
abstractions sans responsabilité.

L'init est une docstring seule. Le router global importe explicitement
`app.modules.reports.api.router`. Les deux anciens modules Python et l'ancien
template sont absents ; aucun wrapper ne maintient une seconde implémentation.
Le namespace horizontal `app/exporters/__init__.py` restant est une docstring,
pas un renderer actif ; son retrait relève du nettoyage legacy R11.

## 3. Le template est résolu par rapport au code, pas au cwd

Dans le [constructeur](../../../backend/app/modules/reports/renderer.py#L19) :

```python
def __init__(self):
    template_path = Path(__file__).resolve().parent / "templates" / "report_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        self.template = Template(f.read())
```

`__file__` désigne le renderer réellement importé. `resolve().parent` donne
le dossier `modules/reports`, quel que soit le répertoire courant du processus.
L'ancien renderer utilisait déjà `__file__` ; R8 **préserve** cette indépendance,
il ne prétend pas corriger un ancien bug de cwd. Seul le segment `templates`
est ajouté pour suivre le déplacement.

Deux possibilités étaient pertinentes :

| Approche | Choix |
|---|---|
| `Path(__file__)`, comme l'implémentation actuelle | Retenu : règle simple, code et ressource livrés ensemble |
| `importlib.resources` avec support de distributions compressées | Possible pour une autre cible de packaging, mais non nécessaire au déploiement actuel |

Le Dockerfile copie `/app/app` intégralement du builder vers le runtime :
le nouveau template reste dans cet arbre. Le contrat de ressource n'exige
aucun accès à l'ancien dossier exporters. Cette lecture du Dockerfile n'est
pas annoncée comme un build Docker exécuté ou un déploiement validé.

Le template déplacé est comparé **octet pour octet** au parent Git R7.
Une première tentative de renommage via l'outil n'avait pas matérialisé le
fichier HTML au nouveau chemin ; le contrôle d'existence l'a détecté avant les
tests. L'ajout/suppression explicite a ensuite déplacé les octets exacts,
et le contrôle a été rejoué. Aucun renderer de secours n'a été ajouté.

## 4. Contrat HTTP et ordre des refus

La [route](../../../backend/app/modules/reports/api.py#L21) reste :

```text
GET /api/v1/interventions/{intervention_id}/report/download
```

Elle conserve le tag `reports`, la dépendance `get_current_user` et la session
injectée par `get_db`. Il n'y a pas de nouvelle URL `/reports` pour INT-107.

| Condition | Résultat actuel |
|---|---|
| JWT manquant/invalide ou utilisateur inactif | Refus d'authentification existant |
| Intervention inconnue | 404, `Intervention non trouvée` |
| Intervention attribuée à un autre utilisateur | 403, même si le demandeur est ADMIN |
| Intervention assignée mais non COMPLETED | 400 |
| Intervention COMPLETED assignée au demandeur | 200, PDF |

L'ordre est conservé : existence, assignation, puis statut. R8 n'ajoute pas
d'exception ADMIN et n'harmonise pas les erreurs avec les 409 d'Installation.

La réponse conserve ses headers :

```python
filename = f"rapport-intervention-{intervention_id}.pdf"

return Response(
    content=pdf_bytes,
    media_type="application/pdf",
    headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
    },
)
```

Le PDF est rendu en mémoire et retourné en bytes, pas stocké dans une table
ou un nouveau fichier d'archive. Le lien `report_url` produit par la clôture
terrain reste le même ; son consommateur n'a pas à découvrir une nouvelle route.

## 5. De l'ORM chargé au contexte de rendu

La route réutilise InterventionRepository du module terrain. Sa méthode
`get_by_id()` charge site puis client, technicien, checklist, photos et matériel
avec `selectinload`. Le renderer ne déclenche pas une série de requêtes SQL
au fil des interpolations du template.

Les responsabilités restent distinctes :

| Élément | Responsabilité |
|---|---|
| Route | JWT, référence, assignation, statut, chargement et réponse HTTP |
| Repository terrain | Lecture SQL et chargement des relations |
| Renderer | Préparer les groupes et valeurs du template |
| Jinja2 | Transformer le contexte en HTML |
| WeasyPrint | Transformer ce HTML en PDF |

### Checklist

```python
for item in intervention.checklist_items or []:
    entry = {"label": item.label, "checked": item.checked, "note": item.note}
    if item.category == "pre_intervention":
        pre_items.append(entry)
    else:
        post_items.append(entry)
```

Le groupe post conserve le fallback pour une catégorie différente de
`pre_intervention`. R8 n'ajoute pas d'enum ni de modèle snapshot. L'ordre
des éléments transmis par la relation reste le même.

### Matériel

```python
materials_list.append({"name": mat.name, "quantity": mat.quantity})
```

La quantité reste du texte. Le template remplace une quantité absente par
`---` ; il ne calcule ni stock ni coût. La note et l'API ne présentent pas
ce rendu comme une fonctionnalité financière.

### Client, site, technicien et dates

Le client est trouvé via `intervention.site.client`. Les champs rendus restent
nom/téléphone client, nom/adresse/code postal/ville du site, nom du technicien,
titre/statut/date/créneau/observations de l'Intervention.
Les références absentes donnent les chaînes vides existantes.

```python
"generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
```

Cette valeur est volatile. La fixer dans la comparaison de tests élimine
une différence temporelle, sans modifier le comportement livré.
Les statuts sont traduits par le dictionnaire d'affichage existant.

## 6. Photos incorporées : un PDF autonome, pas de nouveaux uploads

Le [_embed_photo](../../../backend/app/modules/reports/renderer.py#L24) lit
un fichier existant et produit une data URI :

```python
data = path.read_bytes()
b64 = base64.b64encode(data).decode("ascii")
ext = path.suffix.lower()
mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(
    ext.lstrip("."), "jpeg"
)
return f"data:image/{mime};base64,{b64}"
```

Les octets sont incorporés à l'HTML, sans requête HTTP vers une URL uploads.
Un chemin null ou inexistant donne None et la photo est omise ; une erreur
de lecture autre que l'absence n'est pas masquée par une nouvelle gestion
d'exceptions. La catégorie `avant` est distinguée ; les autres catégories
suivent le groupe après comme dans le parent.

R8 ne déplace, ne convertit ni ne supprime les fichiers uploadés. Le renderer
consomme les chemins déjà enregistrés par PhotoService. Il ne committe pas
la session et ne modifie pas l'Intervention lors du téléchargement.

## 7. Template et WeasyPrint : préserver le contenu effectif

Le template conserve sections Informations, Checklist, Photos, Matériaux,
Observations et Signatures ainsi que le CSS de pagination. Les modifications
de design, d'échappement ou de vocabulaire seraient des changements visibles,
pas de simples déplacements.

Les libellés historiques `ResQ - Rapport` restent donc inchangés dans cette
capture : le projet reste Tervo, sans décision de rebranding prise dans R8.
Une correction de ces libellés demanderait un changement de contenu assumé.

Le renderer utilise toujours `Template(f.read())`. R8 ne substitue pas
silencieusement un Environment avec une politique autoescape différente.
Il préserve le rendu courant ; il ne présente pas cette conservation comme
une revue complète de sécurité des données HTML ou des ressources PDF.

L'import WeasyPrint reste local à la conversion :

```python
def _html_to_pdf(self, html: str) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint."""
    from weasyprint import HTML

    return HTML(string=html).write_pdf()
```

Importer le package pur ne charge pas l'API, un engine ou WeasyPrint.
Importer le renderer charge son modèle Intervention utilisé pour l'annotation,
mais ne crée ni modèle Report ni engine. Un environnement de rendu réel doit
toujours disposer des bibliothèques système WeasyPrint existantes.
Une erreur de template/conversion n'est pas transformée en nouvelle erreur
métier dans ce refactor.

## 8. Comparaison avant/après et tests spécifiques

Les [sept nouveaux cas](../../../backend/tests/test_reports_module.py#L64)
distinguent le contenu de rendu, le moteur PDF réel, le cutover et le contrat HTTP :

| Famille | Cas | Résultat vérifié |
|---|---:|---|
| HTML complet et fallbacks | 2 | Comparaison de tout le HTML à la référence R7 |
| PDF réel dans un cwd isolé | 1 | Template chargé sans ancien chemin, `%PDF-`, taille > 1000 et `%%EOF` |
| Init pur | 1 | Pas d'import SQL, API ou renderer implicite |
| Layout/cutover AST | 1 | Anciennes sources absentes, pas de couches artificielles, imports app/tests sans legacy |
| Composition | 1 | Une route GET effective, compatible inclusions différées FastAPI |
| API/JWT réels | 1 | PDF + filename exact ; 400/403/404 et refus JWT vérifiés dans le même scénario |

**Sept cas pytest**, pas un cas supplémentaire par assertion HTTP. La fixture
API réutilise les utilisateurs et clés étrangères d'Installation sur SQLite,
en neutralisant explicitement sa variante PostgreSQL. Elle insère deux
Interventions, COMPLETED et PLANNED, avec un technicien assigné, puis utilise
de vrais tokens ; le renderer PDF n'est pas simulé dans le scénario API.

### Références métier fixes

La recette contient données fictives de client/site/technicien, titre et
observations avec caractères spéciaux, créneau, checklist pré/post cochée et
non cochée, catégorie checklist legacy, quantités texte, deux images existantes
avant/après, un chemin inexistant et un chemin null. La variante fallbacks
retire relations, dates, observations et collections et utilise un statut inconnu.

L'horloge est gelée au **28/09/2026 14:35**, seulement dans les tests :

```python
class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 28, 14, 35, tzinfo=tz)
```

Le worker a capturé les références sur le renderer R7 avant cutover. Le parent
a ensuite chargé **le code original via `git show 7a52d03`**, avec son template
original dans un dossier temporaire, et reproduit les deux références.
La fixture ne provient donc pas seulement de la sortie du nouveau renderer.

| HTML original, hors newline de stockage | Taille UTF-8 | SHA-256 |
|---|---:|---|
| Complet | 6 953 octets | `32756ef001d98bce9ec6925eaaa225c2a5aa9caeffffa20b0271c05e0fa86057` |
| Fallbacks | 3 272 octets | `ebcd76c80620eff838bd8b92722954d4c910de63cd83c652f93f414c09199daf` |

`fallbacks.html` est lisible directement. `complete.html.zlib.b64` conserve sans
perte le HTML complet et les deux data URI ; le test décode base64 puis zlib
avant comparaison intégrale. La newline finale du fichier fallback est retirée,
car le rendu Jinja R7 n'en possède pas. Aucune normalisation des champs, images
ou espaces du HTML rendu ne masque une différence.

Les trois lignes vides indentées de `fallbacks.html` (57, 63, 69) conservent
volontairement les espaces du rendu original. Elles peuvent être signalées
par un contrôle Git de whitespace sur la fixture ajoutée ; ce sont des octets
de référence, pas des espaces introduits dans le code de production.

Le test remplace uniquement `_html_to_pdf` par une capture de son argument pour
la comparaison HTML. Les autres tests appellent réellement WeasyPrint. On a
donc deux preuves complémentaires : entrée HTML identique et conversion réelle
fonctionnelle, sans imposer une égalité binaire PDF horodatée.

Les subprocess de pureté/PDF ont un timeout de 60 s et un environnement
SQLite/uploads temporaire explicite, sans URLs TERVO_* héritées. Le scénario
PDF démarre dans un dossier sans `app/exporters` ni ancien routeur ; le code
est découvert par PYTHONPATH, pas par un cwd correspondant à l'ancien backend.

## 9. Résultats finaux, commandes et revue

| Vérification | Résultat observé |
|---|---|
| Cinq fichiers ciblés, nouveaux cas inclus | **76 passed**, 5 warnings, 26,08 s |
| Suite SQLite entière | **360 passed**, 7 warnings, 70,91 s |
| PostgreSQL canonique via scout | **95 passed**, 1 warning, 52,46 s : 56 + 39 |
| Round-trip Alembic | Upgrade/downgrade -1/reupgrade réussis, head `f102e0010001` |
| Alembic check | Seul écart FK technicien historique ; aucune opération nouvelle |
| OpenAPI/metadata | Identiques à R0, 46 paths, 63 opérations, 17 tables |
| Runtime docs/OpenAPI | 200, OpenAPI HTTP égal à R0, startup/shutdown complets |
| Sources | API AST hors un import ; renderer AST hors un chemin ; template exact |

**360 = 353 R7 + 7 nouveaux cas R8.** Le premier run des quatre fichiers
existants comptait 69 succès, 5 warnings, 32,08 s après matérialisation effective
du template. Il n'est pas ajouté au total final.

La revue indépendante confirme le diff entier contre `7a52d03`, template
exact de 5 432 octets, une seule classe ReportExporter active, import WeasyPrint
lazy et packaging Docker compatible. Aucun finding restant. Elle a rejoué
**8 tests existants ciblés** (7 route/composition puis 1 OpenAPI), sans exécuter
les sept nouveaux tests de son snapshot ni répéter la suite entière/PostgreSQL.
Les sept nouveaux tests ont été exécutés dans les runs finaux du parent.

Commandes applicatives réellement exécutées :

```text
python -m pytest <5 fichiers ciblés absolus> -q -p no:cacheprovider
python -m pytest <backend/tests absolu> -q -p no:cacheprovider
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head
python -m alembic check
python -m pytest -q <5 fichiers PostgreSQL canoniques absolus>
python -m uvicorn app.main:app --host 127.0.0.1 --port <port libre>
git diff --check
```

Les sélections exactes sont dans le manifeste. Python 3.12.0 vient de
`/home/lob/workspace/python/fastapi/Tervo/backend/.venv/bin/python` ;
PYTHONPATH cible **les sources du worktree attaché**, pas celles du checkout
principal. Les runs parent utilisent cwd/SQLite/uploads temporaires et retirent
les variables TERVO_* pour SQLite, avec timeout pytest 240 s.

Le scout a utilisé PostgreSQL 17.4 local `--pull never`, port loopback éphémère,
sans volume nommé. URLs sync Alembic et async des fixtures pointent seulement
cette instance jetable. Les ressources ont été supprimées et aucun fichier
source modifié. Le groupe canonique est constitué d'installations/ventes/migration
Installation (56) et imports service/API (39), **pas de tests HTTP reports PG**.

L'écart Alembic reste remove_fk `intervention.technician_id → user.id` sans
ondelete SQL historique (`job_technician_id_fkey`), puis add_fk avec `SET NULL`
ORM. R8 ne le corrige pas et ne prétend pas obtenir un check vide.
Les captures R0 à R7 et les fixtures d'import sont conservées intactes.

Les snapshots sont comparés avec la représentation UTF-8 R0 : JSON trié,
indent 2, `ensure_ascii=False`, newline finale. Le serveur HTTP a été arrêté
par SIGTERM puis attendu : code `-15`, avec startup/shutdown complets dans
les logs. Aucun serveur n'est laissé actif.

## 10. Suivi et limites

TD-B005 pointe désormais vers le nouveau renderer/template ; sa réalisation
historique WeasyPrint reste acquise. TD-B018 conserve la reprise documentaire
7.4 dans un scope autorisé distinct, avec les chemins reports désormais connus.
La note R7 enregistre son commit et renvoie à R8, sans réécrire sa capture
historique ni ses résultats. Le déplacement n'autorise pas à implémenter ou
cocher INT-107. Les todos backend/frontend ont été relus : rôles TD-B013,
volume TD-B016 et interfaces TD-F007 ne sont pas débloqués par R8.

R9 exige sa propre autorisation et sa comparaison fonctionnelle d'import
avant/après, pas seulement les hashes des fixtures. Aucun de ces travaux
n'est commencé dans R8.

Limites à garder explicites :

- aucun modèle/versionnement ou archivage de rapport ajouté ;
- commit R8 autorisé après acceptation ; feu vert distinct R9 reçu ;
- pas de requête HTTP reports PostgreSQL revendiquée par les groupes canoniques ;
- aucun build Docker, CI distante, déploiement, seed, push ou E2E navigateur ;
- aucun changement d'auth, de transaction terrain, d'uploads, de template métier
  ou de politique HTML/ressources rendu ;
- une preuve de rendu HTML identique n'est pas une égalité binaire de PDF
  horodatés ni une campagne de sécurité PDF.

### Acceptation et vérification avant commit

L'utilisateur a demandé « commit R8 & passe R9 ». Les neuf empreintes
sources/tests/fixtures du manifeste sont conformes. Bootstrap, reports et
`test_api.py` ont été rejoués sur SQLite/uploads temporaires : **49 passed,
2 warnings, 24,53 s**, avec l'interpréteur et PYTHONPATH décrits plus haut.
Ce contrôle ne prétend pas répéter PostgreSQL. Le commit regroupe R8 uniquement ;
sa capture JSON avant acceptation est conservée.
