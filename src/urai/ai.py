"""Penghubung ke penyedia AI yang kompatibel dengan API OpenAI (Claude, Gemini, DeepSeek, OpenAI, OpenRouter)."""
from __future__ import annotations

import base64
import io
import struct
import zlib

from PIL import Image

PROVIDERS = {
    "claude": {"name": "Claude (Anthropic)", "base_url": "https://api.anthropic.com/v1/", "model": "claude-haiku-5-5", "key_link": "key_claude"},
    "gemini": {"name": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-3.8-flash", "key_link": "key_gemini"},
    "deepseek": {"name": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-flash", "key_link": "key_deepseek"},
    "openai": {"name": "OpenAI", "base_url": "", "model": "gpt-5.6-terra", "key_link": "key_openai"},
    "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "model": "google/gemini-3.5-flash", "key_link": "key_openrouter"},
    "other": {"name": "Server lain (kompatibel OpenAI)", "base_url": "", "model": "", "key_link": ""},
}

OCR_PROMPT = (
    "Tuliskan ulang seluruh teks yang terlihat pada gambar ini apa adanya, dengan urutan dan susunan seperti aslinya. "
    "Jika ada tabel, tulis sebagai tabel Markdown. Jangan menambahkan komentar atau penjelasan."
)
IMAGE_PROMPT = (
    "Tuliskan ulang seluruh teks yang terlihat pada gambar ini apa adanya. Jika gambar berisi foto, grafik, diagram, "
    "atau bagian visual lain, jelaskan isinya secara singkat dan jelas dalam Bahasa Indonesia. Jangan menambahkan komentar lain."
)


class AIConfig:
    def __init__(self, provider: str, api_key: str, model: str = "", base_url: str | None = None):
        preset = PROVIDERS.get(provider, PROVIDERS["other"])
        self.provider = provider if provider in PROVIDERS else "other"
        self.api_key = (api_key or "").strip()
        self.model = (model or preset["model"]).strip()
        self.base_url = (preset["base_url"] if base_url is None else base_url).strip()
        self.name = preset["name"]

    @property
    def ready(self) -> bool:
        return bool(self.api_key and self.model)

    def client(self):
        from openai import OpenAI

        kw = {"api_key": self.api_key, "timeout": 180, "max_retries": 2}
        if self.base_url:
            kw["base_url"] = self.base_url
        return OpenAI(**kw)


def _data_uri(img: Image.Image, max_side: int = 2000) -> str:
    img = img.convert("RGB")
    if max(img.size) > max_side:
        k = max_side / max(img.size)
        img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _content(resp) -> str:
    msg = resp.choices[0].message
    return (getattr(msg, "content", None) or "").strip()


def vision_text(cfg: AIConfig, img: Image.Image, prompt: str = OCR_PROMPT) -> str:
    resp = cfg.client().chat.completions.create(
        model=cfg.model,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": _data_uri(img)}},
        ]}],
    )
    return _content(resp)


def chat(cfg: AIConfig, system: str, user: str) -> str:
    resp = cfg.client().chat.completions.create(
        model=cfg.model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return _content(resp)


def _tiny_png() -> bytes:
    size, rgb = 16, (220, 38, 38)
    raw = b"".join(b"\x00" + bytes(rgb) * size for _ in range(size))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def test_connection(cfg: AIConfig) -> str:
    """Kirim satu gambar kecil. Mengembalikan jawaban model, atau melempar exception."""
    img = Image.open(io.BytesIO(_tiny_png()))
    return vision_text(cfg, img, "Apa warna gambar ini? Jawab satu kata.")
