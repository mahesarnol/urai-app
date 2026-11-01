"""Titik masuk Urai App: membuka jendela aplikasi.

    urai                      buka aplikasi
    urai file1.pdf file2.docx buka aplikasi dengan file sudah ada di daftar (dipakai menu Kirim ke)
    urai --dev                tampilan di browser biasa, untuk pengembangan
    urai --selftest FOLDER    uji tanpa jendela, hasil di FOLDER/selftest.json
    urai --smoke FILE         buka jendela, tunggu tampilan siap, tutup lagi (uji di GitHub Actions)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import i18n, info
from .i18n import t
from .paths import log_dir, web_dir

log = logging.getLogger("urai")

LIGHT_BG, DARK_BG = "#F2F4F8", "#15181E"


def setup_logging(debug: bool = False) -> None:
    handlers: list[logging.Handler] = []
    try:
        fh = RotatingFileHandler(log_dir() / "urai.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handlers.append(fh)
    except OSError:
        pass
    if sys.stderr and (debug or not getattr(sys, "frozen", False)):
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, handlers=handlers, force=True)
    for noisy in ("pdfminer", "PIL", "urllib3", "httpx", "httpcore", "openai", "pywebview"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def windows_dark() -> bool:
    """Apakah aplikasi Windows memakai tema gelap (Pengaturan > Personalisasi > Warna)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def window_dark(theme: str) -> bool:
    """Warna latar jendela sebelum tampilan dimuat (supaya tidak berkedip putih): ikut pengaturan Tema,
    atau tema Windows bila Tema = system."""
    if theme in ("light", "dark"):
        return theme == "dark"
    return windows_dark()


def load_settings():
    """Baca pengaturan sedini mungkin supaya kotak pesan dan teks lain sudah memakai bahasa pilihan pengguna."""
    try:
        from .settings import Settings

        settings = Settings()
    except Exception:  # noqa: BLE001 - aplikasi tetap jalan dengan pengaturan bawaan
        log.warning("Pengaturan tidak bisa dibaca saat mulai", exc_info=True)
        return None
    i18n.set_lang(settings.get("lang"))
    return settings


def message_box(text: str, title: str = info.APP_NAME, ask: bool = False) -> bool:
    """Kotak pesan Windows. Dengan ask=True ada tombol Ya/Tidak; mengembalikan True bila Ya."""
    if sys.platform == "win32":
        try:
            import ctypes

            flags = 0x34 if ask else 0x10  # MB_ICONWARNING|MB_YESNO atau MB_ICONERROR
            return ctypes.windll.user32.MessageBoxW(None, text, title, flags) == 6  # IDYES
        except Exception:
            pass
    print(text, file=sys.stderr)
    return False


def hide_console_windows() -> None:
    """Aplikasi berjendela tidak boleh memunculkan jendela hitam saat menjalankan program lain
    (mis. ffmpeg yang dipanggil pustaka audio). Tambahkan CREATE_NO_WINDOW bila pemanggil tidak memilih sendiri."""
    if sys.platform != "win32":
        return
    import subprocess

    base = subprocess.Popen
    if getattr(base, "_urai_no_window", False):
        return

    class NoWindowPopen(base):  # type: ignore[misc, valid-type]
        _urai_no_window = True

        def __init__(self, *args, **kwargs):
            if not kwargs.get("creationflags"):
                kwargs["creationflags"] = 0x08000000
            super().__init__(*args, **kwargs)

    subprocess.Popen = NoWindowPopen  # type: ignore[misc]


def webview2_available() -> bool:
    """pywebview diam-diam memakai Internet Explorer bila WebView2 tidak ada; tampilan Urai App tidak jalan di sana."""
    if sys.platform != "win32":
        return True
    try:
        from webview.platforms import winforms

        return getattr(winforms, "renderer", "edgechromium") == "edgechromium"
    except Exception:
        log.exception("Pemeriksaan WebView2 gagal")
        return True


def _on_loaded(window, api, home: dict) -> None:
    """Dipanggil setiap kali halaman selesai dimuat. Jendela hanya boleh menampilkan halaman Urai App sendiri:
    bila sempat berpindah ke situs lain (mis. tautan), kembalikan, karena jembatan ke Python ikut tersedia di sana."""
    try:
        url = window.get_current_url() or ""
    except Exception:
        url = ""
    if not home.get("url") and url:
        home["url"] = url
        home["origin"] = "/".join(url.split("/", 3)[:3])
    elif home.get("origin") and url and not url.startswith(home["origin"] + "/"):
        log.warning("Jendela berpindah ke %s; dikembalikan ke tampilan Urai App", url.split("?", 1)[0][:80])
        window.load_url(home["url"])
        return
    _bind_drop(window, api)


def _bind_drop(window, api) -> None:
    """File yang ditarik dari File Explorer: pywebview memberi path lengkap lewat pywebviewFullPath."""
    from webview.dom import DOMEventHandler

    def on_drop(event) -> None:
        files = (event.get("dataTransfer") or {}).get("files") or []
        paths = [f.get("pywebviewFullPath") for f in files if isinstance(f, dict) and f.get("pywebviewFullPath")]
        if paths:
            api._drop(paths)

    try:
        window.dom.document.events.drop += DOMEventHandler(on_drop, prevent_default=True, stop_propagation=False)
    except Exception:
        log.exception("Tarik-lepas file tidak bisa diaktifkan")


def _smoke_watch(window, api, out: Path, result: dict) -> None:
    ok = api._ready.wait(90)
    result["ready"] = ok
    if ok:
        try:
            result["title"] = window.evaluate_js("document.title")
            result["state"] = window.evaluate_js("document.getElementById('win').dataset.state")
        except Exception as e:  # noqa: BLE001
            result["js_error"] = str(e)
    time.sleep(1)
    try:
        out.write_text(repr(result), encoding="utf-8")
    finally:
        window.destroy()


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(prog="urai", description=t("app.tagline"))
    parser.add_argument("paths", nargs="*", help=t("cli.paths"))
    parser.add_argument("--dev", action="store_true", help=t("cli.dev"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--selftest", metavar="FOLDER")
    parser.add_argument("--smoke", metavar="FILE")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--version", action="version", version=f"{info.APP_NAME} {info.VERSION}")
    args = parser.parse_args(argv)
    setup_logging(args.debug)
    log.info("%s %s mulai (%s)", info.APP_NAME, info.VERSION, sys.platform)
    hide_console_windows()

    if args.selftest:
        from .selftest import run

        return run(args.selftest)

    if args.dev:
        from .devserver import serve

        httpd = serve(args.port, open_browser=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    try:
        import webview
    except Exception:
        log.exception("pywebview tidak bisa dimuat")
        message_box(t("app.broken_ui"))
        return 2

    from .api import Api, Dialogs

    if not webview2_available():
        if args.smoke:
            Path(args.smoke).write_text(repr({"ready": False, "error": "WebView2 tidak ada"}), encoding="utf-8")
            return 3
        if message_box(t("app.need_webview2"), ask=True):
            import webbrowser

            webbrowser.open(info.LINKS["webview2"])
        return 2

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mahesarnol.UraiApp")
        except Exception:
            pass

    api = Api(settings)
    if args.paths:
        api._add_paths([os.path.abspath(p) for p in args.paths])
    dark = window_dark(api._settings.get("theme"))
    window = webview.create_window(
        info.APP_NAME, url=str(web_dir() / "index.html"), js_api=api,
        width=1180, height=800, min_size=(980, 660),
        background_color=DARK_BG if dark else LIGHT_BG, text_select=True,
    )
    api._dialogs = Dialogs(window)
    home: dict = {}
    window.events.loaded += lambda: _on_loaded(window, api, home)

    smoke: dict = {}
    if args.smoke:
        threading.Thread(target=_smoke_watch, args=(window, api, Path(args.smoke), smoke), daemon=True).start()
    try:
        webview.start(gui="edgechromium" if sys.platform == "win32" else None, http_server=True, debug=args.debug)
    except Exception as e:  # noqa: BLE001
        log.exception("Jendela gagal dibuka")
        if args.smoke:
            Path(args.smoke).write_text(repr({"ready": False, "error": str(e)}), encoding="utf-8")
            return 3
        if message_box(t("app.need_webview2"), ask=True):
            import webbrowser

            webbrowser.open(info.LINKS["webview2"])
        return 2
    finally:
        api._close()  # jendela ditutup: hentikan unduhan dan pekerja mesin PDF teliti
    if args.smoke:
        return 0 if smoke.get("ready") else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
