# Stage 7 — Tervo V2

Tervo V2 est réparti en six sprints. Ils reprennent les lots auparavant regroupés dans `sprint-6.2-v2`, puis `sprint7`, en conservant les identifiants INT, critères validés et cas de test.

La référence métier et technique reste le [DAT unique](../../DAT/new/00-sommaire.md). La prochaine tâche est **INT-102**, dans **sprint7.3**.

| Sprint | Périmètre | Tâches | Avancement |
|---|---|---|---|
| [7.1](sprint7.1/tasks.md) | Socle physique | INT-94 à INT-97 | Terminé |
| [7.2](sprint7.2/tasks.md) | Migration Excel | INT-98 à INT-101 | Terminé |
| [7.3](sprint7.3/tasks.md) | Chaîne commerciale | INT-102 à INT-103 | À démarrer — prochaine tâche INT-102 |
| [7.4](sprint7.4/tasks.md) | Cycle terrain | INT-104 à INT-108 | À traiter |
| [7.5](sprint7.5/tasks.md) | Showroom et remplacement | INT-109 à INT-110 | À traiter |
| [7.6](sprint7.6/tasks.md) | Déploiement VPS et documentation entretien | INT-111 à INT-112 | À traiter |

Chaque dossier contient son `tasks.md` et son `test-cases.json`. Les notes terminées sont classées dans [sprint7.1](../../../notes/backend/sprint7.1/) et [sprint7.2](../../../notes/backend/sprint7.2/).

## Dépendances et suivi

- 7.1 fournit le socle à 7.2, 7.3 et 7.4.
- 7.2 ne dépend pas de 7.3 : les équipements historiques ont `installation_id` nullable.
- 7.5 utilise le socle 7.1 et la chaîne commerciale 7.3 pour relier showroom et vente.
- 7.6 déploie le périmètre effectivement validé et documente les fonctionnalités encore en backlog.

La mesure de l’import sur un volume représentatif reste ouverte dans [TD-B016](../../todos/backend.md#td-b016--mesurer-limport-sur-un-volume-représentatif). Le raccordement Equipment → Installation reste suivi dans TD-B014 pour INT-103. Avant INT-110, vérifier le remplacement déjà amorcé dans INT-97.

## Historique du Stage 6

Les sprints 6.1 et 6.2 restent dans le Stage 6. Les dossiers 6.3 à 6.5 ont été supprimés après reprise des éléments utiles ; leur version initiale reste consultable dans l’historique Git.

| Ancien planning | Reprise V2 |
|---|---|
| [6.2 — Import](../stage6/sprint-6.2/tasks.md) | [7.2](sprint7.2/tasks.md), après le socle [7.1](sprint7.1/tasks.md) |
| 6.3 — Catalogue et exposition (ancien) | Catalogue INT-96 dans [7.1](sprint7.1/tasks.md) ; showroom repensé INT-109 dans [7.5](sprint7.5/tasks.md) |
| 6.4 — Déploiement VPS (ancien) | INT-111 dans [7.6](sprint7.6/tasks.md) |
| 6.5 — Documentation entretien (ancien) | INT-112 dans [7.6](sprint7.6/tasks.md) |

Les critères détaillés de déploiement et d’entretien, ainsi que leurs dix cas de test, sont repris dans 7.6 (provenance `legacy_id`). TD-B010 est désormais rattaché à INT-111.

L’ancien 6.3 décrivait un modèle différent : prix d’achat/vente dans le catalogue, statut de stock, exposition physique, badges essai/vendable et suppression en cascade. Ces critères et leurs tests ne sont pas transposés au modèle V2 (`Product` désactivable, `ShowroomVisit`). Le CRUD et l’unicité du catalogue sont suivis dans INT-96. Les anciens écrans d’exposition ne sont pas considérés comme livrés : les besoins frontend catalogue/showroom (navigation, filtres, états loading/empty/error) restent à vérifier et planifier selon le DAT V2 avant leur livraison, avec suivi dans [TD-F007](../../todos/frontend.md#td-f007--reprendre-les-besoins-frontend-catalogueshowroom-dans-le-modèle-v2).

## Décisions verrouillées (rappel)

- Identifiants **entiers auto-incrémentés** (pas d'UUID)
- `job` → **`Intervention`** (rename, + `under_warranty`)
- `Equipment` **sans** `PLANNED` — `ACTIVE / OUT_OF_SERVICE / REPLACED / RETIRED`
- `SaleLine 1 → N Installation` · `Installation 1 → 0..1 Equipment`
- `Installation.status` : `SCHEDULED / IN_PROGRESS / COMPLETED / CANCELLED`
- `Report` versionné V1 · `ShowroomVisit.client_id` nullable · `Quote` hors V1
- `replaced_by_id` (ancien → nouveau) · `under_warranty` sur `Intervention`

---

Les développements suivent le workflow Fuliyeh, avec un feu vert par tâche. Ce découpage conserve les critères et leur avancement ; il ne lance aucune implémentation ni aucun déploiement.
