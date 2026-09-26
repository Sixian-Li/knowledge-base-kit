# Agent compatibility

Both agents use one installed implementation under `.kbkit/skills`. Claude
finds `.claude/skills`; Codex finds `.agents/skills`. These are local relative
symlinks created by the initializer. No global skills/configuration are changed.

Choose `--backend claude` or `--backend codex` on every worker invocation. An
installation for one backend does not require the other CLI. The main agent must
read the skill; `kb.py` does not itself invoke a document-generation agent.

Claude workers run in a temporary folder containing one copied image, with
`Read` only, `dontAsk`, `--restricted`, `--safe-mode` and no MCP servers. They
return text to the host; the host validates and saves it. Codex workers attach
one image, ignore user configuration and exec rules, run with a read-only sandbox
and disable shell/apps/browser/computer-use/hooks/skill-search features. Unexpected
tool events fail validation. These controls are not a separate operating-system
container or proof against all provider/CLI bugs; do not process adversarial
material containing secrets on the assumption of complete host isolation.

Null model settings use the CLI default; set a vision-capable model available to
your account when needed. Model access, auth and quota remain provider concerns.
A doctor login check is not a billable model call and does not establish quota.
See the release's compatibility record for the versions actually exercised.
