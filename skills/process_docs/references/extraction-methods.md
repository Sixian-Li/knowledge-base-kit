# Extraction methods

Use `python kb.py extract SOURCE FRESH_WORK_DIRECTORY`; it produces a common
text/image manifest without running a model. All extraction warnings must be
reviewed. Keep the source attachment even when an extractor appears complete.

| Input | Extracted material | Review requirements |
| --- | --- | --- |
| PDF | Text layer, tables, 150 DPI page images | Default: every page goes through a worker. Scanned pages depend on vision. Check small fonts, ordering and math. |
| DOCX | Body paragraphs/tables in XML order, inline image positions, headers/footers and notes | Merged cells, charts, equations, text boxes, tracked changes and pagination can require a PDF export. |
| HTML | Static text, links, tables and local/data-URI images | No JavaScript or network fetch. Remote images fail until a local authorized copy is supplied. Review SVG/canvas/media separately. |
| Notebook | Saved Markdown, source code, output text/tables/errors and supported embedded images | No cells execute. Missing outputs must be stated. Rich interactive output may require a saved static export. |
| Markdown/text | Original UTF-8 text | Resolve local assets, code fences and source-specific structure manually. |
| Rmd | Original source | Use `python kb.py rmd FILE` to detect saved renders. Only use `--render` after explicit execution authorization. |
| Image | Copied source image | One manifest entry, one independent worker session. |

PDF `RENDER_ALL_PAGES: false` uses a heuristic and may miss sparse vector diagrams;
keep the default `true` for coverage. Worker `page` identifiers mean PDF pages for
PDFs, and sequential extracted-image numbers for other formats.

No extractor claims zero loss for every possible source. Inventory the source,
compare extracted sections/cells/tables/images, and document anything missing.
If needed, use a suitable static export and keep both original and export with
clear provenance. Do not silently replace the original document.

For sources longer than `SHARD_THRESHOLD`, plan section-aligned chunks and a
coverage checklist. This is an instruction to the main agent, not automatic
chunk generation by the Python scripts. Keep formulas and code blocks intact.
