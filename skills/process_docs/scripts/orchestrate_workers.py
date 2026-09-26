#!/usr/bin/env python3
"""Describe one image per isolated CLI session; retry a transient failure once."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import _config
from worker_backends import (AuthError, QuotaError, StartupError, BACKENDS,
                             PROTOCOL_VERSION, describe_image, find_cli, valid_description)

DESCRIPTION_REQUIREMENTS = """Transcribe all visible text without translating quotations.
Describe every diagram node, arrow direction, branch, label and meaningful color.
For tables, preserve every column heading and cell. For plots, include axes,
units, legends and visible values. Include relevant layout and UI field values.
Mark unreadable content explicitly; do not invent missing content."""


def requirements(cfg):
    language = "Chinese" if cfg.get("OUTPUT_LANGUAGE") == "zh-CN" else "English"
    return DESCRIPTION_REQUIREMENTS + f"\nWrite the explanation in {language}."


def output_is_valid(output_file):
    match = re.search(r"_page_(\d+)\.md$", str(output_file))
    try:
        path = Path(output_file)
        return bool(match and not path.is_symlink()
                    and valid_description(path.read_text(encoding="utf-8"), int(match[1])))
    except (OSError, UnicodeError):
        return False


def launch_worker(cfg, cli, image_path, output_file, summary, doc_dir, page_num, backend="claude"):
    return describe_image(cfg, backend, cli, image_path, output_file, summary,
                          page_num, requirements(cfg))


def _fingerprint(cfg, backend, image_path, summary=""):
    return {"protocol": PROTOCOL_VERSION, "backend": backend,
            "image_sha256": hashlib.sha256(Path(image_path).read_bytes()).hexdigest(),
            "model": cfg.get("WORKER_MODEL" if backend == "claude" else "CODEX_WORKER_MODEL"),
            "effort": cfg.get("CODEX_WORKER_REASONING_EFFORT") if backend == "codex" else None,
            "language": cfg.get("OUTPUT_LANGUAGE", "en"),
            "context_sha256": hashlib.sha256(summary.encode()).hexdigest(),
            "requirements_sha256": hashlib.sha256(requirements(cfg).encode()).hexdigest()}


def _records(doc_dir):
    try:
        data = json.loads((Path(doc_dir) / ".worker_results.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def page_output_path(doc_dir, page_num):
    return str(Path(doc_dir) / f".image_descriptions_page_{page_num}.md")


def write_json(path, value):
    path = Path(path)
    pending = path.with_name(path.name + ".partial")
    if path.is_symlink() or pending.is_symlink():
        raise ValueError("Worker artifacts must not be symlinks")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, path)


def validate_manifest(metadata, doc_dir, cfg):
    root = Path(doc_dir).resolve()
    if metadata.get("failed_images"):
        raise ValueError("Source extraction has failed images; resolve them before running workers")
    images = metadata.get("image_files")
    if not isinstance(images, list):
        raise ValueError("image_files must be a list")
    seen, result = set(), []
    for entry in images:
        if not isinstance(entry, dict) or type(entry.get("page")) is not int or entry["page"] < 1:
            raise ValueError("Image page identifiers must be positive integers")
        if entry["page"] in seen:
            raise ValueError("Duplicate page identifier in image manifest")
        seen.add(entry["page"])
        path = Path(entry["path"])
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(root):
            raise ValueError("Image path leaves the extraction directory")
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"):
            raise ValueError("Image manifest contains an unsupported image type")
        result.append({**entry, "path": str(path)})
    return result


def process_page(cfg, cli, image_path, page_num, doc_dir, summary, force=False, backend="claude"):
    """Describe one image. Return a page -> success/error mapping."""
    output_file = page_output_path(doc_dir, page_num)
    path = Path(image_path)
    if not path.is_file():
        return {page_num: {"error": "image file does not exist", "path": str(path)}}
    size = path.stat().st_size
    # Small icons can be valid; zero-byte or oversized inputs are rejected.
    if size == 0 or size > cfg.get("MAX_IMAGE_MB", 8) * 1024 * 1024:
        return {page_num: {"error": f"image size is invalid ({size} bytes)", "path": str(path)}}
    import pymupdf
    try:
        pix = pymupdf.Pixmap(str(path))
        if pix.width < 1 or pix.height < 1:
            raise ValueError("Image has no pixels")
        del pix
    except Exception as exc:  # native image-decoder exception types vary by release
        return {page_num: {"error": f"image cannot be decoded: {exc}", "path": str(path)}}
    identity = _fingerprint(cfg, backend, image_path, summary)
    records = _records(doc_dir)
    if not force and output_is_valid(output_file):
        current_hash = hashlib.sha256(Path(output_file).read_bytes()).hexdigest()
        if records.get(str(page_num)) == {**identity, "output_sha256": current_hash}:
            print(f"Page {page_num}: cached ({backend})")
            return {page_num: True}
    for attempt in (1, 2):
        print(f"Page {page_num}: {backend}, attempt {attempt}/2", flush=True)
        success, error = launch_worker(cfg, cli, image_path, output_file,
                                       summary, doc_dir, page_num, backend)
        if success:
            identity["output_sha256"] = hashlib.sha256(Path(output_file).read_bytes()).hexdigest()
            records[str(page_num)] = identity
            write_json(Path(doc_dir) / ".worker_results.json", records)
            return {page_num: True}
        print(f"  Failed: {error}", flush=True)
    return {page_num: {"error": error, "path": str(path)}}


def merge_descriptions(doc_dir, results, total_pages):
    sections, missing = [], []
    for page in sorted(p for p, value in results.items() if value is True):
        path = page_output_path(doc_dir, page)
        if output_is_valid(path):
            sections.append(Path(path).read_text(encoding="utf-8").strip())
        else:
            missing.append(page)
    text = "# Image descriptions\n\n" + "\n\n---\n\n".join(sections)
    text += f"\n\n<!-- Source pages: {total_pages}; described images: {len(sections)}/{len(results)} -->\n"
    path = Path(doc_dir) / ".image_descriptions.md"
    if path.is_symlink():
        raise ValueError("Merged description must not be a symlink")
    path.write_text(text, encoding="utf-8")
    if missing:
        print(f"Missing or invalid description files: {missing}")
    return not missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc_dir")
    parser.add_argument("--backend", choices=BACKENDS, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    doc = Path(args.doc_dir).resolve()
    results = {}
    try:
        cfg = _config.load()
        metadata = json.loads((doc / ".extraction_metadata.json").read_text(encoding="utf-8"))
        images = validate_manifest(metadata, doc, cfg)
        cli = find_cli(cfg, args.backend) if images else None
        if images and not cli:
            raise ValueError(f"{args.backend} CLI not found; configure {args.backend.upper()}_CLI")
        for image in images:
            results.update(process_page(cfg, cli, image["path"], image["page"], str(doc),
                                        metadata.get("summary", ""), args.force, args.backend))
        clean = merge_descriptions(doc, results, metadata.get("total_pages", len(images)))
        failed = [{"page": p, **v} for p, v in results.items() if isinstance(v, dict)]
        failure = doc / ".extraction_failed.json"
        if failed or not clean:
            write_json(failure, {"backend": args.backend, "failed_images": failed, "merge_ok": clean})
            return 1
        failure.unlink(missing_ok=True)
        print(f"Described {len(images)}/{len(images)} images.")
        return 0
    except (AuthError, QuotaError, StartupError, OSError, ValueError, KeyError) as exc:
        if doc.is_dir():
            write_json(doc / ".extraction_failed.json",
                       {"backend": args.backend, "aborted": type(exc).__name__, "error": str(exc)})
        print(f"Worker run stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
