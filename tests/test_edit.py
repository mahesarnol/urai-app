"""Menyunting hasil (save_result), menyunting mind map (update_summary), dan menghapus beberapa dokumen (remove_items)."""
import json
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from urai.api import Api
from urai.settings import Settings
from urai.textutil import word_count


@pytest.fixture
def api(tmp_path):
    a = Api(Settings(tmp_path / "settings.json"), dev=True)
    a.save_settings({"custom_dir": str(tmp_path / "out"), "location": "custom", "ocr_mode": "off"})
    return a


def wait_for(api, kind, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        for e in api.poll():
            if e["type"] == kind:
                return e
        time.sleep(0.05)
    raise AssertionError(f"event {kind} tidak datang")


def run(api, samples, *names, **settings):
    if settings:
        api.save_settings(settings)
    api.add_paths([str(samples[n]) for n in names])
    assert api.start()["ok"]
    return wait_for(api, "finished")


class FakeTesseract:
    """Pengganti Tesseract supaya baca ulang hasil scan bisa diuji tanpa programnya."""
    available = True

    def pick_langs(self, wanted):
        return ["ind", "eng"]

    def read(self, img, langs, psm=3):
        return "Teks dari gambar uji"


def test_save_result_separate(api, samples):
    done = run(api, samples, "Notulen Rapat Tim.docx", "Scan Buku Sejarah Kopi.pdf")
    doc, scan = done["items"]
    assert api.summarize(doc["id"], "struct")["ok"] and api.summarize("ALL", "struct")["ok"]
    wait_for(api, "mm")
    edited = "# Notulen baru\r\n\r\nKeputusan: rapat berikutnya hari Senin.\r\n\r\n"
    res = api.save_result(doc["id"], edited)
    clean = "# Notulen baru\n\nKeputusan: rapat berikutnya hari Senin."
    assert res["ok"] and res["name"] == "Notulen Rapat Tim.md" and res["combined_words"] is None
    assert res["words"] == word_count(clean) == next(i for i in res["items"] if i["id"] == doc["id"])["words"]
    assert Path(doc["output"]).read_text(encoding="utf-8") == clean + "\n"
    assert api.result_text(doc["id"]) == clean
    assert not [p for p in Path(doc["output"]).parent.iterdir() if p.suffix == ".tmp"]  # file sementara tidak tertinggal
    # rangkuman lama dokumen ini dan gabungan dibuang; mind map berikutnya memakai teks suntingan
    assert "cached" not in api.summarize(doc["id"], "struct")
    assert "- Keputusan: rapat berikutnya hari Senin." in wait_for(api, "mm")["md"].splitlines()
    assert "cached" not in api.summarize("ALL", "struct")
    # dokumen tanpa file hasil, kunci tidak dikenal, mode yang salah, isi yang bukan teks
    assert api.save_result(scan["id"], "x")["error"] == "This document wasn't saved to a file, so there's nothing to update."
    assert api.save_result("ALL", "x") == {"ok": False, "error": "There's no combined file to save to."}
    assert api.save_result("tidak-ada", "x")["error"] == "This document isn't in the list."
    assert api.save_result(doc["id"], None)["ok"] is False
    api.set_language("id")
    assert api.save_result(scan["id"], "x")["error"] == "Dokumen ini tidak disimpan ke file, jadi tidak ada yang bisa diperbarui."


@pytest.mark.parametrize("exc,expect", [
    (PermissionError(13, "The process cannot access the file"), "No permission to open or save this file"),
    (OSError(28, "No space left on device"), "Couldn't save the file."),
])
def test_save_result_failure_keeps_old_file(api, samples, monkeypatch, exc, expect):
    item = run(api, samples, "Notulen Rapat Tim.docx")["items"][0]
    out = Path(item["output"])
    before = out.read_text(encoding="utf-8")

    def locked(src, dst):
        raise exc

    monkeypatch.setattr("urai.textutil.os.replace", locked)
    res = api.save_result(item["id"], "# teks baru")
    assert res["ok"] is False and res["error"].startswith(expect)
    assert out.read_text(encoding="utf-8") == before and api.result_text(item["id"]) + "\n" == before
    assert not [p for p in out.parent.iterdir() if p.suffix == ".tmp"]


def test_save_result_combined_and_reread_keeps_edits(api, samples, monkeypatch):
    done = run(api, samples, "Notulen Rapat Tim.docx", "Scan Buku Sejarah Kopi.pdf", out_mode="combined")
    doc, scan = done["items"]
    path = Path(done["summary"]["combined_path"])
    assert api.save_result(doc["id"], "x")["error"].startswith("These results were saved as one combined file")
    assert api.summarize("ALL", "struct")["ok"]
    wait_for(api, "mm")
    edited = api.result_text("ALL").replace("# Notulen Rapat Tim.docx", "# Notulen (disunting)") + "\nCatatan tambahan dari pengguna.\n"
    res = api.save_result("ALL", edited)
    assert res["ok"] and res["name"] == path.name == "Combined.md"
    assert res["words"] == res["combined_words"] == word_count(edited)
    assert path.read_text(encoding="utf-8") == api.result_text("ALL") == edited.strip() + "\n"
    # mind map gabungan dibuat ulang dari teks suntingan
    assert "cached" not in api.summarize("ALL", "struct")
    md = wait_for(api, "mm")["md"]
    assert md.startswith("# Combined\n") and "## Notulen (disunting)" in md and "- Catatan tambahan dari pengguna." in md
    # baca ulang scan hanya mengganti bagian scan; suntingan lain tetap ada
    monkeypatch.setattr("urai.convert.engine", lambda: FakeTesseract())
    assert api.reread(scan["id"])["ok"]
    assert wait_for(api, "reread_done")["ok"]
    text = api.result_text("ALL")
    assert "# Notulen (disunting)" in text and "Catatan tambahan dari pengguna." in text
    assert "Teks dari gambar uji" in text and "_(no text could be taken)_" not in text
    assert path.read_text(encoding="utf-8") == text
    # bagian dokumen yang ikut disunting tidak boleh ditimpa diam-diam
    assert api.reread(doc["id"])["error"].startswith("You edited this document's part of the combined file")
    assert "# Notulen (disunting)" in api.result_text("ALL")


def test_update_summary_is_returned_from_cache(api, samples):
    item = run(api, samples, "Notulen Rapat Tim.docx")["items"][0]
    edited = "# Rapat\n## Keputusan\n- Rapat berikutnya hari Senin"
    assert api.update_summary(item["id"], "struct", "poin", edited) == {"ok": True}
    assert api.summarize(item["id"], "struct") == {"ok": True, "cached": True}
    assert wait_for(api, "mm") == {"type": "mm", "state": "done", "key": item["id"], "src": "struct", "kind": "poin", "md": edited}
    # rangkuman AI: jenis lama dinormalkan, disimpan walau belum pernah dibuat, tanpa API key karena dari cache
    assert api.update_summary("ALL", "ai", "laporan", edited + "\r\n")["ok"]
    assert api.summarize("ALL", "ai", "lengkap")["cached"]
    mm = wait_for(api, "mm")
    assert mm["md"] == edited and mm["kind"] == "lengkap" and mm["src"] == "ai"
    assert api.update_summary(item["id"], "lain", "poin", edited) == {"ok": False, "error": "Unknown mind map source."}
    assert api.update_summary(item["id"], "struct", "poin", "  ")["error"] == "The mind map is empty."
    assert api.update_summary("tidak-ada", "struct", "poin", edited)["ok"] is False
    # menyunting teks dokumennya membuang mind map yang disimpan
    assert api.save_result(item["id"], "# Baru\n\nisi baru")["ok"]
    assert "cached" not in api.summarize(item["id"], "struct")


def test_remove_items_ready_and_done(api, samples):
    api.add_samples()
    ids = [i["id"] for i in api.init()["items"]]
    res = api.remove_items([ids[0], ids[2], "tidak-ada"])
    assert res["ok"] and [i["id"] for i in res["items"]] == [ids[1]] + ids[3:]
    assert api.remove_items("bukan daftar")["items"] == res["items"]
    api.clear()
    done = run(api, samples, "Notulen Rapat Tim.docx", "Statistik Perpustakaan.xlsx")
    a, b = done["items"]
    for key in (a["id"], b["id"], "ALL"):
        api.summarize(key, "struct")
    res = api.remove_items([a["id"]])
    assert res == {"ok": True, "items": res["items"]} and [i["id"] for i in res["items"]] == [b["id"]]
    assert Path(a["output"]).exists()  # file hasil di disk tidak pernah dihapus
    assert api.summarize(b["id"], "struct").get("cached") and "cached" not in api.summarize("ALL", "struct")
    assert api.remove_items([b["id"]])["items"] == [] and api.result_text("ALL") == "" and Path(b["output"]).exists()


def test_busy_refusals_in_both_languages(api, samples):
    api.add_samples()
    ids = [i["id"] for i in api.init()["items"]]
    gate = threading.Event()
    api._job = threading.Thread(target=gate.wait, daemon=True)  # seolah konversi sedang berjalan
    api._job.start()
    try:
        assert api.remove_items(ids[:2]) == {"ok": False, "error": "Wait for the current process to finish."}
        assert api.save_result(ids[0], "x") == {"ok": False, "error": "Wait for the current process to finish."}
        api.set_language("id")
        assert api.remove_items(ids[:2]) == {"ok": False, "error": "Tunggu proses selesai dulu."}
        assert len(api.init()["items"]) == len(ids)
    finally:
        gate.set()


def test_devserver_proxies_edit_apis(api, samples):
    from urai.devserver import serve

    httpd = serve(0, open_browser=False, api=api)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def call(name, *args):
        req = urllib.request.Request(f"http://127.0.0.1:{httpd.server_address[1]}/api/{name}", data=json.dumps(list(args)).encode(),
                                     headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req).read())["result"]

    try:
        call("add_paths", [str(samples["Notulen Rapat Tim.docx"])])
        assert call("start")["ok"]
        item = wait_for(api, "finished")["items"][0]
        res = call("save_result", item["id"], "# Judul\n\nisi suntingan")
        assert res["ok"] and res["words"] == 3 and Path(item["output"]).read_text(encoding="utf-8") == "# Judul\n\nisi suntingan\n"
        assert call("update_summary", item["id"], "struct", "poin", "# Judul\n- poin") == {"ok": True}
        assert call("remove_items", [item["id"]]) == {"ok": True, "items": []}
    finally:
        httpd.shutdown()
