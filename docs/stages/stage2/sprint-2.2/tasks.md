# Sprint 2.2 : Rapport PDF + Avis client (Semaine 3, Jeu-Ven)

> **Durée :** 2 jours | **Points :** 33 | **Tâches :** 9 (INT-29 à INT-37)

---

## INT-29 — Génération PDF rapport (WeasyPrint + template HTML) (8 pts)

**User Story**  
En tant que **technicien**,  
Je veux **générer automatiquement un rapport PDF de l'intervention**  
Afin de **le remettre au client ou l'archiver**.

**Acceptance Criteria**

- [x] Installer WeasyPrint dans `requirements.txt`
- [x] Créer le template HTML du rapport : `backend/app/exporters/report_template.html`
- [x] Générer le PDF via `weasyprint.HTML(string=html).write_pdf()`
- [x] Le rapport inclut :
  - En-tête : titre du job, date, technicien
  - Client : nom, adresse, téléphone
  - Checklist pré/post (items cochés/non cochés)
  - Photos avant/après (intégrées en base64)
  - Matériaux utilisés (nom + quantité)
  - Observations
  - Signature / pied de page
- [x] Rapport stocké en mémoire (bytes), pas sur disque
- [x] Jinja2 pour le templating HTML

**Technical Notes**

- Fichier : `backend/app/exporters/report.py` — `ReportExporter` class
- Template : `backend/app/exporters/report_template.html` (HTML + CSS inline pour PDF)
- Jinja2 : `from jinja2 import Template`
- Photos : inclure les thumbnails ou les chemins absolus
- `weasyprint.HTML(string=html).write_pdf()` retourne des bytes

---

## INT-30 — `GET /jobs/{id}/report/download` (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **télécharger le rapport PDF d'un job**  
Afin de **le partager avec le client**.

**Acceptance Criteria**

- [x] `GET /api/v1/jobs/{job_id}/report/download` → retourne le PDF (`Content-Type: application/pdf`)
- [x] Si le rapport n'a pas encore été généré, le générer à la volée
- [x] Nom de fichier : `rapport-intervention-{id}.pdf`
- [x] Authentification requise
- [x] 404 si job inexistant

**Technical Notes**

- Router : `backend/app/api/v1/reports.py` (nouveau)
- Response : `StreamingResponse` ou `Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": ...})`
- `Content-Disposition: attachment; filename="rapport-intervention-{id}.pdf"`
- Ajouter le router dans `main.py`

---

## INT-31 — Modèle `Review` + migration (2 pts)

**User Story**  
En tant que **développeur backend**,  
Je veux **créer le modèle `Review` et sa migration**  
Afin de **recueillir les avis clients via un lien public**.

**Acceptance Criteria**

- [x] Modèle `Review` : id, job_id (FK UNIQUE), rating (1-5), comment, reviewer_name, share_token (UUID), share_token_expires_at, submitted_at, created_at
- [x] `job_id` UNIQUE (un seul avis par job)
- [x] `share_token` VARCHAR(64) UNIQUE (généré automatiquement)
- [x] FK `job_id` → job.id (ON DELETE CASCADE)
- [x] Index sur `share_token`
- [x] Migration générée et appliquée
- [x] Ajouter la relation `job.review` dans `models/job.py` (débloque TD-B003 + TD-B006)

> **Note** : `share_token_expires_at` est une colonne du modèle mais sa valeur est fixée dans INT-34 (à la complétion du job).

**Technical Notes**

- Fichier : `backend/app/models/review.py`
- `share_token` généré via `secrets.token_urlsafe(32)` ou `uuid.uuid4().hex`
- Validation `rating` : must be >= 1 and <= 5

---

## INT-32 — `GET /review/{share_token}` (public, no auth) (2 pts)

**User Story**  
En tant que **client**,  
Je veux **ouvrir le lien d'avis que le technicien m'a envoyé**  
Afin de **donner mon avis sur l'intervention**.

**Acceptance Criteria**

- [x] `GET /api/v1/review/{share_token}` — endpoint **public** (pas d'authentification)
- [x] Retourne les infos du job (titre, date complétion) + technicien
- [x] Retourne `already_reviewed: bool`
- [x] 404 si token invalide ou expiré
- [x] Le token expire après 30 jours

**Technical Notes**

- Router : `backend/app/api/v1/reviews.py` (public + auth mix)
- Vérifier `share_token_expires_at` > now avant de retourner les données
- `ReviewService.get_review_by_token(token)`

---

## INT-33 — `POST /review/{share_token}/submit` (public) (3 pts)

**User Story**  
En tant que **client**,  
Je veux **soumettre mon avis (note + commentaire)**  
Afin de **donner mon feedback au technicien**.

**Acceptance Criteria**

- [x] `POST /api/v1/review/{share_token}/submit` — endpoint **public**
- [x] Body : `{ "rating": 4, "comment": "Travail propre", "reviewer_name": "M. Dupont" }`
- [x] Validation : rating 1-5 requis
- [x] `reviewer_name` optionnel
- [x] Retourne 200 : `{ "message": "Merci pour votre avis !" }`
- [x] 404 si token invalide/expiré
- [x] 400 si déjà soumis (already_reviewed)
- [x] Enregistre `submitted_at = now`

**Technical Notes**

- Même router que INT-32
- Vérifier `review.submitted_at is None` avant de permettre la soumission

---

## INT-34 — Génération `share_token` automatique à la complétion (2 pts)

**User Story**  
En tant que **technicien**,  
Je veux **que le lien d'avis soit automatiquement créé quand je termine un job**  
Afin de **ne pas avoir à le faire manuellement**.

**Acceptance Criteria**

- [x] Dans `PUT /api/v1/jobs/{id}/complete` → créer une `Review` avec `share_token` automatiquement
- [x] `share_token` = UUID unique
- [x] `share_token_expires_at` = `completed_at + 30 jours`
- [x] `JobCompleteResponse` étendu avec : `report_url`, `review_share_token`, `review_share_url`
- [x] Mettre à jour le schéma `JobCompleteResponse` dans `schemas/job.py`

**Technical Notes**

- Modifier `JobService.complete_job()` pour créer la review après le changement de statut
- `secrets.token_urlsafe(32)` ou `uuid.uuid4()` pour le token
- `review_share_url` = `/review/{share_token}`
- `report_url` = `/api/v1/jobs/{id}/report/download`

---

## INT-35 — Frontend : `ReportPreviewPage` (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **visualiser le rapport PDF avant de le partager**  
Afin de **vérifier que tout est correct**.

**Acceptance Criteria**

- [x] Onglet "Rapport" dans `JobDetailPage` devient actif
- [x] Affiche un `<iframe>` avec le PDF intégré (via blob URL + auth fetch)
- [x] Bouton "📥 Télécharger le PDF" → fetch blob + anchor.click()
- [x] Si le job n'est pas terminé : message "Rapport disponible après complétion"
- [x] États loading/error

**Technical Notes**

- Fichier : `frontend/src/pages/JobDetailPage.vue` (modifier onglet Rapport)
- PDF en iframe : `<iframe :src="reportUrl" class="pdf-preview" />` avec `width=100%, height=500px`
- `reportUrl` = `/api/v1/jobs/${job.id}/report/download` avec token dans l'URL ou header
- Option : utiliser `<object>` ou `<embed>` au lieu de `<iframe>` selon compatibilité

---

## INT-36 — Frontend : `ReviewPage` publique (star rating + commentaire) (5 pts)

**User Story**  
En tant que **client**,  
Je veux **noter l'intervention et laisser un commentaire**  
Afin de **donner mon avis simplement, sans création de compte**.

**Acceptance Criteria**

- [x] Page publique (no auth) affichée quand le client ouvre le lien `/review/{token}`
- [x] Appel API `GET /api/v1/review/{share_token}` au chargement
- [x] Affiche les infos du job (titre, date, technicien)
- [x] Formulaire : star rating 1-5 (PrimeVue Rating) + champ commentaire (textarea) + nom optionnel
- [x] Bouton "Envoyer mon avis" → `POST /api/v1/review/{share_token}/submit`
- [x] Si déjà soumis : message "Merci, votre avis a bien été enregistré"
- [x] Si token invalide/expiré : message "Ce lien n'est plus valable"
- [x] Design épuré, pas de BottomNav (`meta: { hideNav: true }`)

**Technical Notes**

- Fichier : `frontend/src/pages/ReviewPage.vue` (nouveau)
- Route : `{ path: '/review/:token', name: 'Review', component: () => import('@/pages/ReviewPage.vue'), meta: { guest: true } }` (pas de `requiresAuth`)
- Appel API : `api.get<ReviewData>('/review/' + token)` (pas de token auth)
- PrimeVue Rating : `<Rating v-model="rating" :stars="5" />`
- Si `already_reviewed` → template de remerciement
- CSS spécifique : centré, pas de padding bottom (pas de BottomNav)

---

## INT-37 — Tests API : photos, matériaux, rapport, avis (5 pts)

**User Story**  
En tant que **développeur**,  
Je veux **couvrir les nouveaux endpoints avec des tests API**  
Afin de **garantir la non-régression et valider le comportement**.

**Acceptance Criteria**

- [x] Tests upload photo : multipart, thumbnail, validation taille/format (6 tests)
- [x] Tests suppression photo : fichier supprimé, double suppression (2 tests)
- [x] Tests CRUD matériaux : ajout, modification, suppression (5 tests)
- [x] Tests génération rapport : PDF retourné, job non terminé = erreur (4 tests)
- [x] Tests avis public : GET token invalide/valide, POST soumission, double soumission (9 tests)
- [x] Tests intégration : complete_job crée review + share_token (3 tests)
- [x] Coverage ≥ 60% (65% atteint sur app)

**Technical Notes**

- Fichier : `backend/tests/` (à créer si inexistant)
- Utiliser `pytest` + `httpx.AsyncClient` pour les tests API
- `pytest --cov=app tests/` pour la couverture

---

## Tests Cases Sprint 2.2

Les tests cases détaillés sont dans `test-cases.json`.
