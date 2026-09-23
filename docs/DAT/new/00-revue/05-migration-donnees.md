# Migration des données historiques — différenciateur

> **Statut :** transverse — remontée dans la priorité (ne dépend que du Lot 1).
> **Rôle entretien :** c'est le **différenciateur** technique du projet.

---

# 1. Positionnement

La migration de **20 ans d'Excel** est le sujet technique central. Elle est **remontée** dans
la priorité (elle ne dépend que du cœur physique, pas de la chaîne commerciale) et cible :

```text
Client ──► Site ──► Équipement ──► Intervention   (+ Product pour le catalogue)
```

**Pourquoi elle ne dépend pas de la vente/installation :** les équipements historiques ont
`installation_id` nullable — ils ont été installés il y a des années, sans vente/installation
enregistrée dans Tervo.

---

# 2. Le pipeline (réutilisé)

Le package `app/importers/` (structure du pipeline) est réutilisé tel quel :

```text
ExcelReader → FormatDetector → Normalizer → Validator → ClientMatcher → ImportReport
      → ImportService (2 passes + transactions)
```

Seuls le **vocabulaire** (les champs) et les **cibles** (5 entités) changent.

---

# 3. Rapprochement multi-niveaux (fuzzy, 3 zones)

Le matching s'opère sur **3 niveaux** :

```text
Client  →  match nom + téléphone
   └── Site  →  match adresse + ville (dans le client)
        └── Équipement  →  match n° série + produit (dans le site)
```

Trois zones de décision, par niveau :

| Score | Décision |
|-------|----------|
| `≥ 95` | rapprochement **automatique** |
| `80 – 95` | **validation humaine** (zone grise) |
| `< 80` | **nouvelle entité** |

> Une erreur de rapprochement (fusion de deux entités distinctes) coûte plus cher qu'un
> doublon temporaire — d'où la zone grise large.

---

# 4. Deux passes + transactions par batch

```text
PASS 1 — Client → Site → Équipement   (résolution + IDs canoniques)
PASS 2 — Intervention                   (résolution site_id + equipment_id)
```

- **Transaction par batch** (500 lignes), jamais une transaction géante.
- Un batch en échec est rollbacké seul ; les précédents restent commités.

---

# 5. Idempotence (SHA-256)

- `file_hash` = SHA-256 du fichier, enregistré dans `ImportBatch`.
- Un fichier déjà importé (`status=success`) est **ignoré** (`skipped`).
- Traçabilité ligne à ligne via `ImportRecord`.

---

# 6. Orphelins tracés, jamais ignorés

Une intervention dont l'équipement (ou le site) est introuvable part en `import_errors` avec
`status=ORPHAN` — **jamais ignorée silencieusement**, et l'`original_value` est conservé pour
résolution manuelle ultérieure.

---

# 7. Ne pas inventer les données manquantes

Une donnée historique ambiguë ne doit pas produire une fausse certitude :

```text
Client : Dupont
Intervention : « Réparation climatisation » — 12/05/2024
```

→ on crée `Client → Équipement → Intervention`, mais **sans inventer** marque, modèle,
n° de série ou date d'installation.

Une anomalie peut être : rattachée à une entité existante, utilisée pour en créer une
nouvelle, corrigée, ou ignorée **avec justification** — toujours traçable.

---

# 8. Résumé des mécanismes conservés

| Mécanisme | Statut |
|-----------|--------|
| Normalisation (accents, casse, téléphone) | ✅ |
| Fuzzy matching 3 zones (95/80) | ✅ |
| 2 passes (dépendances FK d'abord) | ✅ |
| Transaction par batch | ✅ |
| Idempotence SHA-256 + `ImportBatch` | ✅ |
| Orphelins → `import_errors` | ✅ |
