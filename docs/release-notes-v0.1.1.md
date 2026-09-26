# Knowledge Base Kit 0.1.1

Bug-fix release. Upgrading an existing workspace: re-run
`python scripts/init_workspace.py <workspace> --backend <same backend>` from the
new toolkit copy; your configuration, catalog and documents are preserved.

Fixed:

- Display math (`align`, `\tag`, …) is validated in display mode and no longer
  blocks filing.
- `kb.py tree` no longer reports attachment or README links under References as
  missing documents.
- Notebook code/output containing triple backticks keeps valid Markdown; SVG,
  WebP and PDF outputs are marked instead of silently dropped.
- Corrupt or empty PDF/DOCX files and non-object notebooks fail with a clear
  message instead of a traceback.
- An interrupted installation can be retried, and installed files no longer get
  0600 permissions.
- Date validation is identical on Python 3.10 and 3.11+; `rmd --render` uses a
  fresh output directory each time; UTF-8 decoding no longer depends on locale.

Changed: WebP is no longer a supported input (convert to PNG/JPEG); `.tif` is.

The offline suite (51 tests) passed locally on Python 3.10 and 3.13. The worker
protocol is unchanged and live backend runs were not repeated; see
`docs/compatibility.md`. License terms are unchanged (AGPL-3.0-only).
