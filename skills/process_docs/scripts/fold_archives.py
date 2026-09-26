#!/usr/bin/env python3
"""Fold raw text archives without changing their contents. Safe to run twice."""
import argparse
import html
from pathlib import Path
import sys

from validate_generated import archive_blocks, unfolded_archives


def fold_text(text, label="Raw source text (verbatim archive)"):
    lines, count = text.split("\n"), 0
    for start, end, folded in reversed(archive_blocks(text)):
        if folded or end is None:
            continue
        lines[start:end + 1] = (["<details>", f"<summary>{html.escape(label)}</summary>", ""]
                                + lines[start:end + 1] + ["", "</details>"])
        count += 1
    return "\n".join(lines), count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc_dir", nargs="+")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--label", default="Raw source text (verbatim archive)")
    args = parser.parse_args()
    remaining = 0
    for doc in args.doc_dir:
        for name in ("full.md", "summary.md"):
            path = Path(doc) / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            new, count = fold_text(text, args.label)
            if not args.check and count:
                path.write_text(new, encoding="utf-8")
                print(f"{path}: folded {count} block(s)")
            pending = unfolded_archives(text if args.check else new)
            remaining += len(pending)
            if pending:
                print(f"{path}: unresolved archive fences at lines {pending}")
    return 1 if remaining else 0


if __name__ == "__main__":
    sys.exit(main())
