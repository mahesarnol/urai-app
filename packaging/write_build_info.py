"""Tulis informasi rakitan: src/urai/_build_info.py dan build/version_info.txt (resource versi Windows).

Dipanggil GitHub Actions sebelum PyInstaller. Nilai diambil dari variabel lingkungan GitHub:
GITHUB_REPOSITORY (mis. mahesarnol/urai-app), GITHUB_REF_NAME (tag v3.0.0), GITHUB_SHA.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else "0.0.0"


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    ref = os.environ.get("GITHUB_REF_NAME", "")
    sha = os.environ.get("GITHUB_SHA", "")
    version = project_version()
    if re.fullmatch(r"v?\d+\.\d+\.\d+", ref or ""):
        tag = ref.lstrip("v")
        if tag != version:
            print(f"Tag {ref} tidak sama dengan versi di pyproject.toml ({version})", file=sys.stderr)
            return 1
    (ROOT / "src" / "urai" / "_build_info.py").write_text(
        "# Dibuat otomatis oleh packaging/write_build_info.py. Jangan disunting.\n"
        f"REPO = {repo!r}\nVERSION = {version!r}\nCOMMIT = {sha!r}\n",
        encoding="utf-8",
    )
    nums = [int(x) for x in version.split(".")[:3]] + [0]
    while len(nums) < 4:
        nums.insert(-1, 0)
    t = tuple(nums[:4])
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    (build / "version_info.txt").write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'mahesarnol'),
      StringStruct('FileDescription', 'Urai App'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'Urai App'),
      StringStruct('LegalCopyright', '(c) 2026 mahesarnol. Lisensi MIT.'),
      StringStruct('OriginalFilename', 'Urai App.exe'),
      StringStruct('ProductName', 'Urai App'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"version={version}\n")
    print(f"Urai App {version} · repo={repo or '-'} · commit={sha[:7] or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
