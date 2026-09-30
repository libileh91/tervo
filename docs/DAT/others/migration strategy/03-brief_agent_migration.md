# Lot 2 — Brief d'implémentation pour l'agent

## Statut et objectif

Ce brief s'appuie sur des **hypothèses métier non validées**. Le jeu de fichiers joint est **entièrement fictif**. Adapter le code aux vrais échantillons MBChauffage avant de figer les mappings.

**Objectif V1 :** importer des données structurées Excel/CSV vers `Client → Site → Equipment → Intervention`, sans perdre la provenance ni créer de liens métier incertains.

## Périmètre initial

1. Dépôt manuel de fichiers `.xlsx` et `.csv` ; ajouter `.xls` seulement si présent dans les archives réelles.
2. Détection des feuilles, en-têtes, séparateurs, encodages et formats de dates courants.
3. Mapping des colonnes par modèle de fichier observé ; aperçu avant import.
4. Normalisation des noms, téléphones, adresses et dates, sans écraser la valeur d'origine.
5. Détection de doublons clients, sites et équipements ; confirmation humaine des cas ambigus.
6. Import en deux passes : d'abord Client/Site/Equipment, puis Intervention.
7. Journal par fichier et par ligne : résultat, cible créée/associée, erreur et décision humaine.
8. Réimport contrôlé : empreinte SHA-256 pour le fichier identique **et** rapprochement métier inter-fichiers.
9. Transactions par lots et bilan final (créés, rapprochés, ignorés, erreurs).

## Contraintes métier à préserver

- `Equipment.installation_id` peut être `NULL` pour les équipements historiques.
- `Intervention.equipment_id` peut être `NULL` pour un diagnostic au niveau du site.
- Un rapport d'intervention ne nécessite ni devis ni facture.
- Une facture ne prouve pas à elle seule la date réelle d'installation.
- Une attestation n'implique pas automatiquement l'existence d'un contrat.
- Ne jamais déduire un numéro de série, un équipement ou un remplacement à partir d'un texte ambigu.
- Conserver les anciens équipements et leur historique ; ne pas les remplacer par écrasement.

## Documents annexes

Les PDF du dossier `pdf/` illustrent devis, factures, rapports, contrat et attestation. Pour V1, les conserver comme exemples de pièces jointes ; **OCR, extraction automatique et gestion contractuelle avancée sont hors périmètre**. Si l'archivage documentaire n'est pas encore disponible dans le code, ne pas le construire uniquement pour cette migration.

## Ordre de travail

1. Inventorier les vrais fichiers du DG (format, période, feuilles, colonnes, volume, anomalies).
2. Écrire un mapping pour **un seul format Excel réel**.
3. Tester lecture, prévisualisation et normalisation sans écrire en base.
4. Ajouter rapprochement et validation des ambiguïtés.
5. Implémenter l'import transactionnel et la traçabilité.
6. Tester réimport identique, doublons inter-fichiers et reprise après erreur.
7. Ajouter les autres formats réellement observés.

## Critères d'acceptation

- Un fichier source n'est jamais modifié.
- Chaque enregistrement importé est traçable jusqu'au fichier, à la feuille et à la ligne.
- Les champs absents restent absents ; les cas ambigus sont signalés.
- Un même fichier déjà importé avec succès n'engendre pas de doublons.
- Deux fichiers différents contenant le même client ne créent pas automatiquement deux clients.
- Une intervention sans équipement identifié reste importable si le site est connu.
- Un rapport d'import lisible récapitule succès, rapprochements et anomalies.

## Fichiers de référence

- `01_questions_reponses_DG.md` : questionnaire et hypothèses à valider.
- `anomalies_attendues.json` : cas de test du jeu fictif.
- `../excel/` et `../csv/` : données structurées de test.
- `../pdf/` : documents métier annexes fictifs.
