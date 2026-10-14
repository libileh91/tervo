# Guides transversaux

| Guide | Utilité |
|---|---|
| [Usage de uv](guide-uv-usage.md) | Commandes backend et dépannage du venv |
| [Migration pip → uv](migrate-pip-to-uv.md) | Historique de l'adoption de l'outil |
| [SQL brut et SQLAlchemy](raw_vs_sqlalchemy.md) | Comparaison pédagogique |
| [Rebase et merge](git-rebase-vs-merge.md) | Comprendre les historiques Git |
| [Checkout Delta](delta_worktree.md) | Identifier la copie de travail avant intégration |

## Références à conserver

[R0 — baseline du refactor](refactor-monolithe-modulaire/R0-baseline.md)
et ses JSON sont des **fixtures de non-régression utilisées par les tests**,
pas des déchets générés. Ne pas les supprimer ni les régénérer lors d'un nettoyage.
Le [planning du refactor](../../../docs/stages/stage7/refactor-monolithe-modulaire/README.md)
et son [bilan R0–R11](../refactor-monolithe-modulaire/bilan-R0-R11.md)
remplacent l'ancien plan intermédiaire.

Le Compose de production est [celui de `deploy/`](../../../deploy/docker-compose.yml).
L'ancien exemplaire PostgreSQL sous `extras/` a été supprimé : ne pas multiplier
les stacks ou réutiliser ses valeurs par défaut.
