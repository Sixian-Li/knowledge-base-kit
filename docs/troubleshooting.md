# Troubleshooting / 故障处理

| Symptom | What to check |
| --- | --- |
| No `kb.config.yaml` | Run from an initialized workspace, use its `kb.py`, or explicitly set `KB_CONFIG` for a helper. |
| Missing module | Activate the venv that installed `requirements.txt`; `PYTHON: auto` uses the running interpreter. |
| CLI not found | Check PATH or set `CLAUDE_CLI` / `CODEX_CLI` in this workspace's config. |
| Agent cannot discover skills | Reopen the workspace and verify `.agents/skills` or `.claude/skills` links resolve inside `.kbkit`. |
| Doctor login failure | Log in through the chosen provider CLI yourself, then repeat doctor. It does not test remaining quota. |
| Worker permission/startup failure | Read the concise failure log and compare CLI version with compatibility notes. Do not remove safety flags or switch accounts automatically. |
| Worker timeout | Inspect image size/complexity, provider status and selected model. Increase the explicit timeout if appropriate, then retry. |
| Wrong page/empty output | Preserve failure artifacts and inspect the image; protocol validation deliberately rejects it. |
| Remote HTML image | Save an authorized local copy and rewrite the source copy's asset link; preserve the original separately. |
| Extraction output already exists | Choose a fresh scratch folder; the generic extractor prevents silently mixing attempts. |
| `unchecked` in validator | Install Node/Pandoc or repair the vendored KaTeX files. Missing checks produce failure. |
| TeX fails | Compare to the source, fix markup only when justified and label source errors. Do not replace all dollar signs blindly. |
| Update conflict | Back up local changes to managed files, reconcile with the new skill version, then retry. User config/catalog are preserved. |

When reporting a bug, use a self-authored minimal input and sanitized output.
Never attach account logs, private course/work documents or full provider responses.
中文：保留失败现场，先定位工具、配置或源文件问题；不要靠扩大权限、自动换号或删掉失败标记
让流程“看起来通过”。请用最小自制示例提交问题。
