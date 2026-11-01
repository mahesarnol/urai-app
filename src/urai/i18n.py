"""Teks yang tampil ke pengguna dalam dua bahasa: English (bawaan) dan Bahasa Indonesia.

    t("api.need_key")               teks dalam bahasa aktif
    t("meta.pages", n=3)            nilai berupa tuple (tunggal, jamak) dipilih dari n
    set_lang("id")                  ganti bahasa aktif (dipanggil Api saat pengaturan berubah)

Bilangan bulat di argumen otomatis diberi pemisah ribuan sesuai bahasa (1,240 atau 1.240).
Kunci bahasa "en" dan "id" wajib sama persis (diuji di tests/test_i18n.py).
"""
from __future__ import annotations

from datetime import datetime

LANGS = ("en", "id")
DEFAULT = "en"

STRINGS: dict[str, dict[str, str | tuple[str, str]]] = {
    "en": {
        # ---------- aplikasi ----------
        "app.tagline": "Turn documents into clean Markdown text",
        "app.broken_ui": "Urai App can't open because its display component is damaged. Please reinstall Urai App.",
        "app.need_webview2": ("Urai App needs the Microsoft Edge WebView2 Runtime to show its window, "
                              "but it wasn't found on this computer.\n\n"
                              "WebView2 is free from Microsoft. Open its download page now? "
                              "After installing it, open Urai App again."),
        "cli.paths": "files or folders to add to the list right away",
        "cli.dev": "run the interface in a normal browser (development)",
        # ---------- jenis file dan keterangan di daftar ----------
        "kind.pdf": "PDF", "kind.doc": "Word", "kind.ppt": "PowerPoint", "kind.xls": "Excel", "kind.csv": "CSV",
        "kind.html": "HTML", "kind.epub": "EPUB", "kind.zip": "ZIP", "kind.msg": "Outlook", "kind.img": "Image",
        "kind.aud": "Audio", "kind.text": "Text", "kind.yt": "YouTube link", "kind.web": "Web page link",
        "kind.file": "File",
        "meta.pages": ("{n} page", "{n} pages"),
        "meta.slides": ("{n} slide", "{n} slides"),
        "meta.sheets": ("{n} sheet", "{n} sheets"),
        "link.yt_name": "YouTube video",
        "link.web_name": "Page on {host}",
        "samples.folder": "samples",
        "combined.default": "Combined",
        # ---------- bahasa OCR ----------
        "lang.ind": "Indonesian", "lang.eng": "English", "lang.jav": "Javanese", "lang.sun": "Sundanese",
        "lang.ara": "Arabic",
        "ocr.label_ai": "AI ({name})",
        "ocr.label_offline": "Offline OCR ({names})",
        "ocr.failed": "Tesseract failed: {msg}",
        "ocr.exit_code": "code {n}",
        "ai.other_name": "Other server (OpenAI-compatible)",
        # ---------- kabar proses ----------
        "sub.page": "{label} · page {k} of {n}",
        "sub.image_read": "{label} · reading image…",
        "sub.image_k": "{label} · image {k} of {n}",
        "sub.audio": "Turning speech into text (Indonesian)…",
        "sub.doc": "Reading document…",
        "sub.yt": "Getting title and transcript…",
        "sub.web": "Reading web page…",
        "sub.check_pages": "Checking pages…",
        "sub.read_pages": ("Reading {n} page…", "Reading {n} pages…"),
        "sub.docling_start": "Starting the accurate PDF engine…",
        "sub.docling_read": "Reading layout and tables (accurate mode)…",
        "sub.docling_fallback": "The accurate engine couldn't read this file, using the standard reader…",
        "note.docling_fallback": "The accurate PDF engine couldn't read this file, so the standard reader was used.",
        "note.docling_missing": "The accurate PDF engine isn't installed, so the standard reader was used.",
        # ---------- mengunduh mesin PDF teliti ----------
        "dl.offline": "Couldn't download the accurate PDF engine. Check your internet connection and try again.",
        "dl.interrupted": "The download was interrupted. Try again to continue where it stopped.",
        "dl.not_found": "The accurate PDF engine isn't available for download right now. Try again later.",
        "dl.server": "The download server didn't respond properly. Try again later.",
        "dl.disk": "Not enough free disk space. Installing the accurate PDF engine needs about {gb} GB free.",
        "dl.disk_full": "The disk ran out of space while installing. Free up some space and try again.",
        "dl.checksum": "The downloaded file was damaged (checksum mismatch). Please download it again.",
        "dl.extract": "Couldn't unpack the accurate PDF engine. Try downloading it again.",
        "dl.failed": "Couldn't install the accurate PDF engine. Try again.",
        "dl.busy": "The accurate PDF engine is already downloading.",
        "dl.remove_failed": "Couldn't remove the accurate PDF engine. Close Urai App and try again.",
        # ---------- teks yang ditulis ke Markdown ----------
        "md.read_with": "> Read with {label}",
        "md.scan_note": ("> Read with {label} · {k} of {n} page scanned", "> Read with {label} · {k} of {n} pages scanned"),
        "md.page": "Page {n}",
        "md.blank_page": "_(blank page)_",
        "md.scan_pages_head": "Text from scanned pages",
        "md.no_text_read": "_(no readable text)_",
        "md.image_k": "Image {k} ({name})",
        "md.images_head": "Text from images in the document",
        "md.combined_head": ("> Combined from {n} document, created {date} with {app}",
                             "> Combined from {n} documents, created {date} with {app}"),
        "md.combined_empty": "_(no text could be taken)_",
        # ---------- pesan per dokumen ----------
        "msg.empty_scan": "No readable text because this document is a scan.",
        "msg.empty_image": "No readable text because this is an image.",
        "msg.empty_audio": "No speech was recognized in this recording.",
        "msg.empty": "No text could be taken from this file.",
        "msg.no_transcript": "No transcript available. Only the title and description were taken.",
        "log.failed": "Failed: {name}. {msg}",
        "log.saved": "Saved: {path}",
        "log.combined_saved": "Combined file saved: {path}",
        # ---------- jawaban API ----------
        "api.busy_wait": "Wait for the current process to finish.",
        "api.busy": "A process is already running.",
        "api.no_file_dialog": "The file picker isn't available.",
        "api.no_folder_dialog": "The folder picker isn't available.",
        "api.bad_link": "Paste the full link, for example https://youtu.be/…",
        "api.dup_link": "This link is already in the list.",
        "api.list_full": "The list is full ({n} documents).",
        "api.unknown_provider": "Unknown AI provider.",
        "api.url_changed": "The server address changed. Enter the API key again to test it.",
        "api.need_key": "Enter an API key first.",
        "api.need_url": "Enter the server address first (Advanced section).",
        "api.need_model": "Enter the model name first (Advanced section).",
        "api.connected": "Connected to {name}",
        "api.no_items": "Add documents first.",
        "api.ai_needs_key": "AI mode needs an API key. Add it in Settings, or choose Offline mode.",
        "api.not_in_list": "This document isn't in the list.",
        "api.folder_missing": "Folder not found.",
        "api.notices_missing": "THIRD-PARTY-NOTICES.txt wasn't found in the app folder.",
        "api.bad_lang": "Unknown language.",
        "upd.self_built": "This copy was built from source, so it can't check for updates automatically.",
        "upd.failed": "Couldn't check for updates. Check your internet connection.",
        "upd.newer": "Version {v} is available.",
        "upd.latest": "You're using the latest version ({v})",
        # ---------- jendela pilih/simpan file ----------
        "dlg.supported": "Supported documents ({ext})",
        "dlg.all": "All files (*.*)",
        "dlg.md": "Markdown (*.md)",
        "dlg.html": "Interactive HTML (*.html)",
        "dlg.png": "PNG image (*.png)",
        "dlg.pdf": "PDF (*.pdf)",
        # ---------- rangkuman dan mind map ----------
        "mm.ai_needs_key": "AI summary needs an API key. Add it in Settings, or choose Document structure.",
        "mm.read_part": "Reading {name} · part {k} of {n}…",
        "mm.building": "Building the mind map…",
        "mm.reading": "Reading the document…",
        "mm.summarizing": "Summarizing…",
        "mm.summarizing_n": ("Summarizing {n} document…", "Summarizing {n} documents…"),
        "mm.summarizing_k": "Summarizing document {k} of {n}…",
        "mm.merging": "Combining the key points…",
        "mm.no_text_head": "No readable text",
        "mm.no_text_tip": "Turn on scan reading, then try again",
        "mm.no_structure": "No structure could be found",
        "mm.no_points": "Nothing to summarize",
        "sum.ai_needs_key": "Summaries are written by AI and need an API key. Add it in Settings.",
        "sum.need_summary": "Create a summary first in the Summary tab.",
        "sum.writing": "Writing the summary…",
        "sum.no_text": "No readable text to summarize. Turn on scan reading, then try again.",
        "sum.title": "Summary",
        "sum.file_suffix": "summary",
        "export.ai_label": "AI summary, may contain mistakes. Check it against the original document.",
        "export.fit": "Fit to screen",
        "export.made_with": "Made with {app}",
        "export.bad_image": "The mind map image is not valid.",
        # ---------- menyunting hasil ----------
        "edit.no_file": "This document wasn't saved to a file, so there's nothing to update.",
        "edit.no_combined": "There's no combined file to save to.",
        "edit.combined_only": "These results were saved as one combined file. Edit the combined file instead.",
        "edit.write_failed": "Couldn't save the file. Check that its folder still exists and the disk isn't full.",
        "edit.bad_text": "The edited text couldn't be read. Try again.",
        "edit.empty_map": "The mind map is empty.",
        "edit.bad_src": "Unknown mind map source.",
        "edit.reread_conflict": ("You edited this document's part of the combined file. Reading it again would replace "
                                 "your edits, so edit the combined file instead, or convert again."),
        # ---------- error yang mudah dipahami ----------
        "err.auth": "The API key was rejected. Check the API key in Settings.",
        "err.denied": "The AI service denied access. Check the API key and account permissions.",
        "err.model": "The AI provider doesn't recognize this model name. Check the model name in Settings.",
        "err.rate": "The AI service usage limit or quota is used up. Try again later or check your account balance.",
        "err.ai_conn": "Can't connect to the AI service. Check your internet connection.",
        "err.ai_timeout": "The AI service took too long to respond. Try again.",
        "err.ai_bad": "The AI service rejected the request. The model may not read images, or the document is too long.",
        "err.format": "This file format isn't supported.",
        "err.not_found": "File not found. It may have been moved or deleted.",
        "err.permission": "No permission to open or save this file. Close it in other apps, then try again.",
        "err.is_dir": "You picked a folder, not a file.",
        "err.conn": "Can't open the link. Check your internet connection.",
        "err.timeout": "The page took too long to respond. Try again.",
        "err.missing_dep": "A component for this format isn't installed. Please reinstall Urai App.",
        "err.speech": "Speech not recognized. The recording is unclear or has no speech.",
        "err.speech_service": "Can't reach the speech-to-text service. Check your internet, or the recording may be too long.",
        "err.audio_decode": "Can't open the recording. For MP3/M4A, install FFmpeg (see Help).",
        "err.yt_blocked": "YouTube refused requests from this network. Try again later.",
        "err.yt_unavailable": "Video not available. It may be private or deleted.",
        "err.ocr": "The offline scan reader (Tesseract) wasn't found. Please reinstall Urai App.",
        "err.pdf": "Can't open the PDF. The file may be damaged or password-protected.",
        "err.ffmpeg": "MP3/M4A recordings need FFmpeg. See the voice recordings tip in Help.",
        "err.transcript": "This video has no subtitles or transcript that can be taken.",
        "err.password": "This file is password-protected. Unlock it first, then try again.",
        "err.other": "{text}",
    },
    "id": {
        # ---------- aplikasi ----------
        "app.tagline": "Urai dokumen jadi teks Markdown yang rapi",
        "app.broken_ui": "Urai App tidak bisa dibuka karena komponen tampilan rusak. Pasang ulang Urai App.",
        "app.need_webview2": ("Urai App butuh Microsoft Edge WebView2 Runtime untuk menampilkan jendelanya, "
                              "tetapi komponen itu tidak ditemukan di komputer ini.\n\n"
                              "WebView2 gratis dari Microsoft. Buka halaman unduhannya sekarang? "
                              "Setelah terpasang, buka Urai App lagi."),
        "cli.paths": "file atau folder yang langsung dimasukkan ke daftar",
        "cli.dev": "jalankan tampilan di browser (pengembangan)",
        # ---------- jenis file dan keterangan di daftar ----------
        "kind.pdf": "PDF", "kind.doc": "Word", "kind.ppt": "PowerPoint", "kind.xls": "Excel", "kind.csv": "CSV",
        "kind.html": "HTML", "kind.epub": "EPUB", "kind.zip": "ZIP", "kind.msg": "Outlook", "kind.img": "Gambar",
        "kind.aud": "Audio", "kind.text": "Teks", "kind.yt": "Link YouTube", "kind.web": "Link halaman web",
        "kind.file": "File",
        "meta.pages": "{n} halaman",
        "meta.slides": "{n} slide",
        "meta.sheets": "{n} sheet",
        "link.yt_name": "Video YouTube",
        "link.web_name": "Halaman {host}",
        "samples.folder": "contoh",
        "combined.default": "Gabungan",
        # ---------- bahasa OCR ----------
        "lang.ind": "Indonesia", "lang.eng": "Inggris", "lang.jav": "Jawa", "lang.sun": "Sunda", "lang.ara": "Arab",
        "ocr.label_ai": "AI ({name})",
        "ocr.label_offline": "OCR offline ({names})",
        "ocr.failed": "Tesseract gagal: {msg}",
        "ocr.exit_code": "kode {n}",
        "ai.other_name": "Server lain (kompatibel OpenAI)",
        # ---------- kabar proses ----------
        "sub.page": "{label} · halaman {k} dari {n}",
        "sub.image_read": "{label} · membaca gambar…",
        "sub.image_k": "{label} · gambar {k} dari {n}",
        "sub.audio": "Mengubah suara jadi teks (bahasa Indonesia)…",
        "sub.doc": "Membaca dokumen…",
        "sub.yt": "Mengambil judul dan transkrip…",
        "sub.web": "Membaca halaman web…",
        "sub.check_pages": "Memeriksa halaman…",
        "sub.read_pages": "Membaca {n} halaman…",
        "sub.docling_start": "Menyalakan mesin PDF teliti…",
        "sub.docling_read": "Membaca tata letak dan tabel (mode teliti)…",
        "sub.docling_fallback": "Mesin teliti gagal membaca file ini, memakai pembaca biasa…",
        "note.docling_fallback": "Mesin PDF teliti tidak bisa membaca file ini, jadi pembaca biasa yang dipakai.",
        "note.docling_missing": "Mesin PDF teliti belum terpasang, jadi pembaca biasa yang dipakai.",
        # ---------- mengunduh mesin PDF teliti ----------
        "dl.offline": "Mesin PDF teliti tidak bisa diunduh. Periksa koneksi internet, lalu coba lagi.",
        "dl.interrupted": "Unduhan terputus. Coba lagi untuk melanjutkan dari bagian terakhir.",
        "dl.not_found": "Mesin PDF teliti belum tersedia untuk diunduh. Coba lagi nanti.",
        "dl.server": "Server unduhan tidak merespons dengan benar. Coba lagi nanti.",
        "dl.disk": "Ruang disk tidak cukup. Memasang mesin PDF teliti butuh sekitar {gb} GB ruang kosong.",
        "dl.disk_full": "Disk penuh saat memasang. Kosongkan sebagian ruang, lalu coba lagi.",
        "dl.checksum": "File unduhan rusak (checksum tidak cocok). Silakan unduh ulang.",
        "dl.extract": "Mesin PDF teliti tidak bisa dibongkar. Coba unduh ulang.",
        "dl.failed": "Mesin PDF teliti tidak bisa dipasang. Coba lagi.",
        "dl.busy": "Mesin PDF teliti sedang diunduh.",
        "dl.remove_failed": "Mesin PDF teliti tidak bisa dihapus. Tutup Urai App, lalu coba lagi.",
        # ---------- teks yang ditulis ke Markdown ----------
        "md.read_with": "> Dibaca dengan {label}",
        "md.scan_note": "> Dibaca dengan {label} · {k} dari {n} halaman hasil scan",
        "md.page": "Halaman {n}",
        "md.blank_page": "_(halaman kosong)_",
        "md.scan_pages_head": "Teks dari halaman hasil scan",
        "md.no_text_read": "_(tidak ada teks terbaca)_",
        "md.image_k": "Gambar {k} ({name})",
        "md.images_head": "Teks dari gambar di dalam dokumen",
        "md.combined_head": "> Gabungan dari {n} dokumen, dibuat {date} dengan {app}",
        "md.combined_empty": "_(tidak ada teks yang bisa diambil)_",
        # ---------- pesan per dokumen ----------
        "msg.empty_scan": "Tidak ada teks terbaca karena dokumen ini hasil scan.",
        "msg.empty_image": "Tidak ada teks terbaca karena ini gambar.",
        "msg.empty_audio": "Tidak ada ucapan yang dikenali di rekaman ini.",
        "msg.empty": "Tidak ada teks yang bisa diambil dari file ini.",
        "msg.no_transcript": "Transkrip tidak tersedia. Hanya judul dan deskripsi yang diambil.",
        "log.failed": "Gagal: {name}. {msg}",
        "log.saved": "Tersimpan: {path}",
        "log.combined_saved": "File gabungan tersimpan: {path}",
        # ---------- jawaban API ----------
        "api.busy_wait": "Tunggu proses selesai dulu.",
        "api.busy": "Proses sedang berjalan.",
        "api.no_file_dialog": "Jendela pilih file tidak tersedia.",
        "api.no_folder_dialog": "Jendela pilih folder tidak tersedia.",
        "api.bad_link": "Tempel link yang lengkap, misalnya https://youtu.be/…",
        "api.dup_link": "Link ini sudah ada di daftar.",
        "api.list_full": "Daftar sudah penuh ({n} dokumen).",
        "api.unknown_provider": "Penyedia AI tidak dikenal.",
        "api.url_changed": "Alamat server berubah. Isi API key lagi untuk mengetesnya.",
        "api.need_key": "Isi API key dulu.",
        "api.need_url": "Isi alamat server dulu (bagian Lanjutan).",
        "api.need_model": "Isi nama model dulu (bagian Lanjutan).",
        "api.connected": "Terhubung ke {name}",
        "api.no_items": "Tambahkan dokumen dulu.",
        "api.ai_needs_key": "Mode AI butuh API key. Isi di Pengaturan, atau pilih mode Offline.",
        "api.not_in_list": "Dokumen tidak ada di daftar.",
        "api.folder_missing": "Folder tidak ditemukan.",
        "api.notices_missing": "File THIRD-PARTY-NOTICES.txt tidak ditemukan di folder aplikasi.",
        "api.bad_lang": "Bahasa tidak dikenal.",
        "upd.self_built": "Versi ini dirakit sendiri, jadi tidak bisa cek pembaruan otomatis.",
        "upd.failed": "Tidak bisa memeriksa pembaruan. Periksa koneksi internet.",
        "upd.newer": "Versi {v} tersedia.",
        "upd.latest": "Anda memakai versi terbaru ({v})",
        # ---------- jendela pilih/simpan file ----------
        "dlg.supported": "Dokumen yang didukung ({ext})",
        "dlg.all": "Semua file (*.*)",
        "dlg.md": "Markdown (*.md)",
        "dlg.html": "HTML interaktif (*.html)",
        "dlg.png": "Gambar PNG (*.png)",
        "dlg.pdf": "PDF (*.pdf)",
        # ---------- rangkuman dan mind map ----------
        "mm.ai_needs_key": "Rangkuman AI butuh API key. Isi di Pengaturan, atau pilih Struktur dokumen.",
        "mm.read_part": "Membaca {name} · bagian {k} dari {n}…",
        "mm.building": "Menyusun mind map…",
        "mm.reading": "Membaca isi dokumen…",
        "mm.summarizing": "Meringkas…",
        "mm.summarizing_n": "Meringkas {n} dokumen…",
        "mm.summarizing_k": "Meringkas dokumen {k} dari {n}…",
        "mm.merging": "Menggabungkan poin penting…",
        "mm.no_text_head": "Tidak ada teks terbaca",
        "mm.no_text_tip": "Aktifkan baca scan, lalu ulangi",
        "mm.no_structure": "Tidak ada struktur yang bisa diambil",
        "mm.no_points": "Tidak ada poin yang bisa dirangkum",
        "sum.ai_needs_key": "Ringkasan ditulis oleh AI dan butuh API key. Isi di Pengaturan.",
        "sum.need_summary": "Buat ringkasan dulu di tab Ringkasan.",
        "sum.writing": "Menulis ringkasan…",
        "sum.no_text": "Tidak ada teks terbaca untuk diringkas. Aktifkan baca scan, lalu ulangi.",
        "sum.title": "Ringkasan",
        "sum.file_suffix": "ringkasan",
        "export.ai_label": "Rangkuman AI, bisa keliru. Periksa kembali dengan dokumen asli.",
        "export.fit": "Pas di layar",
        "export.made_with": "Dibuat dengan {app}",
        "export.bad_image": "Gambar mind map tidak valid.",
        # ---------- menyunting hasil ----------
        "edit.no_file": "Dokumen ini tidak disimpan ke file, jadi tidak ada yang bisa diperbarui.",
        "edit.no_combined": "Belum ada file gabungan untuk disimpan.",
        "edit.combined_only": "Hasil ini disimpan sebagai satu file gabungan. Sunting file gabungannya saja.",
        "edit.write_failed": "File tidak bisa disimpan. Pastikan foldernya masih ada dan disk tidak penuh.",
        "edit.bad_text": "Teks suntingan tidak terbaca. Coba lagi.",
        "edit.empty_map": "Mind map kosong.",
        "edit.bad_src": "Sumber mind map tidak dikenal.",
        "edit.reread_conflict": ("Anda sudah menyunting bagian dokumen ini di file gabungan. Membacanya ulang akan menimpa "
                                 "suntingan itu, jadi sunting file gabungannya, atau ubah ulang dari awal."),
        # ---------- error yang mudah dipahami ----------
        "err.auth": "API key ditolak. Periksa API key di Pengaturan.",
        "err.denied": "Akses ditolak oleh layanan AI. Periksa API key dan izin akun.",
        "err.model": "Nama model tidak dikenali penyedia AI. Periksa nama model di Pengaturan.",
        "err.rate": "Batas pemakaian atau kuota layanan AI habis. Coba lagi nanti atau cek saldo akun.",
        "err.ai_conn": "Tidak bisa terhubung ke layanan AI. Periksa koneksi internet.",
        "err.ai_timeout": "Layanan AI terlalu lama merespons. Coba lagi.",
        "err.ai_bad": "Permintaan ditolak layanan AI. Model mungkin tidak bisa membaca gambar atau dokumen terlalu panjang.",
        "err.format": "Format file ini tidak didukung.",
        "err.not_found": "File tidak ditemukan. Mungkin sudah dipindah atau dihapus.",
        "err.permission": "Tidak punya izin membuka atau menyimpan file ini. Tutup file itu di aplikasi lain, lalu coba lagi.",
        "err.is_dir": "Yang dipilih adalah folder, bukan file.",
        "err.conn": "Tidak bisa membuka link. Periksa koneksi internet.",
        "err.timeout": "Halaman terlalu lama merespons. Coba lagi.",
        "err.missing_dep": "Komponen untuk format ini belum terpasang. Pasang ulang Urai App.",
        "err.speech": "Suara tidak dikenali. Rekaman kurang jelas atau tidak ada ucapan.",
        "err.speech_service": "Layanan pengubah suara ke teks tidak bisa dihubungi. Periksa internet, atau rekaman terlalu panjang.",
        "err.audio_decode": "Rekaman tidak bisa dibuka. Untuk MP3/M4A, pasang FFmpeg (lihat Panduan).",
        "err.yt_blocked": "YouTube menolak permintaan dari jaringan ini. Coba lagi nanti.",
        "err.yt_unavailable": "Video tidak tersedia. Mungkin privat atau sudah dihapus.",
        "err.ocr": "Mesin baca scan offline (Tesseract) tidak ditemukan. Pasang ulang Urai App.",
        "err.pdf": "PDF tidak bisa dibuka. File mungkin rusak atau dikunci kata sandi.",
        "err.ffmpeg": "Rekaman MP3/M4A butuh FFmpeg. Lihat Panduan bagian rekaman suara.",
        "err.transcript": "Video ini tidak punya subtitle atau transkrip yang bisa diambil.",
        "err.password": "File ini dikunci kata sandi. Buka kuncinya dulu, lalu coba lagi.",
        "err.other": "{text}",
    },
}

_lang = DEFAULT
_ID_NUM = str.maketrans(",.", ".,")


def set_lang(lang: str) -> str:
    """Ganti bahasa aktif. Nilai yang tidak dikenal kembali ke bawaan (English)."""
    global _lang
    _lang = lang if lang in STRINGS else DEFAULT
    return _lang


def get_lang() -> str:
    return _lang


def has(key: str) -> bool:
    return key in STRINGS[DEFAULT]


def variants(key: str) -> list[str]:
    """Teks kunci ini dalam semua bahasa (untuk mengenali teks yang ditulis saat bahasa lain aktif)."""
    out: list[str] = []
    for lang in LANGS:
        val = STRINGS[lang][key]
        for form in val if isinstance(val, tuple) else (val,):
            if form not in out:
                out.append(form)
    return out


def fmt_num(x: float, digits: int = 0) -> str:
    """Bilangan dengan pemisah sesuai bahasa: 1,240.5 (en) atau 1.240,5 (id)."""
    s = f"{x:,.{digits}f}"
    return s.translate(_ID_NUM) if _lang == "id" else s


def fmt_date(dt: datetime, with_time: bool = False) -> str:
    """Tanggal untuk teks hasil: 2026-10-31 09:05 (en) atau 31-10-2026 09.05 (id)."""
    fmt = {"en": ("%Y-%m-%d", "%Y-%m-%d %H:%M"), "id": ("%d-%m-%Y", "%d-%m-%Y %H.%M")}[_lang][with_time]
    return dt.strftime(fmt)


def t(key: str, **kw) -> str:
    """Teks untuk kunci ini dalam bahasa aktif. Kunci yang tidak ada dikembalikan apa adanya."""
    val = STRINGS[_lang].get(key)
    if val is None:
        val = STRINGS[DEFAULT].get(key, key)
    if isinstance(val, tuple):
        val = val[0] if kw.get("n") == 1 else val[1]
    if not kw:
        return val
    return val.format(**{k: _fmt_arg(v) for k, v in kw.items()})


def _fmt_arg(v):
    """Bilangan bulat diberi pemisah ribuan, pecahan satu angka desimal, sesuai bahasa aktif."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return fmt_num(v)
    if isinstance(v, float):
        return fmt_num(v, 1)
    return v
