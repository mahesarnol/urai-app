qris.png di folder ini adalah kode QR dukungan (QRIS GoPay Merchant) yang tampil di jendela Dukung.

Mengganti QRIS:
- Unduh poster QRIS dari aplikasi GoPay Merchant (menu QRIS > Unduh/Simpan QRIS).
- Potong kotak kode QR-nya saja, beri margin putih di sekelilingnya, simpan sebagai qris.png di folder ini.
- Isi SUPPORT_MERCHANT di src/urai/info.py dengan nama merchant yang tersimpan di dalam QR. Nama itulah
  yang tampil di aplikasi pembayaran; QRIS memotongnya menjadi 25 karakter, jadi bisa berbeda dari poster.
- Rakit ulang aplikasinya.

Bila file ini tidak ada, jendela Dukung menampilkan tempat QRIS dengan tulisan "QRIS resmi menyusul",
dan ajakan dukungan di panel hasil tidak ditampilkan.
