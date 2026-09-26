# Configuration / 配置

The workspace owns `kb.config.yaml`; package defaults live in
`skills/process_docs/config.defaults.yaml`. Values are merged and validated with
safe YAML parsing. Unknown/duplicate keys, nested values and invalid types fail.
`python kb.py config` prints the resolved configuration without reading auth files.

| Setting | Default / meaning |
| --- | --- |
| `KB_ROOT` | `.` relative to the config file; may be an explicit absolute library path |
| `SYSTEM_DIR` / `INPUT_DIR` | `system` / `inbox` |
| `WORK_DIR` / `DRAFT_DIR` / `TRASH_DIR` | `inbox/.work` / `.drafts` / `.trash` |
| `CATALOG` | `catalog.md` |
| `PYTHON` | `auto`, the running interpreter; an explicit executable is checked by the doctor |
| `CLAUDE_CLI` / `CODEX_CLI` | `auto`, locate the CLI; or set its executable path |
| `WORKER_MODEL` | `null`, Claude CLI default; set an available vision model when needed |
| `CODEX_WORKER_MODEL` | `null`, Codex CLI default |
| `CODEX_WORKER_REASONING_EFFORT` | `null`; optional model-supported effort |
| `OUTPUT_LANGUAGE` | `en` or `zh-CN`; structural headings stay fixed |
| `WORKER_TIMEOUT` | `180` seconds per image attempt |
| `MAX_IMAGE_MB` | `8`; reject larger image inputs before starting a worker |
| `RENDER_ALL_PAGES` | `true`; false is a heuristic with coverage risk |
| `SHARD_THRESHOLD` | `30000` extracted characters; main agent plans section chunks |
| `LARGE_FILE_WARN_MB` | `15`; advisory for the main agent |
| `MAX_CATEGORY_DEPTH` | `7` snake_case category segments |
| `RELATED_PREFILTER_MIN` | `10`; advisory threshold for narrowing related-document candidates |
| `RMD_WHEN_NO_RENDER` | Only `ask` is allowed; config cannot authorize code execution |
| `SUPPORTED_FORMATS` | Comma-separated extensions; see defaults for the authoritative list |

All subordinate paths must remain inside `KB_ROOT`, including after symlink
resolution. Changing `KB_ROOT` is an explicit retargeting operation; use a new
workspace for a different library to keep its rules/discovery links aligned.
`kb.py` selects its own workspace config. When running individual helper scripts,
`KB_CONFIG` explicitly overrides discovery; without it, installed helpers bind to
their installation's config, and source-checkout helpers search cwd ancestors.

The helper launcher uses the interpreter that launches it. `PYTHON` is also
reported for agent-side commands; it does not restart the launcher in a different
environment. Prefer `auto` and an activated venv.

A null model uses the CLI default **at run time**. Caches record that requested
setting; they cannot detect a provider changing its default behind the same null
value. Set explicit models for repeatability, and use `--force` after changing CLI
versions/default model behavior. Do not copy an account's private model identifier
into public examples or issue reports.

中文：路径相对配置文件指定的库根解析，未知键、重复键和目录越界会报错。模型不内置账号专属
名称；需要时填入自己可用的视觉模型。默认模型变化不会自动改变缓存标识，升级 CLI 或切换
默认模型后应明确重跑。`SHARD_THRESHOLD` 等规划参数由主 agent 执行，不是后台自动任务。
