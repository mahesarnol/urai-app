# Mengunggah ke GitHub dan merakit installer

[English](BUILDING.md) · **Bahasa Indonesia**

Panduan ini untuk pemilik repo. Installer Windows dirakit oleh GitHub Actions, jadi Anda tidak perlu memasang Python atau alat apa pun di komputer sendiri.

## 1. Buat repo dan unggah

1. Masuk ke GitHub, tekan **New repository**. Nama yang disarankan: `urai-app`. Pilih **Public** (Actions gratis tanpa batas untuk repo publik). Jangan centang README atau lisensi, karena sudah ada di sini.
2. Unggah isi folder ini. Cara termudah tanpa perintah: di halaman repo yang masih kosong, pilih **uploading an existing file**, lalu tarik semua file dan folder (termasuk folder `.github`). Bila folder `.github` tidak ikut karena tersembunyi, buat manual: **Add file › Create new file**, ketik `.github/workflows/build.yml`, lalu tempel isinya.

   Dengan Git:

   ```bash
   git init
   git add .
   git commit -m "Urai App 3.0.0"
   git branch -M main
   git remote add origin https://github.com/NAMA-ANDA/urai-app.git
   git push -u origin main
   ```

3. Buka tab **Actions**. Alur **Build** berjalan otomatis (sekitar 15–25 menit). Bila diminta, tekan **I understand my workflows, go ahead and enable them**.

## 2. Ambil hasil rakitan uji

Setelah centang hijau muncul, buka hasil alur itu, lalu di bagian **Artifacts** unduh `UraiApp-3.0.0-windows`. Isinya:

- `UraiApp-3.0.0-Setup.exe`: installer
- `UraiApp-3.0.0-portable.zip`: versi tanpa pasang
- `SHA256SUMS.txt`: sidik jari file untuk memastikan file tidak diubah orang lain

Cobalah installer ini dulu di komputer Anda sebelum dirilis.

## 3. Rilis resmi

Buat tag versi, lalu dorong:

```bash
git tag v3.0.0
git push origin v3.0.0
```

Tanpa Git: tab **Releases › Draft a new release › Choose a tag**, ketik `v3.0.0`, pilih **Create new tag**, lalu **Publish release**. Alur Build akan berjalan untuk tag itu dan menempelkan installer ke rilis tersebut.

Catatan rilis diambil dari [RELEASE_NOTES.md](RELEASE_NOTES.md) (berbahasa Inggris). Untuk versi berikutnya, naikkan `version` di `pyproject.toml` dan `__version__` di `src/urai/__init__.py`, tambahkan catatan di `CHANGELOG.md` dan `docs/RELEASE_NOTES.md`, lalu buat tag yang sama dengan versinya (mis. `v3.0.1`). Alur akan gagal bila tag dan versi tidak sama.

## 4. Google Drive

Unggah `UraiApp-3.0.0-Setup.exe` dan `SHA256SUMS.txt` dari halaman Releases ke folder Google Drive, lalu bagikan dengan akses **Siapa saja yang memiliki link: Pengakses lihat**. Google Drive kadang menampilkan peringatan "tidak dapat memindai virus" untuk file besar; itu normal.

## 5. Sebelum rilis publik

- **QRIS**: kode QR dukungan ada di `src/urai/web/img/qris.png` (hanya kotak QR, dengan margin putih). Untuk menggantinya, potong kotak QR saja dari poster GoPay Merchant yang baru, lalu isi `SUPPORT_MERCHANT` di `src/urai/info.py` dengan nama merchant yang tersimpan di dalam QR (nama itulah yang tampil di aplikasi pembayaran; QRIS memotongnya menjadi 25 karakter, jadi bisa berbeda dari poster). Tanpa gambar ini, jendela Dukung menampilkan tempat kosong bertuliskan "QRIS resmi menyusul".
- **Syarat Penggunaan dan Kebijakan Privasi**: drafnya ada di [TERMS.id.md](TERMS.id.md) dan [PRIVACY.id.md](PRIVACY.id.md) (beserta versi bahasa Inggris). Tinjau, putuskan bagian bertanda **[perlu diputuskan]**, lalu tautkan dari README.
- **Ikon**: `packaging/urai.ico` masih ikon polos sementara (huruf U). Ganti dengan logo setelah nama aman didaftarkan.
- **Peringatan SmartScreen**: installer yang belum ditandatangani akan memunculkan peringatan "Windows melindungi PC Anda" sampai cukup banyak orang mengunduhnya. Untuk menghilangkannya perlu sertifikat code signing (berbayar). Untuk proyek open source, [SignPath Foundation](https://signpath.org) menyediakan tanda tangan gratis.

## 6. Mesin PDF akurat (Docling)

Mesin Docling yang opsional dirakit terpisah dari aplikasi, karena ukurannya besar (sekitar 0,8 GB setelah dikompres) dan jarang berubah. Alur [docling-engine.yml](../.github/workflows/docling-engine.yml) merakitnya saat tag `docling-engine-v*` didorong, mengujinya pada satu PDF contoh, lalu menempelkan `UraiDocling-1-windows-x64.zip` dan `SHA256SUMS.txt` ke rilis itu. Aplikasi mengunduhnya dari rilis `docling-engine-v1` dan memeriksa SHA-256-nya sebelum memasang.

Pertama kali:

```bash
git tag docling-engine-v1
git push origin docling-engine-v1
```

Rakit ulang hanya bila pekerja (`packaging/docling/worker.py`) atau versi Docling (`DOCLING_VERSION` di `packaging/docling/build_engine.py`) berubah. Untuk perubahan yang tidak bisa dipakai aplikasi versi lama, naikkan `ENGINE_VERSION` di `worker.py` dan `ENGINE` di `src/urai/docling_engine.py`, perbarui nama file di alur itu, lalu dorong tag baru (misalnya `docling-engine-v2`).

Merakit di komputer sendiri: `python packaging/docling/build_engine.py --out build/docling --zip dist/UraiDocling-1-windows-x64.zip` (butuh [uv](https://docs.astral.sh/uv/) dan ruang kosong sekitar 2,5 GB). Simpan hasilnya di luar OneDrive atau folder lain yang disinkronkan.

## Merakit di komputer sendiri (opsional)

Di Windows 10/11 dengan Python 3.12, Inno Setup 6, dan Tesseract (dari Chocolatey atau installer UB Mannheim):

```powershell
pip install -r requirements-dev.txt
python packaging\write_build_info.py
.\packaging\fetch_tesseract.ps1 -Out build\tesseract
python packaging\gen_notices.py
pyinstaller packaging\urai.spec --noconfirm --clean
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=3.0.0 packaging\installer.iss
```

Hasilnya ada di folder `dist`. Uji tanpa jendela: `"dist\Urai App\Urai App.exe" --selftest build\selftest` lalu lihat `build\selftest\selftest.json`.
