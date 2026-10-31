import threading

import pytest

from urai.convert import Options, item_from_link, item_from_path, run_job
from urai.fileinfo import embedded_images, inspect_file


def test_inspect_samples(samples):
    scan = inspect_file(samples["Surat Undangan Musdes.pdf"])
    assert scan["kind"] == "pdf" and scan["scan"] and scan["pages"] == 2
    text = inspect_file(samples["Laporan Pemetaan Sosial 2026.pdf"])
    assert not text["scan"] and not text["mixed"]
    assert "3 slide" in inspect_file(samples["Paparan Program CSR.pptx"])["meta"]
    assert "2 sheet" in inspect_file(samples["Rekap Survei Rumah Tangga.xlsx"])["meta"]
    assert inspect_file(samples["Foto Papan Informasi.jpg"])["meta"].startswith("Gambar · 1400×800")
    assert len(embedded_images(samples["Paparan Program CSR.pptx"])) == 1


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
    items, res, events = _run([samples["Surat Undangan Musdes.pdf"], samples["Notulen FGD Kelompok Tani.docx"]], tmp_path, ocr_mode="off")
    scan, doc = items
    assert scan.status == "warn" and scan.fix == "ocr" and "hasil scan" in scan.message
    assert scan.output == ""  # file kosong tidak ditulis
    assert doc.status == "done" and doc.output.endswith("Notulen FGD Kelompok Tani.md")
    assert res["summary"]["warn"] == 1 and res["summary"]["ok"] == 1
    kinds = [k for k, _ in events]
    assert kinds[0] == "items" and "progress" in kinds and kinds.count("item") >= 4


def test_cancel_before_start(samples, tmp_path):
    cancel = threading.Event()
    cancel.set()
    items = [item_from_path(samples["Notulen FGD Kelompok Tani.docx"])]
    res = run_job(items, Options(custom_dir=str(tmp_path)), lambda k, d: None, cancel)
    assert res["summary"]["cancelled"] and items[0].status == "wait"


def test_missing_file_is_friendly(tmp_path, samples):
    p = tmp_path / "hilang.docx"
    import shutil

    shutil.copy(samples["Notulen FGD Kelompok Tani.docx"], p)
    item = item_from_path(p)
    p.unlink()
    res = run_job([item], Options(custom_dir=str(tmp_path / "o")), lambda k, d: None, threading.Event())
    assert item.status == "error" and item.message and res["summary"]["error"] == 1


@pytest.mark.tesseract
def test_full_offline_run(samples, tmp_path, has_tesseract):
    items, res, _ = _run(sorted(samples.values()), tmp_path, ocr_mode="offline", langs=["ind", "eng"])
    by = {i.name: i for i in items}
    assert all(i.status == "done" for i in items), [(i.name, i.status, i.message) for i in items]
    assert "Musyawarah" in by["Surat Undangan Musdes.pdf"].result
    assert "## Halaman 2" in by["Surat Undangan Musdes.pdf"].result
    assert "Target Program 2027" in by["Paparan Program CSR.pptx"].result
    assert "PAPAN INFORMASI" in by["Foto Papan Informasi.jpg"].result
    assert res["summary"]["ok"] == len(items)


@pytest.mark.tesseract
def test_combined_same_folder(copy_samples, tmp_path, has_tesseract):
    paths = [copy_samples / "Notulen FGD Kelompok Tani.docx", copy_samples / "Foto Papan Informasi.jpg"]
    items = [item_from_path(p) for p in paths]
    opts = Options(out_mode="combined", combined_name="Bahan: Kajian?", location="same", ocr_mode="offline")
    res = run_job(items, opts, lambda k, d: None, threading.Event())
    out = res["summary"]["combined_path"]
    assert out.endswith("Bahan Kajian.md") and out.startswith(str(copy_samples))
    text = res["combined_text"]
    assert text.index("# Notulen FGD Kelompok Tani.docx") < text.index("# Foto Papan Informasi.jpg")
