# INT-95 — Entité `Site` + chaîne `Client → Site → Intervention`

> Tervo v2 · Sprint 7.1 · Lot 1 (socle physique)

## Objectif

Introduire l'entité **`Site`** (le lieu physique) et **casser la liaison directe
`Client → Intervention`** pour respecter la chaîne physique verrouillée du DAT :

```text
Client ──► Site ──► Équipement ──► Intervention
```

Avant INT-95, une intervention portait directement `client_id`. Or le DAT est clair :
**le client n'est pas une adresse physique, l'adresse appartient au Site**, et
l'intervention se déroule **sur un site**. On a donc :

1. créé l'entité `Site` (avec les champs complets du data-model) ;
2. remplacé `Intervention.client_id` par `Intervention.site_id` (requis) ;
3. propagé le changement partout (service, repo, API, seed, report, tests, frontend).

Le contrat API change ; la migration préserve désormais les interventions existantes (correction lors de la revue INT-97).

## 1. Le modèle `Site` (champs complets du DAT)

Le data-model `02-techniques/02-data-model.md` listait `country` et `access_notes`
en plus de l'AC minimale. On a suivi le **DAT complet** (pas l'AC réduite) :

| Colonne        | Type           | Contrainte                                    |
| -------------- | -------------- | --------------------------------------------- |
| `id`           | `Integer`      | PK                                            |
| `client_id`    | `Integer`      | FK `client.id`, `NOT NULL`, `ON DELETE CASCADE` |
| `name`         | `String(255)`  | `NOT NULL`, indexé                            |
| `address`      | `String(500)`  | `NOT NULL`                                    |
| `postal_code`  | `String(20)`   | nullable                                      |
| `city`         | `String(255)`  | nullable, indexé                              |
| `country`      | `String(100)`  | nullable                                      |
| `access_notes` | `Text`         | nullable                                      |
| `notes`        | `Text`         | nullable                                      |
| `created_at` / `updated_at` | `DateTime` | `CURRENT_TIMESTAMP`              |

## 2. La chaîne `Intervention → Site`

`Intervention` ne référence **plus** `client_id`. Il porte `site_id` (FK `site.id`,
`ON DELETE CASCADE`, `NOT NULL`). Le client se remonte via `site.client_id`.

```python
# app/models/intervention.py
site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False, index=True)
site = relationship("Site", backref="interventions")
```

Conséquences en cascade :

- **Schéma** : `InterventionCreate.site_id` (au lieu de `client_id`),
  `InterventionResponse.site: SiteRef` (au lieu de `client: ClientRef`).
- **API** : `POST /interventions` exige `site_id` ; `GET /clients/{id}/interventions`
  est **supprimé** au profit de `GET /sites/{id}/interventions` (section 5.5 du DAT).
- **Dashboard** : `next_intervention` / `overdue` exposent `site_name` + `site_address`
  (plus `client_full_name`/`client_address`).
- **Statistiques client** (`get_client`) : la requête joint `Intervention → Site → Client`
  pour compter les interventions d'un client à travers ses sites.
- **Report PDF** : l'en-tête « Informations » affiche désormais **Client** (contact) +
  **Site** (localisation) + **Technicien**, car l'adresse appartient au site.
- **Seed** : chaque client reçoit un `Site`, et les interventions se rattachent à ce site.

## 3. Migration Alembic et données existantes

La révision `24556984074e` crée Site. La révision `06c3c51d3e72` ajoute ensuite `site_id` nullable, crée un site principal pour chaque ancien client ayant des interventions sans site, puis renseigne les liens avant d’imposer NOT NULL et de retirer `client_id`.

Si un client possède déjà des sites, le site de plus petit identifiant est retenu : l’ancien modèle ne fournissait pas de localisation plus précise. Le downgrade reconstitue client_id par la relation Site → Client.

La contrainte PostgreSQL historique reste nommée `job_client_id_fkey` après le renommage de la table ; la migration utilise donc ce nom. Un test sur PostgreSQL 17.4 jetable a validé upgrade, second upgrade, downgrade et remontée avec une intervention existante conservée. Aucun reseed n’est nécessaire pour ce changement.

## 4. Le pattern « chaîne d'entités » à retenir

Quand on remplace un FK direct par une chaîne (`Client → Site → Intervention`) :

1. **On casse d'abord le modèle** (`client_id` → `site_id`), puis on laisse le
   compilateur/tests pointer chaque usage cassé.
2. Les **requêtes spécialisées** (dashboard, stats) doivent **joindre** à travers la
   chaîne (`selectinload(Intervention.site).selectinload(Site.client)`).
3. Les **endpoints nichés** suivent la ressource : `GET /sites/{id}/interventions`
   remplace `GET /clients/{id}/interventions`.
4. Le **frontend** doit refléter la nouvelle hiérarchie : créer une intervention
   demande désormais un **client PUIS un site**.

## Vérification

- `uv run pytest tests/ -q` → **126 passed** (dont les 12 tests `Site` d'INT-95).
- `uv run alembic heads` → `06c3c51d3e72 (head)`.
- `npm run build` (frontend) → **✓ built**.

## Reste à aligner sur le DAT (tickets suivants)

- `equipment_id` (nullable) sur `Intervention` → **INT-97**.
- `type` / `result` / `created_by` / `scheduled_start/end` (datetime) sur
  `Intervention` → couverts par INT-106 (« Résultat + clôture ») et suivants.
- `priority` et `title` ne sont pas dans le data-model cible : à trancher plus tard.
