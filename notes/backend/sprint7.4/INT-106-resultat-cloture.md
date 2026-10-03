# INT-106 — Résultat global et clôture atomique

## 1. Le problème métier : terminée ne veut pas dire résolue

Cette tâche prolonge INT-104 (`74f05a6`) et INT-105 (`5b8eb36`).
Le statut décrit l'avancement ; le résultat décrit l'issue métier.
Une intervention peut être terminée alors qu'une pièce reste nécessaire :

```json
{
  "status": "COMPLETED",
  "result": "PART_NEEDED"
}
```

Ce JSON est une combinaison valide, pas un échec de workflow.
On ne remplace donc pas `COMPLETED` par un nouveau statut « pièce nécessaire ».
Le technicien qualifie explicitement l'issue au moment de clôturer.

Trois notions restent distinctes :

| Donnée | Sens | Exemple |
|---|---|---|
| `Intervention.status` | Avancement | `IN_PROGRESS`, `COMPLETED` |
| `Intervention.result` | Issue globale, six valeurs | `PART_NEEDED` |
| `ChecklistItem.result` | Texte de réalisation d'un contrôle | `"Pression faible"` |

Un item renseigné n'est pas nécessairement conforme. Une checklist entièrement
réalisée ne justifie pas de sélectionner automatiquement `RESOLVED`.
De même, la note client `Review.rating` n'est pas une preuve de résolution.

La tâche ne crée ni devis, ni vente, ni nouvelle intervention :
`QUOTE_NEEDED` et `RESCHEDULE` qualifient une suite à prévoir, sans l'automatiser.

## 2. Sources et responsabilités

| Couche | Source | Rôle |
|---|---|---|
| ORM | [intervention.py](../../../backend/app/modules/interventions/models/intervention.py#L35) | Enum et contrainte SQL |
| Schémas | [schemas/intervention.py](../../../backend/app/modules/interventions/schemas/intervention.py#L36) | Contrats de lecture, clôture et anti-bypass |
| Service | [complete_intervention](../../../backend/app/modules/interventions/services/intervention.py#L208) | Préconditions et transaction |
| Repository intervention | [get_by_id](../../../backend/app/modules/interventions/repositories/intervention.py#L68) | Verrou et rechargement de l'état |
| Repository avis | [create](../../../backend/app/modules/interventions/repositories/review.py#L32) | Flush sans commit quand le service possède la transaction |
| Migration | [i106e0010001](../../../backend/alembic/versions/i106e0010001_intervention_result.py#L1) | Historique inconnu et downgrade sûr |
| Import | [service.py](../../../backend/app/modules/imports/service.py#L69) | Empreinte canonique compatible avec les résultats inconnus |
| Frontend | [InspectionPage](../../../frontend/src/pages/InspectionPage.vue#L40) | Choix explicite et protection des saisies |
| Helpers frontend | [interventionCompletion.ts](../../../frontend/src/composables/interventionCompletion.ts#L1) | Enum, labels et payload |
| Client API | [client.ts](../../../frontend/src/api/client.ts#L369) | DTO de clôture exact, distinct du détail |
| Historique UI | [SiteInterventionHistory](../../../frontend/src/components/SiteInterventionHistory.vue#L1) | Lecture paginée de l'endpoint existant |

La route conserve `PUT /api/v1/interventions/{id}/complete`.
Les routes de création et édition ordinaires ne deviennent pas des raccourcis
de clôture. Le registre compte toujours 19 tables/mappers : un enum Python
et une nouvelle colonne ne créent pas une nouvelle entité persistée.

## 3. Enum et stockage : une contrainte, pas seulement une convention

Le modèle définit les six issues exactes :

```python
class InterventionResult(str, enum.Enum):
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    PART_NEEDED = "PART_NEEDED"
    QUOTE_NEEDED = "QUOTE_NEEDED"
    RESCHEDULE = "RESCHEDULE"
```

`str` facilite la représentation JSON ; `enum.Enum` ferme l'ensemble des valeurs.
Une chaîne `"resolved"`, un texte blanc ou une septième issue ne sont pas
des valeurs canoniques.

La contrainte ORM est :

```python
__table_args__ = (
    CheckConstraint(
        "result IN (" + ", ".join(repr(value.value) for value in InterventionResult) + ")",
        name="ck_intervention_result",
    ),
)
```

La colonne `result` est un `String(30)` nullable, sans valeur par défaut.
Le CHECK existe également dans la migration : une insertion SQL ne peut pas
contourner l'ensemble des six valeurs simplement en évitant Pydantic.

Pourquoi nullable alors que la nouvelle clôture exige un résultat ?

- Les anciennes interventions terminées ne portaient pas cette information.
- Leur attribuer `RESOLVED` à partir du seul statut inventerait une donnée.
- La base conserve donc `NULL` pour l'historique inconnu.
- L'API impose un résultat explicite pour chaque nouvelle clôture.

La contrainte ne prétend pas que toute ligne `COMPLETED` a un résultat :
ce serait incompatible avec la conservation de l'historique.
Elle contrôle le domaine des valeurs lorsqu'une issue est renseignée.

## 4. Contrats API

### 4.1 Requête de clôture

Extrait réel :

```python
class InterventionCompleteRequest(BaseModel):
    model_config = {"extra": "forbid"}
    result: InterventionResult
    observations: str | None = None
```

Pas de défaut sur `result` : absence et `null` donnent 422.
`extra="forbid"` refuse notamment d'envoyer un statut arbitraire dans ce body.

```json
{
  "result": "PART_NEEDED",
  "observations": "Une pièce de remplacement est nécessaire."
}
```

Le résultat d'un item checklist peut rester un texte libre ;
ce contrat d'enum concerne seulement l'issue globale.

### 4.2 Observations : trois intentions différentes

| Payload | Comportement |
|---|---|
| Pas de clé `observations` | Conserver les observations existantes |
| `"observations": null` | Conserver les observations existantes |
| `"observations": ""` | Remplacer explicitement par une chaîne vide |
| `"observations": "Texte"` | Remplacer par ce texte |

Le service teste `is not None`, pas la vérité de la chaîne :

```python
if body.observations is not None:
    intervention.observations = body.observations
intervention.status = InterventionStatus.COMPLETED
intervention.result = body.result.value
intervention.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
```

La date est calculée en UTC puis stockée sans timezone pour rester cohérente
avec les colonnes `DateTime` actuelles. Cela n'est pas une migration globale
de toutes les dates vers des timestamps timezone-aware.

### 4.3 Refuser le contournement par CRUD

Les schémas create/update héritent de ce garde :

```python
class _NoEditableResult(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def refuse_result(cls, data):
        if isinstance(data, dict) and "result" in data:
            raise ValueError("result is only writable through completion")
        return data
```

Le validateur voit le dictionnaire avant que les champs inconnus soient ignorés.
Même `{"result": null}` est refusé, afin de ne pas accepter une intention
qui ne serait pas appliquée.

La politique existante pour les **autres** champs inconnus n'est pas modifiée
transversalement. L'import utilise notamment le schéma de création pour
valider les champs physiques, puis extrait son propre statut historique.
Passer tous les schémas create en `extra="forbid"` sans adapter cette frontière
aurait cassé un autre module sous couvert d'INT-106.

### 4.4 Réponses de lecture et de clôture

Détail, liste et historique exposent `result` nullable.
La réponse de clôture l'expose non nullable, avec ces huit champs :

```typescript
export interface InterventionCompletionResponse {
  id: number;
  status: string;
  result: InterventionResult;
  completed_at: string;
  duration_minutes: number;
  report_url: string | null;
  review_share_token: string | null;
  review_share_url: string | null;
}
```

La revue a détecté un mauvais type initial : le client annonçait une réponse
de détail complète, alors que la clôture ne renvoie ni site, ni photos,
ni matériaux. Ce DTO propre remplace cet héritage trompeur.
Le smoke contrôle les huit clés de la réponse HTTP réelle.

Un défaut Python `None` peut être omis dans le schéma OpenAPI publié.
Le garde accepte cette absence ou un défaut JSON null, mais refuse un défaut
métier tel que `"RESOLVED"`. Nullable et résultat requis à la clôture ne sont
pas contradictoires : ils concernent des contrats différents.

## 5. Préconditions et verrou partagé

Avant de modifier quoi que ce soit, le service vérifie :

1. intervention existante ;
2. statut `IN_PROGRESS` ;
3. technicien courant assigné ;
4. tous les items checklist réalisés, c'est-à-dire résultat non null.

Le statut incorrect ou la checklist incomplète donnent 400.
L'assignation incorrecte sur une intervention au statut attendu donne 403.
Le body invalide est refusé en 422 par la validation de requête.

La recherche de clôture utilise :

```python
intervention = await self._find_or_404(intervention_id, for_update=True)
```

Le repository prend un verrou PostgreSQL et recharge l'identity map :

```python
query = query.with_for_update().execution_options(populate_existing=True)
```

`populate_existing=True` est important lorsqu'un autre writer a terminé
pendant l'attente du verrou. Réutiliser un statut mis en cache `IN_PROGRESS`
permettrait de traiter une clôture déjà réalisée.

Les PATCH d'items utilisent le même verrou parent, puis rafraîchissent l'item.
Le protocole conserve l'ordre intervention → item/avis.
Les quatre tests de course INT-104 restent exécutés avec le nouveau body
de clôture ; leur preuve n'est pas déduite des tests de helpers frontend.

Deux clôtures concurrentes sur la même intervention donnent un succès et
un refus. La première issue reste persistée, et un seul avis est créé.
Cette propriété est vérifiée sur PostgreSQL, pas revendiquée à partir de SQLite.

Une checklist historique vide ne bloque pas la clôture, si les autres
préconditions sont valides. TD-B004 reste différé : aucune photo BEFORE/AFTER
n'est rendue obligatoire implicitement.

## 6. Une transaction pour intervention et avis

### 6.1 Le problème évité

Commettre l'intervention, puis créer l'avis dans une deuxième transaction
laissait une possibilité d'échec partiel :

```text
intervention COMMITTED
création Review échoue
client reçoit une erreur, mais intervention déjà terminée
```

INT-106 regroupe la transition et l'avis automatique.
La génération du token n'est pas un envoi de SMS ou d'email.
Le champ rating initial de l'avis reste un comportement préexistant ;
il ne prouve pas que le client a répondu, ni que l'intervention est résolue.

### 6.2 Le repository respecte la transaction de l'appelant

Code réel :

```python
async def create(self, data: dict, *, commit: bool = True) -> Review:
    review = Review(**data)
    self.db.add(review)
    if commit:
        await self.db.commit()
    else:
        await self.db.flush()
    await self.db.refresh(review)
    return review
```

Le défaut conserve les appels directs existants.
La clôture utilise explicitement `commit=False`, pour obtenir l'ID et charger
les valeurs serveur sans rendre les écritures durables avant le service.

`flush` peut exécuter des INSERT/UPDATE et vérifier les contraintes ;
il ne signifie pas que la transaction est validée.
Une erreur après flush doit donc encore permettre de tout annuler.

### 6.3 Valider aussi la réponse avant le commit

Extrait de la fin du service :

```python
response = InterventionCompleteResponse(
    id=intervention.id,
    status=intervention.status.value,
    result=intervention.result,
    completed_at=intervention.completed_at,
    duration_minutes=duration,
    report_url=f"/api/v1/interventions/{intervention.id}/report/download",
    review_share_token=share_token,
    review_share_url=f"/review/{share_token}",
)
await self.db.commit()
return response
```

Le même `try` couvre observations, statut, résultat, date, flush de l'avis,
construction de cette réponse et commit.
Son traitement d'erreur est :

```python
except Exception:
    await self.db.rollback()
    raise
```

Le DTO est construit **avant** commit. Une erreur de validation de réponse
ne doit pas produire une erreur HTTP après avoir terminé durablement l'intervention.

Les tests injectent désormais trois types d'échec :

| Injection | Vérification après relecture dans une nouvelle session |
|---|---|
| Après le flush du Review | Ancien statut/résultat/date/observations, aucun avis |
| Pendant la construction de réponse | Même conservation |
| Au commit | Même conservation, y compris avis non persisté |

La relecture dans une nouvelle session est essentielle : vérifier seulement
l'objet ORM déjà chargé pourrait confondre état mémoire et données durables.
La répétition d'une clôture valide sur une intervention déjà terminée donne 400
et conserve la première issue, sa date et ses observations.

## 7. Migration : inconnu n'est pas résolu

Révision `i106e0010001`, après `h105e0010001`.
Les anciennes migrations ne sont pas réécrites.

```python
def upgrade():
    with op.batch_alter_table("intervention") as batch:
        batch.add_column(sa.Column("result", sa.String(30), nullable=True))
        batch.create_check_constraint(
            "ck_intervention_result",
            "result IN (" + ", ".join(repr(value) for value in RESULTS) + ")",
        )
```

Pas d'UPDATE qui déduirait une issue des anciens statuts.
Les dates, observations et avis existants restent inchangés.
Les tests vérifient également les anciennes interventions `COMPLETED`.

Le downgrade cherche une donnée non représentable avant toute DDL :

```python
row = op.get_bind().execute(sa.text(
    "SELECT id FROM intervention WHERE result IS NOT NULL ORDER BY id LIMIT 1"
)).first()
if row is not None:
    raise RuntimeError(f"INT-106 downgrade refused result at id={row.id}")
```

Un résultat renseigné ferait perdre une information métier lors du retrait
de la colonne : le downgrade refuse, avec l'ID concerné.
Un round trip sur données sans issue renseignée reste possible.
Il ne faut pas supprimer arbitrairement les résultats pour « faire passer » la commande.

La fixture ancienne d'installation reconstruit un schéma antérieur :
elle retire la colonne et le CHECK de sa copie de metadata avant de stamper
l'ancienne révision. Elle ne modifie pas la `Base` vivante.

L'arbitrage des résultats historiques confirmés reste un travail distinct,
suivi dans TD-B021. Une clôture obligatoire en V2 n'autorise pas un backfill
fictif de vingt années d'interventions.

## 8. Import : conserver une empreinte sans ignorer les changements métier

### 8.1 Ce que l'intégration a révélé

L'oracle R0 compare les données complètes, y compris les hashes de plans
et empreintes d'approbation. Ajouter une colonne `result=None` changeait
trois `database_snapshot`, même si aucune information métier n'avait changé.

Ni le fichier `before.json`, ni ses SHA, ni les empreintes attendues n'ont été
réécrits ou ignorés pour faire passer le test.

### 8.2 Canonicaliser seulement l'inconnu

Extrait réel de `ImportService._load` :

```python
if kind == 'interventions':
    # A nullable outcome added in INT-106 carries no information for
    # historical unknowns. Preserve their existing approval fingerprint,
    # but include every actual outcome so a changed result stales a plan.
    for row in pools[kind]:
        if row.get('result') is None:
            row.pop('result', None)
```

L'absence historique de la propriété et une valeur inconnue null ont la même
signification pour cette empreinte canonique. En revanche, un vrai résultat
reste dans le pool et donc dans le hash.

Le test dédié vérifie le cycle :

```text
historique result=NULL → empreinte compatible, plan approuvé
result=PART_NEEDED     → nouvelle empreinte, execute refuse en 409
result=NULL           → retour à l'ancienne empreinte
```

Retirer le résultat de toutes les empreintes aurait caché une modification
réelle après approbation. Cette règle conditionnelle préserve la protection
contre les plans obsolètes.

La projection de l'oracle retire la nouvelle colonne seulement après
`assert result is None` pour chaque intervention historique.
La présence d'une issue inventée échoue au test, au lieu d'être masquée.
Les gardes se composent 106 → 105 → 104 → R0 et gardent les autres contrats stricts.

## 9. Frontend : choix explicite, pas état déduit

Les options définissent les six libellés, sans valeur sélectionnée par défaut.
La liste reste distincte du champ libre de chaque item.

Le payload respecte l'intention sur les observations :

```typescript
export function completionPayload(result: unknown, observations: string, observationsEdited: boolean): InterventionCompletionPayload {
    if (!isInterventionResult(result)) throw new Error("Choisissez un résultat global.");
    // Omission preserves existing observations; an explicitly empty edit remains an edit.
    return observationsEdited ? { result, observations } : { result };
}
```

Une valeur non modifiée n'est pas renvoyée pour écraser des observations.
Une saisie explicitement vide reste une modification.

La garde de clôture cumule les conditions, elle ne teste pas seulement le select :

```typescript
const canComplete = computed(() => canEdit.value && intervention.value?.status === "IN_PROGRESS"
    && !!snapshot.value && !isError.value && !dirtyItems.value.size && !saving.value && !completing.value
    && !interventionError.value && isInterventionResult(selectedResult.value) && checklistReady(items.value));
```

Le handler revérifie cette garde puis positionne `completing=true`
avant son premier `await`. Les champs sont désactivés pendant la clôture.
Une erreur laisse le choix et les observations disponibles pour un réessai.

Le garde de navigation protège aussi les nouvelles saisies globales :

```typescript
onBeforeRouteLeave(() => {
    if (saving.value || completing.value) return false;
    if (completionSucceeded.value) return true;
    return (!dirtyItems.value.size && !selectedResult.value && !observationsEdited.value)
        || window.confirm("Quitter sans sauvegarder les modifications ?");
});
```

`completionSucceeded` évite de demander d'abandonner une saisie qui vient
d'être enregistrée, lors de la navigation normale vers le détail.
Les query refreshs n'écrasent pas des observations déjà éditées.

Le détail affiche l'issue à part du statut. L'historique par site réutilise
`GET /sites/{id}/interventions`, avec pages et états loading/error/empty.
Un null historique est affiché `Non renseigné`, jamais `Résolu`.

## 10. Rapport, mocks et limites historiques

Le rapport possède une ligne `Issue` distincte de `Statut`, avec six libellés
et le fallback `Non renseigné`. L'autoescape Jinja reste actif.
La fixture HTML R7 est conservée ; sa projection ajoute explicitement cette
seule nouvelle ligne au delta média/checklist déjà contrôlé.

Les mocks historiques du seed peuvent rester sans résultat connu.
Le seed n'a pas été lancé sur une base existante pour valider cette tâche.
TD-B019 reste ouvert.

Ne pas survendre l'immutabilité : INT-106 protège l'issue contre le CRUD normal
et les clôtures répétées. Elle ne fige pas tous les champs de l'intervention
ni un PDF transmis. Le rapport versionné/stable relève d'INT-107.

## 11. Validation exécutée

| Vérification | Résultat réellement observé |
|---|---|
| Backend complet, SQLite/schémas et uploads scratch | **617 passed, 9 skipped, 23 warnings**, 135,44 s |
| PostgreSQL canonique avant ajout du test d'échec au commit | **238 passed, 21 warnings**, 108,34 s |
| PostgreSQL final clôture/migration/empreinte, avec échec au commit | **39 passed, 22 warnings**, 13,10 s |
| Guards, oracle d'import et empreinte de résultat ciblés | **52 passed**, 17,27 s |
| Frontend | **14 tests, 74 assertions**, typecheck/build réussis |
| Build | Bun 1.2.20, Vite 6.4.3, 455 modules |
| Alembic réel PostgreSQL avec env.py | upgrade head → downgrade -1 → upgrade head réussis |
| Metadata PostgreSQL | Aucun nouvel écart INT-106 |

La revalidation de 39 cas inclut l'échec au commit, la concurrence, la migration
et l'empreinte d'import. Le tableau distingue les runs, sans déclarer
rétroactivement ce nouveau cas exécuté dans le run de 238.

Les neuf skips du run sans URL PostgreSQL sont les trois chaînes migration
et six cas de concurrence/verrouillage. Ils ne représentent pas neuf échecs.
Les warnings concernent passlib/crypt et le `datetime.utcnow()` du start
préexistant ; le timestamp de clôture utilise désormais `datetime.now(timezone.utc)`.

`alembic check` retourne encore **255**, uniquement pour la FK technicien
historique sans ON DELETE en SQL et avec SET NULL dans l'ORM.
Le parent exige exactement ces opérations remove/add dans la comparaison
structurée : aucun autre drift ne passe silencieusement.

### 11.1 Commandes parent

Interpréteur existant du checkout principal, pas d'installation Python utilisateur :

```sh
ROOT=/home/lob/workspace/python/fastapi/Tervo
# Cwd, DATABASE_URL SQLite et UPLOAD_DIR dans le scratch :
"$ROOT/backend/.venv/bin/python" -m pytest "$ROOT/backend/tests" \
  -q --tb=short -p no:cacheprovider

# Cible PostgreSQL jetable, variables TERVO_* explicites :
"$ROOT/backend/.venv/bin/python" -m pytest \
  "$ROOT/backend/tests/test_int106_completion.py" \
  "$ROOT/backend/tests/test_intervention_result_migration.py" \
  -q --tb=short -p no:cacheprovider

cd "$ROOT/frontend"
bun test tests
bun run typecheck
bun run build
```

Le run canonique de 238 cas contient également les fichiers ventes,
installations, imports, empreinte de résultat, checklist, médias et migrations.
Docker utilise l'image locale PostgreSQL 17.4, `--pull never`, port loopback
éphémère et aucun volume existant. Les conteneurs sont arrêtés après les runs.

Le workflow CI ajoute les URLs `TERVO_RESULT_TEST_DATABASE_URL` et
`TERVO_RESULT_MIGRATION_TEST_URL`. Sa configuration ne prouve pas un run
distant réussi ; aucun push ni déploiement n'est revendiqué ici.

### 11.2 Smoke navigateur effectué par le parent

Les sous-agents note/navigateur ont atteint leur limite d'abonnement.
Le parent a repris cette vérification lui-même, sans confondre arrêt de
délégation et validation fonctionnelle.

Setup : SQLite/uploads scratch, utilisateur/site fictifs, intervention en cours
avec deux contrôles, intervention historique terminée avec résultat null,
et lignes fictives supplémentaires pour tester la pagination.
Le setup ORM n'est ni `app.seed`, ni une écriture dans une base existante.

Playwright **1.49.1** et Chromium **131.0.6778.33** / v1148 sont utilisés.
Le parent réutilise le navigateur en cache en lecture seule : aucune nouvelle
installation globale. Frontend servi sur loopback et routage de recette
API/uploads vers le backend, sans modification des sources Vite.

| Étape | Observation |
|---|---|
| Login UI | Réussi |
| Sauvegarde de deux contrôles | Résultats libres enregistrés |
| Aucun choix global | Clôture toujours désactivée, même checklist complète |
| Choix PART_NEEDED et observations | Clôture disponible |
| Première tentative | HTTP 500 volontairement injecté avant l'API |
| Échec | Choix et observations conservés |
| Réessai | PUT complete 200 |
| Relecture détail | COMPLETED, PART_NEEDED et observations persistés |
| Vérification DB | Un seul avis, résultat historique toujours null |
| Historique UI | Issue connue/inconnue affichée, navigation page 2 réussie |
| PDF | 200, signature `%PDF-`, **15 907 octets** |
| Extraction PDF | Texte `Pièce nécessaire` confirmé avec pdftotext |

Payload HTTP réellement capturé :

```json
{
  "result": "PART_NEEDED",
  "observations": "Waiting for replacement part"
}
```

La réponse contient les huit clés du DTO de clôture, vérifiées par assertion.
Les tokens de recette sont normalisés dans la preuve retenue ; aucun token
de login n'est publié.

Aucun `pageerror` ni erreur HTTP inattendue n'a été observé.
Le 500 injecté est compté séparément. Backend/frontend/navigateur de recette
sont arrêtés à la fin, y compris lorsqu'une assertion échoue.

## 12. Suite et réserves

- INT-107 et INT-108 ne démarrent pas automatiquement.
- Aucun devis, vente ou replanification automatique.
- Pas de minimum photos à la clôture (TD-B004).
- Historique inconnu conservé ; arbitrage confirmé à cadrer dans TD-B021.
- Rôles élargis, volume réel d'import et seed sûr restent suivis dans leurs todos.
- Le cache Chromium créé durant le smoke INT-105 est documenté dans cette note
  de média ; il n'a pas été supprimé ni modifié par ce smoke INT-106.
- Preuves R0/R7/R11 et helpers historiques restent immuables.
- Pas de base applicative existante modifiée, pas de seed production,
  pas de CI distante ou déploiement annoncé sans exécution.
