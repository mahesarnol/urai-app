"""Uji mandiri tanpa jendela: mengubah semua file contoh dan memeriksa hasilnya.

Dipakai GitHub Actions setelah installer dirakit:  "Urai App.exe" --selftest <folder>
Hasil ditulis ke <folder>/selftest.json. Kode keluar 0 berarti semua lolos.
"""
from __future__ import annotations

import json
import platform
import threading
import time
import traceback
from pathlib import Path

from . import info
from .convert import Options, item_from_path, run_job
from .ocr import engine
from .paths import samples_dir

# Potongan teks yang wajib muncul di hasil tiap file contoh.
EXPECT = {
    "Laporan Pemetaan Sosial 2026.pdf": ["Pemetaan Aktor", "1.240"],
    "Surat Undangan Musdes.pdf": ["Musyawarah", "Sukamaju"],          # PDF hasil scan, dibaca OCR offline
    "Notulen FGD Kelompok Tani.docx": ["Masalah utama", "pompa air"],
    "Rekap Survei Rumah Tangga.xlsx": ["Dusun 2", "Posyandu"],
    "Paparan Program CSR.pptx": ["Rencana Program CSR 2027", "Target Program 2027"],  # teks di gambar dalam slide
    "Foto Papan Informasi.jpg": ["PAPAN INFORMASI", "Posyandu"],
}


def _check_exports(out: Path) -> dict:
    from . import export
    from .summarize import struct_outline

    md = struct_outline("Uji", "# Uji\n## Cabang\n- poin satu\n- poin dua")
    res = {}
    try:
        export.save_html(out / "uji - mind map.html", md, "Uji", None, True)
        res["html"] = (out / "uji - mind map.html").stat().st_size > 100_000
    except Exception as e:  # noqa: BLE001
        res["html"] = f"{type(e).__name__}: {e}"
    try:
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (800, 500), "white").save(buf, "PNG")
        export.save_pdf(out / "uji - mind map.pdf", buf.getvalue(), md, "Uji", size="F4", orient="land",
                        show_title=True, show_label=True, text_page=True)
        res["pdf"] = (out / "uji - mind map.pdf").read_bytes()[:5] == b"%PDF-"
    except Exception as e:  # noqa: BLE001
        res["pdf"] = f"{type(e).__name__}: {e}"
    return res


def run(out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"app": info.APP_NAME, "version": info.VERSION, "python": platform.python_version(),
                    "platform": platform.platform(), "files": {}, "ok": False}
    try:
        tess = engine()
        report["tesseract"] = {"path": str(tess.cmd), "tessdata": str(tess.tessdata), "version": tess.version(),
                               "langs": tess.languages()}
        files = sorted(p for p in samples_dir().iterdir() if p.is_file())
        items = [item_from_path(p) for p in files]
        opts = Options(ocr_mode="offline", langs=["ind", "eng"], quality="fast", embedded=True,
                       out_mode="separate", location="custom", custom_dir=str(out / "md"))
        t0 = time.time()
        res = run_job(items, opts, lambda kind, data: None, threading.Event())
        report["seconds"] = round(time.time() - t0, 1)
        report["summary"] = res["summary"]
        all_ok = True
        for it in items:
            want = EXPECT.get(it.name, [])
            low = it.result.lower()
            missing = [w for w in want if w.lower() not in low]
            ok = it.status == "done" and not missing
            all_ok &= ok
            report["files"][it.name] = {"status": it.status, "words": it.words, "missing": missing,
                                        "message": it.message, "ok": ok}
        report["exports"] = _check_exports(out)
        all_ok &= all(v is True for v in report["exports"].values())
        report["ok"] = all_ok
    except Exception:  # noqa: BLE001
        report["error"] = traceback.format_exc()
    (out / "selftest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0 if report["ok"] else 1
