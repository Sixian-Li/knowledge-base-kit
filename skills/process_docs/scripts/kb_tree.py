#!/usr/bin/env python3
"""
Walk the knowledge base and report its category tree, document counts and
structural violations.

Why this is a script and not something the agent eyeballs: once categories can
nest, the catalog stats line (`📊 N documents | M categories`) and the
per-category health check stop being countable by hand — and that stats line has
already drifted silently for weeks at a time. Stage 4 (show the tree), Stage 5
(health), Stage 6 (stats line) and `--check` all read their numbers from here so
they cannot disagree with each other.

The load-bearing invariant, used to tell the two kinds of folder apart:

    category folder  ->  has README.md, no full.md
    document folder  ->  has full.md (+ summary.md), no README.md

A category may hold documents and subcategories at the same time. A document
folder's subfolders are its group-mode children (plus `images/`), never
categories.

"M categories" counts every category folder at every depth, not just leaves.

It also checks Related Documents symmetry. The bidirectional sync in Stage 6 is four
separate appends (full.md and summary.md on both sides); an interruption partway
leaves A pointing at B while B does not point back, and nothing anywhere errors.

Usage:
    kb_tree.py                 # human-readable tree + stats + violations
    kb_tree.py --json          # machine-readable
    kb_tree.py --stats-line    # just the catalog stats line, ready to paste
"""

import datetime
import json
import os
import posixpath
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load  # noqa: E402

SKIP_IN_DOC = {"images"}


def classify(path):
    """category | document | conflict | unknown"""
    has_readme = os.path.isfile(os.path.join(path, "README.md"))
    has_full = os.path.isfile(os.path.join(path, "full.md"))
    if has_full and has_readme:
        return "conflict"
    if has_full:
        return "document"
    if has_readme:
        return "category"
    return "unknown"


def _subdirs(path):
    try:
        names = sorted(os.listdir(path))
    except OSError as exc:
        return [], str(exc)
    out = []
    for name in names:
        if name.startswith("."):
            continue
        full = os.path.join(path, name)
        if os.path.isdir(full) and not os.path.islink(full):
            out.append((name, full))
    return out, None


def walk_document(path, rel, level, acc):
    """A document folder. Its subfolders are group-mode children."""
    acc["documents"].append({"path": rel, "level": level, "abs": path})
    if not os.path.isfile(os.path.join(path, "summary.md")):
        acc["violations"].append({"path": rel, "problem": "Document directory is missing summary.md"})

    subs, err = _subdirs(path)
    if err:
        acc["violations"].append({"path": rel, "problem": f"Cannot read: {err}"})
        return
    for name, full in subs:
        if name in SKIP_IN_DOC:
            continue
        kind = classify(full)
        child_rel = f"{rel}/{name}"
        if kind == "document":
            walk_document(full, child_rel, level + 1, acc)
        elif kind == "category":
            acc["violations"].append({
                "path": child_rel,
                "problem": "Category nested inside a document; categories belong in categories or at the KB root"})
        elif kind == "conflict":
            acc["violations"].append({
                "path": child_rel,
                "problem": "Both README.md and full.md exist; category/document role is ambiguous"})
        else:
            acc["violations"].append({
                "path": child_rel,
                "problem": "Neither full.md nor README.md exists; directory role is unknown"})


def walk_category(path, rel, depth, acc, max_depth):
    """A category folder. May hold documents and subcategories."""
    entry = {"path": rel, "depth": depth, "direct_docs": 0, "subcategories": 0}
    acc["categories"].append(entry)

    if not os.path.isfile(os.path.join(path, "README.md")):
        acc["violations"].append({"path": rel, "problem": "Category is missing README.md"})
    # `depth` drives the catalog heading level. MAX_CATEGORY_DEPTH is a runaway
    # guard, not a design constraint: how deep to nest is a judgement call and is
    # not this script's business, but past this many levels something has gone
    # wrong (a recursive mkdir, a mangled path) rather than been decided.
    if depth > max_depth:
        acc["violations"].append({
            "path": rel,
            "problem": f"Category depth {depth} exceeds MAX_CATEGORY_DEPTH={max_depth}. "
                       f"Review the target path."})

    subs, err = _subdirs(path)
    if err:
        acc["violations"].append({"path": rel, "problem": f"Cannot read: {err}"})
        return
    for name, full in subs:
        kind = classify(full)
        child_rel = f"{rel}/{name}"
        if kind == "category":
            entry["subcategories"] += 1
            walk_category(full, child_rel, depth + 1, acc, max_depth)
        elif kind == "document":
            entry["direct_docs"] += 1
            walk_document(full, child_rel, 0, acc)
        elif kind == "conflict":
            acc["violations"].append({
                "path": child_rel,
                "problem": "Both README.md and full.md exist; category/document role is ambiguous"})
        else:
            acc["violations"].append({
                "path": child_rel,
                "problem": "Neither full.md nor README.md exists; directory role is unknown"})


def scan(cfg):
    root = cfg["KB_ROOT"]
    max_depth = int(cfg.get("MAX_CATEGORY_DEPTH", 7))
    # Everything the pipeline owns rather than the library.
    reserved = {os.path.normpath(cfg[k]).split(os.sep)[0]
                for k in ("SYSTEM_DIR", "INPUT_DIR", "WORK_DIR", "TRASH_DIR", "DRAFT_DIR")}
    reserved.add(os.path.normpath(cfg["SKILL_ROOT"]).split(os.sep)[0])

    acc = {"categories": [], "documents": [], "violations": []}
    subs, err = _subdirs(root)
    if err:
        acc["violations"].append({"path": ".", "problem": f"Cannot read KB root: {err}"})
        return acc

    for name, full in subs:
        if name in reserved:
            continue
        kind = classify(full)
        if kind == "category":
            walk_category(full, name, 1, acc, max_depth)
        elif kind == "document":
            acc["violations"].append({
                "path": name,
                "problem": "Document is at the KB root; put it inside a category"})
            walk_document(full, name, 0, acc)
        elif kind == "conflict":
            acc["violations"].append({
                "path": name,
                "problem": "Both README.md and full.md exist; category/document role is ambiguous"})
        else:
            acc["violations"].append({
                "path": name,
                "problem": "Neither full.md nor README.md exists; directory role is unknown"})
    check_links(acc)
    return acc


_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_SECTION = re.compile(r"^#{2,4}\s+(?:Related Documents|References)\s*$", re.M)


def _links_in(path):
    """Markdown link targets inside the Related Documents / References section."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    m = _SECTION.search(text)
    if not m:
        return []
    rest = text[m.end():]
    nxt = re.search(r"^#{1,4}\s+\S", rest, re.M)
    return _LINK.findall(rest[:nxt.start()] if nxt else rest)


def _resolve(doc_rel, target):
    """Turn a link found in doc_rel's files into a KB-relative document path."""
    if target.startswith(("http://", "https://", "#", "mailto:")):
        return None
    target = target.split("#", 1)[0].strip()
    if not target:
        return None
    joined = posixpath.normpath(posixpath.join(doc_rel, target))
    if joined.endswith(".md"):
        joined = posixpath.dirname(joined)
    joined = joined.strip("/")
    if not joined or joined.startswith(".."):
        return None
    return joined


def check_links(acc):
    """Populate acc['edges'] and flag one-way edges and dangling targets."""
    known = {d["path"] for d in acc["documents"]}
    edges = {}
    for doc in acc["documents"]:
        rel, out = doc["path"], set()
        for fname in ("full.md", "summary.md"):
            for raw in _links_in(os.path.join(doc["abs"], fname)):
                tgt = _resolve(rel, raw)
                if tgt and tgt != rel:
                    out.add(tgt)
        edges[rel] = out

    for src, targets in sorted(edges.items()):
        for tgt in sorted(targets):
            if tgt not in known:
                acc["violations"].append({
                    "path": src,
                    "problem": f"Related Documents points to missing document {tgt}"})
            elif src not in edges[tgt]:
                acc["violations"].append({
                    "path": src,
                    "problem": f"Related Documents points to {tgt}, but the reciprocal link is missing"})
    acc["edges"] = {k: sorted(v) for k, v in edges.items()}
    acc["edge_count"] = sum(len(v) for v in edges.values())


def stats_line(acc):
    return (f"> 📊 {len(acc['documents'])} documents | "
            f"{len(acc['categories'])} categories | "
            f"Last updated: {datetime.date.today():%Y-%m-%d}")


def render(acc, cfg):
    lines = []
    lines.append(stats_line(acc))
    lines.append("")
    if not acc["categories"]:
        lines.append("(No categories yet)")
    else:
        lines.append("Category tree:")
        for cat in acc["categories"]:
            indent = "  " * (cat["depth"] - 1)
            leaf = cat["path"].rsplit("/", 1)[-1]
            bits = []
            if cat["direct_docs"]:
                bits.append(f"{cat['direct_docs']} docs")
            if cat["subcategories"]:
                bits.append(f"{cat['subcategories']} subcats")
            # Counts are informational. There is deliberately no threshold:
            # a course with 20 lecture notes is healthy, and splitting on a
            # number rather than on mixed subject matter is the wrong trigger.
            suffix = f"  ({', '.join(bits)})" if bits else "  (empty)"
            lines.append(f"  {indent}{leaf}/{suffix}")

    if acc["documents"]:
        lines.append("")
        half = sum(1 for s_, ts in acc["edges"].items() for t in ts
                   if s_ in acc["edges"].get(t, []))
        lines.append(f"Documents ({acc.get('edge_count', 0)} related edges, "
                     f"{half // 2} reciprocal pairs):")
        for doc in acc["documents"]:
            lines.append(f"  {'  ' * doc['level']}{doc['path']}")

    lines.append("")
    if acc["violations"]:
        lines.append(f"Structure issues: {len(acc['violations'])}")
        for v in acc["violations"]:
            lines.append(f"  - {v['path']}: {v['problem']}")
    else:
        lines.append("Structure checks passed")
    return "\n".join(lines)


def main(argv):
    cfg = load()
    acc = scan(cfg)
    if "--json" in argv:
        print(json.dumps({**acc, "stats_line": stats_line(acc)},
                         indent=2, ensure_ascii=False))
    elif "--stats-line" in argv:
        print(stats_line(acc))
    else:
        print(render(acc, cfg))
    return 1 if acc["violations"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
