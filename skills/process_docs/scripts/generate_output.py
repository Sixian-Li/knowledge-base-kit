#!/usr/bin/env python3
"""Fallback/test concatenation only. Its output is deliberately rejected by validation."""
from pathlib import Path
import sys


def merge_content(doc_dir):
    root = Path(doc_dir)
    text = (root / ".extracted_content.md").read_text(encoding="utf-8")
    desc = root / ".image_descriptions.md"
    images = desc.read_text(encoding="utf-8") if desc.exists() else ""
    warning = "<!-- KBKIT_FALLBACK_OUTPUT -->\n> Test concatenation; an agent must create and review the real document.\n\n"
    for name, content in (("full.md", text + "\n" + images), ("summary.md", "No reviewed summary has been generated.\n")):
        target = root / name
        if target.exists():
            raise ValueError("Refusing to overwrite existing generated content: " + name)
    (root / "full.md").write_text(warning + text + "\n" + images, encoding="utf-8")
    (root / "summary.md").write_text(warning + "No reviewed summary.\n", encoding="utf-8")
    return str(root / "full.md"), str(root / "summary.md")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_output.py FRESH_EXTRACTION_DIRECTORY")
    merge_content(sys.argv[1])
