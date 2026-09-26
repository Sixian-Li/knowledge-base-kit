# Knowledge Base Kit

**用 Claude Code 或 Codex，把文档整理成保留来源、可查阅的本地 Markdown 知识库。**
每篇文档保留原件、详细的 `full.md` 和便于快速查阅的 `summary.md`；agent 按
“目录 → 摘要 → 全文”逐层读取。

[English](README.md) · [安装](docs/installation.md) · [示例](examples/README.md) · [已知限制](docs/limitations.md)

![原始资料经 Claude Code 或 Codex 整理和审核，形成保留原件、全文、摘要与目录的本地知识库。](docs/assets/overview.zh-CN.svg)

## 提供什么

- **共用的 agent 技能。** 项目内的 `process_docs` 写入技能和 `kb` 读取技能，两种 agent 共用一份实现。
- **多格式内容提取。** 支持 PDF、DOCX、静态 HTML、Notebook、文本和图片。
- **隔离的图片 worker。** 一图一 worker，显式选择后端、超时停止、最多一次重试、按来源校验缓存。
- **入库前校验。** 检查文档结构、链接、原文存档折叠和 TeX 公式。
- **独立的资料工作区。** 工具仓库与私人资料库分开，方便升级和分享。

这是 **agent 辅助的工作流**：主 agent 负责撰写与核对全文、摘要，脚本负责提取、
图片 worker 和校验。它不是无人审核的一键入库引擎；结构校验不能证明内容完整、准确。

## 快速开始

需要 Python 3.10+、Node.js 20+、Pandoc 3+；实际模型处理还需要已登录的 Claude Code
或 Codex CLI。先下载或克隆本仓库。具体已验证版本见[兼容性记录](docs/compatibility.md)。

```sh
cd knowledge-base-kit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/init_workspace.py ../my-kb --backend codex --language zh-CN --with-example
cd ../my-kb
python kb.py check --backend codex
```

使用 Claude 时改为 `--backend claude`，两者都用则选 `both`。初始化器会复制技能，
建立项目内的相对软链接；不会修改全局 agent 配置或另一个知识库，也不会接管已有的陌生目录。

### 处理第一篇文档

在 `my-kb` 中打开 agent，输入：

> 使用本项目的 process_docs 技能和 Codex 后端处理 inbox/quickstart.md。生成全文和摘要，
> 展示建议分类、草稿和具体改动文件，等我审核后再入库。

### 先试离线演示

只想先看效果，可以在安装依赖和 Node/Pandoc 后，从工具仓库目录运行完全离线的演示：

```sh
python scripts/offline_demo.py ../kb-demo
```

演示会提取自制 Markdown、复制经过审阅的参考产物并运行校验，**不会调用模型，也不会假装
执行了 AI 生成**。可先看[参考全文](examples/expected-output/quickstart/full.md)与
[参考摘要](examples/expected-output/quickstart/summary.md)。

## 工作原理

![提取原稿，有图片时一图一 worker；主 agent 对照来源撰写全文和摘要，核对与校验后入库并更新关联，需要修改时返回草稿。](docs/assets/workflow.zh-CN.svg)

工作区包含 `inbox/`、`catalog.md`、知识分类和独立的 `.kbkit/` 安装目录。
每篇文档保留 `full.md`、`summary.md` 和原始附件，每个分类都有 `README.md`。
读取时先查目录，再看摘要，必要时展开全文。[架构](docs/architecture.md)解释脚本与 agent 的边界；
[工作流](docs/workflows.md)说明操作细节。

## 配置与隐私

配置文件是工作区根目录的 `kb.config.yaml`，所有相对路径都以该文件指定的库根为基准。
默认沿用 CLI 的模型，需要时改成你的账号可用的视觉模型；项目不内置账号或密钥。

图片 worker 会把图片与少量文档上下文发送给所选服务商，主 agent 的文本处理也遵循其服务条款。
“本地知识库”指文件保存在本地，不代表模型推理完全离线。不要把自己的资料工作区、日志或
账号信息提交到本工具仓库。详见[配置](docs/configuration.md)与[安全说明](SECURITY.md)。

## 开发

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/validate_release.py
```

测试离线运行，使用模拟 CLI 进程；GitHub Actions 无需模型凭据即可执行相同检查。
详见[贡献指南](CONTRIBUTING.md)、[维护说明](docs/maintaining.md)与[发布指南](docs/publishing.md)。

## 许可证

原创代码和文档采用 [AGPL-3.0-only](LICENSE)。PyMuPDF、html2text 保留各自 GPL 系许可证，
随包附带的 KaTeX 保留 MIT 许可和署名，详见[第三方声明](THIRD_PARTY_NOTICES.md)。
软件许可证不会自动改变你自己的原始文档或知识内容的权属。
