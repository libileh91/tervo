# Sprint 7.6 — Déploiement VPS et documentation entretien

> **Tervo V2** · INT-111/112 + INT-124 à INT-130 · **Statut :** socle système/SSH validé ; INT-124 planifiée, autres tâches non démarrées
> **Dépendances :** Valider le périmètre livré et ses tests avant déploiement ; documenter explicitement le backlog restant.
> **Cadrage commun :** [Stage 7](../README.md) · [DAT](../../../DAT/new/00-sommaire.md)
> **Notes à produire :** `notes/backend/sprint7.6/` (guides transversaux et fiches entretien dans leurs dossiers dédiés).

> Reprend et finalise l'ancien sprint 6.4/6.5, sur le modèle v2.

## Découpage du chantier INT-111

INT-111 conserve la mise en service publique et ses preuves système
acquises ; INT-112 reste la documentation entretien. Les prérequis
techniques sont transférés aux nouveaux identifiants INT-124 à INT-130,
vérifiés libres. Aucun transfert de critères ou de tests ne vaut livraison.

| Ordre | Tâche | Livrable | Dépendances |
|---|---|---|---|
| 1 | INT-124 (3 pts) | 1Panel/OpenResty et administration privée | Socle système validé, pas clôture d'INT-111 |
| 2 | INT-125 (5 pts) | Images/configuration de production reproductibles | INT-124 pour la stratégie réseau |
| 3 | INT-126 (2 pts) | Bootstrap sécurisé du premier administrateur | Modèle identité existant |
| 4 | INT-127 (3 pts) | PostgreSQL cible et décision de reprise | INT-125 |
| 5 | INT-128 (5 pts) | Backup/restore vérifié en isolation | INT-125, INT-127 |
| 6 | INT-129 (5 pts) | Commande de release et rollback contrôlé | INT-125, INT-127, INT-128 |
| 7 | INT-111 (5 pts) | Mise en service manuelle, DNS/HTTPS et recette | INT-124 à INT-129 |
| 8 | INT-130 (3 pts) | CI/CD réutilisant la commande de release | INT-111 manuelle validée, INT-129 |
| 9 | INT-112 (3 pts) | Entretien fondé sur les preuves finales | INT-111 et INT-130 pour le bilan final |

Estimations indicatives à réévaluer par tâche : 34 points au total,
contre les 8 points historiques trop larges. Ce n'est pas une mesure du
travail déjà consommé. Le dossier reste `sprint7.6`, sans nouveau sprint.

**Règles communes**
- Feu vert distinct par tâche ; la reprise autorisée après découpage
  concerne **INT-124 uniquement**. Aucune tâche future n'est démarrée.
- Git/Compose définissent Tervo ; 1Panel administre proxy/certificats/
  opérations, pas une seconde stack PostgreSQL/applicative.
- CI vérifie, VPS construit les images de production ; GHCR reste hors
  périmètre. Ne pas confondre compilation Vue de vérification et image
  de production, ni rebuild ancien et artefact exact de secours.
- Secrets hors Git/logs partagés, `.env` explicite et `config --quiet`.
  Pannes/restores/rollback en isolation, pas d'opération destructive implicite.
- Commits par tâche ; guides dans `notes/backend/deploy/vps/`, notes de
  livraison dans `notes/backend/sprint7.6/`.
- Cas JSON : `id` et `legacy_id` historiques conservés, `task` indique
  le propriétaire et `origin_task` trace les transferts depuis INT-111.

---

## INT-111 — Déploiement VPS (5 pts)

**User Story**
En tant que **gérant**,
Je veux **déployer Tervo v2 sur un VPS en production**,
Afin de **disposer d'une instance publique avec HTTPS**.

**Acceptance Criteria**
- [x] VPS : Debian 13 (choix utilisateur, remplace Ubuntu 24.04 prévu), SSH clé, ufw (22/80/443), fail2ban
- [x] SSH par clé uniquement, connexion root directe désactivée, utilisateur non-root et mises à jour de sécurité automatiques
- [ ] Prérequis INT-124 à INT-129 livrés et vérifiés ; périmètre réellement disponible et backlog explicités avant publication
- [ ] Choix de reprise INT-127 appliqué après backup/restore INT-128 : transfert réel si nécessaire, aucune source présumée ; TD-B010 clôturé sur preuves
- [ ] Release manuelle via INT-129 : SHA/images identifiés, migrations avant exposition et disponibilité effective des services
- [ ] PostgreSQL non publié, services applicatifs loopback et administration 7410 privée ; surface publique 22/80/443 vérifiée
- [ ] DNS frontend/API, reverse proxy vers les services locaux, certificats Let's Encrypt valides, renouvellement automatique et redirection HTTP vers HTTPS vérifiés
- [ ] GET réels frontend/API et recette navigateur : admin via INT-126, connexion, dashboard, upload/récupération photo sans compte démo
- [ ] Backups planifiés et récupération INT-128 vérifiés sur le déploiement réel, y compris secrets/proxy ; seuils disque/RAM suivis
- [ ] Procédure rejouable dans `notes/backend/deploy/vps/` (dossier demandé par l'utilisateur) : prérequis, commandes, erreurs/corrections, schéma et différences mini-s1/VPS ; bilan du sprint dans `notes/backend/sprint7.6/`

**Technical Notes**
- INT-111 garde son objectif public et ses critères système validés.
  La CI/CD passe à INT-130, après la recette manuelle : clore INT-111
  ne termine pas le sprint et n'active pas `DEPLOY_ENABLED`.
- Socle Hostkey/Debian 13 contrôlé : compte `tervo`, accès SSH par clé,
  sudo, root SSH interdit, UFW actif et retour arrière annulé après
  reconnexion, jail sshd systemd chargée. Docker/Compose préinstallés ;
  noyau Security 6.12.111 actif après mise à jour et reboot.
- Dépôt Debian Security réactivé et overrides de validation temporelle
  APT retirés. Cadence quotidienne configurée pour Security uniquement,
  reboot/nettoyage automatiques désactivés ; dry-run code 0 relu par
  l'agent. La prochaine exécution automatique réelle reste à observer.
- Preuves et limites : [note SSH](../../../../notes/backend/deploy/vps/01-inventaire-et-acces-ssh.md)
  et [note système](../../../../notes/backend/deploy/vps/02-preparation-securite-systeme.md).
  Empreinte serveur indépendante non documentée et pare-feu fournisseur
  non inventorié ; application, HTTPS, données et déploiement CI non validés.
- Cas propriétaires : TC-INT-111-01/04/05/07. Le cas système reste
  partiel sur les vérifications non retranscrites ; les autres ne sont
  pas déclarés réussis.

---

## INT-124 — 1Panel et OpenResty à administration privée (3 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **installer le panneau et son proxy sans exposer l'administration**,
Afin de **gérer le VPS sans créer une seconde stack Tervo**.

**Acceptance Criteria**
- [ ] Archive v2.3.2 amd64 et SHA-256 vérifiés localement ; installateur lu, patch supprimant son appel d'ouverture automatique du port testé sans fuzz et avec contrôle d'unique changement
- [ ] Inventaire VPS actualisé, absence de données/installation 1Panel préexistantes vérifiée ; paquet exact préparé et hash revérifié sur le VPS
- [ ] Installation contrôlée, versions/chemins/services core-agent documentés ; Docker/Compose et daemon.json existants conservés, aucune licence Pro activée
- [ ] Administration 7410 privée en fonctionnement : bind loopback, tunnel avec clé choisie, bind local explicite et `ExitOnForwardFailure`, refus TCP public IPv4 ; aucune écoute administrative IPv6 ni IPv6 publique constatée dans l'inventaire ; bind et UFW conservés après restart core/agent
- [ ] Persistance après reboot réel et contrôle après mise à jour ; règles automatiques éventuelles inventoriées selon l'exception approuvée, refus extérieur IPv4/IPv6 si présente et accès navigateur recontrôlés
- [ ] OpenResty 1.31.1.1-2-4-noble installé : conteneur actif, écoutes 80/443 IPv4/IPv6 et HTTP public 200
- [ ] Mode OpenResty host/bridge observé, configuration valide, dépendances réseau nécessaires recréables et résolution/rechargement validés sur cible jetable sans IP statique de conteneur
- [ ] Changements du panneau journalisés, retour arrière et note de livraison documentés ; critères/cas mis à jour

**Technical Notes**
- Dépend du socle système déjà validé, **pas de la clôture d'INT-111**.
- Fichiers envisagés : `deploy/patches/1panel-v2.3.2-private-admin.patch`,
  `notes/backend/deploy/vps/03-preparation-1panel-prive.md` (à produire).
  Préparation locale ne signifie pas installation ou bind validé.
- Host : upstreams loopback du VPS. Bridge : noms sur réseau partagé et
  résolution/rechargement après recréation ; réseau externe seulement si utile.
- La recette du proxy utilise une cible jetable : elle n'attend pas les
  services Tervo d'INT-125 ni les domaines/HTTPS publics d'INT-111.
- Aucun PostgreSQL, runtime Python/Node ou Compose Tervo créé dans 1Panel.
- Cas TC-INT-111-02 : ID historique conservé, propriétaire INT-124.

---

## INT-125 — Stack de production reproductible (5 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **construire et configurer les services depuis un checkout neuf**,
Afin de **déployer un artefact traçable sans secrets ni fichiers manuels cachés**.

**Acceptance Criteria**
- [ ] Dockerfiles construisibles depuis un checkout neuf, frontend multi-stage sans `dist/` manuel ; versions/digests utiles fixés et images identifiables par SHA
- [ ] Secrets critiques obligatoires, `.env` explicite et modèle sans vraie valeur, permissions et parsing/échappement du DSN vérifiés ; validation Compose `--quiet`
- [ ] Binds applicatifs loopback, PG non publié, réseaux selon INT-124, volumes persistants et versions d'image explicites
- [ ] Healthcheck PostgreSQL, readiness backend vérifiant la DB et santé frontend ; panne DB testée en isolation
- [ ] Domaines/transport API choisis, client configurable sans hostname historique, appels API/uploads cohérents et CORS limité aux origines nécessaires
- [ ] Rotation des logs bornée, seuils disque/RAM et nettoyage documentés ; pas de suppression automatique des volumes/réseaux nécessaires
- [ ] Scénarios checkout neuf/configuration/disponibilité et note de livraison validés

**Technical Notes**
- Dépend d'INT-124 pour le réseau. Sources : Dockerfiles, Compose,
  configuration/main backend et client frontend.
- Une construction par image/version sur VPS ; compilation Vue CI distincte.
  OpenAPI seul ne remplace pas la readiness DB.
- Ne pas partager de rendu complet Compose/inspect avec les environnements.
- Cas TC-INT-111-03/08 : propriétaires INT-125, IDs conservés.

---

## INT-126 — Bootstrap sûr du premier administrateur (2 pts)

**User Story**
En tant qu'**administrateur d'exploitation**,
Je veux **créer le premier compte par une commande ponctuelle sécurisée**,
Afin de **valider la production sans seed destructif ni inscription publique**.

**Acceptance Criteria**
- [ ] CLI versionnée, DB explicitement configurée, saisie privée du secret ; rien dans Git/arguments/logs partagés
- [ ] Compte validé et mot de passe haché selon l'identité existante, création transactionnelle
- [ ] Rejeu sans réinitialisation silencieuse du secret/rôle/données d'un compte existant ; conflits explicites
- [ ] Aucun DELETE métier, seed automatique ou endpoint public d'inscription ajouté
- [ ] Création/rejeu/échec/login testés sur DB jetable ; TD-B019 traité pour le bootstrap autorisé et limites de l'ancien seed documentées

**Technical Notes**
- Dépend du modèle identité existant, pas d'une DB de production peuplée.
- Compte Linux, rôle DB et compte applicatif sont distincts. Ne pas modifier
  les comptes existants pour rendre une recette artificiellement verte.
- Sources : module identité, CLI opérateur et procédures. Cas TC-INT-126-01.
  Cette tâche ne démarre pas le registre public historique TD-B002.

---

## INT-127 — PostgreSQL cible et décision de reprise (3 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **préparer une DB dédiée et inventorier les données source**,
Afin de **choisir une reprise sans présumer un ancien conteneur ou rôle**.

**Acceptance Criteria**
- [ ] Patch PostgreSQL supporté retenu, une instance Compose Tervo, healthcheck/volume réels identifiés et aucun port publié
- [ ] Base/rôles/privilèges cadrés et état SQL contrôlé sans supposer `postgres`/`lob` ; rôle applicatif distinct du compte Linux
- [ ] Source réelle (mini-s1 ou aucune donnée) inventoriée : version/schema/volumes/provenance et décision utilisateur enregistrés
- [ ] Plan de reprise ou démarrage vide, préflight et retour arrière établis ; aucun volume existant réinitialisé par facilité
- [ ] Cible/reconstruction testée en isolation, commandes adaptées ; TD-B008/B009/B010 annotés selon la décision

**Technical Notes**
- Dépend d'INT-125. Distinguer les privilèges d'initialisation/migration et
  d'application. Modifier POSTGRES_* ne modifie pas un volume déjà initialisé.
- Prépare la DB et la décision, **pas le transfert réel** : backup/restore
  en INT-128, application du plan en INT-111 ; pas de dépendance circulaire.
  Cette tâche ne clôture pas seule TD-B010.
- Sources : Compose PostgreSQL et procédures SQL/reprise. Cas TC-INT-127-01.

---

## INT-128 — Sauvegarde et restauration cohérentes (5 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **sauvegarder et restaurer DB, uploads et paramètres nécessaires**,
Afin de **prouver la récupération sans détruire la source**.

**Acceptance Criteria**
- [ ] Scripts versionnés dump PG/archive uploads, volumes découverts et cohérence DB/fichiers garantie par une fenêtre contrôlée si nécessaire
- [ ] Archives atomiques, checksum, chiffrement, destination hors VPS explicitement autorisée et rétention ; aucun secret committé
- [ ] Un seul scheduler, procédure manuelle possible sans UI 1Panel
- [ ] Restore isolé vérifiant relations, photo et octets/empreinte PDF BYTEA, source et volumes réels inchangés
- [ ] Récupération sécurisée `.env` et reconstruction/export du proxy documentés sans secrets
- [ ] Preuves enregistrées pour TD-B010/TD-B022 ; limites volume et stockage photo TD-B020 explicites

**Technical Notes**
- Dépend d'INT-125/127. Fixtures autorisées/jetables, jamais seed sur base réelle.
  Dump et archive pris à des instants différents ne sont pas présumés cohérents.
- Scripts futurs dans `deploy/scripts/`, pas considérés déjà livrés.
- La preuve complète de restore utilise un jeu isolé avant INT-111 ;
  la planification/récupération du déploiement réel sera recontrôlée en INT-111.
- Cas TC-INT-111-09, propriétaire INT-128 ; clôture TD-B010 en INT-111
  après application réelle de la décision de reprise.

---

## INT-129 — Release traçable et rollback contrôlé (5 pts)

**User Story**
En tant qu'**exploitant**,
Je veux **une commande de release commune au manuel et à la CI**,
Afin de **maîtriser artefacts, migrations, disponibilité et retour arrière**.

**Acceptance Criteria**
- [ ] Commande versionnée avec Compose/.env explicites, services Compose, verrou de déploiement et SHA enregistré
- [ ] Build/version des images une fois, backup/maintenance avant migration si nécessaire, migration avant exposition, démarrage/attente puis GET readiness/smoke
- [ ] Échec propagé pour build/migration/readiness/smoke ; conteneur Up ou OpenAPI seul ne rend pas la release verte
- [ ] Images précédentes conservées sans prune immédiat, rollback vers artefact exact testé sans HEAD détaché laissé sur VPS
- [ ] Schéma compatible vérifié, roll-forward/procédure contrôlée sinon ; aucun downgrade/restore/`down -v`/nettoyage de volumes implicite
- [ ] Échec/rollback testés en isolation, commandes de secours et note de livraison documentées

**Technical Notes**
- Dépend d'INT-125/127/128. Script testé sur stack jetable avant sa première
  exécution réelle en INT-111 ; pas besoin de pipeline GitHub pour le clore.
- Sources : `deploy/scripts/`, versions locales, migrations et rollback.
  Rebuild ancien n'est pas ancien artefact.
- Cas TC-INT-111-10, propriétaire INT-129. La CI INT-130 appellera ce script.

---

## INT-130 — CI/CD de production sécurisée (3 pts)

**User Story**
En tant que **mainteneur**,
Je veux **automatiser une release déjà validée manuellement**,
Afin de **déployer les commits testés sans second chemin de déploiement**.

**Acceptance Criteria**
- [ ] INT-111 manuelle validée et INT-129 livrée ; workflow appelle cette commande, pas une seconde orchestration
- [ ] Clé CI distincte de la clé personnelle, compte/permissions documentés, Git lecture si privé ; Docker root-equivalent traité, pas de `NOPASSWD: ALL` par facilité
- [ ] Empreinte SSH vérifiée indépendamment et contrôlée par workflow, secrets GitHub scoped et autorisation production documentée
- [ ] CI tests/build Vue de vérification, `git pull --ff-only`, puis release ; ni image CI jetée, ni nom de conteneur dur, ni prune des images de secours
- [ ] `DEPLOY_ENABLED` activé après recette manuelle seulement, push autorisé et déploiement réellement exécuté/observé avec SHA/smoke
- [ ] Échecs remontés, désactivation de l'automatisation et notes/todos/cas à jour

**Technical Notes**
- Dépend d'INT-111/129 ; la CI n'est pas un prérequis de la recette manuelle.
- Sources : workflow, identité SSH/Git et configuration GitHub. Ne pas
  réutiliser la clé personnelle de l'agent pour les credentials CI.
- Cas TC-INT-111-06, propriétaire INT-130. CI verte avec Deploy sauté ne
  valide pas cette tâche ; anciens runs verts restent historiques.

---

## INT-112 — Doc entretien (3 pts)

**User Story**
En tant que **dev backend**,
Je veux **une fiche d'architecture et un Q/R entretien**,
Afin de **présenter le projet avec crédibilité (profil backend Java/Go)**.

**Acceptance Criteria**
- [ ] Fiche archi : chaîne Client→Site→Equipment→Intervention + migration
- [ ] Q/R : pourquoi la migration est transverse, pourquoi 3 zones, pourquoi transactions par batch
- [ ] Périmètre crédibilité : ne pas survendre Vue/TS, GH Actions, VPS, 1Panel
- [ ] Fichiers : `notes/interview/`
- [ ] Fiche d’une page présentable en 2–3 minutes : flux réseau, couches Router → Service → Repository, modèle V2, pipeline d’import et déploiement ; choix 1Panel, Compose et PostgreSQL justifiés
- [ ] Q/R couvrant healthchecks, idempotence, fuzzy matching, deux passes, transactions, interventions orphelines, CI/CD, ports, versions, modélisation V2 et sécurité VPS ; réponses de 3–5 phrases maximum
- [ ] Seuils 95/80 présentés comme paramètres à calibrer ; réalisations distinguées du backlog et compétences présentées sans survente
- [ ] Formulation adaptée pour chaque limite de compétence et pitch de 5–6 phrases ; livrables `architecture-presentation.md`, `questions-reponses.md`, `perimetre-credibilite.md`

**Technical Notes**
- Le différenciateur = la migration Excel (pandas, fuzzy, 2 passes, transactions)

---

## Cas de test

Voir [test-cases.json](test-cases.json).

Quinze scénarios : dix hérités (avec `legacy_id` conservés), trois issus
de la revue production et deux pour le bootstrap admin/la décision DB.
Le propriétaire `task` est aligné sur le découpage ; les IDs historiques
ne sont pas renommés et `origin_task` trace les transferts.
TC-INT-111-01 conserve les observations partielles du socle VPS,
TC-INT-111-02 la préparation locale 1Panel ; aucune installation ni
recette future n'est déclarée réussie. Les autres cas restent à exécuter.
Le planning ne vaut pas implémentation ou validation de déploiement.
