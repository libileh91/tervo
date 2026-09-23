# Tervo — Modèle métier

## 1. Vue d'ensemble

Le modèle métier repose sur le cycle suivant :

```text
Client
  │
  └── Site
       │
       ├── Équipement
       │    │
       │    └── Intervention
       │         ├── Checklist
       │         ├── Photo
       │         ├── Matériel utilisé
       │         ├── Rapport
       │         └── Avis
       │
       └── ...

Produit catalogue
       │
       └── peut donner naissance à plusieurs équipements installés
```

Le modèle distingue systématiquement la **référence commerciale** de la **réalité physique installée**.

## 2. Client

Le client est le propriétaire ou interlocuteur commercial de la relation.

Un client peut être :

* une personne ;
* une entreprise ;
* une autre organisation.

Relation principale :

```text
Client 1 ─────── N Site
```

Le client ne représente pas directement une adresse physique.

## 3. Site

Le site représente le lieu physique dans lequel se trouve l'activité concernée.

Un site appartient à un client et peut contenir plusieurs équipements.

Relation :

```text
Client 1 ─────── N Site
Site   1 ─────── N Équipement
```

Un site possède au minimum une identité et une localisation permettant aux équipes d'intervenir.

## 4. Produit catalogue

Le produit catalogue est une référence commerciale.

Il peut être :

* présenté au showroom ;
* proposé à un client ;
* vendu ;
* installé.

Il ne possède pas d'historique d'intervention propre.

Exemple :

```text
Produit
Marque : Daikin
Modèle : XYZ
Référence : ABC-123
Catégorie : PAC air/eau
```

## 5. Équipement

L'équipement est l'instance physique installée sur un site.

Il possède son propre cycle de vie et son propre historique.

Informations métier typiques :

* produit d'origine ;
* site ;
* numéro de série ;
* date d'installation ;
* date de mise en service ;
* garantie ;
* état du cycle de vie.

Cycle simplifié :

```text
À installer
    ↓
Installé
    ↓
En service
    ├── Maintenance
    ├── Dépannage
    └── SAV
    ↓
Remplacé / retiré
```

Un équipement représente une unité physique installée. Il n'a pas d'état
`PLANNED` ; la planification relève de l'installation.

Un équipement remplacé reste conservé afin de préserver son historique.
Lorsqu'un équipement est remplacé, l'ancien équipement est conservé et
pointe vers le nouvel équipement via `replaced_by_id`.

## 6. Intervention

L'intervention représente une opération terrain.

Elle possède notamment :

* un type ;
* un statut ;
* un résultat ;
* un site ;
* éventuellement un équipement ;
* un ou plusieurs intervenants ;
* une période ;
* des observations.

### Type

Le type décrit la nature de l'opération :

* installation ;
* mise en service ;
* maintenance préventive ;
* maintenance corrective ;
* dépannage ;
* diagnostic ;
* SAV ;
* autre.

### Statut

Le statut décrit le cycle d'avancement :

```text
Planifiée → En cours → Terminée
                  └──→ Annulée
```

### Résultat

Le résultat décrit l'issue métier :

* résolu ;
* partiellement résolu ;
* non résolu ;
* pièce nécessaire ;
* devis nécessaire ;
* à replanifier.

Le résultat peut être renseigné à la clôture et reste indépendant du statut.

## 7. Checklist

Une checklist possède deux niveaux :

```text
Modèle de checklist
        │
        │ au moment de la création
        ▼
Checklist de l'intervention
```

Le modèle sert de base.

L'instance associée à l'intervention constitue l'historique réel des contrôles effectués.

Une évolution du modèle ne doit pas modifier rétroactivement les anciennes interventions.

## 8. Photo

Une photo appartient au contexte d'une intervention.

Elle peut être qualifiée par son usage :

* avant ;
* après ;
* équipement ;
* anomalie ;
* pièce ;
* autre.

La photo contribue à la traçabilité de l'intervention.

## 9. Matériel utilisé

Le matériel utilisé représente ce qui a été consommé ou posé pendant l'intervention.

V1 :

```text
Matériel
├── désignation
└── quantité
```

Une référence vers le catalogue produit pourra être introduite ultérieurement.

## 10. Rapport

Le rapport est une restitution de l'intervention.

Il constitue un document historique et ne doit pas dépendre silencieusement d'un état mutable de l'intervention après transmission.

Conceptuellement :

```text
Intervention
      │
      └── Génération
             ↓
          Rapport
             │
             └── état historique transmis
```

## 11. Avis

Un avis est associé à une intervention.

Cardinalité :

```text
Intervention 1 ───── 0..1 Avis
```

Cette relation permet de rattacher directement la satisfaction exprimée au contexte de l'intervention.

## 12. Showroom

Le showroom est une activité commerciale distincte de l'installation terrain.

On distingue :

* produit catalogue ;
* produit présenté ;
* visite ;
* suivi commercial ;
* vente ;
* installation.

Une visite peut présenter plusieurs produits.

Le suivi commercial doit pouvoir évoluer sans transformer directement la visite en vente.

## 13. Vente

La vente représente l'événement commercial.

Elle est distincte de l'installation :

```text
Produit
   ↓
Vente
   ↓
Installation
   ↓
Équipement
```

Cette distinction permet de gérer les situations où un produit est vendu mais pas encore installé, ou lorsqu'une installation intervient plus tard.

Une ligne de vente peut donner lieu à plusieurs installations lorsque la
quantité vendue est supérieure à 1.

## 14. Garantie et SAV

La garantie est une propriété liée à l'équipement installé.

Le SAV est une activité portant sur cet équipement.

Le modèle doit donc permettre :

```text
Équipement
    │
    ├── Garantie
    │
    └── SAV
         │
         └── Intervention
```

L'éligibilité à la garantie lors d'une intervention doit pouvoir être explicitement qualifiée.

Une intervention peut être explicitement qualifiée comme réalisée sous
garantie. Cette qualification est conservée dans l'historique de
l'intervention.

## 15. Relations principales

| Concept                            | Relation          |
| ---------------------------------- | ----------------- |
| Client → Site                      | 1 → N             |
| Site → Équipement                  | 1 → N             |
| Produit → Équipement               | 1 → N             |
| Équipement → Intervention          | 1 → N             |
| Intervention → Checklist           | 1 → 0..1          |
| Intervention → Photo               | 1 → N             |
| Intervention → Matériel            | 1 → N             |
| Intervention → Rapport             | 1 → 0..N versions |
| Intervention → Avis                | 1 → 0..1          |
| Visite showroom → Produit présenté | 1 → N             |
| Équipement → historique SAV        | 1 → N             |

## 16. Principes de modélisation

### 16.1 La réalité physique prime sur la référence commerciale

Un produit catalogue peut être vendu plusieurs fois.

Chaque installation physique doit pouvoir être suivie séparément.

### 16.2 L'historique ne doit pas être écrasé

Une intervention terminée, une checklist réalisée, un rapport transmis ou un équipement remplacé constituent des faits historiques.

### 16.3 Les événements métier restent distincts

Une vente n'est pas une installation.

Une installation n'est pas une maintenance.

Un statut n'est pas un résultat.

Un produit catalogue n'est pas un équipement.

### 16.4 Les relations ambiguës doivent rester explicites

Lorsque Tervo ne peut pas déterminer automatiquement une relation historique, il doit conserver l'incertitude plutôt que créer une fausse certitude.

### 16.5 Le modèle doit rester extensible

Stock, fournisseurs, contrats et reporting pourront être ajoutés autour de ce noyau sans remettre en cause les concepts fondamentaux.
