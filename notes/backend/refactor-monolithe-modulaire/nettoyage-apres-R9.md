# Nettoyage technique après R9

> **Demande utilisateur :** nettoyer les dossiers vides/résidus générés et committer R9.
> **R9 :** accepté et committé sous `205969a23370d3ef5883ac38cf3280b6a5cd661c`.
> **Périmètre :** worktree Delta attaché uniquement ; aucun feu vert R10/R11.

## Ce qui a été retiré

| Élément | Nettoyage |
|---|---|
| Caches Python/pytest | 27 répertoires ignorés, sous `backend/app`, `tests`, `alembic` et `.pytest_cache` |
| Dossiers devenus vides | `backend/app/importers`, `exporters`, `repositories`, `services` |
| Sources suivies sans code actif | Les trois `__init__.py` restants dans exporters/repositories/services |
| Fichiers OS | Aucun `.DS_Store`/`Thumbs.db` présent à retirer |

`importers/__init__.py` a déjà été déplacé dans le commit R9, vers
`modules/imports/pipeline/__init__.py` : ce n'est pas un export supprimé.
Les deux init repositories/services étaient vides ; celui d'exporters ne
contenait qu'une docstring décrivant l'ancien emplacement du renderer.
Aucun import actif ne dépend de ces trois namespaces.

Les caches et répertoires vides ne sont pas versionnés par Git. Leur retrait
physique nettoie ce worktree ; le commit de nettoyage conserve la suppression
des trois fichiers suivis et le présent compte rendu.

## Ce qui a été conservé

- `.git`, `.delta`, `.venv`, `node_modules` et `dist` exclus du parcours ;
- tous les dossiers `uploads`, même vides, préservés ;
- bases `.db`, fichiers `.env`, sources, fixtures et preuves conservés ;
- symlinks non parcourus ;
- packages Python actifs et leurs init conservés, même lorsqu'un init est vide ;
- auth/dashboard encore legacy et réexports Base/API/models conservés pour R10/R11.

Il ne s'agit ni d'un `git clean -fdx`, ni d'un déplacement de User/Auth,
ni d'une clôture d'INT-123. Les frontières encore actives ne sont pas
supprimées pour rendre artificiellement tous les dossiers « propres ».

## Contrôles avant suppression

Le parcours ignore les répertoires protégés et les symlinks. Pour chaque cache,
le script vérifie qu'aucun fichier n'est suivi dans l'index et que le chemin
est ignoré par Git avant de le supprimer. Les autres dossiers sont retirés
uniquement par `rmdir()` : un contenu restant empêche leur suppression.
Les trois sources suivies ont été retirées par l'outil d'édition, après
inspection de leur contenu et des imports actifs.

## Validation après nettoyage

Exécution réelle avec le Python préexistant, PYTHONPATH du backend attaché,
cwd/SQLite/uploads temporaires, `PYTHONDONTWRITEBYTECODE=1` et
`-p no:cacheprovider` :

| Vérification | Résultat |
|---|---|
| 28 empreintes sources/tests/fixtures R9 | Conformes au manifeste |
| Huit fichiers ciblés, replay intégral inclus | **115 passed**, 1 warning, 34,32 s |
| Suite SQLite entière | **371 passed**, 7 warnings, 88,34 s |

Ces tests comprennent les snapshots metadata/OpenAPI R0 et l'oracle avant/après
des imports. Les données et preuves historiques sont intactes.
Les 95 tests PostgreSQL antérieurement validés pour R9 ne sont pas présentés
comme réexécutés pour ce nettoyage. Aucun build, CI distante, déploiement,
seed ou push.

## Découpage Git

R9 est committé seul sous `[DEV]INT-121 — Refactor : isoler le domaine imports`,
avec ses développements, tests, oracle, notes et suivi.
La suppression des trois namespaces sans code actif et l'actualisation de
l'état committé du planning sont regroupées dans un commit technique distinct.
R10 et R11 restent ouverts et attendent une autorisation explicite.
