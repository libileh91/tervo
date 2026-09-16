# Architecture Reseau — Pourquoi 1Panel/Traefik ne sont pas utilises

> **Date :** 11/07/2026
> **Contexte :** Apres le deploiement internet via Cloudflare Tunnel, on re-evalue le besoin de 1Panel et Traefik.
> **Projet :** Tervo (mini-s1, Docker Compose, Cloudflare Tunnel)

---

## Rappel : ce que fait Cloudflare Tunnel

```
internaute → Cloudflare Edge (SSL, cache) → Tunnel → localhost:3000/8000
```

Le tunnel remplit **deja** les 3 fonctions essentielles qu'auraient du assurer 1Panel et Traefik :

| Fonction | Sans tunnel (avec Traefik/1Panel) | Avec Cloudflare Tunnel |
|----------|-----------------------------------|----------------------|
| **Reverse proxy** | Un point d'entree unique qui route vers differents services selon le chemin (`/api/` → backend, `/` → frontend) | **Plus besoin** : chaque service a son propre sous-domaine (`tervoapp.com` → frontend, `api.tervoapp.com` → backend). Le routage est fait au niveau DNS, pas au niveau proxy. |
| **SSL** | Let's Encrypt via Traefik ou 1Panel (ACME, challenge HTTP-01) | **Automatique** : Cloudflare signe tout le trafic entre l'internaute et son Edge. Pas de certificat a generer, renouveler, ou stocker. |
| **Ingress** | Redirection `/api/v2/*` vers un nouveau service | **Ajout en 30s** : nouveau sous-domaine → nouveau tunnel ingress → `sudo systemctl restart cloudflared` |

---

## Pourquoi 1Panel n'est pas necessaire

1Panel a ete installe initialement pour gerer les conteneurs et faire office de reverse proxy via OpenResty. Mais dans la pratique :

### 1Panel comme reverse proxy

**Probleme :** OpenResty est en mode reseau `host`. Il ne peut pas resoudre les noms des conteneurs Docker (`tervo-frontend-1`). Les IPs internes des conteneurs changent au redemarrage.

```bash
docker inspect 1Panel-openresty-DXF3 | grep -A5 Networks
# → \"Networks\": {\"host\": {}}           ← pas de DNS Docker
```

**Donc pour utiliser 1Panel comme proxy, il faudrait :**
1. A chaque `docker compose up`, recuperer l'IP du conteneur
2. Aller dans 1Panel → Websites → modifier le ProxyAddress
3. Verifier que le port n'est pas deja utilise par le container

**Alternative (retenue) :** Sous-domaines via Cloudflare Tunnel. Meme pas de proxy, pas de port a gerer, pas de maintenance.

### 1Panel pour le build Docker

Le build se fait en CLI : `docker compose build`. C'est une ligne de commande. L'UI 1Panel ajoute de la friction (copier le docker-compose.yml, naviguer dans l'interface).

### 1Panel pour la DB

Le container PostgreSQL etait deja la avant 1Panel. La gestion se fait via `psql` en ligne de commande.

### Ce que 1Panel fait encore de bien

| Usage | Note | Commentaire |
|-------|------|-------------|
| Monitoring visuel | ⚠️ Confort | Voir les logs et ressources des containers d'un coup d'oeil |
| File manager | ⚠️ Confort | Naviguer dans les fichiers du serveur depuis le navigateur |
| Backups | ❌ Pas utilise | Pourrait etre configure, mais pas necessaire aujourd'hui |

**→ 1Panel reste installe, mais n'est pas un composant cle de l'infrastructure.**

---

## Pourquoi Traefik n'est pas necessaire

Le DAT original prevoyait Traefik pour :

```
Traefik (port 80/443)
  ├── / → frontend (port 3000)
  ├── /api/ → backend (port 8000)
  └── Let's Encrypt (SSL)
```

### Traefik vs Cloudflare Tunnel

| Criteres | Traefik | Cloudflare Tunnel |
|----------|---------|-------------------|
| **Configuration** | Fichier `traefik.yml` + labels Docker | Fichier `config.yml` avec ingress |
| **SSL** | Let's Encrypt challenge HTTP | Automatique (SSL Edge) |
| **Exposition** | Ouvre les ports 80/443 sur le reseau local | Connexion sortante uniquement (pas de port ouvert) |
| **Resolution noms** | DNS Docker (peut joindre les containers par leur nom) | `localhost` uniquement (les containers doivent exposer leurs ports sur l'hote) |
| **Evolution** | Ajouter un label `traefik.http.routers.pay.rule=Host(\`pay.tervoapp.com\`)` | Ajouter un bloc `- hostname: pay.tervoapp.com` dans config.yml + restart |
| **Securite** | Exposition IP du serveur | IP masquee derriere Cloudflare |

### Cas concret : ajouter Tervo Pay

Avec Traefik :

1. Creer le conteneur `tervo-pay-1` avec label `traefik.http.routers.pay.rule=Host(\`pay.tervoapp.com\`)`
2. `docker compose up -d tervo-pay`
3. Traefik detecte automatiquement le nouveau label et route le trafic

Avec Cloudflare Tunnel (sans Traefik) :

1. Ajouter dans `config.yml` :
   ```yaml
   - hostname: pay.tervoapp.com
     service: http://localhost:5000
   ```
2. `sudo systemctl restart cloudflared`
3. Ajouter le record DNS `CNAME pay → tunnel` dans Cloudflare

**Difference :** Avec Traefik, tu ne touches pas au fichier de config — le label Docker suffit. C'est plus "automatique". Mais avec le tunnel, tu as une ligne de configuration explicite, ce qui est plus transparent.

---

## Architecture finale retenue

```
internaute
   │
   └── https://*.tervoapp.com
        │ (SSL automatique Cloudflare)
        │
        └── Cloudflare Edge (cache, protection DDoS)
             │
             └── Cloudflare Tunnel (cloudflared)
                  │ (connexion sortante permanente)
                  │
                  └── mini-s1
                       │
                       ├── tervo-frontend-1 (Nginx, port 3000)
                       │    └── sert dist/ statique
                       │
                       ├── tervo-backend-1 (uvicorn, port 8000)
                       │    └── FastAPI
                       │
                       ├── postgres (port 5432)
                       │
                       └── [futur] tervo-pay-1 (port 5000)
                       └── [futur] tervo-iq-1 (port 5100)
```

**Stack minimale :**

| Composant | Role |
|-----------|------|
| Docker Compose | Orchestration des conteneurs |
| Cloudflare Tunnel | Exposition internet + SSL |
| Cloudflare DNS | Routage des sous-domaines vers le tunnel |
| PostgreSQL (container) | Base de donnees |

**Absents :** Traefik, 1Panel (reverse proxy), Nginx (proxy), Let's Encrypt.

---

## Quand reviendraient-ils ?

| Scenario | Solution |
|----------|----------|
| Ajout d'un sous-domaine | `config.yml` + `cloudflared restart` — 30s |
| Ajout d'un container | `docker compose up -d` — 5s |
| Nouveau service avec son propre domaine | `cloudflared tunnel route dns` — 10s |
| Multi-serveurs | Swarm (pas Traefik/1Panel) |
| Env de staging separe | Un deuxieme tunnel Cloudflare — 2 min |

→ **Ni 1Panel ni Traefik ne reapparaitraient** dans la stack, meme en croissance.
