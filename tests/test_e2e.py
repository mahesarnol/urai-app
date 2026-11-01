"""Uji tampilan menyeluruh di Chromium lewat server pengembangan (tanpa pywebview).

Jalankan:  URAI_E2E=1 python -m pytest tests/test_e2e.py
Butuh:     pip install playwright && playwright install chromium, serta Tesseract (ind, eng).
Tangkapan layar disimpan ke folder yang ditunjuk URAI_E2E_SHOTS (bila diisi).
"""
import json
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
        assert page.evaluate("document.documentElement.lang") == "en"  # bahasa bawaan
        assert "Convert 6 documents" in page.text_content("#goText")
        assert page.locator("#files .tag.scan").count() == 2  # PDF hasil scan dan gambar diberi label
        shot(page, "2-ready")

        page.keyboard.press("Control+Enter")
        page.wait_for_function(f"{state} === 'done'", timeout=180000)
        assert page.locator("#files .st.ok").count() == 6
        shot(page, "3-done")

        # pratinjau berpindah sesuai baris yang dipilih
        page.click("#files .row:has-text('Sejarah Kopi')")
        page.wait_for_function("document.getElementById('pvBody').textContent.includes('Kaldi')")
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
        assert "A3 portrait" in page.text_content("#pdfInfo")
        page.click("#pdfSave")
        page.wait_for_selector("#dlgPdf", state="hidden", timeout=30000)
        exported = sorted(x.suffix for x in (tmp / "exports").iterdir())
        assert exported == [".html", ".md", ".pdf", ".png"]
        png = next((tmp / "exports").glob("*.png")).read_bytes()
        assert png.startswith(b"\x89PNG") and len(png) > 20000

        # edit mind map: ganti nama satu cabang, lalu hapus cabang itu beserta isinya; ekspor memakai hasil edit
        node = "#mmSvg g.markmap-node"
        outline = next((tmp / "exports").glob("*.md")).read_text(encoding="utf-8")
        page.click("#mmEdit")
        page.wait_for_selector("#mmEdBar:not([hidden])")
        nodes = page.locator(node).count()
        page.locator(node).nth(1).locator("foreignObject").click()  # urutan 0 = judul utama
        page.wait_for_selector("#mmNodeEd:not([hidden])")
        assert page.is_visible("#mmDelBranch")
        page.fill("#mmNodeIn", "Cabang uji")
        page.press("#mmNodeIn", "Enter")
        page.wait_for_function("document.getElementById('mmSvg').textContent.includes('Cabang uji')")
        page.locator(node, has_text="Cabang uji").first.locator("foreignObject").click()
        page.wait_for_selector("#mmNodeEd:not([hidden])")
        page.click("#mmDelBranch")
        page.wait_for_function(f"!document.getElementById('mmSvg').textContent.includes('Cabang uji') && document.querySelectorAll('{node}').length < {nodes}")
        shot(page, "4c-map-edited")
        page.click("#mmEdDone")
        page.click("#mmSave")
        page.click("#mmMenu button[data-f=md]")
        page.wait_for_function("document.getElementById('toast').textContent.includes('mind map.md')", timeout=20000)
        edited = max((tmp / "exports").glob("*.md"), key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8")
        assert "Cabang uji" not in edited and len(edited.splitlines()) < len(outline.splitlines())

        # tab Ringkasan tanpa API key: catatannya meminta API key, dan Buat ringkasan membuka Pengaturan › AI
        page.click(".tabs button[data-tab=sum]")
        page.wait_for_selector("#sumPanel:not([hidden]) #sumSetup:not([hidden])")
        assert page.get_attribute("#sumKind button[data-k=sedang]", "aria-pressed") == "true"
        assert "API key" in page.text_content("#sumNote") and page.locator("#sumSetKey").count() == 1
        page.click("#sumGo")
        page.wait_for_selector("#pane-ai:not([hidden])")
        page.keyboard.press("Escape")
        page.wait_for_selector("#dlgSettings", state="hidden")

        # mind map Dari ringkasan: belum ada ringkasan, jadi diminta membuat ringkasan dulu
        page.click(".tabs button[data-tab=map]")
        page.click("#mmRedo")  # kembali ke pilihan sumber
        page.click("#mmSetup .opt[data-src=sum]")
        page.wait_for_selector("#mmMakeSum")
        assert page.is_disabled("#mmGo") and page.is_visible("#mmSumKind") and page.is_hidden("#mmKind")
        page.click("#mmMakeSum")
        page.wait_for_selector("#sumPanel:not([hidden])")
        assert page.get_attribute(".tabs button[data-tab=sum]", "aria-selected") == "true"

        # Pengaturan › Prompt: ubah, tanda Diubah, kembalikan ke bawaan, simpan (tersimpan di settings.json)
        custom, badge = "Fokus pada angka, tanggal, dan keputusan.", "#pane-prompts [data-pk=sedang] .pcustom"
        page.click("#btnSettings")
        page.click("#dTabs button[data-pane=prompts]")
        page.wait_for_selector("#pane-prompts:not([hidden])")
        default = page.input_value("#pr-sedang")
        assert default.strip() and page.is_hidden(badge)
        page.fill("#pr-sedang", custom)
        assert page.is_visible(badge)
        page.click("#pane-prompts [data-reset=sedang]")
        assert page.input_value("#pr-sedang") == default and page.is_hidden(badge)
        page.fill("#pr-sedang", custom)
        page.click("#pSave")
        page.wait_for_selector("#dlgSettings", state="hidden")
        page.wait_for_function("document.getElementById('toast').textContent === 'Prompts saved'")
        for _ in range(20):  # settings.json ditulis Python setelah save_settings
            saved = json.loads((tmp / "settings.json").read_text(encoding="utf-8"))
            if (saved.get("prompts") or {}).get("sedang") == custom:
                break
            page.wait_for_timeout(100)
        assert saved["prompts"]["sedang"] == custom
        page.click("#btnSettings")
        page.click("#dTabs button[data-pane=prompts]")
        assert page.input_value("#pr-sedang") == custom and page.is_visible(badge)
        page.click("#pane-prompts [data-reset=sedang]")
        page.click("#pSave")  # kembalikan ke bawaan untuk langkah berikutnya
        page.wait_for_selector("#dlgSettings", state="hidden")

        # dialog utama terbuka dan tertutup dengan Escape
        for btn, dlg in (("#btnSettings", "#dlgSettings"), ("#btnAbout", "#dlgAbout"), ("#btnSupport", "#dlgSupport"), ("#btnHelp", "#dlgHelp")):
            page.click(btn)
            page.wait_for_selector(dlg + ":not([hidden])")
            page.keyboard.press("Escape")
            page.wait_for_selector(dlg, state="hidden")

        # Pengaturan > Umum: tema dan bahasa langsung berlaku tanpa tombol Simpan
        page.click("#btnSettings")
        page.wait_for_selector("#pane-general:not([hidden])")
        assert page.is_hidden("#dSave") and page.is_visible("#dDone")
        other = "dark" if scheme == "light" else "light"
        page.click(f"#uiTheme button[data-v={other}]")
        assert page.evaluate("document.getElementById('win').dataset.mode") == other
        page.click("#uiTheme button[data-v=system]")
        assert page.evaluate("document.getElementById('win').dataset.mode") == scheme
        page.click("#uiLang button[data-v=id]")
        page.wait_for_function("document.documentElement.lang === 'id'")
        page.wait_for_function("document.getElementById('resMeta').textContent.includes('berhasil')")
        assert page.text_content("#btnHelp").strip() == "Panduan"
        assert page.locator("#btnHelp svg").count() == 1  # ikon tidak hilang saat teks diganti
        shot(page, "4b-settings-id")
        page.click("#uiLang button[data-v=en]")
        page.wait_for_function("document.documentElement.lang === 'en'")
        page.keyboard.press("Escape")
        page.wait_for_selector("#dlgSettings", state="hidden")

        # Pengaturan > Baca offline: pilihan mesin PDF; tidak ada unduhan sungguhan (konfirmasi dijawab "Nanti saja")
        page.click("#btnSettings")
        page.click("#dTabs button[data-pane=offline]")
        page.wait_for_selector("#engField:not([hidden])")
        assert page.text_content("#engSeg").strip() == "Standard (fast)Accurate (Docling)"
        assert page.get_attribute("#engSeg button[data-v=standard]", "aria-pressed") == "true"
        if page.locator("#engBox [data-eng=dl]").count():  # mesin akurat belum terpasang di komputer uji
            assert "installed yet" in page.text_content("#engBox")
            assert "Download (about" in page.text_content("#engBox [data-eng=dl]")
            page.click("#engSeg button[data-v=docling]")
            page.wait_for_selector("#engBox [data-eng=get]")
            assert "one-time download" in page.text_content("#engBox")
            page.click("#engBox [data-eng=no]")
            assert page.get_attribute("#engSeg button[data-v=standard]", "aria-pressed") == "true"
            assert page.locator("#engBox [data-eng=dl]").count() == 1
            assert "PDF: accurate" not in page.text_content("#sbMid")
        page.keyboard.press("Escape")
        page.wait_for_selector("#dlgSettings", state="hidden")

        # gabung jadi satu dengan urutan baru
        page.click("#backSetup")
        page.wait_for_function(f"{state} === 'ready'")
        page.click(".opt[data-out=combined]")
        page.fill("#cname", "Bahan Klub Baca")
        page.wait_for_timeout(600)
        page.focus("#files .row:nth-child(2) .grip")
        page.keyboard.press("ArrowUp")
        page.wait_for_function("document.querySelector('#files .row:nth-child(1) .nm').textContent === 'Foto Pengumuman Perpustakaan.jpg'")
        assert page.evaluate("document.activeElement.closest('.row').dataset.id") == page.get_attribute("#files .row:nth-child(1)", "data-id")
        page.keyboard.press("ArrowDown")  # fokus tetap di pegangan yang sama, jadi bisa dipindah lagi
        page.wait_for_function("document.querySelector('#files .row:nth-child(2) .nm').textContent === 'Foto Pengumuman Perpustakaan.jpg'")
        page.keyboard.press("ArrowUp")
        page.wait_for_function("document.querySelector('#files .row:nth-child(1) .nm').textContent === 'Foto Pengumuman Perpustakaan.jpg'")
        page.wait_for_timeout(300)
        assert "Combine 6 documents" in page.text_content("#goText")
        page.click("#go")
        page.wait_for_function(f"{state} === 'done'", timeout=180000)
        assert "Bahan Klub Baca.md" in page.text_content("#outbox")
        combined = (tmp / "out" / "Bahan Klub Baca.md").read_text(encoding="utf-8")
        assert combined.index("# Foto Pengumuman") < combined.index("# Bab 1")
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

        # edit hasil di Tampilan: ganti satu bagian, simpan, lalu file .md di disk harus sama persis dengan draf
        mark = "# Notulen yang diedit"
        page.click("#files .row:has-text('Notulen') .ftxt")
        page.click("#edBtn")
        page.wait_for_selector("#pvBody .md.editing .eb")
        page.click(".tabs button[data-tab=raw]")
        original = page.input_value("#edRaw")
        page.click(".tabs button[data-tab=view]")
        block = page.locator("#pvBody .eb").first
        start, end = map(int, block.get_attribute("data-l").split(","))
        block.hover()
        block.locator("[data-eb=edit]").click()
        page.fill("#pvBody .ebta", mark)
        page.keyboard.press("Control+Enter")
        page.wait_for_selector("#edBar.dirty")
        page.click("#files .row:has-text('Bab 1') .ftxt")  # pindah dokumen ditahan selama ada perubahan
        assert "Save or discard" in page.text_content("#toast")
        page.click("#edSave")
        page.wait_for_function("document.getElementById('toast').textContent.startsWith('Saved to')")
        lines = original.split("\n")
        lines[start:end] = [mark]
        saved = [p for p in (tmp / "out").glob("*.md") if mark in p.read_text(encoding="utf-8")]
        assert len(saved) == 1 and saved[0].read_text(encoding="utf-8").strip() == "\n".join(lines).strip()
        page.click("#edDone")

        # pilih dua baris lalu hapus dari daftar; file di komputer tidak ikut terhapus
        files_on_disk = sorted(p.name for p in (tmp / "out").iterdir())
        page.check("#files .row:nth-child(1) .pick")
        page.check("#files .row:nth-child(2) .pick")
        assert page.text_content("#pickCount") == "2 selected"
        page.click("#rmPicked")
        page.wait_for_function("document.querySelectorAll('#files .row').length === 4")
        assert sorted(p.name for p in (tmp / "out").iterdir()) == files_on_disk

        # tautan apa pun tidak boleh membuat jendela aplikasi pindah halaman
        before = page.url
        page.evaluate("""() => { const a = document.createElement('a'); a.href = 'https://example.com/'; a.id = 'luar';
                                  a.textContent = 'luar'; document.getElementById('pvBody').prepend(a); }""")
        page.click("#luar")
        page.wait_for_timeout(300)
        assert page.url == before
        browser.close()
    assert not errors, errors
