"""Susun THIRD-PARTY-NOTICES.txt: lisensi semua komponen yang ikut dipasang bersama Urai App.

Daftar pustaka Python diambil dari dependensi Urai App yang benar-benar terpasang di lingkungan
perakitan (ditelusuri dari pyproject.toml), lengkap dengan teks lisensinya dari metadata paket.
Ditambah komponen non-Python: Python, Tesseract dan DLL-nya, data bahasa, PDFium, markmap, d3, huruf.

    python packaging/gen_notices.py            (menulis THIRD-PARTY-NOTICES.txt di akar repo)
"""
from __future__ import annotations

import re
import sys
import tomllib
import urllib.request
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "urai" / "web"
TESS = ROOT / "build" / "tesseract"
OUT = ROOT / "THIRD-PARTY-NOTICES.txt"
LICENSE_FILE = re.compile(r"(^|/)(licen[cs]e|copying|notice|authors?)([._-][^/]*)?$", re.I)
RULE = "=" * 78

# Lisensi DLL yang ikut dibawa Tesseract (paket MSYS2/MinGW). Kunci: awalan nama file.
DLL_LICENSES = [
    ("libtesseract", "Apache-2.0"), ("libleptonica", "BSD-2-Clause"), ("libarchive", "BSD-2-Clause"),
    ("libcurl", "curl"), ("libssl", "Apache-2.0"), ("libcrypto", "Apache-2.0"), ("libnghttp", "MIT"),
    ("libssh2", "BSD-3-Clause"), ("libpsl", "MIT"), ("libbrotli", "MIT"), ("libidn2", "LGPL-3.0-or-later OR GPL-2.0-or-later"),
    ("libunistring", "LGPL-3.0-or-later OR GPL-2.0-or-later"), ("libiconv", "LGPL-2.1-or-later"), ("libintl", "LGPL-2.1-or-later"),
    ("libpng", "Libpng"), ("libjpeg", "IJG AND BSD-3-Clause"), ("libturbojpeg", "IJG AND BSD-3-Clause"), ("libtiff", "libtiff"),
    ("libwebp", "BSD-3-Clause"), ("libsharpyuv", "BSD-3-Clause"), ("libopenjp2", "BSD-2-Clause"), ("libgif", "MIT"),
    ("zlib", "Zlib"), ("libzstd", "BSD-3-Clause"), ("liblzma", "0BSD"), ("libbz2", "bzip2-1.0.6"), ("liblz4", "BSD-2-Clause"),
    ("libdeflate", "MIT"), ("libLerc", "Apache-2.0"), ("libjbig", "GPL-2.0-or-later"), ("libb2", "CC0-1.0"),
    ("libexpat", "MIT"), ("libxml2", "MIT"), ("libgcc", "GPL-3.0-or-later WITH GCC-exception-3.1"),
    ("libstdc++", "GPL-3.0-or-later WITH GCC-exception-3.1"), ("libgomp", "GPL-3.0-or-later WITH GCC-exception-3.1"),
    ("libwinpthread", "MIT AND BSD-3-Clause"), ("libicu", "Unicode-3.0"), ("libcairo", "LGPL-2.1-only OR MPL-1.1"),
    ("libpango", "LGPL-2.1-or-later"), ("libglib", "LGPL-2.1-or-later"), ("libgobject", "LGPL-2.1-or-later"),
    ("libharfbuzz", "MIT"), ("libfreetype", "FTL OR GPL-2.0-or-later"), ("libfontconfig", "MIT"), ("libpcre2", "BSD-3-Clause"),
    ("libffi", "MIT"), ("libpixman", "MIT"), ("libfribidi", "LGPL-2.1-or-later"), ("libgraphite2", "LGPL-2.1-or-later OR MPL-2.0"),
    ("libdatrie", "LGPL-2.1-or-later"), ("libthai", "LGPL-2.1-or-later"),
]


def section(title: str, body: str) -> str:
    return f"\n{RULE}\n{title}\n{RULE}\n\n{body.strip()}\n"


def spdx_text(spdx_id: str) -> str:
    """Teks lisensi dari daftar resmi SPDX (butuh internet; dipakai saat perakitan di GitHub Actions)."""
    url = f"https://raw.githubusercontent.com/spdx/license-list-data/main/text/{spdx_id}.txt"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:  # noqa: S310 - alamat tetap
            return r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return f"Teks lengkap: https://spdx.org/licenses/{spdx_id}.html"


def requirement_roots() -> list[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return list(data["project"]["dependencies"])


def closure() -> dict[str, metadata.Distribution]:
    """Semua distribusi yang terpasang dan dibutuhkan Urai App, termasuk extras yang dipakai."""
    found: dict[str, tuple[metadata.Distribution, set[str]]] = {}
    stack = [Requirement(r) for r in requirement_roots()]
    while stack:
        req = stack.pop()
        try:
            dist = metadata.distribution(req.name)
        except metadata.PackageNotFoundError:
            continue
        key = canonicalize_name(dist.metadata["Name"])
        extras = set(req.extras)
        if key in found and extras <= found[key][1]:
            continue
        prev = found.get(key, (dist, set()))[1]
        found[key] = (dist, prev | extras)
        for raw in dist.requires or []:
            sub = Requirement(raw)
            if sub.marker is not None:
                envs = [{"extra": e} for e in (found[key][1] or {""})]
                if not any(sub.marker.evaluate(env) for env in envs):
                    continue
            stack.append(sub)
    return {k: v[0] for k, v in sorted(found.items())}


def license_name(dist: metadata.Distribution) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr
    lic = (md.get("License") or "").strip()
    if lic and len(lic) < 80 and "\n" not in lic:
        return lic
    classifiers = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    return ", ".join(classifiers) or (lic.splitlines()[0][:80] if lic else "lihat teks di bawah")


def license_texts(dist: metadata.Distribution) -> list[tuple[str, str]]:
    out = []
    for f in dist.files or []:
        name = str(f).replace("\\", "/")
        if not (LICENSE_FILE.search(name) or "/licenses/" in name):
            continue
        if name.endswith((".py", ".pyc", ".json", "RECORD", "WHEEL", "METADATA", "INSTALLER", "REQUESTED")):
            continue
        try:
            p = Path(f.locate())
            if p.is_file() and p.stat().st_size < 400_000:
                out.append((name.split("/")[-1], p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    if not out:
        lic = (dist.metadata.get("License") or "").strip()
        if len(lic) > 80:
            out.append(("License", lic))
    return out


def python_notice() -> str:
    for cand in (Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE"):
        if cand.exists():
            return cand.read_text(encoding="utf-8", errors="replace")
    return "Python Software Foundation License Version 2. Teks lengkap: https://docs.python.org/3/license.html"


def tesseract_notice() -> str:
    parts = ["Tesseract OCR (Apache-2.0), build Windows dari UB Mannheim: https://github.com/UB-Mannheim/tesseract",
             "Kode sumber Tesseract: https://github.com/tesseract-ocr/tesseract",
             "Data bahasa tessdata_fast 4.1.0 (Apache-2.0): https://github.com/tesseract-ocr/tessdata_fast", ""]
    dlls_file = TESS / "BUNDLED-DLLS.txt"
    if dlls_file.exists():
        parts.append("Pustaka pendukung yang ikut dibawa (dari paket MSYS2 MinGW, kode sumber:")
        parts.append("https://github.com/msys2/MINGW-packages). Setiap pustaka memakai lisensinya sendiri:")
        for name in dlls_file.read_text(encoding="utf-8").split():
            if name.lower() == "tesseract.exe":
                continue
            lic = next((l for prefix, l in DLL_LICENSES if name.lower().startswith(prefix.lower())), "lihat paket MSYS2")
            parts.append(f"  {name:<36} {lic}")
        parts.append("")
        parts.append("Pustaka LGPL dimuat sebagai DLL terpisah dan boleh diganti oleh pengguna dengan versi lain.")
    for f in ("LICENSE-tesseract.txt",):
        p = TESS / f
        if p.exists():
            parts += ["", "-- Lisensi Tesseract --", p.read_text(encoding="utf-8", errors="replace")]
    return "\n".join(parts)


def main() -> int:
    blocks = [
        "URAI APP: PEMBERITAHUAN KOMPONEN PIHAK KETIGA\n\n"
        "Urai App (c) 2026 mahesarnol, dirilis dengan lisensi MIT (lihat file LICENSE).\n"
        "Urai App dibangun di atas MarkItDown dari Microsoft (lisensi MIT) dan tidak berafiliasi dengan Microsoft.\n"
        "Berikut komponen pihak ketiga yang ikut dipasang bersama Urai App beserta lisensinya.\n"
        "Microsoft Edge WebView2 Runtime tidak ikut dipasang; komponen itu bagian dari Windows."
    ]
    blocks.append(section("Python", python_notice()))
    blocks.append(section("Tesseract OCR dan pustaka pendukungnya", tesseract_notice()))
    for spdx in ("Apache-2.0", "LGPL-2.1-or-later", "LGPL-3.0-or-later"):
        if spdx != "Apache-2.0" and not (TESS / "BUNDLED-DLLS.txt").exists():
            continue
        blocks.append(section(f"Teks lisensi {spdx}", spdx_text(spdx)))
    for name, label in (("markmap-view", "markmap-view (MIT)"), ("markmap-lib", "markmap-lib (MIT)"), ("d3", "d3 (ISC)")):
        p = WEB / "vendor" / f"{name}.LICENSE.txt"
        if p.exists():
            blocks.append(section(label, p.read_text(encoding="utf-8")))
    for f, label in (("PlusJakartaSans-OFL.txt", "Huruf Plus Jakarta Sans (SIL OFL 1.1)"), ("JetBrainsMono-OFL.txt", "Huruf JetBrains Mono (SIL OFL 1.1)")):
        p = WEB / "fonts" / f
        if p.exists():
            blocks.append(section(label, p.read_text(encoding="utf-8")))
    dists = closure()
    index = [f"  {d.metadata['Name']} {d.version}: {license_name(d)}" for d in dists.values()]
    blocks.append(section("Pustaka Python", "\n".join(index)))
    for d in dists.values():
        texts = license_texts(d)
        body = f"Versi {d.version}. Lisensi: {license_name(d)}\n"
        home = d.metadata.get("Home-page") or next((u.split(",", 1)[-1].strip() for u in d.metadata.get_all("Project-URL") or []), "")
        if home:
            body += f"Situs: {home}\n"
        for fname, text in texts:
            body += f"\n-- {fname} --\n{text.strip()}\n"
        blocks.append(section(d.metadata["Name"], body))
    OUT.write_text("\n".join(blocks) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(dists)} pustaka Python, {OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
