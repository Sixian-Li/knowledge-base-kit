#!/usr/bin/env python3
"""Check the explicit public-file allowlist, licenses, local doc links and privacy patterns."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {"_local", "dist", ".git", ".venv", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {".md", ".py", ".js", ".yaml", ".yml", ".json", ".txt", ".html", ".ipynb", ".template"}
PRIVATE = (re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
           re.compile(r"\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,})\b"),
           re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"))
REQUIRED = {"README.md", "README.zh-CN.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
            "SECURITY.md", "CONTRIBUTING.md", "requirements.txt", "constraints.txt",
            "scripts/init_workspace.py", "skills/kb/SKILL.md", "skills/process_docs/SKILL.md",
            "skills/process_docs/vendor/KATEX-LICENSE", ".github/workflows/ci.yml"}


def public_files(root=ROOT):
    path = root / "release-files.txt"
    entries = [s.strip() for s in path.read_text(encoding="utf-8").splitlines() if s.strip() and not s.startswith("#")]
    if entries != sorted(set(entries)):
        raise ValueError("release-files.txt must be sorted with no duplicates")
    for name in entries:
        part = PurePosixPath(name)
        if part.is_absolute() or ".." in part.parts or "\\" in name or any(x in IGNORED for x in part.parts):
            raise ValueError("Unsafe release path: " + name)
        file = root / name
        if any((root / Path(*part.parts[:i])).is_symlink() for i in range(1, len(part.parts)+1)):
            raise ValueError("Symlink in release path: " + name)
        if not file.is_file():
            raise ValueError("Missing release file: " + name)
    return entries


def without_fences(text):
    result, fence = [], None
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            if fence is None:
                fence = match[1]
            elif match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
            continue
        if fence is None:
            result.append(line)
    return "\n".join(result)


def validate(root=ROOT):
    errors = []
    try:
        entries = public_files(root)
    except (OSError, ValueError) as exc:
        return {"ok": False, "errors": [str(exc)]}
    names = set(entries)
    for missing in sorted(REQUIRED - names):
        errors.append("Required file not listed: " + missing)
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for item in [*dirs, *files]:
            file = Path(directory) / item
            rel = file.relative_to(root)
            if file.suffix == ".pyc" or file.name == ".DS_Store":
                continue
            if file.is_symlink():
                errors.append("Unexpected public symlink: " + rel.as_posix())
            elif file.is_file() and rel.as_posix() not in names:
                errors.append("Unlisted public file: " + rel.as_posix())
    total = 0
    for name in entries:
        path = root / name
        data = path.read_bytes()
        total += len(data)
        chunks = []
        if path.suffix in TEXT_SUFFIXES or path.name in ("LICENSE", "KATEX-LICENSE", ".gitignore", "VERSION"):
            try:
                chunks.append(data.decode("utf-8"))
            except UnicodeDecodeError:
                errors.append("Expected UTF-8 text: " + name)
        elif path.suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                chunks.extend(archive.read(n).decode("utf-8") for n in archive.namelist() if n.endswith(".xml"))
        if any(pattern.search(chunk) for pattern in PRIVATE for chunk in chunks):
            errors.append("Potential private path/credential in " + name)
        if path.suffix == ".py":
            try:
                ast.parse(data.decode(), filename=name)
            except SyntaxError as exc:
                errors.append(str(exc))
        if path.suffix == ".md":
            text = without_fences(data.decode())
            for target in re.findall(r"!?\[[^\]\n]+\]\(([^\s)]+)\)", text):
                url = urlsplit(target)
                if url.scheme or url.netloc or not url.path:
                    continue
                resolved = (path.parent / unquote(url.path)).resolve()
                if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                    errors.append(f"Broken/escaping document link in {name}: {target}")
    katex = root / "skills/process_docs/vendor/katex.min.js"
    if hashlib.sha256(katex.read_bytes()).hexdigest() != "10a91b479cd927446ceb60409fb0d72b5d0d05eaf446c9e52fafd64058c84540":
        errors.append("KaTeX hash differs from the pinned distribution; review its provenance and update the pin deliberately")
    if "GNU AFFERO GENERAL PUBLIC LICENSE" not in (root / "LICENSE").read_text():
        errors.append("Root AGPL license text is missing")
    return {"ok": not errors, "files": len(entries), "bytes": total, "errors": errors,
            "scope": "Static release checks; no external link, account or semantic-content audit"}


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = validate()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)
