# Tervo — Workflows & UX Patterns

> **Objet :** Workflows utilisateur pour Tervo.
>
> **Documents liés :** `specs/01-specs-fonctionnelle.md`, `specs/03-api-spec.md`

---

## 1. Persona (acteur unique)

### Technicien CVC

| Attribut   | Valeur                                                         |
| ---------- | -------------------------------------------------------------- |
| Expérience | 2-10 ans en CVC                                                |
| Tech-savvy | Variable (moyen)                                               |
| Équipement | Smartphone (4G), parfois tablette                              |
| Contexte   | Sur le terrain, sous-sols sans réseau                          |
| Tâches     | Interventions, dépannage, maintenance                          |
| Besoin     | Rapidité, simplicité, pas de double saisie                     |
| Pages clés | Dashboard du jour, fiche client, formulaire inspection, caméra |

**Frustrations :** Papier perdu, photos sur téléphone perso, rapport à refaire le soir

**Patterns UX :** Bouton unique "Démarrer/Terminer", checklist rapide, upload photo automatique, rapport PDF one-click

---

## 2. Workflows principaux

### 2.1 Intervention complète de A à Z

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 : MATIN — CONSULTER LE PLANNING                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Ouvrir l'app → Dashboard du jour                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  📋 Aujourd'hui : 3 jobs                              │       │
│  │  ▶  1 en cours | ✅ 2 terminés                        │       │
│  │                                                       │       │
│  │  PROCHAIN JOB                                         │       │
│  │  🔴 HAUTE  14:00  Panne clim — M. DUPONT              │       │
│  │  12 rue de Paris, 75001 Paris                         │       │
│  │                    [▶ Démarrer]                       │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  GET /api/v1/dashboard/summary → affiche les jobs du jour       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 2 : ARRIVÉE — DÉMARRER LE JOB                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [▶ Démarrer] → PUT /api/v1/jobs/{id}/start                     │
│  → Statut : en_cours → started_at = now → timer lancé            │
│  → Checklist pré-intervention affichée                           │
│                                                                  │
│  Checklist pré (items automatiques) :                            │
│  ☑ État général               [RAS, installation propre___]     │
│  ☑ Équipement hors tension    [Disjoncteur coupé__________]     │
│  ☑ Zone sécurisée             [OK_________________________]     │
│  ☑ Accès dégagé              [______________________________]   │
│                                                                  │
│  Photos avant (min. 1) :                                         │
│  ┌──────┐ [+ Ajouter photo] — POST /api/v1/jobs/{id}/photos     │
│  │      │  multipart: file + category=avant                      │
│  └──────┘                                                        │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 3 : PENDANT — SAISIR LES MATÉRIAUX                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Matériaux utilisés :                                            │
│  ┌────────────────────────────────────────────────────┐         │
│  │ Filtre à air HEPA     [1]  [✕]                     │         │
│  │ Gaz R410A             [0.5] [✕]                    │         │
│  │ [+ Ajouter] → POST /api/v1/jobs/{id}/materials     │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 4 : FIN — CLÔTURER LE JOB                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Checklist post-intervention :                                   │
│  ☑ Installation fonctionnelle    [OK, climatisation OK____]     │
│  ☑ Nettoyage effectué            [Zone propre_____________]     │
│  ☑ Explication client faite      [Client satisfait________]     │
│                                                                  │
│  Photos après (min. 1) :                                         │
│  ┌──────┐ [+ Ajouter photo] — POST /api/v1/jobs/{id}/photos     │
│  │      │  multipart: file + category=après                      │
│  └──────┘                                                        │
│                                                                  │
│  Observations : [Filtre encrassé remplacé, recharge gaz.___]     │
│                                                                  │
│  [Terminer le job]                                               │
│  → PUT /api/v1/jobs/{id}/complete                               │
│  → Validation : checklist OK, photos avant OK, photos après OK  │
│  → completed_at = now, status = terminé, durée calculée         │
│  → Report generated, share_token created                         │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 5 : APRÈS — RAPPORT & AVIS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [📄 Voir le rapport] → GET /api/v1/jobs/{id}/report/download   │
│  → PDF téléchargé : client, dates, durée, matériaux, photos,    │
│    checklist, observations                                       │
│                                                                  │
│  [⭐ Demander un avis] → lien copié : /review/{share_token}     │
│  → Envoyer par SMS ou email au client                            │
│  → Le client ouvre → note 1-5 ⭐ + commentaire                   │
│  → POST /api/v1/review/{share_token}/submit (public, no auth)   │
│                                                                  │
│  → Job terminé ✅                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Intervention urgente (express)

```
1. Appel client → recherche rapide par téléphone
   GET /api/v1/clients?search=0612345678

2. Client inconnu → [+ Nouveau client]
   POST /api/v1/clients → full_name, phone, address

3. [+ Nouveau job] → priorité "urgente"
   POST /api/v1/jobs → client_id, title, priority=urgente

4. [▶ Démarrer] immédiatement

5. Intervention → checklist + photos

6. [Terminer] → rapport PDF généré

7. Lien avis envoyé

Temps total hors intervention : < 2 minutes
```

### 2.3 Consultation historique client

```
1. Menu → 📁 Clients → recherche : "Dupont"
   GET /api/v1/clients?search=dupont

2. Fiche client M. DUPONT :
   ┌──────────────────────────────────────┐
   │  📞 06 12 34 56 78                   │
   │  📍 12 rue de Paris, 75001 Paris     │
   │  📝 Code porte B4, 3e étage          │
   ├──────────────────────────────────────┤
   │  HISTORIQUE (3 interventions)        │
   │  15/05/2026  Panne clim    ⭐ 4/5    │
   │  02/03/2026  Maintenance   ⭐ 5/5    │
   │  10/12/2025  Installation  ⭐ 4/5    │
   │  Note moyenne : 4.3/5 ★★★★★         │
   ├──────────────────────────────────────┤
   │  [+ Nouveau job]                     │
   └──────────────────────────────────────┘

3. Clic sur "Panne clim" → détail du job
   GET /api/v1/jobs/42
   → voir photos, rapport PDF, avis client
```

---

## 3. Navigation & Layout

```
┌──────────────────────────────┐
│  Tervo                  │ ← TopBar (fixe)
├──────────────────────────────┤
│                              │
│    CONTENU DE LA PAGE        │
│                              │
│                              │
├──────────────────────────────┤
│  🏠     📋     📁     👤     │ ← Bottom nav
│ Accueil Jobs  Clients Profil │
└──────────────────────────────┘
```

**Bottom navbar fixe** (mobile-first, pas de sidebar) :

- 🏠 **Accueil** : dashboard du jour (jobs, timer)
- 📋 **Jobs** : liste filtrée (statut, date)
- 📁 **Clients** : recherche + liste
- 👤 **Profil** : informations technicien, déconnexion

---

## 4. Patterns UX récurrents

### 4.1 Couleurs & statuts

| État             | Couleur   | Usage                     |
| ---------------- | --------- | ------------------------- |
| Succès / Terminé | 🟢 Vert   | Job terminé, création OK  |
| En cours         | 🔵 Bleu   | Job en cours, timer actif |
| Planifié         | ⚪ Gris   | Job planifié, en attente  |
| Urgente          | 🔴 Rouge  | Priorité urgente          |
| Haute            | 🟠 Orange | Priorité haute            |
| Normale          | 🟡 Jaune  | Priorité normale          |
| Basse            | 🟢 Vert   | Priorité basse            |
| Avis             | ⭐ Jaune  | Note client               |

### 4.2 Composants interactifs

| Pattern        | Usage                    | Composant           |
| -------------- | ------------------------ | ------------------- |
| **Toast**      | Feedback succès/erreur   | PrimeVue Toast      |
| **Dialog**     | Confirmation terminaison | PrimeVue Dialog     |
| **FileUpload** | Upload photos            | PrimeVue FileUpload |
| **DataTable**  | Liste jobs/clients       | PrimeVue DataTable  |
| **Skeleton**   | Chargement données       | PrimeVue Skeleton   |
| **Rating**     | Note avis client         | PrimeVue Rating     |
| **BottomNav**  | Navigation principale    | Composant custom    |
| **Timer**      | Durée intervention       | Composant custom    |

### 4.3 États d'écran

| État        | Affichage                              |
| ----------- | -------------------------------------- |
| **Loading** | Skeleton cards                         |
| **Empty**   | "Aucun job aujourd'hui" + illustration |
| **Error**   | Message d'erreur + "Réessayer"         |
| **Success** | Données affichées normalement          |

---

## 5. Règles métier

| Table  | Règle                                            |
| ------ | ------------------------------------------------ |
| client | Téléphone obligatoire                            |
| job    | `started_at` renseigné si status = `en_cours`    |
| job    | `completed_at` renseigné si status = `terminé`   |
| job    | Min. 1 photo avant + 1 photo après pour terminer |
| job    | Checklist pré + post complètes pour terminer     |
| review | Un seul avis par job                             |
| review | Lien partage valide 30 jours                     |
| review | Endpoint public (no auth)                        |

---

> **Document mis à jour le 03/06/2026**
> **Version :** 3.0 (Interventions)
> **Documents liés :** `specs/01-specs-fonctionnelle.md`, `specs/03-api-spec.md`
