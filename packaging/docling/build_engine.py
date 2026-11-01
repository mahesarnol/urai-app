"""Rakit mesin "Baca PDF teliti" (Docling) untuk Urai App menjadi satu zip yang diunduh terpisah.

Isi zip (folder akar UraiDocling/):
    engine.json      versi mesin, Docling, dan Python
    python/          CPython mandiri (python-build-standalone lewat uv) yang sudah berisi Docling
    worker.py        pekerja JSON-lines yang dipanggil Urai App
    models/          model tata letak dan tabel, supaya bisa dipakai tanpa internet
    LICENSES/        teks lisensi semua paket Python di dalamnya

Dipakai GitHub Actions (docling-engine.yml), bisa juga dijalankan manual di Windows (butuh uv):
    python packaging/docling/build_engine.py --out build/docling --zip dist/UraiDocling-1-windows-x64.zip \
        --smoke-pdf "src/urai/samples/Bab 1 Mengelola Waktu.pdf"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCLING_VERSION = "2.145.0"
PYTHON_VERSION = "3.12"
MODELS = ["layout", "tableformer"]
UNUSED_MODEL_DIRS = ["docling-project--docling-layout-heron-onnx"]  # pekerja memakai versi PyTorch
LICENSE_NAMES = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.I)


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def engine_version() -> str:
    m = re.search(r'^ENGINE_VERSION = "([^"]+)"', (HERE / "worker.py").read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("ENGINE_VERSION tidak ditemukan di worker.py")
    return m.group(1)


def standalone_python(uv: str) -> Path:
    """Folder CPython mandiri (bisa dipindah) yang dikelola uv."""
    run([uv, "python", "install", PYTHON_VERSION])
    exe = subprocess.run([uv, "python", "find", "--managed-python", PYTHON_VERSION],
                         check=True, capture_output=True, text=True).stdout.strip()
    root = Path(exe).parent
    if not (root / "Lib").is_dir():
        raise SystemExit(f"Python mandiri tidak dikenali: {exe}")
    return root


def collect_licenses(site: Path, dest: Path) -> int:
    n = 0
    for info in sorted(site.glob("*.dist-info")):
        files = [p for p in info.rglob("*") if p.is_file() and LICENSE_NAMES.match(p.name)]
        if not files:
            continue
        out = dest / info.name.removesuffix(".dist-info")
        out.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, out / f.name)
        n += 1
    return n


def smoke(py: Path, worker: Path, pdf: Path) -> None:
    """Pekerja hasil rakitan harus siap dan bisa mengubah satu PDF tanpa internet."""
    reqs = [{"id": "1", "cmd": "ping"}, {"id": "2", "cmd": "convert", "input": str(pdf.resolve()), "ocr": False},
            {"id": "3", "cmd": "quit"}]
    t0 = time.time()
    p = subprocess.run([str(py), "-I", "-u", str(worker)], input="".join(json.dumps(r) + "\n" for r in reqs),
                       capture_output=True, text=True, encoding="utf-8", timeout=900)
    lines = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
    print(f"smoke: exit {p.returncode}, {time.time() - t0:.0f} s, {len(lines)} lines", flush=True)
    if p.returncode != 0 or len(lines) < 3 or not lines[0].get("ready") or not lines[2].get("ok"):
        print(p.stderr[-4000:], file=sys.stderr)
        raise SystemExit(f"uji mesin gagal: {lines[:3]}")
    md = lines[2]["markdown"]
    print(f"smoke: {lines[2]['pages']} pages, {len(md.split())} words, {lines[2]['seconds']} s", flush=True)
    if len(md.split()) < 20:
        raise SystemExit("uji mesin gagal: hasil terlalu pendek")


def make_zip(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".zip.tmp")
    files = sorted(p for p in src.rglob("*") if p.is_file())
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in files:
            z.write(f, Path(src.name) / f.relative_to(src))
    tmp.replace(dst)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="folder kerja; mesin dirakit di <out>/UraiDocling")
    ap.add_argument("--zip", help="tulis zip (dan SHA256SUMS.txt di folder yang sama)")
    ap.add_argument("--smoke-pdf", help="PDF untuk uji singkat setelah dirakit")
    args = ap.parse_args()

    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("uv tidak ditemukan (pip install uv)")
    eng = Path(args.out) / "UraiDocling"
    if eng.exists():
        shutil.rmtree(eng)
    eng.mkdir(parents=True)

    src_py = standalone_python(uv)
    print(f"python: {src_py}", flush=True)
    shutil.copytree(src_py, eng / "python", ignore=shutil.ignore_patterns("__pycache__"))
    py = eng / "python" / "python.exe"
    (eng / "python" / "Lib" / "EXTERNALLY-MANAGED").unlink(missing_ok=True)  # salinan ini milik mesin
    run([uv, "pip", "install", "--python", py, "--break-system-packages", "--no-progress", f"docling=={DOCLING_VERSION}"])

    models = eng / "models"
    dl = ("import sys; from docling.cli.tools import app; "
          f"sys.argv = ['docling-tools', 'models', 'download', '-o', {str(models)!r}, *{MODELS!r}]; app()")
    run([py, "-I", "-c", dl])
    for d in UNUSED_MODEL_DIRS:
        shutil.rmtree(models / d, ignore_errors=True)

    shutil.copy2(HERE / "worker.py", eng / "worker.py")
    pyver = subprocess.run([py, "-I", "-c", "import platform; print(platform.python_version())"],
                           check=True, capture_output=True, text=True).stdout.strip()
    meta = {"engine": engine_version(), "docling": DOCLING_VERSION, "python": pyver,
            "models": MODELS, "built": time.strftime("%Y-%m-%d")}
    (eng / "engine.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    n = collect_licenses(eng / "python" / "Lib" / "site-packages", eng / "LICENSES")
    print(f"licenses: {n} packages", flush=True)

    if args.smoke_pdf:
        smoke(py, eng / "worker.py", Path(args.smoke_pdf))
    for cache in eng.rglob("__pycache__"):  # dibuat ulang saat dipakai; tidak perlu ikut di zip
        shutil.rmtree(cache, ignore_errors=True)

    size = sum(p.stat().st_size for p in eng.rglob("*") if p.is_file())
    print(f"engine size: {size / 1048576:.0f} MB", flush=True)
    if args.zip:
        z = Path(args.zip)
        make_zip(eng, z)
        digest = sha256(z)
        (z.parent / "SHA256SUMS.txt").write_text(f"{digest}  {z.name}\n", encoding="ascii")
        print(f"zip: {z} ({z.stat().st_size / 1048576:.0f} MB) sha256 {digest}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
