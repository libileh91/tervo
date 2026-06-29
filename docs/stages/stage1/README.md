# Phase 1 : Core + Auth (Semaines 1-2)

> **Objectif :** Auth JWT + CRUD Clients + CRUD Jobs + workflow start/complete + checklist + dashboard.

---

## Vue d'ensemble

| Sprint | Période | Tâches | Points totaux |
|--------|---------|--------|---------------|
| 1.1 | Semaine 1, Lun-Mer | INT-00 à INT-07 | 23 |
| 1.2 | Semaine 1, Jeu-Ven | INT-08 à INT-16 | 39 |
| 1.3 | Semaine 2, Lun-Mer | INT-17 à INT-21 | 20 |
| **Total** | **10 jours** | **22 tâches** | **82 pts** |

---

## Dépendances

```
Sprint 1.1 (Base)
    ↓
Sprint 1.2 (Jobs)  ← dépend de Sprint 1.1 (modèle User, Client, Auth)
    ↓
Sprint 1.3 (Checklist)  ← dépend de Sprint 1.2 (modèle Job)
```

---

## Critères de succès Phase 1

- [ ] Auth JWT fonctionnelle (login, refresh, profil)
- [ ] CRUD Clients API opérationnel (création, modification, suppression, historique)
- [ ] CRUD Jobs + workflow start/complete opérationnel
- [ ] Checklist pré/post fonctionnelle (batch update, seed auto)
- [ ] Dashboard du jour (jobs du jour, timer)
- [ ] Navigation mobile (BottomNav, 4 onglets)
- [ ] Pages frontend : Login, Dashboard, JobList, JobDetail, ClientList, ClientDetail, Inspection

---

## Équipe Phase 1

| Rôle | Allocation | Focus |
|------|-----------|-------|
| Dev Backend | 100% | API, services, modèles, migrations |
| Dev Frontend | 100% | Composants Vue.js, routing, API calls |
| Dev Fullstack | 50% | Support back/front, CI init |

**ETP :** 2.5

---

## Risques Phase 1

| Risque | Prob. | Impact | Mitigation |
|--------|-------|--------|------------|
| Délai sprint 1.1 déborde | Faible | Moyen | Buffer sprint 1.2 (Jeu-Ven) |
| JWT mal configuré (refresh) | Faible | Élevé | Tests dès INT-02 |
| Modèle User conflict avec mot-clé SQL | Faible | Moyen | Table nommée "user" avec guillemets |
| Frontend sans API (bloquant) | Moyen | Moyen | Mock API en début de sprint |

---

**Documents liés :**
- `docs/DAT/07-implementation-roadmap.md`
- `docs/DAT/specs/03-api-spec.md`
- `docs/DAT/05-data-model.md`
