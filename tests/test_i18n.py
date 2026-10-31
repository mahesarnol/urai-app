"""Teks dua bahasa: kunci lengkap di kedua bahasa dan semua kunci yang dipakai kode memang ada."""
import re
import string
from datetime import datetime
from pathlib import Path

from urai import errors, i18n
from urai.fileinfo import BADGE, KIND_BY_EXT
from urai.i18n import STRINGS, fmt_date, fmt_num, t
from urai.ocr import LANG_CODES

SRC = Path(__file__).resolve().parents[1] / "src" / "urai"


def _fields(value) -> set[str]:
    forms = value if isinstance(value, tuple) else (value,)
    return {f for form in forms for _, f, _, _ in string.Formatter().parse(form) if f}


def test_same_keys_and_placeholders():
    assert set(STRINGS) == set(i18n.LANGS) and i18n.DEFAULT == "en"
    assert set(STRINGS["en"]) == set(STRINGS["id"])
    for key, en in STRINGS["en"].items():
        idv = STRINGS["id"][key]
        assert _fields(en) == _fields(idv), key
        if isinstance(en, tuple) or isinstance(idv, tuple):
            assert "n" in _fields(en), key  # bentuk tunggal/jamak dipilih dari n
        assert all(s.strip() for s in (en if isinstance(en, tuple) else (en,))), key


def test_every_key_used_in_code_exists():
    groups = {k.split(".")[0] for k in STRINGS["en"]}
    # teks berbentuk kunci, kecuali kunci dict (mis. "kind.poin": di perintah AI summarize.PROMPTS)
    literal = re.compile(r"[\"']((?:%s)\.[a-z_]+)[\"'](?!\s*:)" % "|".join(sorted(groups)))
    used = set()
    for p in SRC.glob("*.py"):
        if p.name == "i18n.py":
            continue
        code = p.read_text(encoding="utf-8")
        used |= set(re.findall(r"\bt\(\s*[\"']([\w.]+)[\"']", code))  # t("kunci", ...)
        used |= set(literal.findall(code))  # kunci yang disimpan dulu, mis. it.say("msg.empty") atau "err.ffmpeg"
    assert len(used) > 50
    missing = sorted(k for k in used if k not in STRINGS["en"])
    assert not missing
    # kunci yang disusun dari variabel
    dynamic = {f"kind.{k}" for k in set(KIND_BY_EXT.values()) | set(BADGE)} | {f"lang.{c}" for c in LANG_CODES}
    dynamic |= set(errors._BY_NAME.values()) | {f"dlg.{f}" for f in ("md", "html", "png", "pdf")}
    assert not sorted(k for k in dynamic if k not in STRINGS["en"])


def test_plural_numbers_and_dates():
    assert t("meta.pages", n=1) == "1 page" and t("meta.pages", n=2) == "2 pages" and t("meta.pages", n=0) == "0 pages"
    assert t("api.list_full", n=1500) == "The list is full (1,500 documents)."
    assert fmt_num(1240.5, 1) == "1,240.5" and fmt_date(datetime(2026, 10, 31, 9, 5), True) == "2026-10-31 09:05"
    assert t("tidak.ada") == "tidak.ada"  # kunci yang hilang tidak membuat aplikasi macet
    assert i18n.set_lang("xx") == "en"
    i18n.set_lang("id")
    assert i18n.get_lang() == "id"
    assert t("meta.pages", n=1) == "1 halaman" and t("api.list_full", n=1500) == "Daftar sudah penuh (1.500 dokumen)."
    assert fmt_num(1240.5, 1) == "1.240,5" and fmt_date(datetime(2026, 10, 31, 9, 5), True) == "31-10-2026 09.05"
    assert fmt_date(datetime(2026, 10, 31)) == "31-10-2026"
