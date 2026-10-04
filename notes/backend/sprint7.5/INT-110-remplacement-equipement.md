# INT-110 — Remplacer un équipement sans perdre son histoire

## 1. Point de départ : INT-97, pas une seconde implémentation

INT-97 a déjà livré la ressource `Equipment`, la self-FK
`replaced_by_id`, le statut `REPLACED`, la route
`POST /api/v1/equipment/{equipment_id}/replace` et son écriture atomique.
INT-103 y a ajouté le lien optionnel vers `Installation`. INT-105 et
INT-107 ont depuis enrichi les interventions liées avec les photos et
les rapports PDF versionnés. INT-110 ne recrée donc ni table ni endpoint :
il complète le **contrat des informations du successeur** et vérifie
l'historique traversant les modules après remplacement.

Le sprint 7.5 contient deux tâches distinctes. La visite showroom
INT-109 reste un événement commercial ; INT-110 manipule uniquement
des équipements physiques. Le statut showroom `SOLD` n'est ni une
condition de remplacement ni une nouvelle vente automatique.

## 2. Invariants du modèle et des relations

`Equipment` est une instance matérielle, pas la référence catalogue
`Product`. Après remplacement :

```text
Ancien équipement (REPLACED) ── replaced_by_id ──► Nouveau (ACTIVE)
    ├── son site, numéro, dates, garantie
    ├── son installation éventuelle
    └── ses interventions ──► photos et rapport PDF versionné

Nouveau : même site, nouvel ID, sa propre identité et ses dates,
          installation_id NULL tant qu'aucune installation distincte
          n'est enregistrée.
```

La relation `Intervention.equipment_id` n'est **jamais réécrite** par
la route de remplacement. `Photo.intervention_id`, `Report.intervention_id`
et `ReportVersion.report_id` ne le sont pas davantage. Une ancienne
installation reste liée à l'ancien appareil ; copier son
`installation_id` sur le nouveau violerait l'unicité 1 → 0..1 et
inventerait que la même installation a produit deux appareils.
La route crée un appareil sur le même `site_id`, sans recopier
automatiquement produit, série, garantie, notes, intervention ou vente.
La nouvelle `installation_id` reste nullable par conception.

Les dates/numéros historiques de l'ancien restent inchangés. Des
équipements importés peuvent manquer de série ou de dates : les champs
de remplacement demeurent **facultatifs**, comme dans le DAT, pour
ne pas inventer des valeurs. Si deux numéros de série sont connus,
la route refuse de déclarer un nouvel appareil avec la même série
que l'ancien (409), après normalisation des espaces et de la casse.
Cela ne crée pas une règle d'unicité globale qui empêcherait la reprise
de données historiques.

## 3. Contrat HTTP et validation

La route authentifiée existante reçoit toujours le nom historique
`installation_date`, mappé sur `Equipment.installed_at`. Le remplacer
par un alias non prévu aurait cassé les consommateurs INT-97.
INT-110 ajoute `commissioned_at`, `warranty_start` et
`warranty_end` au corps `EquipmentReplace` :

```json
{
  "new_product_id": 12,
  "serial_number": "NEW-200",
  "installation_date": "2026-10-15",
  "commissioned_at": "2026-10-16",
  "warranty_start": "2026-10-15",
  "warranty_end": "2030-10-15"
}
```

Dans `app/modules/equipment/schemas.py`, Pydantic interdit les champs
inconnus, impose un ID produit positif s'il est présent, limite le
numéro de série à 255 caractères, supprime ses espaces de bord et
refuse une série fournie mais blanche. `warranty_end` ne peut précéder
`warranty_start` ; `commissioned_at` ne peut précéder la pose si les
deux dates sont connues. Deux dates absentes ne sont pas remplacées
par « aujourd'hui » et une garantie inconnue ne devient pas une
garantie fictive. Une violation du schéma reçoit 422.

Le service conserve l'ordre déjà prévu : équipement existant (404),
statut `ACTIVE`/`OUT_OF_SERVICE` sans successeur (sinon 409),
numéro de série distinct (409), référence produit réelle (404),
puis création atomique. L'extrait ci-dessous écrit **sur le nouveau
seulement** :

```python
new = await self.repo.replace(old, dict(
    product_id=body.new_product_id,
    installed_at=body.installation_date,
    commissioned_at=body.commissioned_at,
    serial_number=body.serial_number,
    warranty_start=body.warranty_start,
    warranty_end=body.warranty_end,
    notes=body.notes,
))
```

Une réponse 201 est `EquipmentResponse` : elle expose le nouvel ID,
`installed_at`, `commissioned_at`, la garantie et `installation_id: null`.
Une lecture GET de l'ancien expose `lifecycle_status: REPLACED` et
`replaced_by_id` pointant sur ce nouvel ID. Le rôle d'écriture reste
celui de la route équipement existante : utilisateur authentifié ;
INT-110 n'introduit pas en douce de nouveaux rôles. La politique
fine d'affectation des techniciens n'est pas prétendue livrée ici.

## 4. Transaction, concurrence et erreurs

Le repository d'INT-97 fait déjà le travail crucial :

```python
new = Equipment(site_id=old.site_id, **values)
self.db.add(new)
await self.db.flush()
result = await self.db.execute(update(Equipment).where(
    Equipment.id == old.id,
    Equipment.replaced_by_id.is_(None),
    Equipment.lifecycle_status.in_([
        EquipmentStatus.ACTIVE, EquipmentStatus.OUT_OF_SERVICE,
    ]),
).values(replaced_by_id=new.id, lifecycle_status=EquipmentStatus.REPLACED))
if result.rowcount != 1:
    await self.db.rollback()
    return None
await self.db.commit()
```

`flush` attribue l'ID du successeur mais ne commit pas. L'UPDATE
conditionnel « réclame » l'ancien : si l'état a changé, le rollback
supprime aussi le nouveau non validé ; le service transforme ce refus
en 409. Si `flush`, `execute` ou `commit` échoue, le repository rollback
également. Rien n'est écrit dans les tables interventions, photos,
rapports ou installations. Une seconde demande de remplacement
séquentielle obtient 409 ; une course réelle entre deux connexions
n'a **pas** été lancée dans INT-110. La condition SQL et la
transaction sont des protections, non une preuve de charge concurrente
sur PostgreSQL.

## 5. Migration et préservation des données

INT-110 ne modifie aucune table : `Equipment.serial_number`,
`installed_at`, `commissioned_at`, `warranty_start/end`,
`lifecycle_status`, `replaced_by_id` et `installation_id`
existent déjà. Il n'y a donc pas de révision Alembic INT-110,
pas de backfill, pas de changement de contrainte sur une base
existante. Le contrat du payload est la seule évolution de schéma
API. La projection OpenAPI `tests/contract_int110.py` valide
précisément les trois nouvelles dates optionnelles avant de repasser
par les gardes INT-109 → INT-104 → R0. Les anciens artefacts et
empreintes de référence restent immuables.

La migration PostgreSQL introduite par INT-109 n'est **pas**
validée par ces tests INT-110. L'état du sprint reste « vérifié
localement » jusqu'à un run CI/déploiement demandé séparément.

## 6. Recette API et résultats réellement observés

Une recette directe `test_int110_replacement_keeps_installation_intervention_photo_and_pdf`
est ajoutée dans `backend/tests/test_equipment.py`. Sur une SQLite
jetable, elle crée par ORM une ancienne installation et un appareil
avec date/série/garantie, une intervention qui référence cet appareil,
une photo et un rapport avec version PDF et SHA-256. Puis elle
utilise l'API réelle pour :

| Scénario | Résultat observé |
|---|---|
| Série blanche, garantie inversée, mise en service antérieure à la pose | 422, ancien toujours ACTIVE, un seul appareil en base |
| Série identique à l'ancien, produit introuvable | 409 / 404, aucune création |
| Remplacement complet | 201 ; nouvel ID, même site, série distincte, pose/mise en service/garantie ; `installation_id` null |
| Lecture de l'ancien après remplacement | `REPLACED`, `replaced_by_id` renseigné ; installation, série et garantie initiales inchangées |
| Lecture intervention/photo et téléchargement PDF v1 | `equipment_id` ancien, photo conservée, octets PDF identiques |
| Rejeu | 409 ; pas de troisième appareil |

La photo est contrôlée ici comme **enregistrement lié et chemin** dans
la réponse, pas par l'ouverture du fichier physique : la recette
utilise un chemin fictif. Le PDF vérifie bien les octets archivés via
la route privée existante, sans le régénérer. Trois tests historiques
injectent séparément une panne sur `flush`, `execute` et `commit`
et vérifient le rollback ; un scénario INT-103 confirme que
l'ancien `REPLACED` n'est pas rattachable à une autre installation.

Commande réellement exécutée depuis `backend/` :

```sh
uv run pytest tests/test_equipment.py \
  tests/test_equipment_module.py::test_technician_replacement_keeps_historical_orm_links \
  tests/test_equipment_module.py::test_repository_replace_rolls_back_after_controlled_failure \
  tests/test_installations.py::test_replaced_equipment_cannot_be_attached \
  tests/test_modular_bootstrap.py::test_openapi_matches_r0_with_only_authorized_int106_delta_without_startup_or_sql \
  -q --tb=short
```

**10 tests réussis**, un warning `passlib/crypt`. Une première
exécution avait signalé que la garde OpenAPI R0 ne reconnaissait
pas encore les trois champs du payload ; la projection dédiée
INT-110 l'a corrigée, sans modifier le baseline. Aucun run
PostgreSQL, CI distante, frontend, navigateur ou déploiement
n'est revendiqué pour INT-110. Le cas de concurrence réelle
`TC-INT-110-03` reste **partiel**, explicitement noté dans
`docs/stages/stage7/sprint7.5/test-cases.json`.

## 7. Suite et limites

Les todos backend/frontend ont été relus avant et après la tâche.
TD-B013 (rôles), TD-B016 (volume d'import), TD-B019 (seed sûr),
TD-B020 (audit/maintenance photo), TD-B021 (résultats importés),
TD-B022 (volumétrie PDF), TD-B023 (origine vente showroom),
TD-F007 (écrans showroom/catalogue) et TD-F008 (administration
checklist) ne sont pas débloqués par les trois nouvelles dates
de remplacement. Aucune base locale persistante ni déploiement
n'a été modifié pour les valider. Le sprint
7.6 (VPS / documentation entretien) attend un feu vert distinct.

### Validation distante après le push du sprint

La section 6 décrit l'état **au moment de la livraison locale**. Le
code INT-109/110 a ensuite été poussé sur `main` (`624424b`) et le
[run CI/CD #37186606561](https://github.com/libileh91/tervo/actions/runs/37186606561)
a réussi : suite backend, migrations PostgreSQL sur tables vides,
recette showroom PostgreSQL et job frontend (tests, typecheck, build).
`Deploy — VPS` a été sauté. Il n'y a toujours **pas** de migration
INT-110 spécifique, de smoke navigateur ni de preuve d'une course
simultanée de deux remplacements sur PostgreSQL ; le cas
`TC-INT-110-03` demeure partiel.
