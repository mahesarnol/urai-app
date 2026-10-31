"""Uji tampilan menyeluruh di Chromium lewat server pengembangan (tanpa pywebview).

Jalankan:  URAI_E2E=1 python -m pytest tests/test_e2e.py
Butuh:     pip install playwright && playwright install chromium, serta Tesseract (ind, eng).
Tangkapan layar disimpan ke folder yang ditunjuk URAI_E2E_SHOTS (bila diisi).
"""
import os
import threading
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.tesseract]
if os.environ.get("URAI_E2E") != "1":
    pytest.skip("uji tampilan dilewati (set URAI_E2E=1)", allow_module_level=True)
sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def app_url(tmp_path, has_tesseract):
    from urai.api import Api
    from urai.devserver import serve
    from urai.settings import Settings

    api = Api(Settings(tmp_path / "settings.json"), dev=True)
    api.save_settings({"custom_dir": str(tmp_path / "out"), "location": "custom"})
    httpd = serve(0, open_browser=False, api=api)
    api._dialogs.save_dir = tmp_path / "exports"  # jendela "Simpan sebagai" diganti folder ini
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/index.html?dev=1", tmp_path
    httpd.shutdown()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_full_flow(app_url, scheme):
    url, tmp = app_url
    shots = Path(os.environ["URAI_E2E_SHOTS"]) if os.environ.get("URAI_E2E_SHOTS") else None
    errors = []

    def shot(page, name):
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots / f"{scheme}-{name}.png"))

    state = "document.getElementById('win').dataset.state"
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1180, "height": 800}, color_scheme=scheme)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_selector("#boot", state="hidden")
        assert page.evaluate("document.getElementById('win').dataset.mode") == scheme
        shot(page, "1-empty")

        page.click("#tryDemo")
        page.wait_for_function("document.querySelectorAll('#files .row').length === 6")
        assert "Ubah 6 dokumen" in page.text_content("#goText")
        assert page.locator("#files .tag.scan").count() == 2  # PDF hasil scan dan gambar diberi label
        shot(page, "2-ready")

        page.keyboard.press("Control+Enter")
        page.wait_for_function(f"{state} === 'done'", timeout=180000)
        assert page.locator("#files .st.ok").count() == 6
        shot(page, "3-done")

        # pratinjau berpindah sesuai baris yang dipilih
        page.click("#files .row:has-text('Surat Undangan')")
        page.wait_for_function("document.getElementById('pvBody').textContent.includes('Musyawarah')")
        page.click(".tabs button[data-tab=raw]")
        page.wait_for_function("document.querySelector('#pvBody pre.raw') !== null")

        # mind map dari struktur dokumen, ganti gaya, lalu simpan dalam empat format
        page.click("#files .row:has-text('Notulen')")
        page.click(".tabs button[data-tab=map]")
        page.click("#mmSetup .opt[data-src=struct]")
        page.click("#mmGo")
        page.wait_for_selector("#mmReady:not([hidden])")
        page.wait_for_function("document.querySelectorAll('#mmSvg g.markmap-node').length >= 5")
        page.click("#mmStyleBtn")
        page.click("#stTheme button[data-v=lembut]")
        page.click("#stMode button[data-v=level]")
        page.wait_for_timeout(500)
        shot(page, "4-map-style")
        page.click("#mmStyleClose")
        for fmt in ("md", "html", "png"):
            page.click("#mmSave")
            page.click(f"#mmMenu button[data-f={fmt}]")
            page.wait_for_function(f"document.getElementById('toast').textContent.includes('mind map.{fmt}')", timeout=20000)
        page.click("#mmSave")
        page.click("#mmMenu button[data-f=pdf]")
        page.wait_for_selector("#dlgPdf:not([hidden])")
        page.click("#pdfSize button[data-v=A3]")
        page.click("#pdfOrient button[data-v=port]")
        assert "A3 tegak" in page.text_content("#pdfInfo")
        page.click("#pdfSave")
        page.wait_for_selector("#dlgPdf", state="hidden", timeout=30000)
        exported = sorted(x.suffix for x in (tmp / "exports").iterdir())
        assert exported == [".html", ".md", ".pdf", ".png"]
        png = next((tmp / "exports").glob("*.png")).read_bytes()
        assert png.startswith(b"\x89PNG") and len(png) > 20000

        # dialog utama terbuka dan tertutup dengan Escape
        for btn, dlg in (("#btnSettings", "#dlgSettings"), ("#btnAbout", "#dlgAbout"), ("#btnSupport", "#dlgSupport"), ("#btnHelp", "#dlgHelp")):
            page.click(btn)
            page.wait_for_selector(dlg + ":not([hidden])")
            page.keyboard.press("Escape")
            page.wait_for_selector(dlg, state="hidden")

        # gabung jadi satu dengan urutan baru
        page.click("#backSetup")
        page.wait_for_function(f"{state} === 'ready'")
        page.click(".opt[data-out=combined]")
        page.fill("#cname", "Bahan Kajian Desa")
        page.wait_for_timeout(600)
        page.focus("#files .row:nth-child(2) .grip")
        page.keyboard.press("ArrowUp")
        page.wait_for_function("document.querySelector('#files .row:nth-child(1) .nm').textContent === 'Laporan Pemetaan Sosial 2026.pdf'")
        assert page.evaluate("document.activeElement.closest('.row').dataset.id") == page.get_attribute("#files .row:nth-child(1)", "data-id")
        page.keyboard.press("ArrowDown")  # fokus tetap di pegangan yang sama, jadi bisa dipindah lagi
        page.wait_for_function("document.querySelector('#files .row:nth-child(2) .nm').textContent === 'Laporan Pemetaan Sosial 2026.pdf'")
        page.keyboard.press("ArrowUp")
        page.wait_for_function("document.querySelector('#files .row:nth-child(1) .nm').textContent === 'Laporan Pemetaan Sosial 2026.pdf'")
        page.wait_for_timeout(300)
        assert "Gabungkan 6 dokumen" in page.text_content("#goText")
        page.click("#go")
        page.wait_for_function(f"{state} === 'done'", timeout=180000)
        assert "Bahan Kajian Desa.md" in page.text_content("#outbox")
        combined = (tmp / "out" / "Bahan Kajian Desa.md").read_text(encoding="utf-8")
        assert combined.index("# Laporan Pemetaan") < combined.index("# Foto Papan")
        shot(page, "5-combined")

        # mode Mati: scan perlu dicek, lalu dibaca ulang dari barisnya
        page.click("#backSetup")
        page.click(".opt[data-out=separate]")
        page.click(".mode[data-ocr=off]")
        page.click("#go")
        page.wait_for_function(f"{state} === 'done'", timeout=180000)
        assert page.locator("#files .st.warn").count() == 2
        shot(page, "6-off")
        for left in (1, 0):
            page.click("[data-fix]")
            page.wait_for_function(f"document.querySelectorAll('#files .st.warn').length === {left} && !document.querySelector('#files .st.work')", timeout=60000)
        assert page.locator("#files .st.ok").count() == 6

        # tautan apa pun tidak boleh membuat jendela aplikasi pindah halaman
        before = page.url
        page.evaluate("""() => { const a = document.createElement('a'); a.href = 'https://example.com/'; a.id = 'luar';
                                  a.textContent = 'luar'; document.getElementById('pvBody').prepend(a); }""")
        page.click("#luar")
        page.wait_for_timeout(300)
        assert page.url == before
        browser.close()
    assert not errors, errors
