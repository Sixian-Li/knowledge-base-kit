#!/usr/bin/env python3
"""Regenerate the English and Chinese README diagrams (Python standard library)."""

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs" / "assets"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', 'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei', sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', monospace"
LIGHT = {
    "bg": "#fbfcfd", "ink": "#19313f", "muted": "#586c78", "line": "#d7e2e8",
    "paper": "#ffffff", "blue": "#285d92", "blue-soft": "#eaf2fa",
    "teal": "#147566", "teal-soft": "#e8f5ef", "amber": "#985818", "amber-soft": "#fff5e7",
}
DARK = {
    "bg": "#101820", "ink": "#e3edf3", "muted": "#a1b4bf", "line": "#344854",
    "paper": "#192630", "blue": "#99c7f0", "blue-soft": "#20374b",
    "teal": "#82d9bb", "teal-soft": "#193c35", "amber": "#edbd7d", "amber-soft": "#3b2f22",
}
# Literal light-mode attributes remain readable in SVG renderers without CSS
# variables or media-query support. Browsers can apply the dark-mode classes.
STYLE = "text { font-kerning: normal; }\n@media (prefers-color-scheme: dark) {\n" + "\n".join(
    f"  .fill-{name} {{ fill: {value}; }} .stroke-{name} {{ stroke: {value}; }}"
    for name, value in DARK.items()
) + "\n}"


class Drawing:
    def __init__(self, height, title, description, lang):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height}" '
            f'viewBox="0 0 1120 {height}" role="img" aria-labelledby="title desc" lang="{lang}">',
            f"<title id=\"title\">{escape(title)}</title>",
            f"<desc id=\"desc\">{escape(description)}</desc>",
            f"<style>{STYLE}</style>",
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" '
            'orient="auto-start-reverse"><path d="M1 1L6 4L1 7" fill="none" '
            f'stroke="{LIGHT["muted"]}" class="stroke-muted" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>',
            '<marker id="revise" markerWidth="8" markerHeight="8" refX="6" refY="4" '
            f'orient="auto"><path d="M1 1L6 4L1 7" fill="none" stroke="{LIGHT["amber"]}" class="stroke-amber" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>',
        ]
        self.box(1, 1, 1118, height - 2, "bg", 20, "line")

    def text(self, x, y, value, size=20, weight=400, color="ink", mono=False, spacing=None):
        tracking = f' letter-spacing="{spacing}"' if spacing is not None else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{escape(MONO if mono else FONT, quote=True)}" '
            f'font-size="{size}" font-weight="{weight}" fill="{LIGHT[color]}" class="fill-{color}"{tracking}>'
            f"{escape(value)}</text>"
        )

    def box(self, x, y, width, height, color="paper", radius=14, border=None):
        stroke = f' stroke="{LIGHT[border]}"' if border else ""
        classes = f'fill-{color}' + (f' stroke-{border}' if border else "")
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
            f'fill="{LIGHT[color]}" class="{classes}"{stroke}/>'
        )

    def path(self, d, color="line", width=2, arrow=None, dashed=False):
        marker = f' marker-end="url(#{arrow})"' if arrow else ""
        dash = ' stroke-dasharray="5 6"' if dashed else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{LIGHT[color]}" class="stroke-{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"{marker}{dash}/>'
        )

    def icon(self, name, x, y, color="teal", scale=1):
        paths = {
            "file": "M6 3H17L24 10V29H6Z M17 3V10H24 M11 16H19 M11 21H19",
            "notebook": "M8 4H26V28H8Z M4 9H11 M4 16H11 M4 23H11 M16 11H21 M16 17H21",
            "image": "M4 5H28V27H4Z M4 23L12 15L18 21L23 16L28 21 M21 10H21.01",
            "draft": "M5 7H21V28H5Z M11 3H27V23 M10 13H16 M10 18H16 M10 23H14",
            "check": "M28 16A12 12 0 1 1 4 16A12 12 0 1 1 28 16 M10 16L14 20L22 12",
            "folder": "M3 8H13L17 12H29V27H3Z M3 8V5H13L17 9H27V12",
        }
        self.parts.append(f'<g transform="translate({x} {y}) scale({scale})">')
        self.path(paths[name], color, 1.8)
        self.parts.append("</g>")

    def write(self, name):
        (DEST / name).write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def overview(zh=False):
    title = "保留来源，让知识随时可查。" if zh else "Keep the source. Find the answer."
    description = (
        "原始文档交给 Claude Code 或 Codex 提取、撰写和核对；经审核后存入本地知识库，保留原件、全文、摘要和目录。读取时依次查阅目录、摘要和全文。"
        if zh else
        "Source documents are extracted, drafted and reviewed with Claude Code or Codex. "
        "The local workspace keeps original attachments, full text, summaries and a catalog. "
        "Read the catalog first, then a summary, then the full document."
    )
    d = Drawing(558, title, description, "zh-CN" if zh else "en")
    d.text(48, 43, "从原稿到知识" if zh else "SOURCE TO KNOWLEDGE", 14, 600, "teal", spacing=1.6)
    d.text(840, 43, "CLAUDE CODE / CODEX", 14, 500, "muted", spacing=0.6)
    d.text(48, 100, title, 35, 650)
    d.text(48, 138, "原始文件、经过核对的 Markdown，以及 agent 能逐层查阅的目录。" if zh else
           "Original files, reviewed Markdown, and a catalog your agents can navigate.", 20, color="muted")
    d.path("M48 172H1072", width=1)
    for x, label in [(48, "01 / 原始资料" if zh else "01 / SOURCES"),
                     (372, "02 / AGENT 整理" if zh else "02 / AGENT WORKFLOW"),
                     (768, "03 / 本地知识库" if zh else "03 / LOCAL KNOWLEDGE")]:
        d.text(x, 210, label, 14, 600, "muted", spacing=0.8)

    sources = [
        ("file", "文档" if zh else "Documents", "PDF · DOCX · HTML"),
        ("notebook", "笔记本" if zh else "Notebooks", "IPYNB · R Markdown"),
        ("image", "文本与图片" if zh else "Text & images", "Markdown · 图片" if zh else "Markdown · images"),
    ]
    for index, (icon, label, formats) in enumerate(sources):
        y = 245 + index * 76
        d.box(48, y, 48, 48, "blue-soft", 12)
        d.icon(icon, 56, y + 8, "blue")
        d.text(111, y + 17, label, 23, 600)
        d.text(111, y + 43, formats, 17, color="muted")

    d.path("M315 346H350", "muted", arrow="arrow")
    d.box(372, 236, 324, 220, "paper", 16, "line")
    d.icon("draft", 394, 259)
    d.text(441, 282, "整理、核对、审核" if zh else "Draft, check, review", 23, 600)
    d.path("M396 304H672", width=1)
    for y, line in zip([338, 377, 416],
                       ["提取内容，撰写草稿", "对照原稿核查内容", "审核分类与入库改动"] if zh else
                       ["Extract and draft", "Compare with the source", "Review before filing"]):
        d.path(f"M397 {y - 7}l4 4l8 -9", "teal", 2)
        d.text(425, y, line, 19)
    d.path("M710 346H746", "muted", arrow="arrow")

    d.box(768, 236, 304, 220, "teal-soft", 16)
    d.icon("folder", 790, 253)
    d.text(837, 278, "my-kb/", 23, 600, "teal", mono=True)
    d.path("M790 297H1050", "line", 1)
    d.path("M797 316V342H811 M821 361V428 M821 369H835 M821 398H835 M821 427H835", "teal", 1.3)
    d.text(814, 322, "catalog.md", 19, mono=True)
    d.text(814, 351, "topic/document/", 19, mono=True)
    for y, line in zip([376, 405, 434], ["full.md", "summary.md", "original.pdf"]):
        d.text(841, y, line, 18, mono=True)

    d.path("M48 488H1072", width=1)
    d.text(48, 525, "按需逐层读取" if zh else "READ IN LAYERS", 14, 600, "teal", spacing=1)
    d.text(242, 526, "catalog.md  →  summary.md  →  full.md", 20, mono=True)
    d.write("overview.zh-CN.svg" if zh else "overview.svg")


def workflow(zh=False):
    title = "从收件箱，到经过核对的知识。" if zh else "From inbox to reviewed knowledge."
    description = (
        "第一步提取内容，有图片时一图一 worker；第二步主 agent 对照来源撰写全文和摘要；第三步核对来源并完成结构、链接、TeX 校验和入库审核。需要修改时回到草稿，审核通过后保留原件、入库并更新目录和关联。"
        if zh else
        "Extract sources, using one worker per image when needed. The main agent drafts full text "
        "and a summary against the sources. Review the sources and proposed filing, and validate "
        "structure, links and TeX. Revise the draft when needed; after review, file the document, "
        "keep the original, and update the catalog and related-document links."
    )
    d = Drawing(586, title, description, "zh-CN" if zh else "en")
    d.text(48, 43, "每一步都可核对" if zh else "A REVIEWABLE WORKFLOW", 14, 600, "teal", spacing=1.6)
    d.text(48, 98, title, 35, 650)
    d.text(48, 135, "脚本准备材料，主 agent 撰写，你审核入库结果。" if zh else
           "Scripts prepare the material. The main agent drafts. You review the result.", 20, color="muted")

    d.path("M910 225V198Q910 186 898 186H546Q534 186 534 198V225", "amber", 1.6, "revise", True)
    d.box(644, 170, 212, 28, "bg", 0)
    d.text(656, 190, "需要修改时返回草稿" if zh else "Revise when needed", 17, 500, "amber")

    stages = [
        (48, "blue-soft", "blue", "file", "01", "提取原稿" if zh else "Extract sources",
         ["提取文字，渲染页面。", "有图片时，一图一 worker。"] if zh else
         ["Extract text and render pages.", "One worker per image, if needed."],
         "脚本 + 图片 WORKER" if zh else "SCRIPTS + IMAGE WORKERS"),
        (408, "paper", "teal", "draft", "02", "对照来源撰写" if zh else "Draft in context",
         ["主 agent 对照原始资料，", "生成全文和实用摘要。"] if zh else
         ["The main agent uses the sources", "to write full text and a summary."],
         "主 AGENT" if zh else "MAIN AGENT"),
        (768, "amber-soft", "amber", "check", "03", "核对与校验" if zh else "Review & validate",
         ["核对来源、结构、链接与公式，", "审核分类和具体入库改动。"] if zh else
         ["Check sources, structure, links", "and TeX; review the filing plan."],
         "你 + 校验脚本" if zh else "YOU + VALIDATORS"),
    ]
    for x, bg, color, icon, number, heading, lines, role in stages:
        d.box(x, 225, 304, 218, bg, 16, "line" if bg == "paper" else None)
        d.icon(icon, x + 22, 246, color)
        d.text(x + 246, 272, number, 17, 600, color, mono=True)
        d.text(x + 22, 311, heading, 24, 600)
        for y, line in zip([349, 376], lines):
            d.text(x + 22, y, line, 17, color="muted")
        d.text(x + 22, 415, role, 12.5, 600, color, spacing=0.6)
    d.path("M366 332H393", "muted", arrow="arrow")
    d.path("M726 332H753", "muted", arrow="arrow")
    d.path("M920 443V477", "muted", arrow="arrow")
    d.text(942, 469, "审核后" if zh else "after review", 15, 500, "muted")

    d.box(48, 491, 1024, 68, "teal-soft", 14)
    d.icon("folder", 68, 509)
    d.text(122, 519, "入库并建立关联" if zh else "File & link", 22, 600, "teal")
    d.text(122, 546, "保留原件，更新目录，连接相关文档。" if zh else
           "Keep the original, update the catalog, and link related documents.", 18, color="muted")
    d.text(1010, 532, "04", 19, 600, "teal", mono=True)
    d.write("workflow.zh-CN.svg" if zh else "workflow.svg")


if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    for chinese in (False, True):
        overview(chinese)
        workflow(chinese)
    print("Built four README diagrams in docs/assets/.")
