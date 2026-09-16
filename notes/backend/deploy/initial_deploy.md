### Étape 1 — Le projet est-il sur le serveur ?

Vérifions d'abord que tout est prêt avant de toucher 1Panel :

**Dans ton terminal (SSH ou local) :**

```bash
# 1. Les fichiers de déploiement existent ?
ls ~/workspace/python/fastapi/Tervo/deploy/docker-compose.yml ~/workspace/python/fastapi/Tervo/backend/Dockerfile ~/workspace/python/fastapi/Tervo/frontend/Dockerfile
```

```bash
# 2. Le container PostgreSQL tourne bien ?
docker ps | grep postgres
```

```bash
# 3. Le réseau postgres_network existe ?
docker network ls | grep postgres
```

Exécute ces 3 commandes et donne-moi le résultat.

---

### Étape 2 — Créer la base de données Tervo

Le container PostgreSQL tourne bien. Maintenant on crée `tervo_db` dedans. Exécute **une par une** :

the postgres superuser role doesn't exist in your PostgreSQL instance. Instead, the user is lob (based on your previous commands). Instead I used lob user

**1. Create DB**

```zsh
docker exec -it postgres psql -U lob -d postgres -c "CREATE DATABASE tervo_db;"              ─╯
CREATE DATABASE
```

**2. Vérifier les droits (lob est déjà owner puisqu'il a créé la DB)**

```bash
    docker exec -it postgres psql -U lob -d tervo_db -c "\dt"        ─╯
    Did not find any relations. ## it exist
```

**3. Vérifier que la base existe bien**

```bash
    docker exec -it postgres psql -U lob -d postgres -c "\l" | grep tervo        ─╯
    tervo_db | lob | UTF8 | libc | en_US.utf8 | en_US.utf8 | |
```

---

### NB: If lob did not exist use this command

```bash
# Créer la base de données
docker exec -it postgres psql -U postgres -c "CREATE DATABASE tervo_db;"
```

```bash
# Donner les droits à l'utilisateur 'lob' (qui existe déjà dans le container)
docker exec -it postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tervo_db TO lob;"
```

```bash
# Vérifier
docker exec -it postgres psql -U postgres -c "\l" | grep tervo
```

---

### Étape 3 — Build des images Docker

On va builder les deux images (backend et frontend). Exécute **une par une** :
**1. Build Backend & Frontend**

```bash
# 1. Build backend
cd ~/workspace/python/fastapi/Tervo && docker build -t tervo-backend:latest -f backend/Dockerfile backend/    ─╯
```

```bash
cd ~/workspace/python/fastapi/Tervo && docker build -t tervo-frontend:latest -f frontend/Dockerfile frontend/     ─╯
```

```bash
 docker images | grep tervo                                                                                 ─╯
 tervo-backend:latest    804bcc890f12        260MB             0B
 tervo-backend:test      a4d0f8fd609a        260MB             0B
 tervo-frontend:latest   e6f6b54c3024       64.1MB             0B
 tervo-frontend:test     5829ca28f34e       63.9MB             0B
```

---

### Étape 4 — Déploiement via 1Panel UI

Maintenant on bascule sur l'interface 1Panel. Ouvre `http://192.168.10.192:7410` et connecte-toi.

Une fois connecté, suis ces étapes :

**1. Va dans `Containers` → `Compose`**

**2. Clique `Create Compose`**

**3. Remplis :**

**NB: 1Panel compose ne permet pas de definir le nom du compose: ça doit être setter dans le docker-compose avec la balise _name_**

- **Name :** `tervo`
- **File :** colle le chemin du docker-compose

```
~/workspace/python/fastapi/Tervo/deploy/docker-compose.yml
```

**4. Avant de lancer, on doit ajouter les variables d'environnement :**

Dans l'onglet `Env`, ajoute :

```zsh
TERVO_DB_NAME=tervo_db
TERVO_DB_USER=lob
TERVO_DB_PASSWORD=postgres
SECRET_KEY=change-me-in-production
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

> ⚠️ Le port 80 est souvent déjà utilisé — on met le frontend sur 8080.

**5. Clique `Save` puis `Up`**

Tu me dis ce que tu vois dans l'UI 1Panel à chaque étape.

---

### Étape 5 — Migrations + Seed

Maintenant on initialise la base de données. Exécute :

**#### 1. Lancer les migrations (crée les tables)**

```bash
docker exec -it tervo-backend-1 alembic upgrade head
```
**result**:
  import_dbapi
      import psycopg2
  ModuleNotFoundError: No module named 'psycopg2'
#### **Fix**
  Il manque le driver PostgreSQL **sync** pour Alembic (psycopg2). On a que l'async (asyncpg). J'ajoute :
  
  ```toml
  # Database
  "sqlalchemy>=2.0.0",
  "alembic>=1.13.0",
  "aiosqlite>=0.20.0",
  "asyncpg>=0.29.0",  # PostgreSQL async driver (prod)
  "psycopg2-binary>=2.9.0",  # adding PostgreSQL sync driver (Alembic migrations)
  ```
  Then lock the pyprpoject.toml
  
  ```zsh
  cd backend && uv lock 2>&1 && echo "✅ lock OK"
    pyenv: shell integration not enabled. Run `pyenv init' for instructions.
    Resolved 66 packages in 957ms
    Added psycopg2-binary v2.9.12
    ✅ lock OK
  ```

  Maintenant rebuild l'image et relance le compose. Sur le serveur :
  ```zsh
  # 1. Rebuild avec psycopg2
  cd ~/workspace/python/fastapi/Tervo && docker build -t tervo-backend:latest -f backend/Dockerfile backend/
  ```


**#### 2. Seed les données de démo**  
```bash
docker exec -it tervo-backend-1 python -m app.seed
```

  **result:**
    raise translated_error from error
    sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.PostgresSyntaxError'>: syntax error at or near "user"
    [SQL: DELETE FROM user]
    (Background on this error at: https://sqlalche.me/e/20/f405)
  
  **Fix**:
  user` est un mot réservé PostgreSQL. Les guillemets sont nécessaires. Je corrige le seed :
  ```python
   # ── 1. Nettoyage (ordre inverse des dépendances) ──────
        print("🧹 Cleaning existing data…")
        for table in [
            "review",
            "material",
            "job_photo",
            "checklist_item",
            "job",
            "client",
           "error:user", '"user"',  # quoted: reserved keyword in PostgreSQL
        ]:
  ```
  Rebuild + relancer :
  
  ```bash
  # 1. Rebuild (le fix seed)
  cd ~/workspace/python/fastapi/Tervo && docker build -t tervo-backend:latest -f backend/Dockerfile backend/
  ```
  
  ```bash
  # 2. 1Panel → Compose → tervo → Down → Up
  ```

**#### 3. Seed**
```bash
docker exec -it tervo-backend-1 python -m app.seed
```
