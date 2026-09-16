# Fix : Upload photo → 400 + photo invisible après upload

## Contexte

Deux bugs en cascade sur l'upload de photos :

1. **POST `/api/v1/jobs/{id}/photos`** retournait `400 Bad Request`
2. Une fois l'upload réparé, la photo **n'apparaissait pas** dans l'onglet Photos après upload (« Aucune photo pour l'instant. »)

---

## Bug 1 — 400 Bad Request (3 causes racines)

### 1a. Dépendance Pillow manquante

`from PIL import Image` était placé dans un `try/except Exception`. Pillow n'était **pas dans `requirements.txt`** et pas installé dans le venv.

L'`import` échouait silencieusement → le `except` attrapait tout → supprimait le fichier original et renvoyait un message « Impossible de générer la miniature. Vérifiez le fichier. » trompeur.

**Fix** :

- Ajout de `Pillow>=10.0.0` dans `backend/requirements.txt`
- Installation : `pip install Pillow` (⚠️ bien utiliser le pip du venv : `.venv/bin/pip install Pillow`)
- L'import PIL est maintenant dans un `try/except ImportError` **séparé**, avec un message clair (HTTP 500) et **sans supprimer le fichier original**

```python
# Import séparé — ne supprime PAS le fichier si la lib manque
try:
    from PIL import Image
except ImportError:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Pillow n'est pas installé.",
    )
```

### 1b. Types MIME trop restrictifs

`ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}` uniquement.

Sur mobile (Android/Chrome), les photos de la galerie sont souvent en `image/webp`. Les iPhones utilisent `image/heic`.

**Fix** : ajout de `image/webp` + fallback si `content_type` est `None`:

```python
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Certains mobiles ne fournissent pas le content_type
content_type = file.content_type or "application/octet-stream"
```

### 1c. Thumbnail échouait sur les images avec transparence (RGBA → JPEG)

Un PNG avec canal alpha (`mode="RGBA"`) ou un WebP transparent plantait à `img.save(thumb_path, "JPEG")` car JPEG ne supporte pas l'alpha.

**Fix** : conversion explicite RGBA → RGB avec fond blanc avant de sauvegarder :

```python
if img.mode in ("RGBA", "LA", "P", "PA"):
    background = Image.new("RGB", img.size, (255, 255, 255))
    background.paste(
        img, mask=img.split()[-1] if img.mode in ("RGBA", "PA") else None
    )
    img = background
elif img.mode != "RGB":
    img = img.convert("RGB")
```

Le paramètre `mask` conserve la transparence lors du collage sur fond blanc.

### 1d. Un seul `<input>` pour les deux boutons (frontend)

Les deux boutons « Prendre une photo » et « Choisir dans la galerie » utilisaient **le même** `<input type="file">` avec l'attribut `capture="environment"`. Résultat : les deux ouvraient l'appareil photo.

**Fix** : deux `<input>` séparés, chacun avec son `ref` et sa fonction :

```html
<!-- Caméra (capture=environment) -->
<input
  ref="cameraInputRef"
  type="file"
  accept="image/jpeg,image/png,image/webp"
  capture="environment"
  class="hidden-input"
  @change="onFileSelected"
/>

<!-- Galerie (sans capture) -->
<input
  ref="galleryInputRef"
  type="file"
  accept="image/jpeg,image/png,image/webp"
  class="hidden-input"
  @change="onFileSelected"
/>
```

```ts
function triggerUpload(category: string) {
  uploadCategory.value = category;
  cameraInputRef.value?.click();
}

function triggerGalleryUpload(category: string) {
  uploadCategory.value = category;
  galleryInputRef.value?.click();
}
```

---

## Bug 3 — Icône « image cassée » (photo non servie via HTTP)

L'upload retournait 201, le détail du job contenait les bonnes URLs (`/uploads/photos/xxx.jpg`), mais le navigateur affichait l'icône « image cassée ».

**Cause** : les photos étaient écrites sur le disque (`backend/uploads/photos/`) mais il n'y avait **aucun endpoint HTTP** pour les servir.

**Fix** : montage du dossier en static files FastAPI + proxy Vite :

### Backend — `main.py`

```python
from fastapi.staticfiles import StaticFiles

app.mount(
    settings.UPLOAD_URL,         # → "/uploads"
    StaticFiles(directory=settings.UPLOAD_DIR),  # → "backend/uploads/"
    name="uploads",
)
```

`app.mount()` attache un dossier du disque à un chemin URL. Toute requête `GET /uploads/photos/xxx.jpg` est servie directement depuis le système de fichiers.

### Frontend — `vite.config.ts`

```ts
proxy: {
  "/api":     { target: "http://localhost:8000", changeOrigin: true },
  "/uploads": { target: "http://localhost:8000", changeOrigin: true },
}
```

Sans ce proxy, le navigateur chercherait `/uploads/photos/xxx.jpg` sur le port 5173 (Vite) au lieu du port 8000 (FastAPI).

### Test

```bash
curl -sI http://localhost:8000/uploads/photos/0166de30....jpg
# → HTTP/1.1 200 OK
# → content-type: image/jpeg
```

---

## Bug 2 — Photo invisible après upload (3 causes racines)

L'upload renvoyait 201 ✅, toast « Photo ajoutée » ✅, mais l'écran affichait encore « Aucune photo pour l'instant. ».

### 2a. `JobResponse` n'avait pas de champ `photos`

Le schéma Pydantic `JobResponse` n'incluait pas les photos (ni les matériaux). Même avec le refetch, la réponse `GET /jobs/{id}` ne contenait pas les photos.

**Fix** : ajout de `PhotoRef` + `photos` et `materials` dans `JobResponse` :

```python
class PhotoRef(BaseModel):
    id: int
    category: str
    file_url: str
    thumbnail_url: str | None = None
    taken_at: datetime | None = None
    model_config = {"from_attributes": True}

class JobResponse(BaseModel):
    ...
    photos: list[PhotoRef] = []
    materials: list[MaterialResponse] = []
```

### 2b. Pas de propriétés `file_url` / `thumbnail_url` sur le modèle `JobPhoto`

Le modèle ORM stocke `file_path` et `thumbnail_path` (chemins disque). Le frontend attend `file_url` et `thumbnail_url` (URLs publiques).

**Fix** : ajout de propriétés calculées sur le modèle :

```python
class JobPhoto(Base):
    file_path = Column(String(500))
    thumbnail_path = Column(String(500), nullable=True)

    @property
    def file_url(self) -> str:
        return f"/uploads/photos/{Path(self.file_path).name}"

    @property
    def thumbnail_url(self) -> str | None:
        if self.thumbnail_path:
            return f"/uploads/photos/{Path(self.thumbnail_path).name}"
        return None
```

Les `@property` sont accessibles par Pydantic avec `from_attributes = True`.

### 2c. `selectinload` manquant dans le repository

`JobRepository.get_by_id()` et `list_all()` ne faisaient pas de `selectinload(Job.photos)` ni `selectinload(Job.materials)`. Les relations n'étaient donc pas chargées depuis la base.

**Fix** : ajout des deux `selectinload` dans les options des requêtes :

```python
query = select(Job).options(
    selectinload(Job.client),
    selectinload(Job.technician),
    selectinload(Job.checklist_items),
    selectinload(Job.photos),       # ← NOUVEAU
    selectinload(Job.materials),    # ← NOUVEAU
)
```

### 2d. `MaterialResponse` défini après `JobResponse` (ordre Python)

`MaterialResponse` était défini **après** `JobResponse` qui l'utilisait. Python interdit les références à des classes non encore définies.

**Fix** : déplacement de `MaterialResponse` avant `JobResponse` dans le fichier `schemas/job.py`.

---

## Bug 4 — Layout photo : mauvaise visibilité + encombrement

### Problèmes remontés

1. Les miniatures (120px) étaient trop petites → mauvaise visibilité
2. La grille 2 colonnes fixes devenait encombrante avec beaucoup de photos → scroll long
3. Impossible de voir une photo en grand → pas de zoom / galerie

### Correctifs appliqués (`frontend/src/pages/JobDetailPage.vue`)

| Avant                                           | Après                                                       |
| ----------------------------------------------- | ----------------------------------------------------------- |
| Miniature 120px                                 | **160px** — plus visible                                    |
| 2 colonnes fixes                                | **2 colonnes** par défaut, **3 colonnes** si ≥ 3 photos     |
| Pas de clic possible                            | **Clic → Dialog plein écran** avec l'image en taille réelle |
| `@click` sur la carte déclenchait `deletePhoto` | `@click.stop` sur le bouton supprimer — pas de conflit      |
| Compteur absent                                 | **📸 Avant (3)** — affiche le nombre de photos              |
| Supprimer toujours visible                      | `opacity: 0.85` — plus discret                              |
| Aucun feedback tactile                          | `scale(0.96)` au clic — effet de pression natif             |

### Fonctionnement du preview Dialog

```vue
<Dialog
    v-model:visible="showPreview"
    :header="null"        <!-- pas de header pour économiser l'espace -->
    modal
    dismissableMask        <!-- fermeture en cliquant à côté -->
    :style="{ maxWidth: '95vw', maxHeight: '90vh' }"
    @hide="previewPhoto = null"
>
    <img v-if="previewPhoto" :src="previewPhoto" class="preview-image" />
</Dialog>
```

Points clés :

- `dismissableMask` = clic en dehors de l'image → ferme le Dialog (mobile friendly)
- `maxWidth: 95vw` = s'adapte à tous les écrans (pas de dépassement)
- `maxHeight: 90vh` = laisse une marge en haut/bas
- `:header="null"` = pas de barre de titre, tout l'espace pour l'image
- `@click.stop` sur le bouton supprimer évite d'ouvrir le Dialog quand on clique sur la corbeille

### Grille adaptative

```css
/* 2 colonnes par défaut */
.photo-grid {
  grid-template-columns: repeat(2, 1fr);
}
/* 3 colonnes automatique si ≥ 3 photos */
.photo-grid--many {
  grid-template-columns: repeat(3, 1fr);
}
```

Le passage à 3 colonnes réduit l'encombrement vertical quand le technicien a pris plusieurs photos.

---

## Validation

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tech1","password":"password123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Upload (cette fois sans 400)
curl -s -X POST "http://localhost:8000/api/v1/jobs/13/photos" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/photo.jpg;type=image/jpeg" \
  -F "category=avant"
# → 201 ✅

# 3. Vérifier que les photos apparaissent dans le détail du job
curl -s "http://localhost:8000/api/v1/jobs/13" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
    print(f'Photos: {len(d.get(\"photos\",[]))}'); \
    print(f'Materials: {len(d.get(\"materials\",[]))}'); \
    [print(f'  - {p[\"category\"]}: {p[\"thumbnail_url\"]}') for p in d.get('photos',[])]"
# → Photos: 7, Materials: 2 ✅
```

---

## Fichiers modifiés

| Fichier                                  | Bug        | Changement                                                                        |
| ---------------------------------------- | ---------- | --------------------------------------------------------------------------------- |
| `backend/requirements.txt`               | 1a         | Ajout `Pillow>=10.0.0`                                                            |
| `backend/app/services/photo.py`          | 1a, 1b, 1c | Import PIL séparé (500), `image/webp`, fallback content_type, conversion RGBA→RGB |
| `frontend/src/pages/JobDetailPage.vue`   | 1d         | Deux inputs (camera + gallery) + `triggerGalleryUpload()`                         |
| `backend/app/schemas/job.py`             | 2a, 2d     | Ajout `PhotoRef`, `photos`/`materials` dans `JobResponse`, réordonnancement       |
| `backend/app/models/job_photo.py`        | 2b         | Propriétés `file_url`, `thumbnail_url`                                            |
| `backend/app/repositories/job.py`        | 2c         | `selectinload(Job.photos)` + `selectinload(Job.materials)`                        |
| `backend/app/main.py`                    | 3          | `app.mount(UPLOAD_URL, StaticFiles(...))`                                         |
| `frontend/vite.config.ts`                | 3          | Proxy `/uploads` → backend                                                        |
| `frontend/src/pages/JobDetailPage.vue`   | 4          | Miniatures 160px, grille 2→3 colonnes, Dialog preview, compteur                   |
| `docs/stages/stage2/sprint-2.1/tasks.md` | —          | Mise à jour critères « JPEG, PNG, WebP » + « Servir fichiers » ✅                 |

---

## Commandes utiles

```bash
# Installer Pillow dans le venv
cd backend/
.venv/bin/pip install Pillow

# Lister les photos uploadées
ls -la backend/uploads/photos/

# Vérifier que le modèle expose les URLs
.venv/bin/python -c "
from app.models.job_photo import JobPhoto
print([p for p in dir(JobPhoto) if 'url' in p.lower()])
"
```
