import threading

from urai import ai as ai_mod
from urai.summarize import CHUNK_CHARS, Summarizer, clean_outline, split_chunks, struct_combined, struct_outline


def test_struct_word_style_multiple_h1():
    md = ("Notulen FGD\n\n**Tanggal:** 14 Oktober 2026\n\n# Masalah utama\n\n1. Harga gabah turun\n"
          "2. Irigasi rusak\n\n# Usulan\n\n* Pelatihan beras organik\n")
    out = struct_outline("Notulen FGD.docx", md).splitlines()
    assert out[0] == "# Notulen FGD"
    assert "## Masalah utama" in out and "## Usulan" in out
    assert "- Harga gabah turun" in out
    assert "## Tanggal: 14 Oktober 2026" in out  # poin sebelum sub-judul dijadikan cabang supaya tidak hilang di markmap
    assert "- Notulen FGD" not in out  # judul yang diulang di baris pertama dilewati


def test_struct_plain_pdf_text():
    md = ("Laporan Pemetaan Sosial 2026\n1. Ringkasan\nDesa Sukamaju dihuni 1.240 kepala keluarga. Sebagian besar bekerja sebagai petani padi dan\n"
          "buruh tani musiman.\n2. Analisis Lima Modal\n| Modal | Skor | Temuan |\n| --- | --- | --- |\n| Manusia | 3,4 | Lulusan SMA meningkat, |\n"
          "keterampilan olahan pangan\n| Sosial | 4,1 | 12 kelompok tani aktif, |\n| --- | --- | --- |\ngotong royong kuat\n"
          "3. Pemetaan Aktor\n Kelompok Tani Mekar Sari: penggerak utama\n")
    out = struct_outline("Laporan Pemetaan Sosial 2026.pdf", md).splitlines()
    assert out[:3] == ["# Laporan Pemetaan Sosial 2026", "## 1. Ringkasan", "- Desa Sukamaju dihuni 1.240 kepala keluarga."]
    assert "- Manusia: 3,4 · Lulusan SMA meningkat, keterampilan olahan pangan" in out
    assert "- Sosial: 4,1 · 12 kelompok tani aktif, gotong royong kuat" in out
    assert "- Kelompok Tani Mekar Sari: penggerak utama" in out


def test_struct_slides_keep_lines_and_nested():
    md = "<!-- Slide number: 1 -->\n# Rencana CSR\nDesa Sukamaju\n\n<!-- Slide number: 2 -->\n# Tujuan\nPendapatan naik 15%\nBUMDes lebih kuat\n"
    out = struct_outline("Paparan.pptx", md, nested=True).splitlines()
    assert out[0] == "## Paparan"
    assert "### Tujuan" in out
    assert "- Pendapatan naik 15%" in out and "- BUMDes lebih kuat" in out


def test_promote_orphans():
    from urai.summarize import promote_orphans

    md = "# A\n- x\n  - x1\n## B\n- y\n# C\n- z"
    assert promote_orphans(md) == "# A\n## x\n- x1\n## B\n- y\n# C\n- z"


def test_struct_empty_and_combined():
    assert struct_outline("kosong.pdf", "").endswith("- Tidak ada struktur yang bisa diambil")
    md = struct_combined("Gabungan", [("a.docx", "# A\n- satu\n# B\n- dua"), ("b.pdf", "")])
    assert md.startswith("# Gabungan\n## a\n")
    assert "### A" in md


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
    assert clean_outline("", "X") == "# X\n- Tidak ada poin yang bisa dirangkum"


def test_summarizer_chunks_long_documents(monkeypatch):
    calls = []

    def fake_chat(cfg, system, user):
        calls.append((system, len(user)))
        if "kerangka mind map" in system:
            return "# Laporan\n## Temuan\n- poin"
        return "- catatan penting"

    monkeypatch.setattr(ai_mod, "chat", fake_chat)
    cfg = ai_mod.AIConfig("gemini", "kunci")
    progress = []
    sm = Summarizer(cfg, "laporan", progress.append, threading.Event())
    text = "\n\n".join(("Paragraf panjang tentang desa. " * 80) for _ in range(40))
    assert len(text) > CHUNK_CHARS
    md = sm.one("Laporan.pdf", text)
    assert md.startswith("# Laporan")
    notes_calls = [c for c in calls if "mencatat poin" in c[0]]
    assert len(notes_calls) >= 2
    assert all(n <= CHUNK_CHARS + 200 for _, n in calls)
    assert any("bagian" in p for p in progress)
    # dokumen kosong tidak memanggil AI sama sekali
    calls.clear()
    assert "Tidak ada teks terbaca" in sm.one("scan.pdf", "  ")
    assert calls == []


def test_summarizer_many_short(monkeypatch):
    seen = {}

    def fake_chat(cfg, system, user):
        seen["user"] = user
        return "# Gabungan\n## Isi\n- poin"

    monkeypatch.setattr(ai_mod, "chat", fake_chat)
    sm = Summarizer(ai_mod.AIConfig("claude", "k"), "umum", lambda t: None, threading.Event())
    md = sm.many("Gabungan", [("a.docx", "isi a"), ("b.pdf", "isi b"), ("c.jpg", "")])
    assert md.startswith("# Gabungan")
    assert "=== Dokumen 1: a ===" in seen["user"] and "=== Dokumen 2: b ===" in seen["user"]
    assert "Dokumen 3" not in seen["user"]


def test_outlines_have_no_links():
    md = "# Judul\n## [Bab](https://contoh.example)\n- lihat [situs](http://x.y/z) ini\n![gambar](a.png)\n| [A](u) | b |\n| --- | --- |\n| [c](u) | d |"
    out = struct_outline("Judul.docx", md)
    assert "](" not in out and "Bab" in out and "lihat situs ini" in out
    assert "](" not in clean_outline("# T\n## [x](http://a.b)\n- [y](http://c.d)", "T")
