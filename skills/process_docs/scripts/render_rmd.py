#!/usr/bin/env python3
"""Detect saved Rmd renders by default. --render explicitly executes source code.

Detection reports artifact staleness and probes the R toolchain without loading
user startup profiles. Rendering is opt-in and may have arbitrary side effects
from the document's R code; the calling agent must obtain execution authorization.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config

# Checked in this order; the first hit wins because it is the richest form.
ARTIFACT_EXTS = (".html", ".pdf", ".docx", ".md")

RENDER_TIMEOUT = 900  # knitting can legitimately take minutes on a real analysis


def find_artifacts(rmd_path):
    """Look for already-rendered siblings of the .Rmd."""
    directory = os.path.dirname(os.path.abspath(rmd_path)) or "."
    stem = os.path.splitext(os.path.basename(rmd_path))[0]
    rmd_mtime = os.path.getmtime(rmd_path)

    found = []
    for ext in ARTIFACT_EXTS:
        candidate = os.path.join(directory, stem + ext)
        if not os.path.exists(candidate):
            continue
        mtime = os.path.getmtime(candidate)
        found.append({
            "path": candidate,
            "ext": ext,
            "size": os.path.getsize(candidate),
            # Older than its source means it was knitted from an earlier draft.
            "stale": mtime < rmd_mtime,
            "mtime": mtime,
        })
    return found


def r_toolchain():
    """Report whether R and the packages a render needs are actually present."""
    rscript = shutil.which("Rscript")
    info = {"rscript": rscript, "rmarkdown": False, "knitr": False,
            "tinytex": False, "error": ""}
    if not rscript:
        info["error"] = "Rscript not found on PATH"
        return info

    probe = ('cat(paste(c("rmarkdown","knitr","tinytex") %in% '
             'rownames(installed.packages()), collapse=" "))')
    try:
        result = subprocess.run([rscript, "--vanilla", "-e", probe], capture_output=True,
                                text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as exc:
        info["error"] = f"probe failed: {exc}"
        return info

    flags = result.stdout.strip().split()
    if len(flags) == 3:
        info["rmarkdown"] = flags[0] == "TRUE"
        info["knitr"] = flags[1] == "TRUE"
        info["tinytex"] = flags[2] == "TRUE"
    else:
        info["error"] = (result.stderr or result.stdout).strip()[:500]
    return info


def render(rmd_path, out_dir, fmt=None):
    """Knit the document. Only ever reached via an explicit --render."""
    rscript = shutil.which("Rscript")
    if not rscript:
        return {"ok": False, "error": "Rscript not found on PATH"}

    if os.path.exists(out_dir) and os.listdir(out_dir):
        return {"ok": False, "error": "Choose a fresh render output directory"}
    os.makedirs(out_dir, exist_ok=True)
    src = json.dumps(os.path.abspath(rmd_path), ensure_ascii=False)
    dst = json.dumps(os.path.abspath(out_dir), ensure_ascii=False)

    if fmt not in (None, "html", "pdf"):
        return {"ok": False, "error": "format must be html or pdf"}
    fmt_arg = f'output_format = "{fmt}_document", ' if fmt else ""
    # intermediates_dir keeps knitr's scratch files out of the inbox; the
    # document's own working directory stays its source directory so relative
    # data paths (read.csv("data.csv")) still resolve.
    expr = (f'rmarkdown::render({src}, {fmt_arg}'
            f'output_dir = {dst}, intermediates_dir = {dst}, quiet = TRUE)')

    try:
        result = subprocess.run([rscript, "--vanilla", "-e", expr], capture_output=True,
                                text=True, timeout=RENDER_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"render timed out after {RENDER_TIMEOUT}s"}
    except OSError as exc:
        return {"ok": False, "error": f"could not launch Rscript: {exc}"}

    produced = []
    if os.path.isdir(out_dir):
        stem = os.path.splitext(os.path.basename(rmd_path))[0]
        for name in sorted(os.listdir(out_dir)):
            if name.startswith(stem) and os.path.splitext(name)[1] in ARTIFACT_EXTS:
                produced.append(os.path.join(out_dir, name))

    # R exits 0 on some failures, so the artifact's existence is the real test.
    if result.returncode != 0 or not produced:
        return {
            "ok": False,
            "returncode": result.returncode,
            "error": (result.stderr or result.stdout).strip()[-2000:],
            "produced": produced,
        }
    return {"ok": True, "returncode": 0, "produced": produced,
            "stderr": result.stderr.strip()[-2000:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--out")
    parser.add_argument("--format", choices=("html", "pdf"))
    args = parser.parse_args()
    rmd_path, do_render, fmt, out_dir = args.source, args.render, args.format, args.out

    if not os.path.exists(rmd_path):
        print(json.dumps({"ok": False, "error": f"not found: {rmd_path}"},
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    report = {
        "rmd": os.path.abspath(rmd_path),
        "artifacts": find_artifacts(rmd_path),
        "toolchain": r_toolchain(),
        "rendered": None,
        "mode": "render" if do_render else "detect",
    }

    if do_render:
        cfg = _config.load()
        target = out_dir or os.path.join(cfg["WORK_DIR_ABS"], "_rmd_render")
        report["rendered"] = render(rmd_path, target, fmt)

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if do_render and not (report["rendered"] or {}).get("ok"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
