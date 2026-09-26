# Architecture / 架构

The toolkit repository contains reusable code, instructions, templates and public
examples. An initialized workspace contains the user's knowledge and a local copy
of those instructions/code. No live private library is required to run the tests.

```text
knowledge-base-kit/           my-kb/
  skills/process_docs/         .kbkit/skills/   # managed local copies
  skills/kb/                   .agents/skills/ # relative discovery links
  scripts/                     .claude/skills/
  templates/workspace/         kb.py, kb.config.yaml
  examples/                    catalog.md, inbox/, system/
  tests/                       topic/README.md
                               topic/document/{full.md,summary.md,source.pdf}
```

Static extractors produce `.extracted_content.md`, an image directory and
`.extraction_metadata.json`. Workers consume one manifest image per isolated CLI
session. Text is validated and atomically saved by the host; cache identity
includes source image bytes, backend, requested model, effort, language, context
and prompt protocol. A successful worker protocol is not a content accuracy test.

The main agent interleaves source text and image information into `full.md`, writes
a useful `summary.md`, chooses a category and prepares related links. Python does
not replace this stage. The validator checks structure, local links and anchors,
source attachment presence, image coverage, text archive folding and TeX syntax.
The tree checker walks real directories and checks category/document roles plus
reciprocal related links; it does not chase symlinked category trees.

Filing is a reviewed agent operation with backups and post-copy validation. The
reader skill then loads catalog → summary → full. There is no vector database,
web server, background daemon, hosted sync or collaborative write coordinator.
Only one writing task should operate on a workspace at a time.

中文：工具与资料分开；技能在资料工作区内部保存副本，两种 agent 共用。提取、图片识读、
主 agent 整理、校验、归档各有明确职责。系统没有后台服务、自动执行 Notebook、向量库或
多写入者锁；不要同时让两个 agent 修改同一个资料库。
