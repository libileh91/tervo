# Spécification Fonctionnelle — Tervo

> **Objet :** Application Web de gestion d'interventions pour techniciens CVC.
>
> **Acteur principal :** le technicien sur le terrain.
>
> **Documents liés :** `02-spec-technique.md`

---

## Sommaire

1. [Vision produit](#1-vision-produit)
2. [Périmètre MVP](#2-périmètre-mvp)
3. [Personas](#3-personas)
4. [Fiches clients](#4-fiches-clients)
5. [Jobs / Interventions](#5-jobs--interventions)
6. [Formulaire d'inspection](#6-formulaire-dinspection)
7. [Photos avant/après](#7-photos-avantaprès)
8. [Rapport post-intervention](#8-rapport-post-intervention)
9. [Avis / Review client](#9-avis--review-client)
10. [User stories](#10-user-stories)
11. [Workflows](#11-workflows)
12. [Maquettes fonctionnelles](#12-maquettes-fonctionnelles)

---

## 1. Vision produit

Application **mobile-first** permettant aux techniciens CVC de gérer leurs interventions quotidiennes :

- Retrouver les clients et leur historique avant d'intervenir
- Suivre les jobs avec un workflow de statuts clair
- Standardiser les inspections avec des checklists
- Capturer des photos avant/après
- Générer un rapport d'intervention professionnel
- Recueillir l'avis du client avec un lien de partage

L'application remplace le carnet papier + l'appareil photo + l'envoi de rapport par email.

---

## 2. Périmètre MVP

```
┌──────────────────────────────────────────────────────────────┐
│                    APP INTERVENTIONS CVC (MVP)               │
├────────────┬───────────┬─────────────┬───────────┬───────────┤
│  CLIENTS   │   JOBS    │ INSPECTION  │  RAPPORT  │   AVIS    │
├────────────┼───────────┼─────────────┼───────────┼───────────┤
│ • Création │ • CRUD    │ • Checklist │ • Généré  │ • Note 1-5│
│ • Fiche    │ • Statuts │   pré/post  │   auto    │ • Commen- │
│ • Historiq.│ • Planning│ • Notes     │ • PDF     │   taire   │
│ • Recherche│ • Liste   │ • Photos    │ • Matériaux│ • Lien   │
└────────────┴───────────┴─────────────┴───────────┴───────────┘
```

### Fonctionnalités détaillées

**Module CLIENTS**

| ID     | Fonctionnalité                                         | Priorité |
| ------ | ------------------------------------------------------ | -------- |
| CLI-01 | Création fiche client (nom, téléphone, adresse, email) | P1       |
| CLI-02 | Liste paginée + recherche (nom, téléphone, adresse)    | P1       |
| CLI-03 | Fiche détail client (infos + historique des jobs)      | P1       |
| CLI-04 | Modification fiche client                              | P1       |

**Module JOBS**

| ID     | Fonctionnalité                                          | Priorité |
| ------ | ------------------------------------------------------- | -------- |
| JOB-01 | Création d'un job (client, date, description, priorité) | P1       |
| JOB-02 | Liste des jobs avec filtres (statut, date, technicien)  | P1       |
| JOB-03 | Fiche détail job (infos, photos, checklist, rapport)    | P1       |
| JOB-04 | Workflow de statuts : planifié → en cours → terminé     | P1       |
| JOB-05 | Modification fiche job                                  | P1       |

**Module INSPECTION**

| ID     | Fonctionnalité                              | Priorité |
| ------ | ------------------------------------------- | -------- |
| INS-01 | Checklist pré-intervention (état des lieux) | P1       |
| INS-02 | Checklist post-intervention (vérifications) | P1       |
| INS-03 | Notes libres par item de checklist          | P1       |
| INS-04 | Photos avant intervention                   | P1       |
| INS-05 | Photos après intervention                   | P1       |

**Module RAPPORT**

| ID     | Fonctionnalité                          | Priorité |
| ------ | --------------------------------------- | -------- |
| RPT-01 | Génération rapport PDF automatique      | P1       |
| RPT-02 | Observations générales                  | P1       |
| RPT-03 | Matériaux utilisés (nom, quantité)      | P1       |
| RPT-04 | Durée de l'intervention (calculée auto) | P1       |
| RPT-05 | Signature client (P2)                   | P2       |

**Module AVIS**

| ID     | Fonctionnalité                        | Priorité |
| ------ | ------------------------------------- | -------- |
| AVI-01 | Note 1 à 5 étoiles                    | P1       |
| AVI-02 | Commentaire client                    | P1       |
| AVI-03 | Lien de partage unique (URL publique) | P1       |
| AVI-04 | Vue avis sur fiche client             | P1       |

---

## 3. Personas

### Technicien CVC (acteur unique du MVP)

| Attribut     | Valeur                                                                        |
| ------------ | ----------------------------------------------------------------------------- |
| Expérience   | 2-10 ans en CVC                                                               |
| Tech-savvy   | Variable (moyen)                                                              |
| Équipement   | Smartphone (4G) + parfois tablette                                            |
| Contexte     | Sur le terrain, parfois en sous-sol sans réseau                               |
| Tâches       | Interventions, dépannage, maintenance, installation                           |
| Besoin       | Rapidité, simplicité, pas de double saisie                                    |
| Frustrations | Papier qui se perd, photos sur le téléphone perso, rapports à refaire le soir |

**Journée type :**

1. Le matin : regarde les jobs planifiés du jour
2. Arrivé chez le client : ouvre la fiche client, consulte l'historique
3. Avant intervention : prend des photos, fait la checklist pré
4. Pendant : note les matériaux utilisés
5. Après : prend des photos, checklist post, observations
6. En partant : montre le rapport au client, envoie le lien d'avis
7. Le soir : vérifie que tous les jobs sont bien terminés

---

## 4. Fiches clients

### Champs

| Champ       | Type  | Requis | Description                                |
| ----------- | ----- | ------ | ------------------------------------------ |
| Nom complet | texte | ✓      | Nom du client (ou entreprise)              |
| Téléphone   | texte | ✓      | Portable de préférence                     |
| Email       | email | —      | Pour envoi rapport/avis                    |
| Adresse     | texte | ✓      | Numéro, rue                                |
| Code postal | texte | ✓      |                                            |
| Ville       | texte | ✓      |                                            |
| Notes       | texte | —      | Infos complémentaires (code porte, étage…) |

### Comportement

- Recherche rapide par nom, téléphone, adresse
- Depuis la fiche client : voir tous les jobs passés (historique)
- Un clic → créer un nouveau job pour ce client

### Maquette fiche client

```
┌──────────────────────────────────────┐
│  ← Clients        M. DUPONT         │
│                    ✏️ Modifier       │
├──────────────────────────────────────┤
│                                      │
│  📞 06 12 34 56 78                   │
│  ✉️  dupont@email.fr                 │
│  📍 12 rue de Paris, 75001 Paris    │
│  📝 Code porte B4, 3e étage         │
│                                      │
├──────────────────────────────────────┤
│  HISTORIQUE (3 interventions)        │
│                                      │
│  15/05/2026  Panne clim    ✅        │
│  02/03/2026  Maintenance   ✅        │
│  10/12/2025  Installation  ✅        │
│                                      │
├──────────────────────────────────────┤
│  [+ Nouveau job]                     │
└──────────────────────────────────────┘
```

---

## 5. Jobs / Interventions

### Champs

| Champ              | Type  | Requis | Description                    |
| ------------------ | ----- | ------ | ------------------------------ |
| Client             | FK    | ✓      | Client concerné                |
| Titre              | texte | ✓      | Ex: "Panne clim salon"         |
| Description        | texte | —      | Description détaillée          |
| Statut             | enum  | ✓      | planifié, en_cours, terminé    |
| Priorité           | enum  | —      | basse, normale, haute, urgente |
| Date planifiée     | date  | ✓      | Quand le job doit être fait    |
| Heure début prévue | heure | —      | Créneau                        |
| Heure fin prévue   | heure | —      | Créneau                        |

### Workflow de statuts

```
┌──────────┐      ┌───────────┐      ┌──────────┐
│ PLANIFIÉ │ ───→ │ EN COURS  │ ───→ │ TERMINÉ  │
└──────────┘      └───────────┘      └──────────┘
                       │
                       │ (annulation)
                       ▼
                  ┌──────────┐
                  │ ANNULÉ   │
                  └──────────┘
```

- **Planifié** : le job est créé, en attente
- **En cours** : le technicien est sur place (déclenche le timer)
- **Terminé** : intervention finie, rapport généré
- **Annulé** : intervention annulée (ne pas supprimer, garder trace)

### Liste des jobs (vue planning)

```
┌──────────────────────────────────────────┐
│  Jobs > Aujourd'hui (15/05/2026)         │
│                                          │
│  Filtres : [Tous statuts ▾] [Date ▾]    │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ 🔴 HAUTE  14:00-16:00              │  │
│  │ Panne clim — M. DUPONT             │  │
│  │ 12 rue de Paris, 75001 Paris       │  │
│  │ [▶ Démarrer]                       │  │
│  ├────────────────────────────────────┤  │
│  │ 🟡 NORMALE  10:00-12:00            │  │
│  │ Maintenance — M. MARTIN            │  │
│  │ 5 av. des Lilas, 69002 Lyon        │  │
│  │ [▶ Démarrer]                       │  │
│  ├────────────────────────────────────┤  │
│  │ 🟢 BASSE  09:00-10:00              │  │
│  │ Diagnostic — Sté BATI-PRO         │  │
│  │ 28 rue du Commerce, 33000 Bordeaux │  │
│  │ [Terminé ✅]                       │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [+ Nouveau job]                         │
└──────────────────────────────────────────┘
```

---

## 6. Formulaire d'inspection

### Checklist pré-intervention

Liste d'items à vérifier avant de commencer le travail :

| Item                           | Type         | Obligatoire |
| ------------------------------ | ------------ | ----------- |
| État général de l'installation | ✅/❌ + note | ✓           |
| Équipement sous tension coupé  | ✅/❌ + note | ✓           |
| Zone de travail sécurisée      | ✅/❌ + note | ✓           |
| Accès dégagé                   | ✅/❌ + note | —           |
| Photo avant (min. 1)           | 📷           | ✓           |

### Checklist post-intervention

| Item                       | Type         | Obligatoire |
| -------------------------- | ------------ | ----------- |
| Installation fonctionnelle | ✅/❌ + note | ✓           |
| Nettoyage zone effectué    | ✅/❌ + note | ✓           |
| Pièces remplacées notées   | ✅/❌ + note | —           |
| Photo après (min. 1)       | 📷           | ✓           |
| Explication client faite   | ✅/❌ + note | ✓           |

### Maquette checklist

```
┌──────────────────────────────────────┐
│  Inspection > Job #42                │
│                                      │
│  [PRÉ-INTERVENTION]                  │
│                                      │
│  ☑ État général                     │
│    [RAS, installation propre____]   │
│                                      │
│  ☑ Équipement hors tension          │
│    [Disjoncteur coupé__________]    │
│                                      │
│  ☑ Zone sécurisée                   │
│    [OK_________________________]    │
│                                      │
│  ☑ Accès dégagé                     │
│    [______________________________]  │
│                                      │
│  Photos avant (2)                    │
│  ┌──────┐ ┌──────┐                  │
│  │      │ │      │                  │
│  └──────┘ └──────┘                  │
│  [+ Ajouter photo]                   │
│                                      │
│  [POST-INTERVENTION]  ▾              │
└──────────────────────────────────────┘
```

---

## 7. Photos avant/après

### Comportement

- Capture directe depuis l'appareil photo du smartphone
- Upload automatique vers le serveur
- Tag automatique : `avant` ou `après`
- Affichage côte à côte dans le rapport PDF
- Horodatage automatique

### Spécifications techniques

- Format : JPEG, max 5 Mo par photo
- Stockage : système de fichiers ou S3-compatible
- Miniatures générées pour les listes
- Photos associées au job (pas au client directement)

---

## 8. Rapport post-intervention

### Contenu généré automatiquement

Le rapport PDF inclut :

```
┌─────────────────────────────────────────┐
│  RAPPORT D'INTERVENTION                 │
│  Job #42 — Panne clim                   │
├─────────────────────────────────────────┤
│  CLIENT                                 │
│  M. Dupont                              │
│  12 rue de Paris, 75001 Paris           │
│  📞 06 12 34 56 78                      │
├─────────────────────────────────────────┤
│  INTERVENTION                           │
│  Date : 15/05/2026                      │
│  Heure début : 14:05                    │
│  Heure fin : 15:45                      │
│  Durée : 1h40                           │
│  Technicien : Guuleed Liban             │
├─────────────────────────────────────────┤
│  MATÉRIAUX UTILISÉS                     │
│  • Filtre à air HEPA — 1 unité          │
│  • Gaz R410A — 0.5 kg                   │
│  • Joint silicone — 1 tube              │
├─────────────────────────────────────────┤
│  OBSERVATIONS                           │
│  Filtre complètement encrassé.          │
│  Recharge gaz nécessaire.               │
│  Fonctionnement OK après intervention.  │
├─────────────────────────────────────────┤
│  PHOTOS AVANT/APRÈS                     │
│  [photo1] [photo2]  [photo3] [photo4]   │
├─────────────────────────────────────────┤
│  CHECKLIST                              │
│  Pré : tout OK                          │
│  Post : tout OK                         │
│  Signature client : _____________       │
└─────────────────────────────────────────┘
```

### Champs du rapport

| Champ               | Source                        |
| ------------------- | ----------------------------- |
| Client              | Fiche client                  |
| Date, heures, durée | Job (timer auto)              |
| Technicien          | Utilisateur connecté          |
| Matériaux           | Saisie par le technicien      |
| Observations        | Saisie libre                  |
| Photos              | Upload pendant l'intervention |
| Checklist           | Formulaire d'inspection       |

### Saisie des matériaux

```
┌──────────────────────────────────────────┐
│  Matériaux utilisés                      │
│                                          │
│  Filtre à air HEPA     [1]  [✕]         │
│  Gaz R410A             [0.5][✕]         │
│  Joint silicone        [1]  [✕]         │
│                                          │
│  [+ Ajouter un matériau]                 │
└──────────────────────────────────────────┘
```

Chaque matériau : nom libre + quantité (nombre ou texte).

---

## 9. Avis / Review client

### Workflow

```
1. Job terminé → bouton "Partager avis"
2. Génération d'un lien unique et court
3. Le technicien envoie le lien au client (SMS, email, QR code)
4. Le client ouvre le lien → page publique
5. Le client donne une note (1-5 ⭐) + commentaire
6. L'avis est rattaché au job et au client
```

### Page publique d'avis

```
┌──────────────────────────────────────┐
│         Votre avis compte !          │
│                                      │
│  Intervention du 15/05/2026          │
│  Technicien : Guuleed Liban          │
│                                      │
│  Quelle note donneriez-vous ?        │
│  ☆ ☆ ☆ ☆ ☆   (4/5)                  │
│                                      │
│  Un commentaire ?                    │
│  ┌────────────────────────────────┐  │
│  │ Travail propre et rapide !     │  │
│  │ Merci au technicien.           │  │
│  └────────────────────────────────┘  │
│                                      │
│  Nom (optionnel) : [M. Dupont____]   │
│                                      │
│           [Envoyer mon avis]         │
└──────────────────────────────────────┘
```

### Spécifications

- Pas d'authentification requise (lien unique = accès)
- Lien valide 30 jours après la fin du job
- Un avis par job maximum
- Affichage de la moyenne + derniers avis sur la fiche client

---

## 10. User stories

```
En tant que technicien,
Je veux consulter la fiche d'un client avant d'arriver,
Afin de connaître son adresse, son code de porte
et l'historique de ses interventions passées.

Critères d'acceptation :
- Recherche rapide par nom ou téléphone
- Affichage de l'adresse en évidence (pour le GPS)
- Notes visibles (code porte, étage...)
- Historique des jobs dans l'ordre chronologique inverse
```

```
En tant que technicien,
Je veux démarrer un job d'un simple clic,
Afin de déclencher le chronomètre et passer en statut "en cours".

Critères d'acceptation :
- Bouton "Démarrer" depuis la liste ou la fiche job
- Le statut passe à "en cours"
- L'heure de début est enregistrée automatiquement
```

```
En tant que technicien,
Je veux prendre des photos avant et après mon intervention,
Afin de documenter l'état de l'installation et justifier mon travail.

Critères d'acceptation :
- Appareil photo natif du smartphone
- Upload automatique (pas de manipulation)
- Tag avant/après automatique selon l'étape
- Photos visibles dans le rapport final
```

```
En tant que technicien,
Je veux remplir une checklist rapide,
Afin de ne rien oublier et de standardiser mes interventions.

Critères d'acceptation :
- Liste de points à cocher (✅/❌)
- Note possible par point
- Pas de scroll infini (5-6 items max par section)
```

```
En tant que technicien,
Je veux générer un rapport PDF en un clic à la fin du job,
Afin de le remettre au client ou de l'archiver.

Critères d'acceptation :
- Rapport inclut toutes les infos du job
- Photos intégrées
- Checklist résumée
- Téléchargement / partage direct
```

```
En tant que technicien,
Je veux envoyer un lien d'avis au client après l'intervention,
Afin de recueillir sa satisfaction et valoriser mon travail.

Critères d'acceptation :
- Génération d'un lien unique
- Page publique simple (note + commentaire)
- Avis visible sur la fiche client
```

---

## 11. Workflows

### Workflow complet : une intervention de A à Z

```
1. MATIN — CONSULTATION DU PLANNING
─────────────────────────────────────
Ouvrir l'app → Jobs → Filtre "Aujourd'hui"
→ Voir les 3 jobs du jour avec adresses
→ Cliquer sur le 1er → fiche client → voir notes
→ GPS → se rendre chez le client

2. ARRIVÉE — DÉMARRAGE
─────────────────────────
Sur place → ouvrir le job → [▶ Démarrer]
→ Statut passe à "en cours" → timer lancé
→ Checklist pré-intervention :
  ☑ État général OK, ☑ Hors tension, ☑ Zone sécurisée
→ Photos avant (2 photos, appareil photo natif)

3. PENDANT — SAISIE MATÉRIAUX
───────────────────────────────
→ Ajouter les matériaux au fur et à mesure
  • Filtre HEPA x1
  • Gaz R410A x0.5

4. FIN — CLÔTURE
───────────────────
→ Checklist post-intervention :
  ☑ Installation OK, ☑ Nettoyage fait, ☑ Explication client
→ Photos après (2 photos)
→ Observations : "Filtre encrassé remplacé, recharge gaz."
→ [Terminer le job] → timer stop → durée calculée

5. RAPPORT + AVIS
───────────────────
→ [📄 Rapport PDF] → génération automatique
→ Montrer au client ou envoyer par email
→ [⭐ Demander un avis] → lien généré
→ SMS au client : "Merci ! Donnez votre avis : https://..."
→ Job terminé ✅
```

### Workflow : le technicien en mode urgence

```
1. Appel du client → recherche rapide par téléphone
2. Client inconnu → [+ Nouveau client] → saisie express (nom + tél + adresse)
3. [+ Nouveau job] → priorité "urgente", titre, description
4. [▶ Démarrer] immédiatement
5. Intervention → checklist + photos
6. [Terminer] → rapport généré
7. Lien avis envoyé

Temps total hors intervention : < 2 minutes
```

---

## 12. Maquettes fonctionnelles

### Dashboard / Accueil

```
┌──────────────────────────────────────┐
│  Bonjour, Jean !                     │
│                        📅 15/05/2026 │
├──────────────────────────────────────┤
│                                      │
│  AUJOURD'HUI                         │
│  ┌────────────────────────────────┐  │
│  │ 📋 3 jobs planifiés             │  │
│  │ ▶  1 en cours                   │  │
│  │ ✅ 2 terminés                    │  │
│  └────────────────────────────────┘  │
│                                      │
│  PROCHAIN JOB                        │
│  ┌────────────────────────────────┐  │
│  │ 🔴 HAUTE  14:00                 │  │
│  │ Panne clim — M. DUPONT          │  │
│  │ 12 rue de Paris, 75001 Paris    │  │
│  │ 📞 06 12 34 56 78              │  │
│  │              [▶ Démarrer]       │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ 🟡 NORMALE  10:00 (en cours)   │  │
│  │ Maintenance — M. MARTIN         │  │
│  │ ⏱  1h12 écoulées               │  │
│  │              [Terminer]         │  │
│  └────────────────────────────────┘  │
├──────────────────────────────────────┤
│  [+ Nouveau job]  [📁 Clients]       │
└──────────────────────────────────────┘
```

### Navigation (mobile-first)

```
┌──────────────────────────────┐
│  Tervo                   │ ← TopBar (fixe)
├──────────────────────────────┤
│                              │
│                              │
│    CONTENU DE LA PAGE        │
│                              │
│                              │
│                              │
│                              │
├──────────────────────────────┤
│  🏠     📋     📁     👤     │ ← Bottom nav
│ Accueil Jobs  Clients Profil │
└──────────────────────────────┘
```

---

> **Document créé le 03/06/2026**
> **Version :** 3.0 (Refonte MVP)
> **Document technique associé :** `02-spec-technique.md`
