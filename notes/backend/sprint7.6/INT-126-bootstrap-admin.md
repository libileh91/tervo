# INT-126 — Premier administrateur sans seed

## Pourquoi une commande séparée ?

`app.seed` efface des tables métier et crée des identifiants de démonstration.
Il ne convient donc pas à une base à conserver. `app.bootstrap_admin` ne
charge ni le seed ni `Base.metadata.create_all` : **les migrations doivent
précéder son exécution**. Aucun endpoint d'inscription n'a été ajouté.

## Contrat de la commande

La commande attend un nom de base non secret, une configuration DB fournie
explicitement dans l'environnement (`DATABASE_URL` ou composants
`TERVO_DB_NAME/USER/PASSWORD`) et un terminal interactif :

```bash
python -m app.bootstrap_admin --confirm-db-name NOM_DE_LA_BASE
```

Sur un futur backend Compose **après migration**, elle pourra être exécutée
ainsi (sans insérer de secret dans la commande) :

```bash
docker compose --env-file CHEMIN_PRIVE -f deploy/docker-compose.yml exec backend \
  python -m app.bootstrap_admin --confirm-db-name NOM_DE_LA_BASE
```

Ce n'est pas une commande de release : la DB cible, l'environnement et
l'absence de processus bootstrap concurrent sont à contrôler avant usage.
**Elle n'a pas été exécutée sur le VPS.**

Le nom d'utilisateur et l'email sont demandés au terminal. Le secret est
saisi et confirmé avec `getpass` (sans écho) ; il ne figure ni dans les
arguments, ni dans le dépôt, ni dans les messages de résultat. Sans TTY, avec
DB implicite ou nom de base différent, la commande refuse avant toute
écriture. Les noms sont limités à 3–100 caractères ASCII sûrs, l'email doit
avoir une forme valide, le secret 12–72 octets UTF-8 (limite bcrypt).

## Transaction, rejeu et login

`check_existing` vérifie les trois conflits possibles : username, email et
existence d'un autre `Role.ADMIN`. Un admin **actif** avec exactement la
même identité produit « déjà présent » sans demander le secret et sans
modifier son hash. Un compte inactif, un autre rôle ou une identité divergente
est refusé ; une collision d'unicité concurrente échoue aussi explicitement.
L'outil n'est pas un moyen de réinitialiser un compte.

La création utilise `User` et `get_password_hash` existants :

```python
async with session.begin():
    created = await create_admin(session, username, email, password)
```

La session englobe vérification et `flush` : échec ou conflit avant commit
annule la création. Aucun `DELETE` métier. Le routeur `/api/v1/auth/login`
emploie ensuite la même vérification bcrypt et renvoie ses jetons habituels.
Le CLI suppose une exécution ponctuelle par un seul opérateur : il ne prétend
pas imposer une unicité globale « un admin au total » face à deux créations
concurrentes avec identités différentes.

## Limite du seed de démo

`app.seed` refuse désormais tout environnement autre que `development` sur
SQLite. **Sur une SQLite de développement existante, il reste destructif** :
sa boucle de `DELETE` ne protège pas les données importées. TD-B019 reste
ouvert pour tout usage sur données persistantes ; ne pas lancer le seed
depuis Dockge comme raccourci.

## Preuves locales et suite

`uv run pytest tests/test_bootstrap_admin.py tests/test_seed_bootstrap.py
tests/test_auth.py -q` : **18 tests réussis** (création/hash, rejeu, conflits,
saisie simulée via TTY, absence de TTY et mauvaise DB, login HTTP, refus du
seed hors dev, non-régressions auth et seed démo). Un `uv run pytest tests/ -q`
complet a été interrompu par le timeout de 120 s après ~37 % : il ne vaut pas
validation de la suite complète. Le test construit seulement la table `User`
au schéma courant dans une SQLite temporaire ; il **ne valide pas** la chaîne
Alembic PostgreSQL. Usage avec migrations réelles et création de l'admin
sur VPS restent pour INT-111, après décision DB (INT-127) et release (INT-129).
