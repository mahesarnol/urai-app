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

KINDS = ("poin", "notulen", "lengkap")         # jenis rangkuman AI; nama tampilannya diatur tampilan
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


def struct_outline(title: str, md: str, nested: bool = False) -> str:
    """Kerangka mind map dari judul, daftar, dan tabel di dokumen, tanpa internet.

    Dokumen dengan beberapa judul tingkat 1 (Word, PowerPoint) memakai judul itu sebagai cabang utama.
    Untuk teks tanpa tanda judul sama sekali (mis. PDF), judul bernomor seperti "2. Analisis" dan baris
    berhuruf kapital dianggap judul, dan baris yang terpotong di tengah kalimat digabung lagi.
    """
    name = base_name(title)
    shift = 1 if nested else 0
    lines = (md or "").splitlines()
    heads = [len(m.group(1)) for m in (re.match(r"^\s*(#{1,6})\s+\S", l) for l in lines) if m]
    structured = bool(heads)
    h1_count = heads.count(1)
    md_shift = 1 if h1_count >= 2 else 0  # beberapa judul tingkat 1 berarti itu bab, bukan judul dokumen
    nodes: list[list] = []  # [jenis, teks]; jenis: h<level> | item | para
    in_code = False
    table = False          # sedang di dalam (atau di sela-sela potongan) tabel
    last = None            # jenis node terakhir yang masih bisa disambung
    prev_len = 0
    seen_text = False
    for raw in lines:
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
        else:
            out.append("- " + _first_sentence(text))
    if len(out) == 1:
        out.append("- " + t("mm.no_structure"))
    return promote_orphans("\n".join(out))


def struct_combined(name: str, entries: list[tuple[str, str]]) -> str:
    parts = [f"# {name}"] + [struct_outline(title, md, nested=True) for title, md in entries]
    return promote_orphans("\n".join(parts))


# ---------- rangkuman AI ----------

# Perintah ke AI dalam bahasa aplikasi. Perintah sistem = kepala + aturan kesetiaan (dipakai bersama oleh
# rangkuman dan catatan) + bentuk keluaran + aturan per jenis. Aturan per jenis memegang batas cabang,
# tingkat, dan panjang poin. {out} diisi kata "rangkuman" atau "catatan".
PROMPTS = {
    "en": {
        "head": "You turn documents into a mind map outline, written in English.\nRequired rules:",
        "rules": (
            "- Only include what is actually in the document. Do not add data, numbers, names, dates, opinions, "
            "or conclusions that are not written there.\n"
            "- Keep numbers, dates, units, terms, and names exactly as in the document.\n"
            "- If the document is in another language, still write {out} in English; proper names and special terms "
            "may stay as in the original.\n"
            "- Ignore content that is not part of the substance, such as ads, subscribe prompts, promotional contacts, "
            "social media links, and keyword lists."
        ),
        "out_outline": "the outline",
        "format": (
            "- Output only a Markdown outline in this form:\n"
            "  # Title\n"
            "  ## Main branch\n"
            "  ### Sub-branch (if needed)\n"
            "  - point\n"
            "- Do not use tables, code blocks, links, images, emoji, or HTML. Do not write an introduction or closing sentence."
        ),
        "kind.poin": (
            "Summary type: Key points. The goal is for the reader to grasp the core of the document in one minute.\n"
            "- Create 3 to 6 main branches with the most important ideas or topics, in the order they appear in the document.\n"
            "- Each branch has 2 to 4 points. At most 3 levels (title, branch, point).\n"
            "- Each point is one short statement of at most 12 words.\n"
            "- Prioritize the main message, key numbers, and stated conclusions; skip examples, minor details, and repetition."
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
            "- Each point has at most 15 words. At most 4 levels."
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
            "- End with a \"## Conclusion\" branch containing the document's conclusion or final message, if there is one."
        ),
        "notes_head": "You take notes on the important content of part of a document, written in English.\nRequired rules:",
        "out_notes": "the notes",
        "notes_format": "- Write a Markdown bullet list, one fact per point.\n- Do not write an introduction or closing sentence.",
        "notes.poin": "Focus on the main ideas, key numbers, and stated conclusions. Skip examples, minor details, and repetition.",
        "notes.notulen": ("Focus on who said what, the topics discussed, decisions and agreements, tasks with their owners "
                          "and deadlines, and open questions."),
        "notes.lengkap": ("Focus on every section and every important fact in detail, in the order of the document, "
                          "including numbers, reasons, important examples, and conclusions."),
        "chunk": "Part {k} of {n} of the document \"{name}\":\n\n{text}",
        "doc": "Document \"{name}\":\n\n{text}",
        "block": "=== Document {i}: {name} ===\n{text}",
        "final": "Mind map title: {title}\n\nDocument content between <<< and >>>:\n<<<\n{body}\n>>>",
    },
    "id": {
        "head": "Anda menyusun dokumen menjadi kerangka mind map dalam Bahasa Indonesia.\nAturan wajib:",
        "rules": (
            "- Tulis hanya hal yang benar-benar ada di dokumen. Jangan menambah data, angka, nama, tanggal, pendapat, "
            "atau kesimpulan yang tidak tertulis.\n"
            "- Pertahankan angka, tanggal, satuan, istilah, dan nama persis seperti di dokumen.\n"
            "- Bila dokumen berbahasa lain, tetap tulis {out} dalam Bahasa Indonesia; nama dan istilah khusus boleh "
            "dibiarkan seperti aslinya.\n"
            "- Abaikan bagian yang bukan isi, seperti iklan, ajakan berlangganan, kontak promosi, tautan media sosial, "
            "dan daftar kata kunci."
        ),
        "out_outline": "rangkuman",
        "format": (
            "- Keluarkan hanya kerangka Markdown dengan bentuk:\n"
            "  # Judul\n"
            "  ## Cabang utama\n"
            "  ### Sub-cabang (bila perlu)\n"
            "  - poin\n"
            "- Jangan memakai tabel, blok kode, tautan, gambar, emoji, atau HTML. Jangan menulis kalimat pembuka atau penutup."
        ),
        "kind.poin": (
            "Jenis rangkuman: Poin utama. Tujuannya agar pembaca menangkap inti dokumen dalam satu menit.\n"
            "- Buat 3 sampai 6 cabang utama berisi gagasan atau topik terpenting, berurutan seperti di dokumen.\n"
            "- Setiap cabang berisi 2 sampai 4 poin. Paling banyak 3 tingkat (judul, cabang, poin).\n"
            "- Setiap poin berupa satu pernyataan singkat, paling banyak 12 kata.\n"
            "- Utamakan pesan pokok, angka kunci, dan kesimpulan yang tertulis; lewati contoh, detail kecil, dan pengulangan."
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
            "- Setiap poin paling banyak 15 kata. Paling banyak 4 tingkat."
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
            "- Akhiri dengan cabang \"## Kesimpulan\" berisi kesimpulan atau pesan akhir dokumen, bila ada."
        ),
        "notes_head": "Anda mencatat poin penting dari potongan dokumen dalam Bahasa Indonesia.\nAturan wajib:",
        "out_notes": "catatan",
        "notes_format": "- Tulis sebagai daftar poin Markdown, satu fakta per poin.\n- Jangan menulis kalimat pembuka atau penutup.",
        "notes.poin": "Fokus pada gagasan pokok, angka kunci, dan kesimpulan yang tertulis. Lewati contoh, detail kecil, dan pengulangan.",
        "notes.notulen": ("Fokus pada siapa menyampaikan apa, pokok bahasan, keputusan dan kesepakatan, tugas beserta "
                          "penanggung jawab dan tenggatnya, serta pertanyaan yang belum terjawab."),
        "notes.lengkap": ("Fokus pada setiap bagian dan setiap fakta penting secara rinci, berurutan seperti di dokumen, "
                          "termasuk angka, alasan, contoh penting, dan kesimpulan."),
        "chunk": "Potongan {k} dari {n} dokumen \"{name}\":\n\n{text}",
        "doc": "Dokumen \"{name}\":\n\n{text}",
        "block": "=== Dokumen {i}: {name} ===\n{text}",
        "final": "Judul mind map: {title}\n\nIsi dokumen di antara tanda <<< dan >>>:\n<<<\n{body}\n>>>",
    },
}


def system_prompt(kind: str, lang: str | None = None) -> str:
    """Perintah sistem untuk menyusun kerangka mind map jenis ini."""
    p = PROMPTS.get(lang or get_lang(), PROMPTS["en"])
    return "\n".join([p["head"], p["rules"].format(out=p["out_outline"]), p["format"], "", p[f"kind.{clean_kind(kind)}"]])


def notes_prompt(kind: str, lang: str | None = None) -> str:
    """Perintah sistem untuk mencatat poin penting dari potongan dokumen panjang; fokusnya mengikuti jenis rangkuman."""
    p = PROMPTS.get(lang or get_lang(), PROMPTS["en"])
    return "\n".join([p["notes_head"], p["rules"].format(out=p["out_notes"]), p["notes_format"], "", p[f"notes.{clean_kind(kind)}"]])


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


class Summarizer:
    def __init__(self, cfg: ai_mod.AIConfig, kind: str, progress: Progress, cancel: threading.Event):
        self.cfg = cfg
        self.kind = clean_kind(kind)
        self.progress = progress
        self.cancel = cancel
        self.lang = get_lang()  # satu rangkuman memakai satu bahasa, meski bahasa aplikasi diganti di tengah jalan
        self._p = PROMPTS.get(self.lang, PROMPTS["en"])
        # Ringkas lengkap butuh catatan lebih panjang supaya rinciannya tidak hilang.
        self.notes_target = NOTES_TARGET * 2 if self.kind == "lengkap" else NOTES_TARGET

    def _check(self) -> None:
        if self.cancel.is_set():
            raise Cancelled()

    def _no_text(self, title: str) -> str:
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
        self.progress(t("mm.building"))
        user = self._p["final"].format(title=title, body=body)
        return clean_outline(ai_mod.chat(self.cfg, system_prompt(self.kind, self.lang), user), title)

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


