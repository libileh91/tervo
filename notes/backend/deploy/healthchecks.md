# INT-67 — Healthchecks : `depends_on` ≠ readiness

> **Stage 6 / Sprint 6.1** | Points : 3 | Statut : ✅
> **Référence :** `docs/DAT/annexes/revue-architecture.md` §4

---

## Le problème

```yaml
backend:
  depends_on:
    - postgres
```

Beaucoup croient que ça signifie « attends que PostgreSQL soit prêt ».

**Faux.** Ça signifie seulement :

> « Démarre le conteneur `postgres` **avant** le conteneur `backend`. »

Et rien de plus.

### Pourquoi ça casse

Un conteneur PostgreSQL passe par plusieurs états :

```
créé → démarré → [initialisation] → prêt à accepter des connexions
                    ↑
         5 à 30 secondes (initdb, WAL, etc.)
```

`depends_on` (simple) s'arrête à « démarré ». Le backend peut donc tenter de se connecter **pendant l'initialisation** :

```
backend: "Connexion à postgres:5432…"
postgres: "Je démarre encore, je n'écoute pas encore"
backend: ❌ connection refused
```

---

## La solution : `healthcheck` + `condition`

### 1. Déclarer un healthcheck sur PostgreSQL

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U lob -d tervo_db"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s
```

| Paramètre | Rôle |
|-----------|------|
| `test` | La commande exécutée dans le conteneur. Code 0 = sain, ≠ 0 = malsain |
| `interval` | Fréquence des vérifications |
| `timeout` | Durée max d'une vérification |
| `retries` | Nombre d'échecs consécutifs avant de passer `unhealthy` |
| `start_period` | Délai de grâce au démarrage (les échecs ne comptent pas) |

**`pg_isready`** : outil livré avec PostgreSQL. Il retourne 0 **uniquement** si le serveur accepte les connexions. C'est exactement la sémantique « readiness » qu'on veut.

### 2. Faire dépendre le backend de l'état sain

```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy
```

Les valeurs possibles de `condition` :

| Valeur | Signification |
|--------|---------------|
| `service_started` | Le conteneur est lancé (= ancien comportement) |
| `service_healthy` | Le healthcheck passe ✅ |
| `service_completed_successfully` | Le conteneur s'est terminé avec code 0 (tâches one-shot) |

---

## Vérification réelle (test isolé exécuté)

Compose de test minimal (db + app) :

```bash
docker compose -p hctest -f .tmp-healthcheck/docker-compose.yml up -d
```

Sortie obtenue :

```
Container hctest-db-1 Starting
Container hctest-db-1 Started
Container hctest-db-1 Waiting      ← attend le healthcheck
Container hctest-db-1 Healthy      ← healthcheck OK
Container hctest-app-1 Starting    ← démarre SEULEMENT MAINTENANT
Container hctest-app-1 Started
```

Puis, dans les logs de l'app :

```
app-1  | >>> APP DEMARRE (PostgreSQL est healthy)
```

**La ligne `Waiting` → `Healthy` → `Starting` est la preuve visuelle du mécanisme.**

---

## ⚠️ Contrainte importante : même fichier Compose

`depends_on: condition: service_healthy` **ne fonctionne que si les deux services sont dans le même fichier Compose.**

C'est pourquoi la stack Tervo a été consolidée :

| Avant | Après |
|-------|-------|
| `docker-compose.yml` → backend + frontend | `docker-compose.yml` → **postgres + backend + frontend** |
| `postgres.docker-compose.yml` → postgres seul | Conservé pour le cas « PG partagé » (usage avancé) |

---

## Ce qui a été modifié

### `deploy/docker-compose.yml`

| Ajout | Détail |
|-------|--------|
| Service `postgres` | `postgres:17.4`, volume `postgres_data`, réseau `tervo_network` |
| Healthcheck `postgres` | `pg_isready -U lob -d tervo_db`, interval 10s, timeout 5s, retries 5, start_period 30s |
| `backend.depends_on` | `postgres: { condition: service_healthy }` |
| `postgres` | aucun port publié (cf. INT-66) |
| Réseau interne | `tervo_network` (bridge) remplace le réseau externe `postgres_postgres_network` |

### `deploy/postgres.docker-compose.yml`

Healthcheck harmonisé (10s / 5s / 5 essais, utilisateur + base explicites).

---

## À retenir pour l'entretien

**Question type :** « Pourquoi utilisez-vous un healthcheck ? »

> « Parce que le démarrage d'un conteneur PostgreSQL ne garantit pas que la base soit prête à accepter des connexions. `depends_on` seul n'assure que l'ordre de démarrage, pas la disponibilité. Avec un healthcheck `pg_isready` et `condition: service_healthy`, le backend ne démarre qu'une fois la base réellement joignable — ça élimine les erreurs de connexion au démarrage. »

**Question type :** « Quelle différence entre démarré et prêt ? »

> « Un conteneur peut être "Up" alors que le processus interne finit son initialisation. Le healthcheck matérialise cette frontière : c'est ce qui distingue un conteneur lancé d'un service réellement disponible. »

---

## Pièges

| Piège | Conséquence |
|-------|-------------|
| `depends_on` sans `condition` | Le backend démarre trop tôt |
| Healthcheck sans `start_period` | Le conteneur est marqué `unhealthy` pendant l'init |
| `pg_isready` sans `-U`/`-d` | Peut réussir alors que la base cible n'existe pas |
| Services dans deux fichiers Compose | `condition: service_healthy` ignoré |

---

> **Fichiers liés :** `deploy/docker-compose.yml`, `deploy/postgres.docker-compose.yml`
> **Précédent :** INT-66 (ports sécurisés)
> **Suite :** INT-68 (firewall 22/80/443)
