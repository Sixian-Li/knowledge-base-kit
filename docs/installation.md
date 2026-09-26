# Installation / 安装

## Requirements

Python 3.10+, Node.js 20+, Pandoc 3+ and a macOS or Linux environment with symbolic
links. Start with the [tested compatibility record](compatibility.md). Windows
native installation is not validated; use a Linux environment such as WSL at your
own discretion rather than assuming native feature parity.

Install Python, Node and Pandoc using your OS's normal package manager. For
example, macOS Homebrew users can install `python`, `node` and `pandoc`; Ubuntu
users need Python's venv support plus a current Pandoc/Node distribution. Older OS
packages may not meet the minimum versions. Check `python3 --version`,
`node --version` and `pandoc --version` before continuing.

Install/authenticate the chosen agent following its official documentation:
[Codex CLI](https://developers.openai.com/codex/cli/) or
[Claude Code](https://code.claude.com/docs/en/setup). CLI permissions and supported
flags change; the doctor checks installation/login but the compatibility record
is the evidence for actual worker execution.

## Create a workspace

From a clone or extracted release folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/init_workspace.py ../my-kb --backend both --language en --with-example
```

Inspect first with `--dry-run`. `--with-example` copies only the self-authored
quickstart Markdown to the new inbox. The installer uses a managed-file manifest;
a repeat with the same backend selection preserves your config, catalog and
rules. A locally modified managed skill causes a conflict before planned file
writes. It is not a transactional filesystem snapshot: keep a backup for upgrades.
Changing backend selection in place is not supported in v0.1; initialize a new
workspace and migrate deliberately if needed.

The initial interpreter is your active venv (`PYTHON: auto`). Activating that venv
before launching the main agent lets its scripts use the same dependencies. If
opening the workspace later from a fresh shell, activate the toolkit venv by its
path or create a separate workspace venv and install
`.kbkit/requirements.txt`. Dependencies are not copied with the skills.

```sh
cd ../my-kb
python kb.py check --backend codex
python kb.py config
```

Restart the agent after adding project-local skills if it has not discovered
them. Both `.claude/skills` and `.agents/skills` point to the same workspace-local
copy. It is safe to move the toolkit checkout afterward; the workspace has no
symlink back to it. Never run the initializer over an existing unrelated KB.

## 中文操作要点

先安装运行依赖，再创建一个**新的资料目录**。`--language zh-CN` 控制说明与摘要语言，
必要的结构标题保持英文，以便校验。工作区中的 `.kbkit/` 是技能副本，虚拟环境不在其中，
每次打开 agent 时仍需使用已安装依赖的 Python。`--dry-run` 不落盘；重复初始化保留个人
配置和目录内容，遇到修改过的受管文件会报冲突。不要用初始化器覆盖已有私人知识库。
