# Spécification des Endpoints API — Tervo

> **Objet :** API REST pour Tervo.
>
> **Documents liés :** `specs/01-specs-fonctionnelle.md` (périmètre fonctionnel), `specs/02-spec-technique.md` (architecture tech)

---

## 1. Conventions

| Règle      | Valeur                                      |
| ---------- | ------------------------------------------- |
| Base URL   | `/api/v1/`                                  |
| Format     | JSON request/response                       |
| Auth       | `Authorization: Bearer <JWT>`               |
| Pagination | `?page=1&page_size=25`                      |
| Codes HTTP | 200, 201, 204, 400, 401, 403, 404, 422, 500 |

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
  "expires_in": 1800
}
```

---

## 3. Clients

```
GET    /api/v1/clients                        # Liste paginée + recherche
POST   /api/v1/clients                        # Créer un client
GET    /api/v1/clients/{id}                   # Détail + historique jobs
PUT    /api/v1/clients/{id}                   # Mettre à jour
DELETE /api/v1/clients/{id}                   # Supprimer
GET    /api/v1/clients/{id}/jobs              # Jobs du client
```

### `GET /api/v1/clients`

```
?page=1&page_size=25&search=dupont
```

```json
// Response 200
{
  "items": [
    {
      "id": 1,
      "full_name": "M. Dupont",
      "phone": "06 12 34 56 78",
      "email": "dupont@email.fr",
      "address": "12 rue de Paris",
      "postal_code": "75001",
      "city": "Paris",
      "notes": "Code porte B4, 3e étage",
      "jobs_count": 3,
      "last_job_date": "2026-05-15"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 25,
  "pages": 2
}
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
  "notes": "Code porte B4, 3e étage"
}

// Response 201
{ "id": 1, "full_name": "M. Dupont", ... }
```

### `GET /api/v1/clients/{id}`

Inclut l'historique des jobs :

```json
{
  "id": 1,
  "full_name": "M. Dupont",
  "phone": "06 12 34 56 78",
  "email": "dupont@email.fr",
  "address": "12 rue de Paris",
  "postal_code": "75001",
  "city": "Paris",
  "notes": "Code porte B4, 3e étage",
  "jobs": [
    {
      "id": 42,
      "title": "Panne clim",
      "status": "terminé",
      "completed_at": "2026-05-15T15:45:00",
      "technician": { "id": 1, "full_name": "Guuleed Liban" }
    }
  ]
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

### `GET /api/v1/jobs`

```
?page=1&page_size=25&status=planifié&date=2026-05-15&technician_id=1
```

```json
// Response 200
{
  "items": [
    {
      "id": 42,
      "title": "Panne clim salon",
      "status": "planifié",
      "priority": "haute",
      "scheduled_date": "2026-05-15",
      "scheduled_start_time": "14:00",
      "scheduled_end_time": "16:00",
      "client": {
        "id": 1,
        "full_name": "M. Dupont",
        "phone": "06 12 34 56 78",
        "address": "12 rue de Paris, 75001 Paris"
      },
      "technician": { "id": 1, "full_name": "Guuleed Liban" }
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 25,
  "pages": 1
}
```

### `POST /api/v1/jobs`

```json
// Request
{
  "client_id": 1,
  "title": "Panne clim salon",
  "description": "Le client signale que la clim ne refroidit plus.",
  "priority": "haute",
  "scheduled_date": "2026-05-15",
  "scheduled_start_time": "14:00",
  "scheduled_end_time": "16:00"
}

// Response 201
{
  "id": 42,
  "title": "Panne clim salon",
  "status": "planifié",
  "priority": "haute",
  "client": { "id": 1, "full_name": "M. Dupont" },
  "checklist_items": [
    { "category": "pre_intervention", "label": "État général de l'installation", "checked": false },
    { "category": "pre_intervention", "label": "Équipement sous tension coupé", "checked": false },
    { "category": "pre_intervention", "label": "Zone de travail sécurisée", "checked": false },
    { "category": "post_intervention", "label": "Installation fonctionnelle", "checked": false },
    { "category": "post_intervention", "label": "Nettoyage zone effectué", "checked": false }
  ]
}
```

À la création, la checklist pré et post est initialisée automatiquement avec les items par défaut.

### `GET /api/v1/jobs/{id}`

Retourne le job complet avec :

```json
{
  "id": 42,
  "title": "Panne clim salon",
  "status": "en_cours",
  "priority": "haute",
  "started_at": "2026-05-15T14:05:00",
  "client": { ... },
  "technician": { ... },
  "checklist_items": [
    { "id": 1, "category": "pre_intervention", "label": "État général...", "checked": true, "note": "RAS" }
  ],
  "photos": [
    { "id": 1, "category": "avant", "file_url": "/uploads/photo1.jpg", "thumbnail_url": "/uploads/thumb1.jpg" }
  ],
  "materials": [
    { "id": 1, "name": "Filtre HEPA", "quantity": "1" }
  ],
  "review": null,
  "report_url": null
}
```

### `PUT /api/v1/jobs/{id}/start`

```json
// Response 200
{
  "id": 42,
  "status": "en_cours",
  "started_at": "2026-05-15T14:05:00"
}
```

Validation : le job doit être `planifié`.

### `PUT /api/v1/jobs/{id}/complete`

```json
// Request
{
  "observations": "Filtre encrassé remplacé. Recharge gaz. OK."
}

// Response 200
{
  "id": 42,
  "status": "terminé",
  "completed_at": "2026-05-15T15:45:00",
  "duration_minutes": 100,
  "report_url": "/api/v1/reports/42/download",
  "review_share_token": "abc123def456",
  "review_share_url": "/review/abc123def456"
}
```

Validation : checklists pré/post OK, min. 1 photo avant + 1 photo après.

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
    { "id": 2, "checked": true, "note": "Disjoncteur coupé" },
    { "id": 3, "checked": true, "note": "OK" }
  ]
}

// Response 200
{ "updated": 3 }
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
  "taken_at": "2026-05-15T14:10:00"
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

### `POST /api/v1/jobs/{job_id}/materials`

```json
// Request
{ "name": "Filtre HEPA", "quantity": "1" }

// Response 201
{ "id": 1, "name": "Filtre HEPA", "quantity": "1", "position": 0 }
```

---

## 8. Rapports

```
GET    /api/v1/jobs/{job_id}/report              # Générer le rapport
GET    /api/v1/jobs/{job_id}/report/download     # Télécharger PDF
```

### `GET /api/v1/jobs/{job_id}/report/download`

Retourne le PDF généré. Si pas encore généré, le génère à la volée.

---

## 9. Reviews

```
GET    /api/v1/review/{share_token}             # Page publique (no auth)
POST   /api/v1/review/{share_token}/submit      # Soumettre un avis (no auth)
GET    /api/v1/jobs/{job_id}/review             # Voir l'avis (auth)
```

### `GET /api/v1/review/{share_token}`

Endpoint **public** (pas d'authentification requise).

```json
// Response 200
{
  "job": {
    "title": "Panne clim salon",
    "completed_at": "2026-05-15T15:45:00"
  },
  "technician": { "full_name": "Guuleed Liban" },
  "already_reviewed": false
}
```

### `POST /api/v1/review/{share_token}/submit`

```json
// Request
{
  "rating": 4,
  "comment": "Travail propre et rapide !",
  "reviewer_name": "M. Dupont"
}

// Response 200
{ "message": "Merci pour votre avis !" }
```

---

## 10. Dashboard

```
GET    /api/v1/dashboard/summary                # Résumé technicien
```

### `GET /api/v1/dashboard/summary`

```json
// Response 200
{
  "today": {
    "date": "2026-05-15",
    "jobs_total": 3,
    "jobs_in_progress": 1,
    "jobs_completed": 2
  },
  "next_job": {
    "id": 42,
    "title": "Panne clim salon",
    "priority": "haute",
    "client": { "full_name": "M. Dupont", "address": "12 rue de Paris" },
    "scheduled_start_time": "14:00"
  },
  "in_progress_job": {
    "id": 43,
    "title": "Maintenance annuelle",
    "started_at": "2026-05-15T10:00:00",
    "elapsed_minutes": 72
  }
}
```

---

## 11. Matrice de permissions

| Endpoint                         |   Technicien    | Admin | Public |
| -------------------------------- | :-------------: | :---: | :----: |
| `GET /clients`                   |       ✅        |  ✅   |   —    |
| `POST /clients`                  |       ✅        |  ✅   |   —    |
| `GET/POST /jobs`                 |       ✅        |  ✅   |   —    |
| `PUT /jobs/{id}/start`           | ✅ (si assigné) |  ✅   |   —    |
| `PUT /jobs/{id}/complete`        | ✅ (si assigné) |  ✅   |   —    |
| `POST /jobs/{id}/photos`         | ✅ (si assigné) |  ✅   |   —    |
| `GET /jobs/{id}/report/download` |       ✅        |  ✅   |   —    |
| `GET /review/{token}`            |        —        |   —   |   ✅   |
| `POST /review/{token}/submit`    |        —        |   —   |   ✅   |
| `GET/POST/PUT /admin/*`          |        —        |  ✅   |   —    |

---

> **Document mis à jour le 03/06/2026**
> **Version :** 3.0 (Refonte MVP)
