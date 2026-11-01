"""Mesin PDF teliti (Docling): pekerja tiruan (tanpa Docling) dan pengunduh terhadap server rilis lokal."""
import hashlib
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import types
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from urai import ai as ai_mod
from urai import docling_engine as dl
from urai.api import Api
from urai.convert import Converter, Options, item_from_path, run_job
from urai.settings import Settings

FAKE = Path(__file__).with_name("fake_docling_worker.py")
TEXT_PDF = "Bab 1 Mengelola Waktu.pdf"
FALLBACK_NOTE = "The accurate PDF engine couldn't read this file, so the standard reader was used."


def wait_until(cond, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


# ---------- pekerja tiruan ----------

@pytest.fixture
def fake_engine(monkeypatch, tmp_path):
    """Mesin dianggap terpasang lewat URAI_DOCLING_PYTHON; pekerjanya tests/fake_docling_worker.py."""
    log = tmp_path / "worker.log"
    monkeypatch.setenv("URAI_DOCLING_PYTHON", sys.executable)
    monkeypatch.setenv("URAI_DOCLING_WORKER", str(FAKE))
    monkeypatch.setenv("FAKE_DOCLING_LOG", str(log))
    monkeypatch.setattr(dl, "_WORKER", None)

    def events():
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []

    return events


def pdf_copy(samples, tmp_path, name):
    p = tmp_path / "pdf" / name
    p.parent.mkdir(exist_ok=True)
    shutil.copy(samples[TEXT_PDF], p)
    return p


def mixed_pdf(samples, tmp_path):
    """Satu halaman berteks dan dua halaman hasil scan."""
    import pypdfium2 as pdfium

    out = pdfium.PdfDocument.new()
    srcs = [pdfium.PdfDocument(str(samples[n])) for n in (TEXT_PDF, "Scan Buku Sejarah Kopi.pdf")]
    for src in srcs:
        out.import_pages(src)
    path = tmp_path / "campuran.pdf"
    out.save(str(path))
    out.close()
    for src in srcs:
        src.close()
    return path


def run(paths, tmp_path, **kw):
    items = [item_from_path(p) for p in paths]
    opts = Options(ocr_mode=kw.pop("ocr_mode", "off"), pdf_engine=kw.pop("pdf_engine", "docling"), location="custom",
                   custom_dir=str(tmp_path / "out"), **kw)
    events = []
    res = run_job(items, opts, lambda k, d: events.append((k, d)), threading.Event())
    return items, res, events


def test_text_pdf_goes_through_worker_and_is_normalized(fake_engine, samples, tmp_path):
    items, _, events = run([pdf_copy(samples, tmp_path, "laporan.pdf"), samples["Notulen Rapat Tim.docx"]], tmp_path)
    pdf, doc = items
    assert pdf.status == "done" and pdf.engine == "docling" and pdf.note == ""
    assert doc.engine == "standard"
    pub = pdf.public()
    assert pub["engine"] == "docling" and pub["note"] == "" and "note_ref" not in pub
    md = pdf.result
    assert md.startswith("## Judul laporan") and "<!--" not in md and "\n\n\n" not in md
    assert all(line == line.rstrip() for line in md.splitlines())
    assert "| Kolom A | Kolom B |\n|---------|---------|\n| isi 1   | isi 2   |" in md  # tabel dibiarkan apa adanya
    assert Path(pdf.output).read_text(encoding="utf-8") == md + "\n"
    subs = [d["sub"] for k, d in events if k == "item" and d.get("sub")]
    assert "Starting the accurate PDF engine…" in subs and "Reading layout and tables (accurate mode)…" in subs
    ev = fake_engine()
    assert [e["event"] for e in ev] == ["start", "convert"]
    assert ev[1]["ocr"] is False and ev[1]["tesseract"] is None and ev[1]["langs"] == []
    assert dl.worker().version == "fake-1.0"


def test_worker_is_reused_then_stopped_when_idle(fake_engine, samples, tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "IDLE_SECONDS", 0.5)
    items, _, _ = run([pdf_copy(samples, tmp_path, "a.pdf"), pdf_copy(samples, tmp_path, "b.pdf")], tmp_path)
    assert [i.engine for i in items] == ["docling", "docling"]
    w = dl.worker()
    assert w.starts == 1 and [e["event"] for e in fake_engine()] == ["start", "convert", "convert"]
    assert wait_until(lambda: not w.running, 10)
    assert fake_engine()[-1]["event"] == "quit"  # berhenti dengan sopan


def test_fallback_on_error_crash_timeout_and_not_ready(fake_engine, samples, tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "DOC_TIMEOUT_BASE", 1.0)
    monkeypatch.setattr(dl, "DOC_TIMEOUT_PER_PAGE", 0.5)
    names = ["fail.pdf", "baik.pdf", "crash.pdf", "slow.pdf", "lagi.pdf"]
    items, _, events = run([pdf_copy(samples, tmp_path, n) for n in names], tmp_path)
    by = {Path(i.source).name: i for i in items}
    for n in ("fail.pdf", "crash.pdf", "slow.pdf"):
        it = by[n]
        assert it.status == "done" and it.engine == "standard" and it.note == FALLBACK_NOTE, n
        assert "Matriks Prioritas" in it.result  # dibaca ulang oleh pembaca biasa
    assert by["baik.pdf"].engine == "docling" and by["lagi.pdf"].engine == "docling"
    # ok:false tidak mematikan pekerja; mati dan macet membuat pekerja dinyalakan ulang
    assert dl.worker().starts == 3
    subs = [d["sub"] for k, d in events if k == "item" and d.get("sub")]
    assert "The accurate engine couldn't read this file, using the standard reader…" in subs
    # pekerja yang menolak mulai juga memakai jalur cadangan
    dl.stop_worker()
    monkeypatch.setenv("FAKE_DOCLING_NOT_READY", "1")
    items, _, _ = run([pdf_copy(samples, tmp_path, "c.pdf")], tmp_path)
    assert items[0].engine == "standard" and items[0].note == FALLBACK_NOTE and items[0].status == "done"


def test_scanned_pdf_and_mixed_pdf_with_ai_stay_on_standard(fake_engine, samples, tmp_path):
    items, _, _ = run([samples["Scan Buku Sejarah Kopi.pdf"]], tmp_path)
    assert items[0].engine == "standard" and items[0].note == "" and items[0].status == "warn"
    assert fake_engine() == []  # PDF hasil scan penuh tidak menyalakan mesin teliti
    mixed = mixed_pdf(samples, tmp_path)
    opts = Options(ocr_mode="ai", ai=ai_mod.AIConfig("gemini", "kunci"), pdf_engine="docling")
    assert Converter(opts, lambda k, d: None, threading.Event())._convert_docling(item_from_path(mixed)) is None
    assert fake_engine() == []  # mode AI: halaman scan dibaca AI lewat jalur biasa
    items, _, _ = run([mixed], tmp_path)  # tanpa AI, PDF campuran lewat mesin teliti
    assert items[0].engine == "docling"


def test_offline_ocr_passes_tesseract_to_worker(fake_engine, samples, tmp_path, monkeypatch):
    class FakeTesseract:
        available = True
        cmd = Path("C:/Tesseract-OCR/tesseract.exe")
        tessdata = Path("C:/Tesseract-OCR/tessdata")

        def pick_langs(self, wanted):
            return ["ind", "eng"]

    monkeypatch.setattr("urai.convert.engine", lambda: FakeTesseract())
    # PDF berteks: tanpa OCR, karena tidak ada halaman scan (OCR hanya memperlambat)
    items, _, _ = run([pdf_copy(samples, tmp_path, "teks.pdf")], tmp_path, ocr_mode="offline")
    assert items[0].engine == "docling"
    req = [e for e in fake_engine() if e["event"] == "convert"][-1]
    assert req["ocr"] is False and req["tesseract"] is None
    # PDF campuran: halaman scan dibaca Tesseract milik aplikasi di dalam Docling
    items, _, _ = run([mixed_pdf(samples, tmp_path)], tmp_path, ocr_mode="offline")
    assert items[0].engine == "docling"
    req = [e for e in fake_engine() if e["event"] == "convert"][-1]
    assert req["ocr"] is True and req["tesseract"] == str(FakeTesseract.cmd)
    assert req["tessdata"] == str(FakeTesseract.tessdata) and req["langs"] == ["ind", "eng"]


def test_mixed_pdf_without_tesseract_uses_standard_path(fake_engine, samples, tmp_path, monkeypatch):
    class NoTesseract:
        available = False
        cmd = None
        tessdata = None

    monkeypatch.setattr("urai.convert.engine", lambda: NoTesseract())
    opts = Options(ocr_mode="offline", pdf_engine="docling")
    conv = Converter(opts, lambda k, d: None, threading.Event())
    assert conv._convert_docling(item_from_path(mixed_pdf(samples, tmp_path))) is None  # jalur biasa memberi tahu
    assert [e for e in fake_engine() if e["event"] == "convert"] == []


def test_cancel_kills_worker(fake_engine, samples, tmp_path):
    cancel = threading.Event()
    items = [item_from_path(pdf_copy(samples, tmp_path, "slow.pdf"))]
    out = {}
    opts = Options(ocr_mode="off", pdf_engine="docling", custom_dir=str(tmp_path / "out"))
    th = threading.Thread(target=lambda: out.update(run_job(items, opts, lambda k, d: None, cancel)))
    th.start()
    assert wait_until(lambda: any(e["event"] == "convert" for e in fake_engine()))
    proc = dl.worker()._proc
    cancel.set()
    th.join(15)
    assert out["summary"]["cancelled"] and items[0].status == "idle"
    assert proc.poll() is not None and not dl.worker().running  # proses pekerja benar-benar berhenti
    again, _, _ = run([pdf_copy(samples, tmp_path, "baru.pdf")], tmp_path)
    assert again[0].engine == "docling" and dl.worker().starts == 2


def test_engine_missing_note_and_language(samples, tmp_path):
    api = Api(Settings(tmp_path / "s.json"), dev=True)
    api.save_settings({"custom_dir": str(tmp_path / "out"), "ocr_mode": "off", "pdf_engine": "docling"})
    api.add_paths([str(samples[TEXT_PDF])])
    api.start()
    api._job.join(60)
    item = api.init()["items"][0]
    assert item["engine"] == "standard" and item["note"] == "The accurate PDF engine isn't installed, so the standard reader was used."
    assert api.set_language("id")["items"][0]["note"] == "Mesin PDF teliti belum terpasang, jadi pembaca biasa yang dipakai."


def test_settings_and_status_shape(tmp_path, fake_engine):
    s = Settings(tmp_path / "s.json")
    assert s.get("pdf_engine") == "standard"
    s.update({"pdf_engine": "laser"})
    assert s.get("pdf_engine") == "standard"
    s.update({"pdf_engine": "docling"})
    assert Settings(tmp_path / "s.json").get("pdf_engine") == "docling"
    api = Api(s, dev=True)
    st = api.docling_status()
    assert set(st) == {"installed", "engine", "docling", "size_mb", "state", "done_mb", "total_mb", "error"}
    assert st["installed"] is True and st["engine"] == "dev" and st["state"] == "idle" and api.init()["docling"] == st


# ---------- pengunduh ----------

class Release(BaseHTTPRequestHandler):
    files: dict = {}
    seen: list = []
    delay = 0.0

    def log_message(self, *a):
        pass

    def do_GET(self):  # noqa: N802
        name = self.path.rsplit("/", 1)[-1]
        Release.seen.append((name, self.headers.get("Range")))
        data = Release.files.get(name)
        if data is None:
            self.send_response(404)
            self.end_headers()
            return
        start = 0
        rng = self.headers.get("Range")
        if rng:
            start = int(re.match(r"bytes=(\d+)-", rng).group(1))
            if start >= len(data):
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{len(data)}")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
        else:
            self.send_response(200)
        body = data[start:]
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            for i in range(0, len(body), 16384):
                self.wfile.write(body[i:i + 16384])
                self.wfile.flush()
                if Release.delay:
                    time.sleep(Release.delay)
        except OSError:
            pass  # unduhan dibatalkan di tengah jalan


@pytest.fixture
def release(monkeypatch):
    Release.files, Release.seen, Release.delay = {}, [], 0.0
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Release)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setenv("URAI_DOCLING_URL", f"http://127.0.0.1:{httpd.server_address[1]}/rel")
    yield Release
    Release.delay = 0.0
    httpd.shutdown()


def engine_zip(python=True, extra=None, pad=1_500_000) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        z.writestr("UraiDocling/engine.json", json.dumps({"engine": "1", "docling": "2.145.0"}))
        if python:
            z.writestr("UraiDocling/python/" + ("python.exe" if os.name == "nt" else "bin/python3"), b"MZ")
        z.writestr("UraiDocling/worker.py", "print('pekerja')\n")
        z.writestr("UraiDocling/models/info.txt", "model")
        z.writestr("UraiDocling/pad.bin", os.urandom(pad))
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return buf.getvalue()


def publish(rel, data, digest=None):
    rel.files = {dl.ASSET: data, dl.SUMS: f"{digest or hashlib.sha256(data).hexdigest()}  {dl.ASSET}\n".encode()}


@pytest.fixture
def api(tmp_path):
    return Api(Settings(tmp_path / "settings.json"), dev=True)


def download(api):
    assert api.docling_download() == {"ok": True}
    api._dl.wait(60)
    return api.docling_status()


def test_download_installs_engine(api, release, tmp_path):
    publish(release, engine_zip())
    st = download(api)
    assert st["installed"] is True and st["engine"] == "1" and st["docling"] == "2.145.0" and st["size_mb"] == 1
    assert st["state"] == "idle" and st["error"] is None and st["total_mb"] == st["done_mb"] > 1
    assert str(tmp_path / "localappdata") in str(dl.engine_dir()) and dl.engine_dir().name == "docling-1"
    assert (dl.engine_dir() / "worker.py").is_file() and not dl.part_file().exists()  # zip dihapus setelah dipasang
    assert not list(dl.engines_dir().glob(".dl-*"))
    events = [e for e in api.poll() if e["type"] == "docling"]
    states = [e["state"] for e in events]
    assert {"downloading", "verifying", "extracting"} <= set(states) and states[-1] == "idle" and events[-1]["installed"]
    assert all(set(e) == {"type", *st} for e in events)


def test_checksum_mismatch_is_not_installed(api, release):
    publish(release, engine_zip(), digest="0" * 64)
    st = download(api)
    assert st["state"] == "error" and st["installed"] is False
    assert st["error"] == "The downloaded file was damaged (checksum mismatch). Please download it again."
    assert not dl.part_file().exists() and not dl.engine_dir().exists()


def test_download_resumes_partial_file(api, release):
    data = engine_zip()
    publish(release, data)
    dl.engines_dir().mkdir(parents=True)
    half = len(data) // 2
    dl.part_file().write_bytes(data[:half])
    st = download(api)
    assert st["installed"] and (dl.ASSET, f"bytes={half}-") in release.seen
    # file .part yang sudah lengkap (server menjawab 416) langsung diperiksa dan dipasang
    assert api.docling_remove()["docling"]["installed"] is False
    dl.part_file().write_bytes(data)
    release.seen.clear()
    assert download(api)["installed"] and (dl.ASSET, f"bytes={len(data)}-") in release.seen


def test_cancel_keeps_part_for_resume(api, release):
    data = engine_zip()
    publish(release, data)
    release.delay = 0.05
    assert api.docling_download() == {"ok": True}
    assert wait_until(lambda: api._dl.done > 0)
    assert api.docling_download() == {"ok": False, "error": "The accurate PDF engine is already downloading."}
    assert api.docling_cancel() == {"ok": True}
    api._dl.wait(30)
    st = api.docling_status()
    assert st["state"] == "idle" and st["error"] is None and st["installed"] is False
    size = dl.part_file().stat().st_size
    assert 0 < size < len(data)
    release.delay = 0.0
    assert download(api)["installed"] and (dl.ASSET, f"bytes={size}-") in release.seen


def test_not_enough_disk_space(api, release, monkeypatch):
    publish(release, engine_zip())
    monkeypatch.setattr(shutil, "disk_usage", lambda p: types.SimpleNamespace(total=10 ** 9, used=10 ** 9, free=1000))
    st = download(api)
    assert st["state"] == "error" and st["installed"] is False and not dl.engine_dir().exists()
    assert st["error"].startswith("Not enough free disk space.") and "0.1 GB" in st["error"]
    api.set_language("id")
    assert api.docling_status()["error"].startswith("Ruang disk tidak cukup.") and "0,1 GB" in api.docling_status()["error"]


@pytest.mark.parametrize("data", [engine_zip(python=False, pad=10), engine_zip(extra={"../jahat.txt": "x"}, pad=10), b"bukan zip"])
def test_broken_package_never_reports_installed(api, release, data, tmp_path):
    publish(release, data)
    st = download(api)
    assert st["state"] == "error" and st["installed"] is False
    assert st["error"] == "Couldn't unpack the accurate PDF engine. Try downloading it again."
    assert not dl.engine_dir().exists() and not list(dl.engines_dir().glob(".dl-*"))
    assert not (dl.engines_dir().parent / "jahat.txt").exists() and not (dl.engines_dir() / "jahat.txt").exists()


def test_offline_and_missing_release(api, release, monkeypatch):
    st = download(api)  # rilis kosong: 404
    assert st["state"] == "error" and st["error"] == "The accurate PDF engine isn't available for download right now. Try again later."
    monkeypatch.setenv("URAI_DOCLING_URL", "http://127.0.0.1:9/rel")  # tidak ada server
    st = download(api)
    assert st["error"] == "Couldn't download the accurate PDF engine. Check your internet connection and try again."


def test_remove_stops_worker_and_refuses_while_busy(api, release, monkeypatch):
    publish(release, engine_zip(pad=10))
    assert download(api)["installed"]
    gate = threading.Event()
    api._job = threading.Thread(target=gate.wait, daemon=True)  # seolah konversi sedang berjalan
    api._job.start()
    assert api.docling_remove() == {"ok": False, "error": "Wait for the current process to finish."}
    gate.set()
    api._job.join()
    stopped = []
    monkeypatch.setattr(dl, "stop_worker", lambda: stopped.append(True))
    res = api.docling_remove()
    assert res["ok"] and res["docling"]["installed"] is False and stopped and not dl.engine_dir().exists()


def test_release_url_follows_app_repo(monkeypatch):
    from urai import info

    monkeypatch.delenv("URAI_DOCLING_URL", raising=False)
    assert dl.release_base() == "https://github.com/mahesarnol/urai-app/releases/download/docling-engine-v1/"
    monkeypatch.setattr(info, "GITHUB_REPO", "contoh/garpu")
    assert dl.release_base() == "https://github.com/contoh/garpu/releases/download/docling-engine-v1/"
    assert dl.parse_sums(f"{'a' * 64}  {dl.ASSET}\n{'b' * 64} *lain.zip\nsampah") == {dl.ASSET: "a" * 64, "lain.zip": "b" * 64}


def test_normalize_markdown():
    md = "<!-- image -->\n## Judul  \n\n\n\nTeks\t\n```\n<!-- tetap di kode -->\n```\n|a | b |\n|--|--|\n| 1  | 2  |   \n<!-- formula-not-decoded -->"
    out = dl.normalize_markdown(md)
    assert out == "## Judul\n\nTeks\n```\n<!-- tetap di kode -->\n```\n|a | b |\n|--|--|\n| 1  | 2  |"


def test_install_precompiles_python_files(monkeypatch, tmp_path, caplog):
    """Paket mesin dirakit tanpa __pycache__: setelah dibongkar, file .py dikompilasi dulu."""
    monkeypatch.setattr(dl, "_python_in", lambda root: Path(sys.executable))  # python sungguhan untuk compileall
    good = engine_zip(pad=10, extra={"UraiDocling/python/Lib/modul.py": "NILAI = 1\n"})
    zpath = tmp_path / "mesin.zip"
    zpath.write_bytes(good)
    dl.engines_dir().mkdir(parents=True)
    dl.install_zip(zpath)
    assert list((dl.engine_dir() / "python" / "Lib" / "__pycache__").glob("modul.*.pyc"))
    assert list((dl.engine_dir() / "__pycache__").glob("worker.*.pyc"))
    assert dl.installed_engine()["dir"] == str(dl.engine_dir())
    # file yang tidak bisa dikompilasi hanya dicatat; pemasangan tetap selesai
    bad = engine_zip(pad=10, extra={"UraiDocling/python/Lib/rusak.py": "def (:\n"})
    zpath.write_bytes(bad)
    with caplog.at_level("WARNING", logger="urai.docling"):
        dl.install_zip(zpath)
    assert dl.installed_engine() is not None and "compileall" in caplog.text
    assert not list(dl.engines_dir().glob(".dl-*")) and not list(dl.engines_dir().glob(".old-*"))


def test_precompile_failure_is_tolerated(tmp_path, monkeypatch):
    root = tmp_path / "UraiDocling"
    (root / "python").mkdir(parents=True)
    (root / "python" / ("python.exe" if os.name == "nt" else "bin_python3")).write_bytes(b"MZ")  # bukan program
    monkeypatch.setattr(dl, "_python_in", lambda r: r / "python" / ("python.exe" if os.name == "nt" else "bin_python3"))
    assert dl.precompile(root) is False  # tidak bisa dijalankan: dicatat saja
    monkeypatch.setattr(dl, "_python_in", lambda r: Path(sys.executable))
    monkeypatch.setattr(dl, "COMPILE_TIMEOUT", 0.0)
    (root / "python" / "Lib").mkdir()
    (root / "worker.py").write_text("x = 1\n")
    assert dl.precompile(root) in (True, False)  # batas waktu habis: dihentikan tanpa melempar error
