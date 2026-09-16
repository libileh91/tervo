# Incident : 502 Bad Gateway — `host not found in upstream "tervo-backend-1"`

> **Date :** 17/08/2026
> **Environnement :** Production (`tervoapp.com`)
> **Gravité :** Critique — site inaccessible (502 sur `tervoapp.com` et `api.tervoapp.com`)

---

## 1. Symptômes

- `https://tervoapp.com` → **502 Bad Gateway**
- `https://api.tervoapp.com` → **502 Bad Gateway**
- `docker ps` → `tervo-frontend-1` en état `Restarting (1)` (crash en boucle)
- `sudo docker logs tervo-frontend-1` →

```
[emerg] 1#1: host not found in upstream "tervo-backend-1" in /etc/nginx/conf.d/default.conf:1
nginx: [emerg] host not found in upstream "tervo-backend-1"
```

---

## 2. Cause racine

### Le frontend Nginx référençait un conteneur backend inexistant

Un fix précédent avait ajouté un **proxy API** dans la config Nginx du frontend :

```nginx
# ❌ MAUVAIS — ajouté par erreur dans frontend/Dockerfile
location /api/ {
    proxy_pass http://tervo-backend-1:8000;   # ← ce conteneur n'existe pas
}
```

**Pourquoi ça crash :** Nginx, au démarrage, tente de **résoudre le nom** `tervo-backend-1` pour configurer l'upstream. Si ce nom n'existe pas dans le réseau Docker au moment du démarrage → `[emerg]` → Nginx refuse de démarrer → conteneur en `Restarting (1)` en boucle → rien ne répond sur le port 3000 → **502**.

### Pourquoi le backend n'existait pas

Le conteneur `tervo-backend-1` n'était pas (ou plus) dans le réseau Docker du frontend au moment du démarrage. Résultat : la résolution de nom échoue.

---

## 3. Pourquoi ce proxy Nginx était inutile (et dangereux)

**En production, le routage API est déjà géré par le tunnel Cloudflare :**

```
internet → Cloudflare → tunnel cloudflared → localhost:3000 (frontend)
                                      └─────→ localhost:8000 (backend)
```

Le `client.ts` du frontend bascule automatiquement selon le hostname :

```typescript
const API_BASE = window.location.hostname === "tervoapp.com"
  ? "https://api.tervoapp.com/api/v1"   // ← prod : appel direct au backend via Cloudflare
  : "/api/v1";                           // ← dev : relatif (proxy Vite)
```

Donc en prod :
- `tervoapp.com` → Nginx sert le static → le JS appelle `https://api.tervoapp.com/api/v1`
- `api.tervoapp.com` → tunnel → backend sur `localhost:8000`

**Aucun proxy Nginx nécessaire.** Le frontend Docker doit rester **100% statique**.

---

## 4. Correction appliquée

### `frontend/Dockerfile` — retour au Nginx statique pur

```dockerfile
# ✅ BON — config Nginx statique pure
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf
```

### Redéploiement

```bash
# 1. Builder le frontend
cd frontend && npm run build && cd ..

# 2. Rebuild l'image
docker build -t tervo-frontend:latest -f frontend/Dockerfile frontend/

# 3. Relancer les conteneurs (recrée le backend s'il manque)
docker compose -f deploy/docker-compose.yml up -d
```

### Vérification

```bash
docker ps
# → tervo-backend-1  Up (healthy)
# → tervo-frontend-1 Up

curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/      # → 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs  # → 200

curl -s -o /dev/null -w "%{http_code}" https://tervoapp.com        # → 200
curl -s -o /dev/null -w "%{http_code}" https://api.tervoapp.com/docs  # → 200
```

---

## 5. Diagnostic rapide (checklist)

Quand `tervoapp.com` donne 502 :

```bash
# 1. Les conteneurs tournent-ils ?
docker ps

# 2. Le frontend crash-t-il ? → regarder les logs
docker logs tervo-frontend-1 --tail 20
# → Si "host not found in upstream" → le proxy Nginx référence un conteneur absent

# 3. Rien n'écoute sur le port ? → les conteneurs sont down
sudo ss -tlnp | grep -E ":(3000|8000)"

# 4. Test local
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
```

---

## 6. Règle d'or pour ce projet

| Environnement | Comment le frontend accède à l'API |
|---------------|-----------------------------------|
| **Prod** (`tervoapp.com`) | `https://api.tervoapp.com/api/v1` (via tunnel Cloudflare) — Nginx statique pur |
| **Dev local** | `bun run dev` → proxy Vite `/api` → `localhost:8000` |
| **Docker local** | Nginx statique + tunnel — pas de proxy dans le conteneur |

> ⚠️ **NE JAMAIS ajouter de `proxy_pass` vers un conteneur Docker dans le `frontend/Dockerfile`.** Le nom du conteneur peut ne pas être résolvable au démarrage → crash en boucle → 502. Le routage API est la responsabilité du tunnel Cloudflare (prod) ou du proxy Vite (dev).
