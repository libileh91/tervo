# Lot 2 — Questions / réponses pour l'entretien avec le DG

> **Statut : hypothèses métier, NON confirmées par MBChauffage.** Ne pas présenter ces réponses comme des faits. Pendant l'entretien, remplacer chaque hypothèse par la réponse réelle et demander un fichier représentatif. Les consignes « Agent » sont des pistes d'implémentation conditionnelles.

## A. Inventaire des archives

### A1. Où sont stockés les fichiers ?

- **Hypothèse :** PC du DG, dossiers partagés, anciens disques, messagerie et/ou ancien logiciel.
- **À confirmer :** emplacements, accès, existence de sauvegardes.
- **Agent :** commencer par un dépôt manuel de copies de fichiers ; ne pas intégrer tous les systèmes externes.

### A2. Depuis quelle année et pour quel volume ?

- **Hypothèse :** jusqu'à 20 ans d'archives, avec une qualité variable selon les périodes.
- **À confirmer :** années couvertes, nombre approximatif de fichiers, taille totale.
- **Agent :** accepter les dates anciennes, les champs absents et le traitement par lots.

### A3. Un seul Excel ou plusieurs classeurs ?

- **Hypothèse :** plusieurs fichiers par activité ou par année.
- **À confirmer :** demander un ancien et un récent, avec tous leurs onglets.
- **Agent :** détecter les feuilles et permettre un mapping par format source.

### A4. Qui crée et met à jour les documents ?

- **Hypothèse :** DG, secrétariat, comptable et techniciens selon le document.
- **À confirmer :** responsable de chaque fichier et fréquence de mise à jour.
- **Agent :** conserver provenance, nom du fichier, feuille et numéro de ligne.

## B. Recherche au quotidien

### B1. Comment retrouvez-vous un ancien client ?

- **Hypothèse :** nom, téléphone, adresse ou ancienne facture.
- **Agent :** normaliser ces champs ; proposer des correspondances sans fusion irréversible.

### B2. Comment retrouvez-vous une facture ou une intervention ?

- **Hypothèse :** dossiers clients, années, références de documents.
- **Agent :** garder les références d'origine et rattacher les documents seulement si le lien est fiable.

### B3. Quelles recherches prennent le plus de temps ?

- **Hypothèse :** retrouver l'équipement installé, les visites précédentes et les pièces changées.
- **Agent :** privilégier l'historique Client → Site → Equipment → Intervention.

### B4. Quelles informations doivent être disponibles dès le lancement ?

- **Hypothèse :** coordonnées, adresse du chantier, équipement, dernière intervention, documents utiles.
- **À confirmer :** demander au DG de classer ses trois besoins prioritaires.
- **Agent :** importer d'abord les données opérationnelles indispensables.

## C. Qualité et organisation

### C1. Un client peut-il apparaître sous plusieurs noms ?

- **Hypothèse :** oui (abréviations, fautes, société, changements de coordonnées).
- **Agent :** détection de doublons ; validation humaine des cas ambigus.

### C2. Les modèles de fichiers ont-ils changé ?

- **Hypothèse :** oui, selon l'année et les logiciels utilisés.
- **Agent :** plusieurs mappings configurables ; ne pas coder un schéma Excel unique.

### C3. Les références clients et factures sont-elles uniques ?

- **Hypothèse :** factures généralement numérotées ; anciens identifiants clients parfois absents.
- **Agent :** IDs internes propres à Tervo ; références source conservées séparément.

### C4. Adresse de facturation et adresse du chantier identiques ?

- **Hypothèse :** pas toujours (bailleurs, syndics, entreprises multisites).
- **Agent :** distinguer Client et Site ; ne pas fusionner leurs adresses.

## D. Équipements et interventions

### D1. Marques, modèles et numéros de série conservés ?

- **Hypothèse :** partiellement, dans les factures, fiches ou attestations.
- **Agent :** accepter des équipements historiques sans numéro de série ou produit identifié.

### D2. Comment retrouver un équipement remplacé ?

- **Hypothèse :** factures, rapports SAV, notes ou historique du client.
- **Agent :** préserver l'ancien équipement et ses interventions ; ne créer le lien de remplacement que s'il est documenté.

### D3. Rapports d'intervention liés aux devis et factures ?

- **Hypothèse :** parfois classés ensemble, parfois séparément ; certaines visites n'ont ni devis ni facture spécifique.
- **Agent :** le rapport appartient à l'intervention ; les liens commerciaux restent facultatifs.

### D4. Contrats et attestations historiques ?

- **Hypothèse :** contrats annuels, attestations PDF ou scans, parfois archives papier.
- **Agent :** conserver les documents et les dates certaines ; pas de module contractuel complet dans le premier import.

## E. Volumes et priorités

### E1. Combien de clients, équipements, interventions et documents ?

- **Réponse :** inconnu avant inventaire ; ne pas inventer de volume.
- **Agent :** mesurer un échantillon, tester la mémoire et importer par lots.

### E2. Quelles années importer en premier ?

- **Hypothèse :** clients actifs et équipements encore entretenus, puis historique ancien.
- **À confirmer :** demander la période prioritaire au DG.
- **Agent :** import progressif et répétable, sans limite arbitraire d'ancienneté.

### E3. Tous les documents ou seulement les données essentielles ?

- **Hypothèse :** données opérationnelles d'abord ; archivage PDF selon l'utilité.
- **Agent :** séparer import structuré et stockage des documents annexes.

### E4. Que faire des archives inutilisées ou en double ?

- **Hypothèse :** certains dossiers sont redondants ou obsolètes.
- **Agent :** signaler les doublons ; aucune suppression automatique des originaux.

## F. Validation et confidentialité

### F1. Qui valide les doublons et les anomalies ?

- **Hypothèse :** DG ou personne maîtrisant l'historique clients.
- **Agent :** file de validation manuelle et décisions traçables.

### F2. Peut-on obtenir des fichiers d'exemple ?

- **À demander :** classeurs de plusieurs périodes, dossier client complet, PDF variés ; copies anonymisées si possible.
- **Agent :** définir les mappings à partir des vrais fichiers, pas seulement des exemples fictifs.

### F3. Qui doit voir quels documents ?

- **Hypothèse :** direction et administratif pour les finances ; techniciens pour l'historique technique.
- **Agent :** respecter les rôles et permissions de Tervo ; ne pas exposer tous les PDF par défaut.

### F4. Quelles règles de conservation ?

- **Réponse :** à vérifier par type de document et selon les obligations applicables.
- **Agent :** aucune politique de destruction automatique sans validation juridique et métier.

## G. Entretien et contrats

### G1. Contrats annuels ou entretiens ponctuels ?

- **Hypothèse :** les deux peuvent coexister.
- **Agent :** ne pas exiger de contrat pour importer une intervention.

### G2. Comment rappeler les clients ?

- **Hypothèse :** Excel, agenda, logiciel ou rappels manuels.
- **Agent :** importer la dernière date d'entretien et la prochaine échéance seulement si elles sont explicites.

### G3. Comment les techniciens rédigent-ils leurs rapports ?

- **Hypothèse :** papier, PDF, formulaire ou logiciel selon l'époque.
- **Agent :** accepter les documents hétérogènes ; pas d'OCR obligatoire en V1.

### G4. Où sont conservées les attestations ?

- **Hypothèse :** dossiers clients et/ou classement annuel.
- **Agent :** rattacher à l'intervention et à l'équipement lorsque le lien est certain.

### G5. Comment vérifier si un dépannage est couvert par le contrat ?

- **Hypothèse :** consultation des conditions contractuelles et de l'équipement concerné.
- **Agent :** archiver les contrats ; différer le moteur automatique de couverture.

## H. Documents à demander en fin d'entretien

- 1 classeur Excel récent et 1 ancien, avec plusieurs onglets si possible.
- 1 export clients et 1 historique d'interventions.
- 1 dossier client représentatif : devis, facture, rapport, attestation, contrat si disponibles.
- 1 exemple de document difficile à retrouver aujourd'hui.
- Une estimation du nombre de fichiers et du volume total.

**Question de démonstration :** « Un client appelle pour une panne sur un appareil installé il y a dix ans : montrez-moi comment vous retrouvez son équipement, ses dernières visites et sa facture d'origine. »