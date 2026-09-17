# Sprint 6.5 : Documentation & préparation entretien (1.5 jour)

> **Durée :** 1.5 jour (7h/j) | **Points :** 8 | **Tâches :** INT-91 à INT-93
>
> **Référence :** `docs/DAT/MBchauffage-DAT/Todo_Fix.md` §25
>
> **Objectif :** transformer le travail technique en **discours défendable**.

---

## INT-91 — Fiche architecture à présenter (3 pts)

**User Story**
En tant que **candidat**,
Je veux **une fiche synthétique de l'architecture**,
Afin de **la présenter en 2-3 minutes sans hésiter**.

**Acceptance Criteria**
- [ ] Schéma d'architecture final (1 page, lisible)
- [ ] Flux expliqué : `Internet → 1Panel (80/443) → reverse proxy → services (127.0.0.1)`
- [ ] Justification de chaque choix :
  - Pourquoi 1Panel (proxy, SSL, admin)
  - Pourquoi Docker Compose (pas Swarm/K8s sur ce périmètre)
  - Pourquoi PostgreSQL
  - Pourquoi `127.0.0.1` et pas d'exposition publique
- [ ] Séparation `Router → Service → Repository` expliquée
- [ ] Le pipeline d'import expliqué étape par étape
- [ ] Le catalogue produits / exposition expliqué (modélisation métier)
- [ ] Le déploiement VPS expliqué (provisioning → DNS → SSL → CI/CD)
- [ ] Format : support de présentation (markdown → slides si besoin)

**Technical Notes**
- Fichier : `notes/interview/architecture-presentation.md`
- **Règle :** une phrase par décision, pas de pavé

---

## INT-92 — Questions / réponses d'entretien (3 pts)

**User Story**
En tant que **candidat**,
Je veux **une liste de questions probables avec mes réponses**,
Afin de **répondre avec assurance aux points techniques**.

**Acceptance Criteria**
- [ ] Q/R rédigées pour au minimum :
  - **Healthcheck** : « Pourquoi un healthcheck ? »
  - **Idempotence** : « Comment garantissez-vous qu'un import ne soit pas rejoué ? »
  - **Fuzzy matching** : « Comment détectez-vous les doublons ? »
  - **Deux passes** : « Pourquoi clients puis jobs ? »
  - **Transactions** : « Une transaction sur 20 ans de données ? »
  - **Jobs orphelins** : « Que faites-vous des données non rattachables ? »
  - **CI/CD** : « Comment déployez-vous ? »
  - **Ports** : « Vos services sont-ils exposés ? »
  - **Versions** : « Pourquoi le DAT ne fige pas les versions ? »
  - **Modélisation** : « Pourquoi avoir séparé essai et vendable ? »
  - **Sécurité VPS** : « Comment protégez-vous le serveur ? »
- [ ] Chaque réponse : 3-5 phrases max, vocabulaire maîtrisé
- [ ] Aucune réponse ne survend une compétence non réelle

**Technical Notes**
- Fichier : `notes/interview/questions-reponses.md`
- **Rappel :** les seuils 95/80 sont des **paramètres de conception à calibrer**, à présenter comme tels

---

## INT-93 — Périmètre de ce qu'il ne faut PAS survendre (2 pts)

**User Story**
En tant que **candidat**,
Je veux **savoir où placer les limites de mon discours**,
Afin de **rester crédible**.

**Acceptance Criteria**
- [ ] Liste explicite des compétences à **ne pas présenter comme expertises** :
  - Vue/TypeScript (accompagné par l'IA)
  - GitHub Actions (notions)
  - VPS/production (première approche)
  - 1Panel (outil, pas expertise)
  - Architecture financière complète
  - Architecture distribuée/scalable
- [ ] Formulation de repli pour chaque sujet, ex :
  - Frontend → « Ce n'est pas mon domaine principal, j'ai utilisé Vue/TS pour compléter le projet. Mon cœur reste le backend et l'architecture. »
- [ ] Positionnement du module financier : « gestion commerciale simplifiée, pas un logiciel comptable »
- [ ] Pitch de présentation du projet rédigé (5-6 phrases)

**Technical Notes**
- Fichier : `notes/interview/perimetre-credibilite.md`
- **Pitch recommandé (Todo_Fix §25) :**
  > « Tervo est un projet métier que j'ai conçu pour digitaliser une entreprise CVC. Mon socle reste le backend et l'architecture, mais j'ai volontairement élargi le périmètre : FastAPI côté backend, PostgreSQL, Docker Compose et une première approche CI/CD et déploiement VPS. Le principal sujet technique était la migration de plus de 20 ans d'historique Excel vers une base relationnelle, avec normalisation, détection de doublons, fuzzy matching, validation et import en deux passes. »

---

## Tests Cases Sprint 6.5

Les tests cases détaillés sont dans `test-cases.json`.
