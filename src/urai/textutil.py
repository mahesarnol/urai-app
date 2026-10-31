"""Fungsi bantu untuk teks Markdown, nama file, dan ukuran."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .i18n import fmt_date, fmt_num, t

_WORD = re.compile(r"\w+", re.UNICODE)


def word_count(text: str) -> int:
    return len(_WORD.findall(text or ""))


def human_size(n: float) -> str:
    """Ukuran file sesuai bahasa aktif: 3.8 MB (en) atau 3,8 MB (id)."""
    if n < 1024:
        return f"{int(n)} B"
    for unit in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024 or unit == "GB":
            return f"{fmt_num(n, 0 if unit == 'KB' else 1)} {unit}"
    return f"{n} B"


def fmt_int(n: int) -> str:
    return fmt_num(n)


def safe_filename(name: str, fallback: str = "hasil") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name or "")
    name = re.sub(r"\s+", " ", name).strip(" .")
    if name.upper().split(".")[0] in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        name = "_" + name
    return (name[:120].strip() or fallback)


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    i = 2
    while True:
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
        i += 1


def demote_headings(md: str, levels: int = 1) -> str:
    """Turunkan level judul (# menjadi ##) di luar blok kode, supaya rapi saat digabung."""
    out, fence = [], None
    for line in md.splitlines():
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            mark = s[:3]
            if fence is None:
                fence = mark
            elif s.startswith(fence):
                fence = None
            out.append(line)
            continue
        if fence is None:
            m = re.match(r"^(#{1,6})(\s.*|$)", line)
            if m:
                line = "#" * min(6, len(m.group(1)) + levels) + m.group(2)
        out.append(line)
    return "\n".join(out)


def build_combined(entries: list[tuple[str, str]], now: datetime | None = None) -> str:
    """entries: daftar (nama sumber, isi markdown) sesuai urutan daftar."""
    stamp = fmt_date(now or datetime.now(), with_time=True)
    head = [t("md.combined_head", n=len(entries), date=stamp, app="Urai App"), ">"]
    head += [f"> {i}. {name}" for i, (name, _) in enumerate(entries, 1)]
    parts = ["\n".join(head)]
    for name, text in entries:
        body = demote_headings(text.strip()) if text.strip() else t("md.combined_empty")
        parts.append(f"# {name}\n\n{body}")
    return "\n\n---\n\n".join(parts) + "\n"


def base_name(name: str) -> str:
    return re.sub(r"\.[A-Za-z0-9]{2,5}$", "", name)
