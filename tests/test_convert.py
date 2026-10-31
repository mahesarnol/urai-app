import threading

import pytest

from urai import i18n
from urai.convert import Options, item_from_link, item_from_path, run_job
from urai.fileinfo import embedded_images, inspect_file, meta_text
from urai.summarize import struct_outline


def test_inspect_samples(samples):
    scan = inspect_file(samples["Scan Buku Sejarah Kopi.pdf"])
    assert scan["kind"] == "pdf" and scan["scan"] and scan["pages"] == 2
    text = inspect_file(samples["Bab 1 Mengelola Waktu.pdf"])
    assert not text["scan"] and not text["mixed"]
    assert "PowerPoint · 3 slides" in inspect_file(samples["Presentasi Ringkasan Buku.pptx"])["meta"]
    assert "Excel · 2 sheets" in inspect_file(samples["Statistik Perpustakaan.xlsx"])["meta"]
    assert inspect_file(samples["Foto Pengumuman Perpustakaan.jpg"])["meta"].startswith("Image · 1400×800")
    assert len(embedded_images(samples["Presentasi Ringkasan Buku.pptx"])) == 1
    i18n.set_lang("id")
    assert "PowerPoint · 3 slide ·" in inspect_file(samples["Presentasi Ringkasan Buku.pptx"])["meta"]
    assert inspect_file(samples["Scan Buku Sejarah Kopi.pdf"])["meta"].startswith("PDF · 2 halaman")


def test_meta_text_plural_and_sizes():
    assert meta_text("pdf", 3_984_589, {"pages": 1}) == "PDF · 1 page · 3.8 MB"
    assert meta_text("ppt", 0, {"slides": 1}) == "PowerPoint · 1 slide"
    assert meta_text("pdf", 0, {"pages": 1240}) == "PDF · 1,240 pages"
    assert meta_text("unknown", 500) == "File · 500 B"
    i18n.set_lang("id")
    assert meta_text("pdf", 3_984_589, {"pages": 1}) == "PDF · 1 halaman · 3,8 MB"
    assert meta_text("pdf", 0, {"pages": 1240}) == "PDF · 1.240 halaman"


def test_link_items():
    yt = item_from_link("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert yt.kind == "yt" and yt.exp and yt.badge == ""
    web = item_from_link("https://www.bps.go.id/id")
    assert web.kind == "web" and web.name == "Page on bps.go.id"
    assert yt.name == "YouTube video" and yt.meta == "YouTube link · youtube.com"


def _run(paths, tmp_path, **kw):
    items = [item_from_path(p) for p in paths]
    opts = Options(out_mode=kw.pop("out_mode", "separate"), location="custom", custom_dir=str(tmp_path / "out"), **kw)
    events = []
    res = run_job(items, opts, lambda k, d: events.append((k, d)), threading.Event())
    return items, res, events


def test_ocr_off_marks_scans(samples, tmp_path):
    items, res, events = _run([samples["Scan Buku Sejarah Kopi.pdf"], samples["Notulen Rapat Tim.docx"]], tmp_path, ocr_mode="off")
    scan, doc = items
    assert scan.status == "warn" and scan.fix == "ocr" and "is a scan" in scan.message
    assert scan.output == ""  # file kosong tidak ditulis
    assert doc.status == "done" and doc.output.endswith("Notulen Rapat Tim.md")
    assert res["summary"]["warn"] == 1 and res["summary"]["ok"] == 1
    kinds = [k for k, _ in events]
    assert kinds[0] == "items" and "progress" in kinds and kinds.count("item") >= 4


def test_cancel_before_start(samples, tmp_path):
    cancel = threading.Event()
    cancel.set()
    items = [item_from_path(samples["Notulen Rapat Tim.docx"])]
    res = run_job(items, Options(custom_dir=str(tmp_path)), lambda k, d: None, cancel)
    assert res["summary"]["cancelled"] and items[0].status == "wait"


def test_missing_file_is_friendly(tmp_path, samples):
    p = tmp_path / "hilang.docx"
    import shutil

    shutil.copy(samples["Notulen Rapat Tim.docx"], p)
    item = item_from_path(p)
    p.unlink()
    res = run_job([item], Options(custom_dir=str(tmp_path / "o")), lambda k, d: None, threading.Event())
    assert item.status == "error" and item.message and res["summary"]["error"] == 1


@pytest.mark.tesseract
def test_full_offline_run(samples, tmp_path, has_tesseract):
    items, res, _ = _run(sorted(samples.values()), tmp_path, ocr_mode="offline", langs=["ind", "eng"])
    by = {i.name: i for i in items}
    assert all(i.status == "done" for i in items), [(i.name, i.status, i.message) for i in items]
    assert "Kaldi" in by["Scan Buku Sejarah Kopi.pdf"].result and "Jawa" in by["Scan Buku Sejarah Kopi.pdf"].result
    assert "## Page 2" in by["Scan Buku Sejarah Kopi.pdf"].result
    assert "· 2 of 2 pages scanned" in by["Scan Buku Sejarah Kopi.pdf"].result
    assert "## Text from images in the document" in by["Presentasi Ringkasan Buku.pptx"].result
    assert "> Read with Offline OCR (Indonesian, English)" in by["Foto Pengumuman Perpustakaan.jpg"].result
    assert "Kebiasaan yang Dicoba" in by["Presentasi Ringkasan Buku.pptx"].result  # hanya ada di dalam gambar
    assert "PERPUSTAKAAN" in by["Foto Pengumuman Perpustakaan.jpg"].result
    assert "Matriks Prioritas" in by["Bab 1 Mengelola Waktu.pdf"].result
    assert res["summary"]["ok"] == len(items)


class FakeTesseract:
    """Pengganti Tesseract supaya jalur baca scan bisa diuji tanpa programnya."""
    available = True

    def pick_langs(self, wanted):
        return ["ind", "eng"]

    def read(self, img, langs, psm=3):
        return "Teks dari gambar uji"


@pytest.mark.parametrize("lang", ["en", "id"])
def test_ocr_paths_write_localized_markdown(samples, tmp_path, monkeypatch, lang):
    monkeypatch.setattr("urai.convert.engine", lambda: FakeTesseract())
    i18n.set_lang(lang)
    names = ["Scan Buku Sejarah Kopi.pdf", "Presentasi Ringkasan Buku.pptx", "Foto Pengumuman Perpustakaan.jpg"]
    items, _, events = _run([samples[n] for n in names], tmp_path, ocr_mode="offline")
    scan, ppt, img = (i.result for i in items)
    assert all(i.status == "done" for i in items)
    want = {
        "en": ["> Read with Offline OCR (Indonesian, English) · 2 of 2 pages scanned", "## Page 1", "## Page 2",
               "## Text from images in the document", "### Image 1 (image1.png)", "> Read with Offline OCR"],
        "id": ["> Dibaca dengan OCR offline (Indonesia, Inggris) · 2 dari 2 halaman hasil scan", "## Halaman 1",
               "## Halaman 2", "## Teks dari gambar di dalam dokumen", "### Gambar 1 (image1.png)", "> Dibaca dengan OCR offline"],
    }[lang]
    assert want[0] in scan and want[1] in scan and want[2] in scan
    assert want[3] in ppt and want[4] in ppt
    assert img.startswith("# Foto Pengumuman Perpustakaan\n\n" + want[5])
    subs = [d["sub"] for k, d in events if k == "item" and d.get("sub")]
    assert any(("page 2 of 2" if lang == "en" else "halaman 2 dari 2") in s for s in subs)
    assert any(("image 1 of 1" if lang == "en" else "gambar 1 dari 1") in s for s in subs)
    # kerangka offline tetap terbaca dari hasil baca scan dalam kedua bahasa
    outline = struct_outline("Scan Buku Sejarah Kopi.pdf", scan).splitlines()
    assert outline[:3] == ["# Scan Buku Sejarah Kopi", "## " + want[1][3:], "- Teks dari gambar uji"]


@pytest.mark.tesseract
def test_ocr_text_in_indonesian(samples, tmp_path, has_tesseract):
    i18n.set_lang("id")
    items, _, _ = _run([samples["Scan Buku Sejarah Kopi.pdf"], samples["Presentasi Ringkasan Buku.pptx"]], tmp_path,
                       ocr_mode="offline", langs=["ind", "eng"])
    scan, ppt = items
    assert "> Dibaca dengan OCR offline (Indonesia, Inggris) · 2 dari 2 halaman hasil scan" in scan.result
    assert "## Halaman 2" in scan.result
    assert "## Teks dari gambar di dalam dokumen" in ppt.result and "### Gambar 1 (image1.png)" in ppt.result


@pytest.mark.tesseract
def test_combined_same_folder(copy_samples, tmp_path, has_tesseract):
    paths = [copy_samples / "Notulen Rapat Tim.docx", copy_samples / "Foto Pengumuman Perpustakaan.jpg"]
    items = [item_from_path(p) for p in paths]
    opts = Options(out_mode="combined", combined_name="Catatan: Tim?", location="same", ocr_mode="offline")
    res = run_job(items, opts, lambda k, d: None, threading.Event())
    out = res["summary"]["combined_path"]
    assert out.endswith("Catatan Tim.md") and out.startswith(str(copy_samples))
    text = res["combined_text"]
    assert text.index("# Notulen Rapat Tim.docx") < text.index("# Foto Pengumuman Perpustakaan.jpg")
