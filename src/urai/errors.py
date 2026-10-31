"""Ubah pesan error teknis menjadi kalimat yang mudah dipahami pengguna."""
from __future__ import annotations

from .i18n import t


class Cancelled(Exception):
    """Pengguna menekan Batalkan."""


class OcrUnavailable(Exception):
    """Mesin OCR offline (Tesseract) tidak ditemukan."""


# Nama kelas exception -> kunci teks di i18n.
_BY_NAME = {
    "AuthenticationError": "err.auth",
    "PermissionDeniedError": "err.denied",
    "NotFoundError": "err.model",
    "RateLimitError": "err.rate",
    "APIConnectionError": "err.ai_conn",
    "APITimeoutError": "err.ai_timeout",
    "BadRequestError": "err.ai_bad",
    "UnsupportedFormatException": "err.format",
    "FileNotFoundError": "err.not_found",
    "PermissionError": "err.permission",
    "IsADirectoryError": "err.is_dir",
    "ConnectionError": "err.conn",
    "Timeout": "err.timeout",
    "MissingDependencyException": "err.missing_dep",
    "UnknownValueError": "err.speech",
    "RequestError": "err.speech_service",
    "CouldntDecodeError": "err.audio_decode",
    "RequestBlocked": "err.yt_blocked",
    "IpBlocked": "err.yt_blocked",
    "VideoUnavailable": "err.yt_unavailable",
    "OcrUnavailable": "err.ocr",
    "PdfiumError": "err.pdf",
}


def _inner(exc: BaseException) -> BaseException:
    """MarkItDown membungkus error asli di dalam 'attempts'."""
    attempts = getattr(exc, "attempts", None)
    if attempts:
        for a in attempts:
            info = getattr(a, "exc_info", None)
            if info and info[1] is not None:
                return info[1]
    return exc


def error_ref(exc: BaseException) -> tuple[str, dict]:
    """(kunci teks, argumen) untuk error ini, supaya pesannya bisa diterjemahkan ulang saat bahasa diganti."""
    inner = _inner(exc)
    name = type(inner).__name__
    text = str(inner).strip()
    first = text.splitlines()[0] if text else name
    low = text.lower()
    if name in _BY_NAME:
        return _BY_NAME[name], {}
    for key, ref in _BY_NAME.items():
        if key in name:
            return ref, {}
    if "ffmpeg" in low or "ffprobe" in low:
        return "err.ffmpeg", {}
    if "transcript" in name.lower() or "transcript" in low:
        return "err.transcript", {}
    if "password" in low or "encrypted" in low:
        return "err.password", {}
    return "err.other", {"text": first[:220]}


def friendly_error(exc: BaseException) -> str:
    key, kw = error_ref(exc)
    return t(key, **kw)
