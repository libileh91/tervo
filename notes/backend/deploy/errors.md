# Registre des erreurs de déploiement — Tervo

> Historique des erreurs rencontrées en production/dev, avec causes et corrections.

---

## 1. 502 Bad Gateway — `host not found in upstream "tervo-backend-1"` (17/08/2026)

**Cause :** Un `proxy_pass http://tervo-backend-1:8000` a été ajouté par erreur dans le `frontend/Dockerfile`. Nginx tente de résoudre le nom du conteneur au démarrage → échec → `[emerg]` → crash en boucle (`Restarting (1)`) → rien sur le port 3000 → 502.

**Fix :** Retour au Nginx statique pur dans le Dockerfile. Le routage API est géré par le tunnel Cloudflare (prod) ou le proxy Vite (dev).

**Doc complète :** `notes/backend/deploy/incident-502-nginx-upstream.md`

---

## 2. `invalid input value for enum jobstatus: "planifié"` (seed PostgreSQL)

**Cause :** L'enum PostgreSQL `jobstatus` contient des valeurs sans accents (`planifie`) alors que le code Python utilise `planifié` avec accents. La migration a créé l'enum avec les valeurs par défaut Python.

**Fix :** Modifier l'enum PostgreSQL pour accepter les valeurs accentuées. Voir `notes/backend/sprint-3.1/fix-postgresql-enum.md`.

```
asyncpg.exceptions.InvalidTextRepresentationError:
invalid input value for enum jobstatus: "planifié"
```

---

## 3. `PUT /jobs/{id}/start` → 500 Internal Server Error

**Cause :** `datetime.now(timezone.utc)` (datetime aware) inséré dans une colonne `TIMESTAMP` sans timezone → PostgreSQL rejette.

**Fix :** Utiliser `datetime.utcnow()` (naive) dans `backend/app/services/job.py`.

**Doc complète :** `notes/backend/deploy/fix-timezone-aware-datetime-500.md`

---

## 4. Login → `POST /api/v1/auth/login 405 (Not Allowed)`

**Cause :** Frontend buildé servi par Nginx sur le port 3000, avec `client.ts` qui utilise `/api/v1` relatif (hostname ≠ tervoapp.com). Nginx ne proxy pas → 405.

**Fix :** En dev local, utiliser `bun run dev` (proxy Vite vers `localhost:8000`). En prod, le hostname est `tervoapp.com` → le client appelle `https://api.tervoapp.com/api/v1` via le tunnel.

---

## 5. Seed local → `no such table: review`

**Cause :** Le seed exécutait `DELETE FROM review` avant que les tables ne soient créées (base SQLite vierge).

**Fix :** Ajout de `Base.metadata.create_all()` au début du seed (`backend/app/seed.py`).
