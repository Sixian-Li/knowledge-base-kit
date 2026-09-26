# Filing and catalog updates

Before filing, establish the approved target tree and every existing file to edit.
Back up source inputs, existing targets, catalog and category/related metadata.
Use a timestamped workspace-local backup. Do not overwrite a document until its
replacement/version handling is clear and authorized.

Copy `full.md`, `summary.md`, the original source filename and required local
assets to the destination. Hash the source before and after copying. Exclude
worker JSON/logs/temporary files from the filed document; preserve them in scratch
or a recoverable task archive so failures remain diagnosable.

For each changed document, run `python kb.py validate PATH --filed`. Validate the
whole group where applicable. Add category README rows, catalog entries and
keywords. Related-document links must be useful, labeled and reciprocal; update
both ends and check anchors after edits. Run `python kb.py tree` to check category
structure and reciprocity. A successful structure check is not a content audit.

Only after validation succeeds should handled inbox files and scratch move into
recoverable trash. Preserve inputs if any step fails. Record the exact result,
checks actually run, locations of backups and any unresolved warnings in the
workspace's `system/HANDOFF.md`. Do not report an unrun check as successful.
