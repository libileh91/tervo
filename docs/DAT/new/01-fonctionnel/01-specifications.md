# Tervo — Spécifications fonctionnelles

> Ce document décrit **ce que Tervo doit permettre de faire**.
> Les choix d'implémentation sont documentés dans `02-techniques/`.

## 1. Vision

Tervo est une application de gestion des activités CVC centrée sur le cycle de vie des équipements et des interventions terrain.

Le produit doit permettre de relier une activité terrain à son contexte métier :

```text
Client
  │
  └── Site
       │
       └── Équipement
            │
            └── Intervention
                 ├── Checklist
                 ├── Photos
                 ├── Matériel
                 ├── Rapport
                 └── Avis
```

## 2. Utilisateurs

### Technicien

Le technicien doit pouvoir :

* consulter ses interventions ;
* accéder aux informations du client, du site et de l'équipement ;
* réaliser une checklist ;
* ajouter des photos ;
* déclarer le matériel utilisé ;
* renseigner ses observations ;
* qualifier le résultat ;
* clôturer l'intervention ;
* produire ou transmettre le rapport.

### Responsable / gérant

Le responsable doit pouvoir :

* gérer clients, sites et équipements ;
* planifier et suivre les interventions ;
* consulter l'historique d'un équipement ;
* suivre les résultats des interventions ;
* consulter les rapports ;
* suivre l'activité commerciale et le showroom.

### Vendeur / showroom

Le vendeur doit pouvoir :

* consulter le catalogue ;
* enregistrer les produits présentés ;
* créer et suivre une visite showroom ;
* qualifier le suivi commercial ;
* relier le suivi à une vente lorsqu'elle aboutit.

### Administrateur

L'administrateur doit pouvoir :

* gérer les utilisateurs et paramètres ;
* contrôler les données importées ;
* résoudre les anomalies de migration ;
* accéder aux fonctions d'administration.

## 3. Client et site

Un **client** représente la personne ou l'organisation avec laquelle l'entreprise travaille.

Un client peut avoir plusieurs **sites**.

Un **site** représente un lieu physique sur lequel une activité peut avoir lieu. Il possède ses propres informations d'adresse et peut contenir plusieurs équipements.

Exemple :

```text
Client : Société Dupont
├── Site : Agence Massy
│    ├── PAC air/eau
│    └── Climatisation bureaux
└── Site : Agence Palaiseau
     └── Chaudière gaz
```

## 4. Produit catalogue et équipement

Ces deux notions doivent rester distinctes.

### Produit catalogue

Le produit catalogue représente une référence commerciale :

* marque ;
* modèle ;
* référence ;
* catégorie ;
* caractéristiques ;
* informations commerciales.

Il peut être vendu ou présenté dans le showroom.

### Équipement installé

L'équipement représente une **instance physique réelle** installée chez un client.

Il peut notamment conserver :

* le produit d'origine ;
* le site ;
* le numéro de série ;
* la date d'installation ;
* la date de mise en service ;
* les informations de garantie ;
* son état dans son cycle de vie.

Plusieurs équipements peuvent provenir du même produit catalogue.

```text
Produit catalogue
      │
      ├── vendu / installé ──► Équipement A
      ├── vendu / installé ──► Équipement B
      └── vendu / installé ──► Équipement C
```

## 5. Interventions

Une intervention représente une opération réalisée ou planifiée par l'entreprise.

Les types principaux sont :

* installation ;
* mise en service ;
* maintenance préventive ;
* maintenance corrective ;
* dépannage ;
* diagnostic ;
* SAV ;
* autre.

Une intervention est idéalement rattachée à un équipement. Un diagnostic peut exceptionnellement être créé au niveau du site lorsqu'aucun équipement précis n'est encore identifié.

### Statut

Le statut décrit l'avancement de l'intervention :

* planifiée ;
* en cours ;
* terminée ;
* annulée.

### Résultat

Le résultat décrit ce qui s'est passé :

* résolu ;
* partiellement résolu ;
* non résolu ;
* pièce nécessaire ;
* devis nécessaire ;
* à replanifier.

Le statut et le résultat sont deux informations différentes et ne doivent pas être fusionnés.

## 6. Checklist

Chaque type d'intervention peut disposer d'un modèle de checklist.

Lors de la création d'une intervention, le modèle applicable est utilisé pour produire la checklist de cette intervention.

La checklist utilisée par une intervention devient une donnée historique.

Une modification ultérieure du modèle ne doit pas modifier les réponses déjà enregistrées sur les interventions passées.

## 7. Photos et matériel

Les photos servent notamment à documenter :

* l'état avant intervention ;
* l'état après intervention ;
* l'équipement ;
* une anomalie ;
* une pièce ou un composant ;
* une intervention particulière.

Le matériel utilisé doit au minimum permettre d'enregistrer une désignation et une quantité.

Une liaison avec le catalogue pourra être ajoutée ultérieurement sans imposer cette dépendance au cœur de la V1.

## 8. Rapport

Un rapport rassemble les informations utiles à la restitution de l'intervention :

* client ;
* site ;
* équipement ;
* technicien(s) ;
* dates ;
* type d'intervention ;
* résultat ;
* checklist ;
* photos ;
* matériel ;
* observations.

Un rapport transmis au client doit rester cohérent avec l'état de l'intervention au moment de sa génération.

Une modification ultérieure de l'intervention ne doit pas réécrire silencieusement un document déjà transmis.

## 9. Avis client

Une intervention peut produire zéro ou un avis client.

L'avis est rattaché à l'intervention concernée afin de conserver le contexte de l'expérience client.

## 10. Showroom et suivi commercial

Le catalogue représente les produits disponibles comme références commerciales.

Le showroom représente les produits effectivement présentés aux visiteurs.

Une visite showroom doit permettre de conserver :

* le visiteur ou client ;
* la date ;
* les produits présentés ;
* le collaborateur en charge ;
* l'état du suivi commercial.

Le suivi doit pouvoir évoluer vers une demande de devis, une vente puis une installation.

La vente et l'installation restent deux événements distincts.

## 11. Garantie et SAV

La garantie concerne l'équipement physique installé, et non uniquement la référence catalogue.

Une demande SAV doit pouvoir être rattachée à l'équipement concerné et à l'intervention qui la traite.

Le fait qu'un équipement soit sous garantie et le fait qu'une intervention soit effectivement traitée au titre de la garantie sont deux informations distinctes.

## 12. Remplacement d'un équipement

Lorsqu'un équipement est remplacé, son historique ne doit pas disparaître.

Le nouvel équipement possède sa propre identité et son propre historique.

L'ancien équipement est conservé comme élément historique du site.

```text
Équipement A
   │
   └── historique interventions
          │
          ▼
       remplacé
          │
          ▼
Équipement B
   │
   └── nouvel historique
```

## 13. Migration des données historiques

Les données importées doivent conserver autant que possible leur provenance.

Lorsqu'une donnée historique est ambiguë, Tervo ne doit pas inventer une information.

Une anomalie peut être :

1. rattachée à une entité existante ;
2. utilisée pour créer une nouvelle entité ;
3. corrigée ;
4. ignorée avec justification.

Les décisions de rapprochement doivent rester traçables.

## 14. Hors cœur fonctionnel

Ne sont pas prioritaires dans le cœur V1 :

* gestion complète du stock ;
* gestion avancée des fournisseurs ;
* processus d'achat complet ;
* contrats de maintenance complexes ;
* reporting et KPI avancés.

Ces fonctions pourront s'appuyer sur le modèle métier stabilisé sans le dicter.

## 15. Critères fonctionnels de référence

Le modèle fonctionnel est considéré comme cohérent lorsque Tervo permet de :

* retrouver un client et ses sites ;
* retrouver les équipements présents sur un site ;
* consulter l'historique d'un équipement ;
* planifier une intervention ;
* réaliser une intervention sur le terrain ;
* documenter cette intervention ;
* qualifier son résultat ;
* produire un rapport ;
* recueillir un avis ;
* relier catalogue, vente, installation et équipement ;
* conserver l'historique lors d'un remplacement ;
* importer des données historiques sans perdre les cas ambigus.
