# KaTeX syntax checker

Vendored version: **0.18.7**. The minified distribution is unchanged from:
https://cdn.jsdelivr.net/npm/katex@0.18.7/dist/katex.min.js

SHA-256: `10a91b479cd927446ceb60409fb0d72b5d0d05eaf446c9e52fafd64058c84540`

Upstream source: https://github.com/KaTeX/KaTeX/tree/v0.18.7

License: MIT; the complete upstream notice is in [KATEX-LICENSE](KATEX-LICENSE).
The distribution bytes and version were checked during release preparation.

Pandoc extracts mathematical spans from Markdown; `scripts/check_tex.js` asks
this pinned KaTeX build whether those expressions render. Using Pandoc's texmath
conversion alone can reject formulas supported by KaTeX. This check describes
KaTeX compatibility, not a guarantee about every Markdown viewer. No CSS/fonts
are bundled because this module checks syntax rather than providing a web UI.
