# Registre des erreurs de déploiement — Tervo

> Historique de l'ancien modèle `jobs` et du mini-s1, avec causes et corrections.
> Ne pas transposer les correctifs au VPS ou au modèle V2 sans relire le code.
> Incident actuel de permissions SQL et reprise : [journal INT-111](../sprint7.6/INT-111-deploiement-vps.md).

---

## 1. 502 Bad Gateway — `host not found in upstream "tervo-backend-1"` (17/08/2026)

**Cause :** Un `proxy_pass http://tervo-backend-1:8000` a été ajouté par erreur dans le `frontend/Dockerfile`. Nginx tente de résoudre le nom du conteneur au démarrage → échec → `[emerg]` → crash en boucle (`Restarting (1)`) → rien sur le port 3000 → 502.

**Fix historique :** Retour au Nginx statique pur dans le Dockerfile. Le routage
API était géré par le tunnel Cloudflare (mini-s1) ou le proxy Vite (dev).
Le VPS actuel utilise Caddy.

**Doc complète :** [Incident 502](incident-502-nginx-upstream.md).

---

## 2. `invalid input value for enum jobstatus: "planifié"` (seed PostgreSQL)

**Cause :** L'enum PostgreSQL `jobstatus` contient des valeurs sans accents (`planifie`) alors que le code Python utilise `planifié` avec accents. La migration a créé l'enum avec les valeurs par défaut Python.

**Fix historique :** Modifier l'enum PostgreSQL pour accepter les valeurs
accentuées. La note anciennement située dans
`notes/backend/sprint-3.1/fix-postgresql-enum.md` n'est plus présente dans
l'arborescence ; consulter l'historique Git si nécessaire. Ce n'est pas une
migration à appliquer au modèle V2.

```
asyncpg.exceptions.InvalidTextRepresentationError:
invalid input value for enum jobstatus: "planifié"
```

---

## 3. `PUT /jobs/{id}/start` → 500 Internal Server Error

**Cause :** `datetime.now(timezone.utc)` (datetime aware) inséré dans une colonne `TIMESTAMP` sans timezone → PostgreSQL rejette.

**Fix de l'époque :** Utiliser `datetime.utcnow()` (naive) dans l'ancien
`backend/app/services/job.py`. Ce contournement d'une colonne sans timezone
n'est pas une recommandation générale pour les nouveaux modèles.

**Doc complète :** [Incident datetime](fix-timezone-aware-datetime-500.md).

---

## 4. Login → `POST /api/v1/auth/login 405 (Not Allowed)`

**Cause :** Frontend buildé servi par Nginx sur le port 3000, avec `client.ts` qui utilise `/api/v1` relatif (hostname ≠ tervoapp.com). Nginx ne proxy pas → 405.

**Fix historique :** En dev local, utiliser `bun run dev` (proxy Vite vers
`localhost:8000`). Le build mini-s1 appelait l'API via le tunnel. Désormais,
`VITE_API_BASE_URL` est fourni explicitement au build de l'image frontend :
ne pas réintroduire une détection du hostname pour corriger un 405.

---

## 5. Seed local → `no such table: review`

**Cause :** Le seed exécutait `DELETE FROM review` avant que les tables ne soient créées (base SQLite vierge).

**Fix :** Ajout de `Base.metadata.create_all()` au début du seed (`backend/app/seed.py`).
