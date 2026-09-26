#!/usr/bin/env python3
"""
Jupyter Notebook Pre-extraction Script

Flattens an .ipynb into Markdown. Runs in the MAIN session and makes zero LLM
calls, exactly like extract_pdf.py — the images it writes are never read here;
describing them is the worker sessions' job (orchestrate_workers.py).

Why a notebook needs a real extraction step at all, unlike .md/.txt:
a notebook is JSON, and the parts that matter most — what the code actually
printed, plotted and raised — live in each cell's `outputs` array as escaped
strings and base64 blobs. Copying the file verbatim would hand Stage 2 a wall
of JSON. This script is what turns it back into a readable document.

The key asymmetry against R Markdown: **a notebook carries its own outputs**.
Nothing here executes anything. If a notebook was saved with outputs cleared,
that is reported (`outputs_cleared`) rather than fixed — it means the source is
a half-finished document, the same shape as a bare .Rmd, and the user should
know before it is ingested.

Outputs:
  - .extracted_content.md      (cells in order: markdown, code, and their outputs)
  - images/nb_image_N.png      (base64 images decoded out of outputs/attachments)
  - .extraction_metadata.json  (cell counts, image list, summary)

The metadata deliberately mirrors extract_pdf.py's schema — `image_files` with
`page` keys and a matching `total_pages` — so orchestrate_workers.py consumes
it unmodified. For a notebook, "page N" means "the Nth extracted image", and
`image_files[i]["cell_index"]` says which cell it came out of.

Usage:
  python extract_notebook.py <ipynb_path> <output_dir>
"""

import base64
import binascii
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config

# Extensions by MIME type, for the image blobs pulled out of outputs.
IMAGE_MIMES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# Rendered in this order when an output carries several representations.
TEXT_MIMES = ("text/markdown", "text/latex", "text/plain", "text/html")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
TRIVIAL_REPR_RE = re.compile(r"^<[^\n>]*>$")
FRONTMATTER_RE = re.compile(r"^\s*---\s*\n.*?\n---\s*(\n|$)", re.DOTALL)
RULE_RE = re.compile(r"^([-*_=])\1{2,}$")


def as_text(value):
    """Notebook string fields are either a string or a list of lines."""
    if value is None:
        return ""
    if isinstance(value, list):
        return "".join(str(v) for v in value)
    return str(value)


def strip_ansi(text):
    """Tracebacks are stored with the terminal colour codes still in them."""
    return ANSI_RE.sub("", text)


def load_cells(nb):
    """Return the cell list for nbformat 4, or flatten nbformat 3 worksheets."""
    if isinstance(nb.get("cells"), list):
        return nb["cells"]
    cells = []
    for sheet in nb.get("worksheets") or []:
        cells.extend(sheet.get("cells") or [])
    return cells


def language_of(nb):
    """Best-effort source language, used for the code fence info string."""
    meta = nb.get("metadata") or {}
    info = meta.get("language_info") or {}
    name = info.get("name") or (meta.get("kernelspec") or {}).get("language")
    return (name or "python").lower()


class ImageSink:
    """Decodes base64 image blobs to disk and numbers them like PDF pages."""

    def __init__(self, output_dir):
        self.dir = os.path.join(output_dir, "images")
        os.makedirs(self.dir, exist_ok=True)
        self.files = []
        self.failed = []

    def add(self, mime, payload, cell_index, origin):
        ext = IMAGE_MIMES[mime]
        index = len(self.files) + 1
        path = os.path.join(self.dir, f"nb_image_{index}{ext}")
        try:
            blob = base64.b64decode("".join(as_text(payload).split()), validate=True)
        except (binascii.Error, ValueError) as exc:
            self.failed.append({"cell_index": cell_index, "mime": mime,
                                "error": str(exc)})
            return None
        # A truncated blob would sail through the worker's own success checks and
        # come back as a polite "the image could not be read" paragraph, counted
        # as a success. Reject it here instead, before a session is spent on it.
        if not blob:
            self.failed.append({"cell_index": cell_index, "mime": mime,
                                "error": f"decoded to {len(blob)} bytes"})
            return None
        with open(path, "wb") as f:
            f.write(blob)
        self.files.append({
            "page": index,
            "path": path.replace("\\", "/"),
            "size": os.path.getsize(path),
            "cell_index": cell_index,
            "origin": origin,
            "mime": mime,
        })
        return index


def render_data_bundle(data, cell_index, sink, origin, out):
    """Render one MIME bundle (execute_result / display_data / attachment)."""
    wrote_image = False
    for mime, ext in IMAGE_MIMES.items():
        if mime in data:
            index = sink.add(mime, data[mime], cell_index, origin)
            if index is not None:
                out.append(f"> [Output image #{index} — see "
                           f".image_descriptions.md section `## Page {index}`]")
            else:
                out.append(f"> [Output image — decode failed; see "
                           f".extraction_metadata.json failed_images]")
            out.append("")
            wrote_image = True

    for mime in TEXT_MIMES:
        if mime not in data:
            continue
        text = as_text(data[mime]).rstrip()
        if not text:
            continue
        # matplotlib emits `<Figure size 640x480 with 1 Axes>` alongside the PNG.
        # Once the picture is out, that line is noise.
        if wrote_image and mime == "text/plain" and TRIVIAL_REPR_RE.match(text):
            continue
        if mime == "text/plain":
            out.append("```")
            out.append(text)
            out.append("```")
        elif mime == "text/html":
            out.append("```html")
            out.append(text)
            out.append("```")
        else:
            out.append(text)
        out.append("")
        # Only the richest available text form is kept; the rest are the same
        # value re-encoded. text/html is the exception — it is emitted only when
        # nothing plainer exists, because a styled DataFrame keeps information
        # (colour scales, spans) that its text/plain repr throws away.
        if mime != "text/html":
            break


def render_outputs(cell, cell_index, sink, out):
    """Render every output of one code cell, in order."""
    outputs = cell.get("outputs") or []
    for output in outputs:
        kind = output.get("output_type")

        if kind == "stream":
            name = output.get("name", "stdout")
            text = as_text(output.get("text")).rstrip()
            if not text:
                continue
            out.append(f"**Output ({name})**")
            out.append("")
            out.append("```")
            out.append(text)
            out.append("```")
            out.append("")

        elif kind in ("execute_result", "display_data"):
            data = output.get("data") or {}
            if not data:
                continue
            label = "Result" if kind == "execute_result" else "Display output"
            count = output.get("execution_count")
            suffix = f" [{count}]" if count else ""
            out.append(f"**{label}{suffix}**")
            out.append("")
            render_data_bundle(data, cell_index, sink, kind, out)

        elif kind == "error":
            ename = output.get("ename", "Error")
            evalue = as_text(output.get("evalue"))
            traceback = strip_ansi("\n".join(
                as_text(line) for line in (output.get("traceback") or [])))
            out.append(f"**Error: {ename}: {evalue}**")
            out.append("")
            if traceback.strip():
                out.append("```")
                out.append(traceback.rstrip())
                out.append("```")
            out.append("")

        elif kind == "pyout" or kind == "pyerr":
            # nbformat 3 spelling; the payload sits directly on the output dict.
            data = {k: v for k, v in output.items()
                    if k in IMAGE_MIMES or k in ("text", "html", "latex")}
            remapped = {}
            for key, value in data.items():
                mime = {"text": "text/plain", "html": "text/html",
                        "latex": "text/latex"}.get(key, key)
                remapped[mime] = value
            if remapped:
                out.append("**Result**")
                out.append("")
                render_data_bundle(remapped, cell_index, sink, kind, out)


def render_attachments(cell, cell_index, sink, out):
    """Markdown cells can carry pasted images under `attachments`."""
    attachments = cell.get("attachments") or {}
    for name, bundle in attachments.items():
        if not isinstance(bundle, dict):
            continue
        out.append(f"**Attachment: {name}**")
        out.append("")
        render_data_bundle(bundle, cell_index, sink, "attachment", out)


def extract(nb, output_dir):
    """Walk the notebook and build .extracted_content.md."""
    cells = load_cells(nb)
    lang = language_of(nb)
    sink = ImageSink(output_dir)

    out = []
    counts = {"markdown": 0, "code": 0, "raw": 0, "other": 0}
    executed = 0
    empty_code = 0

    for i, cell in enumerate(cells):
        kind = cell.get("cell_type", "other")
        source = as_text(cell.get("source") or cell.get("input"))

        if kind == "markdown":
            counts["markdown"] += 1
            if source.strip():
                out.append(source.rstrip())
                out.append("")
            render_attachments(cell, i, sink, out)

        elif kind == "code":
            counts["code"] += 1
            count = cell.get("execution_count") or cell.get("prompt_number")
            if count:
                executed += 1
            label = f"In [{count}]" if count else "In [ ]"
            out.append(f"**{label}**")
            out.append("")
            out.append(f"```{lang}")
            out.append(source.rstrip())
            out.append("```")
            out.append("")
            before = len(out)
            render_outputs(cell, i, sink, out)
            if len(out) == before:
                empty_code += 1

        elif kind == "raw":
            counts["raw"] += 1
            if source.strip():
                out.append("```")
                out.append(source.rstrip())
                out.append("```")
                out.append("")

        elif kind == "heading":
            # nbformat 3 had a dedicated heading cell type with a `level`
            # field; v4 folded these into markdown. Rebuild the hashes so the
            # document keeps its outline.
            counts["markdown"] += 1
            if source.strip():
                level = min(int(cell.get("level") or 1), 6)
                out.append(f"{'#' * level} {source.strip()}")
                out.append("")

        else:
            counts["other"] += 1
            if source.strip():
                out.append(source.rstrip())
                out.append("")

    text = "\n".join(out).rstrip() + "\n"
    text_file = os.path.join(output_dir, ".extracted_content.md")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(text)

    stats = {
        "cell_counts": counts,
        "executed_cells": executed,
        "code_cells_without_output": empty_code,
        # True when the notebook was saved with Cell > All Output > Clear, or was
        # simply never run. Then this file is source only — the same shape as a
        # bare .Rmd — and full.md must say so.
        #
        # Keyed off the outputs themselves, never off execution_count: notebooks
        # saved by VS Code and by nbconvert routinely carry full outputs with
        # every execution_count still null. Output presence is the evidence.
        "outputs_cleared": (counts["code"] > 0
                            and empty_code == counts["code"]),
        "language": lang,
        "kernel": ((nb.get("metadata") or {}).get("kernelspec") or {}).get(
            "display_name", ""),
        "nbformat": nb.get("nbformat"),
    }
    return text_file, text, sink, stats


def generate_summary(nb, text, fallback):
    """A short summary used only to prime the worker sessions."""
    for cell in load_cells(nb):
        if cell.get("cell_type") not in ("markdown", "heading"):
            continue
        # Quarto and Jupyter Book put a YAML frontmatter cell first; without
        # stripping it the summary comes out as a literal "---".
        source = FRONTMATTER_RE.sub("", as_text(cell.get("source")), count=1)
        for line in source.splitlines():
            line = line.strip()
            if not line or RULE_RE.match(line):
                continue
            if line.startswith("#"):
                return line.lstrip("#").strip()[:200]
            return line[:200]
    preview = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()
    preview = re.sub(r"\*\*.*?\*\*", "", preview).strip()
    preview = re.sub(r"^#+\s*", "", preview).strip()
    return (preview[:150] or fallback)[:200]


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_notebook.py <ipynb_path> <output_dir>")
        sys.exit(1)

    nb_path, output_dir = sys.argv[1], sys.argv[2]

    if not os.path.exists(nb_path):
        print(f"Error: notebook not found: {nb_path}")
        sys.exit(1)

    cfg = _config.load()
    os.makedirs(output_dir, exist_ok=True)

    print(f"Opening notebook: {nb_path}")
    try:
        with open(nb_path, encoding="utf-8") as f:
            nb = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"Error: not a readable .ipynb ({exc})")
        sys.exit(1)

    if not load_cells(nb):
        print("Error: no cells found — is this really a notebook?")
        sys.exit(1)

    text_file, text, sink, stats = extract(nb, output_dir)
    counts = stats["cell_counts"]
    print(f"Cells: {counts['markdown']} markdown, {counts['code']} code, "
          f"{counts['raw']} raw")
    print(f"  -> {text_file} ({len(text)} chars)")
    print(f"  -> {len(sink.files)} images decoded")
    if sink.failed:
        print(f"  !! {len(sink.failed)} image blobs failed to decode")

    if stats["outputs_cleared"]:
        print("  !! outputs are CLEARED — this notebook was never run, or was "
              "saved after clearing. full.md must state that results are absent.")
    elif stats["code_cells_without_output"]:
        print(f"  -> {stats['code_cells_without_output']} code cells produced "
              f"no output")

    summary = generate_summary(nb, text, os.path.basename(nb_path))
    print(f"Summary: {summary[:80]}")

    threshold = int(cfg.get("SHARD_THRESHOLD", 30000))
    metadata = {
        "source_format": "ipynb",
        # Named for extract_pdf.py's schema so orchestrate_workers.py needs no
        # change: here a "page" is one extracted image, not a page of paper.
        "total_pages": len(sink.files),
        "image_files": sink.files,
        "failed_images": sink.failed,
        "skipped_pages": [],
        "summary": summary,
        "text_file": text_file,
        "text_chars": len(text),
        "shard_threshold": threshold,
        "needs_sharding": len(text) > threshold,
    }
    metadata.update(stats)

    metadata_file = os.path.join(output_dir, ".extraction_metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"  -> {metadata_file}")

    if metadata["needs_sharding"]:
        print(f"  !! {len(text)} chars exceeds shard threshold {threshold} — "
              f"shard at section boundaries in Stage 1")

    print("Done.")


if __name__ == "__main__":
    main()
