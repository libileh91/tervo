# Sprint 7.6 — Déploiement VPS et documentation entretien

> **Tervo V2** · INT-111 à INT-112 · **Statut :** À traiter
> **Dépendances :** Valider le périmètre livré et ses tests avant déploiement ; documenter explicitement le backlog restant.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.6/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

> Reprend et finalise l'ancien sprint 6.4/6.5, sur le modèle v2.

---

## INT-111 — Déploiement VPS (5 pts)

**User Story**
En tant que **gérant**,
Je veux **déployer Tervo v2 sur un VPS en production**,
Afin de **disposer d'une instance publique avec HTTPS**.

**Acceptance Criteria**
- [ ] VPS : Ubuntu 24.04, SSH clé, ufw (22/80/443), fail2ban
- [ ] Docker + 1Panel + Let's Encrypt
- [ ] CI/CD : GitHub Actions → tests → SSH → `git pull` → `docker compose up -d` (un seul build)
- [ ] PostgreSQL sans port publié ; services bind `127.0.0.1`
- [ ] `curl` frontend + API → 200
- [ ] SSH par clé uniquement, connexion root directe désactivée, utilisateur non-root et mises à jour de sécurité automatiques
- [ ] Docker Engine + Compose disponibles ; réseau 1Panel opérationnel ; administration 1Panel uniquement par tunnel SSH, port 7410 inaccessible depuis Internet
- [ ] PostgreSQL dédié, healthchecks PostgreSQL/backend, démarrage backend après disponibilité de PostgreSQL, volumes persistants pour la base et les uploads, secrets hors Git
- [ ] TD-B010 traité : choix de la cible PostgreSQL, sauvegarde et migration des données existantes si nécessaire, vérification après restauration
- [ ] DNS frontend/API, reverse proxy vers les services locaux, certificats Let's Encrypt valides, renouvellement automatique et redirection HTTP vers HTTPS vérifiés
- [ ] Migrations appliquées ; connexion, tableau de bord et upload photo validés avec un compte dédié, sans identifiants de démonstration par défaut en production
- [ ] Procédure rejouable dans `notes/backend/deploy/vps-deploy.md` : prérequis, commandes, erreurs/corrections, schéma et différences mini-s1/VPS ; bilan du sprint dans `notes/backend/sprint7.6/`

**Technical Notes**
- Réutilise `notes/backend/deploy/` + `.github/workflows/ci.yml` (déjà prêts)

---

## INT-112 — Doc entretien (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **une fiche d'architecture et un Q/R entretien**,
Afin de **présenter le projet avec crédibilité (profil backend Java/Go)**.

**Acceptance Criteria**
- [ ] Fiche archi : chaîne Client→Site→Equipment→Intervention + migration
- [ ] Q/R : pourquoi la migration est transverse, pourquoi 3 zones, pourquoi transactions par batch
- [ ] Périmètre crédibilité : ne pas survendre Vue/TS, GH Actions, VPS, 1Panel
- [ ] Fichiers : `notes/interview/`
- [ ] Fiche d’une page présentable en 2–3 minutes : flux réseau, couches Router → Service → Repository, modèle V2, pipeline d’import et déploiement ; choix 1Panel, Compose et PostgreSQL justifiés
- [ ] Q/R couvrant healthchecks, idempotence, fuzzy matching, deux passes, transactions, interventions orphelines, CI/CD, ports, versions, modélisation V2 et sécurité VPS ; réponses de 3–5 phrases maximum
- [ ] Seuils 95/80 présentés comme paramètres à calibrer ; réalisations distinguées du backlog et compétences présentées sans survente
- [ ] Formulation adaptée pour chaque limite de compétence et pitch de 5–6 phrases ; livrables `architecture-presentation.md`, `questions-reponses.md`, `perimetre-credibilite.md`

**Technical Notes**
- Le différenciateur = la migration Excel (pandas, fuzzy, 2 passes, transactions)

---

## Cas de test

Voir [test-cases.json](test-cases.json).

Dix cas repris des anciens sprints 6.4 et 6.5, adaptés aux tâches INT-111/112 et au vocabulaire V2. Le champ `legacy_id` conserve leur provenance ; ils restent à exécuter. Les critères détaillés ci-dessus reprennent les exigences utiles avant suppression des anciens dossiers. Les estimations initiales de 5 et 3 points sont à réévaluer au démarrage.
