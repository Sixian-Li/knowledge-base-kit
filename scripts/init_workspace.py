#!/usr/bin/env python3
"""Create/update an independent knowledge workspace without calling a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parents[1]
STATE = ".kbkit/install.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".install-", delete=False) as stream:
        pending = Path(stream.name)
        stream.write(data)
    try:
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def install(root, backend="both", language="en", dry_run=False, with_example=False):
    if backend not in ("claude", "codex", "both") or language not in ("en", "zh-CN"):
        raise ValueError("Unsupported backend or language")
    root = Path(root).expanduser().resolve()
    if root == REPO or (root.is_relative_to(REPO) and root.relative_to(REPO).parts[0] != "_local"):
        raise ValueError("Choose a workspace outside the toolkit checkout")
    state_path = root / STATE
    if state_path.is_symlink() or (root / ".kbkit").is_symlink():
        raise ValueError("The workspace installation state must not be a symlink")
    previous = {}
    if state_path.exists():
        previous = json.loads(state_path.read_text(encoding="utf-8"))
        if previous.get("toolkit") != "knowledge-base-kit" or previous.get("schema") != 1:
            raise ValueError("Unrecognized install manifest; nothing was changed")
        if previous.get("backend") != backend:
            raise ValueError("Keep the installed backend selection when updating this workspace")
    elif root.exists() and any(root.iterdir()):
        raise ValueError("Refusing a nonempty directory without a toolkit install manifest")

    managed = {}
    for path in sorted((REPO / "skills").rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("Release skill packages must not contain symlinks")
        if path.is_file():
            managed[".kbkit/skills/" + path.relative_to(REPO / "skills").as_posix()] = path.read_bytes()
    for name in ("requirements.txt", "constraints.txt", "LICENSE", "THIRD_PARTY_NOTICES.md", "VERSION"):
        managed[".kbkit/" + name] = (REPO / name).read_bytes()
    managed["kb.py"] = (REPO / "scripts/workspace_cli.py").read_bytes()
    owned = {}
    for path in sorted((REPO / "templates/workspace").rglob("*")):
        if path.is_file():
            key = path.relative_to(REPO / "templates/workspace").as_posix()
            if key == "gitignore.template":
                key = ".gitignore"
            owned[key] = path.read_bytes().replace(b"{{OUTPUT_LANGUAGE}}", language.encode())
    if with_example:
        owned["inbox/quickstart.md"] = (REPO / "examples/sources/quickstart.md").read_bytes()

    links = {}
    for agent in (("claude", "codex") if backend == "both" else (backend,)):
        folder = ".claude" if agent == "claude" else ".agents"
        for skill in ("process_docs", "kb"):
            key = folder + "/skills/" + skill
            links[key] = os.path.relpath(root / ".kbkit/skills" / skill, (root / key).parent)

    conflicts, writes = [], []
    for name in ("inbox", "inbox/.work", ".drafts", ".trash", "system"):
        path = root / name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            conflicts.append(name + " (reserved directory is not a real directory)")
    for key, data in {**managed, **owned}.items():
        path = root / key
        parents = list(path.relative_to(root).parents)[:-1]
        if any((root / p).is_symlink() or ((root / p).exists() and not (root / p).is_dir()) for p in parents):
            conflicts.append(key + " (unsafe parent)")
            continue
        if path.is_symlink() or (path.exists() and not path.is_file()):
            conflicts.append(key)
        elif path.exists():
            current = digest(path.read_bytes())
            if key in owned:
                continue  # configuration, catalog and rules belong to the user
            expected = previous.get("managed", {}).get(key)
            if current != digest(data) and current != expected:
                conflicts.append(key + " (locally edited)")
            elif current != digest(data):
                writes.append(key)
        else:
            writes.append(key)
    for key, target in links.items():
        path = root / key
        if any((root / p).is_symlink() or ((root / p).exists() and not (root / p).is_dir()) for p in list(path.relative_to(root).parents)[:-1]):
            conflicts.append(key + " (unsafe parent)")
        elif path.is_symlink():
            if os.readlink(path) != target:
                conflicts.append(key + " (different link target)")
        elif path.exists():
            conflicts.append(key)
    if conflicts:
        raise ValueError("Conflicts; nothing changed:\n" + "\n".join(conflicts))
    result = {"workspace": str(root), "backend": backend, "dry_run": dry_run,
              "files_to_write": sorted(writes), "links": links,
              "preserves_existing_config": bool(previous)}
    if dry_run:
        return result
    for name in ("inbox/.work", ".drafts", ".trash", "system"):
        path = root / name
        if path.is_symlink():
            raise ValueError(f"Reserved directory must not be a symlink: {name}")
        path.mkdir(parents=True, exist_ok=True)
    payload = {**managed, **owned}
    for key in writes:
        atomic_write(root / key, payload[key])
    for key, target in links.items():
        path = root / key
        if not path.is_symlink():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target, target_is_directory=True)
    state = {"schema": 1, "toolkit": "knowledge-base-kit", "backend": backend,
             "version": (REPO / "VERSION").read_text().strip(),
             "managed": {k: digest(v) for k, v in managed.items()}, "links": links}
    atomic_write(state_path, (json.dumps(state, indent=2) + "\n").encode())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="new independent workspace directory")
    parser.add_argument("--backend", choices=("claude", "codex", "both"), default="both")
    parser.add_argument("--language", choices=("en", "zh-CN"), default="en")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--with-example", action="store_true")
    args = parser.parse_args()
    try:
        result = install(args.root, args.backend, args.language, args.dry_run, args.with_example)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Initialization failed: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
