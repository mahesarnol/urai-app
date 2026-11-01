"""Rangkuman teks (tab Rangkuman), instruksi AI yang bisa disunting, dan mind map dari rangkuman."""
import json
import threading
import time
from pathlib import Path

import pytest

from urai import ai as ai_mod
from urai.api import Api
from urai.settings import Settings
from urai.summarize import PROMPT_LIMIT, notes_prompt, prompt_defaults, system_prompt

SHORT_EN = ("Summary type: Short. Write one paragraph of 3 to 5 sentences that captures what the document is about, its most "
            "important facts or numbers, and its conclusion. Only include what is actually in the document, and keep numbers, "
            "dates, and names exactly as written. Ignore ads, subscribe prompts, promotional contacts, social media links, and "
            "keyword lists.")


@pytest.fixture
def api(tmp_path, samples):
    a = Api(Settings(tmp_path / "settings.json"), dev=True)
    a.save_settings({"custom_dir": str(tmp_path / "out"), "ocr_mode": "off"})
    a.add_paths([str(samples["Notulen Rapat Tim.docx"]), str(samples["Statistik Perpustakaan.xlsx"])])
    assert a.start()["ok"]
    wait_for(a, "finished")
    return a


def wait_for(api, kind, timeout=30, **match):
    end = time.time() + timeout
    while time.time() < end:
        for e in api.poll():
            if e["type"] == kind and all(e.get(k) == v for k, v in match.items()):
                return e
        time.sleep(0.02)
    raise AssertionError(f"event {kind} {match} tidak datang")


class FakeAI:
    """Pengganti ai.chat: mencatat perintah dan menjawab teks tetap (atau menunggu / gagal bila diminta)."""

    def __init__(self, answer="Ringkasan.", fail=None, gate=None):
        self.calls, self.answer, self.fail, self.gate = [], answer, fail, gate

    def __call__(self, cfg, system, user):
        self.calls.append((system, user))
        if self.gate is not None:
            self.gate.wait(10)
        if self.fail:
            raise self.fail
        return self.answer


def ids(api):
    return [i["id"] for i in api.init()["items"]]


def test_prompt_assembly_and_defaults():
    defaults = prompt_defaults("en")
    assert set(defaults) == {"poin", "notulen", "lengkap", "singkat", "sedang", "rinci"}
    assert defaults["singkat"] == SHORT_EN
    assert prompt_defaults("id")["sedang"].startswith("Jenis ringkasan: Sedang.")
    # rangkuman teks: instruksi (bawaan atau buatan pengguna) + aturan tetap
    base = system_prompt("sedang", "en")
    assert base.startswith(defaults["sedang"]) and "Write the summary in English." in base
    assert "Output only the summary in Markdown" in base and '"Here is the summary"' in base
    custom = system_prompt("sedang", "en", {"sedang": "  Tulis dua kalimat saja.  "})
    assert custom.startswith("Tulis dua kalimat saja.\n\nRequired output:") and defaults["sedang"] not in custom
    assert "Write the summary in English." in custom  # aturan tetap selalu ditambahkan
    assert "Tulis ringkasan" not in custom and "Tulis rangkuman dalam Bahasa Indonesia." in system_prompt("sedang", "id")
    assert '"Berikut rangkumannya"' in system_prompt("rinci", "id", {"rinci": "Custom"})
    # mind map: aturan isi pindah ke instruksi yang bisa disunting, bentuk kerangka dan bahasa tetap
    mm = system_prompt("poin", "en", {"poin": "My own branches."})
    assert mm.startswith("My own branches.") and "Only include what is actually in the document" not in mm
    assert "Write the mind map outline in English." in mm and "Output only a Markdown mind map outline" in mm
    assert "Only include what is actually in the document" in system_prompt("poin", "en")  # ada di instruksi bawaan
    assert "Tulis kerangka mind map dalam Bahasa Indonesia." in system_prompt("notulen", "id", {"notulen": "x"})
    assert system_prompt("singkat", "en", {"singkat": "a" * 5000}).startswith("a" * PROMPT_LIMIT + "\n\n")
    # catatan potongan dokumen panjang tetap internal
    assert notes_prompt("singkat", "en") == notes_prompt("sedang", "en") == notes_prompt("poin", "en")
    assert notes_prompt("rinci", "id") == notes_prompt("lengkap", "id")
    for lang in ("en", "id"):
        for kind in defaults:
            assert "{" not in system_prompt(kind, lang)


def test_settings_prompts_sum_kind_and_mm_src(tmp_path):
    path = tmp_path / "s.json"
    s = Settings(path)
    assert s.get("sum_kind") == "sedang" and s.get("prompts") == {} and s.get("mm_src") == ""
    s.update({"prompts": {"sedang": " x ", "bogus": "y", "poin": "  ", "rinci": 5, "singkat": "a" * 5000},
              "sum_kind": "rinci", "mm_src": "sum"})
    again = Settings(path)
    assert again.get("prompts") == {"sedang": "x", "singkat": "a" * PROMPT_LIMIT}
    assert again.get("sum_kind") == "rinci" and again.get("mm_src") == "sum"
    s.update({"prompts": {"rinci": "z"}})  # seluruh isi diganti
    assert Settings(path).get("prompts") == {"rinci": "z"}
    s.update({"prompts": "bukan dict", "sum_kind": "puisi", "mm_src": "lain"})
    assert (s.get("prompts"), s.get("sum_kind"), s.get("mm_src")) == ({}, "sedang", "")
    a = Api(s, dev=True)
    assert a.init()["prompt_defaults"]["rinci"].startswith("Summary type: Detailed.")
    assert a.set_language("id")["prompt_defaults"]["rinci"].startswith("Jenis ringkasan: Rinci.")


def test_summarize_text_flow(api, monkeypatch):
    doc, xls = ids(api)
    res = api.summarize_text(doc, "sedang")
    assert res == {"ok": False, "error": "Summaries are written by AI and need an API key. Add it in Settings.", "open": "ai"}
    api.set_ai("gemini", "kunci-uji")
    api.save_settings({"prompts": {"sedang": "Tulis singkat sekali."}})
    fake = FakeAI("```markdown\nRapat membahas **jadwal**.\n\n\n\n- Poin satu\n```")
    monkeypatch.setattr(ai_mod, "chat", fake)
    assert api.summarize_text(doc, "sedang") == {"ok": True, "cached": False}
    done = wait_for(api, "sum", state="done")
    assert done == {"type": "sum", "state": "done", "key": doc, "kind": "sedang", "md": "Rapat membahas **jadwal**.\n\n- Poin satu",
                    "words": 5}
    system, user = fake.calls[-1]
    assert system.startswith("Tulis singkat sekali.\n\n") and "Write the summary in English." in system
    assert user.startswith("Document title: Notulen Rapat Tim\n")
    # dari cache: event done dikirim lagi tanpa memanggil AI
    n = len(fake.calls)
    assert api.summarize_text(doc, "sedang") == {"ok": True, "cached": True}
    assert wait_for(api, "sum", state="done")["md"] == done["md"] and len(fake.calls) == n
    # seluruh daftar, jenis yang tidak dikenal menjadi "sedang"
    assert api.summarize_text("ALL", "aneh")["ok"]
    assert wait_for(api, "sum", state="done", key="ALL")["kind"] == "sedang"
    assert "=== Document 1: Notulen Rapat Tim ===" in fake.calls[-1][1]
    assert api.summarize_text("tidak-ada", "singkat")["ok"] is False
    # gagal: event error dengan pesan yang mudah dipahami
    AuthenticationError = type("AuthenticationError", (Exception,), {})
    monkeypatch.setattr(ai_mod, "chat", FakeAI(fail=AuthenticationError("401")))
    assert api.summarize_text(xls, "singkat")["ok"]
    err = wait_for(api, "sum", state="error")
    assert err == {"type": "sum", "state": "error", "key": xls, "kind": "singkat",
                   "error": "The API key was rejected. Check the API key in Settings."}
    # lupakan, lalu dibuat ulang
    assert api.forget_text_summary(doc, "sedang") is True
    monkeypatch.setattr(ai_mod, "chat", fake)
    assert api.summarize_text(doc, "sedang")["cached"] is False
    wait_for(api, "sum", state="done", key=doc)


def test_cancel_text_summary(api, monkeypatch):
    doc, _ = ids(api)
    api.set_ai("gemini", "kunci-uji")
    gate = threading.Event()
    monkeypatch.setattr(ai_mod, "chat", FakeAI("Hasil yang tidak boleh dipakai.", gate=gate))
    assert api.summarize_text(doc, "rinci")["ok"]
    assert wait_for(api, "sum", state="progress")["kind"] == "rinci"
    assert api.cancel_text_summary() is True
    gate.set()
    api._sum_thread.join(10)
    assert not [e for e in api.poll() if e["type"] == "sum" and e["state"] in ("done", "error")]
    assert api.summarize_text(doc, "rinci")["cached"] is False  # tidak ada yang tersimpan


def test_mind_map_from_summary(api, monkeypatch):
    doc, _ = ids(api)
    assert api.summarize(doc, "sum", "sedang") == {"ok": False, "error": "Create a summary first in the Summary tab.", "need": "sum"}
    api.set_language("id")
    assert api.summarize(doc, "sum", "sedang")["error"] == "Buat ringkasan dulu di tab Ringkasan."
    api.set_language("en")
    api.set_ai("gemini", "kunci-uji")
    summary = ("Dokumen membahas rapat tim. Rapat memutuskan jadwal baru.\n\n**Key points**\n\n- Jadwal baru hari Senin\n"
               "- Anggaran naik 5%")
    monkeypatch.setattr(ai_mod, "chat", FakeAI(summary))
    api.summarize_text(doc, "sedang")
    wait_for(api, "sum", state="done")
    assert api.summarize(doc, "sum", "sedang") == {"ok": True}
    mm = wait_for(api, "mm", state="done")
    assert mm["src"] == "sum" and mm["kind"] == "sedang" and mm["key"] == doc
    # setiap kalimat jadi satu poin; poin sebelum sub-judul dinaikkan jadi cabang supaya tidak hilang di markmap
    assert mm["md"].splitlines() == ["# Notulen Rapat Tim", "## Dokumen membahas rapat tim.", "## Rapat memutuskan jadwal baru.",
                                     "## Key points", "- Jadwal baru hari Senin", "- Anggaran naik 5%"]
    assert api.summarize(doc, "sum", "sedang") == {"ok": True, "cached": True}
    assert api.summarize(doc, "sum", "singkat")["need"] == "sum"  # jenis lain belum dibuat
    # mind map dari rangkuman bisa disunting, lalu dikembalikan dari cache
    assert api.update_summary(doc, "sum", "sedang", "# Edit\n- satu") == {"ok": True}
    api.poll()  # buang event dari panggilan sebelumnya
    api.summarize(doc, "sum", "sedang")
    assert wait_for(api, "mm", state="done")["md"] == "# Edit\n- satu"
    assert api.forget_summary(doc, "sum", "sedang") and api.summarize(doc, "sum", "sedang") == {"ok": True}
    # melupakan rangkuman teks ikut membuang mind map yang dibuat darinya
    api.forget_text_summary(doc, "sedang")
    assert api.summarize(doc, "sum", "sedang")["need"] == "sum"


def test_export_summary_names(api, tmp_path):
    res = api.export_summary({"md": "# Ringkasan\n\nisi", "title": "Notulen: Rapat", "kind": "sedang"})
    assert res["ok"] and res["name"] == "Notulen Rapat - summary.md"
    assert Path(res["path"]).read_text(encoding="utf-8") == "# Ringkasan\n\nisi\n" and api._allowed(res["path"])
    assert api.export_summary({"md": "x"})["name"] == "Summary - summary.md"
    api.set_language("id")
    assert api.export_summary({"md": "x", "title": "Notulen: Rapat"})["name"] == "Notulen Rapat - ringkasan.md"
    assert api.export_summary({"md": "x"})["name"] == "Ringkasan - ringkasan.md"

    class Dialogs:
        answer = ""

        def save_file(self, directory, filename, file_type):
            Dialogs.seen = (filename, file_type)
            return Dialogs.answer

    api._dialogs = Dialogs()
    assert api.export_summary({"md": "x", "title": "A"}) == {"ok": False, "cancelled": True}
    assert Dialogs.seen == ("A - ringkasan.md", "Markdown (*.md)")
    blocker = tmp_path / "bukan-folder"
    blocker.write_text("x")
    Dialogs.answer = str(blocker / "hasil")  # folder tujuan ternyata sebuah file
    res = api.export_summary({"md": "x", "title": "A"})
    assert res["ok"] is False and res["error"]
    Dialogs.answer = str(tmp_path / "pilihan" / "nama tanpa akhiran")
    assert api.export_summary({"md": "x"})["name"] == "nama tanpa akhiran.md"


def test_edits_and_removal_drop_text_summaries(api, monkeypatch):
    doc, xls = ids(api)
    api.set_ai("gemini", "kunci-uji")
    monkeypatch.setattr(ai_mod, "chat", FakeAI("Satu kalimat ringkasan."))
    for key in (doc, xls, "ALL"):
        api.summarize_text(key, "singkat")
        wait_for(api, "sum", state="done", key=key)
        assert api.summarize(key, "sum", "singkat")["ok"]
    assert api.save_result(doc, "# Baru\n\nisi suntingan")["ok"]
    assert api.summarize_text(doc, "singkat")["cached"] is False
    wait_for(api, "sum", state="done", key=doc)
    assert api.summarize_text(xls, "singkat")["cached"] is True  # dokumen lain tidak terpengaruh
    assert api.summarize("ALL", "sum", "singkat")["need"] == "sum"  # gabungan ikut berubah
    assert api.summarize_text("ALL", "singkat")["cached"] is False
    wait_for(api, "sum", state="done", key="ALL")
    assert api.remove_items([xls])["ok"]
    assert api.summarize(xls, "sum", "singkat")["need"] == "sum"
    assert api.summarize_text("ALL", "singkat")["cached"] is False
    json.dumps(api.init())  # semua jawaban tetap bisa dikirim sebagai JSON
