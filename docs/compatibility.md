# Compatibility and validation record

Release: **0.1.1**. Live backend validation: **2026-09-23** (0.1.0).
Offline validation of 0.1.1: **2026-09-26**.

| Component | Locally exercised version / result |
| --- | --- |
| OS | macOS 14.4, Apple Silicon |
| Python | 3.13.9, isolated venv |
| Node.js | 26.0.0 |
| Pandoc | 3.8 |
| PyMuPDF | 1.28.2 |
| python-docx | 1.2.0 |
| Beautiful Soup | 4.15.0 on main (offline suite and HTML example); 4.13.5 in the live runs |
| html2text | 2025.4.15 |
| PyYAML | 6.0.3 |
| Bundled KaTeX | 0.18.7; exact distribution hash verified |
| Codex CLI | 0.155.1; authenticated, two PDF page workers passed |
| Claude Code CLI | 2.1.280; authenticated, two PDF page workers passed |

The live test used the two-page self-authored PDF in `examples/sources`. Both
backends used their account's CLI default model (no public model override),
English output instructions and a 180-second timeout. All four image sessions
succeeded on their first attempt; no retries, account switches or permission
widening were needed. Descriptions were compared to both rendered pages for table
values, the 0.00 control value, formula text, all nodes/arrows and both branches.
This small fixture is a smoke test, not a broad accuracy benchmark or a guarantee
about every default model. No private source material was sent in these tests.

The public test suite uses fake CLI executables and no network/model calls.
It covers configuration, isolated initialization, update conflicts, relative
links, extraction order, saved notebook output, non-execution, cache provenance,
transient retries, auth/quota/startup failures, child-process timeout cleanup,
source preservation, corrupt-image rejection, structural checks and TeX syntax.
PDF pages and the DOCX example were rendered and visually inspected; DOCX used
the available bundled LibreOffice renderer, not an unverified conversion claim.

Hosted GitHub Actions ran the offline suite, release check, offline demo and
archive build for 0.1.0 on Ubuntu and macOS with Python 3.10/3.13 and Node 24;
all four jobs passed. For 0.1.1 the offline suite (51 tests) passed locally on
Python 3.10.20 and 3.13.9; see the repository's Actions page for its hosted runs.
0.1.1 changes extraction, validation and installation, not the worker protocol;
the live backend runs above were not repeated. Only the local versions above
have live backend evidence.
Native Windows, older CLIs, Rmd execution, Chinese live worker output and complex
real-world format variants have not been tested as part of this release.

中文：双后端各两页、共四次真实 worker 首试通过；自动测试不调用模型。以上是实际测试记录，
不是对所有系统、CLI 版本和文档的兼容性承诺。0.1.0 的四组 GitHub 托管 CI 已全部通过；
0.1.1 未改 worker 协议，未重跑真实 worker，离线测试在 Python 3.10/3.13 本地通过。
