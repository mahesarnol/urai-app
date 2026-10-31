# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: merakit "dist/Urai App/Urai App.exe" (mode onedir). Dijalankan dari akar repo:
#     pyinstaller packaging/urai.spec --noconfirm
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - SPECPATH disediakan PyInstaller
SRC = ROOT / "src"
BUILD = ROOT / "build"

datas = [
    (str(SRC / "urai" / "web"), "urai/web"),
    (str(SRC / "urai" / "samples"), "urai/samples"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD-PARTY-NOTICES.txt"), "."),
]
tesseract = BUILD / "tesseract"
if tesseract.exists():
    datas.append((str(tesseract), "tesseract"))
else:
    print("PERINGATAN: build/tesseract tidak ada. Jalankan packaging/fetch_tesseract.ps1 dulu.")

# Data yang dibaca pustaka saat berjalan
datas += collect_data_files("magika")                 # model pengenal jenis file (dipakai MarkItDown)
datas += collect_data_files("pdfminer")               # tabel huruf PDF
datas += collect_data_files("reportlab")
datas += collect_data_files("pypdfium2")
datas += collect_data_files("pypdfium2_raw")
datas += collect_data_files("speech_recognition")
for dist in ("markitdown", "magika", "keyring", "openai", "pypdfium2", "pypdfium2_raw", "youtube-transcript-api", "pywebview"):
    try:
        datas += copy_metadata(dist)
    except Exception as e:  # noqa: BLE001
        print(f"metadata {dist} dilewati: {e}")

binaries = collect_dynamic_libs("pypdfium2_raw")

hiddenimports = (
    collect_submodules("markitdown")
    + collect_submodules("urai")
    + ["keyring.backends.Windows", "win32ctypes.core", "win32ctypes.pywin32", "pydub", "speech_recognition"]
)

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "PyQt5", "PyQt6", "PySide2", "PySide6", "gi", "scipy", "notebook"],
    noarchive=False,
    optimize=0,
)
# Hook bawaan speech_recognition ikut membawa data pocketsphinx (sekitar 38 MB) dan program flac untuk
# Linux/macOS. Urai App hanya memakai layanan Google dan flac-win32, jadi sisanya dibuang di sini.
_DROP = ("pocketsphinx-data", "flac-linux", "flac-mac")


def _keep(entry) -> bool:
    dest = str(entry[0]).replace("\\", "/")
    return not (dest.startswith("speech_recognition/") and any(d in dest for d in _DROP))


a.datas = [d for d in a.datas if _keep(d)]
a.binaries = [b for b in a.binaries if _keep(b)]

pyz = PYZ(a.pure)  # noqa: F821

version_file = BUILD / "version_info.txt"
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Urai App",
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "packaging" / "urai.ico"),
    version=str(version_file) if version_file.exists() else None,
    upx=False,
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Urai App",
)
