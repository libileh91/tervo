# Spécification des Endpoints API — Tervo

> **Objet :** API REST pour Tervo.
>
> **Documents liés :** `specs/01-specs-fonctionnelle.md`, `specs/02-spec-technique.md`

---

## 1. Conventions

| Règle | Valeur |
|-------|--------|
| Base URL | `/api/v1/` |
| Format | JSON request/response |
| Auth | `Authorization: Bearer <JWT>` |
| Pagination | `?page=1&page_size=25` |
| Codes HTTP | 200, 201, 204, 400, 401, 403, 404, 409, 422, 500 |

---

## 2. Auth

```
POST   /api/v1/auth/login                    # Login → JWT
POST   /api/v1/auth/refresh                   # Refresh token
GET    /api/v1/auth/me                        # Profil courant
PUT    /api/v1/auth/me                        # Mise à jour profil
POST   /api/v1/auth/register                  # Création compte (admin)
```

### `POST /api/v1/auth/login`

```json
// Request
{ "username": "jean.martin", "password": "secret123" }

// Response 200
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": 1, "username": "jean.martin", "role": "technician" }
}
```

---

## 3. Clients

```
GET    /api/v1/clients                        # Liste paginée + recherche
POST   /api/v1/clients                        # Créer un client
GET    /api/v1/clients/{id}                   # Détail + historique
PUT    /api/v1/clients/{id}                   # Mettre à jour
DELETE /api/v1/clients/{id}                   # Supprimer
GET    /api/v1/clients/{id}/jobs              # Jobs du client
GET    /api/v1/clients/{id}/devis             # Devis du client
GET    /api/v1/clients/{id}/factures          # Factures du client
```

### `POST /api/v1/clients`

```json
// Request
{
  "full_name": "M. Dupont",
  "phone": "06 12 34 56 78",
  "email": "dupont@email.fr",
  "address": "12 rue de Paris",
  "postal_code": "75001",
  "city": "Paris",
  "siret": "12345678900012",
  "tva_intra": "FR12345678900",
  "type": "particulier",
  "notes": "Code porte B4, 3e étage"
}
```

---

## 4. Jobs

```
GET    /api/v1/jobs                            # Liste paginée + filtres
POST   /api/v1/jobs                            # Créer un job
GET    /api/v1/jobs/{id}                       # Détail complet
PUT    /api/v1/jobs/{id}                       # Mettre à jour
DELETE /api/v1/jobs/{id}                       # Annuler
PUT    /api/v1/jobs/{id}/start                 # Démarrer → en_cours
PUT    /api/v1/jobs/{id}/complete              # Terminer
```

### `POST /api/v1/jobs`

```json
// Request
{
  "client_id": 1,
  "title": "Panne clim salon",
  "description": "Le client signale que la clim ne refroidit plus.",
  "priority": "haute",
  "scheduled_date": "2026-07-15",
  "scheduled_start_time": "14:00",
  "scheduled_end_time": "16:00",
  "devis_id": null
}
```

---

## 5. Checklist

```
GET    /api/v1/jobs/{job_id}/checklist          # Liste items
PUT    /api/v1/jobs/{job_id}/checklist/{id}     # Mettre à jour un item
PUT    /api/v1/jobs/{job_id}/checklist/batch    # Mise à jour batch
```

### `PUT /api/v1/jobs/{job_id}/checklist/batch`

```json
// Request
{
  "items": [
    { "id": 1, "checked": true, "note": "RAS, installation propre" },
    { "id": 2, "checked": true, "note": "Disjoncteur coupé" }
  ]
}
// Response 200
{ "updated": 2 }
```

---

## 6. Photos

```
POST   /api/v1/jobs/{job_id}/photos            # Upload photo
DELETE /api/v1/jobs/{job_id}/photos/{id}       # Supprimer
```

### `POST /api/v1/jobs/{job_id}/photos`

```http
POST /api/v1/jobs/42/photos
Content-Type: multipart/form-data

file: photo.jpg
category: avant
```

```json
// Response 201
{
  "id": 1,
  "category": "avant",
  "file_url": "/uploads/photos/abc123.jpg",
  "thumbnail_url": "/uploads/photos/thumb_abc123.jpg",
  "taken_at": "2026-07-15T14:10:00"
}
```

---

## 7. Matériaux

```
GET    /api/v1/jobs/{job_id}/materials          # Liste
POST   /api/v1/jobs/{job_id}/materials          # Ajouter
PUT    /api/v1/jobs/{job_id}/materials/{id}     # Modifier
DELETE /api/v1/jobs/{job_id}/materials/{id}     # Supprimer
```

---

## 8. Rapports

```
GET    /api/v1/jobs/{job_id}/report/download     # Télécharger PDF
```

---

## 9. Reviews

```
GET    /api/v1/review/{share_token}             # Page publique (no auth)
POST   /api/v1/review/{share_token}/submit      # Soumettre un avis (no auth)
GET    /api/v1/jobs/{job_id}/review             # Voir l'avis (auth)
```

---

## 10. Dashboard

```
GET    /api/v1/dashboard/summary                # Résumé technicien
```

---

## 11. Devis (NOUVEAU — Module Financier)

```
GET    /api/v1/devis                            # Liste paginée (admin/comptable)
POST   /api/v1/devis                            # Créer un devis
GET    /api/v1/devis/{id}                       # Détail + lignes
PUT    /api/v1/devis/{id}                       # Mettre à jour
DELETE /api/v1/devis/{id}                       # Supprimer (brouillon uniquement)
PUT    /api/v1/devis/{id}/status                # Changer le statut
GET    /api/v1/devis/{id}/pdf                   # Télécharger PDF
POST   /api/v1/devis/{id}/lignes                # Ajouter une ligne
PUT    /api/v1/devis/{id}/lignes/{line_id}      # Modifier une ligne
DELETE /api/v1/devis/{id}/lignes/{line_id}      # Supprimer une ligne
POST   /api/v1/devis/{id}/facturer              # Transformer en facture
```

### `POST /api/v1/devis`

```json
// Request
{
  "client_id": 1,
  "tva_taux": 20.0,
  "notes": "Installation climatisation réversible",
  "lignes": [
    { "description": "Unité intérieure Mitsubishi", "quantite": 1, "prix_unitaire_ht": 1200.00 },
    { "description": "Main d'œuvre - pose 2 jours", "quantite": 2, "unite": "jour", "prix_unitaire_ht": 450.00 }
  ]
}

// Response 201
{
  "id": 42,
  "numero": "DEV-2026-00042",
  "statut": "brouillon",
  "montant_ht": 2100.00,
  "montant_ttc": 2520.00,
  "lignes": [...]
}
```

### `PUT /api/v1/devis/{id}/status`

```json
// Request
{ "statut": "envoyé" }
// → passe de "brouillon" à "envoyé"
// Statuts valides : envoyé, accepté, refusé, expiré
```

### `POST /api/v1/devis/{id}/facturer`

```json
// Response 201
{
  "facture_id": 18,
  "numero": "FAC-2026-00018",
  "message": "Facture créée à partir du devis DEV-2026-00042"
}
```

---

## 12. Factures (NOUVEAU)

```
GET    /api/v1/factures                         # Liste paginée (admin/comptable)
POST   /api/v1/factures                         # Créer une facture
GET    /api/v1/factures/{id}                    # Détail + lignes
PUT    /api/v1/factures/{id}                    # Mettre à jour
DELETE /api/v1/factures/{id}                    # Supprimer (en_attente uniquement)
PUT    /api/v1/factures/{id}/payer              # Marquer comme payée
GET    /api/v1/factures/{id}/pdf                # Télécharger PDF
POST   /api/v1/factures/{id}/lignes             # Ajouter une ligne
PUT    /api/v1/factures/{id}/lignes/{line_id}   # Modifier une ligne
DELETE /api/v1/factures/{id}/lignes/{line_id}   # Supprimer une ligne
```

### `PUT /api/v1/factures/{id}/payer`

```json
// Request
{
  "date_paiement": "2026-07-20",
  "mode_paiement": "virement"
}

// Response 200
{
  "id": 18,
  "statut": "payée",
  "date_paiement": "2026-07-20",
  "mode_paiement": "virement"
}
```

### `GET /api/v1/factures` — Filtres

```
?page=1&page_size=25&statut=en_attente&statut=retard&client_id=1
```

---

## 13. Bilans (NOUVEAU)

```
GET    /api/v1/bilans                           # Liste des bilans mensuels/annuels
GET    /api/v1/bilans/{periode}                 # Détail d'un bilan
POST   /api/v1/bilans/calculer                  # Calculer le bilan du mois en cours (admin)
GET    /api/v1/bilans/impayes                   # Factures en retard
```

### `GET /api/v1/bilans/{periode}`

```
GET /api/v1/bilans/2026-07
```

```json
// Response 200
{
  "periode": "2026-07",
  "type": "mensuel",
  "nb_interventions": 45,
  "nb_devis_emis": 38,
  "nb_devis_acceptes": 30,
  "nb_factures_emises": 28,
  "nb_factures_payees": 22,
  "total_devis_ht": 52000.00,
  "total_factures_ht": 41000.00,
  "total_factures_ttc": 49200.00,
  "total_encaisse": 31000.00,
  "total_impaye": 18200.00,
  "panier_moyen_ht": 911.11,
  "delai_paiement_moyen_jours": 18.5
}
```

---

## 14. Import (NOUVEAU — Admin)

```
POST   /api/v1/admin/import/preview             # Preview Excel (multipart)
POST   /api/v1/admin/import/validate            # Validation complète
POST   /api/v1/admin/import/execute             # Exécuter l'import
GET    /api/v1/admin/import/logs                # Historique des imports
GET    /api/v1/admin/import/logs/{id}           # Détail + erreurs
```

### `POST /api/v1/admin/import/preview`

```http
POST /api/v1/admin/import/preview
Content-Type: multipart/form-data

file: clients_2015.xlsx
type: clients
```

```json
// Response 200
{
  "fichier": "clients_2015.xlsx",
  "type_detecte": "clients",
  "lignes_totales": 234,
  "colonnes_detectees": ["Nom Client", "Tel", "Adresse", "Ville", "Code Postal", "Email", "SIRET", "Notes"],
  "mapping_propose": {
    "full_name": "Nom Client",
    "phone": "Tel",
    "address": "Adresse",
    "city": "Ville",
    "postal_code": "Code Postal",
    "email": "Email",
    "siret": "SIRET",
    "notes": "Notes"
  },
  "preview": [
    { "full_name": "M. Dupont", "phone": "06 12 34 56 78", ... },
    ...
  ]
}
```

### `POST /api/v1/admin/import/validate`

```json
// Request
{
  "fichier": "clients_2015.xlsx",
  "type": "clients",
  "mapping": {
    "full_name": "Nom Client",
    "phone": "Tel",
    "address": "Adresse",
    "city": "Ville"
  }
}

// Response 200
{
  "total": 234,
  "pret_a_importer": 210,
  "doublons_potentiels": 18,
  "erreurs": 6,
  "doublons": [
    { "row": 12, "nom": "Dupont Jean", "match": "DUPONT Jean (existant)", "score": 95 },
    ...
  ],
  "erreurs_detail": [
    { "row": 45, "champ": "phone", "valeur": "", "erreur": "Champ obligatoire manquant" },
    ...
  ]
}
```

### `POST /api/v1/admin/import/execute`

```json
// Request
{
  "fichier": "clients_2015.xlsx",
  "type": "clients",
  "mapping": { ... },
  "doublons_resolus": {
    "12": "skip",
    "45": "merge"
  }
}

// Response 200
{
  "import_id": 3,
  "statut": "succes",
  "lignes_traitees": 234,
  "lignes_creees": 210,
  "lignes_ignorees": 18,
  "lignes_erreurs": 6,
  "rapport": "Import terminé avec succès. 210 clients créés, 18 doublons ignorés."
}
```

---

## 15. Admin Users (futur P2)

```
GET    /api/v1/admin/users                     # Liste utilisateurs
POST   /api/v1/admin/users                     # Créer un utilisateur
PUT    /api/v1/admin/users/{id}                # Modifier
DELETE /api/v1/admin/users/{id}                # Désactiver (soft delete)
```

---

## 16. Matrice de permissions

| Endpoint | Technician | Comptable | Admin | Public |
|----------|:----------:|:---------:|:-----:|:------:|
| `GET /dashboard/summary` | ✅ | — | ✅ | — |
| `GET/POST /clients` | ✅ | ✅ | ✅ | — |
| `GET/POST /jobs` | ✅ | — | ✅ | — |
| `PUT /jobs/{id}/start` | ✅ (si assigné) | — | ✅ | — |
| `PUT /jobs/{id}/complete` | ✅ (si assigné) | — | ✅ | — |
| `POST /jobs/{id}/photos` | ✅ | — | ✅ | — |
| `GET /jobs/{id}/report/download` | ✅ | ✅ | ✅ | — |
| `GET/POST /devis` | — | ✅ | ✅ | — |
| `GET/POST /factures` | — | ✅ | ✅ | — |
| `GET /bilans` | — | ✅ | ✅ | — |
| `POST /bilans/calculer` | — | — | ✅ | — |
| `POST /admin/import/*` | — | — | ✅ | — |
| `GET /admin/users` | — | — | ✅ | — |
| `GET /review/{token}` | — | — | — | ✅ |
| `POST /review/{token}/submit` | — | — | — | ✅ |

---

> **Sommaire :** `00-sommaire.md`
> **Architecture :** `04-architecture.md`
