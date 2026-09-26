# Maintaining Knowledge Base Kit

Keep one source package in `skills/process_docs` and one reader in `skills/kb`.
Workspace installations are generated copies, not a second development source.
The installer must never overwrite user content or a locally edited managed file.

Use a dedicated Python virtual environment and temporary workspaces for changes.
Run `python -m unittest discover -s tests -v` and
`python scripts/validate_release.py` before packaging. Ordinary tests must not
contact a model, run source notebook cells, or render source R Markdown code.
Model integration tests are separately invoked and use only self-authored input.

Configuration defaults own the supported extension list. The main agent owns
full-text and summary generation; extraction scripts are not a substitute for
source comparison. Validate both draft and filed forms. Never treat skipped
formula checks, failed image workers or missing source attachments as a pass.

When changing a CLI adapter, test its protocol, timeout cleanup, cache invalidation
and failure behavior. Do not widen permissions or change accounts automatically.
Record the CLI versions actually tested in `docs/compatibility.md`.

Preserve third-party license notices. Bump `VERSION` and `CHANGELOG.md` for a
release, regenerate the release manifest/archive, and inspect the file list.
Do not include personal libraries, credentials, local review records or run logs.
Use `docs/publishing.md` for the first GitHub publication.
