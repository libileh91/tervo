# Déploiement Internet — Tervo (IaaS)

> **Stratégie :** IaaS (Infrastructure as a Service) via le serveur `mini-s1` + Docker + Cloudflare Tunnel.
> **Pas de PaaS** — on garde le contrôle total sur l'infra.

---

## Distinction importante

- **Compte Cloudflare** = le service DNS/Tunnel. Identifiant : `libileh11+cloudflare@gmail.com`
- **Binaire cloudflared** = le logiciel installé sur le serveur pour créer le tunnel. Téléchargé depuis GitHub (comme on télécharge n'importe quel logiciel : `apt install`, `curl`, etc.)
- GitHub c'est juste le téléchargement, pas l'authentification. L'auth se fait via ton email Cloudflare.

---

## Architecture

```
internet
   │
   ├── Cloudflare (DNS + Tunnel)
   │   └── cloudflared tunnel ← relais sécurisé
   │
   ├── Routeur (PAS besoin d'ouvrir les ports — tunnel sortant)
   │
   └── mini-s1 (192.168.10.192)
           ├── cloudflared service (tunnel permanent)
           ├── tervo-frontend-1 (port 3000 → Nginx statique)
           ├── tervo-backend-1 (port 8000 → uvicorn)
           └── postgres (port 5432)
```

**Avantage du tunnel :** pas besoin de toucher au routeur. Le serveur se connecte à Cloudflare (connexion sortante, autorisée partout), Cloudflare redirige les requêtes entrantes via ce tunnel.

---

## DNS Cloudflare

Records actuels (déjà configurés) :

| Name | Type | Content | Proxy |
|------|------|---------|-------|
| `tervoapp.com` | A | `2.57.91.91` | Proxied |
| `www.tervoapp.com` | CNAME | `tervoapp.com` | Proxied |
| `api` | A | `2.57.91.91` | Proxied |

> Le statut **Proxied** (orange) active la protection Cloudflare (cache IP, SSL).
> Le mode **DNS only** (gris) expose directement ton IP.

---

## Cloudflare Tunnel — setup initial (déjà fait)

### Étapes réalisées au premier déploiement

```bash
# 1. Installer cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
chmod +x /tmp/cloudflared
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
cloudflared version  # → 2026.7.1

# 2. S'authentifier
cloudflared tunnel login  # → lien navigateur → compte libileh11+cloudflare@gmail.com

# 3. Créer le tunnel
cloudflared tunnel create tervo  # → crée UUID + cert

# 4. Configurer les routes DNS
cloudflared tunnel route dns tervo tervoapp.com
cloudflared tunnel route dns tervo api.tervoapp.com

# 5. Installer le service permanent
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

---

## Configuration du tunnel

Fichier actuel : `~/.cloudflared/config.yml`

```yaml
tunnel: tervo
credentials-file: /home/lob/.cloudflared/ID_UUID.json

ingress:
  - hostname: api.tervoapp.com
    service: http://localhost:8000
  - hostname: tervoapp.com
    service: http://localhost:3000
  - service: http_status:404
```

### Commandes utiles

```bash
# Statut
sudo systemctl status cloudflared

# Logs en temps réel
sudo journalctl -u cloudflared -f

# Liste des tunnels
cloudflared tunnel list

# Infos
cloudflared tunnel info tervo
```

---

## Accès finaux

| Point d'accès | URL |
|--------------|-----|
| Frontend | `https://tervoapp.com` |
| API | `https://api.tervoapp.com` |
| API (Swagger) | `https://api.tervoapp.com/docs` |
| API (ReDoc) | `https://api.tervoapp.com/redoc` |
| Login test | `tech1 / password123` |

---

## Procédure de déploiement (mise à jour)

> À exécuter sur le serveur via SSH à chaque mise à jour du code.

### 1. SSH sur le serveur

```bash
# Depuis le réseau local (WiFi maison)
ssh lob@192.168.10.192
```

### 2. Aller dans le projet

```bash
cd /home/lob/workspace/python/fastapi/Tervo
```

### 3. Récupérer le code à jour

```bash
git pull
```

> ⚠️ Si tu n'as pas push depuis ton poste local, fais `git push` d'abord sur ta machine.

### 4. Builder le frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Builder les images Docker

```bash
docker build -t tervo-backend:latest -f backend/Dockerfile backend/
docker build -t tervo-frontend:latest -f frontend/Dockerfile frontend/
```

### 6. Redémarrer les conteneurs

```bash
docker compose -f deploy/docker-compose.yml up -d
```

### 7. Seed la base de données (optionnel)

⚠️ **Écrase toutes les données existantes.** À faire uniquement sur dev/demo.

```bash
docker exec tervo-backend-1 python -m app.seed
```

### 8. Redémarrer le tunnel (optionnel)

Le tunnel se met à jour tout seul, mais par sécurité :

```bash
sudo systemctl restart cloudflared
```

### 9. Vérification

```bash
# En local sur le serveur
curl -s -o /dev/null -w "API: HTTP %{http_code}\n" http://localhost:8000/docs
curl -s -o /dev/null -w "Frontend: HTTP %{http_code}\n" http://localhost:3000/

# Depuis l'extérieur (téléphone 4G, autre réseau)
curl -s https://tervoapp.com | head -5
curl -s https://api.tervoapp.com/docs
```

---

## Erreurs fréquentes

| Erreur | Cause | Solution |
|--------|-------|----------|
| `connection refused` | Tunnel pointe vers un port vide | `docker ps` pour vérifier les conteneurs |
| `502 Bad Gateway` | Le service répond mal | `docker logs tervo-backend-1` |
| Page Cloudflare "Domain not found" | DNS pas propagé | `cloudflared tunnel list` |
| `git pull` qui échoue | Conflit de fichiers | `git stash && git pull && git stash pop` |
| `host not found in upstream` | OpenResty ne résout pas les noms Docker | Utiliser l'IP statique du conteneur |
| `port already occupied` | Conteneur + autre service même port | Retirer `ports:` du docker-compose |
| Page Hostinger au lieu de l'app | Pas de port forwarding / tunnel cassé | Vérifier `sudo systemctl status cloudflared` |

---

## Notes d'architecture

- **Nginx frontend** : sert uniquement les fichiers statiques. Pas de proxy API — le tunnel route `/api/` directement vers le backend.
- **Réseau Docker** : `postgres_postgres_network` (externe) + `1panel-network` (si 1Panel est utilisé pour autre chose).
- **Volumes** : `uploads_data` pour les photos des interventions.
