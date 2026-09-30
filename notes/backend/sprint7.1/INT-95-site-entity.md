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

## Vérification à la livraison d’INT-95

- `uv run pytest tests/ -q` → **126 passed** (dont les 12 tests `Site` d'INT-95).
- `uv run alembic heads` → `06c3c51d3e72 (head)`.
- `npm run build` (frontend) → **✓ built**.

## Reste à aligner sur le DAT (tickets suivants)

- `equipment_id` (nullable) sur `Intervention` → **réalisé dans INT-97**.
- `type` / `result` / `created_by` / `scheduled_start/end` (datetime) sur
  `Intervention` → couverts par INT-106 (« Résultat + clôture ») et suivants.
- `priority` et `title` ne sont pas dans le data-model cible : à trancher plus tard.

## Suivre une création et la reprise des données

Extrait du fichier [site.py](../../../backend/app/services/site.py), lignes 67 à 71 :

```python
async def create_site(self, data: SiteCreate) -> SiteResponse:
    """Create a new site (validates the client exists)."""
    await self._check_client_exists(data.client_id)
    site = await self.repo.create(data.model_dump())
    return SiteResponse.model_validate(site)
```

Le service vérifie d’abord que le client existe. `model_dump()` convertit la requête Pydantic en valeurs pour le repository ; `model_validate(site)` prépare la réponse à partir de l’objet ORM. Un client inexistant est signalé avant l’insertion.

La migration traite les interventions qui ne possèdent pas encore de site. Voici son `upgrade()` :

Extrait du fichier [06c3c51d3e72_link_intervention_to_site.py](../../../backend/alembic/versions/06c3c51d3e72_link_intervention_to_site.py), lignes 11 à 31 :

```python
def upgrade():
    # Create one default site per legacy client that has interventions but no site.
    op.execute("""
        INSERT INTO site (client_id, name, address, postal_code, city)
        SELECT c.id, 'Site principal', c.address, c.postal_code, c.city
        FROM client c
        WHERE EXISTS (SELECT 1 FROM intervention i WHERE i.client_id = c.id)
          AND NOT EXISTS (SELECT 1 FROM site s WHERE s.client_id = c.id)
    """)
    op.add_column("intervention", sa.Column("site_id", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE intervention SET site_id = (
            SELECT MIN(s.id) FROM site s WHERE s.client_id = intervention.client_id
        )
    """)
    op.alter_column("intervention", "site_id", nullable=False)
    op.create_foreign_key("intervention_site_id_fkey", "intervention", "site", ["site_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_intervention_site_id", "intervention", ["site_id"])
    op.drop_index("ix_intervention_client_id", table_name="intervention")
    op.drop_constraint("job_client_id_fkey", "intervention", type_="foreignkey")
    op.drop_column("intervention", "client_id")
```

L’INSERT ne crée un site que pour les clients ayant des interventions et aucun site. La nouvelle colonne reste nullable pendant le remplissage. L’UPDATE rattache ensuite chaque intervention au site de plus petit identifiant de son client ; seulement après, la migration impose NOT NULL et retire l’ancienne FK. Ce choix conserve le lien au client mais ne reconstitue pas une localisation historique inconnue.

La protection métier à la suppression est également explicite :

Extrait du fichier [site.py](../../../backend/app/services/site.py), lignes 80 à 85 :

```python
async def delete_site(self, site_id: int) -> None:
    """Delete a site."""
    site = await self._find_or_404(site_id)
    if await self.db.scalar(select(Equipment.id).where(Equipment.site_id == site_id).limit(1)):
        raise HTTPException(409, "Ce site possède des équipements : conserver leur historique")
    await self.repo.delete(site)
```

Le SELECT ne demande qu’un identifiant et s’arrête au premier équipement. Sa présence produit un conflit HTTP 409. La FK et cette règle métier répondent à deux besoins complémentaires : cohérence des relations et conservation de l’historique physique.
