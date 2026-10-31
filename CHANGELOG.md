# Catatan perubahan

## 3.0.0 (2026)

Versi pertama dengan nama Urai App. Sebelumnya bernama "MarkItDown untuk Windows" (versi 1 dan 2, berbasis Tkinter).

- Tampilan baru berbasis web di dalam jendela aplikasi (pywebview + WebView2), mengikuti tema terang/gelap Windows.
- Tarik-lepas file dan folder, menu **Kirim ke**, urutan daftar bisa diseret.
- Hasil satu file per dokumen atau digabung jadi satu.
- Baca scan offline dengan Tesseract OCR yang ikut terpasang (ind, eng, jav, sun, ara); halaman PDF dirender dengan pypdfium2. PyMuPDF (AGPL) tidak lagi dipakai.
- Deteksi PDF hasil scan dan PDF campuran; teks dari gambar di dalam Word, PowerPoint, dan Excel.
- Mode AI untuk Claude, Gemini, DeepSeek, OpenAI, OpenRouter, dan server kompatibel OpenAI; API key di Windows Credential Manager.
- Mind map (markmap, offline): struktur dokumen atau rangkuman AI bertahap untuk dokumen panjang; gaya per sub; simpan sebagai PDF, PNG, HTML, Markdown.
- Halaman Tentang, Panduan, dan Dukung (QRIS GoPay Merchant).
- Installer per pengguna (Inno Setup) dan versi portable, dirakit otomatis di GitHub Actions dengan uji mandiri.
