# INT-50 — Volume persistant uploads + connexion PostgreSQL

> **Objectif :** Configurer les volumes persistants (uploads) et la connexion PostgreSQL pour le déploiement Docker.
> **Date :** 25/06/2026

---

## Problème détecté et corrigé

Lors de l'analyse de cohérence entre INT-49 et INT-50, j'ai trouvé un **décalage de chemin** :

```
Dockerfile:     WORKDIR /app → mkdir -p /app/uploads/photos   ✅
config.py:      UPLOAD_DIR = /app/uploads (calcul automatique) ✅
docker-compose: volume → /backend/uploads                      ❌
```

Le volume était monté sur `/backend/uploads` mais l'application écrit dans `/app/uploads`. Résultat : les photos uploadées n'auraient pas persisté !

**Correction :** `uploads_data:/backend/uploads` → `uploads_data:/app/uploads`

---

## Comment fonctionne la persistance des uploads

```yaml
# deploy/docker-compose.yml
services:
  backend:
    volumes:
      - uploads_data:/app/uploads     # ← volume nommé persistant
    environment:
      - UPLOAD_DIR=/app/uploads      # ← explicite (pydantic-settings)

volumes:
  uploads_data: {}                    # ← volume nommé (pas bind mount)
```

| Concept | Explication |
|---------|-------------|
| **Volume nommé** (`uploads_data:`) | Docker gère le stockage dans `/var/lib/docker/volumes/`. Persiste même après `docker compose down`. |
| **Bind mount** (`./uploads:/app/uploads`) | Monter un dossier du host. Plus fragile (dépend du host). |
| **Volume nommé** > **Bind mount** | Pour la prod : plus portable, pas de permission issues, backup via `docker volume` |

---

## PostgreSQL — config et commandes

### Comment la connexion fonctionne

- **docker-compose** déclare `DATABASE_URL=postgresql://lob:postgres@postgres:5432/tervo_db`
- **pydantic-settings** lit `DATABASE_URL` depuis l'env (override la valeur par défaut SQLite)
3. **database.py** convertit automatiquement : `postgresql://` → `postgresql+asyncpg://`
4. **Alembic** lit `settings.DATABASE_URL` et l'utilise pour les migrations

### Commandes à exécuter sur le serveur (avant le 1er déploiement)

```bash
# 1. Créer la base de données Tervo
docker exec -it postgres psql -U postgres -c "CREATE DATABASE tervo_db;"

# 2. L'utilisateur 'lob' existe déjà dans le container PG (POSTGRES_USER=lob)
#    Il faut juste lui donner les droits sur tervo_db
docker exec -it postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tervo_db TO lob;"

# 3. Vérifier
docker exec -it postgres psql -U postgres -c "\l"
```

> ⚠️ Le mot de passe `postgres` est défini via la variable `${TERVO_DB_PASSWORD:-postgres}` dans docker-compose.

---

## Vérification de la configuration

```bash
# Voir la config résolue du docker-compose
docker compose -f deploy/docker-compose.yml config

# Vérifier le volume
docker compose -f deploy/docker-compose.yml volume ls

# Voir les infos du volume
docker volume inspect deploy_uploads_data
```

---

## Résumé des fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `deploy/docker-compose.yml` | Volume mount : `/backend/uploads` → `/app/uploads` |
| `deploy/docker-compose.yml` | Ajout `UPLOAD_DIR=/app/uploads` dans l'environnement |
| `docs/stages/stage3/sprint-3.1/tasks.md` | Critères INT-50 cochés + commandes PostgreSQL |
| `docs/stages/stage3/sprint-3.1/test-cases.json` | Commandes mises à jour `deploy/` |

---

> **Prochaine tâche :** INT-51 — Seed script : utilisateurs + données demo
