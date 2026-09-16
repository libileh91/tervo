# Spécification Fonctionnelle — MB Chauffage

> **Objet :** Spécification fonctionnelle pour l'application MB Chauffage.
> **Client :** MB Chauffage, entreprise CVC avec 20+ ans d'historique.
> **Projet source :** Tervo (`docs/DAT/specs/01-specs-fonctionnelle.md`)

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
10. **Devis et Factures (module financier)**
11. **Bilans mensuels (tableau de bord financier)**
12. **Import historique Excel**
13. **Administration (users, backups)**
14. User stories
15. Workflows

---

## 1. Vision produit

MB Chauffage passe d'une gestion papier/Excel à une application web centralisée. L'objectif est de :

- **Rassembler 20 ans de données** éparpillées dans des fichiers Excel en une base de données unique
- **Standardiser les processus** de devis, facturation, interventions
- **Donner aux techniciens** un outil mobile simple pour les interventions terrain
- **Donner au gérant/comptable** une vue consolidée de l'activité (bilans mensuels, impayés)
- **Pérenniser les données** avec des backups automatisés

---

## 2. Périmètre

### Modules

| Module | Priorité | Description |
|--------|----------|-------------|
| **Core** | P0 | Auth, Clients, Jobs, Checklist — socle Tervo existant |
| **Data Migration** | P0 | Import 20 ans d'Excels → PostgreSQL |
| **Interventions** | P1 | Photos, Matériaux, Rapport PDF, Avis client |
| **Module Financier** | P1 | Devis, Factures, Bilans |
| **Déploiement Prod** | P1 | VPS, 1Panel, SSL, Backups |
| **Admin** | P2 | Gestion utilisateurs, import, logs |
| **Polish** | P2 | PWA, Dark mode, Signature client, QR codes |

### Hors périmètre MVP

- Module RH (congés, plannings avancés)
- Gestion de stock / inventaire pièces détachées
- Portail client (espace personnel avec historique)
- Intégration comptable (exports EBP, Sage, etc.)
- Application native mobile (iOS/Android) — la PWA suffit

---

## 3. Personas

### 3.1 Technicien CVC

- 3-5 techniciens, expérience 2-20 ans
- Utilise l'app sur smartphone (4G) pendant les interventions
- Besoins : planning du jour, fiche client, checklist, photos, rapport

### 3.2 Comptable / Gérant

- 1 personne, utilise un PC de bureau
- Besoins : créer des devis, facturer, suivre les paiements, consulter les bilans
- N'a jamais utilisé d'outil de gestion moderne — Excel uniquement

### 3.3 Admin technique

- Gère les utilisateurs, les imports de données, les sauvegardes
- Besoins : interface d'import Excel, dashboard de monitoring

---

## 4. Fiches clients

### Champs

| Champ | Type | Obligatoire | Note |
|-------|------|-------------|------|
| `full_name` | Texte | ✅ | Nom complet ou entreprise |
| `phone` | Téléphone | ✅ | Format libre |
| `email` | Email | | |
| `address` | Adresse | ✅ | |
| `postal_code` | Code postal | | |
| `city` | Ville | | |
| `siret` | SIRET | Si pro | 14 chiffres |
| `tva_intra` | TVA intra | Si pro | FRXX... |
| `type` | Liste | ✅ | particulier / professionnel |
| `notes` | Texte long | | Code porte, étage, etc. |

### Comportement

- Recherche par nom, téléphone, adresse
- Historique des interventions avec notes et avis
- Historique des devis et factures

---

## 5. Jobs / Interventions

Même modèle que Tervo, avec ces ajouts :

- `devis_id` : si l'intervention est liée à un devis accepté
- `facture_id` : si l'intervention a été facturée

### Workflow de statuts

```
planifié → en_cours → terminé
              ↓
           annulé
```

---

## 6. Formulaire d'inspection

Identique à Tervo (checklist pré/post intervention).

---

## 7. Photos avant/après

Identique à Tervo (upload multipart, thumbnails, min. 1 avant + 1 après).

---

## 8. Rapport post-intervention

Identique à Tervo (génération PDF automatique avec WeasyPrint).

---

## 9. Avis / Review client

Identique à Tervo (lien public avec token unique, note 1-5 + commentaire).

---

## 10. Devis et Factures (module financier)

### 10.1 Devis

**Champs :**

| Champ | Type | Description |
|-------|------|-------------|
| `numero` | Auto | DEV-AAAA-NNNNN |
| `client_id` | FK | Client concerné |
| `date_emission` | Date | Date de création |
| `date_validite` | Date | Date d'expiration (+30j) |
| `statut` | Énum | brouillon, envoyé, accepté, refusé, expiré |
| `lignes` | Liste | Description, quantité, prix unitaire |
| `montant_ht` | Calculé | Somme des lignes |
| `montant_ttc` | Calculé | HT + TVA |

**Workflow :**

1. Créer un devis (brouillon)
2. Ajouter des lignes (description, qté, prix HT)
3. Générer le PDF
4. Envoyer au client (email)
5. Statut : Envoyé
6. Client accepte → Statut : Accepté
7. Possibilité de créer le job + la facture

### 10.2 Factures

**Champs :**

| Champ | Type | Description |
|-------|------|-------------|
| `numero` | Auto | FAC-AAAA-NNNNN |
| `client_id` | FK | Client |
| `devis_id` | FK nullable | Devis source |
| `date_emission` | Date | |
| `date_echeance` | Date | +30j |
| `statut` | Énum | en_attente, payée, retard, annulée |
| `lignes` | Liste | Reprise du devis ou saisie manuelle |
| `montant_ht` | Calculé | |
| `montant_ttc` | Calculé | |
| `date_paiement` | Date | Date de règlement |
| `mode_paiement` | Liste | virement, chèque, espèces, CB |

**Workflow :**

1. Créer une facture (depuis un devis accepté ou de zéro)
2. Générer le PDF
3. Envoyer au client
4. Suivi : en_attente → payée (ou retard si date dépassée)
5. Dashboard des impayés avec alertes

### 10.3 Génération PDF

Les devis et factures utilisent un template HTML professionnel avec :

- Logo MB Chauffage
- Coordonnées de l'entreprise (SIRET, TVA, adresse)
- Coordonnées du client
- Tableau des lignes avec totaux HT, TVA, TTC
- Mentions légales (TVA, conditions de paiement)
- Date d'échéance pour les factures
- Date de validité pour les devis

---

## 11. Bilans mensuels (tableau de bord financier)

### 11.1 KPIs

| Indicateur | Description |
|------------|-------------|
| Nombre d'interventions | Jobs terminés dans le mois |
| Nombre de devis émis | Nouveaux devis créés |
| Taux de conversion devis | % de devis acceptés |
| Nombre de factures émises | |
| Total facturé HT / TTC | |
| Total encaissé | Somme des factures payées |
| Total impayé | Somme des factures en retard |
| Panier moyen HT | Montant moyen par intervention |
| Délai de paiement moyen | Jours entre émission et paiement |

### 11.2 Calcul automatique

Un CRON mensuel (1er du mois à 2h00) calcule le bilan du mois précédent et le stocke dans la table `bilan`.

### 11.3 Affichage

Dashboard avec graphiques (courbes d'évolution, barres mensuelles, camembert statuts).

---

## 12. Import historique Excel

### 12.1 Fonctionnalités

- Upload de fichiers `.xlsx` ou `.xls`
- Détection automatique du mapping des colonnes
- Preview des 10 premières lignes avant import
- Validation complète (doublons, erreurs, champs obligatoires)
- Résolution manuelle des doublons clients (fuzzy matching)
- Import en 2 passes (clients → jobs)
- Rapport détaillé post-import (créés, ignorés, erreurs)
- Idempotent : ré-exécutable sans doublons

### 12.2 Formats acceptés

| Type | Description |
|------|-------------|
| Clients | Liste des clients avec coordonnées |
| Jobs | Historique des interventions |
| Mixte | Fichier combinant clients + jobs (le plus courant) |
| Devis | Devis historiques |
| Factures | Factures historiques |

### 12.3 Règles d'import

- Un client est considéré comme doublon si nom + téléphone matchent à 90% (fuzzy)
- Les jobs orphelins (client non trouvé) sont ignorés avec warning
- Les champs obligatoires manquants bloquent la ligne (pas d'import partiel)
- L'import est transactionnel : tout ou rien par lot

---

## 13. Administration

### 13.1 Gestion utilisateurs

- Créer / Modifier / Désactiver des comptes techniciens
- Créer des comptes comptables
- Réinitialiser les mots de passe

### 13.2 Logs d'import

- Historique de tous les imports (fichier, date, résultat, erreurs)
- Consultation du détail des erreurs par ligne

### 13.3 Backups

- Dashboard de statut des backups (dernier backup réussi, taille)
- Possibilité de déclencher un backup manuel
- Possibilité de restaurer un backup (admin uniquement)

---

## 14. User Stories

### US-01 — En tant que technicien, je veux consulter mon planning du jour
- Dashboard avec jobs du jour, statuts, prochain job
- Priorité : P0

### US-02 — En tant que technicien, je veux créer une intervention urgente
- Recherche rapide client → création job → démarrage immédiat
- Priorité : P0

### US-03 — En tant que technicien, je veux prendre des photos avant/après
- Upload depuis l'appareil photo du téléphone
- Priorité : P1

### US-04 — En tant que technicien, je veux générer un rapport d'intervention
- PDF automatique avec photos, checklist, matériaux
- Priorité : P1

### US-05 — En tant que comptable, je veux créer un devis
- Interface avec lignes dynamiques, calcul auto des totaux
- Priorité : P1

### US-06 — En tant que comptable, je veux transformer un devis en facture
- Un clic depuis le devis accepté
- Priorité : P1

### US-07 — En tant que comptable, je veux suivre les paiements
- Dashboard des factures en attente et en retard
- Priorité : P1

### US-08 — En tant que gérant, je veux consulter les bilans mensuels
- KPIs : CA, interventions, panier moyen, impayés
- Priorité : P1

### US-09 — En tant qu'admin, je veux importer l'historique Excel
- Upload → preview → validation → import
- Priorité : P0 (données historiques critiques)

### US-10 — En tant qu'admin, je veux gérer les utilisateurs
- CRUD utilisateurs, rôles, activation/désactivation
- Priorité : P2

---

## 15. Workflows

Voir `06-workflows.md` pour le détail des workflows :

1. Intervention complète de A à Z
2. Import historique Excel
3. Création devis → facture
4. Backup & restore
5. Déploiement production

---

> **Document mis à jour le 12/07/2026**
> **Version :** 1.0 (DAT MB Chauffage)
> **Projet source :** `Tervo/docs/DAT/specs/01-specs-fonctionnelle.md`
> **Documents liés :** `06-workflows.md`, `03-api-spec.md`
