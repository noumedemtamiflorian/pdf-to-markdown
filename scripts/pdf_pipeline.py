#!/usr/bin/env python3
"""
pdf_pipeline.py — Universal CLI utility for the `pdf-to-markdown` skill.

Subcommands:
  1. extract : Extracts full text (page by page) and all embedded images from a source PDF.
  2. audit   : Audits completeness between the source PDF and converted Markdown files.
  3. merge   : Merges numbered Markdown chapters into a single unified Markdown document.
"""

import argparse
import io
import json
import pathlib
import re
import sys


def cmd_extract(args):
    try:
        from PIL import Image as PILImage
        from pypdf import PdfReader
    except ImportError as exc:
        sys.stderr.write(
            f"Error: Missing Python dependency ({exc}).\n"
            "Run: python -m pip install pypdf Pillow\n"
        )
        sys.exit(1)

    pdf_path = pathlib.Path(args.pdf).resolve()
    if not pdf_path.exists():
        sys.stderr.write(f"Error: Source PDF not found: {pdf_path}\n")
        sys.exit(1)

    out_dir = pathlib.Path(args.out_dir).resolve()
    images_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    text_chunks = []
    manifest_images = []
    img_counter = 0

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        text_chunks.append(f"=== PAGE {page_num} / {total_pages} ===\n{page_text}\n")

        try:
            page_images = page.images
        except Exception:
            page_images = []

        for img_file in page_images:
            img_counter += 1
            raw_data = img_file.data
            ext = pathlib.Path(img_file.name).suffix.lower() or ".jpg"
            width, height = 0, 0
            try:
                with PILImage.open(io.BytesIO(raw_data)) as pil_im:
                    width, height = pil_im.size
                    if ext not in (".jpg", ".jpeg", ".png"):
                        ext = ".jpg"
                    img_filename = f"page_{page_num:03d}_img_{img_counter:02d}{ext}"
                    img_out_path = images_dir / img_filename
                    if ext in (".jpg", ".jpeg") and pil_im.mode not in ("RGB", "L"):
                        pil_im = pil_im.convert("RGB")
                    pil_im.save(str(img_out_path))
            except Exception:
                img_filename = f"page_{page_num:03d}_img_{img_counter:02d}{ext}"
                img_out_path = images_dir / img_filename
                img_out_path.write_bytes(raw_data)

            manifest_images.append(
                {
                    "index": img_counter,
                    "page": page_num,
                    "filename": f"images/{img_filename}",
                    "original_name": img_file.name,
                    "width": width,
                    "height": height,
                    "bytes": len(raw_data),
                }
            )

    text_out_path = out_dir / "book_text.txt"
    text_out_path.write_text("\n".join(text_chunks), encoding="utf-8")

    manifest = {
        "source_pdf": str(pdf_path),
        "total_pages": total_pages,
        "extracted_text_file": str(text_out_path),
        "total_images_extracted": len(manifest_images),
        "images_dir": str(images_dir),
        "images": manifest_images,
    }
    manifest_path = out_dir / "extraction_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"Success! Extracted {total_pages} pages of text to '{text_out_path}' "
        f"and {len(manifest_images)} images to '{images_dir}'. "
        f"Manifest written to: '{manifest_path}'"
    )


def slugify(text):
    text = re.sub(r"[\*_`]", "", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    return text


def cmd_merge(args):
    chapters_dir = pathlib.Path(args.chapters_dir).resolve()
    if not chapters_dir.exists():
        sys.stderr.write(f"Error: Chapters directory not found: {chapters_dir}\n")
        sys.exit(1)

    output_md = pathlib.Path(args.output).resolve()
    output_md.parent.mkdir(parents=True, exist_ok=True)

    all_md = sorted(chapters_dir.glob("*.md"))
    chapter_files = []
    for p in all_md:
        name_upper = p.name.upper()
        if (
            "INDEX" in name_upper
            or "RAPPORT" in name_upper
            or "AUDIT" in name_upper
            or "DOCUMENT_COMPLET" in name_upper
            or "LIVRE_COMPLET" in name_upper
            or p.resolve() == output_md
        ):
            continue
        if re.match(r"^\d{2}_", p.name):
            chapter_files.append(p)

    if not chapter_files:
        sys.stderr.write(f"Error: No numbered chapter files (e.g. 00_*.md, 01_*.md) found in {chapters_dir}\n")
        sys.exit(1)

    toc_lines = []
    chapter_contents = []
    for ch_file in chapter_files:
        txt = ch_file.read_text(encoding="utf-8").strip()
        chapter_contents.append(txt)
        m_h1 = re.search(r"^#\s+(.+)$", txt, flags=re.MULTILINE)
        if m_h1:
            h1_title = m_h1.group(1).strip()
            toc_lines.append(f"- [{h1_title}](#{slugify(h1_title)})")

    subtitle_line = f"## {args.subtitle}\n" if args.subtitle else ""
    author_line = f"**Auteur :** {args.author}  \n" if args.author else ""
    header = (
        f"# {args.title}\n"
        f"{subtitle_line}"
        f"{author_line}"
        f"\n---\n\n"
        f"## Table des matières\n\n"
        + "\n".join(toc_lines)
        + "\n\n---\n"
    )

    full_text = header + "\n\n---\n\n".join(chapter_contents) + "\n"
    output_md.write_text(full_text, encoding="utf-8")

    img_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", full_text)
    missing_imgs = [
        src for src in img_refs if not (output_md.parent / src).exists() and not (chapters_dir / src).exists()
    ]

    report = {
        "merged_chapters_count": len(chapter_files),
        "chapters": [p.name for p in chapter_files],
        "output_markdown": str(output_md),
        "total_characters": len(full_text),
        "total_images_referenced": len(img_refs),
        "missing_images": missing_imgs,
    }
    report_path = output_md.with_suffix(".merge_report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if missing_imgs:
        sys.stderr.write(f"Warning: {len(missing_imgs)} referenced images were not found: {missing_imgs}\n")

    print(
        f"Success! Merged {len(chapter_files)} chapters ({len(img_refs)} images referenced) "
        f"into: '{output_md}'"
    )


def cmd_audit(args):
    """
    Audits completeness between the source PDF and converted Markdown files.
    Calculates word count ratios, checks for missing outline sections, and counts images.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        sys.stderr.write(
            f"Error: Missing Python dependency ({exc}).\n"
            "Run: python -m pip install pypdf Pillow\n"
        )
        sys.exit(1)

    pdf_path = pathlib.Path(args.pdf).resolve()
    chapters_dir = pathlib.Path(args.chapters_dir).resolve()

    if not pdf_path.exists():
        sys.stderr.write(f"Error: Source PDF not found: {pdf_path}\n")
        sys.exit(1)

    if not chapters_dir.exists():
        sys.stderr.write(f"Error: Chapters dir not found: {chapters_dir}\n")
        sys.exit(1)

    reader = PdfReader(str(pdf_path))
    total_pdf_pages = len(reader.pages)

    pages_text = [p.extract_text() or "" for p in reader.pages]
    total_src_words = sum(len(txt.split()) for txt in pages_text)

    outline = []

    def parse_items(items, depth=1):
        for it in items:
            if isinstance(it, list):
                parse_items(it, depth + 1)
            else:
                try:
                    p = reader.get_destination_page_number(it)
                    outline.append({"depth": depth, "title": it.title, "page": p + 1})
                except Exception:
                    pass

    if reader.outline:
        parse_items(reader.outline)

    md_files = sorted(
        [
            f
            for f in chapters_dir.glob("*.md")
            if not f.name.startswith("00_INDEX")
            and not f.name.startswith("00_RAPPORT")
            and not f.name.startswith("DOCUMENT_COMPLET")
            and not f.name.startswith("LIVRE_COMPLET")
        ]
    )

    anchors = []
    intro_start = None
    for o in outline:
        title_lower = o["title"].lower()
        if any(w in title_lower for w in ["prelude", "introduction", "overview", "foreword", "preface"]):
            if intro_start is None:
                intro_start = o["page"]
    if intro_start is None:
        intro_start = 1
    anchors.append(("00", "Introduction / Prelude", intro_start))

    for o in outline:
        title = o["title"]
        m = re.match(r"^(?:Chapter\s+|Part\s+|Chapitre\s+)?([0-9]+)\s*[:\.\-]\s*(.*)$", title, re.IGNORECASE)
        if m:
            ch_num = int(m.group(1))
            ch_prefix = f"{ch_num:02d}"
            anchors.append((ch_prefix, title, o["page"]))

    # Fallback when outline has no numbered chapters or there is only a single Markdown file
    if (len(anchors) <= 1 or len(md_files) == 1) and md_files:
        anchors = []
        for idx, f in enumerate(md_files):
            prefix = f.name[:2] if f.name[:2].isdigit() else f"{idx:02d}"
            anchors.append((prefix, f.stem, 1))

    chapter_audits = []
    total_md_words = 0
    total_images_found = 0
    has_critical_failure = False

    min_ratio = getattr(args, "min_ratio", 0.95)

    for idx, anc in enumerate(anchors):
        ch_num = anc[0]
        ch_title = anc[1]
        p_start = anc[2]
        p_end = anchors[idx + 1][2] - 1 if idx + 1 < len(anchors) else total_pdf_pages

        subs = [o["title"] for o in outline if p_start <= o["page"] <= p_end and o["title"] != ch_title]
        src_words = sum(len(pages_text[p - 1].split()) for p in range(p_start, min(p_end, total_pdf_pages) + 1))

        matching_md = None
        for f in md_files:
            if f.name.startswith(f"{ch_num}_") or f.name == f"{ch_num}.md" or (len(md_files) == 1 and len(anchors) == 1):
                matching_md = f
                break

        md_words = 0
        img_refs = []
        md_headings = []
        file_present = matching_md is not None

        if matching_md:
            text = matching_md.read_text(encoding="utf-8")
            md_words = len(text.split())
            total_md_words += md_words
            img_refs = re.findall(r"!\[.*?\]\((.*?)\)", text)
            total_images_found += len(img_refs)
            md_headings = [line.lstrip("#").strip() for line in text.splitlines() if line.strip().startswith("#")]

        ratio = (md_words / src_words) if src_words > 0 else 1.0

        if not file_present:
            status = "CRITIQUE (Fichier Manquant)"
            badge = "🔴 MANQUANT"
            has_critical_failure = True
        elif ratio < 0.80:
            status = "CRITIQUE (Fortement Tronqué / Résumé)"
            badge = "🔴 COUPÉ"
            has_critical_failure = True
        elif ratio < min_ratio:
            status = "ATTENTION (Condensé ou Résumé Partiel)"
            badge = "🟡 CONDENSÉ"
        elif ratio > 1.60:
            status = "ATTENTION (Volume Anormalement Élevé)"
            badge = "🟡 VOLUMINEUX"
        else:
            status = "CONFORME (Conversion Intégrale Respectée)"
            badge = "🟢 CONFORME"

        chapter_audits.append(
            {
                "chapter_num": ch_num,
                "title": ch_title,
                "file": matching_md.name if matching_md else None,
                "page_range": f"p.{p_start}-{p_end}",
                "source_words": src_words,
                "markdown_words": md_words,
                "ratio": round(ratio, 2),
                "status": status,
                "badge": badge,
                "images_count": len(img_refs),
                "source_subheadings_count": len(subs),
                "source_subheadings": subs,
                "markdown_headings": md_headings,
            }
        )

    global_ratio = (total_md_words / total_src_words) if total_src_words > 0 else 1.0
    if global_ratio < 0.85:
        global_status = "🔴 ÉCHEC GLOBAL : Le document Markdown est sensiblement tronqué par rapport au PDF."
    elif global_ratio < min_ratio:
        global_status = f"🟡 ATTENTION GLOBALE : Le volume Markdown ({global_ratio:.2f}x) est inférieur au seuil ({min_ratio:.2f}x)."
    else:
        global_status = "🟢 CONFORME GLOBAL : Le volume Markdown correspond à une conversion intégrale rigoureuse."

    print("=" * 80)
    print(" AUDIT D'INTÉGRITÉ ET DE COMPLÉTUDE PDF -> MARKDOWN")
    print("=" * 80)
    print(f"Document source : {pdf_path.name} ({total_pdf_pages} pages, {total_src_words:,} mots)")
    print(f"Dossier cible   : {chapters_dir.name} ({len(md_files)} fichier(s), {total_md_words:,} mots)")
    print(f"Ratio global    : {global_ratio:.2f}x (Seuil minimal attendu : {min_ratio:.2f}x)")
    print(f"Statut global   : {global_status}")
    print("-" * 80)

    header = f"{'CH':<4} | {'TITRE':<30} | {'SRC':<7} | {'MD':<7} | {'RATIO':<6} | {'IMAGES':<6} | {'STATUT'}"
    print(header)
    print("-" * 80)
    for c in chapter_audits:
        title_disp = (c["title"][:27] + "...") if len(c["title"]) > 30 else c["title"]
        row = (
            f"{c['chapter_num']:<4} | {title_disp:<30} | {c['source_words']:<7} | "
            f"{c['markdown_words']:<7} | {c['ratio']:<6.2f} | {c['images_count']:<6} | {c['badge']}"
        )
        print(row)
    print("-" * 80)
    print(f"Images référencées : {total_images_found}")
    print("=" * 80)

    report_json = pathlib.Path(args.report_json).resolve() if args.report_json else chapters_dir / "audit_report.json"
    audit_data = {
        "source_pdf": str(pdf_path),
        "total_source_pages": total_pdf_pages,
        "total_source_words": total_src_words,
        "total_markdown_words": total_md_words,
        "global_ratio": round(global_ratio, 2),
        "min_required_ratio": min_ratio,
        "global_status": global_status,
        "total_images": total_images_found,
        "has_critical_failure": has_critical_failure,
        "chapters": chapter_audits,
    }
    report_json.write_text(json.dumps(audit_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Rapport JSON enregistré : '{report_json}'")

    report_md = (
        pathlib.Path(args.report_md).resolve()
        if args.report_md
        else chapters_dir / "00_RAPPORT_AUDIT_COMPLETUDE.md"
    )
    md_lines = [
        "# Rapport d'Audit de Complétude PDF → Markdown",
        "",
        f"> **Document source :** `{pdf_path.name}` ({total_pdf_pages} pages, {total_src_words:,} mots)  ",
        f"> **Markdown généré :** {total_md_words:,} mots  ",
        f"> **Ratio global :** **{global_ratio:.2f}x** (Seuil attendu : ≥ {min_ratio:.2f}x)  ",
        f"> **Verdict global :** {global_status}",
        "",
        "---",
        "",
        "## Tableau Récapitulatif",
        "",
        "| Section | Titre Source | Pages | Mots Source | Mots MD | Ratio | Images | Évaluation |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for c in chapter_audits:
        md_lines.append(
            f"| **{c['chapter_num']}** | {c['title']} | {c['page_range']} | {c['source_words']:,} | "
            f"{c['markdown_words']:,} | **{c['ratio']:.2f}** | {c['images_count']} | {c['badge']} |"
        )
    md_lines.extend(["", "---", "", "## Diagnostic Détaillé", ""])
    for c in chapter_audits:
        if c["badge"].startswith("🔴") or c["badge"].startswith("🟡"):
            md_lines.append(f"### Section {c['chapter_num']} : {c['title']} ({c['badge']})")
            md_lines.append(f"- **Fichier :** `{c['file']}`")
            if c["source_subheadings"]:
                md_lines.append("- **Sous-sections sources :**")
                for s in c["source_subheadings"]:
                    md_lines.append(f"  - `{s}`")
            md_lines.append("")

    report_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Rapport Markdown enregistré : '{report_md}'")

    if args.strict and has_critical_failure:
        sys.stderr.write("\n❌ ERREUR STRICTE : Des sections tronquées ou manquantes ont été détectées.\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Universal CLI pipeline for converting PDF documents to Markdown (pdf-to-markdown skill)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_ext = subparsers.add_parser("extract", help="Extract text and embedded images from source PDF.")
    p_ext.add_argument("--pdf", required=True, help="Path to source PDF file.")
    p_ext.add_argument("--out-dir", required=True, help="Directory to save book_text.txt, images/, and manifest.")
    p_ext.set_defaults(func=cmd_extract)

    p_aud = subparsers.add_parser(
        "audit", aliases=["verify", "check"], help="Audit completeness between source PDF and Markdown files."
    )
    p_aud.add_argument("--pdf", required=True, help="Path to source PDF file.")
    p_aud.add_argument("--chapters-dir", required=True, help="Directory containing generated .md files.")
    p_aud.add_argument("--min-ratio", type=float, default=0.95, help="Minimum acceptable word ratio (default: 0.95).")
    p_aud.add_argument("--strict", action="store_true", help="Fail with exit code 1 if any section is cut or missing.")
    p_aud.add_argument("--report-md", default=None, help="Custom output path for Markdown audit report.")
    p_aud.add_argument("--report-json", default=None, help="Custom output path for JSON audit report.")
    p_aud.set_defaults(func=cmd_audit)

    p_mrg = subparsers.add_parser("merge", help="Merge numbered Markdown chapters into a unified document.")
    p_mrg.add_argument("--chapters-dir", required=True, help="Directory containing numbered chapter .md files.")
    p_mrg.add_argument("--output", required=True, help="Path for the merged Markdown file.")
    p_mrg.add_argument("--title", required=True, help="Document title.")
    p_mrg.add_argument("--subtitle", default="", help="Document subtitle (optional).")
    p_mrg.add_argument("--author", default="", help="Document author name (optional).")
    p_mrg.set_defaults(func=cmd_merge)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
