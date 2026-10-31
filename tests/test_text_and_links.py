from datetime import datetime
from pathlib import Path

import pytest

from urai import i18n
from urai.errors import friendly_error
from urai.links import host_of, is_youtube, normalize_link
from urai.textutil import build_combined, demote_headings, human_size, safe_filename, unique_path, word_count


def test_word_count_and_sizes():
    assert word_count("Perpustakaan kota punya 1.240 buku") == 6
    assert word_count("") == 0
    assert human_size(500) == "500 B"
    assert human_size(2048) == "2 KB"
    assert human_size(3.8 * 1024 * 1024) == "3.8 MB"
    i18n.set_lang("id")
    assert human_size(3.8 * 1024 * 1024) == "3,8 MB"
    assert human_size(2048) == "2 KB"


@pytest.mark.parametrize("name,expected", [
    ('Laporan: "akhir"?', "Laporan akhir"),
    ("CON", "_CON"),
    ("nul.txt", "_nul.txt"),
    ("   ...   ", "hasil"),
    ("a/b\\c", "a b c"),
])
def test_safe_filename(name, expected):
    assert safe_filename(name) == expected


def test_unique_path(tmp_path: Path):
    p = tmp_path / "hasil.md"
    assert unique_path(p) == p
    p.write_text("x")
    assert unique_path(p).name == "hasil (2).md"
    (tmp_path / "hasil (2).md").write_text("x")
    assert unique_path(p).name == "hasil (3).md"


def test_demote_headings_skips_code():
    md = "# Judul\n```\n# bukan judul\n```\n## Sub"
    assert demote_headings(md) == "## Judul\n```\n# bukan judul\n```\n### Sub"


def test_build_combined_order_and_empty():
    out = build_combined([("a.pdf", "# A\nisi"), ("b.docx", "")], now=datetime(2026, 10, 31, 9, 5))
    assert out.startswith("> Combined from 2 documents, created 2026-10-31 09:05 with Urai App")
    assert out.index("# a.pdf") < out.index("# b.docx")
    assert "## A" in out
    assert "_(no text could be taken)_" in out
    assert build_combined([("a.pdf", "x")], now=datetime(2026, 1, 2, 3, 4)).startswith("> Combined from 1 document, ")
    i18n.set_lang("id")
    out = build_combined([("a.pdf", "# A\nisi"), ("b.docx", "")], now=datetime(2026, 10, 31, 9, 5))
    assert out.startswith("> Gabungan dari 2 dokumen, dibuat 31-10-2026 09.05 dengan Urai App")
    assert "_(tidak ada teks yang bisa diambil)_" in out


@pytest.mark.parametrize("text,url", [
    ("https://youtu.be/dQw4w9WgXcQ?si=abc", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ("youtube.com/shorts/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=10", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ("https://www.youtube.com/live/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ("www.bps.go.id/id/statistics-table", "https://www.bps.go.id/id/statistics-table"),
    ("https://perpusnas.go.id", "https://perpusnas.go.id"),
])
def test_normalize_link(text, url):
    assert normalize_link(text) == url


@pytest.mark.parametrize("text", ["", "bukan link", "ftp://x.y", "https://localhost", "javascript:alert(1)", "https://youtu.be/<x>"])
def test_normalize_link_rejects(text):
    assert normalize_link(text) is None


def test_link_helpers():
    assert is_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert not is_youtube("https://example.com")
    assert host_of("https://www.bps.go.id/a") == "bps.go.id"


def test_friendly_error_unwraps_and_translates():
    class FileConversionException(Exception):
        pass

    class Attempt:
        def __init__(self, exc):
            self.exc_info = (type(exc), exc, None)

    inner = PermissionError("locked")
    outer = FileConversionException("wrapped")
    outer.attempts = [Attempt(inner)]
    assert "permission" in friendly_error(outer)
    assert "password" in friendly_error(RuntimeError("File is encrypted"))
    assert friendly_error(RuntimeError("sesuatu yang lain")) == "sesuatu yang lain"
    assert friendly_error(RuntimeError("{tanda kurung} tetap utuh")) == "{tanda kurung} tetap utuh"
    i18n.set_lang("id")
    assert "izin" in friendly_error(outer)
    assert "kata sandi" in friendly_error(RuntimeError("File is encrypted"))
