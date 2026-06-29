# Phase 3 : First Deploy (Semaine 4)

> **Objectif :** Mise en production via 1Panel. Docker multi-stage, PostgreSQL dédié, premier déploiement en IP:port.

---

## Vue d'ensemble

| Sprint | Période | Tâches | Points totaux |
|--------|---------|--------|---------------|
| 3.1 | Semaine 4, Lun-Ven | INT-48 à INT-51 + INT-45 + INT-47 + INT-DPL + INT-DOC | 29 |

---

## Dépendances

```
Phase 3 (First Deploy) ← dépend de Phase 1 + Phase 2 (code fonctionnel complet)
```

---

## Critères de succès Phase 3

- [ ] Application déployée via 1Panel accessible en `http://<IP>:8000`
- [ ] PostgreSQL `resq_db` créée et connectée
- [ ] Uploads volume persistant monté
- [ ] Seed données : admin + technicien + données demo
- [ ] Dockerfile multi-stage (uv) opérationnel
- [ ] Coverage ≥ 80%
- [ ] Validation formulaires (Zod) active
- [ ] Documentation déploiement livrée

---

## Contexte technique

| Technologie | Détail |
|-------------|--------|
| **1Panel** | Server manager, build Docker via UI |
| **Reverse proxy** | Géré par 1Panel, pas de Traefik dans docker-compose |
| **PostgreSQL** | Container existant `postgres:17.4`, port 5432, réseau `postgres_network` |
| **Nouvelle DB** | `resq_db`, user `resq_user` |
| **Domaine** | Aucun — premier déploiement en IP:port |
| **SSL** | Pas de SSL pour la première version |
| **Build Docker** | `resq-backend:latest` (tag local, pas de registry) |
| **Image tag** | `resq-backend:latest` |

---

**Documents liés :**
- `docs/DAT/07-implementation-roadmap.md`
- `notes/backend/extras/restruct_roadmap-discussion.md`
- `notes/backend/extras/postgres.docker-compose.yml`
