# Third-party notices

Original Knowledge Base Kit code and documentation are licensed under
AGPL-3.0-only. Copyright (c) 2026 Knowledge Base Kit contributors. Third-party
components retain their own licenses; the root LICENSE does not relicense them.

## Bundled code

- KaTeX 0.18.7, MIT, Copyright (c) 2013–2020 Khan Academy and other contributors.
  The distributed `skills/process_docs/vendor/katex.min.js` is accompanied by the
  complete [MIT notice](skills/process_docs/vendor/KATEX-LICENSE). Source and hash
  are recorded in [vendor README](skills/process_docs/vendor/README.md).

## Python dependencies (installed separately)

| Package | License | Upstream |
| --- | --- | --- |
| PyMuPDF | AGPL-3.0 or a commercial license | https://pymupdf.io/licensing |
| html2text | GPL-3.0-or-later | https://github.com/Alir3z4/html2text |
| python-docx | MIT | https://github.com/python-openxml/python-docx |
| beautifulsoup4 | MIT | https://www.crummy.com/software/BeautifulSoup/ |
| PyYAML | MIT | https://github.com/yaml/pyyaml |
| lxml (transitive) | BSD-3-Clause; bundled libxml2/libxslt carry their own notices | https://lxml.de/ |
| soupsieve (transitive) | MIT | https://github.com/facelessuser/soupsieve |
| typing_extensions (transitive) | PSF-2.0 | https://github.com/python/typing_extensions |

Packages are obtained from their upstream distributions, including their license
files. This repository does not vendor their wheels. Development-only fixture
helpers are ReportLab (BSD), Pillow (MIT-CMU), pypdf (BSD-3-Clause), pdf2image (MIT)
and charset-normalizer (MIT); see the installed distributions for complete notices.

Node.js, Pandoc, optional R/rmarkdown, Claude Code and Codex are separate tools and
are not distributed in this archive. Their terms and provider account conditions
are separate from this project's license. The GPL-family dependencies are why this
release is offered as AGPL rather than represented as a permissively licensed kit.
The AGPL applies to the software; it does not automatically change ownership of
input documents or generated knowledge content. Distribute only documents you
have rights to share.
