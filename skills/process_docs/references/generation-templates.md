# Generation templates

These headings and scalar metadata fields are part of the validator contract.
Explanatory prose follows `OUTPUT_LANGUAGE`; keep the structural headings below.
Write factual coverage, not a fixed word count or a promise of perfect extraction.

## Full text

````markdown
---
source: source.pdf
format: <pdf|docx|html|htm|md|txt|ipynb|rmd|png|jpg|jpeg|gif|bmp|webp|tiff>
converted: YYYY-MM-DD
category: category/subcategory
description: "One concise description of this source."
doc_type: normal
---

# Source title

## Table of Contents

- [Content](#content)
- [Related Documents](#related-documents)

## Content

Follow the source's sections. Keep all substantive details, code and values.
Place each image or its description beside its original context. Mark uncertainty.

<details>
<summary>Raw source text (verbatim archive)</summary>

```text
Unmodified extracted PDF page text, including extraction artifacts.
```

</details>

## Related Documents

No related documents yet.
````

Choose one format label, not the literal alternatives. Keep the original source
filename, including spaces and extension; YAML-quote strings containing `:` or
`#`. `converted` is the actual conversion date. Parent documents add `children`
(a list of direct child slugs). Child documents add `parent` (the direct parent
slug). All documents preserve the original source when one exists; a synthetic
parent overview must have an explicit self-authored source attachment.

## Summary

```markdown
# Title — Reading guide

## Overview

What the document covers and when it is useful.

## Prerequisites

Required background, inputs or assumptions. State “None” if appropriate.

## Key Steps

The main procedure, argument or concepts in a useful order. A research or lecture
source may summarize reasoning instead of inventing an operational procedure.

## Configuration Reference

Important parameters, symbols, values and units; “Not applicable” when appropriate.

## Common Pitfalls

Source caveats, common mistakes and clearly identified extraction limitations.

## References

- [Full document](full.md#content)
```

## Formulas and fidelity

Use `$...$` for inline math and `$$...$$` for display math. Keep code and currency
as code/currency; do not turn every dollar sign or single letter into math. Pandoc
identifies math spans and the pinned KaTeX engine checks syntax. Viewer support
may differ. Never repair an apparent source formula error without preserving the
original and labeling the correction as commentary.

Keep raw PDF text archives intact when folding or editing prose. Fences may need
more than three backticks when source code itself contains backticks. Keep notes,
captions, axes, table cells, code output and error output. Absence of saved notebook
output means results are unavailable, not that the code succeeded.

## Category and catalog

A category `README.md` explains the category and lists its immediate children.
The root catalog lists each document's summary with a concise description and
useful keywords. Do not put a category README inside a document folder. Use
relative links that work after filing. Avoid duplicate or speculative relations.
