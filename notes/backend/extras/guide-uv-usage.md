# uv — commandes utiles pour Tervo

Les dépendances et versions de référence sont dans
[`backend/pyproject.toml`](../../../backend/pyproject.toml) et
[`backend/uv.lock`](../../../backend/uv.lock), pas dans cette note.
Exécuter les commandes depuis `backend/`.

## Installer et travailler

```bash
uv --version
uv sync --frozen
uv run uvicorn app.main:app --reload
```

`uv sync --frozen` installe depuis le lockfile sans le recalculer.
`uv run` utilise le venv du projet ; pas besoin de l'activer manuellement.

| Besoin | Commande |
|---|---|
| Tous les tests | `uv run pytest tests/ -q` |
| Un fichier de tests | `uv run pytest tests/test_auth.py -q` |
| Ajouter une dépendance | `uv add NOM` |
| Ajouter un outil de dev | `uv add --dev NOM` |
| Retirer une dépendance | `uv remove NOM` |
| Vérifier les paquets installés | `uv pip list` |
| Exécuter un module | `uv run python -m app.bootstrap_admin --help` |

Les opérations `add/remove` modifient le manifeste et le lockfile :
les vérifier et les committer avec la tâche qui les nécessite.

## Migrations et déploiement

Sur une DB locale **explicitement choisie**, `uv run alembic upgrade head`
applique les migrations ; `revision --autogenerate` prépare une migration à
relire, pas une validation automatique.

En production, suivre le [planning et la procédure de release](../deploy/README.md).
Ne pas remplacer les Dockerfiles versionnés par une recette copiée de cette
note. **Ne pas lancer `app.seed` pour créer un admin** : utiliser le
[bootstrap INT-126](../sprint7.6/INT-126-bootstrap-admin.md) après les migrations.

## Venv déplacé ou cassé

Un venv contient des chemins absolus (activation, shebangs). Renommer ou
déplacer le checkout peut les invalider. Vérifier d'abord le dossier courant
et l'interpréteur :

```bash
pwd
uv run python -c "import sys; print(sys.executable)"
```

Si nécessaire, recréer seulement le venv généré du bon checkout, puis relancer
`uv sync --frozen`. Ne pas modifier les données, migrations ou secrets pour
réparer un problème d'environnement Python.
