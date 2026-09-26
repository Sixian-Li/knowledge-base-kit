# Changelog

## 0.1.1

Bug-fix release; no worker protocol or configuration-key changes.

- Formula check renders display math in display mode, so `align`, `\tag` and
  other display-only TeX no longer block filing.
- `kb.py tree` counts only document directories, `full.md` and `summary.md` as
  related-document links; attachments and category READMEs under References are
  no longer reported as missing documents.
- Notebook extraction chooses fences longer than any backtick run in the content,
  and marks SVG/WebP/PDF outputs with a placeholder plus `unsupported_outputs`
  instead of dropping them silently. Non-object notebook JSON is rejected cleanly.
- WebP is no longer listed as supported (PyMuPDF cannot decode it); `.tif` is.
  HTML/DOCX WebP images fail explicitly and ask for a PNG/JPEG copy.
- Corrupt or empty PDF/DOCX sources report `Extraction failed` instead of a traceback.
- The installer records a pending manifest before writing, so an interrupted
  install or update can be re-run, and installed files follow the umask (were 0600).
- `converted` dates must be `YYYY-MM-DD` on every Python version (3.11+ accepted
  compact and week dates).
- `rmd --render` uses a fresh default output directory per render.
- Files and subprocess output are decoded as UTF-8 regardless of locale.
- Docs: hosted CI results recorded; new format limits documented; announcement
  draft removed from the public tree.

## 0.1.0

Initial standalone release: portable configuration, isolated workspace installer,
Claude/Codex image workers, static document extraction, source-preserving drafting
instructions, structural/TeX validation, catalog checks, bilingual onboarding and
self-authored examples. See [limitations](docs/limitations.md) and the exact
[compatibility record](docs/compatibility.md) before use.
