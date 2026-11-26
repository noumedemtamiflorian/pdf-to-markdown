---
name: pdf-to-markdown
description: >-
  Convertit intégralement un document ou livre PDF (illustré ou non) en
  Markdown propre et structuré. Extrait le texte et toutes les images
  originales, reconstruit fidèlement la structure (titres, listes, tableaux,
  citations, blocs de code), insère chaque image avec sa légende uniquement
  (sans transcription ni traduction du texte interne aux images), audite la
  complétude et fusionne les chapitres si besoin. À utiliser dès que
  l'utilisateur demande de convertir un PDF en Markdown.
---

# Conversion Intégrale de PDF en Markdown (`pdf-to-markdown`)

## Overview

Ce skill permet de convertir un document ou livre PDF complet en **Markdown structuré et fidèle**, sans résumé ni omission, tout en extrayant et en insérant les illustrations originales accompagnées uniquement de leur légende.

Selon la taille du document, le résultat est produit soit en **un seul fichier Markdown** (document court, article, rapport), soit en **chapitres numérotés fusionnés** dans un fichier unique avec table des matières (livre ou manuel complet).

## Dependencies

Le script intégré utilise Python 3 avec deux bibliothèques légères (`pypdf` et `Pillow`), déclarées dans [requirements.txt](./requirements.txt).

Si ces paquets ne sont pas encore installés :

```bash
python -m pip install -r requirements.txt
```

## Quick Start

1. **Extraire le texte et les images du PDF source :**
   ```bash
   python scripts/pdf_pipeline.py extract --pdf "Document.pdf" --out-dir "./Markdown_Out"
   ```
2. **Convertir le contenu en Markdown** (un fichier unique ou des chapitres `00_...md`, `01_...md`, etc.) en insérant les images avec leur légende uniquement.
3. **Auditer la complétude de la conversion :**
   ```bash
   python scripts/pdf_pipeline.py audit --pdf "Document.pdf" --chapters-dir "./Markdown_Out" --min-ratio 0.95 --strict
   ```
4. **Fusionner les chapitres (si découpage multi-chapitres) :**
   ```bash
   python scripts/pdf_pipeline.py merge --chapters-dir "./Markdown_Out" --output "./Markdown_Out/DOCUMENT_COMPLET.md" --title "Titre du Document" --author "Nom de l'Auteur"
   ```

---

## Utility Scripts

Le script principal est [scripts/pdf_pipeline.py](./scripts/pdf_pipeline.py).

### 1. `extract` — Extraction du texte et des images

Extrait le texte page par page dans `book_text.txt`, toutes les images intégrées dans `<out-dir>/images/`, et génère `extraction_manifest.json` (numéro de page, dimensions, nom de fichier).

```bash
python scripts/pdf_pipeline.py extract \
  --pdf "chemin/vers/document.pdf" \
  --out-dir "chemin/vers/Markdown_Out"
```

### 2. `audit` (ou `verify`, `check`) — Audit de complétude

Compare le PDF source et les fichiers Markdown générés (ratio de mots avec seuil minimal `0.95` par défaut, détection des sections du sommaire PDF, comptage des images). Génère `audit_report.json` et `00_RAPPORT_AUDIT_COMPLETUDE.md`.

```bash
python scripts/pdf_pipeline.py audit \
  --pdf "chemin/vers/document.pdf" \
  --chapters-dir "chemin/vers/Markdown_Out" \
  --min-ratio 0.95 \
  --strict
```

### 3. `merge` — Fusion des chapitres Markdown

Assemble les fichiers numérotés (`00_Introduction.md`, `01_Chapitre_1.md`, etc.) en un document unique avec table des matières automatique et vérification de la présence de toutes les images référencées.

```bash
python scripts/pdf_pipeline.py merge \
  --chapters-dir "chemin/vers/Markdown_Out" \
  --output "chemin/vers/Markdown_Out/DOCUMENT_COMPLET.md" \
  --title "Titre du Document" \
  --subtitle "Sous-titre (optionnel)" \
  --author "Nom de l'Auteur"
```

---

## Workflow en 5 Étapes

### Étape 1 : Extraction et Analyse Initiale
1. Exécutez `extract` sur le PDF fourni par l'utilisateur.
2. Lisez `extraction_manifest.json` et parcourez `book_text.txt` pour identifier la structure (titre, auteur, sections/chapitres, nombre d'images).
3. **Cas d'un PDF scanné :** Si `book_text.txt` est vide ou quasi vide sur certaines pages alors que des images sont présentes, utilisez `read_file` sur les images/pages concernées pour lire le contenu.

### Étape 2 : Choix du Découpage
- **Document court** (article, note, rapport court) : rédigez directement un seul fichier Markdown propre (`01_Document.md` ou `<Nom_Document>.md`).
- **Livre ou document long** : découpez par chapitres numérotés (`00_Introduction.md`, `01_Chapitre_1.md`, etc.) afin de traiter chaque partie intégralement sans troncature.

### Étape 3 : Conversion Fidèle en Markdown
1. Conservez **100 % du texte** dans sa langue d'origine, sans résumer, reformuler ni sauter de paragraphe.
2. Reconstruisez proprement la mise en forme Markdown :
   - Hiérarchie des titres (`#`, `##`, `###`, etc.) ;
   - Listes à puces et numérotées ;
   - Tableaux Markdown ;
   - Citations (`>`) et notes de bas de page ;
   - Blocs de code (` ```lang `) uniquement lorsque le PDF contient réellement du code informatique ou des commandes.
3. Nettoyez les artefacts d'extraction PDF (césures de fin de ligne, numéros de page isolés, en-têtes/pieds de page répétitifs).

### Étape 4 : Insertion des Images avec Légende Seulement
À l'endroit exact où chaque illustration apparaît dans le document :
1. Référez l'image extraite (renommée clairement si utile, ex. `images/fig_01_01.jpg`) :
   ```markdown
   ![Description courte de l'image](images/fig_01_01.jpg)
   *Légende originale ou descriptive de l'image.*
   ```
2. **Règle stricte :** Insérez uniquement l'image et sa légende. **N'ajoutez pas** d'encadré de transcription ou de traduction du texte présent à l'intérieur de l'image.

### Étape 5 : Audit et Livraison
1. Exécutez `audit --strict` (avec `--min-ratio 0.95`) et vérifiez que tous les fichiers sont 🟢 CONFORME. Si un chapitre est marqué 🔴 COUPÉ ou 🟡 CONDENSÉ, complétez les passages manquants avant de continuer.
2. Si le document a été découpé en chapitres, exécutez `merge` pour produire le fichier complet unifié.
3. Présentez à l'utilisateur les liens cliquables vers les fichiers Markdown générés et le rapport d'audit.

---

## Erreurs fréquentes à éviter

1. **Résumer un passage long :** Ne condensez jamais. Traitez les documents longs par tranches de pages jusqu'à la dernière ligne.
2. **Laisser les artefacts PDF bruts :** Supprimez les sauts de ligne arbitraires au milieu des phrases et les en-têtes/pieds de page répétés à chaque page.
3. **Transcrire le texte interne des images :** Ce skill insère uniquement les images avec leur légende (`![...](...)` + `*Légende*`), sans bloc de transcription/traduction du contenu interne.
