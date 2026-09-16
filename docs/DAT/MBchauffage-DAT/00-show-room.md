# 8. Module ShowRoom — MB Chauffage

> **Objet :** Extension fonctionnelle et technique du DAT MB Chauffage — module Showroom pour clients particuliers.
> **Origine :** concept porté par Badi.
> **Complète :** `01-specs-fonctionnelle.md` (périmètre, personas), `05-data-model.md` (nouvelles entités), `04-architecture.md` (note technique §10).

---

## Sommaire

1. Vision & positionnement
2. Périmètre — modules ajoutés
3. Personas additionnels
4. Modèle de données
5. Parcours client showroom (workflow)
6. Gestion des stocks
7. Gestion fournisseurs
8. SAV, garanties & contrats
9. User stories
10. Note d'architecture — faut-il ajouter du Go ?

---

## 1. Vision & positionnement

MB Chauffage dispose déjà d'un outil terrain (techniciens) et d'un module financier (devis/factures) pour des clients déjà engagés dans une démarche de devis. Le **Showroom** cible un public différent : le particulier qui n'a pas encore de devis en tête et veut **voir, toucher, comparer** avant de se décider — climatisation, chaudières, PAC, etc.

Objectif : transformer une visite showroom en devis qualifié, puis suivre le produit vendu sur tout son cycle de vie — installation → garantie → maintenance — en réutilisant les modules Jobs, Devis et Avis client déjà existants plutôt qu'en les dupliquant.

---

## 2. Périmètre — modules ajoutés

| Module                        | Priorité | Description                                                        |
| ------------------------------ | -------- | -------------------------------------------------------------------- |
| **Catalogue Produits**        | P1       | Fiches produits (clim, chauffage, PAC...), photos, tarifs           |
| **Exposition Showroom**       | P1       | Association produit ↔ salle d'exposition, disponibilité à l'essai |
| **Stock**                     | P1       | Quantités, mouvements, seuils d'alerte                              |
| **Fournisseurs**              | P2       | Fiches fournisseurs, contrats, commandes                            |
| **SAV / Garanties & Contrats**| P1       | Garantie constructeur, extension, contrats d'entretien              |
| **Visites Showroom**          | P2       | Traçabilité des passages en showroom, taux de transformation        |

> ⚠️ **Le module Stock était explicitement exclu du MVP** (cf. `01-specs-fonctionnelle.md` §2, "Hors périmètre MVP"). Le Showroom le rend nécessaire : on ne peut pas exposer et vendre un produit sans savoir ce qu'il reste en stock. C'est un changement de périmètre assumé, pas un oubli.

---

## 3. Personas additionnels

### 3.4 Client particulier (visiteur showroom)

- Pas encore de devis en tête, vient comparer sur place
- Besoin : voir le produit, l'essayer si possible, comparer les tarifs
- Décision d'achat souvent prise en showroom ou juste après

### 3.5 Vendeur / Responsable showroom

- Badi ou un commercial dédié
- Besoins : accueillir, présenter le catalogue, transformer une visite en devis
- Utilise l'app sur tablette ou PC en showroom

### 3.6 Responsable stock & appro

- Peut être la même personne que le comptable au démarrage
- Besoins : suivre les niveaux de stock, déclencher les commandes fournisseurs

---

## 4. Modèle de données (nouvelles entités)

### 4.1 `produit`

| Champ              | Type    | Obligatoire | Note                                    |
| ------------------- | ------- | ----------- | ---------------------------------------- |
| `reference`         | Texte   | ✅          | Référence interne ou constructeur       |
| `nom`               | Texte   | ✅          |                                          |
| `categorie`         | Liste   | ✅          | clim, chaudière, PAC, chauffage, autre  |
| `marque`            | Texte   |             |                                          |
| `fournisseur_id`    | FK      |             | → `fournisseur`                         |
| `prix_achat_ht`     | Décimal |             |                                          |
| `prix_vente_ht`     | Décimal | ✅          |                                          |
| `photo`             | Fichier |             |                                          |
| `statut`            | Liste   | ✅          | en_exposition, en_stock, discontinué   |

### 4.2 `exposition_showroom`

| Champ                | Type    | Note                                         |
| ---------------------- | ------- | ----------------------------------------------- |
| `produit_id`           | FK      | → `produit`                                    |
| `emplacement`          | Texte   | Zone du showroom                                |
| `disponible_essai`     | Bool    | Le client peut le tester sur place              |
| `vendable_showroom`    | Bool    | Vendable immédiatement ou démo uniquement seulement |
| `date_installation_demo` | Date  |                                                  |

### 4.3 `stock` et `mouvement_stock`

| Champ (`stock`)         | Type    | Note                              |
| -------------------------- | ------- | ------------------------------------ |
| `produit_id`               | FK      |                                      |
| `quantite_disponible`      | Entier  |                                      |
| `quantite_reservee`        | Entier  | Réservé sur devis accepté           |
| `emplacement_stock`        | Texte   | Entrepôt / zone                     |
| `seuil_alerte`              | Entier  | Déclenche une alerte de réappro     |

| Champ (`mouvement_stock`) | Type  | Note                                                                    |
| ---------------------------- | ----- | -------------------------------------------------------------------------- |
| `produit_id`                 | FK    |                                                                              |
| `type`                       | Énum  | reception_fournisseur, vente_installation, affectation_showroom, ajustement |
| `quantite`                   | Entier | Positif ou négatif selon le sens                                          |
| `date`                       | Date  |                                                                              |
| `reference_liee`             | FK    | `job_id` ou `commande_fournisseur_id` selon le type                        |

### 4.4 `fournisseur` et `contrat_fournisseur`

| Champ (`fournisseur`)   | Type  | Note              |
| --------------------------- | ----- | -------------------- |
| `nom`                       | Texte | ✅                   |
| `siret`                     | Texte |                       |
| `contact`, `telephone`, `email` | Texte |                   |
| `delai_livraison_moyen`     | Entier | En jours             |

| Champ (`contrat_fournisseur`) | Type  | Note                                    |
| --------------------------------- | ----- | ------------------------------------------- |
| `fournisseur_id`                  | FK    |                                              |
| `date_debut` / `date_fin`         | Date  |                                              |
| `tarif_negocie`                   | Texte | Grille tarifaire ou remise                  |
| `conditions`                      | Texte | Paiement, retour, garantie fournisseur      |

### 4.5 `contrat_sav`

| Champ            | Type  | Note                                                    |
| ------------------- | ----- | ------------------------------------------------------------ |
| `client_id`         | FK    |                                                                |
| `produit_id`        | FK    | Produit vendu concerné                                        |
| `job_id`            | FK    | Job d'installation d'origine                                  |
| `type`               | Énum  | garantie_constructeur, extension_garantie, contrat_entretien |
| `date_debut` / `date_fin` | Date |                                                          |
| `periodicite_maintenance` | Liste | Si contrat d'entretien (annuelle, semestrielle...)      |
| `statut`             | Énum  | actif, expiré, résilié                                        |

### 4.6 `visite_showroom`

| Champ            | Type  | Note                                       |
| ------------------- | ----- | --------------------------------------------- |
| `client_id`         | FK nullable | Si le visiteur n'est pas encore identifié |
| `date_visite`       | Date  |                                                |
| `produits_vus`      | Liste (FK) | Produits présentés                       |
| `vendeur_id`        | FK    | Utilisateur ayant reçu le client              |
| `suite_donnee`      | Bool  | Un devis a-t-il été créé suite à la visite   |

---

## 5. Parcours client showroom (workflow)

```
visite_showroom créée
        ↓
   produits présentés + essai (exposition_showroom)
        ↓
   intérêt confirmé ?
     ↙            ↘
   non              oui
    ↓                ↓
 fin de visite    devis créé (module existant, lignes liées à produit_id)
 (suite_donnee=false)   ↓
                  devis accepté
                        ↓
              job d'installation (lié au produit vendu → mouvement_stock "vente_installation")
                        ↓
              contrat_sav créé (garantie + option entretien)
                        ↓
              maintenance périodique (jobs récurrents liés au contrat_sav)
                        ↓
              avis client (module existant, déclenché après installation ET après chaque
              intervention de maintenance)
```

Ce parcours ne crée aucun nouveau module de facturation ou d'intervention : il **relie** le catalogue produit aux modules Devis, Jobs et Avis client déjà spécifiés.

---

## 6. Gestion des stocks

- Chaque mouvement de stock (réception, vente, affectation showroom, ajustement d'inventaire) est journalisé dans `mouvement_stock` — jamais de modification directe de `quantite_disponible` sans ligne de mouvement associée (traçabilité).
- Alerte automatique quand `quantite_disponible < seuil_alerte` (même moteur cron que les bilans mensuels).
- Un produit exposé en showroom peut être **démo uniquement** (`vendable_showroom = false`, ex. un modèle d'exposition qui ne part jamais en installation) ou **vendable sur place** (`vendable_showroom = true`).

---

## 7. Gestion fournisseurs

- Fiche fournisseur + contrat cadre (tarifs négociés, délais).
- Une commande fournisseur suit un statut simple : `brouillon → envoyée → confirmée → reçue (partielle ou totale)`.
- La réception d'une commande génère automatiquement les lignes `mouvement_stock` correspondantes — pas de double saisie.

---

## 8. SAV, garanties & contrats

- `contrat_sav` distingue la garantie constructeur (souvent 2 ans, gratuite), l'extension de garantie (payante) et le contrat d'entretien (périodique, ex. visite annuelle obligatoire pour les PAC).
- Les échéances (garantie qui expire, entretien à planifier) utilisent le même mécanisme d'alerte que le stock — un seul moteur de notifications pour tout le système plutôt qu'un par module.
- Le suivi de satisfaction réutilise le module "Avis / Review client" existant : pas de nouveau système de notation à construire.

---

## 9. User stories

### US-11 — En tant que vendeur, je veux enregistrer une visite showroom

- Client identifié ou anonyme, produits vus, intérêt noté
- Priorité : P2

### US-12 — En tant que vendeur, je veux transformer une visite en devis

- Depuis la fiche visite, créer un devis pré-rempli avec les produits vus
- Priorité : P1

### US-13 — En tant que responsable stock, je veux être alerté quand un produit passe sous le seuil

- Notification dashboard + email
- Priorité : P1

### US-14 — En tant que responsable stock, je veux enregistrer une réception fournisseur

- Mise à jour automatique du stock, traçabilité du mouvement
- Priorité : P1

### US-15 — En tant que gérant, je veux suivre les contrats de garantie/entretien actifs

- Liste filtrable, alertes d'échéance à 30 jours
- Priorité : P1

### US-16 — En tant que comptable, je veux voir le taux de transformation showroom → devis

- Ajout d'un KPI aux bilans mensuels existants (`visite_showroom.suite_donnee`)
- Priorité : P2

---

## 10. Note d'architecture — faut-il ajouter du Go ?

Le stack actuel (Python/FastAPI + Vue.js) reste le socle : Clients, Jobs, Devis, Factures, Avis restent en Python — ce sont des CRUD classiques avec beaucoup de logique métier partagée, pas d'intérêt à les réécrire.

Le module **Stock** est le seul candidat raisonnable pour un service Go séparé :

- Frontière nette : le Stock ne touche presque rien du reste (juste `produit_id` et `job_id` en référence), donc un microservice indépendant ne casse pas le monolithe existant.
- Réutilise tes acquis Go réels (Chi, Gorm/SqlC, JWT) plutôt qu'un apprentissage from scratch.
- Donne un vrai argument d'architecture polyglotte en entretien (pas juste "j'ai fait du Go sur un projet perso").

Détail dans ma réponse ci-dessous — je n'ai pas figé ce choix dans la doc, c'est encore une décision ouverte.