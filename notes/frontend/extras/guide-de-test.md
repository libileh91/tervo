# Guide de test — ResQ

> **Objectif** : Lancer l'application complète (backend + frontend) et tester visuellement
> **Stack** : FastAPI (backend) + Vue.js 3 / Vite (frontend) + Bun

---

## 1. Architecture des serveurs

```
┌─────────────────────────────────────────────────┐
│  Terminal 1 : Backend FastAPI                   │
│  http://localhost:8000                           │
│  http://localhost:8000/docs  (Swagger UI)        │
├─────────────────────────────────────────────────┤
│  Terminal 2 : Frontend Vite                     │
│  http://localhost:5173                           │
│  (proxy /api → http://localhost:8000)            │
└─────────────────────────────────────────────────┘
```

**Le proxy Vite** : en dev, le frontend appelle `/api/v1/...` et Vite redirige automatiquement vers le backend. Pas de CORS à gérer.

---

> 💡 **Guide complet `uv`** (dev, test, deploy) :
> `notes/backend/extras/guide-uv-usage.md`

## 2. Lancer le backend

```bash
cd backend/
uv run uvicorn main:app --reload
```

| Option           | Rôle                                                |
| ---------------- | --------------------------------------------------- |
| `--reload`       | Redémarre automatique à chaque modification de code |
| `--host 0.0.0.0` | Accessible depuis le réseau (optionnel)             |
| `--port 8000`    | Port par défaut                                     |

### Vérifier que le backend tourne

```bash
# Swagger UI (interface graphique pour tester les API)
# → Ouvrir http://localhost:8000/docs dans le navigateur

# Test rapide avec curl
curl -s http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tech1","password":"password123"}'
```

![Swagger UI](https://img.shields.io/badge/Swagger-UI-green)  
Si tu vois la page Swagger avec tous les endpoints (auth, clients), c'est bon.

---

## 3. Lancer le frontend

```bash
cd frontend/
bun dev
```

| Option        | Rôle                        |
| ------------- | --------------------------- |
| `--port 3000` | Changer de port (optionnel) |

### Vérifier que le frontend tourne

```bash
# → Ouvrir http://localhost:5173 dans le navigateur
```

Tu devrais voir l'écran de **connexion** (fond violet dégradé, carte blanche au centre).

---

## 4. Scénario de test complet (pas à pas)

### Étape 1 : Page de connexion

```
Ouvrir http://localhost:5173
→ Redirigé vers /login (car pas de token)
→ Tu vois :
  ┌─────────────────────────┐
  │      ResQ           │
  │  Connexion technicien   │
  │                         │
  │  Identifiant            │
  │  [___________________]  │
  │                         │
  │  Mot de passe           │
  │  [___________________]  │
  │                         │
  │  ┌───────────────────┐  │
  │  │  Se connecter     │  │
  │  └───────────────────┘  │
  └─────────────────────────┘
```

**Screenshot 1** : `notes/frontend/extras/screenshots/login-page.png`

### Étape 2 : Connexion réussie

```
Identifiant : tech1
Mot de passe : password123
Cliquer sur "Se connecter"

→ Redirection vers / (Dashboard)
→ BottomNav visible en bas avec 4 onglets :
  🏠 Accueil  📋 Interventions  👥 Clients  👤 Profil
→ Message : "Bienvenue, Guuleed Liban"
```

**Screenshot 2** : `notes/frontend/extras/screenshots/dashboard.png`

### Étape 3 : Navigation BottomNav

```
Cliquer sur chaque onglet :
✓ Accueil     → /    → Dashboard
✓ Interventions → /jobs → "Page en construction"
✓ Clients     → /clients  → "Page en construction"
✓ Profil      → /profile  → Infos utilisateur + bouton Déconnexion
```

**Screenshot 3** : `notes/frontend/extras/screenshots/bottom-nav.png`

### Étape 4 : Déconnexion

```
Aller sur Profil (👤)
→ Voir les infos : Nom, Identifiant, Email, Rôle
→ Cliquer "Se déconnecter"
→ Token supprimé, redirigé vers /login
```

**Screenshot 4** : `notes/frontend/extras/screenshots/profile.png`

### Étape 5 : Guard de route

```
Après déconnexion, essayer d'accéder à /
→ Redirigé automatiquement vers /login
```

---

## 5. Tests API automatisés

### Lancer les tests Python

```bash
cd backend/
uv run pytest tests/ -v
```

(Quand on aura créé les tests — pour l'instant les tests sont dans le JSON)

### Commande de test rapide (tout-en-un)

```bash
cd backend/
uv run python -c "
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        # Login
        r = await client.post('/api/v1/auth/login', json={'username':'tech1','password':'password123'})
        print(f'✅ Login: {r.status_code}')
        token = r.json()['access_token']

        # GET /me
        r = await client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
        print(f'✅ GET /me: {r.status_code} - {r.json()[\"username\"]}')

        # POST /clients
        r = await client.post('/api/v1/clients', headers={'Authorization': f'Bearer {token}'},
            json={'full_name':'Test','phone':'0102030405','address':'1 rue Test'})
        print(f'✅ POST /clients: {r.status_code} - id={r.json()[\"id\"]}')

        # GET /clients
        r = await client.get('/api/v1/clients', headers={'Authorization': f'Bearer {token}'})
        print(f'✅ GET /clients: {r.status_code} - {r.json()[\"total\"]} clients')

asyncio.run(test())
"
```

---

## 6. Captures d'écran

### Outils

| Outil                                | Pour                                                            |
| ------------------------------------ | --------------------------------------------------------------- |
| **Print Screen** (PrtSc)             | Capture rapide                                                  |
| **DevTools Chrome** (`F12`)          | Mode mobile : `Ctrl+Shift+M` → choisir "iPhone 14" ou "Pixel 7" |
| **Flameshot** / **Gnome Screenshot** | Capture + annotation Linux                                      |

### Mode mobile Chrome DevTools

```
1. Ouvrir http://localhost:5173
2. F12 → DevTools
3. Ctrl+Shift+M → Mode mobile
4. Choisir "iPhone 14" (390×844) ou "Pixel 7" (412×915)
5. Faire les captures
```

### Où stocker les screenshots

```
notes/
├── backend/
│   └── extras/
│       └── screenshots/      ← captures backend (optionnel)
├── frontend/
│   ├── extras/
│   │   └── screenshots/      ← captures frontend ici
│   └── INT-07-frontend-login-nav.md
```

---

## 7. Scénarios de test par cas

### TC-INT-07-01 : LoginPage affichée

```
1. Ouvrir http://localhost:5173
2. Vérifier : formulaire avec champ username, champ password, bouton "Se connecter"
3. Capture d'écran
```

### TC-INT-07-02 : Login succès → Dashboard

```
1. Saisir tech1 / password123
2. Cliquer "Se connecter"
3. Vérifier : redirigé vers /, BottomNav visible
4. Capture d'écran
```

### TC-INT-07-03 : Login échec → message d'erreur

```
1. Saisir tech1 / wrongpassword
2. Cliquer "Se connecter"
3. Vérifier : Toast rouge "Identifiants invalides"
4. Vérifier : reste sur /login
5. Capture d'écran
```

### TC-INT-07-04 : Guard de route

```
1. Déconnexion
2. Naviguer vers http://localhost:5173/
3. Vérifier : redirigé vers /login
```

### TC-INT-07-05 : BottomNav 4 onglets

```
1. Connecté
2. Vérifier : 4 onglets en bas
3. Cliquer chaque onglet → page correspondante
4. Capture d'écran
```

---

## 8. Résolution de problèmes

| Problème                    | Solution                                                                          |
| --------------------------- | --------------------------------------------------------------------------------- |
| `Cannot connect to backend` | Vérifier que uvicorn tourne sur le port 8000                                      |
| `401 Unauthorized`          | Token expiré → se reconnecter                                                     |
| `Module not found`          | `bun install` dans `frontend/`, `uv sync` dans `backend/` (ou `uv add <pkg>`) |
| Port déjà utilisé           | `lsof -i :8000` → `kill -9 <PID>`                                                 |
| Proxy Vite ne marche pas    | Vérifier `vite.config.ts` : target = `http://localhost:8000`                      |
