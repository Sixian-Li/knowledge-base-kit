# Examples / 示例

All inputs here were authored for this project. No personal knowledge base,
course material, account data or third-party document is included.

| Source | What it exercises |
| --- | --- |
| [quickstart.md](sources/quickstart.md) | Text, ordered steps, a small table, math and a zero value |
| [sample.pdf](sources/sample.pdf) | Two pages: table/formula and a vector workflow diagram |
| [sample.docx](sources/sample.docx) | Paragraph → table → paragraph → inline image → paragraph |
| [sample.html](sources/sample.html) | Static table, internal anchor and a data-URI image |
| [sample.ipynb](sources/sample.ipynb) | Saved text/image outputs with null execution counts |

Review the [quickstart full text](expected-output/quickstart/full.md) and
[summary](expected-output/quickstart/summary.md), or the
[PDF full text](expected-output/pdf/full.md) and [summary](expected-output/pdf/summary.md).
These are reviewed reference outputs, not exact model-output snapshots or a
promise that every model will produce identical prose. Source attachments are
copied alongside them when filing; they remain in `sources/` in this repository.

Run `python scripts/offline_demo.py NEW_WORKSPACE` to extract the Markdown,
copy its reference output, validate the draft, file it and verify the resulting
tree. This does not invoke a model. Real PDF workers require an authenticated CLI
and send one page image per session to the selected provider.

To rebuild source fixtures after an intentional edit, install
`requirements-dev.txt` and run `python scripts/build_examples.py`. Check PDF/DOCX
rendering after changes and compare expected outputs. Do not treat a fixture
rebuild as evidence that its rendered pages were inspected.

中文：所有输入都是本项目自制示例，可公开分发。离线演示复制的是已审阅参考产物，不冒充
模型生成。PDF 的真实识读需登录所选 CLI，可能产生相应服务使用量。
