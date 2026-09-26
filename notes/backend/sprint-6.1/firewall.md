# INT-68 — Firewall : surface d'exposition minimale

> **Stage 6 / Sprint 6.1** | Points : 1 | Statut : ✅
> **Référence :** `docs/DAT/annexes/revue-architecture.md` §20

---

## Le problème

Le DAT contenait deux politiques **contradictoires** :

```
« ufw : ports 22, 80, 443, 7410 »
« ufw : ports 22, 80, 443 uniquement »
```

Un port en trop peut suffire à ouvrir une brèche. Il faut **une seule règle**, explicite.

---

## La décision

| Port | Service | Public ? | Justification |
|------|---------|:--------:|---------------|
| **22** | SSH | ✅ | Administration du serveur (clé uniquement) |
| **80** | HTTP | ✅ | Redirection → 443 + challenge ACME Let's Encrypt |
| **443** | HTTPS | ✅ | Trafic applicatif (reverse proxy 1Panel) |
| **7410** | 1Panel | ❌ | Interface d'admin — **jamais publique** |
| 8000 | Backend | ❌ | Bindé sur `127.0.0.1` (cf. INT-66) |
| 3000 | Frontend | ❌ | Bindé sur `127.0.0.1` (cf. INT-66) |
| 5432 | PostgreSQL | ❌ | Aucun port publié (cf. INT-66) |

> **Principe :** n'ouvrir que ce qui doit l'être. Une interface d'administration exposée sur Internet est une cible permanente (scans automatisés, brute-force, CVE non patchées).

---

## Mise en place

### 1. Règles ufw

```bash
# Politique par défaut : tout refuser en entrée
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Autoriser SSH AVANT d'activer (sinon on se coupe l'accès)
sudo ufw allow 22/tcp

# HTTP + HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Activer
sudo ufw enable

# Vérifier
sudo ufw status verbose
```

Résultat attendu :

```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

> ⚠️ **Piège classique :** activer ufw **avant** d'autoriser le port 22 coupe la connexion SSH et peut rendre le serveur inaccessible. Toujours autoriser SSH en premier.

### 2. fail2ban (protection SSH)

```bash
sudo apt install fail2ban
sudo systemctl enable --now fail2ban
```

Configuration `/etc/fail2ban/jail.local` :

```ini
[sshd]
enabled = true
port = 22
maxretry = 5
bantime = 1h
findtime = 10m
```

**Rôle :** bannit automatiquement une IP après 5 échecs de connexion SSH. Complète ufw : ufw filtre par port, fail2ban filtre par **comportement**.

---

## Accéder à 1Panel sans l'exposer

### Méthode 1 — Tunnel SSH (recommandée)

Le port 7410 **écoute sur la loopback du serveur**. On le rend accessible localement via un tunnel :

```bash
ssh -L 7410:localhost:7410 user@<IP_VPS>
```

Puis, dans le navigateur :

```
http://localhost:7410
```

**Comment ça marche :**

```
Navigateur (ta machine)          Serveur VPS
   localhost:7410  ──SSH────►  localhost:7410 (1Panel)
        ▲                            ▲
   port local                  écoute loopback
   (tunnel)                    (non exposé à Internet)
```

Le trafic passe **chiffré dans le tunnel SSH**. Aucun port n'est ouvert sur Internet.

### Méthode 2 — Restriction par IP (alternative)

Si l'IP d'administration est fixe :

```bash
sudo ufw allow from 203.0.113.42 to any port 7410 proto tcp
```

**Limite :** dépend d'une IP stable. Une IP dynamique (box domestique) rend cette règle inutilisable.

### Méthode 3 — Bind sur loopback (complément)

Configurer 1Panel pour écouter uniquement sur `127.0.0.1` :

```
Écoute : 127.0.0.1:7410   (et non 0.0.0.0:7410)
```

→ Même si ufw était mal configuré, le port resterait inaccessible de l'extérieur. **Défense en profondeur.**

---

## Vérification

```bash
# Depuis l'extérieur (autre machine)
curl -m 5 http://<IP_VPS>:7410        # → timeout / connexion refusée
curl -m 5 http://<IP_VPS>:8000        # → connexion refusée (127.0.0.1)
curl -m 5 http://<IP_VPS>:5432        # → connexion refusée (aucun port)

# Depuis le tunnel SSH
ssh -L 7410:localhost:7410 user@<IP_VPS>
curl http://localhost:7410            # → réponse 1Panel

# Vérifier les écoutes sur le serveur
sudo ss -tlnp | grep -E '7410|8000|3000|5432'
```

---

## À retenir pour l'entretien

**Question type :** « Comment protégez-vous le serveur ? »

> « Deux niveaux. D'abord le firewall : seuls 22, 80 et 443 sont ouverts. Les services applicatifs écoutent sur la loopback, PostgreSQL ne publie rien. L'interface d'administration 1Panel n'est jamais exposée — j'y accède par tunnel SSH. Ensuite fail2ban, qui bannit les IP après plusieurs échecs SSH. »

**Question type :** « Pourquoi pas exposer l'admin ? »

> « Une interface d'administration publique est une cible permanente : scans, brute-force, exploitation de CVE. Le tunnel SSH coûte une commande et supprime toute cette surface. »

**Formulation courte :** *« Surface d'exposition minimale : 22/80/443 seulement, tout le reste en loopback. »*

---

## Aide-mémoire

| Commande | Effet |
|----------|-------|
| `ufw status verbose` | Voir les règles actives |
| `ufw allow 443/tcp` | Ouvrir un port |
| `ufw delete allow 443/tcp` | Fermer un port |
| `ufw default deny incoming` | Politique par défaut : refuser |
| `ssh -L 7410:localhost:7410 user@vps` | Tunnel vers 1Panel |
| `fail2ban-client status sshd` | Voir les IP bannies |
| `ss -tlnp` | Voir les ports en écoute |

---

> **Fichiers liés :** DAT (`04-architecture.md`, `06-workflows.md`, `07-implementation-roadmap.md`, `specs/02-spec-technique.md`) — mentions `7410` harmonisées
> **Précédent :** INT-67 (healthchecks)
> **Suite :** INT-69 (versions dans le DAT)
