"""Pekerja Docling tiruan untuk uji: berbicara dengan protokol yang sama seperti packaging/docling/worker.py.

Perilaku diatur dari nama file masukan: "fail" -> ok:false, "crash" -> proses mati, "slow" -> tidak menjawab.
FAKE_DOCLING_LOG: file tempat mencatat setiap mulai dan setiap permintaan (satu baris JSON per kejadian).
FAKE_DOCLING_NOT_READY: bila diisi, pekerja menolak mulai.
"""
import json
import os
import sys
import time
from pathlib import Path

LOG = os.environ.get("FAKE_DOCLING_LOG")
proto = open(sys.stdout.fileno(), "w", encoding="utf-8", buffering=1, closefd=False)
sys.stdout = sys.stderr


def note(obj):
    if LOG:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj) + "\n")


def send(obj):
    proto.write(json.dumps(obj, ensure_ascii=False) + "\n")
    proto.flush()


MARKDOWN = (
    "<!-- image -->\n## Judul {stem}\n\n## 1. Bagian Pertama   \n\n\n\nTeks dari mesin teliti.  \n\n"
    "| Kolom A | Kolom B |\n|---------|---------|\n| isi 1   | isi 2   |\n\n<!-- image -->\n\n\n## 1.1 Rincian\n\nRincian kecil."
)


def main():
    note({"event": "start", "pid": os.getpid()})
    print("log pustaka yang tidak boleh masuk ke stdout", file=sys.stderr)
    if os.environ.get("FAKE_DOCLING_NOT_READY"):
        send({"ready": False, "error": "models folder not found"})
        return 3
    send({"ready": True, "engine": "1", "docling": "fake-1.0"})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        note({"event": req.get("cmd"), **{k: req.get(k) for k in ("input", "ocr", "tesseract", "tessdata", "langs")}})
        if req.get("cmd") == "quit":
            break
        if req.get("cmd") == "ping":
            send({"id": req.get("id"), "ok": True, "engine": "1", "docling": "fake-1.0"})
            continue
        name = Path(req.get("input") or "").name.lower()
        if "crash" in name:
            os._exit(1)
        if "slow" in name:
            time.sleep(60)
        if "fail" in name:
            send({"id": req.get("id"), "ok": False, "error": "RuntimeError: boom"})
            continue
        send({"id": req.get("id"), "ok": True, "markdown": MARKDOWN.format(stem=Path(name).stem), "pages": 1, "seconds": 0.1})
    return 0


if __name__ == "__main__":
    sys.exit(main())
