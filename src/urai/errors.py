"""Ubah pesan error teknis menjadi kalimat yang mudah dipahami pengguna."""
from __future__ import annotations


class Cancelled(Exception):
    """Pengguna menekan Batalkan."""


class OcrUnavailable(Exception):
    """Mesin OCR offline (Tesseract) tidak ditemukan."""


_BY_NAME = {
    "AuthenticationError": "API key ditolak. Periksa API key di Pengaturan.",
    "PermissionDeniedError": "Akses ditolak oleh layanan AI. Periksa API key dan izin akun.",
    "NotFoundError": "Nama model tidak dikenali penyedia AI. Periksa nama model di Pengaturan.",
    "RateLimitError": "Batas pemakaian atau kuota layanan AI habis. Coba lagi nanti atau cek saldo akun.",
    "APIConnectionError": "Tidak bisa terhubung ke layanan AI. Periksa koneksi internet.",
    "APITimeoutError": "Layanan AI terlalu lama merespons. Coba lagi.",
    "BadRequestError": "Permintaan ditolak layanan AI. Model mungkin tidak bisa membaca gambar atau dokumen terlalu panjang.",
    "UnsupportedFormatException": "Format file ini tidak didukung.",
    "FileNotFoundError": "File tidak ditemukan. Mungkin sudah dipindah atau dihapus.",
    "PermissionError": "Tidak punya izin membuka atau menyimpan file ini. Tutup file itu di aplikasi lain, lalu coba lagi.",
    "IsADirectoryError": "Yang dipilih adalah folder, bukan file.",
    "ConnectionError": "Tidak bisa membuka link. Periksa koneksi internet.",
    "Timeout": "Halaman terlalu lama merespons. Coba lagi.",
    "MissingDependencyException": "Komponen untuk format ini belum terpasang. Pasang ulang Urai App.",
    "UnknownValueError": "Suara tidak dikenali. Rekaman kurang jelas atau tidak ada ucapan.",
    "RequestError": "Layanan pengubah suara ke teks tidak bisa dihubungi. Periksa internet, atau rekaman terlalu panjang.",
    "CouldntDecodeError": "Rekaman tidak bisa dibuka. Untuk MP3/M4A, pasang FFmpeg (lihat Panduan).",
    "RequestBlocked": "YouTube menolak permintaan dari jaringan ini. Coba lagi nanti.",
    "IpBlocked": "YouTube menolak permintaan dari jaringan ini. Coba lagi nanti.",
    "VideoUnavailable": "Video tidak tersedia. Mungkin privat atau sudah dihapus.",
    "OcrUnavailable": "Mesin baca scan offline (Tesseract) tidak ditemukan. Pasang ulang Urai App.",
    "PdfiumError": "PDF tidak bisa dibuka. File mungkin rusak atau dikunci kata sandi.",
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


def friendly_error(exc: BaseException) -> str:
    inner = _inner(exc)
    name = type(inner).__name__
    text = str(inner).strip()
    first = text.splitlines()[0] if text else name
    low = text.lower()
    if name in _BY_NAME:
        return _BY_NAME[name]
    for key, msg in _BY_NAME.items():
        if key in name:
            return msg
    if "ffmpeg" in low or "ffprobe" in low:
        return "Rekaman MP3/M4A butuh FFmpeg. Lihat Panduan bagian rekaman suara."
    if "transcript" in name.lower() or "transcript" in low:
        return "Video ini tidak punya subtitle atau transkrip yang bisa diambil."
    if "password" in low or "encrypted" in low:
        return "File ini dikunci kata sandi. Buka kuncinya dulu, lalu coba lagi."
    return first[:220]
