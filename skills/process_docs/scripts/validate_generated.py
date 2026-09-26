#!/usr/bin/env python3
"""Read-only checks for a generated document, before and after filing.

Usage: validate_generated.py DOC_DIR [--target CATEGORY/DOC] [--filed]
Without a target, unresolved ../ links are deferred until classification. With a
target, links resolve against both the draft tree and its intended final location.
This checks the template contract, not factual completeness or reading time.
"""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from _config import load

REQUIRED = ("source", "format", "converted", "category", "description", "doc_type")
FULL_HEADINGS = ("Table of Contents", "Related Documents")
SUMMARY_HEADINGS = ("Overview", "Prerequisites", "Key Steps", "Configuration Reference",
                    "Common Pitfalls", "References")
LINK = re.compile(r'!?\[[^\]\n]*\]\((<[^>\n]+>|(?:\\.|[^\s\\()]|\([^()\n]*\))+)(?:\s+["\'][^\n]*?["\'])?\)')


def without_code(text):
    lines, fence = [], None
    for line in text.splitlines():
        candidate = re.sub(r"^(?:\s{0,3}>\s?)+", "", line)
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", candidate)
        if match:
            if fence is None:
                fence = match[1]
            elif match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
            lines.append("")
        elif fence is None:
            lines.append(line)
    return "\n".join(lines)


def scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return json.loads(value) if value[0] == '"' else value[1:-1].replace("''", "'")
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def frontmatter(text):
    """Read the template's scalar fields and simple children list; no YAML dependency."""
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    if not match:
        raise ValueError("full.md has no valid frontmatter")
    data, key = {}, None
    for line in match[1].splitlines():
        field = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if field:
            key, value = field.groups()
            if key in data:
                raise ValueError("Duplicate frontmatter field: " + key)
            if key == "children":
                data[key] = ([scalar(x) for x in value.strip()[1:-1].split(",") if x.strip()]
                             if value.strip().startswith("[") and value.strip().endswith("]") else [])
            else:
                data[key] = scalar(value)
        elif key == "children" and re.match(r"^\s*-\s+", line):
            data[key].append(scalar(re.sub(r"^\s*-\s+", "", line)))
    return data


def anchors(text):
    result, counts = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", without_code(text), re.M):
        heading = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", heading)
        base = re.sub(r"[^\w\s-]", "", heading.lower()).strip().replace(" ", "-")
        count = counts.get(base, 0)
        result.add(base if not count else f"{base}-{count}")
        counts[base] = count + 1
    return result


def archive_blocks(text):
    """Return (start, end, folded) for actual text fences, not fence examples.

    Line indexes are zero based; an unclosed fence has end=None. Details tags
    inside a code fence are literal content and cannot satisfy the folding gate.
    """
    result, fence, depth = [], None, 0
    for i, line in enumerate(text.split("\n")):
        if fence:
            marker, start, archive, folded = fence
            if re.fullmatch(r"\s{0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*", line):
                if archive:
                    result.append((start, i, folded))
                fence = None
            continue
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if match:
            fence = (match[1], i, match[2].strip() == "text", depth > 0)
            continue
        for tag in re.findall(r"</?details\b[^>]*>", line, re.I):
            depth = max(0, depth - 1) if tag.startswith("</") else depth + 1
    if fence and fence[2]:
        result.append((fence[1], None, fence[3]))
    return result


def unfolded_archives(text):
    return [start + 1 for start, end, folded in archive_blocks(text) if not folded or end is None]


def tex_spans(path):
    """Every math span in the file, as pandoc's markdown reader sees them.

    pandoc decides what *is* math by the same rules a reader applies, so fenced
    blocks, inline code and bare currency ("$45") are excluded. Do not replace
    this with a local regex — telling math from those three is the whole job.
    """
    proc = subprocess.run(["pandoc", "-f", "markdown", "-t", "json", str(path)],
                          capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError("pandoc: " + proc.stderr.strip()[:200])
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("t") == "Math":
                found.append(node["c"][1])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads(proc.stdout))
    return found


def tex_render_errors(path):
    """Render-check the file's TeX. Returns (bad, checked_count, skip_reason).

    Pandoc identifies spans; the pinned KaTeX engine checks supported syntax.
    This is a local compatibility check, not a promise about every viewer.
    """
    script = Path(__file__).resolve().parent / "check_tex.js"
    if not shutil.which("pandoc"):
        return [], 0, "pandoc not found"
    if not shutil.which("node") or not script.is_file():
        return [], 0, "node or check_tex.js not found"
    try:
        spans = tex_spans(path)
        if not spans:
            return [], 0, None
        proc = subprocess.run(["node", str(script)], input=json.dumps(spans),
                              capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            return [], 0, "check_tex.js: " + proc.stderr.strip()[:200]
        bad = json.loads(proc.stdout)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return [], 0, str(exc)[:200]
    return [f"{b['tex']} -> {b['error']}" for b in bad], len(spans), None


def check(doc_dir, cfg=None, target=None, filed=False):
    cfg = cfg or load()
    doc = Path(doc_dir).resolve()
    root = Path(cfg["KB_ROOT"]).resolve()
    errors, deferred, unchecked, tex_checked = [], [], [], {}
    texts = {}
    for name in ("full.md", "summary.md"):
        try:
            texts[name] = (doc / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{name}: {exc}")
    if len(texts) != 2:
        return {"ok": False, "errors": errors, "deferred_links": deferred,
                "unchecked": unchecked}
    try:
        meta = frontmatter(texts["full.md"])
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)], "deferred_links": deferred,
                "unchecked": unchecked}
    for field in REQUIRED:
        if not meta.get(field):
            errors.append("Missing frontmatter: " + field)
    category = str(meta.get("category", ""))
    parts = category.split("/")
    if not all(re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", p) for p in parts):
        errors.append("Invalid category path")
    if len(parts) > int(cfg["MAX_CATEGORY_DEPTH"]):
        errors.append("Category exceeds MAX_CATEGORY_DEPTH")
    try:
        date.fromisoformat(str(meta.get("converted", "")))
    except ValueError:
        errors.append("converted must be YYYY-MM-DD")
    template = (Path(__file__).resolve().parent.parent / "references/generation-templates.md").read_text()
    formats = re.search(r"^format: <([^>]+)>", template, re.M)
    if not formats or meta.get("format") not in formats[1].split("|"):
        errors.append("format is not a label in generation-templates.md")
    source = str(meta.get("source", ""))
    if not source or Path(source).name != source or "\\" in source:
        errors.append("source must preserve the original filename, without a path")
    if filed and not (doc / source).is_file():
        errors.append("Filed source attachment is missing")
    if (doc / "README.md").exists():
        errors.append("Document folder must not contain README.md")
    kind = meta.get("doc_type")
    if kind not in ("normal", "parent", "child"):
        errors.append("Invalid doc_type")
    if kind == "child" and not meta.get("parent"):
        errors.append("Child is missing parent")
    if kind == "parent":
        children = meta.get("children", [])
        if not isinstance(children, list) or not children:
            errors.append("Parent is missing children")
        else:
            for child in children:
                if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", child) or not (doc / child / "full.md").is_file():
                    errors.append("Missing or invalid child document: " + child)
    for name, required in (("full.md", FULL_HEADINGS), ("summary.md", SUMMARY_HEADINGS)):
        body = without_code(texts[name])
        for heading in required:
            if len(re.findall(r"^## " + re.escape(heading) + r"\s*$", body, re.M)) != 1:
                errors.append(f"{name}: expected one '## {heading}'")
        if "KBKIT_FALLBACK_OUTPUT" in texts[name]:
            errors.append(name + ": fallback output cannot be filed")
        bad_tex, span_count, skip = tex_render_errors(doc / name)
        for formula in bad_tex:
            errors.append(f"{name}: TeX does not render: {formula}")
        if skip:
            unchecked.append(f"{name}: TeX render check skipped ({skip})")
        else:
            tex_checked[name] = span_count
        for line_no in unfolded_archives(texts[name]):
            errors.append(f"{name}:{line_no}: ```text archive is not folded in <details>")
    final = doc if filed else (root / target).resolve() if target else None
    if final and not final.is_relative_to(root):
        errors.append("Target is outside KB_ROOT")
        final = None
    if final:
        category_dir = (root / category).resolve()
        if not final.is_relative_to(category_dir) or final == category_dir:
            errors.append("Target does not match category")
        elif kind == "normal" and final.parent != category_dir:
            errors.append("Normal document is not directly inside its category")
        if meta.get("parent"):
            expected = category_dir / str(meta["parent"])
            if final.parent != expected.resolve() or not (doc.parent / "full.md").is_file():
                errors.append("parent does not match the immediate parent document")
    summary_links = []
    for name, text in texts.items():
        clean = re.sub(r"(`+).*?\1", "", without_code(text), flags=re.S)
        links = [m[1].strip("<>") for m in LINK.finditer(clean)]
        links += re.findall(r"^\[[^]]+\]:\s*<?([^>\s]+)>?", clean, re.M)
        for raw in links:
            url = urlsplit(raw)
            if url.scheme or url.netloc:
                continue
            rel = unquote(url.path)
            if name == "summary.md" and rel in ("full.md", "./full.md"):
                summary_links.append(raw)
            actual = (doc / rel).resolve() if rel else doc / name
            logical = (final / rel).resolve() if final and rel else actual
            if final and rel and not logical.is_relative_to(root):
                errors.append(f"{name}: link leaves KB_ROOT: {raw}")
                continue
            resolved = actual if actual.exists() else logical
            if not resolved.exists():
                if not final and rel.startswith("../"):
                    deferred.append(f"{name}: {raw}")
                else:
                    errors.append(f"{name}: missing link target: {raw}")
            elif url.fragment and resolved.suffix == ".md":
                if unquote(url.fragment) not in anchors(resolved.read_text(encoding="utf-8")):
                    errors.append(f"{name}: missing heading anchor: {raw}")
    if not summary_links:
        errors.append("summary.md must link to full.md")
    if not filed and (doc / ".extraction_metadata.json").exists():
        try:
            metadata = json.loads((doc / ".extraction_metadata.json").read_text())
            if metadata.get("failed_images"):
                errors.append("Source extraction contains failed images")
            expected = sorted(int(img["page"]) for img in metadata.get("image_files", []))
            if expected:
                merged = (doc / ".image_descriptions.md").read_text()
                present = sorted(map(int, re.findall(r"^##\s+Page\s+(\d+)\s*$", merged, re.M)))
                if expected != present:
                    errors.append("Image descriptions do not cover the image manifest exactly")
        except (OSError, ValueError, KeyError) as exc:
            errors.append("Image coverage check: " + str(exc))
    if not filed and (doc / ".extraction_failed.json").exists():
        errors.append("Extraction failure record remains; resolve before filing")
    return {"ok": not errors and not unchecked, "errors": errors, "deferred_links": deferred,
            "unchecked": unchecked, "tex_spans_checked": tex_checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc_dir")
    parser.add_argument("--target", help="intended KB-relative document path")
    parser.add_argument("--filed", action="store_true")
    args = parser.parse_args()
    result = check(args.doc_dir, target=args.target, filed=args.filed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
