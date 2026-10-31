"""Server pengembangan: menjalankan tampilan di browser biasa tanpa pywebview.

    python -m urai --dev            lalu buka http://127.0.0.1:8765/index.html?dev=1

Tampilan memanggil POST /api/<nama method> dengan isi JSON berupa daftar argumen.
Hanya untuk pengembangan dan uji otomatis; server hanya mendengarkan 127.0.0.1.
"""
from __future__ import annotations

import json
import logging
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .api import Api
from .paths import default_output_dir, samples_dir, web_dir
from .textutil import unique_path

log = logging.getLogger("urai.dev")


class DevDialogs:
    """Pengganti jendela pilih file. Uji otomatis bisa mengisi antrean jawabannya lewat /dev/pick."""

    def __init__(self):
        self.next_files: list[list[str]] = []
        self.next_folder: list[str] = []
        self.save_dir: Path | None = None

    def open_files(self, directory: str = "") -> list[str]:
        if self.next_files:
            return self.next_files.pop(0)
        return sorted(str(p) for p in samples_dir().iterdir() if p.is_file())

    def open_folder(self, directory: str = "") -> str:
        if self.next_folder:
            return self.next_folder.pop(0)
        return str(samples_dir())

    def save_file(self, directory: str, filename: str, file_type: str) -> str:
        base = self.save_dir or Path(directory or default_output_dir())
        base.mkdir(parents=True, exist_ok=True)
        return str(unique_path(base / filename))


class Handler(SimpleHTTPRequestHandler):
    api: Api = None  # type: ignore[assignment]
    dialogs: DevDialogs = None  # type: ignore[assignment]

    def log_message(self, fmt, *args):  # noqa: N802 - API http.server
        log.debug(fmt, *args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _trusted(self) -> bool:
        """Tolak permintaan dari situs lain yang terbuka di browser: Content-Type JSON memaksa pemeriksaan CORS,
        dan Host/Origin wajib alamat server ini sendiri."""
        port = self.server.server_address[1]
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host", "") not in allowed:
            return False
        origin = self.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] not in allowed:
            return False
        return (self.headers.get("Content-Type") or "").split(";")[0].strip() == "application/json"

    def do_POST(self):  # noqa: N802 - API http.server
        if not self._trusted():
            return self._json(403, {"error": "forbidden"})
        length = int(self.headers.get("Content-Length") or 0)
        try:
            args = json.loads(self.rfile.read(length) or b"[]")
        except ValueError:
            return self._json(400, {"error": "bad json"})
        if self.path.startswith("/dev/pick"):
            if isinstance(args, dict):
                if args.get("files") is not None:
                    self.dialogs.next_files.append(list(args["files"]))
                if args.get("folder"):
                    self.dialogs.next_folder.append(args["folder"])
                if args.get("save_dir"):
                    self.dialogs.save_dir = Path(args["save_dir"])
            return self._json(200, {"ok": True})
        if not self.path.startswith("/api/"):
            return self._json(404, {"error": "not found"})
        name = self.path[len("/api/"):].split("?")[0]
        fn = getattr(self.api, name, None)
        if name.startswith("_") or not callable(fn):
            return self._json(404, {"error": f"no method {name}"})
        if not isinstance(args, list):
            args = [args]
        try:
            result = fn(*args)
        except Exception as e:  # noqa: BLE001
            log.exception("API %s gagal", name)
            return self._json(500, {"error": f"{type(e).__name__}: {e}"})
        return self._json(200, {"result": result})


def serve(port: int = 8765, open_browser: bool = True, api: Api | None = None) -> ThreadingHTTPServer:
    api = api or Api(dev=True)
    dialogs = DevDialogs()
    api._dialogs = dialogs
    handler = type("BoundHandler", (Handler,), {"api": api, "dialogs": dialogs})
    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(handler, directory=str(web_dir())))
    url = f"http://127.0.0.1:{httpd.server_address[1]}/index.html?dev=1"
    print(f"Urai App (mode pengembangan): {url}", flush=True)
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    return httpd
