# Note de correction : Reverse Proxy 1Panel pour Tervo

**Contexte** : Déploiement de l'application Tervo (Frontend statique + Backend FastAPI) derrière un reverse proxy 1Panel (OpenResty/Nginx) sur l'environnement local (`192.168.10.192`).

**Objectif** : Accéder à l'application via `http://192.168.10.192:3000`.

---

## 1. Problème initial : Conflit de ports

**Symptôme** : En créant le site dans 1Panel, erreur `"3000 port is already occupied!"`.

**Cause** : Le conteneur `tervo-frontend` exposait le port `3000` sur la machine hôte (via `ports: - "3000:80"`). 1Panel tentait de faire écouter son Nginx également sur le port `3000` de l'hôte, ce qui est impossible.

**Correction** :
Modifier le fichier `deploy/docker-compose.yml` et **supprimer/commenter** l'exposition du port pour le service `frontend` :

```yaml
services:
  frontend:
    # ...
    # ports:
    #   - "${FRONTEND_PORT:-80}:80"  # Commenté car géré par 1Panel
```

---

## 2. Problème réseau : `host not found in upstream`

**Symptôme** : Après avoir libéré le port et mis à jour le ProxyAddress avec `http://tervo-frontend-1:80`, 1Panel renvoie l'erreur :
`nginx: [emerg] host not found in upstream "tervo-frontend-1"`

**Diagnostic** :
Nous avons vérifié la configuration réseau des conteneurs avec :

```bash
# Vérification du réseau du frontend
docker inspect tervo-frontend-1 | grep -A 5 "Networks"
# Résultat : le frontend est bien sur le réseau "1panel-network".

# Vérification du réseau d'OpenResty (le moteur de 1Panel)
docker inspect 1Panel-openresty-DXF3 | grep -A 5 "Networks"
# Résultat : OpenResty est en mode "host".
```

**Conclusion** :
Le conteneur Nginx d'1Panel fonctionne en **mode réseau `host`** et ne se trouve **pas** sur le réseau interne `1panel-network`. Il ne peut donc pas résoudre les noms DNS des conteneurs (`tervo-frontend-1`).  
En revanche, il peut toujours les joindre via leurs **adresses IP internes**.

---

## 3. Solution finale : Utiliser les adresses IP statiques des conteneurs

### Étape 1 : Récupérer les IP internes

Exécutez les commandes suivantes pour obtenir les adresses IP de vos conteneurs sur le réseau `1panel-network` :

```bash
# Récupérer l'IP du Frontend
docker inspect tervo-frontend-1 | grep IPAddress
# Exemple de retour : "IPAddress": "172.18.0.3"

# Récupérer l'IP du Backend
docker inspect tervo-backend-1 | grep IPAddress
# Exemple de retour : "IPAddress": "172.18.0.2"
```

**Notez ces deux IP** (elles seront utilisées dans 1Panel).

---

### Étape 2 : Configurer le Reverse Proxy dans 1Panel

Dans l'interface de création du site (1Panel → Websites → Create → Reverse Proxy) :

| **Section**  | **Champ**      | **Valeur**                                                                                |
| :----------- | :------------- | :---------------------------------------------------------------------------------------- |
| **Domain**   | \*Domain       | `192.168.10.192`                                                                          |
|              | Hostname       | `192.168.10.192`                                                                          |
|              | \*Port         | `3000`                                                                                    |
|              | SSL            | Non coché (pas de SSL pour du local)                                                      |
| **Advanced** | \*Alias        | `tervo.local` (ou ce que vous voulez)                                                      |
| **Proxy**    | \*ProxyAddress | `http://<IP_FRONTEND>:80` <br> _(Remplacez par l'IP récupérée, ex: http://172.18.0.3:80)_ |

**Cliquez sur `Confirm`** – La création du site devrait réussir sans erreur.

---

### Étape 3 : Ajouter les règles de routage (Locations)

Une fois le site créé, allez dans l'onglet **Locations** (ou Règles) et ajoutez **dans cet ordre précis** :
IP_BACKEND:172.19.0.2
IP_FRONTEND:172.19.0.3
| **Ordre**       | **Path** | **Target**                 | **Description**                                                            |
| :-------------- | :------- | :------------------------- | :------------------------------------------------------------------------- |
| 1 (Prioritaire) | `/api/`  | `http://<IP_BACKEND>:8000` | Redirige toutes les requêtes API vers le backend FastAPI.                  |
| 2 (Fallback)    | `/`      | `http://<IP_FRONTEND>:80`  | Toutes les autres requêtes (pages HTML, JS, CSS, images) vers le frontend. |

> **⚠️ Attention** : L'ordre est crucial. Si la règle `/` passe avant `/api/`, le proxy tentera d'envoyer les appels API au frontend, ce qui cassera l'application.

**Cliquez sur `Save`** pour appliquer les changements.

---

## 4. Vérification et Test

Redémarrez éventuellement vos conteneurs pour vous assurer qu'ils sont toujours bien up :

```bash
cd ~/workspace/python/fastapi/tervo
docker compose -f deploy/docker-compose.yml up -d
```

Ouvrez votre navigateur et accédez à :

```
http://192.168.10.192:3000/login
```

- **Succès** : Le frontend s'affiche.
- **Appels API** : Les requêtes vers `/api/v1/...` (ou tout autre endpoint défini) doivent être transmises correctement au backend.

---

## 5. Récapitulatif des fichiers modifiés

| **Fichier**                 | **Modification effectuée**                                                                                                                 |
| :-------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| `deploy/docker-compose.yml` | Commenté le `ports` du service `frontend`. Ajout du réseau `1panel-network` aux services `frontend` et `backend` (s'il n'y était pas).     |
| Configuration 1Panel        | Utilisation des **IPs internes** (`docker inspect`) au lieu des noms de conteneurs dans le champ `ProxyAddress` et les règles `Locations`. |

---

## 6. Pourquoi ne pas utiliser les noms de conteneur ?

Dans un environnement Docker standard, un conteneur peut résoudre les noms des autres conteneurs via le DNS interne de Docker (`127.0.0.11`). Cependant, dans notre cas :

- Le conteneur `1Panel-openresty-DXF3` utilise le réseau **`host`** et n'est pas connecté au même réseau bridge sur lequel se trouvent `tervo-frontend-1` et `tervo-backend-1`.
- Par conséquent, OpenResty ne dispose pas de la configuration DNS pour résoudre ces noms.

L'utilisation des **IP statiques** (qui sont fixes tant que vous ne supprimez pas le réseau ou ne redémarrez pas Docker) est une solution rapide et fiable pour un environnement de développement local.

```

```
