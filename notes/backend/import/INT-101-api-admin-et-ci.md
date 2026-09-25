# INT-101 — API admin d’import et contrôle continu

## Le parcours livré

`app/api/v1/imports.py` expose six routes : aperçu, validation, exécution, liste des imports, détail et anomalies. Elles partagent la dépendance `import_admin` : le JWT doit désigner un utilisateur actif de rôle ADMIN. Les tests utilisent de vrais tokens ; ils vérifient aussi que les appels anonymes ou TECHNICIAN ne créent aucun import.

Les contrats Pydantic sont dans `app/schemas/imports.py`. Le manifeste est une liste JSON transmise dans un champ multipart avec le fichier. `TypeAdapter` valide cette liste ; `UploadFile` est lu avec une limite de 10 Mio + 1 octet pour pouvoir répondre `413`. Les formats malformés, sélections incohérentes et champs inconnus donnent `422`.

La description détaillée et les exemples JSON vivent dans [la spec API](../../../docs/DAT/new/02-techniques/03-api.md#administration--migration-des-archives-int-101).

## Exemple de déroulement

1. Charger le fichier et son namespace. L’aperçu conserve la source et renvoie dix lignes maximum ; aucune entité métier n’est créée.
2. Soumettre les corrections et décisions via `validate`. Les lignes incertaines restent `pending`, avec leurs anomalies et candidats.
3. Lire les statistiques et le plan. Si une décision change, valider à nouveau et utiliser le nouveau jeton.
4. Exécuter avec `batch_id` et `plan_token`. Aucun mapping ni décision supplémentaire n’est accepté ici.
5. Lire le statut du rapport et consulter les anomalies par révision. Après une interruption, réexécuter le plan courant ou revalider si le référentiel a changé.

Une association doit préciser exactement une cible. Un motif composé uniquement d’espaces est refusé. `review` permet de corriger le site d’une intervention puis d’examiner les doublons proposés sans autoriser implicitement une création.

Pour un téléphone manquant, la valeur originale reste vide dans la trace même après correction. Si l’administrateur confirme l’association à un client existant, les coordonnées de ce client ne sont pas écrasées. Le journal peut donc contenir une ancienne anomalie résolue : sa révision explique à quel moment elle a été constatée.

## Pourquoi séparer session d’authentification et transactions d’import ?

L’authentification effectue déjà un SELECT sur l’utilisateur, ce qui ouvre une transaction SQLAlchemy. Démarrer une nouvelle transaction sur la même session provoquerait une erreur. `ImportService` reçoit le moteur de cette session et ouvre ses propres sessions pour les validations et sous-lots. Les tests API PostgreSQL vérifient ce chemin réel, pas seulement un appel direct au service.

## Tests et CI

Les tests `test_import_api_v2.py` couvrent les six routes, les rôles, la pagination, les fichiers invalides, la limite d’upload, les corrections, les associations, les anciens jetons, les changements du référentiel et les lignes déjà commitées.

```bash
cd backend
uv run pytest tests/ -q
TERVO_IMPORT_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/TEST_DB \
  uv run pytest tests/test_import_service_v2.py tests/test_import_api_v2.py -q
```

GitHub Actions conserve la suite générale SQLite et ajoute PostgreSQL 17.4 : montée des migrations, retour d’une révision, remontée et tests service/API d’import dans des schémas isolés. Cela clôt TD-B011 pour le pipeline d’import ; les autres modules ne sont pas tous testés sur les deux dialectes.

## Limites explicites

Pas d’écran frontend d’import dans cette tâche, ni de worker asynchrone, d’OCR ou d’import métier des PDF. Le test de 502 lignes et le pack fictif ne valident pas une volumétrie réelle de vingt ans. TD-B016 conserve la mesure mémoire/durée/verrous à réaliser avant cette migration.
