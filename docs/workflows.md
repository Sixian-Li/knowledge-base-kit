# Workflows / 工作流

## Agent-assisted ingestion

1. Put a source in the initialized workspace's `inbox/` and open that workspace in
   the chosen agent. Ask it to use `process_docs`; specify the backend and review
   preference. The agent reads its local rules, catalog and configuration.
2. Run the selected backend's doctor, then extract into a new scratch directory:
   `python kb.py extract inbox/source.pdf inbox/.work/source`.
3. If images exist, run `python kb.py workers inbox/.work/source --backend codex`
   (or `claude`). Read every failure/warning; never accept incomplete coverage.
4. The agent reads extraction artifacts and source, writes `full.md` and
   `summary.md`, preserves raw archives and reconciles every section/table/image.
5. Run `python kb.py fold inbox/.work/source`, then
   `python kb.py validate inbox/.work/source --target notes/source`.
   The target must match the draft metadata's category. A missing tool yields
   `ok: false`; a draft without target may defer external links, so repeat with
   the actual target before filing.
6. Review the proposed target and all metadata/reciprocal-link changes, unless
   the user already authorized these concrete operations. Back up affected files.
7. File only the reviewed content/assets and original attachment. Validate with
   `python kb.py validate notes/source --filed`, update category/catalog/keywords,
   and run `python kb.py tree`. Preserve or recover inputs if anything fails.

## Reading

Ask the `kb` skill a question. It selects summaries through the catalog and opens
full documents only as needed. Answers should cite concrete source files/headings
and distinguish a source statement from an inference.

## Batch, groups and recovery

Batch processes independent sources with a consolidated change preview. A group
has an explicit parent overview and child documents; see the skill's
[group rules](../skills/process_docs/references/group-mode.md). Neither mode
removes the need for content review or execution authorization.

A worker run is resumable using validated caches. `--force` intentionally discards
reuse and may incur new charges. Account/initialization failures stop the run;
resolve them on the chosen account. A fresh extraction uses a fresh directory so
failed attempts and accepted outputs cannot be silently mixed. There is no
automatic rollback transaction across all catalog writes; back up first.

## 中文提示

先提取、再核对、生成可审阅草稿，最后按授权入库。缺少工具或图片失败时不能当作完成。
`kb.py extract` 不会自动生成最终全文；`kb.py validate` 不负责证明语义无遗漏。
Notebook 默认只读取保存的输出；Rmd 只有明确授权执行后才可加 `--render`。
