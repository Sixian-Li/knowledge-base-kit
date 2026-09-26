#!/usr/bin/env python3
"""Extract supported documents into a fresh scratch directory. Never calls a model."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from _config import load, supported_exts


def extract(source, output, cfg):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_file():
        raise ValueError("Source file does not exist")
    ext = source.suffix.lower()
    if ext not in supported_exts(cfg):
        raise ValueError(f"Unsupported format: {ext}")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Extraction requires a new or empty directory; preserve the previous attempt")
    output.mkdir(parents=True, exist_ok=True)
    meta = {"source_format": ext[1:], "source": source.name,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "image_files": [], "failed_images": [], "warnings": [], "skipped_pages": []}
    if ext == ".pdf":
        import pymupdf
        from extract_pdf import extract_text, render_page_images, generate_summary
        with pymupdf.open(source) as doc:
            if doc.needs_pass:
                raise ValueError("Encrypted PDF needs an authorized decrypted copy")
            _, text = extract_text(doc, str(output))
            images, skipped = render_page_images(doc, str(output), cfg["RENDER_ALL_PAGES"])
            meta.update(image_files=images, skipped_pages=skipped, total_pages=len(doc),
                        summary=generate_summary(text, doc.metadata))
            if skipped:
                meta["warnings"].append("Selective rendering can miss visuals; review every skipped page.")
    elif ext == ".ipynb":
        from extract_notebook import extract as notebook, load_cells
        nb = json.loads(source.read_text(encoding="utf-8"))
        if not load_cells(nb):
            raise ValueError("Notebook contains no cells")
        _, text, sink, stats = notebook(nb, str(output))
        meta.update(image_files=sink.files, failed_images=sink.failed, notebook=stats)
        if stats["outputs_cleared"]:
            meta["warnings"].append("Notebook has no saved outputs; do not infer results or execute it automatically.")
    elif ext in (".docx", ".html", ".htm"):
        if ext == ".docx":
            from extract_docx import extract as loader
        else:
            from extract_html import extract as loader
        result = loader(source, output)
        text = result.pop("text")
        meta.update(result)
    elif ext in (".md", ".txt", ".rmd"):
        text = source.read_text(encoding="utf-8")
        if ext == ".rmd":
            meta["warnings"].append("Rmd source only. Reuse a saved render or obtain explicit permission before executing R.")
    else:
        path = output / "images" / ("image_1" + ext)
        path.parent.mkdir()
        shutil.copyfile(source, path)
        text = f"![Image 1](images/{path.name})\n"
        meta["image_files"] = [{"page": 1, "path": str(path), "size": path.stat().st_size}]
    text_file = output / ".extracted_content.md"
    text_file.write_text(text, encoding="utf-8")
    meta.setdefault("total_pages", len(meta["image_files"]))
    meta.setdefault("summary", text[:200])
    meta.update(text_file=str(text_file), text_chars=len(text), shard_threshold=cfg["SHARD_THRESHOLD"],
                needs_sharding=len(text) > cfg["SHARD_THRESHOLD"])
    (output / ".extraction_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if meta["failed_images"]:
        (output / ".extraction_failed.json").write_text(json.dumps({"failed_images": meta["failed_images"]}, indent=2), encoding="utf-8")
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    try:
        result = extract(args.source, args.output, load())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["failed_images"] else 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Extraction failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
