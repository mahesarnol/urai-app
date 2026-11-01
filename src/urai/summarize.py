"""Rangkuman untuk mind map: struktur dokumen (offline) atau rangkuman AI (Poin utama, Notulen, Ringkas lengkap)."""
from __future__ import annotations

import re
import threading
from typing import Callable

from . import ai as ai_mod
from .errors import Cancelled
from .i18n import get_lang, t
from .textutil import base_name

Progress = Callable[[str], None]

KINDS = ("poin", "notulen", "lengkap")         # jenis mind map AI; nama tampilannya diatur tampilan
SUM_KINDS = ("singkat", "sedang", "rinci")    # jenis rangkuman teks (tab Rangkuman)
PROMPT_KINDS = KINDS + SUM_KINDS              # jenis yang instruksinya bisa disunting pengguna
LEGACY_KINDS = {"umum": "poin", "laporan": "lengkap"}  # nilai lama di pengaturan


def clean_kind(kind) -> str:
    kind = LEGACY_KINDS.get(kind, kind)
    return kind if kind in KINDS else "poin"

# ---------- struktur dokumen (offline) ----------

_FIRST_SENTENCE = re.compile(r"^.*?[.!?](?=\s|$)")
# Penanda daftar, termasuk simbol bullet dari PDF hasil ekspor Word (\uf0b7 dan kawan-kawan).
_BULLET = re.compile(r"^(?:[-*+\u2022\u25cf\u25aa\u25a0\u25e6\u2023\u2219\uf0b7\uf0a7\uf076\uf0d8\uf0fc]|\d+[.)])\s+(.*)$")
_NUM_HEAD = re.compile(r"^((?:\d+\.)*\d+)\.?\s+([A-Z\u00c0-\u024f].*)$")
_MD_INLINE = re.compile(r"\*\*|__|(?<!\w)_(?!\s)|(?<!\s)_(?!\w)")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")


def _inline_text(text: str) -> str:
    """Teks polos: tanpa tanda tebal/miring, tautan dijadikan teks (mind map tidak boleh berisi tautan)."""
    return _LINK.sub(r"\1", _MD_INLINE.sub("", text)).strip()


def _short(text: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 2].rstrip() + "…"


def _first_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    m = _FIRST_SENTENCE.match(text)
    return _short(m.group(0) if m else text)


def _is_caps_heading(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return 4 <= len(line) <= 60 and len(line.split()) >= 2 and len(letters) >= 4 and all(c.isupper() for c in letters)


def promote_orphans(md: str) -> str:
    """markmap membuang poin yang berada di antara sebuah judul dan sub-judul pertamanya
    (mis. "# A / - x / ## B": poin x hilang). Poin seperti itu dijadikan judul satu tingkat di bawahnya."""
    lines = md.split("\n")
    heads = [(i, len(m.group(1))) for i, l in enumerate(lines) if (m := re.match(r"^(#{1,6})\s", l))]
    owner: dict[int, int] = {}
    for k, (idx, level) in enumerate(heads):
        nxt = heads[k + 1] if k + 1 < len(heads) else None
        if nxt and nxt[1] > level:
            for j in range(idx + 1, nxt[0]):
                owner[j] = level
    out = []
    for j, line in enumerate(lines):
        if j in owner:
            m = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
            if m:
                if len(m.group(1).replace("\t", "  ")) < 2:
                    out.append("#" * min(6, owner[j] + 1) + " " + m.group(2))
                else:
                    out.append(line[2:] if line.startswith("  ") else line.lstrip("\t"))
                continue
        out.append(line)
    return "\n".join(out)


def _flat_title_index(lines: list[str]) -> int | None:
    """Baris judul pembuka yang sebenarnya judul dokumen: judul pertama, belum ada isi sebelumnya,
    tidak bernomor, dan langsung disusul judul lain."""
    content = [(i, l.strip()) for i, l in enumerate(lines)
               if l.strip() and not l.strip().startswith(("<!--", ">")) and not re.fullmatch(r"[-*_]{3,}", l.strip())]
    if len(content) < 2:
        return None
    (i, first), (_, second) = content[0], content[1]
    m = re.match(r"^#{1,6}\s+(.*)$", first)
    if not m or _NUM_HEAD.match(_inline_text(m.group(1))) or not re.match(r"^#{1,6}\s+\S", second):
        return None
    return i


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9À-ɏ])")
_LABEL_LINE = re.compile(r"^(?:(\*\*|__)(.+?)\1:?|([^.!?]{2,60}):)$")  # "**Poin penting**" atau "Poin penting:"


def struct_outline(title: str, md: str, nested: bool = False, sentences: bool = False) -> str:
    """Kerangka mind map dari judul, daftar, dan tabel di dokumen, tanpa internet.

    Dokumen dengan beberapa judul tingkat 1 (Word, PowerPoint) memakai judul itu sebagai cabang utama.
    Untuk teks tanpa tanda judul sama sekali (mis. PDF), judul bernomor seperti "2. Analisis" dan baris
    berhuruf kapital dianggap judul, dan baris yang terpotong di tengah kalimat digabung lagi.
    sentences=True (mind map dari rangkuman teks): setiap kalimat paragraf jadi satu poin, bukan hanya kalimat
    pertama, dan baris label seperti "**Poin penting**" atau "Poin penting:" jadi cabang.
    """
    name = base_name(title)
    shift = 1 if nested else 0
    lines = (md or "").splitlines()
    heads = [len(m.group(1)) for m in (re.match(r"^\s*(#{1,6})\s+\S", l) for l in lines) if m]
    structured = bool(heads)
    h1_count = heads.count(1)
    # Beberapa judul tingkat 1 berarti itu bab, bukan judul dokumen. Satu judul tingkat 1 hanya dianggap
    # judul dokumen bila ia judul pertama; bila muncul setelah judul lain, ia bab dan tidak boleh hilang.
    md_shift = 1 if h1_count >= 2 or (h1_count == 1 and heads[0] != 1) else 0
    # Mesin PDF teliti (Docling) menulis semua judul di satu tingkat (##), termasuk judul dokumen dan sub-bab.
    # Tingkat sebenarnya diambil dari nomornya ("3.1 ..."), dan judul pembuka tanpa isi dianggap judul dokumen.
    flat = len(heads) >= 2 and len(set(heads)) == 1 and heads[0] >= 2
    title_at = _flat_title_index(lines) if flat else None
    num_depth = 0          # kedalaman judul bernomor terakhir (mode flat)
    nodes: list[list] = []  # [jenis, teks]; jenis: h<level> | item | para
    in_code = False
    table = False          # sedang di dalam (atau di sela-sela potongan) tabel
    last = None            # jenis node terakhir yang masih bisa disambung
    prev_len = 0
    seen_text = False
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith("```") or line.startswith("~~~"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line:
            last, table = None, False
            continue
        if line.startswith(">") or line.startswith("<!--") or re.fullmatch(r"[-*_]{3,}", line):
            last = None
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level, text = len(m.group(1)) + md_shift, _inline_text(m.group(2))
            if flat:
                if idx == title_at or (not seen_text and text.lower() == name.lower()):
                    last, table, seen_text = None, False, True
                    continue
                num = _NUM_HEAD.match(text)
                if num:
                    num_depth = num.group(1).count(".") + 1
                    level = 1 + num_depth
                else:  # judul tanpa nomor di bawah sub-bab bernomor ("3.2 ...") adalah bagiannya
                    level = num_depth + 2 if num_depth >= 2 else 2
            if level > 1 and text:
                nodes.append([f"h{min(6, level + shift)}", _short(text, 120)])
            last, table, seen_text = None, False, True
            continue
        if re.match(r"^\|\s*:?-{2,}", line):
            table = True
            continue
        if line.startswith("|"):
            cells = [_inline_text(c) for c in line.strip("|").split("|")]
            if not table:
                table, last = True, None  # baris pertama tabel adalah judul kolom
                continue
            rest = " · ".join(c for c in cells[1:] if c)
            nodes.append(["item", cells[0] + (": " + rest if rest else "")])
            last, prev_len = "item", len(line)
            continue
        if re.fullmatch(r"!?\[.*\]\(.*\)", line):
            continue  # baris yang hanya berisi gambar atau tautan
        if sentences and (lm := _LABEL_LINE.match(line)) and not _BULLET.match(line):
            nodes.append([f"h{2 + shift}", _short(_inline_text(lm.group(2) or lm.group(3)), 120)])
            last, table, seen_text = None, False, True
            continue
        plain = _inline_text(line)
        if not plain:
            continue
        if last and nodes and plain[:1].islower():  # lanjutan kalimat atau sel tabel yang terpotong
            nodes[-1][1] += " " + plain
            prev_len = len(plain)
            continue
        table = False
        if not seen_text and plain.lower() == name.lower():
            seen_text = True  # judul dokumen yang tertulis lagi di baris pertama
            continue
        seen_text = True
        if not structured:
            m = _NUM_HEAD.match(plain)
            if m and len(plain) <= 80 and not re.search(r"[.,;:]$", plain):
                depth = m.group(1).count(".") + 1
                nodes.append([f"h{min(6, 1 + depth + shift)}", _short(plain, 120)])
                last = None
                continue
            if _is_caps_heading(plain):
                nodes.append([f"h{2 + shift}", _short(plain, 120)])
                last = None
                continue
        m = _BULLET.match(plain)
        if m:
            nodes.append(["item", m.group(1)])
            last, prev_len = "item", len(plain)
            continue
        if last == "para" and prev_len >= 55 and not re.search(r"[.!?:;]$", nodes[-1][1]):
            nodes[-1][1] += " " + plain  # baris panjang yang terpotong di tengah kalimat
            prev_len = len(plain)
            continue
        nodes.append(["para", plain])
        last, prev_len = "para", len(plain)
    out = [f"## {name}" if nested else f"# {name}"]
    for kind, text in nodes:
        if kind.startswith("h"):
            out.append("#" * int(kind[1:]) + " " + text)
        elif kind == "item":
            out.append("- " + _short(text, 120))
        elif sentences:
            out.extend("- " + _short(s, 120) for s in _SENTENCE_SPLIT.split(re.sub(r"\s+", " ", text).strip()) if s)
        else:
            out.append("- " + _first_sentence(text))
    if len(out) == 1:
        out.append("- " + t("mm.no_structure"))
    return promote_orphans("\n".join(out))


def struct_combined(name: str, entries: list[tuple[str, str]]) -> str:
    parts = [f"# {name}"] + [struct_outline(title, md, nested=True) for title, md in entries]
    return promote_orphans("\n".join(parts))


# ---------- rangkuman AI ----------

# Perintah ke AI = instruksi per jenis (bisa disunting pengguna di Pengaturan) + aturan tetap yang selalu
# ditambahkan aplikasi: bahasa keluaran (bahasa aplikasi) dan bentuk teknis keluarannya. Catatan potongan untuk
# dokumen panjang memakai perintah internal yang tidak bisa disunting. {out} diisi kata "rangkuman" atau "catatan".
_FAITHFUL_EN = (
    "- Only include what is actually in the document. Do not add data, numbers, names, dates, opinions, "
    "or conclusions that are not written there.\n"
    "- Keep numbers, dates, units, terms, and names exactly as in the document.\n"
    "- Ignore content that is not part of the substance, such as ads, subscribe prompts, promotional contacts, "
    "social media links, and keyword lists."
)
_FAITHFUL_ID = (
    "- Tulis hanya hal yang benar-benar ada di dokumen. Jangan menambah data, angka, nama, tanggal, pendapat, "
    "atau kesimpulan yang tidak tertulis.\n"
    "- Pertahankan angka, tanggal, satuan, istilah, dan nama persis seperti di dokumen.\n"
    "- Abaikan bagian yang bukan isi, seperti iklan, ajakan berlangganan, kontak promosi, tautan media sosial, "
    "dan daftar kata kunci."
)
_SUM_FAITHFUL_EN = (" Only include what is actually in the document, and keep numbers, dates, and names exactly as written. "
                    "Ignore ads, subscribe prompts, promotional contacts, social media links, and keyword lists.")
_SUM_FAITHFUL_ID = (" Tulis hanya hal yang benar-benar ada di dokumen, dan pertahankan angka, tanggal, dan nama persis seperti "
                    "tertulis. Abaikan iklan, ajakan berlangganan, kontak promosi, tautan media sosial, dan daftar kata kunci.")

PROMPTS = {
    "en": {
        # ----- instruksi bawaan yang bisa disunting -----
        "kind.poin": (
            "Summary type: Key points. The goal is for the reader to grasp the core of the document in one minute.\n"
            "- Create 3 to 6 main branches with the most important ideas or topics, in the order they appear in the document.\n"
            "- Each branch has 2 to 4 points. At most 3 levels (title, branch, point).\n"
            "- Each point is one short statement of at most 12 words.\n"
            "- Prioritize the main message, key numbers, and stated conclusions; skip examples, minor details, and repetition.\n"
            + _FAITHFUL_EN
        ),
        "kind.notulen": (
            "Summary type: Minutes (notes of a meeting, discussion, interview, or podcast).\n"
            "Use exactly these main branches, in this order:\n"
            "1. Meeting details — time, place, organizer, and participants or speakers, if mentioned.\n"
            "2. Topics discussed — one sub-branch per topic, with the key opinions or arguments and who made them, if mentioned.\n"
            "3. Decisions and agreements\n"
            "4. Action items — tasks, owners, and deadlines, if mentioned.\n"
            "5. Open questions — issues that are unresolved or still debated.\n"
            "Write only the branch names as headings (e.g. \"## Meeting details\"), without the descriptions.\n"
            "- If a branch is not covered in the document, give it one point: \"Not discussed\".\n"
            "- Each point has at most 15 words. At most 4 levels.\n"
            + _FAITHFUL_EN
        ),
        "kind.lengkap": (
            "Summary type: Full summary. The goal is to replace reading the whole document: every important part is "
            "covered, but written concisely.\n"
            "- Follow the flow and structure of the document. Create one main branch for each section or major topic "
            "(usually 4 to 10 branches).\n"
            "- Under each branch, write sub-branches and points with the facts, numbers, reasons, important examples, "
            "and conclusions of that part.\n"
            "- Do not skip important parts, even short ones. Merge repeated content.\n"
            "- Each point has at most 20 words. At most 4 levels.\n"
            "- End with a \"## Conclusion\" branch containing the document's conclusion or final message, if there is one.\n"
            + _FAITHFUL_EN
        ),
        "kind.singkat": (
            "Summary type: Short. Write one paragraph of 3 to 5 sentences that captures what the document is about, "
            "its most important facts or numbers, and its conclusion." + _SUM_FAITHFUL_EN
        ),
        "kind.sedang": (
            "Summary type: Medium. Start with a short paragraph (2 to 3 sentences) on what the document is about. "
            "Then give a \"Key points\" list of 5 to 8 bullets with the most important facts, numbers, decisions, or "
            "arguments. End with one sentence on the conclusion or next steps, if the document has them." + _SUM_FAITHFUL_EN
        ),
        "kind.rinci": (
            "Summary type: Detailed. Follow the structure of the document: one heading per main section or topic, in the "
            "original order, each with a short paragraph or a few bullets covering its facts, numbers, reasons, and "
            "conclusions. Do not skip important parts, even short ones, and merge repeated content. End with a "
            "\"Conclusion\" section if the document has a conclusion or final message." + _SUM_FAITHFUL_EN
        ),
        # ----- aturan tetap yang selalu ditambahkan aplikasi -----
        "lang": ("- Write {out} in English. If the document is in another language, still write in English; proper names "
                 "and special terms may stay as in the original."),
        "out_outline": "the mind map outline",
        "out_summary": "the summary",
        "out_notes": "the notes",
        "fixed_map": (
            "Required output:\n{lang}\n"
            "- Output only a Markdown mind map outline in this form:\n"
            "  # Title\n"
            "  ## Main branch\n"
            "  ### Sub-branch (if needed)\n"
            "  - point\n"
            "- Do not use tables, code blocks, links, images, emoji, or HTML. Do not write an introduction or closing sentence."
        ),
        "fixed_sum": (
            "Required output:\n{lang}\n"
            "- Output only the summary in Markdown: paragraphs, plus headings, bullet lists, or a short table only where they help.\n"
            "- Do not start with an introduction such as \"Here is the summary\", and do not add closing remarks."
        ),
        # ----- catatan potongan untuk dokumen panjang (internal) -----
        "notes_head": "You take notes on the important content of part of a document.\nRequired rules:",
        "notes_format": "- Write a Markdown bullet list, one fact per point.\n- Do not write an introduction or closing sentence.",
        "notes.poin": "Focus on the main ideas, key numbers, and stated conclusions. Skip examples, minor details, and repetition.",
        "notes.notulen": ("Focus on who said what, the topics discussed, decisions and agreements, tasks with their owners "
                          "and deadlines, and open questions."),
        "notes.lengkap": ("Focus on every section and every important fact in detail, in the order of the document, "
                          "including numbers, reasons, important examples, and conclusions."),
        # ----- isi pesan pengguna -----
        "chunk": "Part {k} of {n} of the document \"{name}\":\n\n{text}",
        "doc": "Document \"{name}\":\n\n{text}",
        "block": "=== Document {i}: {name} ===\n{text}",
        "final": "Mind map title: {title}\n\nDocument content between <<< and >>>:\n<<<\n{body}\n>>>",
        "final_sum": "Document title: {title}\n\nDocument content between <<< and >>>:\n<<<\n{body}\n>>>",
    },
    "id": {
        # ----- instruksi bawaan yang bisa disunting -----
        "kind.poin": (
            "Jenis rangkuman: Poin utama. Tujuannya agar pembaca menangkap inti dokumen dalam satu menit.\n"
            "- Buat 3 sampai 6 cabang utama berisi gagasan atau topik terpenting, berurutan seperti di dokumen.\n"
            "- Setiap cabang berisi 2 sampai 4 poin. Paling banyak 3 tingkat (judul, cabang, poin).\n"
            "- Setiap poin berupa satu pernyataan singkat, paling banyak 12 kata.\n"
            "- Utamakan pesan pokok, angka kunci, dan kesimpulan yang tertulis; lewati contoh, detail kecil, dan pengulangan.\n"
            + _FAITHFUL_ID
        ),
        "kind.notulen": (
            "Jenis rangkuman: Notulen (catatan rapat, diskusi, wawancara, atau podcast).\n"
            "Pakai persis cabang utama berikut, berurutan:\n"
            "1. Informasi pertemuan — waktu, tempat, penyelenggara, dan peserta atau narasumber, bila disebut.\n"
            "2. Pokok bahasan — satu sub-cabang per topik, berisi pendapat atau argumen penting dan siapa yang "
            "menyampaikannya, bila disebut.\n"
            "3. Keputusan dan kesepakatan\n"
            "4. Tindak lanjut — tugas, penanggung jawab, dan tenggat waktu, bila disebut.\n"
            "5. Pertanyaan terbuka — hal yang belum selesai atau masih diperdebatkan.\n"
            "Tulis hanya nama cabang sebagai judul (mis. \"## Informasi pertemuan\"), tanpa keterangannya.\n"
            "- Bila sebuah cabang tidak dibahas di dokumen, isi dengan satu poin: \"Tidak dibahas\".\n"
            "- Setiap poin paling banyak 15 kata. Paling banyak 4 tingkat.\n"
            + _FAITHFUL_ID
        ),
        "kind.lengkap": (
            "Jenis rangkuman: Ringkas lengkap. Tujuannya menggantikan membaca seluruh dokumen: setiap bagian penting "
            "tercakup, tetapi ditulis ringkas.\n"
            "- Ikuti alur dan susunan dokumen. Buat satu cabang utama untuk setiap bagian atau topik besar "
            "(biasanya 4 sampai 10 cabang).\n"
            "- Di bawah setiap cabang, tulis sub-cabang dan poin berisi fakta, angka, alasan, contoh penting, "
            "dan kesimpulan dari bagian itu.\n"
            "- Jangan melewatkan bagian penting, meskipun pendek. Gabungkan isi yang berulang.\n"
            "- Setiap poin paling banyak 20 kata. Paling banyak 4 tingkat.\n"
            "- Akhiri dengan cabang \"## Kesimpulan\" berisi kesimpulan atau pesan akhir dokumen, bila ada.\n"
            + _FAITHFUL_ID
        ),
        "kind.singkat": (
            "Jenis ringkasan: Singkat. Tulis satu paragraf berisi 3 sampai 5 kalimat yang menangkap isi dokumen, "
            "fakta atau angka terpentingnya, dan kesimpulannya." + _SUM_FAITHFUL_ID
        ),
        "kind.sedang": (
            "Jenis ringkasan: Sedang. Mulai dengan satu paragraf pendek (2 sampai 3 kalimat) tentang isi dokumen. "
            "Lalu tulis daftar \"Poin penting\" berisi 5 sampai 8 butir dengan fakta, angka, keputusan, atau argumen "
            "terpenting. Tutup dengan satu kalimat tentang kesimpulan atau langkah selanjutnya, bila ada di dokumen."
            + _SUM_FAITHFUL_ID
        ),
        "kind.rinci": (
            "Jenis ringkasan: Rinci. Ikuti susunan dokumen: satu judul untuk setiap bagian atau topik utama, berurutan "
            "seperti aslinya, masing-masing berisi paragraf pendek atau beberapa butir tentang fakta, angka, alasan, dan "
            "kesimpulannya. Jangan melewatkan bagian penting, meskipun pendek, dan gabungkan isi yang berulang. Akhiri "
            "dengan bagian \"Kesimpulan\" bila dokumen punya kesimpulan atau pesan akhir." + _SUM_FAITHFUL_ID
        ),
        # ----- aturan tetap yang selalu ditambahkan aplikasi -----
        "lang": ("- Tulis {out} dalam Bahasa Indonesia. Bila dokumen berbahasa lain, tetap tulis dalam Bahasa Indonesia; "
                 "nama dan istilah khusus boleh dibiarkan seperti aslinya."),
        "out_outline": "kerangka mind map",
        "out_summary": "rangkuman",
        "out_notes": "catatan",
        "fixed_map": (
            "Aturan keluaran:\n{lang}\n"
            "- Keluarkan hanya kerangka mind map Markdown dengan bentuk:\n"
            "  # Judul\n"
            "  ## Cabang utama\n"
            "  ### Sub-cabang (bila perlu)\n"
            "  - poin\n"
            "- Jangan memakai tabel, blok kode, tautan, gambar, emoji, atau HTML. Jangan menulis kalimat pembuka atau penutup."
        ),
        "fixed_sum": (
            "Aturan keluaran:\n{lang}\n"
            "- Keluarkan hanya rangkumannya dalam Markdown: paragraf, ditambah judul, daftar poin, atau tabel pendek "
            "hanya bila membantu.\n"
            "- Jangan membuka dengan kalimat seperti \"Berikut rangkumannya\", dan jangan menambah penutup."
        ),
        # ----- catatan potongan untuk dokumen panjang (internal) -----
        "notes_head": "Anda mencatat poin penting dari potongan dokumen.\nAturan wajib:",
        "notes_format": "- Tulis sebagai daftar poin Markdown, satu fakta per poin.\n- Jangan menulis kalimat pembuka atau penutup.",
        "notes.poin": "Fokus pada gagasan pokok, angka kunci, dan kesimpulan yang tertulis. Lewati contoh, detail kecil, dan pengulangan.",
        "notes.notulen": ("Fokus pada siapa menyampaikan apa, pokok bahasan, keputusan dan kesepakatan, tugas beserta "
                          "penanggung jawab dan tenggatnya, serta pertanyaan yang belum terjawab."),
        "notes.lengkap": ("Fokus pada setiap bagian dan setiap fakta penting secara rinci, berurutan seperti di dokumen, "
                          "termasuk angka, alasan, contoh penting, dan kesimpulan."),
        # ----- isi pesan pengguna -----
        "chunk": "Potongan {k} dari {n} dokumen \"{name}\":\n\n{text}",
        "doc": "Dokumen \"{name}\":\n\n{text}",
        "block": "=== Dokumen {i}: {name} ===\n{text}",
        "final": "Judul mind map: {title}\n\nIsi dokumen di antara tanda <<< dan >>>:\n<<<\n{body}\n>>>",
        "final_sum": "Judul dokumen: {title}\n\nIsi dokumen di antara tanda <<< dan >>>:\n<<<\n{body}\n>>>",
    },
}
_NOTES_RULES = {"en": _FAITHFUL_EN, "id": _FAITHFUL_ID}
NOTES_KIND = {"singkat": "poin", "sedang": "poin", "rinci": "lengkap"}  # catatan potongan untuk rangkuman teks
PROMPT_LIMIT = 4000  # panjang maksimum instruksi buatan pengguna


def _lang_table(lang: str | None) -> tuple[str, dict]:
    lang = lang if lang in PROMPTS else get_lang()
    return lang, PROMPTS.get(lang, PROMPTS["en"])


def prompt_defaults(lang: str | None = None) -> dict[str, str]:
    """Instruksi bawaan semua jenis (mind map dan rangkuman teks) dalam bahasa aktif, untuk ditampilkan di Pengaturan."""
    _, p = _lang_table(lang)
    return {k: p[f"kind.{k}"] for k in PROMPT_KINDS}


def instruction(kind: str, custom: dict | None = None, lang: str | None = None) -> str:
    """Instruksi buatan pengguna untuk jenis ini, atau instruksi bawaan bila kosong."""
    text = ((custom or {}).get(kind) or "").strip()
    return text[:PROMPT_LIMIT] if text else prompt_defaults(lang)[kind]


def system_prompt(kind: str, lang: str | None = None, custom: dict | None = None) -> str:
    """Perintah sistem lengkap: instruksi (bisa disunting) + aturan tetap (bahasa dan bentuk keluaran).
    Jenis rangkuman teks (singkat | sedang | rinci) menghasilkan Markdown biasa, jenis mind map menghasilkan kerangka."""
    lang, p = _lang_table(lang)
    text_kind = kind in SUM_KINDS
    kind = kind if text_kind else clean_kind(kind)
    out = p["out_summary"] if text_kind else p["out_outline"]
    fixed = p["fixed_sum" if text_kind else "fixed_map"].format(lang=p["lang"].format(out=out))
    return instruction(kind, custom, lang) + "\n\n" + fixed


def notes_prompt(kind: str, lang: str | None = None) -> str:
    """Perintah sistem untuk mencatat poin penting dari potongan dokumen panjang; fokusnya mengikuti jenis rangkuman."""
    lang, p = _lang_table(lang)
    kind = NOTES_KIND.get(kind) or clean_kind(kind)
    return "\n".join([p["notes_head"], _NOTES_RULES[lang], p["lang"].format(out=p["out_notes"]), p["notes_format"], "",
                      p[f"notes.{kind}"]])


CHUNK_CHARS = 60_000   # sekitar 15 ribu token: aman untuk semua penyedia yang didukung
NOTES_TARGET = 12_000  # bila catatan gabungan masih lebih panjang dari ini, diringkas lagi


def split_chunks(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Potong teks panjang di batas judul atau paragraf supaya tiap potongan muat satu permintaan."""
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    blocks = re.split(r"\n(?=#{1,3}\s)|\n{2,}", text)
    chunks: list[str] = []
    cur = ""
    for b in blocks:
        while len(b) > limit:  # paragraf raksasa (mis. transkrip tanpa titik): potong paksa
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(b[:limit])
            b = b[limit:]
        if len(cur) + len(b) + 2 > limit and cur:
            chunks.append(cur)
            cur = b
        else:
            cur = f"{cur}\n\n{b}" if cur else b
    if cur.strip():
        chunks.append(cur)
    return chunks


def clean_outline(md: str, title: str) -> str:
    """Rapikan jawaban AI menjadi kerangka yang bisa digambar markmap."""
    text = (md or "").strip()
    text = re.sub(r"^```[\w-]*\s*\n|\n```\s*$", "", text)
    out: list[str] = []
    seen_h1 = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("```"):
            continue
        s = line.strip()
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            level, body = len(m.group(1)), _LINK.sub(r"\1", m.group(2)).strip().strip("*").strip()
            if level == 1:
                if seen_h1:
                    level = 2
                seen_h1 = True
            out.append("#" * min(level, 5) + " " + body)
            continue
        m = re.match(r"^(\s*)(?:[-*+•]|\d+[.)])\s+(.*)$", line)
        if m:
            indent = len(m.group(1).replace("\t", "  ")) // 2
            out.append("  " * min(indent, 3) + "- " + _LINK.sub(r"\1", m.group(2)).strip())
            continue
        if re.fullmatch(r"\|.*\|", s) or re.fullmatch(r"[-=*_]{3,}", s):
            continue
        out.append("- " + _LINK.sub(r"\1", s))
    first_h1 = next((i for i, l in enumerate(out) if l.startswith("# ")), None)
    if first_h1:
        out = out[first_h1:]  # buang kalimat pembuka sebelum judul ("Berikut rangkumannya:")
    elif first_h1 is None:
        out.insert(0, f"# {title}")
    if len(out) == 1:
        out.append("- " + t("mm.no_points"))
    return promote_orphans("\n".join(out))


def clean_summary(md: str) -> str:
    """Rapikan jawaban AI untuk rangkuman teks: buang pagar kode pembungkus dan baris kosong berlebih."""
    text = (md or "").replace("\r\n", "\n").strip()
    m = re.fullmatch(r"```[\w-]*\s*\n(.*)\n```", text, flags=re.S)
    if m:
        text = m.group(1).strip()
    return re.sub(r"\n{3,}", "\n\n", text) or t("mm.no_points")


class Summarizer:
    """Rangkuman AI: kerangka mind map (poin | notulen | lengkap) atau rangkuman teks (singkat | sedang | rinci).
    prompts: instruksi buatan pengguna per jenis (pengaturan "prompts"); kosong berarti instruksi bawaan."""

    def __init__(self, cfg: ai_mod.AIConfig, kind: str, progress: Progress, cancel: threading.Event,
                 prompts: dict | None = None):
        self.cfg = cfg
        self.text_mode = kind in SUM_KINDS
        self.kind = kind if self.text_mode else clean_kind(kind)
        self.prompts = prompts or {}
        self.progress = progress
        self.cancel = cancel
        self.lang = get_lang()  # satu rangkuman memakai satu bahasa, meski bahasa aplikasi diganti di tengah jalan
        self._p = PROMPTS.get(self.lang, PROMPTS["en"])
        # Rangkuman lengkap/rinci butuh catatan lebih panjang supaya rinciannya tidak hilang.
        self.notes_target = NOTES_TARGET * 2 if NOTES_KIND.get(self.kind, self.kind) == "lengkap" else NOTES_TARGET

    def _check(self) -> None:
        if self.cancel.is_set():
            raise Cancelled()

    def _no_text(self, title: str) -> str:
        if self.text_mode:
            return t("sum.no_text")
        return f"# {title}\n## {t('mm.no_text_head')}\n- {t('mm.no_text_tip')}"

    def _block(self, i: int, name: str, text: str) -> str:
        return self._p["block"].format(i=i, name=name, text=text)

    def _notes(self, name: str, text: str) -> str:
        """Catatan poin penting dari satu dokumen, diringkas bertahap bila sangat panjang."""
        chunks = split_chunks(text)
        if len(chunks) <= 1:
            return chunks[0] if chunks else ""
        system = notes_prompt(self.kind, self.lang)
        notes = []
        for k, ch in enumerate(chunks, 1):
            self._check()
            self.progress(t("mm.read_part", name=name, k=k, n=len(chunks)))
            notes.append(ai_mod.chat(self.cfg, system, self._p["chunk"].format(k=k, n=len(chunks), name=name, text=ch)))
        joined = "\n".join(notes)
        if len(joined) > self.notes_target * 2:
            return self._notes(name, joined)
        return joined

    def _final(self, title: str, body: str) -> str:
        self._check()
        system = system_prompt(self.kind, self.lang, self.prompts)
        if self.text_mode:
            self.progress(t("sum.writing"))
            return clean_summary(ai_mod.chat(self.cfg, system, self._p["final_sum"].format(title=title, body=body)))
        self.progress(t("mm.building"))
        return clean_outline(ai_mod.chat(self.cfg, system, self._p["final"].format(title=title, body=body)), title)

    def one(self, title: str, text: str) -> str:
        title = base_name(title)
        if not (text or "").strip():
            return self._no_text(title)
        self.progress(t("mm.reading"))
        notes = self._notes(title, text)
        if len(notes) > CHUNK_CHARS:
            notes = notes[:CHUNK_CHARS]
        self.progress(t("mm.summarizing"))
        return self._final(title, notes)

    def many(self, title: str, entries: list[tuple[str, str]]) -> str:
        entries = [(base_name(name), body) for name, body in entries if (body or "").strip()]
        if not entries:
            return self._no_text(title)
        total = sum(len(body) for _, body in entries)
        if total <= CHUNK_CHARS:
            self.progress(t("mm.summarizing_n", n=len(entries)))
            body = "\n\n".join(self._block(i, name, text) for i, (name, text) in enumerate(entries, 1))
            return self._final(title, body)
        parts = []
        for i, (name, text) in enumerate(entries, 1):
            self._check()
            self.progress(t("mm.summarizing_k", k=i, n=len(entries)))
            if len(text) <= self.notes_target:
                parts.append(self._block(i, name, text))
            else:
                notes = (self._notes(name, text) if len(text) > CHUNK_CHARS else
                         ai_mod.chat(self.cfg, notes_prompt(self.kind, self.lang), self._p["doc"].format(name=name, text=text)))
                parts.append(self._block(i, name, notes))
        self.progress(t("mm.merging"))
        body = "\n\n".join(parts)
        if len(body) > CHUNK_CHARS:
            body = self._notes(title, body)[:CHUNK_CHARS]
        return self._final(title, body)
