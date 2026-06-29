# INT-21 — Validation checklist : messages détaillés + frontend

> **Objectif** : Améliorer la validation checklist + intégration frontend avec bouton Terminer
> **Stack** : Pytest + Vue Query + PrimeVue Tooltip

---

## 1. Tests unitaires backend

```bash
cd backend/
.venv/bin/python -m pytest tests/test_checklist_service.py -v
```

```
tests/test_checklist_service.py::test_all_checked PASSED
tests/test_checklist_service.py::test_some_unchecked PASSED
tests/test_checklist_service.py::test_only_pre_unchecked PASSED
tests/test_checklist_service.py::test_only_post_unchecked PASSED
```

4 tests qui mockent `ChecklistRepository` pour tester `validate_all_checked()` :

```python
@pytest.mark.asyncio
async def test_some_unchecked(service):
    service.repo.count_unchecked_by_category = AsyncMock(
        return_value={"pre_intervention": 1, "post_intervention": 1}
    )
    result = await service.validate_all_checked(1)
    assert result["is_valid"] is False
    assert "pré-intervention" in result["errors"][0]
    assert "2 items non cochés" in result["detail"]
```

---

## 2. Frontend : bouton Terminer sur InspectionPage

```vue
<Button
  label="Terminer l'intervention"
  icon="pi pi-check-circle"
  severity="danger"
  fluid
  :disabled="!allChecked"
  v-tooltip="allChecked ? '' : 'Cochez tous les items de la checklist d\\'abord'"
  :loading="completing"
  @click="handleComplete"
/>
```

**Validation locale :**
```ts
const allChecked = computed(() => {
  if (!items.value || items.value.length === 0) return false
  return items.value.every(
    (i) => localChecked.value[i.id] ?? i.checked
  )
})
```

Bouton désactivé tant que tous les items ne sont pas cochés. Tooltip PrimeVue au survol.

---

## 3. Flow complet

```mermaid
flowchart TD
    A[InspectionPage] -->|Cocher tous les items| B{allChecked?}
    B -->|Non| C[Bouton Terminer désactivé<br/>+ tooltip rouge]
    B -->|Oui| D[Bouton Terminer activé]
    D -->|Clic| E[PUT /jobs/{id}/complete]
    E -->|200| F[Toast succès + invalidation cache]
    F --> G[Redirection JobDetailPage]
    E -->|400 (checklist incomplete)| H[Toast erreur]
```

---

## 4. Fichiers

| Fichier | Action |
|---------|--------|
| `backend/tests/test_checklist_service.py` | **Nouveau** — 4 tests unitaires |
| `frontend/src/main.ts` | Directive `Tooltip` enregistrée |
| `frontend/src/pages/InspectionPage.vue` | Bouton "Terminer" + `allChecked` computed + appel `PUT /complete` |

---

## 5. 🎉 Sprint 1.3 terminé !

## Flux test frontend complet

### Étape 1 : Se connecter
```
URL : http://localhost:5173
Login : tech1 / password123
```

### Étape 2 : Démarrer un job
```
Dashboard → voir les jobs du jour
ou /jobs → cliquer sur un job planifié → JobDetailPage
Cliquer "▶ Démarrer" → le job passe en "en_cours"
```

### Étape 3 : Aller dans la checklist
```
Sur JobDetailPage (job en_cours) → cliquer "📋 Checklist"
→ /jobs/{id}/inspection
```

### Étape 4 : Remplir la checklist
```
Section "🔍 Pré-intervention" : 3 items avec checkbox
Section "✅ Post-intervention" : 2 items avec checkbox
Cocher/décocher → instantané
Ajouter des notes si besoin
```

### Étape 5 : Sauvegarder
```
Cliquer "Sauvegarder" → toast vert + cache invalidé
(Le bouton "Terminer" reste désactivé si items non cochés)
```

### Étape 6 : Terminer
```
Cocher TOUS les items → bouton "Terminer" devient actif
Cliquer "Terminer" → PUT /jobs/{id}/complete
→ Redirection vers JobDetailPage (statut = "terminé")
```

### Étape 7 : Vérifier
```
Dashboard → compteur jobs_completed +1
/jobs → filtre "terminé" → job visible avec chip vert
/clients/{id} → jobs_count et last_job_date mis à jour
```
