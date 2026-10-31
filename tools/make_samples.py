"""Buat enam file contoh untuk tombol "Coba dengan file contoh".

Isinya fiktif dan umum (potongan buku, notulen rapat, perpustakaan), ditulis khusus untuk Urai App.
Setiap file menguji satu kemampuan: PDF teks, PDF hasil scan (OCR), Word bergaya, Excel dua sheet,
PowerPoint dengan teks di dalam gambar, dan foto papan pengumuman.

Jalankan dari akar repo:
    python tools/make_samples.py
Butuh: python-docx, python-pptx, openpyxl, Pillow, reportlab.
"""
from __future__ import annotations

import io
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[1] / "src" / "urai" / "samples"
AUTHOR = "Urai App"
WIN = os.environ.get("WINDIR", "C:/Windows") + "/Fonts/"

FONTS = {
    "serif": [WIN + "georgia.ttf", WIN + "times.ttf", "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
    "serif-bold": [WIN + "georgiab.ttf", WIN + "timesbd.ttf", "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
    "sans": [WIN + "arial.ttf", WIN + "segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/freefont/FreeSans.ttf"],
    "sans-bold": [WIN + "arialbd.ttf", WIN + "segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS[kind]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise SystemExit(f"Tidak ada huruf {kind} di komputer ini")


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    """Pecah paragraf per kata supaya muat selebar `width` piksel (kata tidak pernah dipotong)."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------- 1. PDF teks biasa ----------

def make_text_pdf() -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Huruf TrueType ditanam supaya teks (termasuk tanda bullet) bisa disalin dan dibaca ulang dengan benar
    regular = next(p for p in FONTS["sans"] if os.path.exists(p))
    bold = next(p for p in FONTS["sans-bold"] if os.path.exists(p))
    pdfmetrics.registerFont(TTFont("ContohSans", regular))
    pdfmetrics.registerFont(TTFont("ContohSans-Bold", bold))
    addMapping("ContohSans", 0, 0, "ContohSans")
    addMapping("ContohSans", 1, 0, "ContohSans-Bold")

    ink = colors.HexColor("#1F2937")
    title = ParagraphStyle("t", fontName="ContohSans-Bold", fontSize=22, leading=28, textColor=ink, spaceAfter=14)
    head = ParagraphStyle("h", fontName="ContohSans-Bold", fontSize=14, leading=19, textColor=ink, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("b", fontName="ContohSans", fontSize=11.5, leading=17, textColor=ink)

    def bullets(items):
        return ListFlowable([ListItem(Paragraph(t, body), leftIndent=14) for t in items], bulletType="bullet",
                            start="\u2022", leftIndent=14, bulletFontName="ContohSans", bulletFontSize=11)

    story = [
        Paragraph("Bab 1 Mengelola Waktu", title),
        Paragraph("1. Mengapa Waktu Terasa Kurang", head),
        Paragraph("Banyak orang merasa waktunya selalu kurang, padahal setiap orang punya 24 jam yang sama dalam sehari. "
                  "Masalahnya sering kali bukan jumlah waktu, melainkan cara kita memilih pekerjaan yang didahulukan. "
                  "Bab ini membahas cara sederhana untuk menentukan prioritas.", body),
        Paragraph("2. Matriks Prioritas", head),
        Paragraph("Matriks Prioritas membagi pekerjaan ke dalam empat kelompok:", body),
        Spacer(1, 4),
        bullets([
            "<b>Penting dan mendesak:</b> kerjakan sekarang.",
            "<b>Penting tapi tidak mendesak:</b> jadwalkan.",
            "<b>Mendesak tapi tidak penting:</b> batasi.",
            "<b>Tidak penting dan tidak mendesak:</b> kurangi.",
        ]),
        Paragraph("3. Kebiasaan yang Membantu", head),
        bullets([
            "Tulis tiga tugas terpenting setiap pagi.",
            "Kerjakan tugas yang paling berat saat tenaga masih penuh.",
            "Matikan notifikasi selama bekerja dengan fokus.",
        ]),
    ]
    doc = SimpleDocTemplate(str(OUT / "Bab 1 Mengelola Waktu.pdf"), pagesize=A4, leftMargin=25 * mm, rightMargin=25 * mm,
                            topMargin=25 * mm, bottomMargin=25 * mm, title="Bab 1 Mengelola Waktu",
                            author=AUTHOR, creator=AUTHOR, subject="Contoh dokumen Urai App")
    doc.build(story)


# ---------- 2. PDF hasil scan (gambar saja) ----------

def scan_page(blocks: list[tuple[str, str]], seed: int, page_no: int) -> Image.Image:
    w, h = 1654, 2339  # A4 pada 200 dpi
    img = Image.new("L", (w, h), 246)
    d = ImageDraw.Draw(img)
    margin, y = 190, 230
    styles = {"title": (font("serif-bold", 64), 92, 1.0), "sub": (font("serif", 46), 110, 1.0),
              "p": (font("serif", 40), 64, 0.0)}
    for kind, text in blocks:
        fnt, gap, _ = styles[kind]
        lines = wrap(d, text, fnt, w - 2 * margin)
        for line in lines:
            if kind == "p":
                d.text((margin, y), line, fill=30, font=fnt)
            else:
                tw = d.textlength(line, font=fnt)
                d.text(((w - tw) / 2, y), line, fill=25, font=fnt)
            y += gap if kind != "p" else 64
        y += 30 if kind == "p" else 10
    num = font("serif", 34)
    label = f"- {page_no} -"
    d.text(((w - d.textlength(label, font=num)) / 2, h - 200), label, fill=60, font=num)
    rnd = random.Random(seed)
    for _ in range(420):  # bintik debu halus
        x, yy, r = rnd.randrange(w), rnd.randrange(h), rnd.choice((1, 1, 1, 2))
        d.ellipse((x, yy, x + r, yy + r), fill=rnd.randrange(150, 200))
    img = img.rotate(1.0 if page_no == 1 else -0.8, resample=Image.BICUBIC, fillcolor=246)
    return img.filter(ImageFilter.GaussianBlur(0.7))


def make_scan_pdf() -> None:
    p1 = [
        ("title", "SEJARAH SINGKAT KOPI"),
        ("sub", "Dari Etiopia ke Nusantara"),
        ("p", "Menurut sebuah legenda, kopi pertama kali dikenal di dataran tinggi Etiopia. Seorang penggembala "
              "kambing bernama Kaldi heran melihat kambing-kambingnya menjadi sangat lincah setelah memakan buah "
              "merah dari sebuah semak."),
        ("p", "Kaldi lalu mencoba buah itu sendiri dan merasa lebih segar. Ia membawa buah tersebut kepada para "
              "biarawan di dekat tempat tinggalnya. Mereka merebus buah itu menjadi minuman yang membantu tetap "
              "terjaga saat berdoa pada malam hari."),
        ("p", "Kisah ini sulit dibuktikan, tetapi terus diceritakan dari generasi ke generasi sebagai awal "
              "perjalanan kopi ke seluruh dunia."),
    ]
    p2 = [
        ("p", "Dari Etiopia, kopi menyeberangi Laut Merah dan sampai di Yaman. Di sana kopi mulai ditanam secara "
              "teratur dan diperdagangkan melalui pelabuhan Mokha. Kedai kopi bermunculan di kota-kota besar dan "
              "menjadi tempat orang berkumpul untuk berbincang."),
        ("p", "Pada akhir abad ke-17, bibit kopi dibawa ke Pulau Jawa. Tanaman itu tumbuh subur di dataran tinggi, "
              "dan kopi dari Jawa segera dikenal di pasar dunia."),
        ("p", "Karena terkenalnya kopi dari pulau ini, kata \"Java\" dalam bahasa Inggris ikut dipakai sebagai "
              "sebutan untuk kopi. Sebutan itu masih sering terdengar sampai sekarang."),
    ]
    pages = [scan_page(p1, 11, 1), scan_page(p2, 12, 2)]
    pages[0].save(OUT / "Scan Buku Sejarah Kopi.pdf", save_all=True, append_images=pages[1:], resolution=200,
                  quality=55, title="Scan Buku Sejarah Kopi", author=AUTHOR, creator=AUTHOR, producer=AUTHOR)


# ---------- 3. Word dengan gaya bawaan ----------

def make_docx() -> None:
    from docx import Document

    d = Document()
    d.add_paragraph("Notulen Rapat Tim", style="Title")
    p = d.add_paragraph()
    p.add_run("Tanggal:").bold = True
    p.add_run(" 28 Oktober 2026 · ")
    p.add_run("Peserta:").bold = True
    p.add_run(" 7 orang")
    d.add_heading("Pembahasan", level=1)
    d.add_paragraph("Keluhan pengguna bahwa halaman pendaftaran terlalu panjang dan membingungkan", style="List Number")
    d.add_paragraph("Rencana peluncuran fitur pencarian baru bulan depan", style="List Number")
    d.add_heading("Keputusan", level=1)
    d.add_paragraph("Formulir di halaman pendaftaran dipersingkat menjadi tiga langkah", style="List Bullet")
    d.add_paragraph("Fitur pencarian diluncurkan pada pertengahan November", style="List Bullet")
    d.add_heading("Tindak lanjut", level=1)
    d.add_paragraph("Rina: membuat rancangan formulir pendaftaran yang baru", style="List Bullet")
    d.add_paragraph("Dimas: menyiapkan uji coba fitur pencarian dengan lima pengguna", style="List Bullet")
    cp = d.core_properties
    cp.author = cp.last_modified_by = AUTHOR
    cp.title = "Notulen Rapat Tim"
    cp.comments = "Contoh dokumen Urai App"
    d.save(OUT / "Notulen Rapat Tim.docx")


# ---------- 4. Excel dua sheet ----------

def make_xlsx() -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    head_font, head_fill = Font(bold=True), PatternFill("solid", fgColor="E8EEFF")

    def fill(ws, rows, widths):
        for r in rows:
            ws.append(r)
        for c in ws[1]:
            c.font, c.fill = head_font, head_fill
        for col, wdt in zip("ABC", widths):
            ws.column_dimensions[col].width = wdt

    ws = wb.active
    ws.title = "Koleksi"
    fill(ws, [("Kategori", "Jumlah judul", "Dipinjam bulan ini"), ("Fiksi", 1240, 318), ("Sains", 860, 142),
              ("Sejarah", 530, 97), ("Buku anak", 975, 406)], (16, 16, 22))
    ws2 = wb.create_sheet("Pengunjung")
    fill(ws2, [("Bulan", "Jumlah pengunjung"), ("Agustus", 1820), ("September", 2105), ("Oktober", 2340)], (14, 22))
    wb.properties.creator = wb.properties.lastModifiedBy = AUTHOR
    wb.properties.title = "Statistik Perpustakaan"
    wb.save(OUT / "Statistik Perpustakaan.xlsx")


# ---------- 5. PowerPoint dengan teks di dalam gambar ----------

def chart_png() -> bytes:
    img = Image.new("RGB", (900, 420), "white")
    d = ImageDraw.Draw(img)
    title = font("sans-bold", 44)
    label = font("sans", 30)
    text = "Kebiasaan yang Dicoba Peserta"
    d.text(((900 - d.textlength(text, font=title)) / 2, 26), text, fill="black", font=title)
    rows = (("Tiga tugas", 9), ("Blok fokus", 6), ("Tanpa notifikasi", 4))
    x0, unit = 300, 44
    for i, (name, n) in enumerate(rows):
        y = 130 + i * 92
        d.text((x0 - 24 - d.textlength(name, font=label), y + 8), name, fill="black", font=label)
        d.rectangle((x0, y, x0 + n * unit, y + 54), fill=(160, 184, 240))
        d.text((x0 + n * unit + 18, y + 8), f"{n} orang", fill="black", font=label)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def make_pptx() -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[0])  # Title Slide
    s1.shapes.title.text = "Ringkasan Buku: Mengelola Waktu"
    s1.placeholders[1].text = "Diskusi Klub Baca"
    s2 = prs.slides.add_slide(prs.slide_layouts[1])  # Title and Content
    s2.shapes.title.text = "Poin Utama"
    body = s2.placeholders[1].text_frame
    body.text = "Bedakan pekerjaan yang penting dari yang sekadar mendesak"
    body.add_paragraph().text = "Mulai hari dengan menulis tiga tugas terpenting"
    s3 = prs.slides.add_slide(prs.slide_layouts[5])  # Title Only
    s3.shapes.title.text = "Hasil Diskusi"
    width = Inches(8.4)
    s3.shapes.add_picture(io.BytesIO(chart_png()), Inches(0.8), Inches(2.2), width=width)
    for shape in s3.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(40)
    cp = prs.core_properties
    cp.author = cp.last_modified_by = AUTHOR
    cp.title = "Ringkasan Buku: Mengelola Waktu"
    prs.save(OUT / "Presentasi Ringkasan Buku.pptx")


# ---------- 6. Foto papan pengumuman ----------

def make_photo() -> None:
    w, h = 1400, 800
    rnd = random.Random(7)
    # dinding dengan cahaya yang sedikit tidak rata
    wall = Image.new("RGB", (w, h))
    px = wall.load()
    for yy in range(h):
        for xx in range(w):
            shade = 196 - int(28 * ((xx - 520) ** 2 + (yy - 300) ** 2) / (w * w)) + rnd.randrange(-3, 4)
            px[xx, yy] = (shade, shade - 6, shade - 16)
    board = Image.new("RGB", (1180, 620), (248, 248, 246))
    bd = ImageDraw.Draw(board)
    bd.rectangle((0, 0, 1179, 619), outline=(150, 154, 160), width=22)  # bingkai aluminium
    bd.rectangle((22, 22, 1157, 597), outline=(118, 122, 128), width=3)
    title, body = font("sans-bold", 54), font("sans", 44)
    head = "PENGUMUMAN PERPUSTAKAAN"
    bd.text(((1180 - bd.textlength(head, font=title)) / 2, 92), head, fill=(18, 18, 20), font=title)
    lines = ("Jam buka: Senin sampai Jumat, 08.00-16.00", "Batas peminjaman buku: 14 hari",
             "Klub baca: Sabtu, 7 November 2026")
    for i, line in enumerate(lines):
        bd.text((96, 236 + i * 104), line, fill=(28, 28, 30), font=body)
    mask = Image.new("L", board.size, 255)
    board = board.rotate(1.5, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0))
    mask = mask.rotate(1.5, resample=Image.BICUBIC, expand=True, fillcolor=0)
    wall.paste(board, ((w - board.width) // 2, (h - board.height) // 2), mask)
    photo = wall.filter(ImageFilter.GaussianBlur(0.9))
    exif = Image.Exif()
    exif[0x013B] = AUTHOR            # Artist
    exif[0x010E] = "Contoh foto Urai App"  # ImageDescription
    exif[0x0131] = AUTHOR            # Software
    photo.save(OUT / "Foto Pengumuman Perpustakaan.jpg", quality=85, optimize=True, exif=exif)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():
            old.unlink()
    make_text_pdf()
    make_scan_pdf()
    make_docx()
    make_xlsx()
    make_pptx()
    make_photo()
    for f in sorted(OUT.iterdir()):
        print(f"{f.stat().st_size // 1024:>6} KB  {f.name}")


if __name__ == "__main__":
    main()
