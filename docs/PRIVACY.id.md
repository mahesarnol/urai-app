# Kebijakan Privasi Urai App

[English](PRIVACY.md) · **Bahasa Indonesia**

> **Draf, terakhir diperbarui 31 Oktober 2026.** Perlu ditinjau pengembang sebelum dipublikasikan.

Urai App adalah aplikasi Windows gratis dan open source yang mengubah dokumen menjadi teks Markdown di komputer Anda sendiri. Kebijakan ini menjelaskan apa yang terjadi pada data Anda saat memakainya.

## Ringkasnya

- Urai App **tidak punya server, tidak memakai akun, tidak memakai analitik atau pelacakan, dan tidak menampilkan iklan**. Pengembang tidak menerima dokumen, hasil, pengaturan, maupun data pemakaian Anda.
- Dokumen Anda diproses **di komputer Anda**. Dokumen hanya keluar bila Anda memakai salah satu fitur di bagian [Saat data keluar dari komputer](#saat-data-keluar-dari-komputer), dan hanya ke layanan yang dibutuhkan fitur itu.

## Yang tetap di komputer Anda

| Data | Tempat penyimpanan | Keterangan |
| --- | --- | --- |
| Dokumen Anda dan hasil `.md` | Tempat dokumen itu berada, dan folder hasil pilihan Anda (bawaan: `Dokumen\Urai App`) | Urai App tidak pernah menghapus atau mengunggah file asli Anda. |
| Pengaturan (bahasa, tema, bentuk hasil, penyedia dan model AI pilihan) | `%APPDATA%\UraiApp\settings.json` | File teks biasa di komputer Anda. |
| API key penyedia AI | Windows Credential Manager | Hanya bila Credential Manager tidak tersedia, API key disimpan di `%APPDATA%\UraiApp\keys.json` yang hanya bisa dibaca akun Windows Anda. |
| File catatan (log) | `%APPDATA%\UraiApp\logs\urai.log` (paling besar sekitar 4 MB, catatan lama terhapus otomatis) | Berisi nama file, lokasi folder, dan pesan error untuk membantu mengatasi masalah. Tidak berisi isi dokumen Anda. |
| Mesin PDF akurat (hanya bila Anda mengunduhnya) | `%LOCALAPPDATA%\UraiApp\engines` | File program dan model AI yang berjalan di komputer Anda. Hapus lewat **Pengaturan › Baca offline**. |
| Gambar sementara untuk OCR offline | Folder sementara Windows | Langsung dihapus setelah setiap halaman dibaca. |

## Saat data keluar dari komputer

Data hanya dikirim bila **Anda** memakai salah satu fitur berikut:

| Fitur | Yang dikirim | Dikirim ke |
| --- | --- | --- |
| **Mode AI** (membaca scan dan gambar dengan AI) | Gambar halaman atau gambar yang sedang dibaca, dan API key Anda | Penyedia AI pilihan Anda (misalnya Anthropic, Google, DeepSeek, OpenAI, OpenRouter, atau alamat server yang Anda isi) |
| Tab **Ringkasan**, dan mind map **Rangkuman AI** | Teks dokumen yang dipilih, dan API key Anda | Penyedia AI pilihan Anda |
| **Tes koneksi** di pengaturan AI | Satu gambar uji yang sangat kecil dan API key Anda | Penyedia AI pilihan Anda |
| **Link YouTube dan halaman web** | Permintaan biasa untuk halaman atau transkrip video itu | Situsnya sendiri (misalnya YouTube) |
| **Rekaman suara** (eksperimental) | Rekaman suaranya | Layanan pengenal suara Google |
| **Mengunduh mesin PDF akurat** (hanya bila Anda memilihnya) | Permintaan unduhan biasa | GitHub (halaman Releases proyek ini) |
| **Cek pembaruan** (hanya saat tombolnya ditekan) | Permintaan nomor versi terbaru | GitHub (`api.github.com`) |
| Tautan ke halaman penyedia, kode sumber, atau unduhan | Dibuka di browser biasa Anda | Situs yang Anda buka |

Layanan-layanan itu mengolah data Anda menurut kebijakan privasi dan ketentuannya sendiri, yang tidak dikendalikan pengembang. Seperti situs web pada umumnya, mereka bisa melihat alamat IP Anda. Biaya pemakaian AI ditagihkan ke akun Anda sendiri di penyedia tersebut. **Untuk dokumen rahasia atau data pribadi, pakai mode Offline dan mind map Struktur dokumen yang gratis**, karena keduanya tidak mengirim apa pun.

Jendela aplikasi ditampilkan dengan Microsoft Edge WebView2, komponen Windows buatan Microsoft. Data diagnostiknya, bila ada, mengikuti pengaturan privasi Windows Anda dan pernyataan privasi Microsoft.

## Mendukung pengembang

Dukungan dibayar lewat QRIS yang dipindai dari aplikasi bank atau dompet digital Anda sendiri. Pembayaran sepenuhnya diproses oleh bank atau dompet digital Anda dan GoPay; Urai App tidak menerima informasi pembayaran apa pun. Tombol **Sudah mendukung** hanya menyimpan catatan di komputer Anda supaya ajakan dukungan tidak muncul lagi.

## Melaporkan masalah

Bila Anda melaporkan masalah lewat GitHub Issues, semua yang Anda tulis di sana bersifat **publik**. Sebelum melampirkan file catatan, periksa dulu dan hapus nama file atau lokasi folder yang tidak ingin Anda bagikan.

## Pilihan Anda

- Hapus API key tersimpan di **Pengaturan › AI**.
- Hapus folder `%APPDATA%\UraiApp` untuk menghapus semua pengaturan, API key di `keys.json`, dan file catatan. API key di Windows Credential Manager bisa dihapus dari aplikasi atau dari **Credential Manager** Windows (entri bernama `UraiApp`).
- Copot aplikasi lewat **Pengaturan › Aplikasi › Aplikasi terinstal** di Windows. Dokumen dan hasil Anda tidak ikut terhapus.

## Perubahan kebijakan

Bila cara Urai App menangani data berubah, kebijakan ini diperbarui di repositori proyek dengan tanggal baru di bagian atas.

## Kontak

Pertanyaan tentang kebijakan ini: buka issue di <https://github.com/mahesarnol/urai-app/issues>.
