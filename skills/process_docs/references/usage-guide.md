# Usage guide

Open an initialized workspace in Claude Code or Codex. Ask the agent to use the
local `process_docs` skill to process selected files in `inbox/`. Ask for a draft
first, or explicitly authorize the full extraction/review/filing process when
that is what you intend. The agent still verifies the source and checks links.

Example: “Use process_docs with the Codex backend to process inbox/quickstart.md.
Prepare the full document and summary, show me the proposed category and files,
and wait for my review before filing.”

Use `kb` for questions about filed knowledge. It reads catalog → summary → full
text. Use a check request for a read-only audit, batch for multiple independent
sources, group for a coherent collection, delete for recoverable removal, or teach
for a source-backed explanation. See [modes](modes.md).

For deterministic helpers, run `python kb.py --help`. The helper does not provide
a complete automatic ingest command. Select the installed Python environment
before launching the agent so subprocesses can find the dependencies.
