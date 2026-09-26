# Known limitations / 已知限制

- v0.1 is a CLI/skill toolkit for experienced agent users. There is no GUI,
  background indexing service, concurrent writer lock or automatic migration of
  an existing KB. Installer upgrades preserve user files but are not atomic over
  every file; interrupted upgrades may require restoring a backup.
- Source review remains essential. Scans, tiny fonts, diagrams, dense formulas
  and unusual reading order can confuse extraction or a model. “Preserve all
  information” is a workflow objective, not a measured universal guarantee.
- DOCX body order and inline images are supported. Merged cells, floating objects,
  tracked changes, equations, charts, notes and unusual pagination need visual
  source comparison or a PDF export. Embedded links/media are not executed.
  EMF/WMF drawings are not extracted; they are reported as failed images and
  block filing until you supply a PNG export of that page or image.
- WebP images are not supported, as sources or embedded images, because the
  pinned PyMuPDF cannot decode them for the worker's image check. Convert them
  to PNG or JPEG first.
- Static HTML is supported. JavaScript, canvas, iframes, remote assets, inline SVG
  and audio/video need separately reviewed static material. Remote image failures
  are explicit; the extractor does not download them automatically.
- Notebooks are read, not run. SVG, WebP and PDF outputs are not described:
  they leave a visible placeholder and are listed under `unsupported_outputs`.
  Interactive widgets and other unsupported MIME output may need a static
  export; missing output cannot be reconstructed honestly.
  Rmd rendering can execute code and remains an explicit, separate action.
- Model CLI versions, protocols, feature flags and account access can change.
  Tested versions are listed, not a promise that every newer/older CLI works.
  A provider's default model may change without invalidating a null-model cache.
- Image caches use bytes and protocol settings, not semantic equivalence. Keep
  one writer per workspace. One session per image favors isolation and traceability
  over minimum latency/cost; large PDFs can be expensive and slow.
- Formula checks target one KaTeX version. Other Markdown viewers can render
  differently. Escape literal dollar signs when mixed with math in a paragraph;
  Pandoc's math parsing can otherwise pair unintended dollar delimiters.
- Markdown link/anchor validation covers common Markdown, not all HTML, renderer
  extensions or external URLs. Category symlinks are intentionally not followed.
- macOS was exercised locally and hosted CI runs the offline checks on Linux and
  macOS. Native Windows and a broad CLI-version matrix have not been validated.
  There is no production security certification.

中文：主要限制是复杂版式与动态内容、模型输出的不确定性，以及仍需主 agent 和人工审阅。
不要把验证通过理解为“零信息损失已被证明”。首版优先把来源、失败和检查结果讲清楚。
