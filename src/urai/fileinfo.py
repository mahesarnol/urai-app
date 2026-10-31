"""Mengenali jenis file dan informasi singkatnya (halaman, slide, sheet, hasil scan)."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

from .i18n import has, t
from .textutil import human_size

KIND_BY_EXT = {
    ".pdf": "pdf", ".docx": "doc", ".pptx": "ppt", ".xlsx": "xls", ".xls": "xls", ".csv": "csv",
    ".html": "html", ".htm": "html", ".epub": "epub", ".zip": "zip", ".msg": "msg",
    ".jpg": "img", ".jpeg": "img", ".png": "img", ".webp": "img", ".bmp": "img", ".tif": "img", ".tiff": "img",
    ".mp3": "aud", ".wav": "aud", ".m4a": "aud", ".mp4": "aud",
    ".txt": "text", ".md": "text", ".json": "text", ".jsonl": "text", ".xml": "text", ".ipynb": "text",
    ".rss": "text", ".atom": "text",
}
BADGE = {
    "pdf": "PDF", "doc": "DOC", "ppt": "PPT", "xls": "XLS", "csv": "CSV", "html": "HTM", "epub": "EPUB",
    "zip": "ZIP", "msg": "MSG", "img": "IMG", "aud": "AUD", "text": "TXT", "yt": "", "web": "WEB",
}
SUPPORTED_EXT = frozenset(KIND_BY_EXT)
SCAN_CHARS = 25  # halaman dengan teks lebih sedikit dari ini dianggap hasil scan


def kind_of(path: str | Path) -> str | None:
    return KIND_BY_EXT.get(Path(path).suffix.lower())


def kind_label(kind: str) -> str:
    """Nama jenis dalam bahasa aktif, mis. "img" -> "Image" atau "Gambar"."""
    return t(f"kind.{kind}") if has(f"kind.{kind}") else t("kind.file")


def meta_text(kind: str, size: int = 0, facts: dict | None = None) -> str:
    """Keterangan singkat di daftar, mis. "PDF · 3 pages · 1.2 MB", dalam bahasa aktif.
    facts: pages, slides, sheets, dims (disimpan di Item supaya bisa disusun ulang saat bahasa diganti)."""
    f = facts or {}
    parts = [kind_label(kind)]
    if f.get("pages") is not None:
        parts.append(t("meta.pages", n=f["pages"]))
    if f.get("slides"):
        parts.append(t("meta.slides", n=f["slides"]))
    if f.get("sheets"):
        parts.append(t("meta.sheets", n=f["sheets"]))
    if f.get("dims"):
        parts.append(f["dims"])
    if size:
        parts.append(human_size(size))
    return " · ".join(parts)


def pdf_text_lengths(path: str | Path, limit: int | None = None) -> list[int]:
    """Jumlah karakter teks per halaman PDF (0 berarti halaman tanpa teks, kemungkinan hasil scan)."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(path))
    try:
        n = len(doc)
        out = []
        for i in range(n if limit is None else min(n, limit)):
            page = doc[i]
            tp = page.get_textpage()
            out.append(len(re.sub(r"\s+", "", tp.get_text_range())))
            tp.close()
            page.close()
        return out
    finally:
        doc.close()


def pdf_page_count(path: str | Path) -> int:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(path))
    try:
        return len(doc)
    finally:
        doc.close()


def _zip_count(path: Path, pattern: str) -> int:
    try:
        with zipfile.ZipFile(path) as z:
            return sum(1 for n in z.namelist() if re.fullmatch(pattern, n))
    except Exception:
        return 0


def inspect_file(path: str | Path) -> dict:
    """Informasi singkat untuk ditampilkan di daftar. Tidak pernah melempar error."""
    p = Path(path)
    kind = kind_of(p) or "text"
    info = {"kind": kind, "label": kind_label(kind), "badge": BADGE.get(kind, "FILE"),
            "size": 0, "pages": None, "scan": False, "scan_pages": 0, "exp": kind == "aud", "meta": "", "facts": {}}
    try:
        info["size"] = p.stat().st_size
    except OSError:
        pass
    facts = info["facts"]
    try:
        if kind == "pdf":
            lens = pdf_text_lengths(p, limit=40)
            total = pdf_page_count(p)
            info["pages"] = total
            scanned = sum(1 for n in lens if n < SCAN_CHARS)
            info["scan_pages"] = scanned
            info["scan"] = bool(lens) and scanned / len(lens) >= 0.5
            info["mixed"] = 0 < scanned and not info["scan"]
            facts["pages"] = total
        elif kind == "ppt":
            facts["slides"] = _zip_count(p, r"ppt/slides/slide\d+\.xml")
        elif kind == "xls" and p.suffix.lower() == ".xlsx":
            facts["sheets"] = _zip_count(p, r"xl/worksheets/sheet\d+\.xml")
        elif kind == "img":
            from PIL import Image

            with Image.open(p) as im:
                facts["dims"] = f"{im.width}×{im.height}"
    except Exception:
        pass
    info["meta"] = meta_text(kind, info["size"], facts)
    return info


MEDIA_DIRS = ("word/media/", "ppt/media/", "xl/media/")
MEDIA_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")


def embedded_images(path: str | Path, limit: int = 40, min_side: int = 120) -> list[tuple[str, bytes]]:
    """Gambar di dalam file Word/PowerPoint/Excel yang cukup besar untuk dibaca."""
    from io import BytesIO

    from PIL import Image

    out: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(path) as z:
            names = sorted(n for n in z.namelist() if n.startswith(MEDIA_DIRS) and n.lower().endswith(MEDIA_EXT))
            for n in names:
                data = z.read(n)
                try:
                    with Image.open(BytesIO(data)) as im:
                        if min(im.size) < min_side // 2 or max(im.size) < min_side:
                            continue
                except Exception:
                    continue
                out.append((n.rsplit("/", 1)[-1], data))
                if len(out) >= limit:
                    break
    except Exception:
        return []
    return out
