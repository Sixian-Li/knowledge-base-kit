#!/usr/bin/env python3
"""
PDF Pre-extraction Script

Extracts text and renders page images from a PDF. Runs in the MAIN session but
makes zero LLM calls — that is the whole point. The rendered images are written
to disk and never read here; describing them is the worker sessions' job
(orchestrate_workers.py).

Outputs:
  - .extracted_content.md      (all text, page-by-page, with tables)
  - images/page_N.png          (rendered pages at 150 DPI)
  - .extraction_metadata.json  (page count, image list, summary)

Usage:
  python extract_pdf.py <pdf_path> <output_dir>
"""

import sys
import os
import json
import re

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config


def extract_text(doc, output_dir):
    """Extract all text from the PDF, page by page, including tables."""
    text_file = os.path.join(output_dir, ".extracted_content.md")
    full_text = ""

    for i, page in enumerate(doc):
        full_text += f"\n--- Page {i + 1} ---\n\n"
        full_text += page.get_text()

        tables = page.find_tables()
        if tables:
            for table in tables:
                full_text += "\n[Table]\n"
                for row in table.extract():
                    full_text += " | ".join(str(cell) if cell is not None else "" for cell in row) + "\n"
                full_text += "\n"

    with open(text_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    return text_file, full_text


def page_is_visual(page):
    """Whether a page carries visual content a worker should describe.

    `get_images()` alone is not enough: flowcharts and diagrams in PDFs are
    frequently drawn as vector paths, which carry no embedded image. The
    drawing-count threshold catches those while ignoring pages whose only
    "drawings" are rules and table borders.
    """
    if page.get_images():
        return True
    try:
        return len(page.get_drawings()) > 12
    except Exception:
        return True  # when in doubt, render it


def render_page_images(doc, output_dir, render_all=True):
    """Render pages as PNG at 150 DPI. Stored only — never read here."""
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    image_files = []
    skipped = []

    for i in range(len(doc)):
        page = doc[i]
        if not render_all and not page_is_visual(page):
            skipped.append(i + 1)
            continue
        pix = page.get_pixmap(dpi=150)
        img_path = os.path.join(images_dir, f"page_{i + 1}.png")
        pix.save(img_path)
        image_files.append({
            "page": i + 1,
            "path": img_path.replace("\\", "/"),  # normalize for cross-platform joins
            "size": os.path.getsize(img_path),
        })

    return image_files, skipped


def generate_summary(full_text, doc_metadata):
    """Generate a brief summary (tens of words) used to prime worker sessions."""
    title = (doc_metadata.get("title") or "").strip()
    subject = (doc_metadata.get("subject") or "").strip()

    if title:
        summary = title
        if subject:
            summary += f"。{subject}"
        return summary[:200]

    lines = full_text.strip().split("\n")
    title_lines = []
    for line in lines[:10]:
        line = line.strip()
        if not line or line.startswith("--- Page"):
            continue
        if len(line) < 100:
            title_lines.append(line)
            if len(" ".join(title_lines)) > 60:
                break
        else:
            break

    if title_lines:
        return " ".join(title_lines)[:200]

    text_preview = full_text[:500].strip()
    text_preview = re.sub(r"^#+\s+.*$", "", text_preview, flags=re.MULTILINE)
    text_preview = re.sub(r"```.*?```", "", text_preview, flags=re.DOTALL)
    text_preview = re.sub(r"--- Page \d+ ---", "", text_preview).strip()

    if len(text_preview) < 20:
        return "Source has too little text for a preview."

    for sep in ["。", ".", "\n"]:
        idx = text_preview.find(sep)
        if idx != -1 and idx < 150:
            return text_preview[:idx + 1].strip()[:200]

    return text_preview[:100].strip()


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_pdf.py <pdf_path> <output_dir>")
        sys.exit(1)

    pdf_path, output_dir = sys.argv[1], sys.argv[2]

    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    cfg = _config.load()
    render_all = bool(cfg.get("RENDER_ALL_PAGES", True))

    os.makedirs(output_dir, exist_ok=True)

    print(f"Opening PDF: {pdf_path}")
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")

    print("Extracting text...")
    text_file, full_text = extract_text(doc, output_dir)
    print(f"  -> {text_file} ({len(full_text)} chars)")

    mode = "all pages" if render_all else "visual pages only"
    print(f"Rendering page images at 150 DPI ({mode})...")
    image_files, skipped = render_page_images(doc, output_dir, render_all)
    print(f"  -> {len(image_files)} images rendered")
    if skipped:
        print(f"  -> {len(skipped)} text-only pages skipped: {skipped}")

    print("Generating summary...")
    summary = generate_summary(full_text, doc.metadata)
    print(f"  -> {summary[:80]}...")

    metadata = {
        "total_pages": total_pages,
        "image_files": image_files,
        "skipped_pages": skipped,
        "render_all_pages": render_all,
        "summary": summary,
        "text_file": text_file,
        "text_chars": len(full_text),
        "shard_threshold": cfg.get("SHARD_THRESHOLD", 30000),
        "needs_sharding": len(full_text) > int(cfg.get("SHARD_THRESHOLD", 30000)),
    }

    metadata_file = os.path.join(output_dir, ".extraction_metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"  -> {metadata_file}")

    if metadata["needs_sharding"]:
        print(f"  !! {len(full_text)} chars exceeds shard threshold "
              f"{metadata['shard_threshold']} — shard at section boundaries in Stage 1")

    doc.close()
    print("Done.")


if __name__ == "__main__":
    main()
