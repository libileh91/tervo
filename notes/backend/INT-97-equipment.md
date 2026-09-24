# INT-97 — Appareils physiques, remplacement et historique

## Référence commerciale et instance physique

Product décrit une référence commerciale. Equipment décrit un appareil sur un Site, avec ses dates, son numéro de série et sa garantie. La FK product_id est nullable et non unique : deux appareils peuvent partager la même référence, et les imports historiques peuvent ignorer le produit.

Les statuts sont ACTIVE, OUT_OF_SERVICE, REPLACED et RETIRED. PLANNED appartient au domaine Intervention, pas à Equipment. L’enum est également contraint en base. installation_id est réservé, nullable, sans FK jusqu’à INT-103 : le report est centralisé dans TD-B014 et l’API refuse un identifiant d’installation libre.

## API et remplacement atomique

- `POST /equipment` crée un appareil ; son site et son produit éventuel sont vérifiés.
- `GET /equipment` pagine et filtre par site_id, product_id et lifecycle_status.
- `GET /equipment/{id}` et `GET /sites/{id}/equipment` consultent le parc.
- `POST /equipment/{id}/replace` accepte new_product_id, serial_number, installation_date et notes. Il renvoie le nouvel appareil (201), sur le même site.

Le remplacement conserve l’ancien, passe son statut à REPLACED et renseigne ancien.replaced_by_id = nouveau.id. Les interventions ne sont jamais déplacées. Un second remplacement du même appareil ou le remplacement d’un appareil RETIRED renvoie 409.

Le repository insère le nouveau puis modifie l’ancien dans une même transaction. L’UPDATE conditionnel exige que l’ancien soit encore remplaçable : si une requête concurrente a déjà gagné, rollback retire aussi la nouvelle instance. Un essai réel PostgreSQL avec deux sessions simultanées confirme un seul succès et aucun orphelin.

Les utilisateurs authentifiés accèdent à cette API terrain, selon le fonctionnement actuel de Site/Intervention. Aucun DELETE Equipment n’est exposé. Supprimer un Site ou Client qui possède des équipements renvoie 409 pour préserver leur historique.

## Raccordement à Intervention et Product

Intervention.equipment_id est une FK nullable. Le service contrôle Equipment.site_id == Intervention.site_id à la création et à la modification. Sans appareil identifié, un diagnostic reste possible. Une modification avec equipment_id=null retire le lien. under_warranty est désormais accessible en entrée de l’API.

TD-B012 est terminé : Product.equipment et Equipment.product sont bidirectionnels, et le test métier vérifie deux appareils d’un même produit après désactivation du catalogue.

## Revue INT-94 à INT-97

La migration Site a été corrigée avant publication : elle renseigne site_id avant NOT NULL, et conserve les interventions historiques. Pour les clients déjà dotés de plusieurs sites, elle choisit le premier identifiant, faute de localisation dans l’ancien modèle. Voir la note INT-95.

La revue frontend a aussi corrigé la configuration TypeScript, les callbacks de rechargement, les types photo/matériel et l’option de pagination Vue Query. Le contrôle de types passe désormais, ainsi que le build.

## Vérifications

```bash
cd backend
uv run pytest tests/ -q
cd ../frontend
npm run typecheck
npm run build
```

Résultat local : 141 tests backend réussis. Les tests Equipment activent les FK SQLite et couvrent le remplacement, la conservation des interventions, les références absentes, la cohérence du site, le diagnostic sans appareil, les états interdits, la pagination, les protections de suppression et l’authentification.

Sur PostgreSQL 17.4 jetable : montée depuis le schéma avant INT-94 avec une intervention existante, second upgrade head, downgrade jusqu’avant INT-94 et remontée. L’intervention et son client restent reliés, avec traduction du statut. Le test concurrent complète les tests API SQLite. Aucune base applicative n’a été migrée.

## Todos revus

- TD-B012 : ✅ résolu dans cette tâche.
- TD-B013 : rôles MANAGER/COMMERCIAL encore absents, reste en attente.
- TD-B014 : FK Installation et alimentation métier à réaliser dans INT-103.

Le détail des actions reste dans [docs/todos/backend.md](../../docs/todos/backend.md). INT-98 n’est pas commencé.
