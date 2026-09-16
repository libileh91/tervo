# Sprint 4.2 : Tests & Perf (Semaine 5, Jeu-Ven)

> **Durée :** 2 jours | **Points :** 21 | **Tâches :** 5 (INT-43, INT-44, INT-46, INT-52, INT-53)
>
> Sprint déplacé depuis l'ancien Sprint 3.1 (Tests & Perf).

---

## INT-43 — Tests E2E Playwright : workflow complet (8 pts)

**User Story**  
En tant que **développeur**,  
Je veux **tester le workflow complet avec Playwright**  
Afin de **vérifier que tout le parcours fonctionne de bout en bout**.

**Acceptance Criteria**
- [ ] Scénario : login → créer client → créer job → démarrer → checklist → photos → compléter → rapport
- [ ] Playwright installé en dépendance de dev frontend
- [ ] `frontend/e2e/` dossier créé avec les tests
- [ ] Script npm : `npm run test:e2e`
- [ ] Test headless (CI-compatible)
- [ ] Assertions sur chaque étape (status chips, redirections, messages toast)

**Technical Notes**
- `npm install -D @playwright/test`
- `npx playwright install chromium`
- Fichier : `frontend/e2e/full-workflow.spec.ts`

---

## INT-44 — Tests E2E : avis client (lien public → note → submit) (3 pts)

**User Story**  
En tant que **développeur**,  
Je veux **tester le parcours d'avis client**  
Afin de **vérifier que les endpoints publics fonctionnent sans auth**.

**Acceptance Criteria**
- [ ] Scénario : ouvrir lien public → voir infos job → noter 4 étoiles → commentaire → submit
- [ ] Vérifier le message "Merci pour votre avis !"
- [ ] Vérifier que la soumission double est bloquée
- [ ] Vérifier qu'un token invalide affiche "Ce lien n'est plus valable"

**Technical Notes**
- Fichier : `frontend/e2e/review-flow.spec.ts`
- Tester sans cookie de session (page propre)
- Récupérer le share_token depuis la base ou l'API

---

## INT-46 — Performance : N+1 queries, index manquants (3 pts)

**User Story**  
En tant que **développeur**,  
Je veux **vérifier les performances des requêtes les plus fréquentes**  
Afin de **ne pas avoir de lenteur en production**.

**Acceptance Criteria**
- [ ] Vérifier que toutes les queries utilisent `selectinload` pour les relations (N+1 problem)
- [ ] Vérifier les index existants couvrent :
  - `job.scheduled_date` + `job.technician_id` (dashboard)
  - `job.client_id` (historique client)
  - `checklist_item.job_id` (checklist)
  - `job_photo.job_id` (photos)
  - `material.job_id` (matériaux)
  - `review.share_token` (avis public)
- [ ] Ajouter les index manquants via migration Alembic
- [ ] Tester le dashboard avec 100+ jobs sur une journée

**Technical Notes**
- SQLAlchemy echo mode : `engine = create_async_engine(..., echo=True)`
- Logger les queries SQL et vérifier le nombre de requêtes
- Migration : `alembic revision --autogenerate -m "add missing indexes"` si nécessaire

---

## INT-52 — Documentation utilisateur (guide + captures) (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **un guide utilisateur clair pour utiliser l'application**  
Afin de **prendre en main Tervo rapidement**.

**Acceptance Criteria**
- [ ] Document `docs/user-guide.md` avec :
  - Connexion / déconnexion
  - Dashboard : comprendre les compteurs et les cartes
  - Gestion des clients : recherche, création, modification
  - Gestion des jobs : création, démarrage, checklist, photos, matériaux
  - Terminer un job et télécharger le rapport
  - Partage du lien d'avis client
- [ ] Captures d'écran pour chaque section
- [ ] Format : sections claires, pas de jargon technique

**Technical Notes**
- Fichier : `docs/user-guide.md` (nouveau)
- Captures : `docs/images/` dossier à créer
- Outil de capture : tout outil (Flameshot, screenshot navigateur)

---

## INT-53 — Documentation API (Swagger/OpenAPI enrichi) (2 pts)

**User Story**  
En tant que **développeur**,  
Je veux **une documentation API complète**  
Afin de **comprendre les endpoints sans lire le code**.

**Acceptance Criteria**
- [ ] Ajouter des `description` et `summary` sur tous les endpoints FastAPI
- [ ] Tags organisés par groupe : Auth, Clients, Jobs, Checklist, Photos, Matériaux, Rapports, Reviews, Dashboard
- [ ] Exemples de requêtes/réponses dans les docstrings des endpoints
- [ ] Vérifier que `/docs` (Swagger UI) et `/redoc` (ReDoc) sont accessibles

**Technical Notes**
- FastAPI génère automatiquement Swagger depuis les type hints Pydantic
- Enrichir avec `@router.get("/...", summary="...", description="...")`
- Les tags sont déjà définis dans chaque router : `tags=["auth"]`

---

## Tests Cases Sprint 4.2

Les tests cases détaillés sont dans `test-cases.json`.
