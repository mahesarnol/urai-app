"""Merapikan link YouTube dan halaman web yang ditempel pengguna."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


def normalize_link(text: str) -> str | None:
    """Kembalikan link siap dikonversi, atau None bila bukan link http(s)."""
    url = (text or "").strip()
    if not url or " " in url:
        return None
    if not re.match(r"^https?://", url, re.I):
        if re.match(r"^(www\.|m\.)?[\w-]+(\.[\w-]+)+(/|$)", url, re.I):
            url = "https://" + url
        else:
            return None
    p = urlparse(url)
    if not p.netloc or "." not in p.netloc:
        return None
    host = p.netloc.lower()
    for prefix in ("www.", "m.", "music."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    vid = None
    if host == "youtu.be":
        vid = p.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com"):
        if p.path == "/watch":
            vid = (parse_qs(p.query).get("v") or [None])[0]
        else:
            m = re.match(r"^/(shorts|live|embed)/([^/?#]+)", p.path)
            if m:
                vid = m.group(2)
    if vid:
        if not re.fullmatch(r"[\w-]{6,20}", vid):
            return None
        return f"https://www.youtube.com/watch?v={vid}"
    return url


def is_youtube(url: str) -> bool:
    return url.startswith("https://www.youtube.com/watch?v=")


def host_of(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h
