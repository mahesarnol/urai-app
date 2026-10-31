"""Membaca teks dari gambar: Tesseract (offline, di prosesor) atau AI (lewat penyedia pilihan pengguna)."""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageOps

from .errors import OcrUnavailable
from .paths import bundled_tesseract_dir, is_frozen

LANG_NAMES = {"ind": "Indonesia", "eng": "Inggris", "jav": "Jawa", "sun": "Sunda", "ara": "Arab"}
DPI = {"fast": 200, "accurate": 300}
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: jangan munculkan jendela hitam


def _candidates() -> list[tuple[Path, Path | None]]:
    """(tesseract.exe, folder tessdata) yang dicoba, berurutan."""
    exe = "tesseract.exe" if os.name == "nt" else "tesseract"
    out: list[tuple[Path, Path | None]] = []
    bundled = bundled_tesseract_dir()
    if is_frozen() or (bundled / exe).exists():
        out.append((bundled / exe, bundled / "tessdata"))
    env = os.environ.get("URAI_TESSERACT")
    if env:
        out.append((Path(env), None))
    found = shutil.which("tesseract")
    if found:
        out.append((Path(found), None))
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "")):
            if base:
                out.append((Path(base) / "Tesseract-OCR" / exe, None))
                out.append((Path(base) / "Programs" / "Tesseract-OCR" / exe, None))
    return out


class Tesseract:
    """Pembungkus kecil untuk program Tesseract. Dipanggil sebagai proses terpisah per halaman."""

    def __init__(self) -> None:
        self.cmd: Path | None = None
        self.tessdata: Path | None = None
        self._langs: list[str] | None = None
        self._lock = threading.Lock()
        for cmd, data in _candidates():
            if cmd.exists():
                self.cmd = cmd
                self.tessdata = data if data and data.exists() else None
                break
        env = dict(os.environ)
        env["OMP_THREAD_LIMIT"] = "1"  # kami menjalankan beberapa halaman sekaligus; jangan rebutan inti prosesor
        if self.tessdata:
            env["TESSDATA_PREFIX"] = str(self.tessdata)
        self._env = env

    @property
    def available(self) -> bool:
        return self.cmd is not None

    def _run(self, args: list[str], timeout: int = 300, data: bytes | None = None) -> subprocess.CompletedProcess:
        if not self.cmd:
            raise OcrUnavailable("tesseract tidak ditemukan")
        kw = {"input": data} if data is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run([str(self.cmd), *args], capture_output=True, timeout=timeout, env=self._env,
                              creationflags=_NO_WINDOW, **kw)

    def version(self) -> str:
        if not self.cmd:
            return ""
        try:
            r = self._run(["--version"], timeout=20)
            text = (r.stdout or r.stderr).decode("utf-8", "replace").strip().splitlines()
            return text[0] if text else ""
        except Exception:
            return ""

    def languages(self) -> list[str]:
        """Bahasa yang terpasang dan kami kenal (ind, eng, jav, sun, ara)."""
        with self._lock:
            if self._langs is None:
                langs: list[str] = []
                if self.cmd:
                    try:
                        r = self._run(["--list-langs"], timeout=20)
                        lines = (r.stdout or r.stderr).decode("utf-8", "replace").splitlines()
                        langs = [l.strip() for l in lines if l.strip() in LANG_NAMES]
                    except Exception:
                        langs = []
                self._langs = langs
            return list(self._langs)

    def pick_langs(self, wanted: list[str]) -> list[str]:
        have = self.languages()
        chosen = [l for l in wanted if l in have]
        if not chosen:
            chosen = [l for l in ("ind", "eng") if l in have] or have[:1]
        if not chosen:
            raise OcrUnavailable("tidak ada file bahasa Tesseract")
        return chosen

    def read(self, img: Image.Image, langs: list[str], psm: int = 3) -> str:
        """Teks dari satu gambar."""
        img = prepare(img)
        opts = ["stdout", "-l", "+".join(langs), "--oem", "1", "--psm", str(psm)]
        with tempfile.TemporaryDirectory(prefix="urai-ocr-") as td:
            src = Path(td) / "page.png"
            if str(src).isascii():
                img.save(src)
                r = self._run([str(src), *opts])
            else:
                # folder sementara dengan huruf non-ASCII (mis. nama pengguna Windows): kirim gambar lewat stdin
                buf = io.BytesIO()
                img.save(buf, "PNG")
                r = self._run(["stdin", *opts], data=buf.getvalue())
        if r.returncode != 0:
            msg = r.stderr.decode("utf-8", "replace").strip().splitlines()
            raise RuntimeError("Tesseract gagal: " + (msg[-1] if msg else f"kode {r.returncode}"))
        return clean_ocr_text(r.stdout.decode("utf-8", "replace"))


def prepare(img: Image.Image) -> Image.Image:
    """Abu-abu, putar sesuai EXIF, dan perbesar gambar kecil supaya huruf terbaca."""
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode not in ("L", "RGB"):
        bg = Image.new("RGB", img.size, "white")
        try:
            bg.paste(img, mask=img.getchannel("A") if "A" in img.getbands() else None)
        except Exception:
            bg.paste(img.convert("RGB"))
        img = bg
    img = img.convert("L")
    if img.width < 1000:
        k = min(3.0, 1400 / max(1, img.width))
        img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    return img


def clean_ocr_text(text: str) -> str:
    lines = [l.rstrip() for l in text.replace("\x0c", "\n").splitlines()]
    out: list[str] = []
    for l in lines:
        if not l.strip():
            if out and out[-1] != "":
                out.append("")
            continue
        out.append(l)
    return "\n".join(out).strip()


_ENGINE: Tesseract | None = None
_ENGINE_LOCK = threading.Lock()


def engine() -> Tesseract:
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = Tesseract()
        return _ENGINE


def reset_engine() -> None:
    global _ENGINE
    with _ENGINE_LOCK:
        _ENGINE = None


def worker_count() -> int:
    return max(1, min(4, (os.cpu_count() or 2) - 1))


if __name__ == "__main__":  # python -m urai.ocr gambar.png
    t = engine()
    print(t.cmd, t.tessdata, t.version(), t.languages())
    if len(sys.argv) > 1:
        print(t.read(Image.open(sys.argv[1]), t.pick_langs(["ind", "eng"])))
