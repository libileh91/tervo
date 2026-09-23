# Tervo — Workflows métier

> Référence des principaux parcours métier de Tervo.
>
> Ce document décrit **ce qui se passe dans le métier**, indépendamment de l’implémentation technique.

---

## 1. Principes généraux

Les workflows Tervo suivent une logique simple :

```text
CLIENT
  │
  └── SITE
       │
       └── ÉQUIPEMENT
             │
             └── INTERVENTION
                   ├── Checklist
                   ├── Photos
                   ├── Matériel
                   ├── Rapport
                   └── Avis
```

Le cycle commercial et le cycle technique sont liés mais ne doivent pas être confondus :

```text
Produit catalogue
      │
      ▼
Vente
      │
      ▼
Installation
      │
      ▼
Équipement installé
      │
      ├── Maintenance
      ├── Dépannage
      └── SAV
             │
             ▼
        Intervention
```

Principes :

* une vente n'est pas une installation ;
* une installation crée ou met en service un équipement physique ;
* une intervention décrit une action réellement effectuée ;
* l'historique d'un équipement doit rester consultable après son remplacement ;
* les documents produits à partir d'une intervention doivent conserver une trace de l'état constaté.

---

# 2. Workflow — Création d'un client et de son site

## 2.1 Création du client

Un utilisateur crée un client :

* particulier ;
* entreprise ;
* autre organisation.

Informations minimales :

* nom / raison sociale ;
* coordonnées ;
* informations de contact.

Un client peut posséder plusieurs sites.

```text
Client
 ├── Site A
 ├── Site B
 └── Site C
```

## 2.2 Création du site

Un site représente un lieu physique sur lequel Tervo doit pouvoir intervenir.

Exemples :

* domicile d'un particulier ;
* agence d'une entreprise ;
* magasin ;
* atelier ;
* immeuble ;
* local professionnel.

Le site possède sa propre adresse et ses informations pratiques.

Un site appartient à un seul client.

```text
Client
   │
   ├── Site Massy
   │      ├── PAC
   │      └── VMC
   │
   └── Site Paris
          └── Climatisation
```

---

# 3. Workflow — Vente → Installation → Équipement

## 3.1 Vente d'un produit

Un produit du catalogue peut être vendu à un client.

Exemple :

```text
Produit catalogue
PAC Air/Eau 8 kW
        │
        ▼
Vente
Client : Dupont
Site : Massy
```

La vente représente l'événement commercial.

Elle ne signifie pas encore que l'équipement est installé.

## 3.2 Planification de l'installation

Une installation peut être planifiée ultérieurement.

Exemple :

```text
Vente
  │
  └── Installation prévue le 15/10
```

La date de vente et la date d'installation peuvent donc être différentes.

## 3.3 Installation

Lors de l'installation, les informations techniques réelles sont enregistrées :

* équipement installé ;
* référence produit ;
* numéro de série ;
* site ;
* date d'installation ;
* date de mise en service si applicable ;
* informations de garantie ;
* observations.

L'équipement devient alors une **instance physique identifiable**.

```text
Produit catalogue
      │
      ▼
Vente
      │
      ▼
Installation
      │
      ▼
Équipement physique
      │
      ├── N° série
      ├── Site
      ├── Date installation
      └── Garantie
```

## 3.4 Quantité vendue > 1 et statut de l'installation

Une ligne de vente avec `quantity = N` donne lieu à `N` installations,
chacune produisant un équipement physique distinct :

```text
Sale
  │
  ▼
SaleLine (quantity = N)
  │
  ▼
N Installation
  │
  ▼
Installation COMPLETED
  │
  ▼
Equipment créé/rattaché pour chaque unité
```

Statut d'une installation :

```text
SCHEDULED
    ↓ start
IN_PROGRESS
    ↓ complete
COMPLETED

SCHEDULED ──► CANCELLED   (sortie alternative autorisée)
```

---

# 4. Workflow — Création d'une intervention

Une intervention est créée lorsqu'une action technique doit être réalisée.

## 4.1 Origines possibles

Une intervention peut être déclenchée par :

* une installation ;
* une mise en service ;
* une maintenance préventive ;
* une panne ;
* un dépannage ;
* un diagnostic ;
* une demande SAV ;
* une autre opération technique.

## 4.2 Rattachement

Lorsque l'équipement est connu :

```text
Client
  └── Site
       └── Équipement
             └── Intervention
```

Lorsque l'équipement n'est pas encore identifié, notamment lors d'un diagnostic initial :

```text
Client
  └── Site
       └── Intervention
```

L'équipement peut ensuite être identifié et rattaché à l'intervention.

## 4.3 Planification

Une intervention planifiée contient notamment :

* type d'intervention ;
* client ;
* site ;
* équipement si connu ;
* date/heure prévue ;
* technicien(s) ;
* description de la demande.

Statut initial :

```text
PLANIFIÉE
```

---

# 5. Workflow — Réalisation d'une intervention

Le technicien démarre l'intervention.

```text
PLANIFIÉE
    │
    ▼
EN COURS
```

Pendant l'intervention, il peut :

* consulter les informations du site ;
* consulter l'historique de l'équipement ;
* exécuter une checklist ;
* ajouter des observations ;
* prendre des photos ;
* enregistrer le matériel utilisé ;
* identifier une anomalie ;
* renseigner les mesures nécessaires ;
* ajouter plusieurs techniciens si nécessaire.

---

# 6. Workflow — Checklist

Une checklist dépend du type d'intervention.

Exemple :

```text
Maintenance préventive PAC
├── Vérifier pression
├── Vérifier température départ
├── Vérifier température retour
├── Contrôler connexions
├── Contrôler état général
└── Nettoyer les filtres
```

Le modèle de checklist peut évoluer.

Lorsqu'une intervention démarre, la checklist applicable est enregistrée avec l'intervention.

```text
Modèle checklist
       │
       ▼
Checklist de l'intervention
```

Une modification ultérieure du modèle ne doit pas modifier les anciennes interventions.

---

# 7. Workflow — Photos

Les photos sont prises pendant l'intervention et rattachées à celle-ci.

Exemples :

* avant intervention ;
* après intervention ;
* équipement ;
* anomalie ;
* pièce remplacée ;
* autre.

```text
Intervention
 ├── Photo équipement
 ├── Photo anomalie
 ├── Photo avant
 └── Photo après
```

Les photos servent notamment à documenter le constat technique et le travail réalisé.

---

# 8. Workflow — Matériel utilisé

Le technicien peut enregistrer le matériel utilisé pendant l'intervention.

En V1, le niveau de détail peut rester simple :

```text
Matériel
├── Désignation
└── Quantité
```

Exemple :

```text
Intervention #1042

Matériel utilisé :
- Filtre 20x25 : 1
- Collier de serrage : 2
- Câble 3G1.5 : 5 m
```

Le rattachement direct à un produit du catalogue pourra être ajouté ultérieurement.

---

# 9. Workflow — Fin d'intervention

Lorsque le travail est terminé :

```text
EN COURS
   │
   ▼
TERMINÉE
```

La fin d'intervention doit permettre de renseigner un **résultat métier** distinct du statut.

Exemples :

```text
RÉSOLU
PARTIELLEMENT RÉSOLU
NON RÉSOLU
PIÈCE NÉCESSAIRE
DEVIS NÉCESSAIRE
NOUVELLE INTERVENTION NÉCESSAIRE
```

Exemple :

```text
Statut : TERMINÉE
Résultat : PIÈCE NÉCESSAIRE
```

Cela signifie que le rendez-vous est terminé, mais que le problème n'est pas encore définitivement résolu.

---

# 10. Workflow — Rapport d'intervention

À partir des informations saisies pendant l'intervention, Tervo peut produire un rapport.

Le rapport reprend notamment :

* client ;
* site ;
* équipement ;
* technicien(s) ;
* type d'intervention ;
* date ;
* résultat ;
* checklist ;
* observations ;
* photos ;
* matériel utilisé.

```text
Intervention
     │
     ├── Checklist
     ├── Photos
     ├── Matériel
     └── Observations
             │
             ▼
       Rapport d'intervention
```

Une fois transmis au client, le rapport doit conserver une représentation cohérente de l'intervention au moment de son émission.

Une modification ultérieure des données métier ne doit pas silencieusement réécrire un document déjà transmis.

---

# 11. Workflow — Avis client

Après une intervention, un client peut laisser un avis.

Une intervention peut avoir :

```text
0 ou 1 avis
```

Exemple :

```text
Intervention #1042
        │
        └── Avis
             ├── Note
             └── Commentaire
```

Un avis n'est pas obligatoire.

---

# 12. Workflow — Dépannage

Un client signale une panne.

```text
Demande client
      │
      ▼
Intervention de dépannage
      │
      ▼
Diagnostic
      │
      ├── Réparation immédiate
      │
      ├── Pièce nécessaire
      │
      ├── Devis nécessaire
      │
      └── Nouvelle intervention
```

### Cas 1 — Résolution immédiate

```text
Dépannage
   │
   ▼
Réparation
   │
   ▼
Résultat : RÉSOLU
   │
   ▼
Rapport
```

### Cas 2 — Pièce nécessaire

```text
Dépannage
   │
   ▼
Diagnostic
   │
   ▼
Pièce nécessaire
   │
   ▼
Résultat : PIÈCE NÉCESSAIRE
```

Une nouvelle intervention pourra ensuite être planifiée.

### Cas 3 — Devis nécessaire

```text
Dépannage
   │
   ▼
Diagnostic
   │
   ▼
Travaux supplémentaires
   │
   ▼
Devis nécessaire
```

L'intervention reste terminée en tant que rendez-vous, mais le problème métier peut nécessiter une suite commerciale ou technique.

---

# 13. Workflow — Maintenance préventive

Une maintenance préventive est réalisée sur un équipement existant.

```text
Équipement
    │
    ▼
Maintenance préventive
    │
    ├── Checklist
    ├── Mesures
    ├── Photos
    ├── Matériel
    └── Observations
          │
          ▼
       Résultat
```

L'historique de maintenance doit rester consultable depuis l'équipement.

Exemple :

```text
PAC #PAC-2026-001

Historique
├── 12/03/2025 — Maintenance
├── 18/09/2025 — Maintenance
├── 04/02/2026 — Dépannage
└── 15/09/2026 — Maintenance
```

---

# 14. Workflow — Garantie et SAV

La garantie est associée à l'équipement physique.

```text
Équipement
   │
   └── Garantie
```

Une demande SAV peut donner lieu à une intervention.

```text
Demande SAV
    │
    ▼
Intervention SAV
    │
    ├── Diagnostic
    ├── Réparation
    ├── Pièce
    └── Rapport
```

Le fait qu'un équipement soit sous garantie ne doit pas automatiquement signifier qu'une intervention est traitée sous garantie.

L'intervention doit pouvoir préciser explicitement si elle est traitée dans le cadre de la garantie.

---

# 15. Workflow — Remplacement d'un équipement

Lorsqu'un équipement est remplacé, l'ancien équipement ne doit pas être supprimé.

```text
Ancien équipement
      │
      ▼
REMPLACÉ
      │
      │ historique conservé
      ▼
Nouvel équipement
      │
      ▼
EN SERVICE
```

Exemple :

```text
Site Dupont — Massy

PAC #001
├── Installée : 2022
├── Maintenance : 2023
├── Dépannage : 2024
└── Remplacée : 2026

PAC #002
├── Installée : 2026
└── En service
```

L'historique de PAC #001 reste accessible.

L'ancien équipement pointe vers le nouvel équipement via `replaced_by_id`
(`ancien.replaced_by_id = nouveau.id`).

---

# 16. Workflow — Showroom

Le showroom constitue un parcours commercial distinct du parcours technique.

Une visite peut concerner plusieurs produits.

```text
Visite showroom
├── Client / prospect
├── Date
├── Commercial
├── Produits présentés
└── Suite commerciale
```

La suite donnée doit représenter l'état du suivi.

Exemples :

```text
À RELANCER
EN RÉFLEXION
DEVIS DEMANDÉ
DEVIS ENVOYÉ
VENDU
PERDU
SANS SUITE
```

Le produit présenté dans le showroom ne doit pas être considéré comme vendu ou installé.

---

# 17. Workflow — Showroom → Vente → Installation

Lorsqu'un prospect poursuit son projet :

```text
Visite showroom
      │
      ▼
Suivi commercial
      │
      ▼
Devis
      │
      ▼
Vente
      │
      ▼
Installation
      │
      ▼
Équipement
```

Chaque étape représente un événement différent.

Une vente peut être réalisée sans que l'installation ait lieu immédiatement.

---

# 18. Workflow — Migration de données historiques

Lorsqu'une donnée historique ne permet pas de déterminer avec certitude son rattachement, Tervo ne doit pas inventer l'information.

Exemple :

```text
Ancienne intervention
"Entretien PAC client Dupont"
```

Si plusieurs équipements correspondent au client :

```text
PAC #001 ?
PAC #002 ?
PAC #003 ?
```

L'information doit être traitée comme ambiguë.

Options :

```text
1. Rattacher à un équipement existant
2. Créer un nouvel équipement
3. Corriger les données
4. Ne pas rattacher
5. Ignorer avec justification
```

La décision de migration doit être traçable lorsque cela est nécessaire.

---

# 19. Workflow global

Le fonctionnement général de Tervo peut être résumé ainsi :

```text
                         ┌─────────────────┐
                         │ Produit catalogue│
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │      Vente      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Installation  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    Équipement   │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
               Maintenance    Dépannage       SAV
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  Intervention   │
                         └────────┬────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
            Checklist          Photos          Matériel
                │                 │                 │
                └─────────────────┼─────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     Rapport     │
                         └────────┬────────┘
                                  │
                                  ▼
                              Avis client
```

---

# 20. Règles métier structurantes

Les règles suivantes constituent les invariants principaux du modèle fonctionnel.

### R1 — Un client peut avoir plusieurs sites

```text
Client 1 ─── N Site
```

### R2 — Un site peut avoir plusieurs équipements

```text
Site 1 ─── N Équipement
```

### R3 — Un équipement possède son propre historique

Les interventions sont consultables depuis l'équipement.

### R4 — Un produit catalogue n'est pas un équipement

Le catalogue décrit une référence commerciale.

L'équipement représente une instance physique.

### R5 — Une vente n'est pas une installation

Une vente peut précéder l'installation.

### R6 — Une intervention peut être liée à un équipement

Lorsqu'il est connu, l'équipement constitue le rattachement technique principal.

### R7 — Une intervention peut temporairement être liée uniquement au site

Cela permet notamment de gérer un diagnostic avant identification précise de l'équipement.

### R8 — Statut et résultat sont indépendants

Exemple :

```text
Statut  = TERMINÉE
Résultat = PIÈCE NÉCESSAIRE
```

### R9 — Les checklists historiques ne doivent pas changer avec leur modèle

Modifier un modèle de checklist ne doit pas réécrire les interventions passées.

### R10 — Un équipement remplacé n'est pas supprimé

Son historique doit rester disponible.

### R11 — La garantie concerne l'équipement physique

Elle ne doit pas être portée uniquement par la référence catalogue.

### R12 — Une intervention peut produire un rapport historique

Un rapport transmis ne doit pas être silencieusement réécrit par une modification ultérieure.

### R13 — Un avis est facultatif

Une intervention peut avoir zéro ou un avis.

### R14 — Une donnée historique ambiguë ne doit pas être inventée

Les décisions de migration doivent préserver autant que possible la provenance et l'incertitude.

---

# 21. Priorité des workflows métier

Les workflows nécessaires au cœur de Tervo sont :

| Priorité | Workflow                          |
| -------- | --------------------------------- |
| P0       | Client → Site                     |
| P0       | Vente → Installation → Équipement |
| P0       | Création d'intervention           |
| P0       | Réalisation d'intervention        |
| P0       | Checklist / photos / matériel     |
| P0       | Résultat d'intervention           |
| P0       | Rapport                           |
| P1       | Maintenance préventive            |
| P1       | Dépannage                         |
| P1       | SAV / garantie                    |
| P1       | Remplacement d'équipement         |
| P1       | Avis client                       |
| P1       | Showroom → vente → installation   |
| P1       | Migration historique              |
| P2       | Stock / achats / fournisseurs     |
| P2       | Contrats avancés                  |
| P2       | Reporting avancé                  |

---

## 22. Principe directeur

Le parcours métier que Tervo doit rendre évident est :

```text
Qu'est-ce qui a été vendu ?
          ↓
Qu'est-ce qui a été installé ?
          ↓
Où est-il installé ?
          ↓
Qu'est-ce qui lui est arrivé ?
          ↓
Quelles interventions ont été réalisées ?
          ↓
Quel a été le résultat ?
          ↓
Quels documents et preuves ont été produits ?
```

Le cœur fonctionnel de Tervo est donc l'**historique technique de l'équipement**, alimenté par les interventions et relié au parcours commercial qui a conduit à son installation.
