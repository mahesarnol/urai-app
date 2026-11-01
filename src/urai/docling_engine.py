"""Mesin "Baca PDF teliti" (Docling): diunduh terpisah dan dijalankan sebagai proses pekerja.

Mesin dipasang di %LOCALAPPDATA%\\UraiApp\\engines\\docling-1\\ dari folder UraiDocling/ di zip rilis:
engine.json, python/python.exe, worker.py, models/. Pekerja berbicara lewat baris JSON (lihat
packaging/docling/worker.py), dinyalakan saat dokumen Docling pertama dan dipakai ulang sesudahnya.

Untuk pengembangan dan uji:
    URAI_DOCLING_PYTHON   python yang sudah berisi docling; mesin dianggap terpasang
    URAI_DOCLING_WORKER   skrip pekerja (bawaan packaging/docling/worker.py dari repo)
    URAI_DOCLING_MODELS   folder model untuk pekerja
    URAI_DOCLING_URL      folder unduhan pengganti rilis GitHub
"""
from __future__ import annotations

import atexit
import errno
import hashlib
import http.client
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from collections import deque
from pathlib import Path
from typing import Callable

from . import info
from .errors import Cancelled
from .i18n import t
from .paths import PKG_DIR, engines_dir

log = logging.getLogger("urai.docling")

ENGINE = "1"
TAG = f"docling-engine-v{ENGINE}"
ASSET = f"UraiDocling-{ENGINE}-windows-x64.zip"
SUMS = "SHA256SUMS.txt"
ZIP_ROOT = "UraiDocling"
SPACE_FACTOR = 3          # zip + hasil bongkar + cadangan
MB = 1024 * 1024
CHUNK = 256 * 1024
REPO_WORKER = PKG_DIR.parent.parent / "packaging" / "docling" / "worker.py"
READY_TIMEOUT = 180.0     # muat pertama bisa sekitar satu menit
DOC_TIMEOUT_BASE = 240.0  # detik per dokumen, ditambah per halaman
DOC_TIMEOUT_PER_PAGE = 45.0
IDLE_SECONDS = 600.0      # pekerja dihentikan setelah 10 menit tidak dipakai
COMPILE_TIMEOUT = 1200.0  # kompilasi ribuan file .py setelah dibongkar
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ---------- lokasi dan status ----------

def engine_dir() -> Path:
    return engines_dir() / f"docling-{ENGINE}"


def part_file() -> Path:
    return engines_dir() / (ASSET + ".part")


def release_base() -> str:
    """Folder unduhan rilis mesin di GitHub (repo sama dengan app.repo)."""
    override = os.environ.get("URAI_DOCLING_URL")
    if override:
        return override.rstrip("/") + "/"
    return f"{info.repo_url()}/releases/download/{TAG}/"


def _python_in(root: Path) -> Path:
    return root / "python" / ("python.exe" if os.name == "nt" else "bin/python3")


def _engine_at(root: Path) -> dict | None:
    """Data mesin di folder ini bila lengkap; None bila belum terpasang atau tidak utuh."""
    try:
        meta = json.loads((root / "engine.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    py, worker = _python_in(root), root / "worker.py"
    if not isinstance(meta, dict) or not py.is_file() or not worker.is_file():
        return None
    try:
        size = int(json.loads((root / "install.json").read_text(encoding="utf-8"))["size_mb"])
    except (OSError, ValueError, KeyError, TypeError):
        size = None
    return {"python": str(py), "worker": str(worker), "models": None, "dir": str(root),
            "engine": str(meta.get("engine") or ENGINE), "docling": str(meta["docling"]) if meta.get("docling") else None,
            "size_mb": size}


def installed_engine() -> dict | None:
    """Mesin yang siap dipakai, atau None. Pengganti dari URAI_DOCLING_PYTHON selalu dianggap terpasang."""
    py = os.environ.get("URAI_DOCLING_PYTHON")
    if py:
        return {"python": py, "worker": os.environ.get("URAI_DOCLING_WORKER") or str(REPO_WORKER),
                "models": os.environ.get("URAI_DOCLING_MODELS") or None, "dir": None, "engine": "dev",
                "docling": None, "size_mb": None}
    return _engine_at(engine_dir())


def status(dl: Downloader) -> dict:
    """Bentuk yang dikirim ke tampilan (init()["docling"], docling_status(), event "docling")."""
    eng = installed_engine()
    version = None
    if eng:
        version = eng["docling"] or (_WORKER.version if _WORKER else None)
    return {"installed": bool(eng), "engine": eng["engine"] if eng else None, "docling": version,
            "size_mb": eng["size_mb"] if eng else None, "state": dl.state, "done_mb": round(dl.done / MB, 1),
            "total_mb": round(dl.total / MB, 1) if dl.total else None,
            "error": t(dl.error[0], **dl.error[1]) if dl.error else None}


# ---------- unduh dan pasang ----------

class DownloadError(Exception):
    def __init__(self, key: str, **kw):
        super().__init__(key)
        self.key, self.kw = key, kw


def parse_sums(text: str) -> dict[str, str]:
    """Isi SHA256SUMS.txt ("<sha256>  <nama>") menjadi {nama: sha256}."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", line.strip())
        if m:
            out[m.group(2)] = m.group(1).lower()
    return out


def _long(path: Path) -> str:
    """Path absolut berawalan \\\\?\\ di Windows: isi paket Python sangat dalam dan bisa melewati batas 260 karakter."""
    p = str(Path(path).resolve())
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\") else p


def _rmtree(path: Path) -> None:
    shutil.rmtree(_long(path), ignore_errors=True)


def check_space(folder: Path, total: int, have: int = 0) -> None:
    """Butuh sekitar 3x ukuran zip (zip + hasil bongkar). Yang sudah terunduh tidak dihitung lagi."""
    need = SPACE_FACTOR * total - have
    try:
        free = shutil.disk_usage(folder).free
    except OSError:
        return
    if free < need:
        raise DownloadError("dl.disk", gb=max(0.1, round(need / 1024 ** 3, 1)))


def _range_total(value: str | None) -> int | None:
    m = re.match(r"^bytes\s+(?:\d+-\d+|\*)/(\d+)$", (value or "").strip())
    return int(m.group(1)) if m else None


def _request(url: str, headers: dict | None = None):
    req = urllib.request.Request(url, headers={"User-Agent": f"UraiApp/{info.VERSION}", **(headers or {})})
    return urllib.request.urlopen(req, timeout=30)  # noqa: S310 - alamat rilis tetap (atau pengganti untuk uji)


def _sha256(path: Path, cancel: threading.Event) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(MB), b""):
            if cancel.is_set():
                raise Cancelled()
            h.update(block)
    return h.hexdigest()


def _clean_leftovers(root: Path) -> None:
    """Sisa pemasangan atau penghapusan yang terputus (aplikasi ditutup di tengah jalan)."""
    for p in root.glob(".dl-*"):
        if p.is_dir():
            _rmtree(p)
    for p in root.glob(".old-*"):
        if p.is_dir():
            _rmtree(p)


def _discard(folder: Path) -> None:
    """Singkirkan folder mesin: diganti nama dulu (langsung tidak terpasang), baru dihapus isinya."""
    trash = folder.with_name(f".old-{uuid.uuid4().hex[:8]}")
    for attempt in range(6):  # file python.exe kadang masih terkunci sesaat setelah pekerja berhenti
        try:
            os.rename(folder, trash)
            break
        except OSError:
            if attempt == 5:
                raise
            time.sleep(0.4)
    _rmtree(trash)


def precompile(root: Path, cancel: threading.Event | None = None) -> bool:
    """Paket mesin dirakit tanpa __pycache__; tanpa langkah ini konversi pertama butuh beberapa menit untuk
    mengompilasi ribuan file. Gagal di sini tidak menggagalkan pemasangan (hanya dicatat). True bila berhasil."""
    cmd = [str(_python_in(root)), "-I", "-m", "compileall", "-q", "-j", "0", str(root / "python" / "Lib"),
           str(root / "worker.py")]
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                cwd=str(root), creationflags=_NO_WINDOW)
    except OSError as e:
        log.warning("compileall tidak bisa dijalankan, mesin tetap dipasang: %s", e)
        return False
    end = time.monotonic() + COMPILE_TIMEOUT
    out = b""
    try:
        while True:
            try:
                out, _ = proc.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                if cancel is not None and cancel.is_set():
                    raise Cancelled() from None
                if time.monotonic() > end:
                    log.warning("compileall melewati %s detik, dihentikan; mesin tetap dipasang", COMPILE_TIMEOUT)
                    return False
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(10)
    if proc.returncode != 0:
        tail = out.decode("utf-8", "replace").strip().splitlines()[-3:]
        log.warning("compileall selesai dengan kode %s, mesin tetap dipasang: %s", proc.returncode, " | ".join(tail))
        return False
    return True


def install_zip(zip_path: Path, cancel: threading.Event | None = None) -> None:
    """Bongkar ke folder sementara di sebelahnya, periksa isinya, lalu pindahkan sekaligus ke tempatnya.
    Mesin baru dianggap terpasang setelah langkah terakhir ini, jadi pemasangan yang gagal tidak pernah setengah jadi."""
    root = engines_dir()
    tmp = Path(tempfile.mkdtemp(prefix=".dl-", dir=root))
    try:
        try:
            with zipfile.ZipFile(zip_path) as z:
                members = z.infolist()
                for m in members:
                    name = m.filename.replace("\\", "/")
                    parts = name.split("/")
                    if name.startswith("/") or ":" in name or ".." in parts or parts[0] != ZIP_ROOT:
                        raise DownloadError("dl.extract")
                size = sum(m.file_size for m in members)
                free = shutil.disk_usage(root).free
                if free < size:
                    raise DownloadError("dl.disk", gb=max(0.1, round(size / 1024 ** 3, 1)))
                base = _long(tmp)
                for m in members:
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    z.extract(m, base)
        except zipfile.BadZipFile as e:
            raise DownloadError("dl.extract") from e
        src = tmp / ZIP_ROOT
        if _engine_at(src) is None:
            raise DownloadError("dl.extract")
        precompile(src, cancel)
        (src / "install.json").write_text(json.dumps({"size_mb": max(1, round(size / MB)), "asset": ASSET}), encoding="utf-8")
        target = engine_dir()
        if target.exists():
            _discard(target)
        os.rename(src, target)
    finally:
        _rmtree(tmp)


def remove_engine() -> None:
    """Hapus mesin terpasang beserta sisa unduhan. Melempar OSError bila file masih dipakai."""
    stop_worker()
    root = engines_dir()
    if engine_dir().exists():
        _discard(engine_dir())
    part_file().unlink(missing_ok=True)
    if root.is_dir():
        _clean_leftovers(root)


class Downloader:
    """Mengunduh (bisa dilanjutkan), memeriksa SHA-256, lalu memasang mesin di latar belakang."""

    def __init__(self) -> None:
        self.state = "idle"  # idle | downloading | verifying | extracting | error
        self.done = 0
        self.total: int | None = None
        self.error: tuple[str, dict] | None = None
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self._notify: Callable[[], None] = lambda: None
        self._last = 0.0
        self._got = 0  # byte yang diterima pada percobaan ini

    @property
    def busy(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, notify: Callable[[], None]) -> bool:
        if self.busy:
            return False
        self._cancel = threading.Event()
        self.state, self.error, self.done, self.total = "downloading", None, 0, None
        self._notify = notify
        self._thread = threading.Thread(target=self._run, args=(self._cancel,), daemon=True, name="urai-docling-download")
        self._thread.start()
        return True

    def cancel(self) -> None:
        self._cancel.set()

    def reset(self) -> None:
        """Kembali ke keadaan awal (mis. setelah mesin dihapus)."""
        if not self.busy:
            self.state, self.error, self.done, self.total = "idle", None, 0, None

    def wait(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def _push(self, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self._last >= 0.25:  # paling banyak 4 kabar per detik
            self._last = now
            try:
                self._notify()
            except Exception:  # noqa: BLE001
                log.debug("Kabar unduhan gagal dikirim", exc_info=True)

    def _set(self, state: str) -> None:
        self.state = state
        self._push(force=True)

    def _ref(self, exc: BaseException) -> tuple[str, dict]:
        if isinstance(exc, DownloadError):
            return exc.key, exc.kw
        if isinstance(exc, urllib.error.HTTPError):
            return ("dl.not_found" if exc.code == 404 else "dl.server"), {}
        if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException)):
            return ("dl.interrupted" if self._got else "dl.offline"), {}
        if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
            return "dl.disk_full", {}
        if isinstance(exc, PermissionError):
            return "err.permission", {}
        return "dl.failed", {}

    def _run(self, cancel: threading.Event) -> None:
        self._got = 0
        try:
            root = engines_dir()
            root.mkdir(parents=True, exist_ok=True)
            _clean_leftovers(root)
            self._push(force=True)
            base = release_base()
            with _request(base + SUMS) as r:
                want = parse_sums(r.read(1 << 16).decode("utf-8", "replace")).get(ASSET)
            if not want:
                raise DownloadError("dl.not_found")
            part = part_file()
            self._fetch(base + ASSET, part, cancel)
            self._set("verifying")
            if _sha256(part, cancel) != want:
                part.unlink(missing_ok=True)
                raise DownloadError("dl.checksum")
            self._set("extracting")
            install_zip(part, cancel)
            part.unlink(missing_ok=True)
            self.state, self.error = "idle", None
            log.info("Mesin PDF teliti terpasang di %s", engine_dir())
        except Cancelled:
            self.state, self.error = "idle", None  # file .part disimpan untuk dilanjutkan
        except Exception as e:  # noqa: BLE001
            log.warning("Unduh atau pasang mesin PDF teliti gagal: %r", e)
            self.state, self.error = "error", self._ref(e)
        finally:
            self._push(force=True)

    def _fetch(self, url: str, part: Path, cancel: threading.Event, retry: bool = True) -> None:
        have = part.stat().st_size if part.exists() else 0
        try:
            resp = _request(url, {"Range": f"bytes={have}-"} if have else None)
        except urllib.error.HTTPError as e:
            if e.code == 416 and have:  # file .part sudah lengkap, atau lebih besar dari aslinya
                total = _range_total(e.headers.get("Content-Range"))
                if total == have:
                    self.done = self.total = have
                    return
                part.unlink(missing_ok=True)
                if retry:
                    return self._fetch(url, part, cancel, retry=False)
            raise
        with resp:
            length = resp.headers.get("Content-Length")
            if have and resp.status == 206:
                total = _range_total(resp.headers.get("Content-Range"))
                if total is None and length and length.isdigit():
                    total = have + int(length)
                mode = "ab"
            else:  # server mengirim dari awal
                have, mode = 0, "wb"
                total = int(length) if length and length.isdigit() else None
            self.total, self.done = total, have
            if total:
                check_space(engines_dir(), total, have)
            self._push(force=True)
            read = getattr(resp, "read1", resp.read)  # read1: kabar dan batal tetap cepat di koneksi lambat
            with open(part, mode) as f:
                while True:
                    if cancel.is_set():
                        raise Cancelled()
                    chunk = read(CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    self.done += len(chunk)
                    self._got += len(chunk)
                    self._push()
        if self.total and self.done < self.total:
            raise DownloadError("dl.interrupted")


# ---------- pekerja ----------

class DoclingError(Exception):
    """Mesin teliti tidak mau mulai, berhenti, kehabisan waktu, atau menjawab ok:false."""


def doc_timeout(pages: int) -> float:
    return DOC_TIMEOUT_BASE + DOC_TIMEOUT_PER_PAGE * max(1, pages)


def _pump(stream, q: queue.Queue) -> None:
    try:
        for raw in iter(stream.readline, b""):
            q.put(raw)
    except (OSError, ValueError):
        pass
    finally:
        q.put(None)


def _drain(stream, tail: deque) -> None:
    """stderr pekerja harus terus dibaca supaya pipanya tidak penuh; baris terakhir disimpan untuk log."""
    try:
        for raw in iter(stream.readline, b""):
            tail.append(raw.decode("utf-8", "replace").rstrip()[:300])
    except (OSError, ValueError):
        pass


class Worker:
    """Satu proses pekerja Docling, satu permintaan pada satu waktu."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lines: queue.Queue | None = None
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._n = 0
        self.version: str | None = None
        self.stderr_tail: deque = deque(maxlen=40)
        self.starts = 0  # berapa kali pekerja dinyalakan (untuk uji dan log)

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def convert(self, path: str, *, ocr: bool = False, tesseract: str | None = None, tessdata: str | None = None,
                langs: list[str] | None = None, cancel: threading.Event | None = None,
                on_status: Callable[[str], None] | None = None, timeout: float | None = None) -> str:
        """Markdown dari Docling. Melempar DoclingError (untuk jalur cadangan) atau Cancelled."""
        eng = installed_engine()
        if not eng:
            raise DoclingError("engine not installed")
        say = on_status or (lambda key: None)
        cancel = cancel or threading.Event()
        with self._lock:
            self._stop_timer()
            try:
                if not self.running:
                    say("sub.docling_start")
                    self._start(eng, cancel)
                say("sub.docling_read")
                self._n += 1
                rid = str(self._n)
                self._send({"id": rid, "cmd": "convert", "input": str(path), "ocr": bool(ocr), "tesseract": tesseract,
                            "tessdata": tessdata, "langs": list(langs or [])})
                msg = self._read(lambda m: m.get("id") == rid, timeout or doc_timeout(1), cancel)
            except (Cancelled, DoclingError):
                self._kill()  # dibatalkan, macet, atau berhenti: dinyalakan ulang lain kali
                raise
            except OSError as e:
                self._kill()
                raise DoclingError(f"worker pipe: {e}") from e
            finally:
                self._arm_timer()
        if not msg.get("ok"):  # satu dokumen gagal; pekerja tetap hidup untuk dokumen berikutnya
            raise DoclingError(str(msg.get("error") or "conversion failed"))
        md = msg.get("markdown")
        if not isinstance(md, str):
            raise DoclingError("worker sent no markdown")
        return md

    def _start(self, eng: dict, cancel: threading.Event) -> None:
        env = dict(os.environ)
        if eng.get("models"):
            env["URAI_DOCLING_MODELS"] = eng["models"]
        cmd = [eng["python"], "-I", "-u", eng["worker"]]
        log.info("Menyalakan mesin PDF teliti: %s", cmd)
        self.stderr_tail.clear()
        try:
            self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          cwd=eng.get("dir") or None, env=env, creationflags=_NO_WINDOW)
        except OSError as e:
            self._proc = None
            raise DoclingError(f"cannot start worker: {e}") from e
        self.starts += 1
        self._lines = queue.Queue()
        threading.Thread(target=_pump, args=(self._proc.stdout, self._lines), daemon=True, name="urai-docling-out").start()
        threading.Thread(target=_drain, args=(self._proc.stderr, self.stderr_tail), daemon=True, name="urai-docling-err").start()
        msg = self._read(lambda m: "ready" in m, READY_TIMEOUT, cancel)
        if not msg.get("ready"):
            raise DoclingError(f"worker not ready: {msg.get('error')}")
        self.version = str(msg["docling"]) if msg.get("docling") else None
        log.info("Mesin PDF teliti siap (docling %s)", self.version)

    def _send(self, obj: dict) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
        self._proc.stdin.flush()

    def _read(self, match: Callable[[dict], bool], timeout: float, cancel: threading.Event) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            if cancel.is_set():
                raise Cancelled()
            left = deadline - time.monotonic()
            if left <= 0:
                raise DoclingError(f"no answer within {timeout:.0f} s")
            try:
                raw = self._lines.get(timeout=min(0.2, left))
            except queue.Empty:
                continue
            if raw is None:
                raise DoclingError("worker stopped: " + " | ".join(list(self.stderr_tail)[-3:]))
            try:
                msg = json.loads(raw.decode("utf-8"))
            except ValueError:
                continue
            if isinstance(msg, dict) and match(msg):
                return msg

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.kill()
            proc.wait(10)
        except Exception:  # noqa: BLE001
            log.debug("Pekerja tidak bisa dihentikan", exc_info=True)
        for s in (proc.stdin, proc.stdout, proc.stderr):
            try:
                if s:
                    s.close()
            except OSError:
                pass

    def _stop_timer(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _arm_timer(self) -> None:
        self._stop_timer()
        if self.running:
            self._timer = threading.Timer(IDLE_SECONDS, self.stop)
            self._timer.daemon = True
            self._timer.start()

    def _quit(self) -> None:
        """Minta pekerja berhenti sendiri, lalu pastikan berhenti. Dipanggil sambil memegang kunci."""
        self._stop_timer()
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                self._send({"id": "quit", "cmd": "quit"})
                proc.wait(5)
            except Exception:  # noqa: BLE001
                pass
        self._kill()

    def stop(self) -> None:
        """Hentikan pekerja yang lama tidak dipakai. Tidak mengganggu dokumen yang sedang dibaca."""
        if self._lock.acquire(blocking=False):
            try:
                self._quit()
            finally:
                self._lock.release()

    def shutdown(self) -> None:
        """Aplikasi ditutup atau mesin dihapus: berhenti sekarang juga, meski sedang membaca."""
        self._stop_timer()
        if self._lock.acquire(timeout=0.5):
            try:
                self._quit()
            finally:
                self._lock.release()
        else:
            self._kill()


_WORKER: Worker | None = None
_WORKER_LOCK = threading.Lock()


def worker() -> Worker:
    global _WORKER
    with _WORKER_LOCK:
        if _WORKER is None:
            _WORKER = Worker()
            atexit.register(_WORKER.shutdown)
        return _WORKER


def stop_worker() -> None:
    if _WORKER is not None:
        _WORKER.shutdown()


# ---------- merapikan Markdown Docling ----------

_COMMENT_LINE = re.compile(r"^\s*<!--.*-->\s*$")


def normalize_markdown(md: str) -> str:
    """Buang baris komentar (mis. <!-- image -->; tampilan menganggap baris komentar sebagai penanda slide),
    hapus spasi di akhir baris, dan rapatkan baris kosong berlebih. Tabel dibiarkan apa adanya."""
    out, fence = [], None
    for line in (md or "").replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = None if fence and s.startswith(fence) else (fence or s[:3])
        elif fence is None and _COMMENT_LINE.match(line):
            continue
        out.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
