# Tervo — Lot 2 : jeu de données de migration fictif

**Tous les noms, adresses, sociétés, marques, références, montants et documents de ce dossier sont fictifs.** Les fichiers PDF ne sont ni des factures ni des attestations réglementaires utilisables. Les coordonnées ne sont pas opérationnelles.

## Contenu

- `resources/excel/01_clients_sites_equipements.xlsx` : clients, sites, équipements ; doublon C001/C005 et données manquantes.
- `resources/excel/02_interventions_2018_2025.xlsx` : interventions historiques, dont une ligne volontairement invalide.
- `resources/excel/03_export_ancien_format.xlsx` : ancien schéma de colonnes et dates hétérogènes.
- `resources/csv/04_export_clients_latin1.csv` : export point-virgule, encodage ISO-8859-1.
- `resources/pdf/factures/` : facture d'installation, facture de réparation et facture de forfait annuel.
- `resources/pdf/devis/` : devis de réparation consécutif au diagnostic.
- `resources/pdf/rapports/` : diagnostic, réparation, diagnostic sans équipement identifié.
- `resources/pdf/attestations/` : exemple pédagogique simplifié, non réglementaire.
- `resources/pdf/contrats/` : exemple non contractuel de forfait annuel.
- `anomalies_attendues.json` : cas à vérifier.
- `01-cadrage_archives_et_strategie_migration` : overview de la strategy.
- `02-questions_reponses_DG.md` : questionnaire complet, hypothèses métier et implications techniques.
- `03-brief_agent_migration.md` : périmètre et critères d’acceptation de l’import V1.

## Parcours métier cohérent

1. Jean Dupont : chaudière installée en 2018 (`E001`, `INT-2018-014`, `FAC-2018-042`).
2. Contrat d'entretien 2024 (`CTR-2024-001`) et facture annuelle (`FAC-2024-078`).
3. Visite annuelle 2024 et attestation (`INT-2024-081`, `ATT-2024-081`).
4. Panne diagnostiquée le 03/02/2025 (`INT-2025-016`, `RAP-2025-016`).
5. Devis accepté (`DEV-2025-003`), puis réparation le 10/02/2025 (`INT-2025-017`, `RAP-2025-017`, `FAC-2025-011`).
6. SCI Bellevue : intervention de diagnostic sans équipement identifié ni facture (`INT-2023-010`).

## Consignes pour l'agent

- **Priorité :** import structuré Excel/CSV vers Client → Site → Equipment → Intervention.
- Lire les colonnes sans supposer un format unique ; prévisualiser et signaler les anomalies avant validation.
- Conserver la provenance fichier/feuille/ligne et ne pas créer automatiquement les doublons.
- `Equipment.installation_id` et `Intervention.equipment_id` peuvent être nuls pour l'historique.
- Conserver les PDF comme exemples de documents annexes ; leur OCR/extraction automatique n'est **pas** un prérequis Lot 2.
- Ne pas déduire une date réelle d'installation de la seule date de facture.
- Le fichier identique ne doit pas être importé deux fois ; le rapprochement métier doit aussi couvrir les doublons inter-fichiers.
- Vérifier `specifications/anomalies_attendues.json` dans les tests d'import.

## Important

Ce jeu est volontairement petit et pédagogique. Il ne représente ni la structure ni les données réelles de MBChauffage. Valider les hypothèses sur des copies anonymisées des fichiers du DG avant de figer les mappings.
