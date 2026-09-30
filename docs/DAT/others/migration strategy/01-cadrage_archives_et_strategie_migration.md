# Lot 2 — Archives MBChauffage et stratégie de migration

> **Document de cadrage — ** MBChauffage est une entreprise réelle, mais les formats, volumes et pratiques décrits ci-dessous ne sont pas confirmés. Les fichiers d'exemple du pack Tervo sont fictifs.
>
> **Complément à** `02-questions_reponses_DG.md` (questions d'entretien) et `03-brief_agent_migration.md` (consignes d'implémentation). Ce document explique **quoi chercher**, **à quoi s'attendre** et **comment limiter le périmètre** ; il ne répète pas le questionnaire.

## 1. Ce que le DG est susceptible d'avoir conservé

Pour une entreprise CVC active depuis plus de vingt ans, les archives peuvent être dispersées entre classeurs Excel, dossiers clients, PDF, documents papier et anciens logiciels. **Ne pas supposer que chaque document existe ou qu'il est relié aux autres.**

### 1.1 Données clients et commerciales

| Archive possible                    | Utilité métier                                            | Intérêt pour le Lot 2                                                                          |
| ----------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Fichier clients / carnet d'adresses | Retrouver les clients, téléphones, adresses et contacts   | **Prioritaire** : `Client`, puis `Site` si l'adresse du chantier est identifiable              |
| Devis                               | Proposer matériel, prestations et prix avant accord       | Conserver la référence et le PDF ; extraction détaillée différée                               |
| Factures clients                    | Justifier les prestations et retrouver un ancien chantier | Source documentaire utile, mais **pas une preuve suffisante** de la date réelle d'installation |
| Factures fournisseurs               | Retrouver les achats et références de pièces              | Hors migration métier initiale, sauf besoin confirmé                                           |
| Courriels / courriers               | Retrouver accords, demandes et échanges                   | À inventorier ; pas d'import automatique des messageries en V1                                 |

### 1.2 Archives techniques et d'entretien

| Archive possible                        | Utilité métier                                                    | Intérêt pour le Lot 2                                              |
| --------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------ |
| Fiches d'installation / mise en service | Identifier l'appareil, le site et la date réelle d'installation   | **Prioritaire** si les données sont structurées et fiables         |
| Bons / rapports d'intervention          | Conserver diagnostic, travaux réalisés, pièces et technicien      | **Prioritaire** : historique `Intervention`                        |
| Contrats d'entretien                    | Définir périodicité, prestations incluses et couverture           | Conserver les documents ; module contractuel complet hors Lot 2    |
| Attestations d'entretien                | Justifier une visite d'entretien et ses contrôles                 | Source possible de dates et d'équipements ; rattachement si fiable |
| Documents de garantie / SAV             | Retrouver les conditions de prise en charge et remplacements      | Conserver les pièces et l'historique sans inventer de couverture   |
| Photos / scans                          | Documenter une panne, une installation ou une plaque signalétique | Archivage éventuel ; reconnaissance automatique hors V1            |
| Plannings / tableaux de suivi           | Organiser rendez-vous, visites et prochaines échéances            | À examiner : ils peuvent contenir l'historique le plus exploitable |

### 1.3 Documents administratifs

Comptabilité générale, paie, RH, assurances et autres documents administratifs peuvent exister, mais **ne sont pas à importer par défaut dans Tervo**. Les inventorier seulement pour distinguer clairement ce qui relève du périmètre opérationnel.

**Question pratique à poser au DG :** « Si un client appelle pour une chaudière installée il y a dix ans, quels fichiers ouvrez-vous pour retrouver l'appareil, ses visites d'entretien et sa dernière réparation ? » Demander une démonstration sur un dossier réel, avec les informations personnelles masquées pour le jeu de développement.

## 2. À quels formats s'attendre ?

| Format probable          | Exemples                                          | Points d'attention                                                                    | Traitement initial                                          |
| ------------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `.xlsx`                  | Clients, équipements, interventions, planning     | Plusieurs onglets, titres avant les en-têtes, cellules fusionnées, colonnes renommées | **Importer en V1** à partir des modèles réellement observés |
| `.xls`                   | Anciens classeurs Excel                           | Ancien format, conventions différentes                                                | Ajouter uniquement si le DG en possède                      |
| `.csv`                   | Export d'un logiciel ou d'un tableur              | Séparateur `;` ou `,`, encodage, dates, zéros initiaux                                | **Importer en V1**                                          |
| `.pdf` avec texte        | Devis, factures, contrats, rapports, attestations | Mise en page variable ; références parfois ambiguës                                   | Conserver comme pièce documentaire ; extraction différée    |
| `.pdf` scanné            | Archives papier numérisées                        | Texte non directement exploitable                                                     | Conserver ; OCR hors V1                                     |
| `.doc` / `.docx`         | Courriers, modèles de devis ou comptes rendus     | Champs libres et modèles historiques différents                                       | Inventorier, ne pas créer de parseur générique              |
| `.jpg` / `.png`          | Photos de chantier, plaques, scans                | Noms de fichiers peu explicites, rattachement incertain                               | Conserver si utile ; pas de reconnaissance automatique      |
| Export d'ancien logiciel | CSV, Excel ou format propriétaire                 | Identifiants spécifiques, champs non documentés                                       | Examiner un export avant de prévoir un connecteur           |

### Exemples concrets à demander

- Un classeur **ancien** et un classeur **récent**, avec tous leurs onglets : vérifier si les colonnes ont changé.
- Une facture et un devis liés au **même chantier** : vérifier les références et les adresses de facturation / intervention.
- Un rapport d'entretien, son attestation et, s'il existe, le contrat associé : comprendre les liens **réels**, non supposés.
- Un dossier de dépannage **sans devis** et une visite sous contrat **sans facture individuelle**, si ces cas existent.

**Attention aux classeurs présentables :** les exemples Tervo possèdent un titre et des en-têtes stylisés. L'importeur ne doit donc pas présumer que les colonnes commencent en ligne 1 ; il doit repérer ou configurer la ligne d'en-tête par modèle de fichier.

## 3. Questions au DG : document séparé

Ne pas recopier ici le questionnaire. Utiliser **`02-questions_reponses_DG.md`** pour les questions, hypothèses, points à confirmer et implications pour l'agent. Après l'entretien, remplacer les hypothèses par les réponses constatées et associer chaque réponse à un échantillon de fichier si possible.

## 4. Comment aborder le Lot 2 sans le complexifier

### Étape 0 — Inventorier avant de coder

Créer une fiche par **famille de fichiers**, et non une fiche par document :

- Nom et provenance ; période couverte ; format et volume approximatif.
- Feuilles, colonnes, ligne d'en-tête et quelques valeurs représentatives.
- Clés possibles : référence client, adresse du site, numéro de série, référence d'intervention.
- Données manquantes, doublons et contradictions constatés.
- Priorité métier décidée avec le DG.

**Livrable :** 10 à 20 fichiers représentatifs, si disponibles, et un inventaire simple. Ne pas attendre l'intégralité des archives pour démarrer.

### Étape 1 — Importer un seul modèle Excel réel

Commencer par les données structurées qui permettent de reconstituer :

`Client → Site → Equipment → Intervention`

Respecter le DAT : un équipement historique peut ne pas avoir d'installation commerciale (`Equipment.installation_id = NULL`) ; une intervention peut concerner le site sans équipement identifié (`Intervention.equipment_id = NULL`). Ne pas créer artificiellement de `Sale`, `SaleLine` ou `Installation` pour satisfaire un import historique.

### Étape 2 — Prévisualiser et valider

Pipeline minimal :

`Lecture → Détection / mapping → Normalisation → Validation → Rapprochement → Aperçu → Validation humaine → Import → Bilan`

- Garder **les valeurs sources** et afficher les transformations proposées.
- Détecter les doublons sur plusieurs indices : nom/téléphone pour `Client`, adresse/ville au sein du client pour `Site`, numéro de série/produit au sein du site pour `Equipment`.
- Les rapprochements incertains sont soumis à validation ; ne jamais associer au hasard.
- Importer en deux passes : clients/sites/équipements, puis interventions.
- Journaliser les résultats par fichier et par ligne ; importer par transactions de lots.

### Étape 3 — Conserver les PDF sans les interpréter

Dans un premier temps, un PDF de facture, de devis ou d'attestation est **une pièce documentaire**, pas une source dont toutes les données doivent être extraites. L'associer à un client, un site, un équipement ou une intervention **uniquement si le lien est démontrable**. Sinon, le garder non classé pour examen ultérieur. Si l'archivage documentaire n'existe pas encore dans Tervo, ne pas développer un module complet uniquement pour le Lot 2.

### Étape 4 — Étendre seulement après le premier import validé

Ajouter les autres modèles Excel réellement trouvés, puis éventuellement les anciens `.xls`. Réserver l'OCR, l'extraction automatique de PDF, les connecteurs de messagerie et la gestion complète des contrats à des lots ultérieurs, **si le besoin et les volumes le justifient**.

## 5. Décisions à prendre avant de coder

| Décision              | Proposition V1                                                               | À confirmer                                                      |
| --------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Source prioritaire    | Excel/CSV ; un premier modèle réel                                           | Quels classeurs le DG utilise-t-il aujourd'hui ?                 |
| Périmètre métier      | Clients, sites, équipements, interventions                                   | Quels champs sont indispensables dès le lancement ?              |
| En-têtes Excel        | Ligne détectée ou configurée par modèle                                      | Où commencent les données dans chaque classeur ?                 |
| Correspondances       | Mapping explicite des colonnes par format                                    | Combien de formats distincts existent ?                          |
| Données manquantes    | `NULL` et anomalie documentée ; jamais de valeur inventée                    | Quels champs sont réellement fiables ?                           |
| Doublons              | Automatique si forte confiance ; sinon validation humaine                    | Qui arbitre les cas ambigus ?                                    |
| Historique commercial | Liens facultatifs ; pas de ventes fictives                                   | Existe-t-il des références communes fiables ?                    |
| PDF et photos         | Préservation et rattachement facultatif                                      | Quel volume et quels documents sont utiles au quotidien ?        |
| Réimport              | SHA-256 pour le fichier identique **et** rapprochement métier entre fichiers | Les fichiers sont-ils modifiés et réexportés fréquemment ?       |
| Traçabilité           | `ImportBatch`, `ImportRecord`, `ImportError` selon le DAT                    | Quelles informations doivent figurer dans le bilan ?             |
| Confidentialité       | Copies anonymisées pour les tests, accès métier pour les originaux           | Qui est autorisé à voir les documents financiers et techniques ? |

### Critère de réussite du premier incrément

Sur **un vrai classeur représentatif**, l'agent doit pouvoir :

1. Afficher les feuilles et les colonnes reconnues, puis prévisualiser les données normalisées.
2. Signaler doublons, erreurs et champs manquants sans inventer de relations.
3. Après validation, importer les clients, sites, équipements et interventions exploitables.
4. Produire un bilan compréhensible et permettre de retracer chaque ligne vers sa source.
5. Réexécuter le même import sans créer de doublons.

**Hors objectif initial :** reconstruire vingt ans de comptabilité, reconnaître automatiquement tous les PDF, ou concevoir un importeur universel avant d'avoir vu les fichiers du DG.
