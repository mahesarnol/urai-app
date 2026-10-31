# Panduan Urai App

[English](GUIDE.md) · **Bahasa Indonesia**

Urai App mengubah dokumen menjadi teks Markdown (`.md`): format teks sederhana yang mudah dibaca manusia dan asisten AI. File `.md` bisa dibuka dengan Notepad, dan jauh lebih kecil daripada PDF atau PowerPoint aslinya.

## 1. Tambahkan dokumen

- **Tarik** file atau folder dari File Explorer ke mana saja di jendela Urai App. Lapisan biru muncul saat file berada di atas jendela; lepaskan untuk menambahkan.
- Atau tekan **File** (pilih beberapa file sekaligus dengan Ctrl atau Shift) dan **Folder** (semua file yang didukung di folder itu dan subfoldernya ikut ditambahkan; file `.md` dilewati supaya hasil lama tidak ikut terbaca lagi).
- **Link**: tempel link YouTube atau halaman web di kolom paling bawah, lalu tekan Enter. Bisa juga menarik link dari browser ke jendela Urai App.
- **Kirim ke**: di File Explorer, klik kanan file, pilih **Kirim ke › Urai App** (di Windows 11: **Tampilkan opsi lainnya › Kirim ke**).
- Baru pertama kali? Tekan **Coba dengan file contoh** untuk melihat cara kerjanya dengan enam file contoh.

Format yang didukung: PDF, Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`, `.xls`), CSV, gambar (JPG, PNG, WEBP, BMP, TIFF), audio (WAV, MP3, M4A, MP4), EPUB, ZIP, HTML, Outlook (`.msg`), dan teks (TXT, JSON, XML).

Setiap baris di daftar menampilkan jenis file, jumlah halaman, slide, atau sheet, dan ukurannya. PDF yang ternyata hasil scan (tidak ada teks yang bisa dipilih) diberi label **Hasil scan**. Untuk menghapus satu dokumen dari daftar, arahkan kursor ke barisnya lalu tekan tanda ×.

## 2. Atur hasil

### Bentuk hasil

- **Satu file per dokumen**: setiap dokumen menjadi satu file `.md` dengan nama yang sama. Bila nama itu sudah ada, file baru diberi nomor, misalnya `Laporan (2).md`. File lama tidak pernah ditimpa.
- **Gabung jadi satu**: semua dokumen digabung menjadi satu file dengan nama pilihan Anda. Isinya diurutkan sesuai daftar; seret pegangan titik-titik di kiri baris untuk memindahkan, atau pilih pegangan lalu tekan panah atas/bawah. Di awal file ada daftar isi kecil berisi nama semua dokumen.

### Baca gambar & hasil scan

| Mode | Cocok untuk | Catatan |
| --- | --- | --- |
| **Mati** | Dokumen digital biasa | Gambar dan PDF hasil scan dilewati. |
| **Offline** | Hampir semua kebutuhan | Gratis, tanpa internet, dokumen tidak keluar dari komputer. Berjalan di prosesor. |
| **AI** | Scan buram, tulisan tangan, grafik | Lebih akurat dan bisa menjelaskan isi grafik. Berbayar sesuai pemakaian di akun AI Anda. |

Tekan **Atur** (atau **Pengaturan** di kanan atas) untuk memilih:

- **Bahasa di dokumen** (mode Offline): Indonesia, Inggris, Jawa, Sunda, Arab. Pilih hanya bahasa yang memang ada; makin sedikit, makin cepat dan tepat.
- **Ketelitian**: *Cepat* untuk scan yang bersih, *Teliti* untuk scan buram atau foto dari HP (sekitar dua kali lebih lama).
- **Baca juga gambar di dalam Word, PowerPoint, dan Excel**: misalnya grafik atau tabel yang ditempel sebagai gambar. Teksnya ditambahkan di akhir hasil dokumen itu.

### Memakai mode AI

1. Buka **Pengaturan › AI (berbayar)**.
2. Pilih penyedia, lalu tekan **Buka halaman pembuatan API key** untuk membuat API key di situs penyedia tersebut.
3. Tempel API key, tekan **Tes koneksi**, lalu **Simpan & pakai mode ini**.

API key disimpan di Windows Credential Manager, bukan di file biasa. Nama model bisa diganti di bagian **Lanjutan**; untuk membaca gambar, model harus mendukung gambar. Untuk penyedia **Lainnya**, isi alamat server yang kompatibel dengan API OpenAI (misalnya server lokal) dan nama modelnya.

Untuk dokumen rahasia atau data responden, pakai mode **Offline**.

### Simpan ke

Hasil disimpan di `Dokumen\Urai App` kecuali Anda memilih folder lain lewat **Ubah**, atau mencentang **Simpan di folder yang sama dengan file asli**. Bila folder tujuan tidak bisa ditulisi (misalnya flashdisk yang dikunci), hasil otomatis disimpan di `Dokumen\Urai App`.

## 3. Ubah dan lihat hasil

Tekan tombol biru atau **Ctrl + Enter**. Selama proses berjalan, terlihat persentase, dokumen yang sedang dikerjakan, dan halaman ke berapa saat membaca scan. Tekan **Batalkan** untuk berhenti; dokumen yang sudah selesai tetap tersimpan.

Setelah selesai:

- **Buka file ini** / **Buka file**: membuka file `.md` dengan aplikasi bawaan Windows.
- **Buka folder**: membuka folder hasil di File Explorer.
- **Salin teks**: menyalin isi Markdown ke clipboard, siap ditempel ke ChatGPT atau aplikasi lain.
- Klik baris di daftar untuk melihat hasil dokumen itu. Tab **Tampilan** menampilkan judul, daftar, dan tabel dengan rapi; tab **Teks Markdown** menampilkan isi file apa adanya.
- Penanda **Ukuran** menunjukkan jumlah kata. Di atas sekitar 60.000 kata, sebagian asisten AI mulai kesulitan; pertimbangkan menyimpan terpisah.

Baris berwarna kuning (**Perlu dicek**) menjelaskan masalahnya di baris itu sendiri. Misalnya PDF hasil scan saat mode Mati; tekan **Aktifkan baca scan offline** untuk membacanya ulang tanpa mengulang semuanya. Baris merah (**Gagal**) menyebut penyebabnya, misalnya file dikunci kata sandi.

**Ubah dokumen lain** mengosongkan daftar. **Ubah pengaturan, ulangi** kembali ke langkah 2 dengan daftar yang sama.

## 4. Mind map

Buka tab **Mind map** di panel hasil (atau tombol **Mind map**).

1. Pilih sumber rangkuman:
   - **Struktur dokumen**: gratis dan offline. Cabang diambil dari judul, subjudul, daftar, dan tabel di dokumen. Hasil terbaik untuk Word dan PowerPoint yang memakai gaya judul.
   - **Rangkuman AI**: lebih ringkas dan bisa menggabungkan beberapa dokumen. Pilih jenisnya: **Umum** (poin utama), **Notulen** (masalah, keputusan, tindak lanjut), atau **Laporan** (temuan, aktor, rekomendasi). Seluruh teks dokumen dikirim ke penyedia AI; jumlah katanya ditampilkan sebelum Anda menekan tombol. Dokumen yang sangat panjang diringkas bertahap.
2. Tekan **Buat mind map** atau **Buat rangkuman AI**.
3. Di mind map: geser dengan menyeret, perbesar dengan roda mouse atau tombol + dan −, klik lingkaran pada cabang untuk melipat atau membukanya. **Pas** mengembalikan ke ukuran layar, **Lipat** menampilkan cabang utama saja, **Layar penuh** untuk presentasi, **Teks** menampilkan rangkuman sebagai daftar.

Cakupan mind map mengikuti baris yang dipilih. Pada hasil gabungan, pilih **Lihat semua** untuk merangkum seluruh dokumen sekaligus.

### Gaya

Tekan **Gaya** untuk mengatur:

- **Tema warna**: Pelangi, Urai, Lembut, atau Monokrom.
- **Cara mewarnai**: *Per cabang* (setiap cabang punya warna sendiri) atau *Per sub* (satu warna untuk setiap tingkat).
- **Warna cabang dibedakan sampai**: sub di bawah tingkat yang dipilih ikut warna cabang induknya.
- **Warna dan tebal garis tiap sub**, **lebar teks maksimal**, **jarak antar sub**, dan **tampilkan sampai** sub ke berapa.

Gaya terakhir diingat untuk mind map berikutnya. **Kembalikan ke bawaan** untuk mengulang.

### Simpan

Tekan **Simpan** lalu pilih:

- **PDF (siap cetak)**: kertas A4, A3, atau F4 (folio), mendatar atau tegak. Bisa menyertakan judul dan tanggal, label "Rangkuman AI, periksa kembali", dan halaman tambahan berisi rangkuman dalam bentuk teks. Mind map otomatis disesuaikan agar muat satu halaman; untuk mind map besar, pilih A3.
- **Gambar PNG**: untuk presentasi atau media sosial.
- **HTML interaktif**: satu file yang bisa dibuka di browser mana pun, tetap bisa dilipat dan digeser, tanpa internet.
- **Markdown (.md)**: kerangka rangkuman sebagai teks.

Rangkuman AI bisa keliru. Selalu periksa kembali dengan dokumen asli sebelum dipakai.

## 5. Fitur eksperimental

Keduanya bergantung pada layanan pihak ketiga yang bisa berubah sewaktu-waktu.

- **Link YouTube**: mengambil judul, deskripsi, dan transkrip. Hanya untuk video yang punya subtitle atau transkrip otomatis; bahasa Indonesia diambil lebih dulu, lalu bahasa Inggris. Bila YouTube menolak permintaan dari jaringan Anda, coba lagi nanti.
- **Rekaman suara**: diubah jadi teks dalam bahasa Indonesia lewat layanan pengenal suara Google, jadi butuh internet dan rekaman dikirim ke Google. File WAV bisa langsung dipakai. File MP3, M4A, dan MP4 butuh [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) terpasang dan tercantum di PATH Windows. Rekaman yang panjang bisa ditolak layanan; potong menjadi bagian beberapa menit.

## 6. Masalah yang sering terjadi

| Masalah | Penyebab dan jalan keluar |
| --- | --- |
| Jendela kosong atau Urai App tidak mau terbuka | Microsoft Edge WebView2 Runtime belum terpasang. Unduh gratis dari situs Microsoft, pasang, lalu buka lagi. |
| "Windows melindungi PC Anda" saat memasang | Installer belum ditandatangani. Tekan **Info selengkapnya › Tetap jalankan** bila file berasal dari halaman resmi. |
| PDF hasil scan kosong | Mode baca scan sedang Mati. Pilih Offline, atau tekan **Aktifkan baca scan offline** di barisnya. |
| Hasil OCR banyak salah huruf | Pilih Ketelitian **Teliti**, pastikan bahasa yang dipilih sesuai, atau pakai mode AI. |
| "API key ditolak" | API key salah atau sudah dicabut. Buat API key baru di situs penyedia, lalu tempel ulang. |
| "Batas pemakaian atau kuota habis" | Saldo atau kuota akun AI habis. Isi saldo, tunggu, atau pakai mode Offline. |
| File tidak bisa disimpan | File dengan nama sama sedang terbuka di aplikasi lain, atau folder tidak bisa ditulisi. Hasil otomatis disimpan ke `Dokumen\Urai App`. |

Masih bermasalah? Kirim email ke maheswara.as@gmail.com beserta file `%APPDATA%\UraiApp\logs\urai.log`. File catatan itu berisi nama file dan pesan error, bukan isi dokumen Anda.
