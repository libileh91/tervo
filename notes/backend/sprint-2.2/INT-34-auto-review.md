# INT-34 : Création automatique du Review à la complétion du job

## Contexte

Quand un technicien complète un job (`PUT /jobs/{id}/complete`), un `Review`
avec `share_token` est automatiquement créé en DB. Le client pourra ensuite
noter l'intervention via le lien public (INT-32/33).

---

## Changements

### 1. Schéma `JobCompleteResponse` — 3 nouveaux champs optionnels

```python
class JobCompleteResponse(BaseModel):
    id: int
    status: str
    completed_at: datetime
    duration_minutes: int
    report_url: str | None = None           # ← nouveau
    review_share_token: str | None = None   # ← nouveau
    review_share_url: str | None = None     # ← nouveau
```

### 2. Service `JobService.complete_job()` — création du Review

Après avoir mis le job à `terminé`, on crée un `Review` via `ReviewRepository` :

```python
review_repo = ReviewRepository(self.repo.db)
share_token = uuid.uuid4().hex
expires_at = job.completed_at + timedelta(days=30)

await review_repo.create({
    "job_id": job.id,
    "rating": 5,                    # valeur par défaut, écrasée par le client
    "share_token": share_token,
    "share_token_expires_at": expires_at.replace(tzinfo=None),
})
```

### 3. Retour enrichi

```python
return JobCompleteResponse(
    ...
    report_url=f"/api/v1/jobs/{job.id}/report/download",
    review_share_token=share_token,
    review_share_url=f"/review/{share_token}",
)
```

---

## Test

```bash
# Compléter un job (après l'avoir créé + démarré + checklist cochée)
curl -s -X PUT "http://localhost:8000/api/v1/jobs/14/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"observations":"Test ok"}'
# → {
#     "report_url": "/api/v1/jobs/14/report/download",
#     "review_share_token": "8a51f1623329412a963af9936f9deb90",
#     "review_share_url": "/review/8a51f1623329412a963af9936f9deb90"
#   }

# Vérifier que le review est accessible publiquement
curl -s "http://localhost:8000/api/v1/review/8a51f1623329412a963af9936f9deb90"
# → { "job": { "title": "Test INT-34 auto review", ... }, "already_reviewed": false }
```

---

## Fichiers modifiés

| Fichier                       | Changement                                                |
| ----------------------------- | --------------------------------------------------------- |
| `backend/app/schemas/job.py`  | 3 champs ajoutés à `JobCompleteResponse`                  |
| `backend/app/services/job.py` | `import uuid`, création auto du `Review` après complétion |

## Dépendances débloquées

- **INT-32/33** : les endpoints publics ont désormais des données à servir
- **TD-B006** : ✅ complètement résolu (modèle + endpoints + création auto)

---

## Récapitulatif INT-34 ✅

### Changements

| Fichier                       | Changement                                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| `backend/app/schemas/job.py`  | +3 champs optionnels dans `JobCompleteResponse` : `report_url`, `review_share_token`, `review_share_url` |
| `backend/app/services/job.py` | `import uuid` + création `Review` via `ReviewRepository.create()` après le changement de statut          |

### Logique

```
PUT /jobs/{id}/complete
  → job.status = 'terminé', completed_at = now
  → share_token = uuid4().hex
  → expires_at = completed_at + 30 jours
  → ReviewRepository.create({job_id, rating=5, share_token, share_token_expires_at})
  → retourne { report_url, review_share_token, review_share_url }
```

### Test

```
PUT /jobs/14/complete → {
  "report_url": "/api/v1/jobs/14/report/download",
  "review_share_token": "8a51f1623329412a963af9936f9deb90",
  "review_share_url": "/review/8a51f1623329412a963af9936f9deb90"
}

GET /review/8a51f1623329412a963af9936f9deb90 → 200 ✅
```

### Dépendances

- **TD-B006** : ✅ résolu complètement (modèle INT-31 + GET INT-32 + POST INT-33 + création auto INT-34)
