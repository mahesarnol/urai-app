"""Identitas aplikasi: nama, versi, dan tautan resmi."""
from __future__ import annotations

from . import __version__

try:  # ditulis oleh GitHub Actions saat merakit installer (packaging/write_build_info.py)
    from ._build_info import COMMIT as _COMMIT, REPO as _REPO, VERSION as _BUILD_VERSION
except Exception:  # menjalankan dari kode sumber
    _REPO, _COMMIT, _BUILD_VERSION = "", "", ""

APP_NAME = "Urai App"
APP_ID = "UraiApp"
VERSION = _BUILD_VERSION or __version__
COMMIT = _COMMIT
YEAR = 2026

DEVELOPER = "mahesarnol"

# Dukungan lewat QRIS GoPay Merchant. Gambar QRIS diletakkan di web/img/qris.png.
# Nama ini wajib sama dengan nama merchant di QRIS (yang tampil di aplikasi pembayaran).
SUPPORT_MERCHANT = "Elnola Studio, Digital &"

# Repo GitHub, mis. "mahesarnol/urai-app". Diisi otomatis saat dirakit di GitHub Actions.
# Cek pembaruan hanya berjalan bila nilai ini ada (rakitan resmi).
GITHUB_REPO = _REPO
# Repo resmi untuk ditampilkan dan dibuka bila rakitan tidak membawa informasi repo.
DEFAULT_REPO = "mahesarnol/urai-app"


def repo_url() -> str:
    return f"https://github.com/{GITHUB_REPO or DEFAULT_REPO}"


def issues_url() -> str:
    return f"{repo_url()}/issues"


def releases_url() -> str:
    return f"{repo_url()}/releases" if GITHUB_REPO else ""


# Hanya tautan di daftar ini yang boleh dibuka dari tampilan aplikasi.
LINKS = {
    "key_claude": "https://platform.claude.com/settings/keys",
    "key_gemini": "https://aistudio.google.com/apikey",
    "key_deepseek": "https://platform.deepseek.com/api_keys",
    "key_openai": "https://platform.openai.com/api-keys",
    "key_openrouter": "https://openrouter.ai/keys",
    "markitdown": "https://github.com/microsoft/markitdown",
    "markmap": "https://markmap.js.org",
    "webview2": "https://developer.microsoft.com/microsoft-edge/webview2/",
    "ffmpeg": "https://www.gyan.dev/ffmpeg/builds/",
}
