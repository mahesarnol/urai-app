"""Salin tesseract.exe beserta DLL yang benar-benar dibutuhkannya saja.

Paket Tesseract untuk Windows (build UB Mannheim) membawa banyak DLL untuk alat pelatihan
(pango, cairo, glib, dan lain-lain) yang tidak dipakai Urai App. Skrip ini menelusuri tabel impor
tesseract.exe secara berulang dan hanya menyalin DLL yang ditemukan di folder yang sama.

    python packaging/tess_deps.py "C:\\Program Files\\Tesseract-OCR" build\\tesseract
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pefile  # ikut terpasang bersama PyInstaller di Windows


def imports_of(path: Path) -> list[str]:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
    ])
    names = []
    for attr in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
        for entry in getattr(pe, attr, []) or []:
            names.append(entry.dll.decode("ascii", "replace"))
    pe.close()
    return names


def closure(src: Path) -> list[Path]:
    local = {p.name.lower(): p for p in src.glob("*.dll")}
    todo, seen = [src / "tesseract.exe"], set()
    out = []
    while todo:
        cur = todo.pop()
        if cur.name.lower() in seen:
            continue
        seen.add(cur.name.lower())
        out.append(cur)
        for dll in imports_of(cur):
            hit = local.get(dll.lower())
            if hit and hit.name.lower() not in seen:
                todo.append(hit)
    return out


def main(src: str, dst: str) -> int:
    s, d = Path(src), Path(dst)
    if not (s / "tesseract.exe").exists():
        print(f"tesseract.exe tidak ada di {s}", file=sys.stderr)
        return 1
    d.mkdir(parents=True, exist_ok=True)
    files = closure(s)
    for f in files:
        shutil.copy2(f, d / f.name)
    (d / "BUNDLED-DLLS.txt").write_text("\n".join(sorted(f.name for f in files)) + "\n", encoding="utf-8")
    total = sum(f.stat().st_size for f in files) / 1048576
    print(f"{len(files)} file disalin ({total:.1f} MB):")
    for f in sorted(files, key=lambda x: x.name.lower()):
        print("  ", f.name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
