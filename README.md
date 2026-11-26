# pdf-to-markdown

Skill d'agent permettant de convertir intégralement un document ou livre PDF (illustré ou non) en **Markdown propre et structuré**, tout en extrayant les images originales avec leur légende, en auditant la complétude et en fusionnant les chapitres si nécessaire.

## Contenu du dépôt

- `SKILL.md` : Instructions et workflow complet du skill.
- `scripts/pdf_pipeline.py` : Script Python d'extraction (`extract`), d'audit de complétude (`audit`) et de fusion de chapitres (`merge`).
- `requirements.txt` : Dépendances Python (`pypdf`, `Pillow`).

## Installation sur un autre ordinateur

### 1. Cloner le skill dans votre dossier de skills

Par exemple pour Antigravity / Gemini CLI :

```bash
git clone https://github.com/noumedemtamiflorian/pdf-to-markdown.git ~/.gemini/config/skills/pdf-to-markdown
```

Ou dans un dossier partagé (`~/.agents/skills/`) :

```bash
git clone https://github.com/noumedemtamiflorian/pdf-to-markdown.git ~/.agents/skills/pdf-to-markdown
```

### 2. Installer les dépendances Python

```bash
cd ~/.gemini/config/skills/pdf-to-markdown
python -m pip install -r requirements.txt
```

## Utilisation rapide

Consultez [SKILL.md](./SKILL.md) pour le workflow complet, ou utilisez directement le script :

```bash
# 1. Extraire le texte et les images
python scripts/pdf_pipeline.py extract --pdf "Document.pdf" --out-dir "./Markdown_Out"

# 2. Auditer la complétude après conversion
python scripts/pdf_pipeline.py audit --pdf "Document.pdf" --chapters-dir "./Markdown_Out" --min-ratio 0.95 --strict

# 3. Fusionner les chapitres (si multi-chapitres)
python scripts/pdf_pipeline.py merge --chapters-dir "./Markdown_Out" --output "./Markdown_Out/DOCUMENT_COMPLET.md" --title "Titre" --author "Auteur"
```
