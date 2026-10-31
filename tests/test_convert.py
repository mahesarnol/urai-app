import threading

import pytest

from urai.convert import Options, item_from_link, item_from_path, run_job
from urai.fileinfo import embedded_images, inspect_file


def test_inspect_samples(samples):
    scan = inspect_file(samples["Scan Buku Sejarah Kopi.pdf"])
    assert scan["kind"] == "pdf" and scan["scan"] and scan["pages"] == 2
    text = inspect_file(samples["Bab 1 Mengelola Waktu.pdf"])
    assert not text["scan"] and not text["mixed"]
    assert "3 slide" in inspect_file(samples["Presentasi Ringkasan Buku.pptx"])["meta"]
    assert "2 sheet" in inspect_file(samples["Statistik Perpustakaan.xlsx"])["meta"]
    assert inspect_file(samples["Foto Pengumuman Perpustakaan.jpg"])["meta"].startswith("Gambar · 1400×800")
    assert len(embedded_images(samples["Presentasi Ringkasan Buku.pptx"])) == 1


def test_link_items():
    yt = item_from_link("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert yt.kind == "yt" and yt.exp and yt.badge == ""
    web = item_from_link("https://www.bps.go.id/id")
    assert web.kind == "web" and web.name == "Halaman bps.go.id"


def _run(paths, tmp_path, **kw):
    items = [item_from_path(p) for p in paths]
    opts = Options(out_mode=kw.pop("out_mode", "separate"), location="custom", custom_dir=str(tmp_path / "out"), **kw)
    events = []
    res = run_job(items, opts, lambda k, d: events.append((k, d)), threading.Event())
    return items, res, events


def test_ocr_off_marks_scans(samples, tmp_path):
    items, res, events = _run([samples["Scan Buku Sejarah Kopi.pdf"], samples["Notulen Rapat Tim.docx"]], tmp_path, ocr_mode="off")
    scan, doc = items
    assert scan.status == "warn" and scan.fix == "ocr" and "hasil scan" in scan.message
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
    assert "## Halaman 2" in by["Scan Buku Sejarah Kopi.pdf"].result
    assert "Kebiasaan yang Dicoba" in by["Presentasi Ringkasan Buku.pptx"].result  # hanya ada di dalam gambar
    assert "PERPUSTAKAAN" in by["Foto Pengumuman Perpustakaan.jpg"].result
    assert "Matriks Prioritas" in by["Bab 1 Mengelola Waktu.pdf"].result
    assert res["summary"]["ok"] == len(items)


@pytest.mark.tesseract
def test_combined_same_folder(copy_samples, tmp_path, has_tesseract):
    paths = [copy_samples / "Notulen Rapat Tim.docx", copy_samples / "Foto Pengumuman Perpustakaan.jpg"]
    items = [item_from_path(p) for p in paths]
    opts = Options(out_mode="combined", combined_name="Bahan: Kajian?", location="same", ocr_mode="offline")
    res = run_job(items, opts, lambda k, d: None, threading.Event())
    out = res["summary"]["combined_path"]
    assert out.endswith("Bahan Kajian.md") and out.startswith(str(copy_samples))
    text = res["combined_text"]
    assert text.index("# Notulen Rapat Tim.docx") < text.index("# Foto Pengumuman Perpustakaan.jpg")
