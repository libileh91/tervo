# INT-107 — Rapport logique, versions PDF et confirmation manuelle

## 1. Décision métier et résultat

Une intervention terminée peut être corrigée après édition de son document.
Le GET PDF historique régénérait le rapport à partir des données **actuelles** :
un même lien pouvait alors produire un document différent. INT-107 conserve
un PDF par version ; une correction crée une nouvelle version sans modifier
les octets de l'ancienne.

L'utilisateur a validé une **confirmation manuelle** de transmission externe
pour V1. Cliquer sur « Confirmer » signifie que la personne déclare avoir
transmis *cette version*, hors de Tervo. L'application n'envoie pas d'email,
ne possède aucun SMTP, et n'atteste ni réception ni date effective de livraison.
`transmitted_at` date la confirmation, `transmitted_by_id` identifie son auteur.

```text
Intervention 1 ── 0..1 Report logique
                         ├── ReportVersion 1  [PDF archivé ; transmission confirmée]
                         └── ReportVersion 2  [PDF archivé ; transmission non confirmée]
```

Le statut global `COMPLETED` et le résultat `PART_NEEDED` (INT-106) restent
distincts de l'état d'une version documentaire. Un rapport généré n'est pas
automatiquement transmis. La création d'un devis, la notification client et
la replanification restent hors de ce périmètre.

## 2. Sources et responsabilités

| Couche | Source | Pourquoi |
|---|---|---|
| ORM | [models.py](../../../backend/app/modules/reports/models.py#L1) | Un document logique, plusieurs versions physiques |
| Schémas | [schemas.py](../../../backend/app/modules/reports/schemas.py#L1) | Métadonnées JSON seulement, jamais le BLOB |
| Service | [service.py](../../../backend/app/modules/reports/service.py#L1) | Permissions, transaction, numérotation et lecture |
| Routes | [api.py](../../../backend/app/modules/reports/api.py#L1) | Contrats REST, réponse PDF privée |
| Renderer | [renderer.py](../../../backend/app/modules/reports/renderer.py#L1) | Jinja2 et WeasyPrint existants |
| Template | [report_template.html](../../../backend/app/modules/reports/templates/report_template.html#L1) | PDF client sous le nom Tervo |
| Migration | [j107e0010001](../../../backend/alembic/versions/j107e0010001_report_versions.py#L1) | Création sans effacer les anciennes données |
| Frontend | [InterventionDetailPage](../../../frontend/src/pages/InterventionDetailPage.vue#L284) | Générer, choisir, consulter, confirmer |
| Client HTTP | [client.ts](../../../frontend/src/api/client.ts#L1) | JWT, clé de rejeu, métadonnées et Blob |

Le registre ORM charge `Report` et `ReportVersion`. La `Base` reste unique
et compte maintenant 21 tables/mappers. Les preuves de refactor R0–R11 ne
sont pas réécrites : les nouveaux contrats sont un delta explicite.

## 3. Modèle et contraintes de conservation

Extraits fidèles de [l'ORM](../../../backend/app/modules/reports/models.py#L7) :

```python
class Report(Base):
    __tablename__ = "report"
    __table_args__ = (UniqueConstraint("intervention_id", name="uq_report_intervention"),)

    id = Column(Integer, primary_key=True)
    intervention_id = Column(Integer, ForeignKey("intervention.id", ondelete="RESTRICT"), nullable=False)
```

Une intervention a au plus un document logique. `RESTRICT` empêche une cascade
SQL de détruire son archive. La suppression ordinaire de l'intervention vérifie
aussi la présence d'un rapport et répond 409 avant de tenter le DELETE.
Cette règle ne prétend pas rendre tous les parcours de suppression Client/Site
conviviaux : la politique d'effacement d'archives devra être cadrée séparément.

```python
class ReportVersion(Base):
    __tablename__ = "report_version"
    __table_args__ = (
        UniqueConstraint("report_id", "version", name="uq_report_version_number"),
        UniqueConstraint("report_id", "request_key", name="uq_report_version_request"),
        CheckConstraint("version >= 1", name="ck_report_version_number"),
        CheckConstraint("size > 0", name="ck_report_version_size"),
    )
```

`version` est un entier, non un UUID métier. Les deux unicités protègent la
numérotation et le rejeu facultatif d'une opération, même en présence d'un
writer concurrent. PostgreSQL permet plusieurs clés `NULL` : sans
`Idempotency-Key`, deux POST explicitement distincts peuvent produire v1/v2.

Les champs essentiels de la version sont `pdf` (`LargeBinary`/`BYTEA`),
`sha256`, `size`, `generated_at`/`generated_by_id`,
`transmitted_at`/`transmitted_by_id`.
Le statut `GENERATED` ou `TRANSMITTED` est **calculé** à partir de
`transmitted_at`, pas stocké comme un deuxième état susceptible de diverger.
`storage_key` renvoie `database:report-version:<id>` : c'est une référence
technique au BLOB privé, **pas** une URL publique téléchargeable.

Le [BLOB est différé dans l'ORM](../../../backend/app/modules/reports/models.py#L29) :

```python
pdf = deferred(Column(LargeBinary, nullable=False))
```

Lister les métadonnées de plusieurs versions ne charge donc pas leurs PDF.
Le GET binaire charge explicitement la version et son BLOB. Enregistrer
les bytes dans la DB permet une seule transaction pour document + version,
sans créer un fichier à réconcilier avec un commit SQL. Ce choix V1 ne vaut
pas validation d'un volume documentaire de production (TD-B022).

## 4. API : les GET n'écrivent plus

Préfixe `/api/v1`. Tous les chemins exigent un JWT actif.
La lecture et la génération appartiennent à l'ADMIN ou au technicien
actuellement assigné à l'intervention. MANAGER n'existe pas encore (TD-B013).

| Méthode | Chemin | Résultat |
|---|---|---|
| POST | `/interventions/{id}/reports` | 201, métadonnées de la nouvelle version |
| GET | `/interventions/{id}/reports` | Rapport logique et liste de versions, sinon 404 |
| GET | `/reports/{id}` | Rapport logique et versions |
| GET | `/reports/{id}/versions/{v}` | PDF archivé, `application/pdf` |
| POST | `/reports/{id}/versions/{v}/transmit` | Confirmation **manuelle** de cette version |
| GET | `/interventions/{id}/report/download` | Ancien chemin, lecture seule de la dernière version |

Avant le premier POST, le GET historique répond 404 sans générer en cachette.
L'URL `report_url` fournie à la clôture par INT-106 devient consultable après
la génération explicite. Une intervention non terminée ne peut pas générer
de version (400). L'API refuse l'accès d'un autre technicien en 403 ;
le JWT absent donne 401. ADMIN peut consulter l'archive.

La réponse JSON d'une version contient identité logique/physique, numéro,
hash, taille, dates/auteurs et statut, **pas** `pdf`. Le GET binaire répond
avec `Content-Type: application/pdf` et `Cache-Control: private, no-store`.
Il n'y a pas de `/uploads/reports/**` exposant les données client sans JWT.

La confirmation exige le body :

```json
{"confirmed": true}
```

`false`, l'absence du champ ou une propriété supplémentaire sont refusés.
Le service ne remet pas à jour `transmitted_at` ou `transmitted_by_id` si
la confirmation est répétée, même par un autre utilisateur autorisé.
Il vérifie aussi l'intégrité du PDF avant de marquer une version transmise.

## 5. Générer une version : verrou, PDF et commit

Extrait de [ReportService.generate](../../../backend/app/modules/reports/service.py#L37) :

```python
intervention = await self._intervention(intervention_id, user, lock=True)
if intervention.status != InterventionStatus.COMPLETED:
    raise HTTPException(400, "L'intervention doit être terminée")
```

Le service réutilise le verrou de ligne `Intervention` introduit pour les
transitions et items de checklist. Il lit ensuite le `Report` de cette
intervention ou l'insère par `flush`, sans commit intermédiaire.
Un `request_key` déjà utilisé pour ce rapport renvoie la même version.
La nouvelle génération lit le dernier numéro et ajoute un, sous le verrou
commun. L'unicité SQL reste une défense complémentaire.

```python
pdf = ReportExporter().generate_pdf(intervention)
if not pdf.startswith(b"%PDF-"):
    raise RuntimeError("Le renderer n'a pas produit un PDF valide")
version = ReportVersion(
    report_id=report.id, version=(previous or 0) + 1, request_key=request_key,
    pdf=pdf, sha256=sha256(pdf).hexdigest(), size=len(pdf),
    generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    generated_by_id=user.id,
)
self.db.add(version)
await self.db.flush()
response = ReportVersionResponse.model_validate(version)
await self.db.commit()
return response
```

Le `try/except` du service fait `rollback` si rendu, insertion, validation de
réponse ou commit échoue. Le test API injecte une erreur de renderer *après*
le `flush` du `Report` logique : aucune ligne logique/physique partielle
ne subsiste en nouvelle session. Le rapport ancien, s'il existe, n'est pas
modifié par une génération suivante.

La date générée est en UTC puis stockée sans timezone, conformément aux
colonnes actuelles. Le renderer conserve son horodatage de présentation ;
ce n'est pas une migration des dates de toute l'application.

## 6. Télécharger et confirmer sans régénérer

Lors d'une lecture binaire, le service compare taille et SHA-256 aux
octets archivés :

```python
if len(version.pdf) != version.size or sha256(version.pdf).hexdigest() != version.sha256:
    raise HTTPException(500, "Intégrité du PDF archivé invalide ; aucun recalcul automatique")
```

Un fichier corrompu n'est pas remplacé silencieusement par un rendu du
modèle courant ; il faut investiguer/restaurer les données. Le même garde
s'applique avant une confirmation manuelle de transmission.
SHA-256 détecte une incohérence de contenu ; **ce n'est pas** une signature
légale ni une protection contre un administrateur DB pouvant modifier
à la fois le BLOB et son hash.

Une version déjà confirmée conserve ses octets, son hash et son premier
horodatage/auteur quand on corrige les observations de l'intervention.
POST génère v2. L'ancienne URL choisit alors v2 pour compatibilité,
mais `GET /reports/{id}/versions/1` rend **exactement v1**. Le document
transmis est identifiable et reste téléchargeable par numéro de version.

## 7. Migration et historique non inventé

Révision `j107e0010001` après `i106e0010001`.
Les deux nouvelles tables sont créées avec FK, unicités et CHECK.
Aucune intervention `COMPLETED` ancienne n'obtient un PDF inventé par
la migration. Elle reste sans rapport jusqu'à une génération explicite.

Un downgrade sur base vide réussit. Si un rapport est présent, la migration
refuse **avant la première DDL** :

```python
if op.get_bind().execute(sa.text("SELECT id FROM report LIMIT 1")).first():
    raise RuntimeError("INT-107 downgrade refused: archived reports would be lost")
```

La chaîne réelle PostgreSQL 17.4 `upgrade head → downgrade -1 → upgrade head`
a été exécutée sur conteneur jetable (port loopback, aucun volume existant).
Une SQLite scratch contenant v1/v2 a refusé le downgrade et conservé
ses deux versions. Toutes les anciennes migrations restent inchangées.

La comparaison structurée du schéma PostgreSQL après upgrade ne voit
**aucun nouvel écart** : seulement les deux opérations remove/add de la FK
technicien historique (`ondelete` absent dans l'ancien SQL, `SET NULL`
dans l'ORM). Ne pas annoncer `alembic check` vert sur cette base.

## 8. Frontend et qualité du contrat

Le panneau Rapport d'une intervention terminée propose une génération
explicite, un sélecteur de versions et la preview/téléchargement authentifiés.
Un premier GET 404 affiche « Aucune version archivée » ; une autre erreur
affiche un état avec réessai, au lieu de générer un document pour réparer
une simple erreur de réseau.

Le client utilise `API_BASE` pour les métadonnées **et** le Blob : le
frontend sur `tervoapp.com` peut ainsi appeler le domaine API configuré,
pas une route locale relative qui serait invalide. Les Blob URLs de preview
sont révoquées quand une autre version est chargée. Une clé aléatoire
`crypto.randomUUID()` est conservée pour réessayer la même demande de
génération, puis renouvelée après succès. Ce UUID est un jeton technique
de rejeu HTTP, **pas** un identifiant de modèle métier ; les IDs restent entiers.

Confirmer affiche un dialogue clair : l'utilisateur affirme avoir transmis
la version **hors de Tervo**. Le texte UI ne dit pas « email envoyé ».
Le choix d'une version confirmée affiche la date de confirmation ; la
nouvelle version de correction reste `GENERATED` tant qu'elle n'est pas
confirmée séparément.

Le typecheck et le build frontend passent. Aucun test navigateur INT-107
n'a été effectué : ces vérifications ne prouvent pas à elles seules le
clic réel dans la Vue, la preview iframe ou un téléchargement sur VPS.

Le template PDF hérité contenait encore le libellé « ResQ - Rapport ».
INT-107 rend le document client au nom **Tervo** conformément à l'identité
du projet. Les deux fixtures R7 historiques sont inchangées ; leur test
projette explicitement ce petit delta sur le HTML attendu avant comparaison.
Les PDF déjà stockés ne seront jamais réécrits lors d'une future correction
de libellé.

## 9. Tests réellement effectués et limites

| Vérification | Résultat |
|---|---|
| Recette API directe sur SQLite jetable | Génération v1/v2, contrôle SHA/bytes, rôles, rejeu, confirmation, rollback, suppression 409 |
| Même recette sur PostgreSQL 17.4 isolé | 1 cas d'intégration réussi, warning passlib |
| Anciennes routes, golden et garde import/metadata ciblés | 67 cas réussis avant la correction du seul libellé ; 3 cas ciblés réexécutés ensuite avec le nom Tervo |
| Frontend | `bun run typecheck` et `bun run build` réussis, Vite 6.4.3, 455 modules |
| Migrations | Upgrade/downgrade/re-upgrade PG vides réussis ; downgrade avec v1/v2 refusé sur SQLite |
| CI distante / déploiement / SMTP / navigateur | **Non exécutés** |

Le scénario API est durable dans
[test_report_versions_api.py](../../../backend/tests/test_report_versions_api.py#L1),
avec DB/uploads fictifs et option
`TERVO_REPORT_TEST_DATABASE_URL` vers un PostgreSQL disposable :
le test crée un schéma aléatoire, puis supprime seulement le sien.
Il n'y a pas une série supplémentaire de vingt tests unitaires.
La suite backend **complète** n'a pas été relancée à la demande de l'utilisateur ;
seule la non-régression ciblée indiquée dans le tableau est vérifiée.

Commandes réellement exécutées par le parent :

```sh
# Depuis un cwd scratch, DATABASE_URL SQLite et UPLOAD_DIR scratch :
"$ROOT/backend/.venv/bin/python" -m pytest \
  "$ROOT/backend/tests/test_report_versions_api.py" \
  "$ROOT/backend/tests/test_reports_module.py" \
  "$ROOT/backend/tests/test_api.py" \
  "$ROOT/backend/tests/test_modular_bootstrap.py" \
  "$ROOT/backend/tests/test_imports_module.py" \
  "$ROOT/backend/tests/test_installation_migration.py" -q --tb=short -p no:cacheprovider

# Même recette API, avec TERVO_REPORT_TEST_DATABASE_URL vers le conteneur PG isolé :
"$ROOT/backend/.venv/bin/python" -m pytest \
  "$ROOT/backend/tests/test_report_versions_api.py" -q --tb=short -p no:cacheprovider

cd "$ROOT/frontend"
bun run typecheck
bun run build
```

La CI a été configurée pour exécuter cette unique recette dans son job
PostgreSQL existant ; un workflow configuré n'est pas un run distant réussi.
R0–R11, l'oracle Excel et les fixtures PDF historiques restent intacts.

Limites assumées :

- Marquage manuel, sans garantie de livraison ni preuve de réception ;
  l'heure enregistrée est celle de confirmation dans Tervo.
- Le BLOB privé est sauvegardable avec PostgreSQL, mais aucune restauration
  ou mesure représentative de volume n'a été exécutée (TD-B022).
- L'API ne propose ni UPDATE ni DELETE des versions, mais un acteur ayant les
  privilèges SQL peut toujours changer la base ; SHA-256 seul n'est pas
  une signature infalsifiable.
- Les suppressions Client/Site héritées peuvent rencontrer une contrainte
  SQL lorsqu'une archive existe ; seul le DELETE intervention a une erreur
  métier 409 explicite ici. Politique d'effacement/audit à cadrer.
- Les métadonnées étendues et l'audit des originaux photo restent ouverts
  dans TD-B020 ; PDF v1 reste stable même si la photo source est ensuite supprimée,
  car les octets de la version sont stockés séparément.
- TD-B004 (photos obligatoires), TD-B013 (rôles), TD-B016 (import représentatif),
  TD-B019 (seed sur base existante) et TD-B021 (issues historiques) restent ouverts.
  INT-108 n'est pas commencée.
