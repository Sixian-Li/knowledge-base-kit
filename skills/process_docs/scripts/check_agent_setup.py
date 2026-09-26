#!/usr/bin/env python3
"""Read-only checks for the selected agent's project setup; never calls a model."""

import argparse
import importlib.util
import shutil
import json
from pathlib import Path
import subprocess
import sys

import _config
from worker_backends import BACKENDS, find_cli


def check(backend, cfg=None, login=True):
    cfg = cfg or _config.load()
    root = Path(cfg["KB_ROOT"]).resolve()
    skill = Path(cfg["SKILL_ROOT_ABS"]).resolve()
    results = []

    def add(name, ok, detail, required=True):
        results.append({"check": name, "ok": bool(ok), "required": required, "detail": str(detail)})

    add("KB_ROOT", root.is_dir(), root)
    add("skill/config location", (skill / "SKILL.md").is_file(),
        "Configured skill package is present")
    for key in ("SYSTEM_DIR_ABS", "WORK_DIR_ABS", "INPUT_DIR_ABS", "DRAFT_DIR_ABS", "TRASH_DIR_ABS", "CATALOG_ABS"):
        path = Path(cfg[key]).resolve()
        add(key, path.is_relative_to(root), path)
    for path in (root / "AGENTS.md",
                 Path(cfg["SYSTEM_DIR_ABS"]) / "agent_rules.md",
                 Path(cfg["SYSTEM_DIR_ABS"]) / "HANDOFF.md"):
        add(path.name, path.is_file(), path)
    agent_dir = ".agents" if backend == "codex" else ".claude"
    link = root / agent_dir / "skills/process_docs"
    add("single skill implementation", link.is_symlink() and link.resolve() == skill, link)
    add("Python", Path(cfg["PYTHON"]).is_file(), cfg["PYTHON"])
    for module in ("pymupdf", "docx", "bs4", "html2text", "yaml"):
        add(module, importlib.util.find_spec(module) is not None, "Python dependency")
    # These are the scripts used by this checker or the skill's entrypoints.
    for name in ("extract_pdf", "extract_notebook", "render_rmd", "orchestrate_workers",
                 "extract_document", "extract_docx", "extract_html", "kb_tree", "_config",
                 "worker_backends", "validate_generated", "fold_archives",
                 "check_agent_setup"):
        add(name + ".py", (skill / "scripts" / (name + ".py")).is_file(), "Skill script")
    # Missing formula dependencies fail the publication gate.
    add("check_tex.js", (skill / "scripts" / "check_tex.js").is_file(),
        "KaTeX runner for the TeX render check")
    add("vendor/katex.min.js", (skill / "vendor" / "katex.min.js").is_file(),
        "Vendored KaTeX; without it the TeX check is skipped, not passed")
    for tool, why in (("pandoc", "extracts math spans for the TeX render check"),
                      ("node", "runs check_tex.js")):
        add(tool, shutil.which(tool) is not None, why)
    extensions = _config.supported_exts(cfg)
    add("supported formats", bool(extensions) and all(x.startswith(".") and x == x.lower() for x in extensions),
        ", ".join(extensions))
    for name in BACKENDS:
        cli = find_cli(cfg, name)
        add(name + " CLI", bool(cli), cli or "Not installed", required=name == backend)
        if name == backend and cli and login:
            command = [cli, "auth", "status"] if name == "claude" else [cli, "login", "status"]
            try:
                proc = subprocess.run(command, capture_output=True, text=True, timeout=20)
                if name == "claude":
                    data = json.loads(proc.stdout)
                    ok = proc.returncode == 0 and data.get("loggedIn") is True
                else:
                    ok = proc.returncode == 0 and "logged in" in (proc.stdout + proc.stderr).lower()
                add(name + " login", ok, "Logged in; available quota not tested" if ok else "Login required or status could not be confirmed")
            except (OSError, ValueError, subprocess.TimeoutExpired):
                add(name + " login", False, "Could not check login status")
    reader = Path(cfg["READER_SKILL"]).resolve() / "SKILL.md"
    add("workspace reader", reader.is_file(), reader)
    reader_link = root / agent_dir / "skills/kb"
    add("reader discovery link", reader_link.is_symlink() and reader_link.resolve() == reader.parent,
        reader_link)
    add("Rscript", bool(shutil.which("Rscript")), "Only required for explicitly authorized Rmd rendering", required=False)
    return {"ok": all(x["ok"] for x in results if x["required"]), "backend": backend, "checks": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=BACKENDS, required=True)
    parser.add_argument("--skip-login", action="store_true", help="check files/dependencies only")
    args = parser.parse_args()
    try:
        result = check(args.backend, login=not args.skip_login)
    except (_config.ConfigError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
