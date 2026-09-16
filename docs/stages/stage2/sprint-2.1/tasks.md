# Sprint 2.1 : Photos & Matériaux (Semaine 3, Lun-Mer)

> **Durée :** 3 jours | **Points :** 23 | **Tâches :** 7 (INT-22 à INT-28)

---

## INT-22 — Modèle `JobPhoto` + migration + stockage fichiers (3 pts)

**User Story**  
En tant que **développeur backend**,  
Je veux **créer le modèle `JobPhoto` et la gestion de stockage**  
Afin de **pouvoir attacher des photos avant/après aux jobs**.

**Acceptance Criteria**

- [x] Modèle `JobPhoto` : id, job_id (FK), category ('avant', 'après'), file_path, thumbnail_path, taken_at
- [x] FK `job_id` → job.id (ON DELETE CASCADE)
- [x] Index sur `job_id`
- [x] Colonne `category` avec CHECK contrainte : 'avant', 'après'
- [x] Migration générée et appliquée
- [x] Configurer le dossier `backend/uploads/photos/` (créer si inexistant)
- [x] Configurer les URLs de serveur de fichiers via settings (UPLOAD_DIR, UPLOAD_URL)
- [x] Ajouter la relation `job.photos` dans `models/job.py` (débloque TD-B003 partiellement)

**Technical Notes**

- Fichier : `backend/app/models/job_photo.py`
- Fichiers stockés avec UUID : `{uuid}.jpg`, `thumb_{uuid}.jpg`
- Thumbnail : 300×300, généré côté serveur avec Pillow
- Ajouter `UPLOAD_DIR` et `UPLOAD_URL` dans `backend/app/config.py`
- Model : `from app.models.base import Base`

---

## INT-23 — `POST /jobs/{id}/photos` (multipart + thumbnail) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **uploader une photo avant/après sur un job**  
Afin de **documenter l'état de l'installation**.

**Acceptance Criteria**

- [x] `POST /api/v1/jobs/{job_id}/photos` accepte `multipart/form-data` (file + category)
- [x] Format accepté : JPEG, PNG, WebP, max 10 Mo
- [x] Génération automatique d'un thumbnail 300×300 avec Pillow
- [x] Stockage : `{UPLOAD_DIR}/photos/{uuid}.jpg` + `{UPLOAD_DIR}/photos/thumb_{uuid}.jpg`
- [x] Retourne 201 : `{ id, category, file_url, thumbnail_url, taken_at }`
- [x] Validation : job_id doit exister (404)
- [x] Authentification requise + vérification d'assignation (403)
- [x] Servir les fichiers via un endpoint dédié (StaticFiles) ou 1Panel (P3)

**Technical Notes**

- Router : `backend/app/api/v1/photos.py` (nouveau)
- Service : `backend/app/services/photo.py` (nouveau) avec `upload_photo()`
- Repository : `backend/app/repositories/photo.py` (nouveau)
- Utiliser `UploadFile` de FastAPI pour le multipart
- Thumbnail : `PIL.Image.open() → thumbnail((300, 300)) → save()`
- Nom fichier : `uuid.uuid4().hex + '.jpg'` — pas de doublon possible
- Ajouter le router dans `main.py`

---

## INT-24 — `DELETE /jobs/{id}/photos/{id}` (2 pts)

**User Story**  
En tant que **technicien**,  
Je veux **supprimer une photo que j'ai uploadée**  
Afin de **corriger une erreur ou remplacer une photo**.

**Acceptance Criteria**

- [x] `DELETE /api/v1/jobs/{job_id}/photos/{id}` → supprime le fichier + thumbnail + entrée DB
- [x] Retourne 204
- [x] 404 si photo inexistante
- [x] Authentification requise + vérification d'assignation (403)
- [x] Suppression physique des fichiers sur le disque

**Technical Notes**

- `os.remove(file_path)` et `os.remove(thumbnail_path)` avant suppression DB
- Gérer le cas où le fichier n'existe plus sur disque (graceful delete)

---

## INT-25 — Modèle `Material` + migration (2 pts)

**User Story**  
En tant que **développeur backend**,  
Je veux **créer le modèle `Material` et sa migration**  
Afin de **pouvoir lister les matériaux utilisés dans un job**.

**Acceptance Criteria**

- [x] Modèle `Material` : id, job_id (FK), name, quantity, position
- [x] FK `job_id` → job.id (ON DELETE CASCADE)
- [x] Index sur `job_id`
- [x] Migration générée et appliquée
- [x] `quantity` est un VARCHAR (texte libre : "1", "0.5 kg", "2 m")
- [x] Ajouter la relation `job.materials` dans `models/job.py` (débloque TD-B003)

**Technical Notes**

- Fichier : `backend/app/models/material.py`
- `position` = INTEGER, default=0 (pour l'ordre d'affichage)

---

## INT-26 — `GET/POST /jobs/{id}/materials` + `PUT/DELETE /jobs/{id}/materials/{id}` (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **gérer la liste des matériaux utilisés pendant l'intervention**  
Afin de **les inclure dans le rapport final**.

**Acceptance Criteria**

- [x] `GET /api/v1/jobs/{job_id}/materials` — liste des matériaux (triés par position)
- [x] `POST /api/v1/jobs/{job_id}/materials` — ajouter un matériau → 201
- [x] `PUT /api/v1/jobs/{job_id}/materials/{id}` — modifier quantité/nom
- [x] `DELETE /api/v1/jobs/{job_id}/materials/{id}` — supprimer → 204
- [x] Body POST/PUT : `{ "name": "Filtre HEPA", "quantity": "1" }`
- [x] Authentification requise + vérification d'assignation (403)

**Technical Notes**

- Router : `backend/app/api/v1/materials.py` (nouveau)
- Service/Repository : `MaterialService`, `MaterialRepository`
 - Réutiliser le pattern `_check_assignation` de `checklist.py`
- Ajouter le router dans `main.py`

---

## INT-27 — Frontend : Upload photo (appareil natif + galerie) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **prendre une photo depuis mon téléphone ou la galerie**  
Afin de **documenter l'état avant/après de l'installation**.

**Acceptance Criteria**

- [x] Onglet "Photos" dans `JobDetailPage` devient actif (plus `:disabled`)
- [x] Appel API `GET /api/v1/jobs/{id}` → `photos` inclus (après INT-22/23)
- [x] Bouton "📷 Prendre une photo" → appareil natif (`capture="environment"`)
- [x] Bouton "🖼 Choisir dans la galerie" → file picker standard
- [x] Tag automatique 'avant' ou 'après' selon l'étape du workflow
- [x] Upload via `FormData` multipart → `api.upload()` dans `api/client.ts`
- [x] Thumbnail preview après upload
- [x] Miniatures affichées par catégorie (avant / après)
- [x] Bouton "🗑 Supprimer" sur chaque photo
- [x] Loading spinner pendant l'upload

**Technical Notes**

- Fichier : `frontend/src/pages/JobDetailPage.vue` (modifier onglet Photos)
- API : ajouter `photosApi` dans `api/client.ts` avec méthode `upload(file, jobId, category)`
- Upload native : `<input type="file" accept="image/jpeg,image/png" capture="environment" />`
- FormData : `const fd = new FormData(); fd.append('file', file); fd.append('category', category);`
- Utiliser `api.request` avec `Content-Type: multipart/form-data` (surcharger le Content-Type par défaut)
- Invalider `['job', jobId]` après upload/suppression

---

## INT-28 — Frontend : `MaterialsForm` (ajout/suppression dynamique) (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **saisir les matériaux utilisés pendant l'intervention**  
Afin de **les inclure dans le rapport sans double saisie**.

**Acceptance Criteria**

- [x] Onglet "Matériaux" dans `JobDetailPage` devient actif
- [x] Liste des matériaux existants (nom + quantité)
- [x] Bouton "➕ Ajouter un matériau" → nouvelle ligne éditable
- [x] Bouton "✕ Supprimer" par ligne
- [x] Sauvegarde : appel API `POST /api/v1/jobs/{id}/materials`
- [x] Modification inline : `PUT /api/v1/jobs/{id}/materials/{id}`
- [x] Suppression : `DELETE /api/v1/jobs/{id}/materials/{id}` avec confirmation optionnelle
- [x] Invalider `['job', jobId]` après mutation

**Technical Notes**

- Fichier : `frontend/src/pages/JobDetailPage.vue` (modifier onglet Matériaux)
- API : ajouter `materialsApi` dans `api/client.ts` (`list`, `add`, `update`, `remove`)
- Formulaire inline : `InputText` pour nom + `InputText` pour quantité + bouton validation
- Pas de Dialog pour suppression matériau (action rapide, confirmation toast suffit)

---

## Tests Cases Sprint 2.1

Les tests cases détaillés sont dans `test-cases.json`.
