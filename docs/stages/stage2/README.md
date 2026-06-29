# Phase 2 : Photos, Rapport, Avis (Semaine 3)

> **Objectif :** Upload photos avant/après, saisie matériaux, génération PDF rapport, avis client public.

---

## Vue d'ensemble

| Sprint    | Période            | Tâches          | Points totaux |
| --------- | ------------------ | --------------- | ------------- |
| 2.1       | Semaine 3, Lun-Mer | INT-22 à INT-28 | 23            |
| 2.2       | Semaine 3, Jeu-Ven | INT-29 à INT-37 | 33            |
| **Total** | **5 jours**        | **16 tâches**   | **56 pts**    |

> **Note :** Sprint 2.3 (INT-38 à INT-42) déplacé vers Phase 4 (Sprint 4.1 — Frontend mobile).

---

## Dépendances

```
Sprint 2.1 (Photos & Matériaux) ← dépend de Phase 1 (modèle Job, checklist)
    ↓
Sprint 2.2 (Rapport PDF + Avis) ← dépend de Sprint 2.1 (photos, matériaux)
```

---

## Critères de succès Phase 2 ✅

- [x] Upload photos avant/après avec thumbnails (max 10 Mo, JPEG/PNG)
- [x] Saisie matériaux (ajout/suppression dynamique)
- [x] Rapport PDF téléchargeable (WeasyPrint)
- [x] Avis client via lien public sans auth (note 1-5 + commentaire)
- [x] Tests API ≥ 60%
- [ ] ~~Application responsive mobile~~ → déplacé Phase 4

---

## Équipe Phase 2

| Rôle          | Allocation | Focus                                                        |
| ------------- | ---------- | ------------------------------------------------------------ |
| Dev Backend   | 100%       | Modèles photo/material/review, upload, PDF, avis             |
| Dev Frontend  | 100%       | Upload photo natif, formulaire matériaux, pages rapport/avis |
| Dev Fullstack | 50%        | Tests (INT-37), support                                      |

**ETP :** 2.5

---

**Documents liés :**
- `docs/DAT/07-implementation-roadmap.md`
- `docs/DAT/specs/03-api-spec.md`
- `docs/DAT/05-data-model.md`
