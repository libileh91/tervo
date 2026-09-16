# Sprint 5.2 : Polish & PWA (Semaine 7)

> **Durée :** 5 jours | **Points :** 19 | **Tâches :** 5 (INT-61 à INT-65)

---

## INT-61 — PWA : service worker + manifest + offline basique (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **pouvoir installer l'application sur mon téléphone**  
Afin d'**y accéder comme une app native, même sans réseau**.

**Acceptance Criteria**
- [ ] Service worker enregistré à l'initialisation de l'app (`main.ts`)
- [ ] Manifeste `manifest.webmanifest` avec :
  - `name: "Tervo"`, `short_name: "Tervo"`
  - Icônes 192x192, 512x512
  - `start_url: "/"`, `display: "standalone"`
- [ ] Cache des assets statiques (CSS, JS, fonts PrimeVue)
- [ ] Page offline basique : "Vous êtes hors-ligne. Les données peuvent ne pas être à jour."
- [ ] Installable sur mobile (critère PWA Android/iOS)

**Technical Notes**
- Fichier : `frontend/public/manifest.webmanifest` (nouveau)
- Fichier : `frontend/public/sw.js` ou `frontend/src/sw.ts` (service worker)
- Utiliser Vite PWA plugin : `npm install -D vite-plugin-pwa`
- Configurer dans `vite.config.ts` : `import { VitePWA } from 'vite-plugin-pwa'`
- Icônes : générer 192x192 et 512x512 PNG (via outil en ligne)

---

## INT-62 — Dark mode (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **utiliser l'application en mode sombre le soir**  
Afin de **ne pas fatiguer mes yeux**.

**Acceptance Criteria**
- [ ] Bascule dark/light dans le profil ou le header
- [ ] Persistance du choix (localStorage)
- [ ] PrimeVue dark mode activé via `darkModeSelector`
- [ ] CSS custom : couleurs adaptées sur tous les composants
- [ ] Respecte le `prefers-color-scheme` du système au premier lancement
- [ ] Transition douce entre les modes

**Technical Notes**
- PrimeVue 4 : `darkModeSelector: '.p-dark'` dans la config `main.ts`
- Stockage : `localStorage.setItem('tervo_theme', 'dark'|'light')`
- CSS : variables CSS personnalisées pour les couleurs custom
- `<i class="pi pi-sun" />` / `<i class="pi pi-moon" />` pour l'icône

---

## INT-63 — QR code pour lien avis (3 pts)

**User Story**  
En tant que **technicien**,  
Je veux **générer un QR code pour le lien d'avis client**  
Afin de **le faire scanner par le client plutôt que d'envoyer un SMS**.

**Acceptance Criteria**
- [ ] Dans `JobDetailPage` (job terminé) : afficher un QR code
- [ ] QR code généré côté client (librairie JS, pas d'appel serveur)
- [ ] Le QR code encode l'URL complète du lien d'avis : `https://<domain>/review/{token}`
- [ ] Bouton "📋 Copier le lien" + "📱 Afficher le QR code"
- [ ] QR code affiché dans un Dialog overlay

**Technical Notes**
- Librairie : `npm install qrcode` (ou `vue-qrcode`)
- URL du lien : utiliser `window.location.origin` pour construire l'URL absolue
- Dialog PrimeVue : `<Dialog v-model:visible="showQR"> <vue-qrcode :value="reviewUrl" /> </Dialog>`

---

## INT-64 — Cache offline : derniers jobs téléchargés (5 pts)

**User Story**  
En tant que **technicien**,  
Je veux **pouvoir consulter mes derniers jobs même sans réseau**  
Afin de **préparer mon intervention avant d'arriver sur place**.

**Acceptance Criteria**
- [ ] Les derniers jobs consultés sont mis en cache (localStorage ou IndexedDB)
- [ ] En mode hors-ligne : afficher les données du cache avec un bandeau "Hors-ligne"
- [ ] Cache mis à jour à chaque consultation (stratégie "stale-while-revalidate")
- [ ] Limiter à 20 jobs en cache
- [ ] Photos : afficher les thumbnails du cache ou placeholder
- [ ] Bouton "📥 Mettre en cache pour offline" sur `JobDetailPage`

**Technical Notes**
- Utiliser `localforage` ou IndexedDB via `idb-keyval` pour un stockage structuré
- `npm install localforage`
- Service worker : intercepter les requêtes API et les mettre en cache (Network First → Cache Fallback)

---

## INT-65 — Revue de sécurité + nettoyage (3 pts)

**User Story**  
En tant que **développeur**,  
Je veux **auditer la sécurité et nettoyer le code**  
Afin de **préparer une mise en production sécurisée**.

**Acceptance Criteria**
- [ ] Vérifier : CORS restreint aux origines nécessaires
- [ ] Vérifier : SECRET_KEY forte en production (via variable d'environnement)
- [ ] Vérifier : validation Pydantic sur tous les endpoints
- [ ] Vérifier : `is_active` check sur le login
- [ ] Nettoyer les commentaires de debug, `print()` et code mort
- [ ] Vérifier : pas de mot de passe en dur dans le code
- [ ] Supprimer les fichiers `.db` du repository (garder dans `.gitignore`)
- [ ] Audit de sécurité basique : injections SQL, XSS, CSRF
- [ ] Ajouter un `SECURITY.md` ou section dans le README

**Technical Notes**
- SQL injection : SQLAlchemy paramétré ✅ (déjà)
- XSS : templates Vue.js échappés ✅ (déjà)
- CORS : `allow_origins` à restreindre (`["https://mon-domaine.com"]`)
- `pip-audit` : `pip install pip-audit && pip-audit`
- Nettoyer le repo : `git rm --cached *.db` si versionné

---

## Tests Cases Sprint 5.2

Les tests cases détaillés sont dans `test-cases.json`.
