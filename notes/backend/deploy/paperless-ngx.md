# Paperless-ngx — Installation Docker Classic sur 1Panel

> **Projet :** MB Chauffage
> **Date :** 13/07/2026
> **Statut :** Documentation d'installation

---

## Pourquoi Paperless-ngx ?

Paperless-ngx est un système de gestion documentaire open source qui va :

- **OCRiser** tous les PDFs/scans/photos de documents (reconnaissance de texte)
- **Classifier** automatiquement (par correspondant, type, date)
- **Indexer** pour recherche full-text
- **Stocker** de façon organisée dans l'arborescence

Pour MB Chauffage : archivage des devis, factures, rapports PDF, photos d'intervention, scans de documents fournisseurs — tout ce qui était dans les classeurs papiers ou les dossiers Windows.

---

## Prérequis

| Ressource | Minimum | Recommandé |
|-----------|:-------:|:----------:|
| RAM | 2 Go | 4 Go (OCR) |
| Stockage | 10 Go | 50 Go (documents) |
| Docker | ✅ | Compose |
| 1Panel | ✅ | reverse proxy |

---

## Procédure d'installation

> Paperless-ngx n'est **pas disponible** dans l'App Store 1Panel. On l'installe en Docker Classic via `docker-compose.yml`, exactement comme on a fait pour Tervo.

### Étape 1 — Créer les répertoires

```bash
# Sur le VPS
sudo mkdir -p /opt/paperless/{data,media,export,consume,db,redis}
sudo chmod -R 755 /opt/paperless
```

### Étape 2 — docker-compose.yml

Créer `/opt/paperless/docker-compose.yml` :

```yaml
version: "3.8"

services:
  broker:
    image: redis:7
    container_name: paperless-broker
    volumes:
      - /opt/paperless/redis:/data
    restart: unless-stopped

  db:
    image: postgres:17
    container_name: paperless-db
    environment:
      POSTGRES_DB: paperless
      POSTGRES_USER: paperless
      POSTGRES_PASSWORD: ${PAPERLESS_DB_PASSWORD}
    volumes:
      - /opt/paperless/db:/var/lib/postgresql/data
    restart: unless-stopped

  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    container_name: paperless-ngx
    depends_on:
      - db
      - broker
    ports:
      - "8000:8000"
    volumes:
      - /opt/paperless/data:/usr/src/paperless/data
      - /opt/paperless/media:/usr/src/paperless/media
      - /opt/paperless/export:/usr/src/paperless/export
      - /opt/paperless/consume:/usr/src/paperless/consume
    environment:
      PAPERLESS_DBUSER: paperless
      PAPERLESS_DBPASS: ${PAPERLESS_DB_PASSWORD}
      PAPERLESS_DBHOST: db
      PAPERLESS_DBPORT: "5432"
      PAPERLESS_DBNAME: paperless
      PAPERLESS_REDIS: redis://broker:6379
      PAPERLESS_SECRET_KEY: ${PAPERLESS_SECRET_KEY}
      PAPERLESS_URL: https://docs.mbchauffage.com
      PAPERLESS_TIME_ZONE: Europe/Paris
      PAPERLESS_OCR_LANGUAGE: fra
      PAPERLESS_CONSUMER_POLLING: "60"
    restart: unless-stopped
```

### Étape 3 — Fichier `.env`

Créer `/opt/paperless/.env` :

```bash
PAPERLESS_DB_PASSWORD=CHANGE_ME_complex_password
PAPERLESS_SECRET_KEY=CHANGE_ME_complex_secret_key
```

> **Ne jamais commiter ce fichier.** Il contient les mots de passe en clair.

### Étape 4 — Lancer les conteneurs

```bash
cd /opt/paperless
docker compose up -d

# Vérifier que les 3 conteneurs tournent
docker ps
# paperless-broker   (redis)
# paperless-db       (postgres)
# paperless-ngx      (webserver)

# Voir les logs du premier démarrage (création du superuser)
docker logs -f paperless-ngx
```

À la fin des logs, le superuser est créé automatiquement :

```
Superuser created: plngxadmin / plngxPassWD25680
```

### Étape 5 — Configurer le reverse proxy 1Panel

```
1Panel → Websites → Create Website → Reverse Proxy

Domain: docs.mbchauffage.com
Proxy Address: http://localhost:8000
HTTPS → Let's Encrypt → Enable (one-click)
```

### Étape 6 — Vérification

```bash
# En local
curl http://localhost:8000
# → réponse Paperless-ngx (API)

# Depuis l'extérieur
curl https://docs.mbchauffage.com
# → page de login Paperless-ngx
```

---

## Intégration avec l'application MB Chauffage

### Sauvegarde automatique des rapports PDF

```python
# services/paperless_service.py (futur)
import requests

class PaperlessService:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Token {api_token}"}

    def upload_document(self, file_path: str, title: str,
                        correspondent_id: int | None = None,
                        document_type: int | None = None) -> dict:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {
                "title": title,
                "correspondent": correspondent_id,
                "document_type": document_type,
            }
            resp = requests.post(
                f"{self.base_url}/api/documents/post_document/",
                headers=self.headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()
            return resp.json()
```

### Backup Paperless via 1Panel Cron

```
1Panel → Cron Jobs → créer :

Nom : "paperless-backup"
Commande :
  docker exec paperless-db pg_dump -U paperless paperless | gzip > /opt/paperless/backup/paperless_$(date +\%Y\%m\%d).sql.gz
  tar czf /opt/paperless/backup/paperless-media_$(date +\%Y\%m\%d).tar.gz -C /opt/paperless media
  s3cmd sync /opt/paperless/backup/ s3://mbchauffage-backups/paperless/
Fréquence : 0 4 * * * (4h00 quotidien)
```

---

## Accès

| Point d'accès | URL |
|---------------|-----|
| Interface Web | `https://docs.mbchauffage.com` |
| Login | `plngxadmin` / `plngxPassWD25680` |
| API | `https://docs.mbchauffage.com/api/` |
| Consume folder | `/opt/paperless/consume/` (drop files → auto-import) |

---

## Mise à jour

```bash
cd /opt/paperless
docker compose pull
docker compose up -d
```

---

## Structure des dossiers

```
/opt/paperless/
├── docker-compose.yml
├── .env
├── data/          ← données Paperless (index, thumbs)
├── media/         ← documents stockés (organisés par Paperless)
├── export/        ← export manuel
├── consume/       ← drop folder (déposer un PDF → auto-importé)
├── db/            ← volume PostgreSQL
├── redis/         ← volume Redis
└── backup/        ← backups locaux avant sync S3
```

---

> **Document lié :** `docs/DAT/MBchauffage-DAT/04-architecture.md`
