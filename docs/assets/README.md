# README diagrams

The English and Chinese READMEs use the same diagram layouts, typography, spacing
and color palette. Each SVG includes accessible title/description text and light
and dark palettes selected by the viewer's color-scheme preference. Fonts use the
system sans-serif and monospace stacks; no external fonts, images or scripts load.

Regenerate all four diagrams from the repository root with Python 3.10+:

```sh
python scripts/build_readme_assets.py
```

Edit the shared generator rather than individual exported SVGs. Preview both
languages in light and dark mode, checking text fit and arrows at README width.
The original `examples/sources/workflow.png` is a document-processing fixture and
is intentionally independent of the README artwork.

These diagrams and their generator are original project material under the
repository's AGPL-3.0-only license.
