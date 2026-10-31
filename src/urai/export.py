"""Menyimpan mind map sebagai Markdown, HTML interaktif (offline), gambar PNG, atau PDF siap cetak."""
from __future__ import annotations

import base64
import html
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path

from .i18n import fmt_date, get_lang, t
from .info import APP_NAME, VERSION
from .paths import web_dir

# Ukuran kertas dalam milimeter (lebar x tinggi, posisi tegak). F4 = folio Indonesia.
PAPER_MM = {"A4": (210, 297), "A3": (297, 420), "F4": (215, 330)}
MM = 72 / 25.4  # titik PDF per milimeter


def ai_label() -> str:
    """Peringatan pada mind map hasil AI, dalam bahasa aktif."""
    return t("export.ai_label")


def page_size(size: str, orient: str) -> tuple[float, float]:
    w, h = PAPER_MM.get(size, PAPER_MM["A4"])
    if orient == "land":
        w, h = h, w
    return w * MM, h * MM


def decode_data_url(data_url: str) -> bytes:
    m = re.match(r"^data:image/png;base64,(.+)$", data_url or "", re.S)
    if not m:
        raise ValueError(t("export.bad_image"))
    data = base64.b64decode(m.group(1))
    if not data.startswith(b"\x89PNG"):
        raise ValueError(t("export.bad_image"))
    return data


def save_md(path: Path, md: str) -> Path:
    path.write_text(md.rstrip() + "\n", encoding="utf-8")
    return path


def save_png(path: Path, data_url: str) -> Path:
    path.write_bytes(decode_data_url(data_url))
    return path


# ---------- HTML interaktif ----------

def _vendor(name: str) -> str:
    code = (web_dir() / "vendor" / name).read_text(encoding="utf-8")
    return code.replace("</script", "<\\/script")


def _vendor_license(name: str) -> str:
    p = web_dir() / "vendor" / f"{name}.LICENSE.txt"  # d3, markmap-view, markmap-lib
    try:
        return p.read_text(encoding="utf-8").replace("*/", "* /")
    except OSError:
        return ""


def _json_for_script(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


HTML_TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{app} {version}">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; --bg: #ffffff; --ink: #1f2937; --muted: #64748b; --line: #e2e8f0; --chip: #fcf0df; --chip-ink: #a65a05; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #15181e; --ink: #e7eaf0; --muted: #97a0b0; --line: #2c323d; --chip: #382915; --chip-ink: #f2a541; }} }}
  html, body {{ margin: 0; height: 100%; background: var(--bg); color: var(--ink); font-family: "Segoe UI", system-ui, sans-serif; }}
  header {{ position: fixed; top: 0; left: 0; right: 0; z-index: 2; display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: var(--bg); border-bottom: 1px solid var(--line); }}
  header h1 {{ margin: 0; font-size: 16px; font-weight: 700; }}
  header span {{ font-size: 12px; color: var(--muted); }}
  header .chip {{ padding: 2px 9px; border-radius: 999px; background: var(--chip); color: var(--chip-ink); font-weight: 700; }}
  header button {{ margin-left: auto; font: inherit; font-size: 13px; padding: 5px 12px; border-radius: 8px; border: 1px solid var(--line); background: transparent; color: var(--ink); cursor: pointer; }}
  svg.markmap {{ position: absolute; top: 46px; left: 0; width: 100%; height: calc(100% - 46px); --markmap-text-color: var(--ink); --markmap-circle-open-bg: var(--bg); --markmap-font: 500 14px/1.45 "Segoe UI", system-ui, sans-serif; }}
  footer {{ position: fixed; right: 12px; bottom: 8px; font-size: 11px; color: var(--muted); }}
</style>
</head>
<body>
<header><h1>{title}</h1><span>{date}</span>{label}<button type="button" id="fit">{fit}</button></header>
<svg class="markmap" id="mm"></svg>
<footer>{made_with}</footer>
<script>
/* d3 (ISC)
{d3_license}
*/
</script>
<script>{d3}</script>
<script>
/* markmap-view (MIT)
{view_license}
*/
</script>
<script>{view}</script>
<script>
/* markmap-lib (MIT)
{lib_license}
*/
</script>
<script>{lib}</script>
<script>
(function () {{
  var DATA = {data};
  var PALETTES = {palettes};
  var st = DATA.style;
  function lv(n) {{ return Math.min(Math.max(n.state.depth - 1, 0), 4); }}
  var color;
  if (st.mode === 'level') color = function (n) {{ return st.levels[lv(n)]; }};
  else {{
    var sc = d3.scaleOrdinal(PALETTES[st.theme] || PALETTES.pelangi);
    color = function (n) {{ return sc(st.freeze ? n.state.path.split('.').slice(0, st.freeze + 1).join('.') : n.state.path); }};
  }}
  var md = DATA.md.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  var tr = new markmap.Transformer(markmap.builtInPlugins.filter(function (p) {{ return !/^(hljs|katex|npmUrl)$/.test(p.name); }}));
  var root = tr.transform(md).root;
  var mm = markmap.Markmap.create('#mm', {{
    duration: 350, spacingVertical: 8, paddingX: 10, autoFit: true,
    color: color, lineWidth: function (n) {{ return st.widths[lv(n)]; }},
    maxWidth: st.maxWidth, spacingHorizontal: st.spacingH, initialExpandLevel: st.expand
  }}, root);
  document.getElementById('fit').addEventListener('click', function () {{ mm.fit(); }});
}})();
</script>
</body>
</html>
"""

PALETTES = {
    "pelangi": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"],
    "urai": ["#2e5be6", "#0b7f74", "#d9480f", "#7b4fd6", "#c2255c", "#1d6f42", "#b7791f", "#0e7490"],
    "lembut": ["#6c8ef5", "#4fb3a9", "#f08c5a", "#a98be8", "#e07aa5", "#7fb069", "#e2b45a", "#5ab0d8"],
    "mono": ["#64748b"],
}

DEFAULT_STYLE = {"theme": "pelangi", "mode": "branch", "freeze": 0,
                 "levels": PALETTES["pelangi"][:5], "widths": [2.5, 1.75, 1.5, 1.25, 1],
                 "maxWidth": 260, "spacingH": 70, "expand": -1}


def clean_style(style: dict | None) -> dict:
    out = dict(DEFAULT_STYLE)
    s = style if isinstance(style, dict) else {}
    if s.get("theme") in PALETTES:
        out["theme"] = s["theme"]
    if s.get("mode") in ("branch", "level"):
        out["mode"] = s["mode"]
    if s.get("freeze") in (0, 1, 2, 3):
        out["freeze"] = s["freeze"]
    lv = s.get("levels")
    if isinstance(lv, list) and len(lv) == 5 and all(isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in lv):
        out["levels"] = lv
    w = s.get("widths")
    if isinstance(w, list) and len(w) == 5 and all(isinstance(x, (int, float)) and 0 < x <= 12 for x in w):
        out["widths"] = [float(x) for x in w]
    for k, lo, hi in (("maxWidth", 80, 800), ("spacingH", 10, 300)):
        v = s.get(k)
        if isinstance(v, (int, float)) and lo <= v <= hi:
            out[k] = int(v)
    if s.get("expand") in (-1, 1, 2, 3, 4, 5):
        out["expand"] = s["expand"]
    return out


def save_html(path: Path, md: str, title: str, style: dict | None, show_label: bool) -> Path:
    page = HTML_TEMPLATE.format(
        app=APP_NAME, version=VERSION, title=html.escape(title), lang=get_lang(),
        date=fmt_date(datetime.now()), fit=html.escape(t("export.fit")),
        made_with=html.escape(t("export.made_with", app=APP_NAME)),
        label=f'<span class="chip">{html.escape(ai_label())}</span>' if show_label else "",
        d3=_vendor("d3.min.js"), view=_vendor("markmap-view.js"), lib=_vendor("markmap-lib.js"),
        d3_license=_vendor_license("d3"), view_license=_vendor_license("markmap-view"),
        lib_license=_vendor_license("markmap-lib"),
        data=_json_for_script({"md": md, "style": clean_style(style)}), palettes=_json_for_script(PALETTES),
    )
    path.write_text(page, encoding="utf-8")
    return path


# ---------- PDF ----------

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]
_FONTS: tuple[str, str] | None = None


def _fonts() -> tuple[str, str]:
    """Huruf TrueType dari sistem supaya huruf seperti é, –, dan • tercetak benar."""
    global _FONTS
    if _FONTS:
        return _FONTS
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    windir = os.environ.get("WINDIR")
    cands = list(_FONT_CANDIDATES)
    if windir:
        cands.insert(0, (f"{windir}/Fonts/segoeui.ttf", f"{windir}/Fonts/segoeuib.ttf"))
    for reg, bold in cands:
        if os.path.exists(reg) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont("UraiSans", reg))
                pdfmetrics.registerFont(TTFont("UraiSans-Bold", bold))
                _FONTS = ("UraiSans", "UraiSans-Bold")
                return _FONTS
            except Exception:
                continue
    _FONTS = ("Helvetica", "Helvetica-Bold")
    return _FONTS


def _outline_rows(md: str) -> list[tuple[int, str, bool]]:
    """(tingkat, teks, judul?) untuk halaman teks."""
    rows = []
    level = 0
    for raw in md.splitlines():
        if not raw.strip():
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", raw.strip())
        if m:
            level = len(m.group(1))
            rows.append((level, m.group(2).strip(), True))
            continue
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", raw)
        if m:
            indent = len(m.group(1).replace("\t", "  ")) // 2
            rows.append((level + 1 + indent, m.group(2).strip(), False))
            continue
        rows.append((level + 1, raw.strip(), False))
    return rows


def _inline(text: str) -> str:
    """Teks aman untuk Paragraph reportlab, dengan **tebal** dan *miring* sederhana."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", out)
    return out


def save_pdf(path: Path, png: bytes, md: str, title: str, *, size: str = "A4", orient: str = "land",
             show_title: bool = True, show_label: bool = False, text_page: bool = False) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer

    regular, bold = _fonts()
    pw, ph = page_size(size, orient)
    margin = 12 * MM
    img = ImageReader(io.BytesIO(png))
    iw, ih = img.getSize()
    stamp = fmt_date(datetime.now())
    label = ai_label()
    ink, muted, warn_bg, warn_ink = colors.HexColor("#111827"), colors.HexColor("#64748B"), colors.HexColor("#FCF0DF"), colors.HexColor("#A65A05")

    class MapPage(Flowable):
        def wrap(self, aw, ah):
            self.aw, self.ah = aw, ah
            return aw, ah

        def draw(self):
            c = self.canv
            top = self.ah
            if show_title:
                c.setFillColor(ink)
                c.setFont(bold, 16)
                name = title
                while c.stringWidth(name, bold, 16) > self.aw - 90 and len(name) > 4:
                    name = name[:-2]
                if name != title:
                    name = name.rstrip() + "…"
                c.drawString(0, top - 16, name)
                c.setFillColor(muted)
                c.setFont(regular, 10)
                c.drawRightString(self.aw, top - 14, stamp)
                c.setStrokeColor(colors.HexColor("#E2E8F0"))
                c.setLineWidth(0.6)
                c.line(0, top - 24, self.aw, top - 24)
                top -= 32
            bottom = 0
            if show_label:
                c.setFont(regular, 8.5)
                tw = c.stringWidth(label, regular, 8.5)
                c.setFillColor(warn_bg)
                c.roundRect(0, 0, tw + 14, 15, 4, stroke=0, fill=1)
                c.setFillColor(warn_ink)
                c.drawString(7, 4.4, label)
                bottom = 22
            avail_w, avail_h = self.aw, top - bottom
            k = min(avail_w / iw, avail_h / ih)
            dw, dh = iw * k, ih * k
            c.drawImage(img, (avail_w - dw) / 2, bottom + (avail_h - dh) / 2, dw, dh, mask="auto")

    doc = SimpleDocTemplate(str(path), pagesize=(pw, ph), leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin, title=title, author=APP_NAME,
                            creator=f"{APP_NAME} {VERSION}", subject="Mind map")
    story: list = [MapPage()]
    if text_page:
        story.append(PageBreak())
        h = ParagraphStyle("h", fontName=bold, fontSize=15, leading=19, textColor=ink, spaceAfter=8)
        story.append(Paragraph(_inline(title), h))
        if show_label:
            story.append(Paragraph(_inline(label), ParagraphStyle("l", fontName=regular, fontSize=9, leading=12, textColor=warn_ink, spaceAfter=8)))
        for level, text, is_head in _outline_rows(md):
            if level == 1 and is_head:
                continue  # judul utama sudah ditulis di atas
            indent = max(0, level - 2) * 14
            if is_head:
                st = ParagraphStyle(f"h{level}", fontName=bold, fontSize=12 if level == 2 else 11, leading=16,
                                    textColor=ink, leftIndent=indent, spaceBefore=8 if level == 2 else 4, spaceAfter=2)
                story.append(Paragraph(_inline(text), st))
            else:
                st = ParagraphStyle(f"b{level}", fontName=regular, fontSize=10.5, leading=14.5, textColor=colors.HexColor("#374151"),
                                    leftIndent=indent + 12, bulletIndent=indent + 2, spaceAfter=1)
                story.append(Paragraph(_inline(text), st, bulletText="•"))
        story.append(Spacer(1, 10))
    doc.build(story)
    return path
