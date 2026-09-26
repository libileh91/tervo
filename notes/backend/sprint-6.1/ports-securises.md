# INT-66 — Sécuriser les ports Docker (bind `127.0.0.1`)

> **Stage 6 / Sprint 6.1** | Points : 3 | Statut : ✅
> **Référence :** `docs/DAT/annexes/revue-architecture.md` §2 et §3

---

## Le problème

Dans un `docker-compose.yml`, écrire :

```yaml
ports:
  - "8000:8000"
```

publie le port sur **toutes les interfaces réseau** de l'hôte, c'est-à-dire `0.0.0.0:8000`.

`0.0.0.0` = « toutes les IP de la machine », donc **aussi l'IP publique**.

```
Internet ──► 0.0.0.0:8000 ──► conteneur backend
```

→ N'importe qui sur Internet peut atteindre le backend directement, **en contournant le reverse proxy** (donc sans HTTPS, sans filtrage).

---

## La correction

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

On ajoute l'**IP d'écoute** (`host_ip`) en préfixe. Ici `127.0.0.1` = la **loopback**, uniquement accessible depuis la machine elle-même.

```
Internet ──► 1Panel (443) ──► 127.0.0.1:8000 ──► conteneur backend
                                    ▲
                        seul l'hôte peut joindre ce port
```

### Anatomie d'une ligne `ports:`

```
  "127.0.0.1:8000:8000"
   └───┬───┘ └─┬─┘ └─┬─┘
     host_ip  host  conteneur
     (où on    port   port
      écoute)         interne
```

| Forme | Signification |
|-------|---------------|
| `"8000:8000"` | `0.0.0.0:8000` → exposé publiquement ⚠️ |
| `"127.0.0.1:8000:8000"` | loopback uniquement → sûr ✅ |
| `"8000"` | port aléatoire sur l'hôte (non déterministe) |
| *(aucun `ports:`)* | pas de publication → accessible seulement dans le réseau Docker |

---

## Ce qui a été modifié

| Fichier | Avant | Après |
|---------|-------|-------|
| `deploy/docker-compose.yml` (backend) | `${BACKEND_PORT:-8000}:8000` | `127.0.0.1:${BACKEND_PORT:-8000}:8000` |
| `deploy/docker-compose.yml` (frontend) | `${FRONTEND_PORT:-3000}:80` | `127.0.0.1:${FRONTEND_PORT:-3000}:80` |
| `deploy/postgres.docker-compose.yml` | `"5432:5432"` | *(supprimé)* |

### Pourquoi PostgreSQL n'a plus aucun port

PostgreSQL n'est utilisé que par le backend, via le **réseau Docker interne** (`postgres:5432` — résolution par nom de service). Il n'a donc **jamais besoin** d'un port sur l'hôte.

Accès admin ponctuel :

```bash
docker exec -it postgres psql -U lob -d tervo_db
```

> ⚠️ Publier `5432:5432` sur une machine avec IP publique = base de données ouverte à Internet. C'est l'une des erreurs les plus exploitées (scans automatiques sur le port 5432).

---

## Vérification

```bash
# Voir les ports réellement publiés et leur host_ip
docker compose -f deploy/docker-compose.yml config | grep -A4 "ports:"
```

Résultat attendu :

```yaml
ports:
  - mode: ingress
    host_ip: 127.0.0.1     ← la preuve
    target: 8000
    published: "8000"
```

Test depuis une autre machine :

```bash
curl http://<IP_PUBLIQUE>:8000/openapi.json   # → connexion refusée
curl http://127.0.0.1:8000/openapi.json       # → 200 (depuis l'hôte)
```

---

## À retenir pour l'entretien

| Question | Réponse |
|----------|---------|
| **« Vos services sont-ils exposés ? »** | « Non. Ils écoutent sur la loopback. Le reverse proxy est le seul point d'entrée HTTPS. » |
| **« Pourquoi pas 0.0.0.0 ? »** | « Cela contournerait le proxy : plus de TLS, plus de filtrage, et la base serait joignable depuis Internet. » |
| **« Et PostgreSQL ? »** | « Aucun port publié — il n'est joignable que dans le réseau Docker, par les services qui en ont besoin. » |

**Phrase clé :** *« Les services applicatifs ne sont pas directement exposés à Internet. Le reverse proxy est le seul point d'entrée. »*

---

## Piège fréquent

```yaml
# ❌ Faux sentiment de sécurité
ports:
  - "localhost:8000:8000"
```

`localhost` n'est **pas** résolu comme une IP d'écoute par Docker — il faut l'IP littérale `127.0.0.1`.

```yaml
# ✅ Correct
ports:
  - "127.0.0.1:8000:8000"
```

---

> **Fichiers liés :** `deploy/docker-compose.yml`, `deploy/postgres.docker-compose.yml`
> **Suite :** INT-67 (healthchecks + `depends_on: condition: service_healthy`)
