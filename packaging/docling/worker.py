"""Pekerja Docling untuk Urai App: mesin "Baca PDF teliti" yang diunduh terpisah.

Dijalankan oleh Urai App sebagai proses terpisah dan berbicara lewat baris JSON (UTF-8):

    <engine>/python/python.exe -I -u <engine>/worker.py

Saat siap, pekerja menulis satu baris: {"ready": true, "engine": "1", "docling": "<versi>"}.
Setiap permintaan adalah satu baris JSON di stdin, dan setiap jawaban satu baris JSON di stdout:

    {"id": "7", "cmd": "convert", "input": "C:/x.pdf", "ocr": false,
     "tesseract": null, "tessdata": null, "langs": ["ind", "eng"]}
    -> {"id": "7", "ok": true, "markdown": "...", "pages": 3, "seconds": 4.2}
    -> {"id": "7", "ok": false, "error": "pesan singkat (bahasa Inggris, untuk log)"}

    {"id": "8", "cmd": "ping"}  -> {"id": "8", "ok": true, "engine": "1", "docling": "<versi>"}
    {"id": "9", "cmd": "quit"}  -> pekerja berhenti

Model AI dimuat dari <engine>/models (tanpa internet). Semua keluaran pustaka dialihkan ke stderr
supaya stdout hanya berisi jawaban JSON. Markdown dikirim apa adanya; Urai App yang merapikannya.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ENGINE_VERSION = "1"
ROOT = Path(__file__).resolve().parent
MODELS = Path(os.environ.get("URAI_DOCLING_MODELS") or (ROOT / "models"))

# Jangan pernah menghubungi internet: model sudah ikut di dalam paket mesin.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

proto = open(sys.stdout.fileno(), "w", encoding="utf-8", buffering=1, closefd=False)
sys.stdout = sys.stderr  # cetakan pustaka tidak boleh mengotori jalur jawaban
stdin = open(sys.stdin.fileno(), "r", encoding="utf-8", closefd=False)


def send(obj: dict) -> None:
    proto.write(json.dumps(obj, ensure_ascii=False) + "\n")
    proto.flush()


try:
    from importlib.metadata import version

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, TesseractCliOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    DOCLING_VERSION = version("docling")
except Exception as e:  # noqa: BLE001
    send({"ready": False, "error": f"{type(e).__name__}: {e}"})
    sys.exit(3)

_converters: dict = {}


def converter(ocr: bool, tesseract: str | None, tessdata: str | None, langs: list[str]) -> DocumentConverter:
    key = (ocr, tesseract, tessdata, tuple(langs))
    if key not in _converters:
        o = PdfPipelineOptions()
        o.artifacts_path = str(MODELS)
        o.do_table_structure = True
        o.table_structure_options.mode = TableFormerMode.ACCURATE
        o.table_structure_options.do_cell_matching = True
        o.do_ocr = bool(ocr and tesseract)
        if o.do_ocr:
            kw = {"lang": langs or ["eng"], "tesseract_cmd": tesseract}
            if tessdata:
                kw["path"] = tessdata
            o.ocr_options = TesseractCliOcrOptions(**kw)
        _converters[key] = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=o)})
    return _converters[key]


def convert(req: dict) -> dict:
    src = Path(str(req.get("input") or ""))
    if not src.is_file():
        return {"ok": False, "error": f"file not found: {src}"}
    t0 = time.time()
    conv = converter(bool(req.get("ocr")), req.get("tesseract"), req.get("tessdata"), list(req.get("langs") or []))
    res = conv.convert(str(src))
    doc = res.document
    return {"ok": True, "markdown": doc.export_to_markdown(), "pages": len(getattr(doc, "pages", {}) or {}),
            "seconds": round(time.time() - t0, 2)}


def main() -> int:
    if not MODELS.is_dir():
        send({"ready": False, "error": f"models folder not found: {MODELS}"})
        return 3
    send({"ready": True, "engine": ENGINE_VERSION, "docling": DOCLING_VERSION})
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            send({"ok": False, "error": "invalid JSON"})
            continue
        rid, cmd = req.get("id"), req.get("cmd")
        if cmd == "quit":
            break
        if cmd == "ping":
            send({"id": rid, "ok": True, "engine": ENGINE_VERSION, "docling": DOCLING_VERSION})
            continue
        if cmd != "convert":
            send({"id": rid, "ok": False, "error": f"unknown command: {cmd}"})
            continue
        try:
            out = convert(req)
        except Exception as e:  # noqa: BLE001 - satu dokumen gagal tidak boleh mematikan pekerja
            out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        send({"id": rid, **out})
    return 0


if __name__ == "__main__":
    sys.exit(main())
