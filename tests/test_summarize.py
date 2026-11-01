import threading

from urai import ai as ai_mod
from urai import i18n
from urai.summarize import (CHUNK_CHARS, PROMPTS, Summarizer, clean_kind, clean_outline, notes_prompt, split_chunks,
                            struct_combined, struct_outline, system_prompt)


def test_struct_word_style_multiple_h1():
    md = ("Notulen Rapat Pengurus\n\n**Tanggal:** 14 Oktober 2026\n\n# Masalah utama\n\n1. Jumlah anggota turun\n"
          "2. Atap ruang baca bocor\n\n# Usulan\n\n* Lomba menulis cerpen\n")
    out = struct_outline("Notulen Rapat Pengurus.docx", md).splitlines()
    assert out[0] == "# Notulen Rapat Pengurus"
    assert "## Masalah utama" in out and "## Usulan" in out
    assert "- Jumlah anggota turun" in out
    assert "## Tanggal: 14 Oktober 2026" in out  # poin sebelum sub-judul dijadikan cabang supaya tidak hilang di markmap
    assert "- Notulen Rapat Pengurus" not in out  # judul yang diulang di baris pertama dilewati


def test_struct_single_h1_after_other_heading_is_kept():
    # mis. setelah diedit: judul pertama jadi tingkat 2, satu-satunya tingkat 1 ada di tengah
    md = "Notulen\n\n## Pembahasan\n\n1. Atap bocor\n\n# Keputusan\n\n* Perbaiki atap\n"
    out = struct_outline("Notulen.docx", md)
    assert "Keputusan" in out and "Pembahasan" in out and "Perbaiki atap" in out
    # satu judul tingkat 1 di awal tetap dianggap judul dokumen
    first = struct_outline("Laporan.docx", "# Laporan\n\n## Ringkasan\n\n- Poin\n").splitlines()
    assert first[0] == "# Laporan" and "## Ringkasan" in first


def test_struct_plain_pdf_text():
    md = ("Laporan Tahunan Perpustakaan 2026\n1. Ringkasan\nPerpustakaan kota melayani 1.240 anggota aktif. Sebagian besar datang pada akhir pekan dan\n"
          "saat libur sekolah.\n2. Analisis Layanan\n| Layanan | Skor | Catatan |\n| --- | --- | --- |\n| Peminjaman | 3,4 | Buku anak paling diminati, |\n"
          "terutama cerita bergambar\n| Ruang baca | 4,1 | 12 kelompok belajar rutin, |\n| --- | --- | --- |\nsuasana tenang\n"
          "3. Mitra Kegiatan\n Klub Baca Mekar Sari: penggerak utama\n")
    out = struct_outline("Laporan Tahunan Perpustakaan 2026.pdf", md).splitlines()
    assert out[:3] == ["# Laporan Tahunan Perpustakaan 2026", "## 1. Ringkasan", "- Perpustakaan kota melayani 1.240 anggota aktif."]
    assert "- Peminjaman: 3,4 · Buku anak paling diminati, terutama cerita bergambar" in out
    assert "- Ruang baca: 4,1 · 12 kelompok belajar rutin, suasana tenang" in out
    assert "- Klub Baca Mekar Sari: penggerak utama" in out


def test_struct_slides_keep_lines_and_nested():
    md = ("<!-- Slide number: 1 -->\n# Rencana Program Literasi\nPerpustakaan Kota\n\n<!-- Slide number: 2 -->\n# Tujuan\n"
          "Pengunjung naik 15%\nKoleksi lebih lengkap\n")
    out = struct_outline("Paparan.pptx", md, nested=True).splitlines()
    assert out[0] == "## Paparan"
    assert "### Tujuan" in out
    assert "- Pengunjung naik 15%" in out and "- Koleksi lebih lengkap" in out


def test_promote_orphans():
    from urai.summarize import promote_orphans

    md = "# A\n- x\n  - x1\n## B\n- y\n# C\n- z"
    assert promote_orphans(md) == "# A\n## x\n- x1\n## B\n- y\n# C\n- z"


def test_struct_empty_and_combined():
    assert struct_outline("kosong.pdf", "").endswith("- No structure could be found")
    md = struct_combined("Combined", [("a.docx", "# A\n- satu\n# B\n- dua"), ("b.pdf", "")])
    assert md.startswith("# Combined\n## a\n")
    assert "### A" in md
    i18n.set_lang("id")
    assert struct_outline("kosong.pdf", "").endswith("- Tidak ada struktur yang bisa diambil")


def test_struct_reads_ocr_output_in_both_languages():
    # hasil baca scan memakai judul halaman dan catatan sumber sesuai bahasa; keduanya tetap jadi kerangka yang rapi
    for note, page in (("> Read with Offline OCR (Indonesian, English) · 2 of 2 pages scanned", "Page"),
                       ("> Dibaca dengan OCR offline (Indonesia, Inggris) · 2 dari 2 halaman hasil scan", "Halaman")):
        md = f"{note}\n\n## {page} 1\n\nKopi berasal dari Etiopia.\n\n## {page} 2\n\nKopi sampai ke Jawa."
        out = struct_outline("Scan.pdf", md).splitlines()
        assert out == ["# Scan", f"## {page} 1", "- Kopi berasal dari Etiopia.", f"## {page} 2", "- Kopi sampai ke Jawa."]


def test_struct_docling_flat_headings():
    # mesin PDF teliti menulis semua judul sebagai ##, termasuk judul dokumen dan sub-bab bernomor
    md = ("## Laporan Perpustakaan Kota 2026\n\n## 1. Ringkasan\n\nPengunjung naik 18 persen.\n\n## 2 Layanan\n\n"
          "## 2.1 Peminjaman\n\n| Kategori | Total |\n|---|---|\n| Fiksi | 4.104 |\n\n## Pojok anak\n\nRamai saat Sabtu.\n\n"
          "## 3 Rekomendasi\n\n- Menambah ruang baca\n\n## Lampiran\n\nDaftar mitra.")
    out = struct_outline("tabel-word.pdf", md).splitlines()
    assert out[0] == "# tabel-word" and "## Laporan Perpustakaan Kota 2026" not in out  # judul dokumen tanpa isi
    assert out[1:3] == ["## 1. Ringkasan", "- Pengunjung naik 18 persen."]
    assert "### 2.1 Peminjaman" in out
    assert "#### Pojok anak" in out  # judul tanpa nomor di bawah sub-bab bernomor
    assert "#### Fiksi: 4.104" in out  # poin sebelum sub-judul dinaikkan supaya tidak hilang di markmap
    assert "## 3 Rekomendasi" in out and "## Lampiran" in out
    # judul pembuka yang punya isi tetap jadi cabang
    out = struct_outline("x.pdf", "## Abstrak\n\nRingkas.\n\n## 1 Pendahuluan\n\nIsi.").splitlines()
    assert out[1:3] == ["## Abstrak", "- Ringkas."] and "## 1 Pendahuluan" in out


def test_split_chunks_respects_limit():
    text = "\n\n".join(f"## Bagian {i}\n" + ("kata " * 400) for i in range(60))
    chunks = split_chunks(text, limit=5000)
    assert len(chunks) > 1
    assert all(len(c) <= 5000 for c in chunks)
    assert "".join(chunks).count("## Bagian") == 60
    giant = "x" * 12000
    assert [len(c) for c in split_chunks(giant, limit=5000)] == [5000, 5000, 2000]


def test_clean_outline():
    raw = "Berikut rangkumannya:\n```markdown\n# Judul\n## A\n* poin\n  * sub\n# B lagi\n| tabel |\n```"
    out = clean_outline(raw, "Cadangan").splitlines()
    assert out[0] == "# Judul"  # kalimat pembuka sebelum judul dibuang
    assert not any("Berikut" in line for line in out)
    assert clean_outline("- poin saja", "Cadangan").splitlines()[0] == "# Cadangan"
    assert "## B lagi" in out  # judul tingkat 1 kedua diturunkan
    assert "  - sub" in out
    assert not any("tabel" in line for line in out)
    assert clean_outline("", "X") == "# X\n- Nothing to summarize"
    i18n.set_lang("id")
    assert clean_outline("", "X") == "# X\n- Tidak ada poin yang bisa dirangkum"


def test_kinds_and_prompts():
    assert clean_kind("umum") == "poin" and clean_kind("laporan") == "lengkap" and clean_kind("x") == "poin"
    assert set(PROMPTS["en"]) == set(PROMPTS["id"])
    for lang in ("en", "id"):
        for kind in ("poin", "notulen", "lengkap"):
            assert "{" not in system_prompt(kind, lang) and "{" not in notes_prompt(kind, lang)
    assert "Write the mind map outline in English" in system_prompt("poin", "en") and "Key points" in system_prompt("poin", "en")
    assert "## Meeting details" in system_prompt("notulen", "en") and '"Not discussed"' in system_prompt("notulen", "en")
    assert "## Conclusion" in system_prompt("lengkap", "en")
    assert "## Informasi pertemuan" in system_prompt("notulen", "id") and '"Tidak dibahas"' in system_prompt("notulen", "id")
    assert "## Kesimpulan" in system_prompt("lengkap", "id") and "Bahasa Indonesia" in system_prompt("poin", "id")
    assert "who said what" in notes_prompt("notulen", "en") and "mind map" not in notes_prompt("poin", "en")


def test_summarizer_chunks_long_documents(monkeypatch):
    calls = []

    def fake_chat(cfg, system, user):
        calls.append((system, len(user)))
        if "mind map outline" in system:
            return "# Laporan\n## Temuan\n- poin"
        return "- catatan penting"

    monkeypatch.setattr(ai_mod, "chat", fake_chat)
    cfg = ai_mod.AIConfig("gemini", "kunci")
    progress = []
    sm = Summarizer(cfg, "laporan", progress.append, threading.Event())
    assert sm.kind == "lengkap"  # jenis lama dari pengaturan versi sebelumnya
    text = "\n\n".join(("Paragraf panjang tentang buku. " * 80) for _ in range(40))
    assert len(text) > CHUNK_CHARS
    md = sm.one("Laporan.pdf", text)
    assert md.startswith("# Laporan")
    notes_calls = [c for c in calls if "take notes" in c[0]]
    assert len(notes_calls) >= 2
    assert all("every section" in c[0] for c in notes_calls)  # fokus catatan mengikuti jenis rangkuman
    assert all(n <= CHUNK_CHARS + 200 for _, n in calls)
    assert any("part" in p for p in progress)
    # dokumen kosong tidak memanggil AI sama sekali
    calls.clear()
    assert "No readable text" in sm.one("scan.pdf", "  ")
    assert calls == []


def test_summarizer_many_short(monkeypatch):
    seen = {}

    def fake_chat(cfg, system, user):
        seen["system"], seen["user"] = system, user
        return "# Combined\n## Isi\n- poin"

    monkeypatch.setattr(ai_mod, "chat", fake_chat)
    progress = []
    sm = Summarizer(ai_mod.AIConfig("claude", "k"), "poin", progress.append, threading.Event())
    md = sm.many("Combined", [("a.docx", "isi a"), ("b.pdf", "isi b"), ("c.jpg", "")])
    assert md.startswith("# Combined")
    assert "=== Document 1: a ===" in seen["user"] and "=== Document 2: b ===" in seen["user"]
    assert "Document 3" not in seen["user"]
    assert seen["user"].startswith("Mind map title: Combined") and "Key points" in seen["system"]
    assert "Summarizing 2 documents…" in progress
    # bahasa Indonesia: perintah, judul cabang wajib, dan kabar proses ikut berganti
    i18n.set_lang("id")
    progress.clear()
    sm = Summarizer(ai_mod.AIConfig("claude", "k"), "notulen", progress.append, threading.Event())
    sm.many("Gabungan", [("a.docx", "isi a"), ("b.pdf", "isi b")])
    assert "=== Dokumen 1: a ===" in seen["user"] and seen["user"].startswith("Judul mind map: Gabungan")
    assert "Bahasa Indonesia" in seen["system"] and "Informasi pertemuan" in seen["system"]
    assert "Meringkas 2 dokumen…" in progress


def test_outlines_have_no_links():
    md = "# Judul\n## [Bab](https://contoh.example)\n- lihat [situs](http://x.y/z) ini\n![gambar](a.png)\n| [A](u) | b |\n| --- | --- |\n| [c](u) | d |"
    out = struct_outline("Judul.docx", md)
    assert "](" not in out and "Bab" in out and "lihat situs ini" in out
    assert "](" not in clean_outline("# T\n## [x](http://a.b)\n- [y](http://c.d)", "T")
