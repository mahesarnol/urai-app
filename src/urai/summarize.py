"""Rangkuman untuk mind map: struktur dokumen (offline) atau rangkuman AI (Umum, Notulen, Laporan)."""
from __future__ import annotations

import re
import threading
from typing import Callable

from . import ai as ai_mod
from .errors import Cancelled
from .textutil import base_name

Progress = Callable[[str], None]

KIND_LABEL = {"umum": "Umum", "notulen": "Notulen", "laporan": "Laporan"}

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
        out.append("- Tidak ada struktur yang bisa diambil")
    return promote_orphans("\n".join(out))


def struct_combined(name: str, entries: list[tuple[str, str]]) -> str:
    parts = [f"# {name}"] + [struct_outline(title, md, nested=True) for title, md in entries]
    return promote_orphans("\n".join(parts))


# ---------- rangkuman AI ----------

SYSTEM = """Anda menyusun rangkuman dokumen menjadi kerangka mind map dalam Bahasa Indonesia.

Aturan wajib:
- Tulis hanya hal yang benar-benar ada di dokumen. Jangan menambah data, angka, nama, tanggal, atau kesimpulan yang tidak tertulis.
- Pertahankan angka, tanggal, satuan, dan nama persis seperti di dokumen.
- Bila bagian yang diminta tidak dibahas di dokumen, isi dengan satu poin: "Tidak dibahas di dokumen ini".
- Tulis ringkas. Setiap poin paling banyak 12 kata.
- Keluarkan hanya kerangka Markdown dengan bentuk:
  # Judul
  ## Cabang utama
  ### Sub-cabang (bila perlu)
  - poin
- Buat 3 sampai 7 cabang utama. Jangan lebih dari 4 tingkat.
- Jangan memakai tabel, blok kode, tautan, gambar, atau HTML. Jangan menulis kalimat pembuka atau penutup."""

KIND_RULES = {
    "umum": "Jenis rangkuman: Umum. Susun cabang utama dari topik terpenting di dokumen, berurutan seperti di dokumen.",
    "notulen": (
        "Jenis rangkuman: Notulen (catatan rapat atau diskusi). Pakai cabang utama berikut, berurutan: "
        "Pertemuan (waktu, tempat, peserta bila disebut), Masalah yang dibahas, Keputusan, "
        "Tindak lanjut (siapa dan kapan bila disebut)."
    ),
    "laporan": (
        "Jenis rangkuman: Laporan (laporan atau kajian). Pakai cabang utama berikut, berurutan: "
        "Temuan (pisahkan Kekuatan dan Kelemahan bila ada), Aktor atau pihak terkait, Rekomendasi."
    ),
}

NOTES_SYSTEM = """Anda mencatat poin penting dari potongan dokumen dalam Bahasa Indonesia.
- Tulis sebagai daftar poin Markdown, satu fakta per poin.
- Pertahankan angka, tanggal, satuan, dan nama persis seperti di dokumen.
- Jangan menambah apa pun yang tidak tertulis, dan jangan menulis kalimat pembuka atau penutup."""

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
        out.append("- Tidak ada poin yang bisa dirangkum")
    return promote_orphans("\n".join(out))


class Summarizer:
    def __init__(self, cfg: ai_mod.AIConfig, kind: str, progress: Progress, cancel: threading.Event):
        self.cfg = cfg
        self.kind = kind if kind in KIND_RULES else "umum"
        self.progress = progress
        self.cancel = cancel

    def _check(self) -> None:
        if self.cancel.is_set():
            raise Cancelled()

    def _notes(self, name: str, text: str) -> str:
        """Catatan poin penting dari satu dokumen, diringkas bertahap bila sangat panjang."""
        chunks = split_chunks(text)
        if len(chunks) <= 1:
            return chunks[0] if chunks else ""
        notes = []
        for k, ch in enumerate(chunks, 1):
            self._check()
            self.progress(f"Membaca {name} · bagian {k} dari {len(chunks)}…")
            notes.append(ai_mod.chat(self.cfg, NOTES_SYSTEM, f"Potongan {k} dari {len(chunks)} dokumen \"{name}\":\n\n{ch}"))
        joined = "\n".join(notes)
        if len(joined) > NOTES_TARGET * 2:
            return self._notes(name, joined)
        return joined

    def _final(self, title: str, body: str) -> str:
        self._check()
        self.progress("Menyusun mind map…")
        user = (
            f"{KIND_RULES[self.kind]}\nJudul mind map: {title}\n\n"
            f"Isi dokumen di antara tanda <<< dan >>>:\n<<<\n{body}\n>>>"
        )
        return clean_outline(ai_mod.chat(self.cfg, SYSTEM, user), title)

    def one(self, title: str, text: str) -> str:
        title = base_name(title)
        if not (text or "").strip():
            return f"# {title}\n## Tidak ada teks terbaca\n- Aktifkan baca scan, lalu ulangi"
        self.progress("Membaca isi dokumen…")
        notes = self._notes(title, text)
        if len(notes) > CHUNK_CHARS:
            notes = notes[:CHUNK_CHARS]
        self.progress("Meringkas…")
        return self._final(title, notes)

    def many(self, title: str, entries: list[tuple[str, str]]) -> str:
        entries = [(base_name(n), t) for n, t in entries if (t or "").strip()]
        if not entries:
            return f"# {title}\n## Tidak ada teks terbaca\n- Aktifkan baca scan, lalu ulangi"
        total = sum(len(t) for _, t in entries)
        if total <= CHUNK_CHARS:
            self.progress(f"Meringkas {len(entries)} dokumen…")
            body = "\n\n".join(f"=== Dokumen {i}: {n} ===\n{t}" for i, (n, t) in enumerate(entries, 1))
            return self._final(title, body)
        parts = []
        for i, (n, t) in enumerate(entries, 1):
            self._check()
            self.progress(f"Meringkas dokumen {i} dari {len(entries)}…")
            if len(t) <= NOTES_TARGET:
                parts.append(f"=== Dokumen {i}: {n} ===\n{t}")
            else:
                notes = self._notes(n, t) if len(t) > CHUNK_CHARS else ai_mod.chat(self.cfg, NOTES_SYSTEM, f"Dokumen \"{n}\":\n\n{t}")
                parts.append(f"=== Dokumen {i}: {n} ===\n{notes}")
        self.progress("Menggabungkan poin penting…")
        body = "\n\n".join(parts)
        if len(body) > CHUNK_CHARS:
            body = self._notes(title, body)[:CHUNK_CHARS]
        return self._final(title, body)
