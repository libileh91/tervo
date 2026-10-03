# INT-108 — Avis client : invitation, note réelle et soumission publique

## 1. Ce qui existait et ce qui change

Le refactor monolithe modulaire avait déjà déplacé `Review` dans
`app/modules/interventions/`. Sa FK pointe **déjà** vers `intervention.id`
et l'unicité de `intervention_id` interdit deux avis pour la même intervention.
Il n'y a donc pas de nouvelle table ni de second renommage `job → intervention`.
La relation `Intervention.review` est `uselist=False`. Une intervention sans
avis reste permise ; la clôture crée normalement l'invitation dans la même
transaction que le changement de statut (voir la note INT-106).

Le comportement antérieur prêtait à confusion : la clôture créait un avis
**non soumis** avec `rating=5`. Cette note pouvait être confondue avec un
retour client. L'API publique historique utilisait
`POST /api/v1/review/{share_token}/submit`, alors que le sprint demande
`POST /api/v1/reviews` avec un token de partage.

INT-108 reprend une règle unique : **une invitation n'est pas une réponse**.
`rating` vaut `NULL` tant que `submitted_at` vaut `NULL` ; après soumission,
la note est comprise entre 1 et 5. La vieille route reste fonctionnelle pour
ne pas casser les clients existants ; les deux routes utilisent le même service.
La page publique soumet désormais sur `/api/v1/reviews`. Le lien navigable
`/review/{token}` et son GET public restent inchangés.

## 2. Invariants du modèle et préservation des données

Dans `models/review.py`, la colonne est désormais nullable et une contrainte
SQL lie note et date de soumission :

```python
CheckConstraint(
    "(submitted_at IS NULL AND rating IS NULL) OR "
    "(submitted_at IS NOT NULL AND rating BETWEEN 1 AND 5)",
    name="ck_review_submission_rating",
)
rating = Column(Integer, nullable=True)
```

La contrainte unique sur `intervention_id` n'a pas changé. Elle protège
physiquement `Intervention 1 → 0..1 Review`, y compris si deux insertions
arrivent simultanément. Le token reste unique, expire après 30 jours à la
clôture, et la réponse publique GET ne retourne ni token ni note : elle expose
uniquement le titre/date, le nom du technicien et `already_reviewed`.

Dans `services/intervention.py`, la création du brouillon n'envoie plus
`rating=5` au repository. `rating=NULL` et `submitted_at=NULL` sont enregistrés
avec la transition `IN_PROGRESS → COMPLETED`, le `result` explicite et la
date de clôture dans **un seul commit** ; un échec annule aussi l'invitation.
Une deuxième clôture est rejetée par le service d'intervention, sans recréer
un token. Aucun email/SMS n'est envoyé automatiquement.

La migration `k108e0010001` :

1. Vérifie avant modification qu'aucun avis **déjà soumis** n'a une note
   absente ou hors plage (sinon elle refuse l'opération et affiche son ID).
2. Rend la note nullable, puis exécute
   `UPDATE review SET rating = NULL WHERE submitted_at IS NULL`.
   Les vrais avis conservent note, date, texte, token et ID.
3. Installe la contrainte SQL ci-dessus. Sous SQLite, les opérations
   `batch_alter_table` reconstruisent la table ; l'UPDATE doit avoir lieu
   **après** le retrait du `NOT NULL`, sinon SQLite le refuse.
4. Le downgrade refuse de remettre `NOT NULL` en présence d'invitations
   sans note. Remplacer `NULL` par 5 lors d'un retour arrière aurait recréé
   de faux avis ; on choisit un refus explicite plutôt qu'une altération
   silencieuse. Sur une base ne contenant que des avis soumis, le downgrade
   peut rétablir l'ancienne contrainte de nullabilité.

Ne pas faire de `stamp` sur une vraie base pour préparer cette migration :
il ne recrée pas les migrations antérieures. Le `stamp` utilisé dans la
recette locale ci-dessous ne concerne qu'une **base jetable** préparée avec
le schéma INT-107.

## 3. Parcours HTTP et rôle des couches

| Route | Auth | Rôle / résultat |
|---|---|---|
| `GET /api/v1/review/{share_token}` | Aucune | Aperçu public minimal, `already_reviewed` ; 404 si lien inconnu/expiré |
| `POST /api/v1/reviews` | Aucune | Corps avec `share_token`, `rating` (1..5), `comment` et `reviewer_name` optionnels ; 200 une fois |
| `POST /api/v1/review/{share_token}/submit` | Aucune | Ancienne forme, même service et mêmes garanties |

Exemple de requête canonique :

```http
POST /api/v1/reviews
Content-Type: application/json

{"share_token":"<token-de-la-cloture>","rating":4,"comment":"Très bien","reviewer_name":"Client"}
```

`schemas/review.py` hérite de `ReviewSubmitRequest` pour la route canonique
et y ajoute `share_token` requis (1 à 64 caractères). Pydantic refuse
l'absence du token et les notes hors plage avec 422. Le routeur n'exige
aucun JWT sur ces trois endpoints : la possession d'un token valide est le
seul droit d'accès. Il faut donc traiter ce token comme un secret, ne pas
afficher les avis d'autres clients et limiter sa circulation aux liens
prévus. L'URL historique contient encore le token ; le nouveau POST le
transporte dans le corps de la requête.

`services/review.py` conserve le GET détaillé et délègue la soumission au
repository. Le point décisif est l'UPDATE conditionnel de
`repositories/review.py` :

```python
update(Review).where(
    Review.share_token == token,
    Review.share_token_expires_at > now,
    Review.submitted_at.is_(None),
).values(
    rating=rating, comment=comment, reviewer_name=reviewer_name,
    submitted_at=now,
)
```

Ce n'est pas « lire puis écrire » : deux soumissions ne peuvent pas toutes
deux remplacer la note de la première. Le gagnant met note/commentaire/date
à jour et commit ; si aucune ligne n'est modifiée, le repository rollback
la transaction et le service distingue ensuite un token invalide/expiré
(404) d'un avis déjà soumis (400). La seconde tentative ne modifie ni la
note ni son horodatage. Aucun historique d'édition des avis n'est créé.

Le frontend `ReviewPage.vue` conserve le GET et la route de partage visible
par le client ; son formulaire POST utilise désormais `/api/v1/reviews`,
avec le token dans le JSON. Un échec conserve les saisies et affiche l'erreur ;
une réponse réussie passe l'écran en mode « déjà évalué ».

## 4. Recettes exécutées et limites

Les quatre cas détaillés sont dans `docs/stages/stage7/sprint7.4/test-cases.json`.
Pour aller vite, la validation HTTP ajoute **une seule recette intégrée** au
fichier `backend/tests/test_api.py`, et réutilise les fixtures historiques
avec `rating=NULL` pour les invitations. La recette :

- clôture avec un résultat explicite ; vérifie en DB `rating=NULL`,
  `submitted_at=NULL` et un token ; une seconde insertion pour le même
  `intervention_id` est rejetée par la contrainte unique ;
- GET sans auth, puis POST canonique sans auth, retour 200 et GET
  `already_reviewed=true` ;
- deuxième POST via l'ancienne route : 400 ; note/commentaire conservés ;
- note 0/6 et corps incomplet : 422 ; token inconnu/expiré : 404 et
  aucune soumission effectuée.

Commandes effectivement exécutées dans `backend/` :

```sh
uv run pytest tests/test_api.py -q -k 'Review or int108 or complete_intervention_creates_review'
uv run pytest tests/test_api.py -q
```

Résultats : 11 réussis / 18 non sélectionnés, puis 29 réussis,
un warning de dépréciation `passlib/crypt`. Depuis `frontend/`,
`bun run typecheck` puis `bun run build` ont réussi. Cela ne constitue
ni un smoke navigateur ni un résultat CI distant.

Pour la migration, une SQLite **jetable** a été construite avec le schéma
historique de `review`, un avis en attente (note fictive 5) et un avis soumis
(note 4, commentaire original), puis `alembic stamp j107e0010001` et
`alembic upgrade head`. Observé : le premier avis garde son ID/token mais
sa note devient `NULL`, le second conserve 4 et son commentaire, la
contrainte `ck_review_submission_rating` existe. `alembic downgrade -1`
sur cette base peuplée a refusé avant DDL, sans perdre l'invitation.

Tentative distincte de migration **depuis zéro** sur SQLite : échec dans
`9d34b52092ce_rename_job_to_intervention.py` sur `ALTER TYPE`, instruction
PostgreSQL historique antérieure à INT-108. La migration INT-108 n'a donc
été exercée qu'à partir d'un schéma préalable jetable stampé, **pas**
sur PostgreSQL ni sur une base de production. Une vérification ciblée sur
PostgreSQL reste requise avant déploiement ; le test de concurrence réelle
entre deux connexions n'a pas été exécuté ici. La condition SQL protège
la valeur, mais les détails d'attente/verrouillage dépendent du SGBD.

## 5. Après INT-108

`docs/todos/backend.md` et `docs/todos/frontend.md` ont été relus avant
et après la tâche. TD-B004 (photos obligatoires), TD-B013 (rôles),
TD-B016 (volume import), TD-B019 (seed sûr), TD-B020 (stockage photo),
TD-B021 (issues historiques), TD-B022 (volumétrie PDF), TD-F007
(catalogue/showroom) et TD-F008 (administration checklist) ne sont pas
débloqués par l'avis client ; ils restent ouverts selon leurs dépendances.
L'avis client est optionnel pour l'intervention et ne constitue ni un
résultat de clôture ni une transmission de rapport.
