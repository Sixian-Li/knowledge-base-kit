#!/usr/bin/env python3
"""Installed workspace helper. Generation/filing remain an agent workflow."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / ".kbkit/skills/process_docs/scripts"
COMMANDS = {"check": "check_agent_setup.py", "config": "_config.py",
            "extract": "extract_document.py", "workers": "orchestrate_workers.py",
            "validate": "validate_generated.py", "tree": "kb_tree.py",
            "fold": "fold_archives.py", "rmd": "render_rmd.py"}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__ + "\n\nUsage: python kb.py COMMAND [arguments]\nCommands: " + ", ".join(COMMANDS))
        return 0
    command = sys.argv[1]
    if command not in COMMANDS:
        print("Unknown command: " + command, file=sys.stderr)
        return 2
    env = dict(os.environ, KB_CONFIG=str(ROOT / "kb.config.yaml"))
    return subprocess.call([sys.executable, str(SCRIPTS / COMMANDS[command]), *sys.argv[2:]], env=env)


if __name__ == "__main__":
    sys.exit(main())
