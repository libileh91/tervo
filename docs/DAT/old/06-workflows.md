# Tervo — Workflows & UX Patterns

> **Objet :** Workflows utilisateur et patterns d'interface.
>
> **Documents liés :** `specs/01-specs-fonctionnelle.md`, `04-architecture.md`

---

## 1. Personas

### 1.1 Technicien CVC (acteur principal)

| Attribut | Valeur |
|----------|--------|
| Expérience | 2-20 ans en CVC |
| Tech-savvy | Variable (moyen) |
| Équipement | Smartphone (4G), parfois tablette |
| Contexte | Terrain, sous-sols sans réseau |
| Besoins | Rapidité, simplicité, pas de double saisie |
| Pages clés | Dashboard du jour, fiche client, inspection, caméra |

**Frustrations :** papier perdu, photos sur téléphone perso, rapport à refaire le soir.

### 1.2 Comptable / Gérant *(phase 2)*

| Attribut | Valeur |
|----------|--------|
| Tech-savvy | Faible à moyen |
| Équipement | PC de bureau |
| Besoins | Devis, facturation, bilans, suivi des paiements |

### 1.3 Vendeur / Responsable showroom

| Attribut | Valeur |
|----------|--------|
| Équipement | Tablette ou PC en showroom |
| Besoins | Présenter le catalogue, transformer une visite en devis |

### 1.4 Admin technique

| Attribut | Valeur |
|----------|--------|
| Besoins | Import de données, gestion des utilisateurs, supervision, backups |

---

## 2. Workflow principal : intervention de A à Z

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 — MATIN : CONSULTER LE PLANNING                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Ouvrir l'app → Dashboard du jour                                │
│  GET /api/v1/dashboard/summary                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  📋 Aujourd'hui : 3 interventions                     │       │
│  │  ▶  1 en cours | ✅ 2 terminées                       │       │
│  │                                                       │       │
│  │  PROCHAINE INTERVENTION                               │       │
│  │  🔴 HAUTE  14:00  Panne clim — M. DUPONT              │       │
│  │  12 rue de Paris, 75001 Paris                         │       │
│  │                    [▶ Démarrer]                       │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 2 — ARRIVÉE : DÉMARRER                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [▶ Démarrer] → PUT /api/v1/jobs/{id}/start                     │
│  → status = en_cours, started_at = now → timer lancé             │
│  → Checklist pré-intervention affichée                           │
│                                                                  │
│  Checklist pré :                                                 │
│  ☑ État général               [RAS, installation propre]        │
│  ☑ Équipement hors tension    [Disjoncteur coupé]               │
│  ☑ Zone sécurisée             [OK]                              │
│                                                                  │
│  Photos avant (min. 1) :                                         │
│  POST /api/v1/jobs/{id}/photos (multipart: file + category=avant)│
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 3 — PENDANT : SAISIR LES MATÉRIAUX                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /api/v1/jobs/{id}/materials                                │
│  ┌────────────────────────────────────────────────────┐         │
│  │ Filtre à air HEPA     [1]  [✕]                     │         │
│  │ Gaz R410A             [0.5] [✕]                    │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 4 — FIN : CLÔTURER                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Checklist post-intervention :                                   │
│  ☑ Installation fonctionnelle                                    │
│  ☑ Nettoyage effectué                                            │
│  ☑ Explication client faite                                      │
│                                                                  │
│  Photos après (min. 1)                                           │
│  Observations : [Filtre encrassé remplacé, recharge gaz.]        │
│                                                                  │
│  [Terminer] → PUT /api/v1/jobs/{id}/complete                     │
│  → Validation : checklist OK, photos avant OK, photos après OK   │
│  → completed_at = now, durée calculée                            │
│  → PDF généré + share_token créé                                 │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 5 — APRÈS : RAPPORT & AVIS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [📄 Voir le rapport] → GET /api/v1/jobs/{id}/report/download    │
│                                                                  │
│  [⭐ Demander un avis] → lien copié : /review/{share_token}      │
│  → Envoyer par SMS ou email au client                            │
│  → POST /api/v1/review/{share_token}/submit (public, no auth)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Intervention urgente (express)

```
1. Appel client → recherche rapide par téléphone
   GET /api/v1/clients?search=0612345678

2. Client inconnu → [+ Nouveau client]
   POST /api/v1/clients

3. [+ Nouvelle intervention] → priorité "urgente"
   POST /api/v1/jobs

4. [▶ Démarrer] immédiatement

5. Intervention → checklist + photos

6. [Terminer] → rapport PDF généré

7. Lien avis envoyé

Temps total hors intervention : < 2 minutes
```

### 2.2 Consultation de l'historique client

```
1. Clients → recherche "Dupont"
   GET /api/v1/clients?search=dupont

2. Fiche client : coordonnées, notes, historique des interventions

3. Clic sur une intervention → détail (photos, rapport, avis)
```

---

## 3. Workflow : import de l'historique Excel

```
┌─────────────────────────────────────────────────────────────────┐
│  1. PRÉPARATION                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Collecter les fichiers Excel historiques                        │
│  (un par année ou par type : clients, interventions)             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  2. UPLOAD & PREVIEW                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /api/v1/admin/import/preview                               │
│  → Le serveur parse le fichier (pandas)                          │
│  → Affiche les 10 premières lignes + mapping détecté             │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Fichier : clients_2015.xlsx                              │    │
│  │ 234 lignes, 8 colonnes détectées                         │    │
│  │                                                          │    │
│  │ Mapping proposé :                                        │    │
│  │   "Nom Client"  → full_name                              │    │
│  │   "Tel"         → phone                                  │    │
│  │   "Adresse"     → address                                │    │
│  │   ...                                                    │    │
│  │                                                          │    │
│  │   [Modifier le mapping]  [Valider]                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  3. VALIDATION (sans insertion)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /api/v1/admin/import/validate                              │
│  → Détection des doublons (fuzzy), champs manquants, formats     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ✅ 210 clients prêts                                     │    │
│  │ ⚠️ 18 doublons potentiels (validation humaine requise)   │    │
│  │ ❌  6 lignes en erreur                                   │    │
│  │                                                          │    │
│  │   [Voir les doublons]  [Voir les erreurs]                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  4. IMPORT RÉEL                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /api/v1/admin/import/execute                               │
│  → PASS 1 : Clients (résolution des doublons)                    │
│  → PASS 2 : Jobs (résolution des client_id)                      │
│  → Transaction par batch                                         │
│  → Logs : ImportBatch + ImportRecord + ImportError               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ✅ Import terminé                                        │    │
│  │ 📊 210 clients créés                                     │    │
│  │ 📊 1 247 jobs importés                                   │    │
│  │ ⚠️ 12 doublons résolus automatiquement                   │    │
│  │ ❌  4 anomalies (jobs sans client) → à traiter           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Les 3 zones de décision du fuzzy matching :**

| Score | Décision |
|-------|----------|
| ≥ 95 | Match automatique |
| 80 – 95 | Validation humaine |
| < 80 | Nouveau client |

> Une erreur de rapprochement est plus grave qu'un doublon temporaire. D'où une zone d'ambiguïté explicite.

---

## 4. Workflow : parcours showroom

```
visite / intérêt client
        ↓
produits présentés (exposition_showroom)
   disponible_essai ? vendable_showroom ?
        ↓
intérêt confirmé ?
  ↙            ↘
non            oui
 ↓              ↓
fin         devis créé (lignes liées au produit)   [phase 2]
                ↓
        devis accepté
                ↓
        job d'installation
                ↓
        garantie / contrat d'entretien              [phase 2]
                ↓
        maintenance périodique                       [phase 2]
                ↓
        avis client (module existant)
```

**Le parcours showroom ne crée aucun nouveau module de facturation ou d'intervention : il relie le catalogue aux modules existants.**

---

## 5. Workflow : backup & restore

```
┌─────────────────────────────────────────────────────────────────┐
│  QUOTIDIEN (cron 3h00)                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. pg_dump → gzip → /var/backups/tervo/                         │
│  2. uploads → archive versionnée                                 │
│  3. s3cmd → Object Storage                                       │
│  4. Rétention : 30 jours                                         │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  MENSUEL (1er du mois, 5h00)                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Restauration dans une DB temporaire                          │
│  2. Vérifications : schéma, tables, volumétrie, contraintes      │
│  3. Requête applicative réelle                                   │
│  4. Nettoyage + rapport                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

> **Backup ≠ synchronisation.** On versionne, on ne fait pas de miroir.

---

## 6. Workflow : déploiement

```
┌─────────────────────────────────────────────────────────────────┐
│  PROVISIONING (une fois)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  - VPS Ubuntu 24.04                                              │
│  - SSH par clé, ufw (22/80/443), fail2ban                        │
│  - Docker + 1Panel                                               │
│  - DNS : tervo.com, api.tervo.com → IP du VPS                    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  DÉPLOIEMENT                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  git pull                                                        │
│  docker compose -f deploy/docker-compose.yml up -d --build       │
│                                                                  │
│  → postgres démarre (healthcheck)                                │
│  → backend attend service_healthy, puis démarre                  │
│  → frontend démarre                                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  MIGRATIONS + SEED                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  docker exec tervo-backend-1 alembic upgrade head                │
│  docker exec tervo-backend-1 python -m app.seed                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  CONFIGURATION 1PANEL                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Websites → tervo.com      → http://127.0.0.1:3000 + Let's Encrypt│
│  Websites → api.tervo.com  → http://127.0.0.1:8000 + Let's Encrypt│
│  Cron Jobs → backup quotidien + restore test mensuel             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### CI/CD

```
push main → GitHub Actions (tests) → SSH VPS → git pull → up -d --build
```

**Un seul build.** Détail : `specs/02-spec-technique.md` §4.

---

## 7. Navigation & layout

```
┌──────────────────────────────┐
│  Tervo                  │ ← TopBar (fixe)
├──────────────────────────────┤
│                              │
│    CONTENU DE LA PAGE        │
│                              │
├──────────────────────────────┤
│  🏠     📋     📁     👤     │ ← Bottom nav
│ Accueil Interv. Clients Profil│
└──────────────────────────────┘
```

---

## 8. Patterns UX

### 8.1 Couleurs & statuts

| État | Couleur | Usage |
|------|---------|-------|
| Terminé | 🟢 Vert | Job terminé, création OK |
| En cours | 🔵 Bleu | Job en cours, timer actif |
| Planifié | ⚪ Gris | En attente |
| Urgente | 🔴 Rouge | Priorité urgente |
| Haute | 🟠 Orange | Priorité haute |
| Normale | 🟡 Jaune | Priorité normale |
| Basse | 🟢 Vert | Priorité basse |
| Avis | ⭐ Jaune | Note client |

### 8.2 Composants

| Pattern | Usage | Composant |
|---------|-------|-----------|
| Toast | Feedback succès/erreur | PrimeVue Toast |
| Dialog | Confirmation | PrimeVue Dialog |
| FileUpload | Photos | PrimeVue FileUpload |
| DataTable | Listes | PrimeVue DataTable |
| Skeleton | Chargement | PrimeVue Skeleton |
| Rating | Avis client | PrimeVue Rating |

### 8.3 États d'écran

| État | Affichage |
|------|-----------|
| **Loading** | Skeleton cards |
| **Empty** | Message + illustration + action |
| **Error** | Message clair + bouton « Réessayer » |
| **Success** | Données affichées |

---

## 9. Règles métier

| Entité | Règle |
|--------|-------|
| client | Téléphone obligatoire |
| job | `started_at` renseigné si `status = en_cours` |
| job | `completed_at` renseigné si `status = terminé` |
| job | Min. 1 photo avant + 1 photo après pour terminer |
| job | Checklist pré + post complètes pour terminer |
| review | Un seul avis par job |
| review | Lien de partage valide 30 jours |
| review | Endpoint public (sans auth) |
| produit | `reference` unique |
| exposition | Un produit → au plus une exposition |
| import | Idempotent (SHA-256) |
| import | Job non rattachable → `import_error` (jamais ignoré) |

---

> **Sommaire :** `00-sommaire.md`
> **Spécifications fonctionnelles :** `specs/01-specs-fonctionnelle.md`
> **Modèle de données :** `05-data-model.md`
