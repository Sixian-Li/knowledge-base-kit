"""Extract DOCX body order, tables and inline images without executing content."""
from pathlib import Path
import zipfile

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.table import Table


def extract(source, output_dir):
    document = Document(source)
    output = Path(output_dir).resolve()
    images, failed, warnings, chunks = [], [], [], []
    counter = 0

    def paragraph(element, part):
        nonlocal counter
        text = []
        for node in element.iter():
            if node.tag == qn("w:t"):
                text.append(node.text or "")
            elif node.tag == qn("w:tab"):
                text.append("\t")
            elif node.tag in (qn("w:br"), qn("w:cr")):
                text.append("\n")
            elif node.tag in (qn("w:footnoteReference"), qn("w:endnoteReference")):
                text.append(f" [note {node.get(qn('w:id'))}] ")
            elif node.tag == qn("a:blip"):
                counter += 1
                try:
                    rid = node.get(qn("r:embed"))
                    image = part.related_parts[rid]
                    ext = Path(str(image.partname)).suffix.lower()
                    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"):
                        raise ValueError(f"Unsupported embedded image {ext}; export the page or image as PNG")
                    path = output / "images" / f"image_{counter}{ext}"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(image.blob)
                    images.append({"page": counter, "path": str(path), "size": len(image.blob)})
                    text.append(f"\n\n![Image {counter}]({path.relative_to(output).as_posix()})\n\n")
                except (KeyError, ValueError) as exc:
                    failed.append({"page": counter, "error": str(exc)})
                    text.append(f"[Image {counter} unavailable]")
        return "".join(text)

    def blocks(container):
        result = []
        for block in container.iter_inner_content():
            if isinstance(block, Table):
                rows = []
                for row in block.rows:
                    cells = ["<br>".join(blocks(cell)).replace("|", "\\|").replace("\n", "<br>") for cell in row.cells]
                    rows.append("| " + " | ".join(cells) + " |")
                if rows:
                    rows.insert(1, "| " + " | ".join("---" for _ in block.rows[0].cells) + " |")
                    result.append("\n".join(rows))
            else:
                content = paragraph(block._p, block.part)
                style = block.style.name if block.style else ""
                if style.startswith("Heading ") and style.split()[-1].isdigit():
                    content = "#" * min(6, int(style.split()[-1])) + " " + content
                if content:
                    result.append(content)
        return result

    chunks.extend(blocks(document))
    seen = set()
    for section in document.sections:
        for name in ("header", "footer", "first_page_header", "first_page_footer", "even_page_header", "even_page_footer"):
            item = getattr(section, name)
            if item.is_linked_to_previous:
                continue
            key = str(item.part.partname)
            if key not in seen:
                seen.add(key)
                content = blocks(item)
                if content:
                    chunks.extend([f"## {name.replace('_', ' ').title()}", *content])
    with zipfile.ZipFile(source) as archive:
        for name in ("word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"):
            if name in archive.namelist():
                xml = parse_xml(archive.read(name))
                content = ["".join(p.itertext()) for p in xml.iter(qn("w:p"))]
                chunks.extend([f"## {Path(name).stem.title()}", *content])
                warnings.append(f"Review note/comment numbering against {name}; complex layouts need visual comparison.")
        body = archive.read("word/document.xml")
        if any(tag in body for tag in (b"<w:ins", b"<w:del", b"<m:oMath", b"<w:txbxContent", b"<c:chart")):
            warnings.append("Tracked changes, equations, text boxes or charts detected; export to PDF and review visually.")
    return {"text": "\n\n".join(chunks) + "\n", "image_files": images,
            "failed_images": failed, "warnings": warnings}
