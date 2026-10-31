import json

import pypdfium2 as pdfium
import pytest
from PIL import Image

from urai import export, settings
from urai.settings import Settings, get_key, has_key, set_key


def test_settings_defaults_and_cleaning(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"ocr_mode": "laser", "langs": ["ind", "xx"], "runs": -3, "pdf": {"size": "B5", "orient": "port"},
                                "provider": "claude", "models": {"claude": "model-x", "palsu": "y"}, "unknown": 1}))
    s = Settings(path)
    assert s.get("ocr_mode") == "offline"
    assert s.get("langs") == ["ind"]
    assert s.get("runs") == 0
    assert s.get("pdf") == {"size": "A4", "orient": "port", "title": True, "label": True, "text": False}
    assert s.model_for("claude") == "model-x"
    assert s.model_for("gemini") == "gemini-3.8-flash"
    s.update({"out_mode": "combined", "combined_name": "Kajian", "nonsense": True})
    again = Settings(path)
    assert again.get("out_mode") == "combined" and again.get("combined_name") == "Kajian"
    assert "nonsense" not in json.loads(path.read_text())


def test_settings_survive_broken_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{rusak")
    assert Settings(path).get("out_mode") == "separate"


def test_api_key_falls_back_to_file():
    assert not has_key("gemini")
    assert set_key("gemini", "  kunci-rahasia ") == "file"
    assert get_key("gemini") == "kunci-rahasia"
    set_key("gemini", "")
    assert get_key("gemini") == ""


def test_api_key_uses_keyring_when_available(monkeypatch):
    store = {}

    class Ring:
        @staticmethod
        def get_password(service, user):
            return store.get((service, user))

        @staticmethod
        def set_password(service, user, value):
            store[(service, user)] = value

        @staticmethod
        def delete_password(service, user):
            store.pop((service, user), None)

    monkeypatch.setitem(__import__("sys").modules, "keyring", Ring)
    assert set_key("claude", "abc") == "keyring"
    assert store == {(settings.KEYRING_SERVICE, "claude"): "abc"}
    assert get_key("claude") == "abc"


def _png(w=900, h=500) -> bytes:
    from io import BytesIO

    buf = BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.parametrize("size,orient,mm", [("A4", "land", (297, 210)), ("A3", "port", (297, 420)), ("F4", "land", (330, 215))])
def test_pdf_page_sizes(tmp_path, size, orient, mm):
    out = tmp_path / "peta.pdf"
    export.save_pdf(out, _png(), "# Judul\n## Cabang\n- poin **tebal**\n- <b>bukan tag</b>", "Judul", size=size, orient=orient,
                    show_title=True, show_label=True, text_page=True)
    doc = pdfium.PdfDocument(str(out))
    assert len(doc) == 2
    w, h = doc[0].get_size()
    assert abs(w - mm[0] * 72 / 25.4) < 1 and abs(h - mm[1] * 72 / 25.4) < 1
    text = doc[1].get_textpage().get_text_range()
    assert "Cabang" in text and "<b>bukan tag</b>" in text
    doc.close()


def test_html_export_is_offline_and_escaped(tmp_path):
    out = tmp_path / "peta.html"
    export.save_html(out, "# Judul\n- </script><script>alert(1)</script>", "Judul <x>", {"theme": "urai", "levels": ["bad"]}, True)
    page = out.read_text(encoding="utf-8")
    assert 'src="http' not in page and "<link" not in page  # semua pustaka ditanam, bisa dibuka tanpa internet
    assert "<script>alert(1)" not in page
    assert "Judul &lt;x&gt;" in page
    assert '"theme": "urai"' in page and '"levels": ["#1f77b4"' in page  # gaya yang tidak valid diganti bawaan
    assert "Rangkuman AI" in page


def test_png_data_url_validation(tmp_path):
    import base64

    good = "data:image/png;base64," + base64.b64encode(_png(10, 10)).decode()
    export.save_png(tmp_path / "a.png", good)
    assert (tmp_path / "a.png").read_bytes().startswith(b"\x89PNG")
    with pytest.raises(ValueError):
        export.decode_data_url("data:image/png;base64," + base64.b64encode(b"bukan png").decode())
    with pytest.raises(ValueError):
        export.decode_data_url("data:text/html;base64,PGI+")
