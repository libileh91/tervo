# INT-29 — Génération PDF rapport (WeasyPrint + Jinja2)

> **Objectif** : Générer un rapport PDF d'intervention avec client, checklist, photos, matériaux, observations
> **Stack** : WeasyPrint + Jinja2 + Python base64

---

## 1. Choix techniques

### Pourquoi WeasyPrint et pas un autre générateur PDF ?

| Technologie | Browser headless ? | Installation | Qualité PDF |
|---|---|---|---|
| **WeasyPrint** | Non (Pango + Cairo) | pip + libs système | Excellente |
| pdfkit / wkhtmltopdf | Oui (WebKit) | Binaire externe | Moyenne |
| Playwright | Oui (Chromium) | ~300 Mo de Chrome | Très bonne |
| ReportLab | Non | pip | Bas niveau (pas de CSS) |

**WeasyPrint** a été choisi car :
- Pas de browser headless → pas de dépendance lourde (Playwright = 300 Mo de Chromium)
- Support CSS complet → le template HTML est directement convertible
- Stable et mature (v60+)
- Nécessite seulement des libs système (Pango pour le texte, Cairo pour le rendu) — déjà installées sur le système

---

## 2. Installation

### Dépendances Python

```bash
cd backend/
.venv/bin/pip install weasyprint jinja2
```

| Package | Version | Rôle |
|---|---|---|
| `weasyprint` | >= 60.0 | Convertit HTML/CSS → PDF |
| `Jinja2` | >= 3.1.0 | Moteur de template HTML (boucles, conditions, variables) |

### Dépendances système (vérification)

```bash
dpkg -l | grep -E "libpango|libcairo|libgdk-pixbuf" | wc -l
# → 4 ou plus = OK
```

WeasyPrint utilise les librairies système pour le rendu :
- **Pango** : mesure et disposition du texte
- **Cairo** : rendu graphique vectoriel
- **GDK-Pixbuf** : chargement des images

---

## 3. Architecture

```
backend/app/exporters/
├── __init__.py              # Package
├── report.py                # ReportExporter class
└── report_template.html     # Template Jinja2 (HTML + CSS)
```

### 3.1 `ReportExporter` — le générateur

```python
class ReportExporter:
    def __init__(self):
        # Charge le template Jinja2 UNE FOIS au constructeur
        template_path = Path(__file__).parent / "report_template.html"
        with open(template_path) as f:
            self.template = Template(f.read())

    def generate_pdf(self, job: Job) -> bytes:
        # 1. Organiser les données
        ctx = self._build_context(job)

        # 2. Rendre le template → HTML
        html = self.template.render(**ctx)

        # 3. Convertir en PDF
        pdf = self._html_to_pdf(html)
        return pdf
```

Le template est chargé une seule fois à l'instanciation (pas à chaque appel de `generate_pdf`). C'est un pattern courant pour les moteurs de template : `Template()` compile le template, `render()` l'exécute avec les données.

### 3.2 `_build_context()` — préparation des données

```python
def _build_context(self, job: Job) -> dict:
    # Checklist : grouper par catégorie
    pre_items = []
    post_items = []
    for item in job.checklist_items or []:
        entry = {"label": item.label, "checked": item.checked, "note": item.note}
        if item.category == "pre_intervention":
            pre_items.append(entry)
        else:
            post_items.append(entry)

    # Photos : encoder en base64 (PDF autonome)
    avant_photos = []
    apres_photos = []
    for photo in job.photos or []:
        uri = self._embed_photo(photo.file_path)
        if uri:
            (avant_photos if photo.category == "avant" else apres_photos).append(uri)

    # Matériaux
    materials_list = [
        {"name": m.name, "quantity": m.quantity}
        for m in (job.materials or [])
    ]

    return {
        "job": { "id": job.id, "title": job.title, ... },
        "client": { "full_name": client.full_name, ... },
        "technician": { "full_name": technician.full_name },
        "checklist_pre": pre_items,
        "checklist_post": post_items,
        "photos_avant": avant_photos,
        "photos_apres": apres_photos,
        "materials": materials_list,
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
```

### 3.3 `_embed_photo()` — intégration des photos en base64

```python
def _embed_photo(self, file_path: str | None) -> str | None:
    if not file_path or not Path(file_path).exists():
        return None

    data = Path(file_path).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    ext = Path(file_path).suffix.lstrip(".")

    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(
        ext, "jpeg"
    )
    return f"data:image/{mime};base64,{b64}"
```

**Pourquoi base64 et pas un simple lien ?**

Un chemin comme `/uploads/photos/uuid.jpg` ne fonctionnerait **pas** dans le PDF car :
- Le PDF est visualisé sur le poste du client (pas sur le serveur)
- Le navigateur du client n'a pas accès au système de fichiers du serveur
- Le PDF doit être **autonome** (pas de dépendance réseau)

Le data URI (`data:image/jpeg;base64,...`) intègre directement l'image dans le PDF. Le PDF peut être envoyé par email, imprimé, archivé, sans perte des photos.

**Inconvénient** : la taille du PDF augmente (~150 Ko par photo en base64 vs ~50 Ko pour le fichier original, car base64 = +33%).

### 3.4 `_html_to_pdf()` — conversion WeasyPrint

```python
def _html_to_pdf(self, html: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=html).write_pdf()
```

`HTML(string=html)` crée un document WeasyPrint à partir d'une chaîne HTML. `write_pdf()` rend le HTML en PDF et retourne les bytes. Rien n'est écrit sur le disque.

---

## 4. Le template Jinja2

### 4.1 Syntaxe Jinja2

| Syntaxe | Rôle |
|---|---|
| `{{ variable }}` | Affiche une variable |
| `{% for item in list %}` | Boucle |
| `{% if condition %}` | Condition |
| `{% endif %}` / `{% endfor %}` | Fin de bloc |

### 4.2 Structure du template

```html
<!-- Variables -->
<h1>{{ job.title }}</h1>
<span>Client : {{ client.full_name }}</span>
<span>Technicien : {{ technician.full_name }}</span>

<!-- Conditions -->
{% if item.checked %}
  <td class="check-yes">O</td>
{% else %}
  <td class="check-no">X</td>
{% endif %}

<!-- Boucles -->
{% for mat in materials %}
  <tr>
    <td>{{ mat.name }}</td>
    <td>{{ mat.quantity }}</td>
  </tr>
{% endfor %}

<!-- Conditionnelles (affichage conditionnel) -->
{% if job.observations %}
  <div class="observations">{{ job.observations }}</div>
{% endif %}
```

### 4.3 CSS pour l'impression A4

```css
@page {
    size: A4;
    margin: 2cm 1.5cm;
    @bottom-center {
        content: "Page " counter(page) " / " counter(pages);
        font-size: 9px;
        color: #888;
    }
}
```

- `@page` définit le format du papier (A4) et les marges
- `@bottom-center` ajoute un pied de page avec numérotation automatique (`counter(page)`)
- Le CSS est **inline** dans le template (pas de fichier CSS externe) car le PDF doit être autonome

---

## 5. Test

```bash
cd backend/

# Test unitaire du générateur
.venv/bin/python -c "
from pathlib import Path
from jinja2 import Template
from weasyprint import HTML

# Charger le template
html = Path('app/exporters/report_template.html').read_text(encoding='utf-8')
t = Template(html)

# Contexte de test
ctx = {
    'job': {'id': 13, 'title': 'Intervention chaudière', 'status': 'termine',
            'status_label': 'Terminé', 'scheduled_date': '2026-06-15',
            'observations': 'Travail propre. Client satisfait.'},
    'client': {'full_name': 'M. Dupont', 'phone': '0123456789',
               'address': '1 rue de la Paix', 'postal_code': '75001',
               'city': 'Paris'},
    'technician': {'full_name': 'Jean Martin'},
    'checklist_pre': [{'label': 'Vérifier EPI', 'checked': True, 'note': 'OK'},
                      {'label': 'Couper alimentation', 'checked': True, 'note': ''}],
    'checklist_post': [{'label': 'Nettoyer zone', 'checked': False, 'note': ''}],
    'photos_avant': [],
    'photos_apres': [],
    'materials': [{'name': 'Filtre HEPA', 'quantity': '1'},
                  {'name': 'Joint torique', 'quantity': '2'}],
    'generated_at': '15/06/2026 10:00',
}

# Générer le PDF
pdf = HTML(string=t.render(**ctx)).write_pdf()
print(f'PDF généré : {len(pdf)} bytes')   # ~15 KB

# Sauvegarder pour inspection visuelle
with open('/tmp/test-rapport.pdf', 'wb') as f:
    f.write(pdf)
print('Sauvegard