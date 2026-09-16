# Deploiement Internet via Cloudflare Tunnel — Documentation complete

> **Date :** 11/07/2026
> **Objectif :** Rendre Tervo accessible sur internet depuis le serveur `mini-s1` (192.168.10.192) via Cloudflare Tunnel.
> **Domaine :** `tervoapp.com` (registrar Hostinger, DNS Cloudflare)
> **Compte Cloudflare :** `libileh11+cloudflare@gmail.com`

---

## Architecture finale

```
internaute
   │
   └── https://tervoapp.com
        │ DNS Cloudflare → CNAME vers tunnel
        │
        └── Cloudflare Edge
             │ (chiffre SSL, cache, protection)
             │
             └── Cloudflare Tunnel (cloudflared)
                  │ connexion sortante permanente (pas de port forwarding)
                  │
                  └── mini-s1 (192.168.10.192)
                       │
                       ├── cloudflared service (tunnel)
                       │    ├── tervoapp.com → http://localhost:3000 (frontend)
                       │    └── api.tervoapp.com → http://localhost:8000 (backend)
                       │
                       ├── tervo-frontend-1 (Nginx, port 3000 → 80)
                       │    └── sert dist/ statique
                       │
                       ├── tervo-backend-1 (uvicorn, port 8000)
                       │    └── FastAPI
                       │
                       └── postgres (port 5432)
                            └── tervo_db
```

---

## Chronologie des evenements

### 1. Installation de cloudflared

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
chmod +x /tmp/cloudflared
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
cloudflared version  # → 2026.7.1
```

> **Pourquoi GitHub ?** Cloudflare distribue le binaire `cloudflared` via leur depot GitHub. L'authentification se fait separement avec le compte Cloudflare par email.

---

### 2. Authentification Cloudflare

```bash
cloudflared tunnel login
```

→ Ouvre un lien dans le navigateur → connexion avec `libileh11+cloudflare@gmail.com` → selection du domaine `tervoapp.com` → autorisation.

Fichier cree : `~/.cloudflared/cert.pem`

---

### 3. Creation du tunnel

```bash
cloudflared tunnel create tervo
```

Resultat :

```
Tunnel credentials written to /home/lob/.cloudflared/96761bf9-c4ff-46e0-86e1-45a0a4ed54a0.json
Created tunnel tervo with id 96761bf9-c4ff-46e0-86e1-45a0a4ed54a0
```

Le JSON contient les credentials du tunnel (a garder secret).

---

### 4. Configuration DNS

On supprime d'abord les enregistrements A existants dans Cloudflare Dashboard (DNS → Records) :

| Name           | Type      | Action                               |
| -------------- | --------- | ------------------------------------ |
| `tervoapp.com` | A → CNAME | Supprime (remplace par CNAME tunnel) |
| `api`          | A → CNAME | Supprime (remplace par CNAME tunnel) |

```bash
cloudflared tunnel route dns tervo tervoapp.com
cloudflared tunnel route dns tervo api.tervoapp.com
```

Resultat :

```
Added CNAME tervoapp.com which will route to this tunnel
Added CNAME api.tervoapp.com which will route to this tunnel
```

---

### 5. Fichier de configuration du tunnel

```yaml
# /etc/cloudflared/config.yml
tunnel: 96761bf9-c4ff-46e0-86e1-45a0a4ed54a0
credentials-file: /home/lob/.cloudflared/96761bf9-c4ff-46e0-86e1-45a0a4ed54a0.json

ingress:
  - hostname: api.tervoapp.com
    service: http://localhost:8000 # backend FastAPI
  - hostname: tervoapp.com
    service: http://localhost:3000 # frontend Nginx
  - service: http_status:404
```

Le `config.yml` doit etre dans `/etc/cloudflared/` (et non `~/.cloudflared/`) pour le service systemd.

---

### 6. Installation du service systemd

```bash
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
sudo systemctl status cloudflared
```

Verification :

```bash
cloudflared tunnel list
cloudflared tunnel info tervo
```

---

## Erreurs rencontrees et corrections

### Erreur 1 — `port already occupied / site 1Panel bloque le port`

**Symptome :** En creant un site dans 1Panel pour le port 3000, erreur "port already occupied".

**Cause :** Le docker-compose exposait deja le port 3000 sur l'hote (`ports: - "3000:80"`). 1Panel essayait aussi de l'utiliser.

**Solution :** Supprimer le site cree dans 1Panel (Websites → Delete). Le port 3000 reste dedie au container frontend, accessible directement.

---

### Erreur 2 — `502 Bad Gateway` sur tervoapp.com

**Symptome :** Le tunnel repond mais retourne 502.

**Cause :** Le service derriere `localhost:3000` ne repondait pas car le port etait bloque par 1Panel (cf erreur 1).

**Solution :** Supprimer le site 1Panel → down/up le docker-compose → le port 3000 est libre → le tunnel retrouve le frontend.

---

### Erreur 3 — `405 Method Not Allowed` + "Identifiants invalides" au login

**Symptome :** Le frontend s'affiche (`200 OK`) mais le login echoue. La console montre `405` sur `/api/v1/auth/login`.

**Cause :** Le frontend fait des appels API **relatifs** (`/api/v1/auth/login`) qui arrivent au Nginx frontend, pas au backend. Le Nginx est un simple serveur statique — il ne proxy pas `/api/` vers le backend.

---

### Pourquoi ne pas utiliser 1Panel comme reverse proxy ?

On a teste 1Panel (OpenResty) en creant un site Reverse Proxy. Mais OpenResty est en mode reseau `host` — il ne se trouve pas sur le meme reseau Docker que les conteneurs. Impossible de resoudre les noms `tervo-backend-1` ou d'utiliser les IPs internes Docker.

```bash
docker inspect 1Panel-openresty-DXF3 | grep -A5 Networks
# → "Networks": {"host": {}}   ← mode host, pas de DNS Docker
```

**Comparaison des approches :**

| Criteres            | Reverse Proxy 1Panel                                                                 | Proxy Nginx dans Dockerfile                                                                            | Sous-domaines separes (retenu)                                                                  |
| ------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| **Principe**        | OpenResty ecoute sur 80/443, route `/api/` au backend, `/` au frontend               | Nginx frontend contient un bloc `location /api/` qui forwarde au backend                               | Le code JS du frontend appelle directement `api.tervoapp.com` au lieu de `tervoapp.com/api/...` |
| **Reseau**          | OpenResty en mode `host` → pas de DNS Docker → blocage                               | Nginx dans un container Docker peut joindre le backend via `tervo-backend-1:8000` (sur le meme reseau) | Aucun probleme reseau : chaque domaine a son propre tunnel ingress                              |
| **SSL**             | Let's Encrypt automatique via 1Panel                                                 | Let's Encrypt via 1Panel (frontend uniquement)                                                         | Inclus dans Cloudflare Tunnel (SSL automatique)                                                 |
| **Evolution**       | Si un jour on ajoute `/api/v2/*`, il suffit d'ajouter une regle Location dans 1Panel | Il faut modifier le Dockerfile et rebuild l'image                                                      | Si `/api/v2` existe deja, pas de changement : `api.tervoapp.com` couvre tout l'API              |
| **Noms de domaine** | Un seul domaine : `tervoapp.com` (le proxy decide selon le path)                     | Un seul domaine : `tervoapp.com`                                                                       | Deux domaines : `tervoapp.com` + `api.tervoapp.com`                                             |
| **CORS**            | Pas de probleme (meme origine)                                                       | Pas de probleme (meme origine)                                                                         | Cloudflare gere les en-tetes CORS automatiquement                                               |
| **Maintenance**     | Maintenance dans l'UI 1Panel (pas de code)                                           | Maintenance dans le code + rebuild Docker                                                              | Maintenance dans `client.ts` + rebuild frontend                                                 |
| **Performance**     | Un seul point d'entree, mais un hop supplementaire (OpenResty)                       | Direct, mais le Nginx frontend doit aussi gerer du proxy                                               | Direct : chaque domaine va directement au bon service                                           |

**Decision :** Sous-domaines separes (`tervoapp.com` + `api.tervoapp.com`).

C'est le choix le plus propre architecturalement :

- Chaque service a son propre point d'entree
- Pas de configuration proxy a maintenir
- Evolutif : si tu ajoutes `/v2`, rien ne change — l'API est deja sur son propre domaine
- Le tunnel Cloudflare gere SSL automatiquement pour les deux domaines

```javascript
// frontend/src/api/client.ts — solution retenue
const API_BASE =
  window.location.hostname === "tervoapp.com"
    ? "https://api.tervoapp.com/api/v1" // en prod : appelle api.tervoapp.com
    : "/api/v1"; // en dev : proxy Vite
```

**Attention :** Apres modification du code source, il faut :

1. Rebuild le bundle frontend : `cd frontend && bun run build`
2. Rebuild l'image Docker : `docker compose build frontend`
3. Redemarrer le container : `docker compose up -d`

---

### Erreur 4 — Frontend `500 Internal Server Error` apres rebuild Dockerfile

**Symptome :** Apres avoir modifie le Dockerfile, le frontend repond `500`.

**Cause :** J'ai mal ecrit le `$uri` dans la directive Nginx `try_files`.

**Explication detaillee :**

Pour modifier le Dockerfile, j'utilise un outil qui prend du **JSON**. Dans ce JSON, pour ecrire un `$` litteral, il faut l'echapper en `\$` (parce que `$` a un sens special en JSON). Ma commande etait donc :

```json
// Dans ma commande edit_file, j'ai ecrit :
"old_text": "try_files $uri $uri/ /index.html;"
"new_text": "try_files \\$uri \\$uri/ /index.html;"
```

L'outil JSON transforme `\$` → `\$` (un backslash + un dollar) dans le fichier. Le resultat dans le Dockerfile etait :

```dockerfile
RUN echo '... try_files \$uri \$uri/ /index.html; ...'
```

Mais les **single quotes** (`'...'`) dans le shell protegent deja tout, y compris le `$`. Donc le shell transmet `\$uri` litteralement a Nginx — mais Nginx ne comprend pas `\`. Il attend `$uri`. Pas de chance, mon double-echappement etait errone.

**L'erreur en bref :**

```nginx
# Ce que j'ai mis dans le fichier :
try_files \$uri \$uri/ /index.html;   ← Nginx ne comprend pas

# Ce qu'il fallait :
try_files $uri $uri/ /index.html;      ← OK (les single quotes protegent deja le $)
```

**Ce n'etait pas lie a 1Panel.** C'etait uniquement une erreur d'echappement dans ma commande d'edition.

**Lecon :** Dans un `RUN echo '...'` shell, les single quotes protegent deja le `$`. Ne pas ajouter d'echappement supplementaire. Si tu edites le Dockerfile a la main (pas via outil JSON), ecris simplement `$uri` sans backslash.

---

## Procedure de deploiement (resume)

```bash
# 1. Build frontend
cd ~/workspace/python/fastapi/Tervo/frontend && bun run build

# 2. Build images Docker
docker compose -f ../deploy/docker-compose.yml build

# 3. Lancer les containers
docker compose -f ../deploy/docker-compose.yml down
docker compose -f ../deploy/docker-compose.yml up -d

# 4. Creer la base de donnees
docker exec postgres psql -U lob -d postgres -c "CREATE DATABASE tervo_db;"

# 5. Migrations + Seed
docker exec tervo-backend-1 alembic upgrade head
docker exec tervo-backend-1 python -m app.seed

# 6. Verifier
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000    # frontend → 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000    # backend → 404
curl -s -X POST -w "%{http_code}" http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tech1","password":"password123"}'           # → 200

# 7. Verifier le tunnel
curl -s -o /dev/null -w "%{http_code}" https://tervoapp.com        # → 200
curl -s -X POST -w "%{http_code}" https://api.tervoapp.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tech1","password":"password123"}'               # → 200
```

---

## Cloudflare Tunnel — Commandes et usages

### Gestion du tunnel

```bash
# Lister les tunnels existants
cloudflared tunnel list
# Utile pour : voir tous les tunnels actifs/inactifs, retrouver un UUID

# Voir les infos detailles d'un tunnel
cloudflared tunnel info tervo
# Utile pour : verifier les connexions actives (CONNECTOR ID, EDGE), diagnostiquer une panne

# Supprimer un tunnel (irreversible)
cloudflared tunnel delete tervo
# Utile pour : nettoyer un tunnel de test avant d'en creer un nouveau

# Nettoyer les DNS d'un tunnel (avant de supprimer)
cloudflared tunnel cleanup tervo
# Utile pour : supprimer les enregistrements DNS CNAME crees par le tunnel
```

### Gestion du service

```bash
# Etat du service tunnel
sudo systemctl status cloudflared          # → running/stopped/ failed

# Redemarrer le tunnel (apres modification de config.yml)
sudo systemctl restart cloudflared

# Logs en temps reel
sudo journalctl -u cloudflared -f          # Ctrl+C pour quitter
# Utile pour : deboguer les erreurs de connexion, voir les requetes qui arrivent

# Arreter le tunnel (sans le supprimer)
sudo systemctl stop cloudflared

# Desactiver le demarrage automatique
sudo systemctl disable cloudflared
```

### Tests et diagnostic

```bash
# Tester le tunnel en avant-plan (utile pour debug)
cloudflared tunnel run tervo
# → Affiche les logs en temps reel dans le terminal, les erreurs de connexion, etc.

# Tester la resolution DNS
curl -s -o /dev/null -w "%{http_code}" https://tervoapp.com
curl -s -o /dev/null -w "%{http_code}" https://api.tervoapp.com
# 200 = OK, 502 = backend repond pas, 504 = timeout

# Tester l'API via le tunnel
curl -s -X POST https://api.tervoapp.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tech1","password":"password123"}'
# → 200 + tokens si OK, 401 si mauvais mdp, 405 si mauvaise methode

# Tester localement (hors tunnel)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000      # frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000      # backend (404 normal)
```

### Autres usages possibles de cloudflared

| Usage                                 | Commande                                              | Description                                                                                                                                          |
| ------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tunnel rapide sans installation**   | `cloudflared tunnel --url http://localhost:3000`      | Cree un tunnel temporaire (pas de fichier config, pas de service). Utile pour montrer un projet en dev ou faire une demo sans deploiement permanent. |
| **Tunnel vers un service non-Docker** | `ingress → service: http://localhost:3000`            | Le tunnel peut router vers n'importe quel service sur la machine (pas besoin de Docker).                                                             |
| **Charger les logs tunnel**           | `sudo journalctl -u cloudflared --since "1 hour ago"` | Voir les erreurs recentes pour deboguer.                                                                                                             |
| **Mettre a jour cloudflared**         | `cloudflared update`                                  | Met a jour le binaire vers la derniere version automatiquement (mais nous avons desactive les auto-updates dans le service).                         |
| **Multi-tunnels**                     | Creer plusieurs tunnels avec des noms differents      | Utile si tu as plusieurs projets : `tervo`, `resq`, `blog`, etc. Chacun son tunnel, chacun sa config.                                                |

### Cas d'usage concrets

**Scenario 1 : Faire une demo rapide**

```bash
cloudflared tunnel --url http://localhost:3000
```

Cloudflare genere une URL temporaire du type `https://chouette-saison-1234.trycloudflare.com`. Tu peux la partager pour montrer l'app sans configurer de domaine ni de tunnel permanent.

**Scenario 2 : Diagnostiquer une panne tunnel**

```bash
sudo journalctl -u cloudflared --since "10 minutes ago" | grep -i error
```

Recherche les erreurs dans les logs des 10 dernieres minutes. Si aucune erreur, le probleme vient du service backend.

**Scenario 3 : Changer le port du frontend**

```bash
# Modifier config.yml → changer le port dans ingress
# Puis
sudo systemctl restart cloudflared
```

Pas besoin de recreer le tunnel, juste un restart.

---

---

## Acces

| Point d'acces      | URL                          |
| ------------------ | ---------------------------- |
| Frontend           | `https://tervoapp.com`       |
| API                | `https://api.tervoapp.com`   |
| Login test         | `tech1 / password123`        |
| Admin 1Panel local | `http://192.168.10.192:7410` |
| Frontend local     | `http://192.168.10.192:3000` |
| API locale         | `http://192.168.10.192:8000` |

---

## Fichiers modifies

| Fichier                       | Changement                              |
| ----------------------------- | --------------------------------------- |
| `frontend/src/api/client.ts`  | `API_BASE` → `api.tervoapp.com` en prod |
| `frontend/Dockerfile`         | Revert proxy (conflit avec tunnel)      |
| `deploy/docker-compose.yml`   | Port frontend `3000:80` reactive        |
| `/etc/cloudflared/config.yml` | Configuration du tunnel + ingress       |
