#!/usr/bin/env python3
"""Exercise a real offline pipeline with reviewed reference output, without model calls."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/process_docs/scripts"))
from init_workspace import install
from _config import load
from extract_document import extract
from validate_generated import check
from kb_tree import scan


def run(destination):
    workspace = Path(destination).expanduser().resolve()
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError("Use a new or empty demo workspace; existing data is never replaced")
    install(workspace, with_example=True)
    cfg = load(workspace / "kb.config.yaml")
    scratch = workspace / "inbox/.work/quickstart"
    extraction = extract(workspace / "inbox/quickstart.md", scratch, cfg)
    reference = ROOT / "examples/expected-output/quickstart"
    for name in ("full.md", "summary.md"):
        shutil.copyfile(reference / name, scratch / name)
    draft = check(scratch, cfg, target="notes/quickstart")
    if not draft["ok"]:
        raise ValueError("Draft checks failed: " + json.dumps(draft))
    category = workspace / "notes"
    target = category / "quickstart"
    target.mkdir(parents=True)
    for name in ("full.md", "summary.md"):
        shutil.copyfile(scratch / name, target / name)
    shutil.copyfile(workspace / "inbox/quickstart.md", target / "quickstart.md")
    (category / "README.md").write_text("# Notes\n\n- [Quickstart](quickstart/summary.md)\n", encoding="utf-8")
    (workspace / "catalog.md").write_text("# Knowledge catalog\n\n- [A tiny knowledge library](notes/quickstart/summary.md) — A reviewed, self-authored demonstration.\n\n## Keywords\n\nknowledge base, source review, Markdown\n", encoding="utf-8")
    filed = check(target, cfg, filed=True)
    tree = scan(cfg)
    report = {"ok": draft["ok"] and filed["ok"] and not tree["violations"],
              "workspace": str(workspace), "model_calls": 0,
              "generation": "Copied reviewed reference output; no agent generation was performed",
              "source_sha256": extraction["source_sha256"], "draft": draft, "filed": filed,
              "documents": len(tree["documents"]), "tree_violations": tree["violations"]}
    (workspace / "system/HANDOFF.md").write_text("# Offline demo\n\n" + report["generation"] + ".\n\n```json\n" + json.dumps(report, indent=2) + "\n```\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    args = parser.parse_args()
    try:
        result = run(args.workspace)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["ok"] else 1)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Demo failed: {exc}\n")
