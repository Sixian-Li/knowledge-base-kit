"""Static HTML extraction. No network requests or JavaScript execution."""
import base64
from pathlib import Path
from urllib.parse import unquote, unquote_to_bytes, urlsplit

from bs4 import BeautifulSoup
import html2text

MIME_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
            "image/webp": ".webp", "image/bmp": ".bmp", "image/tiff": ".tiff"}


def extract(source, output_dir):
    source, output = Path(source).resolve(), Path(output_dir).resolve()
    soup = BeautifulSoup(source.read_bytes(), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    images, failed, warnings = [], [], []
    for number, tag in enumerate(soup.find_all("img"), 1):
        src = tag.get("src", "")
        try:
            if src.startswith("data:"):
                header, payload = src.split(",", 1)
                mime = header[5:].split(";")[0].lower()
                ext = MIME_EXT.get(mime)
                if not ext:
                    raise ValueError("Unsupported inline image MIME type")
                data = base64.b64decode(payload, validate=True) if ";base64" in header else unquote_to_bytes(payload)
            else:
                url = urlsplit(src)
                if url.scheme or url.netloc or not url.path:
                    raise ValueError("Remote or missing image; download an authorized local copy first")
                path = (source.parent / unquote(url.path)).resolve()
                if not path.is_relative_to(source.parent):
                    raise ValueError("Image path leaves the source folder")
                ext, data = path.suffix.lower(), path.read_bytes()
                if ext not in set(MIME_EXT.values()) | {".jpeg"}:
                    raise ValueError("Unsupported image format")
            if not data:
                raise ValueError("Empty image")
            path = output / "images" / f"image_{number}{ext}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            images.append({"page": number, "path": str(path), "size": len(data), "alt": tag.get("alt", "")})
            tag["src"] = path.relative_to(output).as_posix()
            tag["alt"] = f"Image {number}: " + tag.get("alt", "")
        except (OSError, ValueError) as exc:
            failed.append({"page": number, "error": str(exc)})
            tag.replace_with(soup.new_string(f"[Image {number} unavailable: {tag.get('alt', '')}]"))
    if soup.find(["svg", "canvas", "iframe", "video", "audio"]):
        warnings.append("Embedded SVG, canvas, frames or media need source review; they are not rendered.")
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = False
    converter.ignore_links = False
    converter.protect_links = True
    return {"text": converter.handle(str(soup)), "image_files": images,
            "failed_images": failed, "warnings": warnings}
