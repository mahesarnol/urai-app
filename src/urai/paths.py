"""Lokasi file aplikasi, baik saat dijalankan dari kode sumber maupun dari installer."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .info import APP_ID, APP_NAME

PKG_DIR = Path(__file__).resolve().parent
IS_WINDOWS = sys.platform == "win32"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """Folder berisi file pendukung: _internal (PyInstaller) atau akar repo."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return PKG_DIR.parent.parent


def web_dir() -> Path:
    return PKG_DIR / "web"


def samples_dir() -> Path:
    return PKG_DIR / "samples"


def notices_file() -> Path:
    return bundle_root() / "THIRD-PARTY-NOTICES.txt"


def license_file() -> Path:
    return bundle_root() / "LICENSE"


def config_dir() -> Path:
    base = os.environ.get("APPDATA") if IS_WINDOWS else os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    d = root / APP_ID
    d.mkdir(parents=True, exist_ok=True)
    return d


def local_data_dir() -> Path:
    """Data besar yang tidak perlu ikut profil roaming: %LOCALAPPDATA%\\UraiApp (Windows)."""
    base = os.environ.get("LOCALAPPDATA") if IS_WINDOWS else os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_ID


def engines_dir() -> Path:
    """Mesin tambahan yang diunduh terpisah, mis. mesin PDF teliti (Docling)."""
    return local_data_dir() / "engines"


def log_dir() -> Path:
    d = config_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def documents_dir() -> Path:
    """Folder Dokumen milik pengguna (ikut pengalihan OneDrive di Windows)."""
    if IS_WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]

            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            fid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(out)) == 0:
                path = Path(out.value)
                ctypes.windll.ole32.CoTaskMemFree(out)
                return path
        except Exception:
            pass
    return Path.home() / "Documents"


def default_output_dir() -> Path:
    return documents_dir() / APP_NAME


def bundled_tesseract_dir() -> Path:
    """Tesseract yang ikut dipasang oleh installer: <app>/_internal/tesseract."""
    return bundle_root() / "tesseract"
