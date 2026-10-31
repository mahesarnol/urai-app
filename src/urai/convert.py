"""Inti konversi: dokumen dan link menjadi Markdown, termasuk baca scan (OCR) dan gabung file."""
from __future__ import annotations

import concurrent.futures as cf
import io
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image

from . import ai as ai_mod
from .errors import Cancelled, OcrUnavailable, friendly_error
from .fileinfo import SCAN_CHARS, embedded_images, inspect_file, pdf_text_lengths
from .links import host_of, is_youtube
from .ocr import DPI, LANG_NAMES, engine, worker_count
from .paths import default_output_dir
from .textutil import base_name, build_combined, safe_filename, unique_path, word_count

log = logging.getLogger("urai.convert")
Emit = Callable[[str, dict], None]


@dataclass
class Item:
    id: str
    source: str
    is_link: bool
    kind: str
    name: str
    meta: str
    badge: str
    size: int = 0
    pages: int | None = None
    scan: bool = False
    mixed: bool = False
    exp: bool = False
    status: str = "idle"  # idle | wait | work | done | warn | error
    sub: str = ""
    words: int = 0
    message: str = ""
    fix: str = ""  # tindakan perbaikan yang ditawarkan, mis. "ocr"
    output: str = ""
    title: str = ""
    result: str = field(default="", repr=False)

    def public(self) -> dict:
        d = asdict(self)
        d.pop("result")
        d["display"] = self.display_name
        return d

    @property
    def display_name(self) -> str:
        return (self.title or self.name) if self.is_link else self.name

    def reset(self) -> None:
        self.status, self.sub, self.words, self.message, self.fix, self.output, self.result = "idle", "", 0, "", "", "", ""


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


def item_from_path(path: str | Path) -> Item:
    p = Path(path)
    info = inspect_file(p)
    return Item(id=_new_id(), source=str(p), is_link=False, kind=info["kind"], name=p.name, meta=info["meta"],
                badge=info["badge"], size=info["size"], pages=info["pages"], scan=info["scan"],
                mixed=bool(info.get("mixed")), exp=info["exp"])


def item_from_link(url: str) -> Item:
    yt = is_youtube(url)
    host = host_of(url)
    return Item(id=_new_id(), source=url, is_link=True, kind="yt" if yt else "web",
                name="Video YouTube" if yt else f"Halaman {host}",
                meta=f"Link YouTube · {host}" if yt else f"Link halaman web · {host}",
                badge="" if yt else "WEB", exp=yt)


@dataclass
class Options:
    ocr_mode: str = "offline"  # off | offline | ai
    langs: list[str] = field(default_factory=lambda: ["ind", "eng"])
    quality: str = "fast"  # fast | accurate
    embedded: bool = True
    ai: ai_mod.AIConfig | None = None
    out_mode: str = "separate"  # separate | combined
    combined_name: str = "Gabungan"
    location: str = "custom"  # same | custom
    custom_dir: str = ""


_MD = None
_MD_LOCK = threading.Lock()


def markitdown():
    """Satu mesin MarkItDown dipakai ulang (memuatnya butuh beberapa detik)."""
    global _MD
    with _MD_LOCK:
        if _MD is None:
            from markitdown import MarkItDown

            _MD = MarkItDown(enable_plugins=False)
        return _MD


def _md_text(res) -> str:
    return (getattr(res, "markdown", None) or getattr(res, "text_content", "") or "").strip()


class Converter:
    def __init__(self, opts: Options, emit: Emit, cancel: threading.Event):
        self.opts = opts
        self.emit = emit
        self.cancel = cancel
        self._langs: list[str] | None = None

    # ---------- OCR engine ----------
    def _check(self) -> None:
        if self.cancel.is_set():
            raise Cancelled()

    def _ocr_label(self) -> str:
        if self.opts.ocr_mode == "ai" and self.opts.ai:
            return f"AI ({self.opts.ai.name})"
        names = ", ".join(LANG_NAMES.get(l, l) for l in self.langs())
        return f"OCR offline ({names})"

    def langs(self) -> list[str]:
        if self._langs is None:
            self._langs = engine().pick_langs(self.opts.langs)
        return self._langs

    def _use_ai(self) -> bool:
        return self.opts.ocr_mode == "ai" and self.opts.ai is not None and self.opts.ai.ready

    def read_images(self, images: list[Image.Image], progress: Callable[[int, int], None]) -> list[str]:
        """Baca teks dari banyak gambar. Offline dijalankan paralel, AI satu per satu."""
        total = len(images)
        if self._use_ai():
            out = []
            for k, img in enumerate(images, 1):
                self._check()
                out.append(ai_mod.vision_text(self.opts.ai, img, ai_mod.OCR_PROMPT))
                progress(k, total)
            return out
        tess = engine()
        if not tess.available:
            raise OcrUnavailable()
        langs = self.langs()
        results: list[str | None] = [None] * total
        done = 0
        with cf.ThreadPoolExecutor(max_workers=worker_count()) as ex:
            futs = {ex.submit(tess.read, img, langs): i for i, img in enumerate(images)}
            try:
                for f in cf.as_completed(futs):
                    self._check()
                    results[futs[f]] = f.result()
                    done += 1
                    progress(done, total)
            except BaseException:
                for f in futs:
                    f.cancel()
                raise
        return [r or "" for r in results]

    def ocr_pdf_pages(self, path: str, indices: list[int], item: Item) -> dict[int, str]:
        """Render halaman PDF terpilih lalu baca teksnya. PDFium tidak aman dipakai dari banyak thread,
        jadi halaman dirender bergantian di sini dan hanya pembacaannya yang paralel."""
        import pypdfium2 as pdfium

        ai = self._use_ai()
        scale = (150 if ai else DPI.get(self.opts.quality, 200)) / 72
        label = self._ocr_label()
        total = len(indices)
        results: dict[int, str] = {}
        doc = pdfium.PdfDocument(path)
        try:
            if ai:
                for k, i in enumerate(indices, 1):
                    self._check()
                    self._sub(item, f"{label} · halaman {k} dari {total}")
                    page = doc[i]
                    img = page.render(scale=scale).to_pil()
                    page.close()
                    results[i] = ai_mod.vision_text(self.opts.ai, img, ai_mod.OCR_PROMPT)
                return results
            tess = engine()
            if not tess.available:
                raise OcrUnavailable()
            langs = self.langs()
            workers = worker_count()
            pending: dict[cf.Future, int] = {}
            done = 0

            def collect(block: bool) -> None:
                nonlocal done
                if not pending:
                    return
                finished, _ = cf.wait(list(pending), return_when=cf.FIRST_COMPLETED if block else cf.ALL_COMPLETED)
                for f in finished:
                    results[pending.pop(f)] = f.result()
                    done += 1
                    self._sub(item, f"{label} · halaman {done} dari {total}")

            self._sub(item, f"{label} · halaman 0 dari {total}")
            with cf.ThreadPoolExecutor(max_workers=workers) as ex:
                try:
                    for i in indices:
                        self._check()
                        page = doc[i]
                        img = page.render(scale=scale).to_pil()
                        page.close()
                        pending[ex.submit(tess.read, img, langs)] = i
                        while len(pending) >= workers * 2:
                            self._check()
                            collect(block=True)
                    while pending:
                        self._check()
                        collect(block=True)
                except BaseException:
                    for f in pending:
                        f.cancel()
                    raise
            return results
        finally:
            doc.close()

    def _sub(self, item: Item, text: str) -> None:
        item.sub = text
        self.emit("item", item.public())

    # ---------- per jenis file ----------
    def convert_item(self, item: Item) -> str:
        if item.is_link:
            return self._convert_link(item)
        path = item.source
        mode = self.opts.ocr_mode
        if item.kind == "img":
            if mode == "off":
                return _md_text(markitdown().convert(path))
            return self._convert_image(item)
        if item.kind == "pdf" and mode != "off":
            return self._convert_pdf(item)
        if item.kind == "aud":
            self._sub(item, "Mengubah suara jadi teks (bahasa Indonesia)…")
            return _md_text(markitdown().convert(path, language="id-ID"))
        self._sub(item, "Membaca dokumen…")
        text = _md_text(markitdown().convert(path))
        if mode != "off" and self.opts.embedded and item.kind in ("doc", "ppt", "xls"):
            text = self._append_embedded(item, text)
        return text

    def _convert_link(self, item: Item) -> str:
        self._sub(item, "Mengambil judul dan transkrip…" if item.kind == "yt" else "Membaca halaman web…")
        res = markitdown().convert(item.source, youtube_transcript_languages=["id", "en"])
        title = (getattr(res, "title", None) or "").strip()
        if title:
            item.title = title
        return _md_text(res)

    def _convert_image(self, item: Item) -> str:
        self._sub(item, f"{self._ocr_label()} · membaca gambar…")
        with Image.open(item.source) as im:
            im.load()
            img = im.copy()
        if self._use_ai():
            text = ai_mod.vision_text(self.opts.ai, img, ai_mod.IMAGE_PROMPT)
        else:
            text = self.read_images([img], lambda d, t: None)[0]
        if not text.strip():
            return ""
        return f"# {base_name(item.name)}\n\n> Dibaca dengan {self._ocr_label()}\n\n{text}"

    def _convert_pdf(self, item: Item) -> str:
        path = item.source
        self._sub(item, "Memeriksa halaman…")
        lengths = pdf_text_lengths(path)
        scanned = [i for i, n in enumerate(lengths) if n < SCAN_CHARS]
        if not scanned:
            self._sub(item, f"Membaca {len(lengths)} halaman…")
            return _md_text(markitdown().convert(path))
        if not self._use_ai() and not engine().available:
            if len(scanned) >= 0.5 * len(lengths):
                raise OcrUnavailable()
            return _md_text(markitdown().convert(path))
        label = self._ocr_label()
        if len(scanned) >= 0.5 * len(lengths):
            texts = self.ocr_pdf_pages(path, scanned, item)
            plain = self._pdf_plain_text(path, [i for i in range(len(lengths)) if i not in texts])
            parts = [f"> Dibaca dengan {label} · {len(scanned)} dari {len(lengths)} halaman hasil scan"]
            for i in range(len(lengths)):
                body = (texts.get(i) if i in texts else plain.get(i, "")).strip()
                parts.append(f"## Halaman {i + 1}\n\n{body or '_(halaman kosong)_'}")
            return "\n\n".join(parts)
        base = _md_text(markitdown().convert(path))
        texts = self.ocr_pdf_pages(path, scanned, item)
        extra = [f"## Teks dari halaman hasil scan\n\n> Dibaca dengan {label}"]
        extra += [f"### Halaman {i + 1}\n\n{texts[i].strip() or '_(tidak ada teks terbaca)_'}" for i in scanned]
        return base + "\n\n" + "\n\n".join(extra)

    @staticmethod
    def _pdf_plain_text(path: str, indices: list[int]) -> dict[int, str]:
        import pypdfium2 as pdfium

        out: dict[int, str] = {}
        if not indices:
            return out
        doc = pdfium.PdfDocument(path)
        try:
            for i in indices:
                page = doc[i]
                tp = page.get_textpage()
                out[i] = tp.get_text_range()
                tp.close()
                page.close()
        finally:
            doc.close()
        return out

    def _append_embedded(self, item: Item, text: str) -> str:
        found = embedded_images(item.source)
        if not found:
            return text
        if not self._use_ai() and not engine().available:
            return text
        label = self._ocr_label()
        imgs = []
        for _, data in found:
            with Image.open(io.BytesIO(data)) as im:
                im.load()
                imgs.append(im.copy())
        total = len(imgs)
        self._sub(item, f"{label} · gambar 0 dari {total}")
        texts = self.read_images(imgs, lambda d, t: self._sub(item, f"{label} · gambar {d} dari {t}"))
        blocks = [f"### Gambar {k} ({name})\n\n{t.strip()}" for k, ((name, _), t) in enumerate(zip(found, texts), 1) if len(t.strip()) >= 6]
        if not blocks:
            return text
        return text + "\n\n## Teks dari gambar di dalam dokumen\n\n" + f"> Dibaca dengan {label}\n\n" + "\n\n".join(blocks)


def output_dir_for(item: Item | None, opts: Options) -> Path:
    if opts.location == "same" and item is not None and not item.is_link:
        return Path(item.source).parent
    return Path(opts.custom_dir) if opts.custom_dir else default_output_dir()


def _write(target: Path, text: str) -> Path:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target = unique_path(target)
        target.write_text(text, encoding="utf-8")
        return target
    except OSError:
        fallback = unique_path(default_output_dir() / target.name)
        fallback.parent.mkdir(parents=True, exist_ok=True)
        fallback.write_text(text, encoding="utf-8")
        return fallback


def _empty_message(item: Item, opts: Options) -> tuple[str, str]:
    if item.kind in ("pdf", "img") and opts.ocr_mode == "off":
        what = "dokumen ini hasil scan" if item.kind == "pdf" else "ini gambar"
        return f"Tidak ada teks terbaca karena {what}.", "ocr"
    if item.kind == "aud":
        return "Tidak ada ucapan yang dikenali di rekaman ini.", ""
    return "Tidak ada teks yang bisa diambil dari file ini.", ""


def run_job(items: list[Item], opts: Options, emit: Emit, cancel: threading.Event) -> dict:
    """Ubah semua item berurutan. Mengirim event 'item', 'progress', 'log', lalu 'finished'."""
    conv = Converter(opts, emit, cancel)
    total = len(items)
    for it in items:
        it.reset()
        it.status = "wait"
    emit("items", {"items": [i.public() for i in items]})
    entries: list[tuple[str, str]] = []
    out_dirs: list[str] = []
    cancelled = False
    for n, it in enumerate(items, 1):
        if cancel.is_set():
            cancelled = True
            break
        it.status = "work"
        emit("progress", {"done": n - 1, "total": total, "current": it.id})
        emit("item", it.public())
        try:
            text = conv.convert_item(it).strip()
        except Cancelled:
            it.status, it.sub = "idle", ""
            emit("item", it.public())
            cancelled = True
            break
        except Exception as e:  # noqa: BLE001 - setiap file berdiri sendiri; error dicatat dan dilanjutkan
            log.exception("Gagal mengubah %s", it.source)
            it.status, it.sub, it.message = "error", "", friendly_error(e)
            emit("item", it.public())
            emit("log", {"text": f"Gagal: {it.display_name}. {it.message}"})
            continue
        it.sub = ""
        it.result = text
        it.words = word_count(text)
        it.status = "done"
        if not text:
            it.status = "warn"
            it.message, it.fix = _empty_message(it, opts)
        elif it.kind == "yt" and "### Transcript" not in text:
            it.status = "warn"
            it.message = "Transkrip tidak tersedia. Hanya judul dan deskripsi yang diambil."
        if opts.out_mode == "combined":
            entries.append((it.display_name, text))
        elif text:  # file kosong tidak disimpan; barisnya diberi tanda "Perlu dicek"
            stem = safe_filename(it.title, "link") if it.is_link else Path(it.source).stem
            target = _write(output_dir_for(it, opts) / f"{stem}.md", text + "\n")
            it.output = str(target)
            out_dirs.append(str(target.parent))
            emit("log", {"text": f"Tersimpan: {target}"})
        emit("item", it.public())
    emit("progress", {"done": sum(1 for i in items if i.status in ("done", "warn", "error")), "total": total, "current": None})

    combined_path, combined_text = "", ""
    if opts.out_mode == "combined" and entries:
        combined_text = build_combined(entries)
        first_local = next((i for i in items if not i.is_link), None)
        name = safe_filename(opts.combined_name, "Gabungan")
        target = _write(output_dir_for(first_local, opts) / f"{name}.md", combined_text)
        combined_path = str(target)
        out_dirs.append(str(target.parent))
        emit("log", {"text": f"File gabungan tersimpan: {target}"})

    summary = {
        "cancelled": cancelled,
        "ok": sum(1 for i in items if i.status == "done"),
        "warn": sum(1 for i in items if i.status == "warn"),
        "error": sum(1 for i in items if i.status == "error"),
        "total": total,
        "words": sum(i.words for i in items),
        "out_dir": out_dirs[-1] if out_dirs else "",
        "combined_path": combined_path,
        "combined_words": word_count(combined_text),
    }
    return {"summary": summary, "combined_text": combined_text}
