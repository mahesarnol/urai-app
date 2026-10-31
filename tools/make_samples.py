"""Buat file contoh untuk tombol "Coba dengan file contoh".

Semua isi fiktif (Desa Sukamaju). Jalankan dari akar repo:
    python tools/make_samples.py
Membutuhkan python-docx, python-pptx, openpyxl, Pillow, dan LibreOffice (soffice) untuk PDF teks.
"""
from __future__ import annotations

import io
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import docx
import openpyxl
import pptx
from pptx.util import Inches, Pt
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[1] / "src" / "urai" / "samples"
FONT_CANDIDATES = [
    "C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size=size)


def laporan_pdf() -> None:
    d = docx.Document()
    d.add_heading("Laporan Pemetaan Sosial 2026", 0)
    d.add_heading("1. Ringkasan", 1)
    d.add_paragraph("Desa Sukamaju dihuni 1.240 kepala keluarga. Sebagian besar bekerja sebagai petani padi dan buruh tani musiman.")
    d.add_heading("2. Analisis Lima Modal", 1)
    rows = [("Modal", "Skor (1–5)", "Temuan utama"),
            ("Manusia", "3,4", "Lulusan SMA meningkat, keterampilan olahan pangan masih rendah"),
            ("Sosial", "4,1", "12 kelompok tani aktif, gotong royong kuat"),
            ("Alam", "2,8", "Sawah tadah hujan, kekeringan Juli–September"),
            ("Fisik", "3,0", "Jalan usaha tani rusak sepanjang 2,3 km"),
            ("Finansial", "2,2", "Akses kredit terbatas pada pinjaman perorangan")]
    t = d.add_table(rows=len(rows), cols=3)
    t.style = "Table Grid"
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            t.cell(r, c).text = v
    d.add_heading("3. Pemetaan Aktor", 1)
    for s in ("Kelompok Tani Mekar Sari: penggerak utama, pengaruh tinggi",
              "BUMDes Sukamaju: minat tinggi, kapasitas pengelolaan masih rendah",
              "Puskesmas Pembantu: mitra untuk program gizi balita"):
        d.add_paragraph(s, style="List Bullet")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "Laporan Pemetaan Sosial 2026.docx"
        d.save(src)
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            raise SystemExit("LibreOffice (soffice) dibutuhkan untuk membuat PDF contoh")
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(src)], check=True, capture_output=True)
        shutil.copy(Path(tmp) / "Laporan Pemetaan Sosial 2026.pdf", OUT / "Laporan Pemetaan Sosial 2026.pdf")


def scanned_page(lines: list[str], seed: int) -> Image.Image:
    rnd = random.Random(seed)
    f = font(34)
    w, h = 1654, 2339  # A4 pada 200 dpi
    img = Image.new("L", (w, h), 244)
    dr = ImageDraw.Draw(img)
    y = 180
    for line in lines:
        dr.text((170, y), line, fill=28, font=f)
        y += 58
    img = img.rotate(rnd.uniform(-1.2, 1.2), expand=False, fillcolor=244, resample=Image.BICUBIC)
    px = img.load()
    for _ in range(int(w * h * 0.004)):
        px[rnd.randrange(w), rnd.randrange(h)] = rnd.choice((60, 120, 200))
    return img.filter(ImageFilter.GaussianBlur(0.6)).convert("RGB")


def surat_scan_pdf() -> None:
    p1 = ["PEMERINTAH DESA SUKAMAJU", "Nomor: 140/27/Ds/X/2026", "Perihal: Undangan Musyawarah Desa", "",
          "Dengan hormat,", "Sehubungan dengan penyusunan Rencana Kerja Pemerintah Desa",
          "tahun 2027, kami mengundang Bapak/Ibu untuk hadir pada:",
          "Hari, tanggal : Kamis, 5 November 2026", "Waktu         : 09.00 WIB sampai selesai",
          "Tempat        : Balai Desa Sukamaju"]
    p2 = ["Acara: pembahasan Rencana Kerja Pemerintah Desa 2027.", "",
          "Mengingat pentingnya acara tersebut, kami mohon kehadiran",
          "Bapak/Ibu tepat waktu. Atas perhatiannya kami ucapkan", "terima kasih.", "", "Kepala Desa Sukamaju"]
    a, b = scanned_page(p1, 1), scanned_page(p2, 2)
    a.save(OUT / "Surat Undangan Musdes.pdf", save_all=True, append_images=[b], resolution=200)


def notulen_docx() -> None:
    d = docx.Document()
    d.add_heading("Notulen FGD Kelompok Tani", 0)
    p = d.add_paragraph()
    p.add_run("Tanggal: ").bold = True
    p.add_run("14 Oktober 2026 · ")
    p.add_run("Peserta: ").bold = True
    p.add_run("18 orang")
    d.add_heading("Masalah utama", 1)
    d.add_paragraph("Harga gabah turun saat panen raya", style="List Number")
    d.add_paragraph("Saluran irigasi tersier rusak di Dusun 2", style="List Number")
    d.add_heading("Usulan", 1)
    d.add_paragraph("Pelatihan pengolahan beras organik", style="List Bullet")
    d.add_paragraph("Pengadaan pompa air bersama", style="List Bullet")
    d.save(OUT / "Notulen FGD Kelompok Tani.docx")


def rekap_xlsx() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap"
    for row in (("Dusun", "Responden", "Rata-rata pendapatan per bulan"), ("Dusun 1", 112, "Rp2,4 juta"),
                ("Dusun 2", 98, "Rp1,9 juta"), ("Dusun 3", 105, "Rp2,1 juta")):
        ws.append(row)
    ws2 = wb.create_sheet("Akses layanan")
    for row in (("Layanan", "Rumah tangga yang memakai"), ("Rekening bank", "63%"), ("Posyandu", "88%"), ("Air bersih PAM", "41%")):
        ws2.append(row)
    wb.save(OUT / "Rekap Survei Rumah Tangga.xlsx")


def chart_image() -> bytes:
    img = Image.new("RGB", (900, 420), "white")
    dr = ImageDraw.Draw(img)
    dr.text((40, 30), "Target Program 2027", fill="black", font=font(44))
    bars = (("Pendapatan petani", 15), ("Anggota BUMDes", 40), ("Lahan teririgasi", 25))
    for i, (label, val) in enumerate(bars):
        y = 130 + i * 90
        dr.text((40, y + 10), label, fill="black", font=font(30))
        dr.rectangle((400, y, 400 + val * 10, y + 54), fill=(46, 91, 230))
        dr.text((410 + val * 10, y + 10), f"+{val}%", fill="black", font=font(30))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def paparan_pptx() -> None:
    p = pptx.Presentation()
    s = p.slides.add_slide(p.slide_layouts[0])
    s.shapes.title.text = "Rencana Program CSR 2027"
    s.placeholders[1].text = "Desa Sukamaju"
    s = p.slides.add_slide(p.slide_layouts[1])
    s.shapes.title.text = "Tujuan"
    s.placeholders[1].text = "Pendapatan petani naik 15% dalam dua tahun\nKelembagaan BUMDes lebih kuat"
    s = p.slides.add_slide(p.slide_layouts[5])
    s.shapes.title.text = "Target"
    s.shapes.add_picture(io.BytesIO(chart_image()), Inches(1), Inches(1.8), width=Inches(8))
    for shape in s.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(36)
    p.save(OUT / "Paparan Program CSR.pptx")


def foto_papan() -> None:
    img = Image.new("RGB", (1400, 800), (226, 232, 240))
    dr = ImageDraw.Draw(img)
    dr.rectangle((80, 80, 1320, 720), fill=(255, 255, 250), outline=(60, 60, 60), width=6)
    dr.text((140, 140), "PAPAN INFORMASI DESA SUKAMAJU", fill=(20, 20, 20), font=font(54))
    for i, line in enumerate(("Jadwal Posyandu: setiap Selasa minggu kedua", "Musyawarah Desa: Kamis, 5 November 2026",
                              "Pendaftaran pelatihan beras organik dibuka")):
        dr.text((140, 280 + i * 110), line, fill=(30, 30, 30), font=font(44))
    img = img.rotate(-1.5, expand=False, fillcolor=(226, 232, 240), resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.7))
    img.save(OUT / "Foto Papan Informasi.jpg", quality=88)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    laporan_pdf()
    surat_scan_pdf()
    notulen_docx()
    rekap_xlsx()
    paparan_pptx()
    foto_papan()
    for f in sorted(OUT.iterdir()):
        print(f"{f.stat().st_size // 1024:>6} KB  {f.name}")


if __name__ == "__main__":
    main()
