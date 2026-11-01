import time
from pathlib import Path

import pytest

from urai.api import Api
from urai.settings import Settings


@pytest.fixture
def api(tmp_path):
    a = Api(Settings(tmp_path / "settings.json"), dev=True)
    a.save_settings({"custom_dir": str(tmp_path / "out"), "location": "custom"})
    return a


def wait_for(api, kind, timeout=120):
    seen = []
    end = time.time() + timeout
    while time.time() < end:
        for e in api.poll():
            seen.append(e)
            if e["type"] == kind:
                return e, seen
        time.sleep(0.05)
    raise AssertionError(f"event {kind} tidak datang; terlihat: {[e['type'] for e in seen]}")


def test_init_shape(api):
    b = api.init()
    assert b["app"]["name"] == "Urai App" and "email" not in b["app"] and "social" not in b["app"]
    assert b["app"]["repo"] == "https://github.com/mahesarnol/urai-app"  # tanpa info rakitan: repo resmi
    assert b["app"]["merchant"] == "Elnola Studio, Digital &"
    assert b["app"]["tagline"] == "Turn documents into clean Markdown text"
    assert set(b["providers"]) == {"claude", "gemini", "deepseek", "openai", "openrouter", "other"}
    assert b["providers"]["other"]["name"] == "Other server (OpenAI-compatible)"
    assert b["tesseract"]["names"]["ind"] == "Indonesian" and b["tesseract"]["names"]["sun"] == "Sundanese"
    assert b["keys"]["gemini"] is False
    assert b["settings"]["ocr_mode"] == "offline"
    assert b["settings"]["lang"] == "en" and b["settings"]["theme"] == "system" and b["settings"]["combined_name"] == ""
    assert b["items"] == [] and b["has_samples"] is True


def test_set_language_relocalizes(api, samples):
    api.add_paths([str(samples["Foto Pengumuman Perpustakaan.jpg"]), str(samples["Scan Buku Sejarah Kopi.pdf"])])
    api.add_link("https://www.bps.go.id/id")
    img, pdf, web = api.init()["items"]
    assert img["meta"].startswith("Image · 1400×800") and pdf["meta"].startswith("PDF · 2 pages")
    assert web["display"] == "Page on bps.go.id" and web["meta"] == "Web page link · bps.go.id"
    assert api.add_link("bukan link")["error"].startswith("Paste the full link")
    res = api.set_language("id")
    assert res["ok"] and set(res) == {"ok", "settings", "items", "app", "providers", "tesseract", "prompt_defaults"}
    assert res["settings"]["lang"] == "id" and Settings(api._settings.path).get("lang") == "id"
    img, pdf, web = res["items"]
    assert img["meta"].startswith("Gambar · 1400×800") and pdf["meta"].startswith("PDF · 2 halaman")
    assert web["display"] == "Halaman bps.go.id" and web["meta"] == "Link halaman web · bps.go.id"
    assert res["app"]["tagline"] == "Urai dokumen jadi teks Markdown yang rapi"
    assert res["providers"]["other"]["name"] == "Server lain (kompatibel OpenAI)"
    assert res["tesseract"]["names"]["eng"] == "Inggris"
    assert api.add_link("bukan link")["error"].startswith("Tempel link")
    assert api.set_language("fr")["ok"] is False and api._settings.get("lang") == "id"
    # save_settings dengan lang juga mengganti bahasa aktif
    api.save_settings({"lang": "en"})
    assert api.init()["items"][0]["meta"].startswith("Image ·")


def test_messages_follow_language(api, samples):
    api.save_settings({"ocr_mode": "off"})
    api.add_paths([str(samples["Scan Buku Sejarah Kopi.pdf"])])
    api.start()
    done, _ = wait_for(api, "finished")
    assert done["items"][0]["message"] == "No readable text because this document is a scan."
    item = api.set_language("id")["items"][0]
    assert item["message"] == "Tidak ada teks terbaca karena dokumen ini hasil scan."
    assert "msg_ref" not in item and "facts" not in item  # bahan terjemahan tidak dikirim ke tampilan
    assert api.start()["ok"] is True
    wait_for(api, "finished")
    assert api.init()["items"][0]["message"].endswith("hasil scan.")


def test_open_links(api, monkeypatch):
    opened = []
    monkeypatch.setattr("urai.api.webbrowser.open", opened.append)
    assert api.open_link("repo") and api.open_link("issues")
    assert opened == ["https://github.com/mahesarnol/urai-app", "https://github.com/mahesarnol/urai-app/issues"]
    assert api.open_link("releases") is False  # rakitan sendiri tidak punya halaman pembaruan
    assert api.open_link("https://contoh.example") is False and len(opened) == 2


def test_combined_name_default_follows_language(api, samples, tmp_path):
    api.save_settings({"ocr_mode": "off", "out_mode": "combined"})
    api.add_paths([str(samples["Notulen Rapat Tim.docx"])])
    api.start()
    done, _ = wait_for(api, "finished")
    assert Path(done["summary"]["combined_path"]).name == "Combined.md"
    text = api.result_text("ALL")
    assert text.startswith("> Combined from 1 document, created ")
    assert api.summarize("ALL", "struct")["ok"]
    mm, _ = wait_for(api, "mm")
    assert mm["md"].startswith("# Combined\n")
    api.set_language("id")
    api.start()
    done, _ = wait_for(api, "finished")
    assert Path(done["summary"]["combined_path"]).name == "Gabungan.md"
    assert api.result_text("ALL").startswith("> Gabungan dari 1 dokumen, dibuat ")
    api.save_settings({"combined_name": "Catatan Tim"})
    api.start()
    done, _ = wait_for(api, "finished")
    assert Path(done["summary"]["combined_path"]).name == "Catatan Tim.md"


def test_list_management(api, samples):
    res = api.add_samples()
    assert res["ok"] and res["added"] == len(samples)
    assert api.add_samples()["added"] == 0  # tidak ada duplikat
    bad = api.add_paths([str(Path(__file__))])
    assert bad["skipped"] == 1
    assert api.add_link("bukan link")["ok"] is False
    link = api.add_link("youtu.be/dQw4w9WgXcQ")
    assert link["ok"] and link["items"][-1]["kind"] == "yt"
    assert api.add_link("https://www.youtube.com/watch?v=dQw4w9WgXcQ")["ok"] is False
    ids = [i["id"] for i in api.init()["items"]]
    rev = api.reorder(list(reversed(ids)))["items"]
    assert [i["id"] for i in rev] == list(reversed(ids))
    left = api.remove_item(ids[0])["items"]
    assert ids[0] not in [i["id"] for i in left]
    assert api.clear()["items"] == []


def test_folder_scan_skips_markdown(api, copy_samples):
    (copy_samples / "hasil lama.md").write_text("# lama")
    (copy_samples / "~$sementara.docx").write_text("x")
    sub = copy_samples / "sub"
    sub.mkdir()
    (sub / "catatan.txt").write_text("catatan")
    res = api._add_paths([str(copy_samples)], from_folder=True)
    names = [i["name"] for i in res["items"]]
    assert "hasil lama.md" not in names and "~$sementara.docx" not in names
    assert "catatan.txt" in names


def test_start_requires_items_and_key(api):
    assert api.start()["ok"] is False
    api.add_samples()
    api.save_settings({"ocr_mode": "ai"})
    res = api.start()
    assert res["ok"] is False and res["open"] == "ai"


def test_run_summarize_export_and_fresh_list(api, tmp_path):
    api.save_settings({"ocr_mode": "off"})
    api.add_paths([str(p) for p in sorted((Path(__file__).parents[1] / "src" / "urai" / "samples").glob("*.docx"))])
    assert api.start()["ok"]
    done, _ = wait_for(api, "finished")
    s = done["summary"]
    assert s["ok"] == 1 and not s["cancelled"] and s["runs"] == 1
    item = done["items"][0]
    assert "Pembahasan" in api.result_text(item["id"])
    out = item["output"]
    assert Path(out).exists()
    # rangkuman struktur dokumen (offline), lalu dari cache
    assert api.summarize(item["id"], "struct")["ok"]
    mm, _ = wait_for(api, "mm")
    assert mm["state"] == "done" and mm["md"].startswith("# Notulen Rapat Tim")
    assert api.summarize(item["id"], "struct")["cached"]
    # rangkuman AI tanpa API key ditolak dengan sopan
    assert api.summarize(item["id"], "ai", "notulen")["open"] == "ai"
    assert api.summarize(item["id"], "ai", "laporan")["error"].startswith("AI summary needs an API key")
    # simpan mind map tanpa jendela dialog: langsung ke folder hasil
    exp = api.export_map("md", {"md": mm["md"], "title": "Notulen: Rapat"})
    assert exp["ok"] and Path(exp["path"]).name == "Notulen Rapat - mind map.md"
    # hanya file buatan aplikasi yang boleh dibuka
    assert api.open_output("/etc/passwd")["ok"] is False
    assert api._allowed(out) and api._allowed(exp["path"])
    # dokumen baru setelah selesai memulai daftar baru
    res = api.add_samples()
    assert res["fresh"] and all(i["status"] == "idle" for i in res["items"])


@pytest.mark.tesseract
def test_reread_after_ocr_off(api, samples, has_tesseract):
    api.save_settings({"ocr_mode": "off"})
    api.add_paths([str(samples["Scan Buku Sejarah Kopi.pdf"])])
    api.start()
    done, _ = wait_for(api, "finished")
    item = done["items"][0]
    assert item["status"] == "warn" and item["fix"] == "ocr" and not item["output"]
    assert api.reread(item["id"])["ok"]
    rr, _ = wait_for(api, "reread_done")
    assert rr["ok"]
    assert "Kaldi" in api.result_text(item["id"])
    fixed = api.init()["items"][0]
    assert fixed["status"] == "done" and Path(fixed["output"]).exists()


def test_set_ai_and_test_connection_without_key(api):
    res = api.set_ai("openrouter", "sk-or-uji", "", None)
    assert res["keys"]["openrouter"] is True and res["settings"]["provider"] == "openrouter"
    assert res["models"]["openrouter"] == "google/gemini-3.5-flash"
    res = api.set_ai("other", "", "model-saya", "http://127.0.0.1:9/v1")
    assert res["models"]["other"] == "model-saya" and res["base_urls"]["other"] == "http://127.0.0.1:9/v1"
    assert api.test_ai("other", "", "", None)["message"] == "Enter an API key first."
    api.set_language("id")
    assert api.test_ai("other", "", "", None)["message"] == "Isi API key dulu."
    assert api.forget_key("openrouter")["keys"]["openrouter"] is False


def test_check_update_without_repo(api):
    assert api.check_update()["ok"] is False


def test_unsupported_drop_keeps_results(api, tmp_path):
    api.save_settings({"ocr_mode": "off"})
    api.add_paths([str(p) for p in (Path(__file__).parents[1] / "src" / "urai" / "samples").glob("*.docx")])
    api.start()
    wait_for(api, "finished")
    exe = tmp_path / "setup.exe"
    exe.write_bytes(b"MZ")
    res = api.add_paths([str(exe)])
    assert not res["fresh"] and res["added"] == 0 and len(res["items"]) == 1
    assert api.result_text(res["items"][0]["id"])  # hasil sebelumnya tetap ada


def test_stored_key_not_sent_to_new_server(api):
    api.set_ai("other", "kunci-rahasia", "model", "http://127.0.0.1:9/v1")
    res = api.test_ai("other", "", "model", "https://contoh-penyerang.example/v1")
    assert res["ok"] is False and "server address changed" in res["message"]


def test_devserver_rejects_cross_site(tmp_path):
    import json
    import threading
    import urllib.error
    import urllib.request

    from urai.devserver import serve

    a = Api(Settings(tmp_path / "s.json"), dev=True)
    httpd = serve(0, open_browser=False, api=a)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}/api/init"
    try:
        for headers in ({"Content-Type": "text/plain"}, {"Content-Type": "application/json", "Origin": "https://jahat.example"}):
            req = urllib.request.Request(base, data=b"[]", headers=headers)
            with pytest.raises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(req)
            assert e.value.code == 403
        ok = urllib.request.urlopen(urllib.request.Request(base, data=b"[]", headers={"Content-Type": "application/json"}))
        assert json.loads(ok.read())["result"]["app"]["name"] == "Urai App"
    finally:
        httpd.shutdown()
