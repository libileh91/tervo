# Stage 6 — Tervo : Import Excel, Catalogue, Déploiement & Présentation

> **Projet :** Tervo (nom conservé — pas de rebranding)
> **Objectif :** rendre Tervo défendable en entretien, **déployé sur un VPS**.
> **Focus :** Architecture corrigée (`annexes/revue-architecture.md`), CI/CD, migration Excel (pandas + fuzzy), catalogue produits, déploiement VPS.
> **Hors périmètre :** Module financier complet, stock, fournisseurs, Paperless, Go.
> **Contrainte :** 7h/jour, pas de Go.

---

## Contexte

Tervo est un socle d'application CVC (interventions, clients, checklists, photos, rapports, avis) déjà fonctionnel. Ce stage l'étend avec :

1. Les **corrections d'architecture** issues de la revue (`docs/DAT/annexes/revue-architecture.md`)
2. Le **cœur du sujet** : la migration de 20 ans d'Excel vers PostgreSQL
3. Une **identité fonctionnelle** : catalogue produits & exposition en salle
4. Le **déploiement réel sur un VPS** (domaine + SSL + CI/CD)
5. La **préparation au discours d'entretien**

---

## Vue d'ensemble

| Sprint | Contenu | Tâches | Points | Jours |
|--------|---------|--------|:------:|:-----:|
| 6.1 | Corrections archi + Docker + CI/CD | INT-66 à INT-70 | 10 | 2 |
| 6.2 | Import Excel (pandas + fuzzy + pipeline) | INT-71 à INT-80 | 39 | 6 |
| 6.3 | Catalogue produits & exposition | INT-81 à INT-84 | 11 | 2.5 |
| 6.4 | **Déploiement VPS** | INT-85 à INT-90 | 16 | 2 |
| 6.5 | Doc & prépa entretien | INT-91 à INT-93 | 8 | 1.5 |
| **Total** | | **28 tâches** | **84** | **14** |

**Buffer :** +2 jours → **16 jours** au total (à 7h/jour).

> ⚠️ **16 jours est le scénario complet.** Si le temps manque, les leviers de réduction sont :
> - 6.2 : réduire la couverture de tests (−1 j)
> - 6.3 : frontend minimal uniquement (−0.5 j)
> - 6.4 : déploiement manuel sans CI/CD auto (−0.5 j)

---

## Dépendances

```
Sprint 6.1 (Corrections)          ← indépendant, à faire en premier
    ↓
    ├── Sprint 6.2 (Import Excel)       ← dépend de 6.1
    └── Sprint 6.3 (Catalogue produits) ← dépend de 6.1
              ↓
        Sprint 6.4 (Déploiement VPS)    ← dépend de 6.1 + 6.2 + 6.3
              ↓
        Sprint 6.5 (Doc entretien)      ← dépend de tout le reste
```

> 6.2 et 6.3 sont indépendants entre eux.
> 6.4 peut être fait plus tôt (juste après 6.1) pour valider le pipeline, puis redéployé.

---

## Référence : corrections de la revue d'architecture

| # | Correction | Sprint |
|---|-----------|--------|
| 1 | Ports `127.0.0.1` (pas d'exposition publique) | 6.1 + 6.4 |
| 2 | Backend non exposé directement | 6.1 + 6.4 |
| 3 | Healthchecks (`depends_on` ≠ readiness) | 6.1 + 6.4 |
| 4 | CI/CD sans double build | 6.1 + 6.4 |
| 5 | Idempotence de l'import (ImportBatch + SHA-256) | 6.2 |
| 6 | Fuzzy matching : normalisation + 3 zones | 6.2 |
| 7 | Jobs orphelins → `import_errors` (pas ignorés) | 6.2 |
| 8 | Transaction par batch (pas une transaction géante) | 6.2 |
| 9 | Versions : DAT = archi, lockfile = versions | 6.1 |
| 10 | Ports firewall : 22/80/443 uniquement | 6.1 + 6.4 |
| 11 | Séparation `importers/` vs `services/` | 6.2 |
| 12 | Bilans à la demande (pas de cron prématuré) | hors scope |

---

## Architecture cible (après le stage 6)

```
                        INTERNET
                           │
                     HTTPS 80/443
                           │
                   ┌───────▼────────┐
                   │     1Panel     │
                   │   OpenResty    │
                   │  SSL / Routing │
                   └───────┬────────┘
                           │ 127.0.0.1
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    Frontend SPA       FastAPI         (futur)
      Vue.js            API
          │                │
          │         Router → Service → Repository
          │                │
          │           PostgreSQL
          │
          └──────── API REST

        DATA MIGRATION
             Excel
               │
        Pandas / openpyxl
               │
        Détection format
               │
         Normalisation
               │
         Validation
               │
        Fuzzy matching (95/80)
               │
        PASS 1 — CLIENTS
               │
        PASS 2 — JOBS
               │
        Transaction / batch
               │
          PostgreSQL
```

---

## Ce que Tervo devient à la fin du stage 6

```
Tervo
├── Socle intervention (déjà fait)
│   ├── Auth JWT
│   ├── Clients CRUD + historique
│   ├── Jobs CRUD + start/complete
│   ├── Checklist pré/post
│   ├── Photos + thumbnails
│   ├── Matériaux
│   ├── Rapport PDF
│   └── Avis client
├── Catalogue produits (6.3)
│   ├── produit (référence, catégorie, marque, prix)
│   └── exposition_showroom (emplacement, essai, vendable)
├── Import Excel (6.2)
│   ├── importers/ (reader, detector, normalizer, validators, matcher, report)
│   ├── ImportService (2 passes + transactions par batch)
│   └── API admin (preview / validate / execute)
├── Architecture corrigée (6.1)
│   ├── ports 127.0.0.1
│   ├── healthchecks
│   └── CI/CD cohérent
└── Déploiement VPS (6.4)
    ├── VPS sécurisé (SSH clé, ufw, fail2ban)
    ├── Docker + 1Panel
    ├── Reverse proxy + Let's Encrypt
    └── CI/CD → VPS
```

---

## Critères de succès Stage 6

- [ ] Architecture corrigée et cohérente (ports, healthchecks, versions)
- [ ] CI/CD fonctionnel sans double build
- [ ] Import Excel opérationnel : normalisation + fuzzy + 2 passes + transactions
- [ ] Idempotence prouvée (SHA-256 + ImportBatch)
- [ ] Jobs orphelins tracés dans `import_errors`
- [ ] Catalogue produits + exposition exposés en API et UI
- [ ] **Tervo déployé sur un VPS avec HTTPS et CI/CD**
- [ ] Fiche de présentation architecture (questions/réponses entretien)
- [ ] Notes pédagogiques : pandas, openpyxl, rapidfuzz, transactions, modélisation, déploiement

---

**Documents liés :**
- `docs/DAT/annexes/revue-architecture.md` (corrections d'architecture)
- `docs/DAT/08-module-catalogue.md` (catalogue, exposition)
- `docs/DAT/04-architecture.md`
- `docs/DAT/05-data-model.md`
- `notes/backend/deploy/` (procédures de déploiement existantes)
