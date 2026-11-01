"""Menyimpan pengaturan pengguna (JSON di %APPDATA%\\UraiApp) dan API key (Windows Credential Manager)."""
from __future__ import annotations

import copy
import json
import logging
import os
import threading
from pathlib import Path

from .ai import PROVIDERS
from .summarize import PROMPT_KINDS, PROMPT_LIMIT
from .i18n import t
from .info import APP_ID
from .paths import config_dir

log = logging.getLogger("urai.settings")

DEFAULTS: dict = {
    "lang": "en",                  # en | id (bahasa tampilan, teks hasil, dan rangkuman AI)
    "theme": "system",             # system | light | dark
    "out_mode": "separate",        # separate | combined
    "combined_name": "",           # kosong berarti nama bawaan sesuai bahasa ("Combined" atau "Gabungan")
    "ocr_mode": "offline",         # off | offline | ai
    "langs": ["ind", "eng"],
    "quality": "fast",             # fast | accurate
    "pdf_engine": "standard",      # standard | docling (mesin PDF teliti yang diunduh terpisah)
    "embedded": True,
    "provider": "gemini",
    "models": {},                  # model pilihan per penyedia; kosong berarti bawaan
    "base_urls": {},               # alamat server untuk penyedia "other" (dan bila diubah)
    "location": "custom",          # custom | same
    "custom_dir": "",              # kosong berarti Dokumen\Urai App
    "runs": 0,                     # berapa kali konversi selesai (untuk ajakan dukungan)
    "supported": False,
    "mm_src": "",                  # struct | ai | sum; kosong berarti dipilih otomatis
    "mm_kind": "poin",             # poin | notulen | lengkap
    "sum_kind": "sedang",          # singkat | sedang | rinci (rangkuman teks)
    "prompts": {},                 # instruksi AI buatan pengguna per jenis; kosong berarti bawaan
    "mm_style": None,              # gaya mind map terakhir
    "pdf": {"size": "A4", "orient": "land", "title": True, "label": True, "text": False},
}

_ENUMS = {
    "lang": {"en", "id"},
    "theme": {"system", "light", "dark"},
    "out_mode": {"separate", "combined"},
    "ocr_mode": {"off", "offline", "ai"},
    "quality": {"fast", "accurate"},
    "pdf_engine": {"standard", "docling"},
    "location": {"custom", "same"},
    "mm_src": {"", "struct", "ai", "sum"},
    "mm_kind": {"poin", "notulen", "lengkap"},
    "sum_kind": {"singkat", "sedang", "rinci"},
}
_LEGACY = {"mm_kind": {"umum": "poin", "laporan": "lengkap"}}  # nilai dari versi lama tetap dipahami
_LANGS = {"ind", "eng", "jav", "sun", "ara"}
KEYRING_SERVICE = APP_ID


def _clean(key: str, value):
    """Tolak nilai yang bentuknya salah supaya file pengaturan rusak tidak membuat aplikasi macet."""
    default = DEFAULTS[key]
    if key in _LEGACY and isinstance(value, str):
        value = _LEGACY[key].get(value, value)
    if key in _ENUMS:
        return value if value in _ENUMS[key] else default
    if key == "langs":
        if isinstance(value, list):
            langs = [l for l in value if l in _LANGS]
            return langs or list(default)
        return list(default)
    if key == "provider":
        return value if value in PROVIDERS else default
    if key in ("models", "base_urls"):
        if isinstance(value, dict):
            return {k: str(v)[:300] for k, v in value.items() if k in PROVIDERS and isinstance(v, str)}
        return {}
    if key == "pdf":
        out = dict(default)
        if isinstance(value, dict):
            if value.get("size") in ("A4", "A3", "F4"):
                out["size"] = value["size"]
            if value.get("orient") in ("land", "port"):
                out["orient"] = value["orient"]
            for k in ("title", "label", "text"):
                if isinstance(value.get(k), bool):
                    out[k] = value[k]
        return out
    if key == "prompts":
        if not isinstance(value, dict):
            return {}
        return {k: v.strip()[:PROMPT_LIMIT] for k, v in value.items() if k in PROMPT_KINDS and isinstance(v, str) and v.strip()}
    if key == "mm_style":
        return value if isinstance(value, dict) else None
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, int):
        return value if isinstance(value, int) and value >= 0 else default
    if isinstance(default, str):
        return str(value)[:500] if isinstance(value, str) else default
    return value


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else (config_dir() / "settings.json")
        self._lock = threading.Lock()
        self.data = copy.deepcopy(DEFAULTS)
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except Exception:
            log.warning("Pengaturan tidak bisa dibaca, memakai bawaan", exc_info=True)
            return
        if isinstance(raw, dict):
            for k in DEFAULTS:
                if k in raw:
                    self.data[k] = _clean(k, raw[k])

    def save(self) -> None:
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            try:
                tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
                os.replace(tmp, self.path)
            except OSError:
                log.warning("Pengaturan gagal disimpan", exc_info=True)

    def update(self, patch: dict) -> dict:
        for k, v in (patch or {}).items():
            if k in DEFAULTS:
                self.data[k] = _clean(k, v)
        self.save()
        return self.public()

    def get(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def public(self) -> dict:
        return copy.deepcopy(self.data)

    def combined_name(self) -> str:
        """Nama file gabungan. Kosong berarti nama bawaan dalam bahasa aktif."""
        return self.data["combined_name"].strip() or t("combined.default")

    def model_for(self, provider: str) -> str:
        return self.data["models"].get(provider) or PROVIDERS.get(provider, PROVIDERS["other"])["model"]

    def base_url_for(self, provider: str) -> str:
        if provider in self.data["base_urls"]:
            return self.data["base_urls"][provider]
        return PROVIDERS.get(provider, PROVIDERS["other"])["base_url"]


# ---------- API key ----------
# Disimpan di Windows Credential Manager lewat keyring. Bila tidak tersedia (mis. Linux tanpa
# layanan kunci), disimpan di file keys.json di folder pengaturan yang hanya bisa dibaca pemiliknya.

def _keyfile() -> Path:
    return config_dir() / "keys.json"


def _read_keyfile() -> dict:
    try:
        data = json.loads(_keyfile().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_keyfile(data: dict) -> None:
    p = _keyfile()
    p.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def get_key(provider: str) -> str:
    try:
        import keyring

        val = keyring.get_password(KEYRING_SERVICE, provider)
        if val:
            return val
    except Exception:
        log.debug("keyring tidak tersedia", exc_info=True)
    return _read_keyfile().get(provider, "")


def set_key(provider: str, key: str) -> str:
    """Simpan (atau hapus bila kosong). Mengembalikan tempat penyimpanan: 'keyring' atau 'file'."""
    key = (key or "").strip()
    try:
        import keyring

        if key:
            keyring.set_password(KEYRING_SERVICE, provider, key)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, provider)
            except Exception:
                pass
        data = _read_keyfile()
        if provider in data:
            data.pop(provider)
            _write_keyfile(data)
        return "keyring"
    except Exception:
        log.info("keyring tidak tersedia, API key disimpan di file pengaturan")
    data = _read_keyfile()
    if key:
        data[provider] = key
    else:
        data.pop(provider, None)
    _write_keyfile(data)
    return "file"


def has_key(provider: str) -> bool:
    return bool(get_key(provider))
