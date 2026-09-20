# Tervo — Spécification Fonctionnelle

> **Objet :** Périmètre fonctionnel, personas, modules et user stories de Tervo.
>
> **Documents liés :** `04-architecture.md`, `05-data-model.md`, `06-workflows.md`

---

## Sommaire

1. Vision produit
2. Périmètre
3. Personas
4. Fiches clients
5. Jobs / Interventions
6. Formulaire d'inspection
7. Photos avant/après
8. Rapport post-intervention
9. Avis / Review client
10. Catalogue produits & exposition
11. Devis et Factures *(phase 2)*
12. Bilans *(phase 2)*
13. Import de l'historique Excel
14. Administration
15. User stories
16. Workflows

---

## 1. Vision produit

Application **mobile-first** permettant aux techniciens CVC de gérer leurs interventions quotidiennes :

- Retrouver les clients et leur historique avant d'intervenir
- Suivre les interventions avec un workflow de statuts clair
- Standardiser les inspections avec des checklists
- Capturer des photos avant/après
- Générer un rapport d'intervention professionnel
- Recueillir l'avis du client via un lien de partage
- Présenter un catalogue produits et gérer l'exposition en salle

L'application remplace le carnet papier, l'appareil photo et l'envoi de rapport par email.

---

## 2. Périmètre

### Modules

| Module | Priorité | Description |
|--------|:--------:|-------------|
| **Clients** | P0 | Fiches, recherche, historique |
| **Interventions** | P0 | CRUD, statuts, planning |
| **Inspection** | P0 | Checklists pré/post, notes |
| **Photos** | P0 | Avant/après, thumbnails |
| **Rapport** | P0 | PDF automatique |
| **Avis client** | P0 | Note + commentaire via lien public |
| **Catalogue produits** | P1 | Fiches produits, exposition en salle |
| **Import Excel** | P1 | Migration de l'historique |
| **Administration** | P2 | Utilisateurs, logs |
| **Devis / Factures** | P2 | Gestion commerciale |
| **Stock** | P2 | Quantités, mouvements |
| **Fournisseurs / SAV** | P2 | Contrats, garanties |

### Hors périmètre actuel

- Comptabilité complète (intégration EBP/Sage)
- Gestion RH / plannings avancés
- Portail client autonome
- Application native iOS/Android (PWA suffisante)
- GED documentaire avec OCR

---

## 3. Personas

### 3.1 Technicien CVC (acteur principal)

| Attribut | Valeur |
|----------|--------|
| Expérience | 2-20 ans en CVC |
| Tech-savvy | Variable (moyen) |
| Équipement | Smartphone (4G) + parfois tablette |
| Contexte | Terrain, parfois en sous-sol sans réseau |
| Besoins | Rapidité, simplicité, pas de double saisie |
| Frustrations | Papier perdu, photos sur téléphone perso, rapport à refaire le soir |

**Journée type :**

1. Le matin : consulte les interventions planifiées du jour
2. Arrivé chez le client : ouvre la fiche, consulte l'historique
3. Avant intervention : photos + checklist pré
4. Pendant : note les matériaux utilisés
5. Après : photos, checklist post, observations
6. En partant : montre le rapport, envoie le lien d'avis
7. Le soir : vérifie que tout est terminé

### 3.2 Comptable / Gérant *(phase 2)*

| Attribut | Valeur |
|----------|--------|
| Tech-savvy | Faible à moyen |
| Équipement | PC de bureau |
| Besoins | Devis, facturation, bilans, suivi des paiements |
| Frustrations | Fichiers éparpillés, pas de vue consolidée |

### 3.3 Vendeur / Responsable showroom

| Attribut | Valeur |
|----------|--------|
| Équipement | Tablette ou PC en showroom |
| Besoins | Présenter le catalogue, guider le client, essais |

### 3.4 Client particulier (visiteur showroom)

| Attribut | Valeur |
|----------|--------|
| Situation | Pas encore de devis, vient comparer sur place |
| Besoins | Voir, essayer, comparer les tarifs |

### 3.5 Admin technique

| Attribut | Valeur |
|----------|--------|
| Besoins | Import de données, gestion des utilisateurs, supervision |

---

## 4. Fiches clients

### Champs

| Champ | Type | Requis | Description |
|-------|------|:------:|-------------|
| Nom complet | texte | ✓ | Nom du client (ou entreprise) |
| Téléphone | texte | ✓ | Portable de préférence |
| Email | email | — | Envoi rapport / avis |
| Adresse | texte | ✓ | Numéro, rue |
| Code postal | texte | ✓ | |
| Ville | texte | ✓ | |
| Notes | texte | — | Code porte, étage, remarques |

### Comportement

- Recherche rapide par nom, téléphone, adresse
- Historique des interventions depuis la fiche
- Un clic → créer une nouvelle intervention pour ce client

### Maquette

```
┌──────────────────────────────────────┐
│  ← Clients        M. DUPONT         │
│                    ✏️ Modifier       │
├──────────────────────────────────────┤
│  📞 06 12 34 56 78                   │
│  ✉️  dupont@email.fr                 │
│  📍 12 rue de Paris, 75001 Paris    │
│  📝 Code porte B4, 3e étage         │
├──────────────────────────────────────┤
│  HISTORIQUE (3 interventions)        │
│  15/05/2026  Panne clim    ✅        │
│  02/03/2026  Maintenance   ✅        │
│  10/12/2025  Installation  ✅        │
├──────────────────────────────────────┤
│  [+ Nouvelle intervention]           │
└──────────────────────────────────────┘
```

---

## 5. Jobs / Interventions

### Champs

| Champ | Type | Requis | Description |
|-------|------|:------:|-------------|
| Client | FK | ✓ | Client concerné |
| Titre | texte | ✓ | Ex : « Panne clim salon » |
| Description | texte | — | Description détaillée |
| Statut | enum | ✓ | planifié, en_cours, terminé, annulé |
| Priorité | enum | — | basse, normale, haute, urgente |
| Date planifiée | date | ✓ | Quand l'intervention doit être faite |
| Heure début / fin prévues | heure | — | Créneau |

### Workflow de statuts

```
planifié ──► en_cours ──► terminé
    │            │
    └────────────┴──► annulé
```

**Règles :**
- Passage `planifié → terminé` interdit (il faut démarrer)
- `started_at` renseigné automatiquement au démarrage
- `completed_at` renseigné automatiquement à la clôture
- Clôture impossible sans checklist complète + photos avant/après

### Liste des interventions

Filtres : statut, date, technicien. Tri par date. Pagination.

---

## 6. Formulaire d'inspection

### Checklist pré-intervention

| Item | Exemple de note |
|------|-----------------|
| État général de l'installation | « RAS, installation propre » |
| Équipement hors tension | « Disjoncteur coupé » |
| Zone de travail sécurisée | « OK » |
| Accès dégagé | |

### Checklist post-intervention

| Item | Exemple de note |
|------|-----------------|
| Installation fonctionnelle | « Climatisation OK » |
| Nettoyage effectué | « Zone propre » |
| Explication client faite | « Client satisfait » |

### Maquette

```
┌──────────────────────────────────────┐
│  ← Inspection — Panne clim           │
│  [ Pré ]  [ Post ]                   │
├──────────────────────────────────────┤
│  ☑ État général                      │
│     [RAS, installation propre_____]  │
│  ☑ Équipement hors tension           │
│     [Disjoncteur coupé___________]   │
│  ☐ Zone sécurisée                    │
│     [____________________________]   │
└──────────────────────────────────────┘
```

**Règles :** les items pré et post sont créés automatiquement à la création de l'intervention. Une intervention ne peut être terminée que si tous les items sont cochés.

---

## 7. Photos avant/après

### Comportement

- Upload depuis l'appareil photo du téléphone
- Catégorie forcée selon l'onglet actif (avant / après)
- Thumbnail généré côté serveur
- Minimum : 1 photo avant + 1 photo après pour clôturer

| Format | JPEG, PNG |
|--------|-----------|
| Taille | limitée (validation serveur) |
| Stockage | volume Docker + chemin en base |

---

## 8. Rapport post-intervention

### Contenu généré automatiquement

| Section | Contenu |
|---------|---------|
| En-tête | Logo, coordonnées, numéro de rapport |
| Client | Nom, adresse, téléphone |
| Intervention | Titre, date, heure début/fin, durée |
| Checklist | Items pré et post avec notes |
| Photos | Avant / après |
| Matériaux | Nom, quantité |
| Observations | Texte libre du technicien |
| Pied de page | Mention légale, page X/Y |

### Champs saisis

| Champ | Type | Description |
|-------|------|-------------|
| Observations | texte | Commentaire général |
| Matériaux | liste | Nom + quantité (texte libre) |

> **Signature client** (P2) — non implémentée.

---

## 9. Avis / Review client

### Workflow

1. À la clôture, un `share_token` unique est généré
2. Le technicien copie le lien `/review/{token}` et l'envoie (SMS/email)
3. Le client ouvre le lien (sans authentification)
4. Il note de 1 à 5 étoiles et laisse un commentaire
5. L'avis apparaît sur la fiche client

### Spécifications

| Élément | Valeur |
|---------|--------|
| Authentification | aucune (endpoint public) |
| Token | UUID unique |
| Validité | 30 jours |
| Unicité | un seul avis par intervention |
| Sécurité | token non devinable, vérification de validité |

---

## 10. Catalogue produits & exposition

**Détail complet :** `08-module-catalogue.md`

| Fonctionnalité | Priorité |
|----------------|:--------:|
| Fiche produit (référence, catégorie, marque, prix, photo) | P1 |
| Liste + filtres (catégorie, statut) + recherche | P1 |
| Exposition en salle (emplacement, essai, vendable) | P1 |
| Vue « showroom » par emplacement | P1 |

**Distinctions de modélisation :**

- `statut` (cycle de vie produit : en exposition, en stock, discontinué) ≠ **exposition** (présence en salle)
- `disponible_essai` (essai physique) ≠ `vendable_showroom` (peut être vendu)

---

## 11. Devis et Factures *(phase 2)*

### Devis

| Champ | Description |
|-------|-------------|
| `numero` | Auto — DEV-AAAA-NNNNN |
| `statut` | brouillon, envoyé, accepté, refusé, expiré |
| Lignes | description, quantité, unité, prix unitaire HT |
| Totaux | HT, TVA, TTC |

Workflow : brouillon → envoyé → accepté / refusé / expiré.

### Factures

| Champ | Description |
|-------|-------------|
| `numero` | Auto — FAC-AAAA-NNNNN |
| `statut` | en_attente, payée, retard, annulée |
| `date_echeance` | + 30 jours |
| `date_paiement`, `mode_paiement` | suivi du règlement |

**Positionnement :** gestion commerciale **simplifiée**. Ce n'est pas un logiciel comptable.

---

## 12. Bilans *(phase 2)*

Indicateurs calculés **à la demande** : nombre d'interventions, devis émis/acceptés,
factures émises/payées, total facturé HT/TTC, encaissé, impayé, panier moyen, délai de paiement moyen.

> Pas de cron mensuel prématuré : les bilans sont des requêtes d'agrégation. Une table de snapshot sera introduite si le volume le justifie.

---

## 13. Import de l'historique Excel

### Fonctionnalités

- Upload de fichiers `.xlsx` / `.xls`
- Détection automatique du mapping des colonnes (surchargeable)
- Preview des lignes avant import
- Validation complète (doublons, erreurs, champs manquants)
- Résolution des doublons clients (fuzzy matching)
- Import en **2 passes** (clients → interventions)
- Rapport détaillé post-import
- **Idempotent** : ré-exécutable sans doublon

### Règles d'import

| Règle | Détail |
|-------|--------|
| Doublon client | Score de similarité (≥ 95 auto, 80-95 validation humaine) |
| Job sans client identifiable | → `import_error` avec statut `ORPHAN` (jamais ignoré) |
| Champs obligatoires manquants | Ligne rejetée + loggée |
| Atomicité | Transaction **par batch**, pas globale |
| Idempotence | Hash SHA-256 du fichier |

Détail : `06-workflows.md` §3 et `05-data-model.md` §5.

---

## 14. Administration

| Fonctionnalité | Description |
|----------------|-------------|
| Gestion utilisateurs | Créer / modifier / désactiver des comptes |
| Logs d'import | Historique des imports + anomalies |
| Supervision des backups | Dernier backup, taille, statut |
| Backups manuels | Déclenchement à la demande |

---

## 15. User stories

### 15.1 Technicien

| # | User story | Priorité |
|---|------------|:--------:|
| US-01 | Consulter mon planning du jour | P0 |
| US-02 | Créer une intervention urgente (client existant ou nouveau) | P0 |
| US-03 | Prendre des photos avant/après | P0 |
| US-04 | Générer un rapport d'intervention | P0 |
| US-05 | Envoyer un lien d'avis au client | P0 |

### 15.2 Vendeur / Showroom

| # | User story | Priorité |
|---|------------|:--------:|
| US-06 | Consulter le catalogue produits | P1 |
| US-07 | Voir quels produits sont exposés et essayables | P1 |

### 15.3 Comptable / Gérant *(phase 2)*

| # | User story | Priorité |
|---|------------|:--------:|
| US-08 | Créer un devis | P2 |
| US-09 | Transformer un devis en facture | P2 |
| US-10 | Suivre les paiements | P2 |
| US-11 | Consulter les bilans | P2 |

### 15.4 Admin

| # | User story | Priorité |
|---|------------|:--------:|
| US-12 | Importer l'historique Excel | P1 |
| US-13 | Traiter les anomalies d'import | P1 |
| US-14 | Gérer les utilisateurs | P2 |

---

## 16. Workflows

Le détail des parcours est dans `06-workflows.md` :

1. Intervention de A à Z (5 phases)
2. Intervention urgente (express)
3. Consultation de l'historique client
4. Import de l'historique Excel
5. Parcours showroom
6. Backup & restore
7. Déploiement

---

> **Sommaire :** `00-sommaire.md`
> **Workflows détaillés :** `06-workflows.md`
> **Modèle de données :** `05-data-model.md`
> **Module catalogue :** `08-module-catalogue.md`
