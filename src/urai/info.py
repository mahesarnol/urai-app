"""Identitas aplikasi: nama, versi, kontak, dan tautan resmi."""
from __future__ import annotations

from . import __version__

try:  # ditulis oleh GitHub Actions saat merakit installer (packaging/write_build_info.py)
    from ._build_info import COMMIT as _COMMIT, REPO as _REPO, VERSION as _BUILD_VERSION
except Exception:  # menjalankan dari kode sumber
    _REPO, _COMMIT, _BUILD_VERSION = "", "", ""

APP_NAME = "Urai App"
APP_ID = "UraiApp"
TAGLINE = "Urai dokumen jadi teks Markdown yang rapi"
VERSION = _BUILD_VERSION or __version__
COMMIT = _COMMIT
YEAR = 2026

DEVELOPER = "mahesarnol"
CONTACT_EMAIL = "maheswara.as@gmail.com"
SOCIAL_HANDLE = "@mahesarnol"

# Dukungan lewat QRIS GoPay Merchant. Gambar QRIS diletakkan di web/img/qris.png.
SUPPORT_MERCHANT = "mahesarnol app"

# Repo GitHub, mis. "mahesarnol/urai-app". Diisi otomatis saat dirakit di GitHub Actions.
GITHUB_REPO = _REPO


def repo_url() -> str:
    return f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else ""


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
