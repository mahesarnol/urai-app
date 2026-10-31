"""Jembatan antara tampilan (HTML/JS) dan mesin Python.

Setiap method publik di kelas Api bisa dipanggil dari JavaScript sebagai window.pywebview.api.<nama>().
Atribut internal wajib diawali garis bawah supaya tidak ikut terbuka ke JavaScript.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from collections import deque
from pathlib import Path

from . import ai as ai_mod
from . import export as export_mod
from . import i18n, info
from .convert import Item, Options, item_from_link, item_from_path, run_job
from .errors import Cancelled, error_ref, friendly_error
from .fileinfo import SUPPORTED_EXT
from .i18n import t
from .links import normalize_link
from .ocr import engine, lang_names, reset_engine
from .paths import default_output_dir, notices_file, samples_dir, web_dir
from .settings import Settings, get_key, has_key, set_key
from .summarize import Summarizer, clean_kind, struct_combined, struct_outline
from .textutil import (COMBINED_SEP, base_name, build_combined, combined_section, combined_sections, safe_filename,
                       unique_path, word_count, write_atomic)

log = logging.getLogger("urai.api")

MAX_ITEMS = 500
FOLDER_SKIP_EXT = {".md"}  # hasil konversi sebelumnya tidak ikut ditambahkan saat memilih folder


def file_types() -> tuple[str, str]:
    """Saringan jendela pilih file, dalam bahasa aktif."""
    return t("dlg.supported", ext=";".join(f"*{e}" for e in sorted(SUPPORTED_EXT))), t("dlg.all")


class Dialogs:
    """Jendela pilih file/folder dari Windows (lewat pywebview)."""

    def __init__(self, window):
        self._window = window

    def open_files(self, directory: str = "") -> list[str]:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.OPEN, directory=directory, allow_multiple=True, file_types=file_types())
        return list(res or [])

    def open_folder(self, directory: str = "") -> str:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=directory)
        if isinstance(res, (list, tuple)):
            res = res[0] if res else None
        return res or ""

    def save_file(self, directory: str, filename: str, file_type: str) -> str:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.SAVE, directory=directory, save_filename=filename, file_types=(file_type,))
        if isinstance(res, (list, tuple)):
            res = res[0] if res else None
        return res or ""


def _open_with_system(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 - membuka file hasil dengan aplikasi bawaan Windows
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _copy_windows(text: str) -> bool:
    import ctypes
    from ctypes import wintypes

    CF_UNICODETEXT, GMEM_MOVEABLE = 13, 0x0002
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalLock.restype = wintypes.LPVOID
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    data = text.encode("utf-16-le") + b"\x00\x00"
    if not u32.OpenClipboard(None):
        return False
    try:
        u32.EmptyClipboard()
        h = k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        p = k32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        k32.GlobalUnlock(h)
        return bool(u32.SetClipboardData(CF_UNICODETEXT, h))
    finally:
        u32.CloseClipboard()


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


class Api:
    def __init__(self, settings: Settings | None = None, dev: bool = False):
        self._settings = settings or Settings()
        self._dev = dev
        self._dialogs = None  # diisi oleh app.py (Dialogs) atau devserver.py
        self._items: list[Item] = []
        self._lock = threading.RLock()
        self._events: deque = deque(maxlen=5000)
        self._ev_lock = threading.Lock()
        self._job: threading.Thread | None = None
        self._cancel = threading.Event()
        self._combined_text = ""
        self._combined_path = ""
        self._summary: dict = {}
        self._combined_edited = False  # file gabungan sudah disunting pengguna; jangan disusun ulang dari hasil per dokumen
        self._text_gen = 0  # naik setiap pengguna menyunting; rangkuman yang mulai sebelumnya tidak disimpan di cache
        self._mm_cancel = threading.Event()
        self._mm_thread: threading.Thread | None = None
        self._produced: set[str] = set()  # file yang dibuat aplikasi ini; hanya ini yang boleh dibuka dari tampilan
        self._ready = threading.Event()
        self._finished = False  # hasil terakhir masih tampil; dokumen baru akan memulai daftar baru
        i18n.set_lang(self._settings.get("lang"))

    # ---------- event ke tampilan ----------
    def _emit(self, kind: str, data: dict | None = None) -> None:
        with self._ev_lock:
            self._events.append({"type": kind, **(data or {})})

    def poll(self) -> list:
        """Dipanggil tampilan beberapa kali per detik untuk mengambil kabar terbaru."""
        with self._ev_lock:
            out = list(self._events)
            self._events.clear()
        return out

    def ready(self) -> bool:
        """Tampilan sudah dimuat (dipakai uji asap di GitHub Actions)."""
        self._ready.set()
        return True

    # ---------- informasi awal ----------
    def _busy(self) -> bool:
        return bool(self._job and self._job.is_alive())

    def _items_public(self) -> list:
        return [i.public() for i in self._items]

    def _keys(self) -> dict:
        return {p: has_key(p) for p in ai_mod.PROVIDERS}

    def _tesseract(self) -> dict:
        tess = engine()
        langs = tess.languages() if tess.available else []
        return {"available": tess.available, "version": tess.version() if tess.available else "", "langs": langs,
                "names": lang_names()}

    def _app(self) -> dict:
        return {"name": info.APP_NAME, "version": info.VERSION, "commit": info.COMMIT, "tagline": t("app.tagline"),
                "developer": info.DEVELOPER, "merchant": info.SUPPORT_MERCHANT, "year": info.YEAR,
                "repo": info.repo_url()}

    @staticmethod
    def _providers() -> dict:
        return {k: {"name": ai_mod.provider_name(k), "model": v["model"], "base_url": v["base_url"],
                    "has_link": bool(v["key_link"])} for k, v in ai_mod.PROVIDERS.items()}

    def init(self) -> dict:
        s = self._settings
        return {
            "app": self._app(),
            "settings": s.public(),
            "providers": self._providers(),
            "models": {p: s.model_for(p) for p in ai_mod.PROVIDERS},
            "base_urls": {p: s.base_url_for(p) for p in ai_mod.PROVIDERS},
            "keys": self._keys(),
            "tesseract": self._tesseract(),
            "default_dir": str(default_output_dir()),
            "items": self._items_public(),
            "has_qris": (web_dir() / "img" / "qris.png").exists(),
            "has_samples": samples_dir().exists() and any(samples_dir().iterdir()),
            "dev": self._dev,
        }

    # ---------- daftar dokumen ----------
    def _add_paths(self, paths, from_folder: bool = False) -> dict:
        added, skipped = 0, 0
        with self._lock:
            if self._busy():
                return {"ok": False, "error": t("api.busy_wait"), "items": self._items_public()}
            fresh = False
            if self._finished and self._any_supported(paths, from_folder):
                # hasil sebelumnya masih tampil: dokumen baru memulai daftar baru (hanya bila memang ada yang bisa ditambah)
                self._items, self._combined_text, self._combined_path, self._summary = [], "", "", {}
                self._finished, self._combined_edited, fresh = False, False, True
            known = {os.path.normcase(i.source) for i in self._items if not i.is_link}
            for raw in paths or []:
                if not raw:
                    continue
                p = Path(raw)
                if p.is_dir():
                    res = self._scan_folder(p, known)
                    added += res[0]
                    skipped += res[1]
                    continue
                if not p.is_file() or p.suffix.lower() not in SUPPORTED_EXT or p.name.startswith("~$"):
                    skipped += 1
                    continue
                if (from_folder and p.suffix.lower() in FOLDER_SKIP_EXT) or os.path.normcase(str(p)) in known:
                    continue
                if len(self._items) >= MAX_ITEMS:
                    skipped += 1
                    continue
                self._items.append(item_from_path(p))
                known.add(os.path.normcase(str(p)))
                added += 1
            items = self._items_public()
        return {"ok": True, "added": added, "skipped": skipped, "items": items, "fresh": fresh}

    @staticmethod
    def _supported_file(p: Path, from_folder: bool) -> bool:
        ext = p.suffix.lower()
        return (ext in SUPPORTED_EXT and not p.name.startswith(("~$", "."))
                and not (from_folder and ext in FOLDER_SKIP_EXT))

    def _any_supported(self, paths, from_folder: bool) -> bool:
        for raw in paths or []:
            if not raw:
                continue
            p = Path(raw)
            if p.is_file() and self._supported_file(p, from_folder):
                return True
            if p.is_dir():
                for _root, _dirs, names in os.walk(p):
                    if any(self._supported_file(Path(n), True) for n in names):
                        return True
        return False

    def _scan_folder(self, folder: Path, known: set) -> tuple[int, int]:
        added = skipped = 0
        files = []
        for root, dirs, names in os.walk(folder):
            dirs[:] = sorted(d for d in dirs if not d.startswith((".", "$")) and d.lower() != "node_modules")
            for n in sorted(names):
                files.append(Path(root) / n)
            if len(files) > MAX_ITEMS * 4:
                break
        for p in files:
            ext = p.suffix.lower()
            if ext not in SUPPORTED_EXT or ext in FOLDER_SKIP_EXT or p.name.startswith(("~$", ".")):
                continue
            if os.path.normcase(str(p)) in known:
                continue
            if len(self._items) >= MAX_ITEMS:
                skipped += 1
                continue
            self._items.append(item_from_path(p))
            known.add(os.path.normcase(str(p)))
            added += 1
        return added, skipped

    def _drop(self, paths: list[str]) -> None:
        """Dipanggil app.py saat file ditarik ke jendela."""
        res = self._add_paths(paths)
        self._emit("dropped", res)

    def add_paths(self, paths: list) -> dict:
        return self._add_paths([str(p) for p in (paths or [])])

    def pick_files(self) -> dict:
        if not self._dialogs:
            return {"ok": False, "error": t("api.no_file_dialog")}
        start = self._items[-1].source if self._items and not self._items[-1].is_link else ""
        paths = self._dialogs.open_files(str(Path(start).parent) if start else "")
        if not paths:
            return {"ok": True, "added": 0, "skipped": 0, "items": self._items_public(), "cancelled": True}
        return self._add_paths(paths)

    def pick_folder(self) -> dict:
        if not self._dialogs:
            return {"ok": False, "error": t("api.no_folder_dialog")}
        folder = self._dialogs.open_folder()
        if not folder:
            return {"ok": True, "added": 0, "skipped": 0, "items": self._items_public(), "cancelled": True}
        res = self._add_paths([folder], from_folder=True)
        res["folder"] = Path(folder).name
        return res

    def add_samples(self) -> dict:
        files = sorted(str(p) for p in samples_dir().iterdir() if p.is_file()) if samples_dir().exists() else []
        res = self._add_paths(files)
        res["folder"] = t("samples.folder")
        return res

    def add_link(self, text: str) -> dict:
        url = normalize_link(text)
        if not url:
            return {"ok": False, "error": t("api.bad_link")}
        with self._lock:
            if self._busy():
                return {"ok": False, "error": t("api.busy_wait")}
            if any(i.is_link and i.source == url for i in self._items):
                return {"ok": False, "error": t("api.dup_link")}
            if len(self._items) >= MAX_ITEMS:
                return {"ok": False, "error": t("api.list_full", n=MAX_ITEMS)}
            self._items.append(item_from_link(url))
            return {"ok": True, "items": self._items_public()}

    def remove_item(self, item_id: str) -> dict:
        with self._lock:
            if self._busy():
                return {"ok": False, "error": t("api.busy_wait"), "items": self._items_public()}
            self._items = [i for i in self._items if i.id != item_id]
            return {"ok": True, "items": self._items_public()}

    def remove_items(self, ids: list) -> dict:
        """Hapus beberapa dokumen dari daftar sekaligus (sebelum atau sesudah diubah). File di disk tidak pernah dihapus."""
        drop = {str(i) for i in ids if isinstance(i, (str, int))} if isinstance(ids, (list, tuple)) else set()
        with self._lock:
            if self._busy():
                return {"ok": False, "error": t("api.busy_wait")}
            removed = [i.id for i in self._items if i.id in drop]
            self._items = [i for i in self._items if i.id not in drop]
            if not self._items:
                self._combined_text, self._combined_path, self._summary = "", "", {}
                self._finished = self._combined_edited = False
            elif removed:
                # rangkuman "ALL" dari hasil per dokumen ikut berubah; yang dari file gabungan suntingan tidak
                prefixes = tuple(f"{r}|" for r in removed) + (() if self._combined_edited else ("ALL|",))
                self._summary = {k: v for k, v in self._summary.items() if not k.startswith(prefixes)}
            return {"ok": True, "items": self._items_public()}

    def reorder(self, ids: list) -> dict:
        with self._lock:
            if self._busy():
                return {"ok": False, "items": self._items_public()}
            by_id = {i.id: i for i in self._items}
            ordered = [by_id[i] for i in ids if i in by_id]
            rest = [i for i in self._items if i.id not in set(ids)]
            self._items = ordered + rest
            return {"ok": True, "items": self._items_public()}

    def clear(self) -> dict:
        with self._lock:
            if self._busy():
                return {"ok": False, "items": self._items_public()}
            self._items = []
            self._combined_text = ""
            self._combined_path = ""
            self._summary = {}
            self._finished = self._combined_edited = False
            return {"ok": True, "items": []}

    def reset_results(self) -> dict:
        """Kembali ke pengaturan tanpa menghapus daftar ("Ubah pengaturan, ulangi")."""
        with self._lock:
            if self._busy():
                return {"ok": False, "items": self._items_public()}
            for i in self._items:
                i.reset()
            self._combined_text = ""
            self._combined_path = ""
            self._summary = {}
            self._finished = self._combined_edited = False
            return {"ok": True, "items": self._items_public()}

    # ---------- pengaturan ----------
    def save_settings(self, patch: dict) -> dict:
        out = self._settings.update(patch or {})
        if "lang" in (patch or {}):
            self._apply_lang()
        return out

    def _apply_lang(self) -> None:
        """Pakai bahasa dari pengaturan dan terjemahkan ulang teks buatan aplikasi di daftar."""
        i18n.set_lang(self._settings.get("lang"))
        with self._lock:
            for i in self._items:
                i.localize()

    def set_language(self, lang: str) -> dict:
        """Ganti bahasa aplikasi (en | id). Mengembalikan data yang teksnya ikut berganti, bentuknya sama dengan init()."""
        if lang not in i18n.LANGS:
            return {"ok": False, "error": t("api.bad_lang")}
        self._settings.update({"lang": lang})
        self._apply_lang()
        return {"ok": True, "settings": self._settings.public(), "items": self._items_public(), "app": self._app(),
                "providers": self._providers(), "tesseract": self._tesseract()}

    def set_ai(self, provider: str, key=None, model: str = "", base_url=None) -> dict:
        if provider not in ai_mod.PROVIDERS:
            return {"ok": False, "error": t("api.unknown_provider")}
        s = self._settings
        models = dict(s.get("models"))
        default_model = ai_mod.PROVIDERS[provider]["model"]
        if model and model.strip() != default_model:
            models[provider] = model.strip()
        else:
            models.pop(provider, None)
        patch = {"provider": provider, "models": models}
        if base_url is not None:
            urls = dict(s.get("base_urls"))
            default_url = ai_mod.PROVIDERS[provider]["base_url"]
            if base_url.strip() and base_url.strip() != default_url:
                urls[provider] = base_url.strip()
            else:
                urls.pop(provider, None)
            patch["base_urls"] = urls
        s.update(patch)
        where = ""
        if key is not None and key != "":
            where = set_key(provider, key)
        return {"ok": True, "keys": self._keys(), "settings": s.public(), "stored": where,
                "models": {p: s.model_for(p) for p in ai_mod.PROVIDERS},
                "base_urls": {p: s.base_url_for(p) for p in ai_mod.PROVIDERS}}

    def forget_key(self, provider: str) -> dict:
        if provider in ai_mod.PROVIDERS:
            set_key(provider, "")
        return {"ok": True, "keys": self._keys()}

    def _ai_config(self, provider: str | None = None, key: str | None = None, model: str | None = None,
                   base_url: str | None = None) -> ai_mod.AIConfig:
        s = self._settings
        provider = provider or s.get("provider")
        return ai_mod.AIConfig(provider, key or get_key(provider), model or s.model_for(provider),
                               s.base_url_for(provider) if base_url is None else base_url)

    def test_ai(self, provider: str, key: str = "", model: str = "", base_url=None) -> dict:
        saved_url = self._settings.base_url_for(provider)
        if not (key or "").strip() and base_url not in (None, "") and base_url.strip() != saved_url:
            # API key tersimpan hanya dikirim ke alamat server yang sudah disimpan, tidak ke alamat baru
            return {"ok": False, "message": t("api.url_changed")}
        cfg = self._ai_config(provider, key, model, base_url if base_url not in (None, "") else None)
        if not cfg.api_key:
            return {"ok": False, "message": t("api.need_key")}
        if provider == "other" and not cfg.base_url:
            return {"ok": False, "message": t("api.need_url")}
        if not cfg.model:
            return {"ok": False, "message": t("api.need_model")}
        try:
            answer = ai_mod.test_connection(cfg)
        except Exception as e:  # noqa: BLE001
            log.info("Tes koneksi gagal: %s", e)
            return {"ok": False, "message": friendly_error(e)}
        return {"ok": True, "message": t("api.connected", name=cfg.name), "answer": answer[:60]}

    def choose_output_dir(self) -> dict:
        if not self._dialogs:
            return {"ok": False}
        current = self._settings.get("custom_dir") or str(default_output_dir())
        folder = self._dialogs.open_folder(current if os.path.isdir(current) else "")
        if not folder:
            return {"ok": False, "cancelled": True}
        return {"ok": True, "path": folder, "settings": self._settings.update({"custom_dir": folder, "location": "custom"})}

    def recheck_tesseract(self) -> dict:
        reset_engine()
        return self._tesseract()

    # ---------- konversi ----------
    def _options(self) -> Options:
        s = self._settings
        cfg = self._ai_config() if s.get("ocr_mode") == "ai" else None
        return Options(ocr_mode=s.get("ocr_mode"), langs=list(s.get("langs")), quality=s.get("quality"),
                       embedded=bool(s.get("embedded")), ai=cfg, out_mode=s.get("out_mode"),
                       combined_name=s.combined_name(), location=s.get("location"),
                       custom_dir=s.get("custom_dir"))

    def start(self) -> dict:
        with self._lock:
            if self._busy():
                return {"ok": False, "error": t("api.busy")}
            if not self._items:
                return {"ok": False, "error": t("api.no_items")}
            opts = self._options()
            if opts.ocr_mode == "ai" and not (opts.ai and opts.ai.ready):
                return {"ok": False, "error": t("api.ai_needs_key"), "open": "ai"}
            self._cancel = threading.Event()
            self._combined_text = ""
            self._combined_path = ""
            self._summary = {}
            self._finished = self._combined_edited = False
            items = list(self._items)
            self._job = threading.Thread(target=self._run, args=(items, opts, self._cancel), daemon=True, name="urai-job")
            self._job.start()
        return {"ok": True}

    def _run(self, items: list[Item], opts: Options, cancel: threading.Event) -> None:
        try:
            res = run_job(items, opts, self._emit, cancel)
            s = res["summary"]
            self._combined_text = res["combined_text"]
            self._combined_path = s["combined_path"]
            for i in items:
                if i.output:
                    self._produced.add(os.path.normcase(i.output))
            if self._combined_path:
                self._produced.add(os.path.normcase(self._combined_path))
            if not s["cancelled"]:
                self._finished = True
                if s["ok"] or s["warn"]:
                    self._settings.update({"runs": self._settings.get("runs") + 1})
            s["runs"] = self._settings.get("runs")
            self._emit("finished", {"summary": s, "items": [i.public() for i in items]})
        except Exception as e:  # noqa: BLE001 - jangan sampai tampilan menunggu selamanya
            log.exception("Proses gagal")
            self._emit("failed", {"error": friendly_error(e), "items": [i.public() for i in items]})

    def cancel(self) -> bool:
        self._cancel.set()
        return True

    def reread(self, item_id: str) -> dict:
        """Baca ulang satu dokumen (tombol "Aktifkan baca scan offline" di baris yang perlu dicek)."""
        with self._lock:
            if self._busy():
                return {"ok": False, "error": t("api.busy")}
            item = next((i for i in self._items if i.id == item_id), None)
            if not item:
                return {"ok": False, "error": t("api.not_in_list")}
            opts = self._options()
            if opts.ocr_mode == "off":
                opts.ocr_mode = "offline"
            section = None  # bagian dokumen ini di file gabungan yang sudah disunting; "" berarti belum ada
            if opts.out_mode == "combined" and self._combined_edited:
                if item.status in ("done", "warn"):
                    section = next((c for c in combined_sections(item.display_name, item.result) if c in self._combined_text), None)
                    if section is None:  # bagian ini ikut disunting: membaca ulang akan menimpa suntingan
                        return {"ok": False, "error": t("edit.reread_conflict")}
                else:
                    section = ""
            self._cancel = threading.Event()
            self._job = threading.Thread(target=self._reread, args=(item, opts, self._cancel, section), daemon=True,
                                         name="urai-reread")
            self._job.start()
        return {"ok": True}

    def _reread(self, item: Item, opts: Options, cancel: threading.Event, section: str | None = None) -> None:
        old_output = item.output
        try:
            combined = opts.out_mode == "combined"
            if combined:
                # tulis ke file gabungan yang sama, bukan file baru
                opts.out_mode = "separate"
                opts.custom_dir = ""
            from .convert import Converter, _empty_message

            conv = Converter(opts, self._emit, cancel)
            item.reset()
            item.status = "work"
            self._emit("item", item.public())
            try:
                text = conv.convert_item(item).strip()
            except Cancelled:
                item.status = "idle"
                self._emit("item", item.public())
                return
            except Exception as e:  # noqa: BLE001
                item.status = "error"
                item.say_error(e)
                self._emit("item", item.public())
                self._emit("reread_done", {"id": item.id, "ok": False})
                return
            item.result, item.words, item.sub = text, word_count(text), ""
            item.status = "done" if text else "warn"
            if not text:
                key, item.fix = _empty_message(item, opts)
                item.say(key)
            if combined:
                if section is None:
                    entries = [(i.display_name, i.result) for i in self._items if i.status in ("done", "warn")]
                    self._combined_text = build_combined(entries)
                else:  # file gabungan sudah disunting: ganti bagian dokumen ini saja, suntingan lain tetap
                    new = combined_section(item.display_name, item.result)
                    if section:
                        self._combined_text = self._combined_text.replace(section, new, 1)
                    else:
                        self._combined_text = self._combined_text.rstrip("\n") + COMBINED_SEP + new + "\n"
                if self._combined_path:
                    write_atomic(Path(self._combined_path), self._combined_text)
            elif text:
                from .convert import _write, output_dir_for

                if old_output and Path(old_output).exists() and Path(old_output).stat().st_size <= 2:
                    Path(old_output).unlink(missing_ok=True)
                o = self._options()
                stem = safe_filename(item.title, "link") if item.is_link else Path(item.source).stem
                target = _write(output_dir_for(item, o) / f"{stem}.md", text + "\n")
                item.output = str(target)
                self._produced.add(os.path.normcase(item.output))
            self._summary = {k: v for k, v in self._summary.items() if not (k.startswith(item.id + "|") or k.startswith("ALL|"))}
            self._emit("item", item.public())
            self._emit("reread_done", {"id": item.id, "ok": item.status == "done",
                                       "combined_words": word_count(self._combined_text)})
        except Exception as e:  # noqa: BLE001
            log.exception("Baca ulang gagal")
            item.status = "error"
            item.say_error(e)
            self._emit("item", item.public())
            self._emit("reread_done", {"id": item.id, "ok": False})

    def result_text(self, key: str) -> str:
        if key == "ALL":
            return self._combined_text
        item = next((i for i in self._items if i.id == key), None)
        return item.result if item else ""

    # ---------- menyunting hasil ----------
    @staticmethod
    def _write_error(exc: BaseException) -> str:
        key, kw = error_ref(exc)
        return t("edit.write_failed") if key == "err.other" else t(key, **kw)

    def save_result(self, key: str, md: str) -> dict:
        """Simpan Markdown yang disunting pengguna. key = id dokumen (file terpisah) atau "ALL" (file gabungan).
        File ditulis lewat file sementara lalu diganti sekaligus; bila gagal, file lama tetap utuh."""
        if not isinstance(md, str):
            return {"ok": False, "error": t("edit.bad_text")}
        text = md.replace("\r\n", "\n").strip()
        with self._lock:
            if self._busy():
                return {"ok": False, "error": t("api.busy_wait")}
            item = None
            if key == "ALL":
                if not self._combined_path:
                    return {"ok": False, "error": t("edit.no_combined")}
                target = Path(self._combined_path)
            else:
                item = next((i for i in self._items if i.id == key), None)
                if not item:
                    return {"ok": False, "error": t("api.not_in_list")}
                if self._combined_path:  # hasil berupa satu file gabungan: yang disunting file itu
                    return {"ok": False, "error": t("edit.combined_only")}
                if not item.output:
                    return {"ok": False, "error": t("edit.no_file")}
                target = Path(item.output)
            try:
                write_atomic(target, text + "\n")
            except Exception as e:  # noqa: BLE001 - file dikunci, folder hilang, disk penuh
                log.warning("Simpan suntingan gagal: %s", e)
                return {"ok": False, "error": self._write_error(e)}
            self._text_gen += 1
            if item is None:
                self._combined_text, self._combined_edited = text + "\n", True
                words = combined_words = word_count(self._combined_text)
                stale = ("ALL|",)
            else:
                item.result, item.words = text, word_count(text)
                words, combined_words = item.words, None
                stale = (f"{item.id}|", "ALL|")
            self._summary = {k: v for k, v in self._summary.items() if not k.startswith(stale)}
            return {"ok": True, "items": self._items_public(), "words": words, "combined_words": combined_words,
                    "name": target.name}

    # ---------- membuka file, folder, tautan ----------
    def _allowed(self, path: str) -> bool:
        return bool(path) and os.path.normcase(path) in self._produced and os.path.exists(path)

    def open_output(self, path: str) -> dict:
        if not self._allowed(path):
            return {"ok": False, "error": t("err.not_found")}
        try:
            _open_with_system(path)
            return {"ok": True}
        except OSError as e:
            return {"ok": False, "error": friendly_error(e)}

    def open_folder(self, path: str) -> dict:
        p = Path(path) if path else default_output_dir()
        try:
            if os.path.normcase(str(p)) in self._produced and p.is_file():
                if sys.platform == "win32":
                    subprocess.Popen(["explorer", "/select,", str(p)])
                    return {"ok": True}
                p = p.parent
            known_dirs = {os.path.normcase(str(Path(x).parent)) for x in self._produced} | {os.path.normcase(str(default_output_dir()))}
            if os.path.normcase(str(p)) not in known_dirs or not p.is_dir():
                return {"ok": False, "error": t("api.folder_missing")}
            _open_with_system(str(p))
            return {"ok": True}
        except OSError as e:
            return {"ok": False, "error": friendly_error(e)}

    def open_link(self, key: str) -> bool:
        extra = {"repo": info.repo_url(), "issues": info.issues_url(), "releases": info.releases_url()}
        url = info.LINKS.get(key) or extra.get(key, "")
        if not url:
            return False
        webbrowser.open(url)
        return True

    def open_notices(self) -> dict:
        p = notices_file()
        if not p.exists():
            return {"ok": False, "error": t("api.notices_missing")}
        _open_with_system(str(p))
        return {"ok": True}

    def copy_text(self, text: str) -> bool:
        """Cadangan bila clipboard dari tampilan ditolak."""
        if sys.platform != "win32":
            return False
        try:
            return _copy_windows(text or "")
        except Exception:
            log.debug("Salin ke clipboard gagal", exc_info=True)
            return False

    def check_update(self) -> dict:
        if not info.GITHUB_REPO:
            return {"ok": False, "message": t("upd.self_built")}
        url = f"https://api.github.com/repos/{info.GITHUB_REPO}/releases/latest"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"UraiApp/{info.VERSION}"})
            with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 - alamat tetap ke api.github.com
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            log.info("Cek pembaruan gagal: %s", e)
            return {"ok": False, "message": t("upd.failed")}
        latest = str(data.get("tag_name", "")).lstrip("vV")
        if latest and _version_tuple(latest) > _version_tuple(info.VERSION):
            return {"ok": True, "newer": True, "version": latest, "message": t("upd.newer", v=latest)}
        return {"ok": True, "newer": False, "message": t("upd.latest", v=info.VERSION)}

    def support_done(self) -> dict:
        return self._settings.update({"supported": True})

    # ---------- rangkuman dan mind map ----------
    def _entries(self) -> list[tuple[str, str]]:
        return [(i.display_name, i.result) for i in self._items if i.status in ("done", "warn")]

    @staticmethod
    def _summary_key(key: str, src: str, kind: str) -> str:
        return f"{key}|{src}|{clean_kind(kind) if src == 'ai' else '-'}"

    def summarize(self, key: str, src: str, kind: str = "poin") -> dict:
        """Mulai membuat rangkuman. Hasilnya dikirim sebagai event 'mm'."""
        kind = clean_kind(kind)
        cache_key = self._summary_key(key, src, kind)
        if cache_key in self._summary:
            self._emit("mm", {"state": "done", "key": key, "src": src, "kind": kind, "md": self._summary[cache_key]})
            return {"ok": True, "cached": True}
        if src == "struct":
            try:
                md = self._struct(key)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": friendly_error(e)}
            self._summary[cache_key] = md
            self._emit("mm", {"state": "done", "key": key, "src": src, "kind": kind, "md": md})
            return {"ok": True}
        cfg = self._ai_config()
        if not cfg.ready:
            return {"ok": False, "error": t("mm.ai_needs_key"), "open": "ai"}
        if self._mm_thread and self._mm_thread.is_alive():
            self._mm_cancel.set()
        self._mm_cancel = threading.Event()
        cancel = self._mm_cancel
        self._mm_thread = threading.Thread(target=self._summarize, args=(key, src, kind, cache_key, cfg, cancel, self._text_gen),
                                           daemon=True)
        self._mm_thread.start()
        return {"ok": True}

    def _struct(self, key: str) -> str:
        if key == "ALL":
            if self._combined_edited:  # pakai isi file gabungan yang sudah disunting
                return struct_outline(self._settings.combined_name(), self._combined_text)
            return struct_combined(self._settings.combined_name(), self._entries())
        item = next((i for i in self._items if i.id == key), None)
        if not item:
            raise LookupError(t("api.not_in_list"))
        return struct_outline(item.display_name, item.result)

    def _summarize(self, key, src, kind, cache_key, cfg, cancel, gen: int = 0) -> None:
        def progress(text: str) -> None:
            if not cancel.is_set():
                self._emit("mm", {"state": "progress", "key": key, "text": text})

        try:
            sm = Summarizer(cfg, kind, progress, cancel)
            if key == "ALL" and self._combined_edited:
                md = sm.one(self._settings.combined_name(), self._combined_text)
            elif key == "ALL":
                md = sm.many(self._settings.combined_name(), self._entries())
            else:
                item = next((i for i in self._items if i.id == key), None)
                if not item:
                    raise LookupError(t("api.not_in_list"))
                md = sm.one(item.display_name, item.result)
            if cancel.is_set():
                return
            if gen == self._text_gen:  # teks atau mind map disunting selama proses: hasil ini sudah usang untuk cache
                self._summary[cache_key] = md
            self._emit("mm", {"state": "done", "key": key, "src": src, "kind": kind, "md": md})
        except Cancelled:
            return
        except Exception as e:  # noqa: BLE001
            log.info("Rangkuman gagal: %s", e)
            if not cancel.is_set():
                self._emit("mm", {"state": "error", "key": key, "error": friendly_error(e)})

    def cancel_summary(self) -> bool:
        self._mm_cancel.set()
        return True

    def forget_summary(self, key: str, src: str, kind: str = "poin") -> bool:
        self._summary.pop(self._summary_key(key, src, kind), None)
        return True

    def update_summary(self, key: str, src: str, kind: str, md: str) -> dict:
        """Simpan kerangka mind map yang disunting pengguna. summarize() berikutnya untuk kombinasi yang sama
        mengembalikannya dari cache."""
        if src not in ("struct", "ai"):
            return {"ok": False, "error": t("edit.bad_src")}
        if not isinstance(md, str) or not md.strip():
            return {"ok": False, "error": t("edit.empty_map")}
        if key != "ALL" and not any(i.id == key for i in self._items):
            return {"ok": False, "error": t("api.not_in_list")}
        self._text_gen += 1
        self._summary[self._summary_key(key, src, kind)] = md.replace("\r\n", "\n").strip()
        return {"ok": True}

    def export_map(self, fmt: str, payload: dict) -> dict:
        """Simpan mind map. payload: md, title, style, ai (bool), png (data URL), pdf (opsi kertas)."""
        fmt = fmt if fmt in ("md", "html", "png", "pdf") else "md"
        title = (payload.get("title") or "Mind map").strip()[:150]
        md = payload.get("md") or ""
        names = {f: t(f"dlg.{f}") for f in ("md", "html", "png", "pdf")}
        filename = f"{safe_filename(title, 'Mind map')} - mind map.{fmt}"
        out_dir = self._last_out_dir()
        if self._dialogs:
            chosen = self._dialogs.save_file(str(out_dir), filename, names[fmt])
            if not chosen:
                return {"ok": False, "cancelled": True}
            path = Path(chosen)
        else:
            path = unique_path(out_dir / filename)
        if path.suffix.lower() != f".{fmt}":
            path = path.with_name(path.name + f".{fmt}")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if fmt == "md":
                export_mod.save_md(path, md)
            elif fmt == "html":
                export_mod.save_html(path, md, title, payload.get("style"), bool(payload.get("ai")))
            elif fmt == "png":
                export_mod.save_png(path, payload.get("png", ""))
            else:
                p = payload.get("pdf") or {}
                self._settings.update({"pdf": p})
                export_mod.save_pdf(path, export_mod.decode_data_url(payload.get("png", "")), md, title,
                                    size=p.get("size", "A4"), orient=p.get("orient", "land"),
                                    show_title=bool(p.get("title", True)), show_label=bool(p.get("label")) and bool(payload.get("ai")),
                                    text_page=bool(p.get("text")))
        except Exception as e:  # noqa: BLE001
            log.exception("Simpan mind map gagal")
            return {"ok": False, "error": friendly_error(e)}
        self._produced.add(os.path.normcase(str(path)))
        return {"ok": True, "path": str(path), "name": path.name}

    def _last_out_dir(self) -> Path:
        for i in reversed(self._items):
            if i.output:
                return Path(i.output).parent
        if self._combined_path:
            return Path(self._combined_path).parent
        custom = self._settings.get("custom_dir")
        d = Path(custom) if custom and self._settings.get("location") == "custom" else default_output_dir()
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            d = default_output_dir()
        return d

    def display_names(self) -> dict:
        return {i.id: base_name(i.display_name) for i in self._items}
