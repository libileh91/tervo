# Fix — Checklist : auto-création + items custom

> **Sprint :** 3.1 — correctif du Sprint 1.3 (INT-18, INT-20)
> **Date :** 26/06/2026

---

## Problèmes corrigés

### 1. Checklist vide sur les jobs du seed
Les jobs créés via `app/seed.py` n'appelaient pas `create_default_items()` → pas d'items checklist → page inspection vide.

**Fix :** `get_items()` dans `ChecklistService` auto-crée les 5 items par défaut si la liste est vide.

```python
async def get_items(self, job_id: int) -> list:
    items = await self.repo.get_items(job_id)
    if not items:
        await self.create_default_items(job_id)
        items = await self.repo.get_items(job_id)
    return items
```

---

### 2. Impossibilité d'ajouter des items custom
La checklist était figée à 5 items (3 pré + 2 post). Aucun endpoint pour en ajouter.

**Fix backend :** `POST /jobs/{id}/checklist`
```python
@router.post("/{job_id}/checklist", response_model=ChecklistItemRef, status_code=201)
async def create_checklist_item(job_id, body, current_user, db):
    service = ChecklistService(db)
    item = await service.add_custom_item(job_id, body.get("label"), body.get("category", "post_intervention"))
    return ChecklistItemRef.model_validate(item)
```

**Fix frontend :** Champ texte + bouton "Ajouter" dans InspectionPage
```vue
<InputText v-model="newItemLabel" placeholder="Ajouter un item..." @keyup.enter="addCustomItem" />
<Button label="Ajouter" icon="pi pi-plus" @click="addCustomItem" />
```

---

### 3. Bouton "Terminer" bloqué sur checklist vide
`allChecked` retournait `false` quand `items.length === 0` → bouton toujours désactivé.

**Fix :** Checklist vide = `true` (pas d'items à vérifier)

```typescript
const allChecked = computed(() => {
    if (!items.value || items.value.length === 0) return true;  // ← corrigé
    return items.value.every(...);
});
```

---

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `api/v1/checklist.py` | Ajout `POST` endpoint |
| `services/checklist.py` | `add_custom_item()` + auto-création dans `get_items()` |
| `pages/InspectionPage.vue` | `allChecked` fix + champ "Ajouter" + import `InputText` |
