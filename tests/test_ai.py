"""Uji jembatan AI dengan server tiruan yang meniru API chat completions (tanpa internet)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

from urai import ai as ai_mod
from urai.errors import friendly_error


class FakeAI(BaseHTTPRequestHandler):
    requests: list = []
    status = 200

    def log_message(self, *a):
        pass

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeAI.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        if FakeAI.status != 200:
            self.send_response(FakeAI.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": {"message": "invalid api key", "type": "invalid_request_error"}}).encode())
            return
        content = body["messages"][-1]["content"]
        answer = "merah" if isinstance(content, list) else "# Judul\n- poin"
        out = {"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
               "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": answer}}]}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def server():
    FakeAI.requests = []
    FakeAI.status = 200
    httpd = HTTPServer(("127.0.0.1", 0), FakeAI)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/v1"
    httpd.shutdown()


def test_providers_have_models_and_urls():
    for key, p in ai_mod.PROVIDERS.items():
        if key != "other":
            assert p["model"], key
        if key not in ("openai", "other"):
            assert p["base_url"].startswith("https://"), key


def test_config_defaults():
    cfg = ai_mod.AIConfig("deepseek", " kunci ")
    assert cfg.api_key == "kunci" and cfg.model == "deepseek-flash" and cfg.base_url == "https://api.deepseek.com"
    assert cfg.ready
    assert not ai_mod.AIConfig("other", "k").ready  # server lain wajib mengisi model sendiri
    assert ai_mod.AIConfig("tidak-ada", "k").provider == "other"


def test_vision_request_shape(server):
    cfg = ai_mod.AIConfig("other", "rahasia", "model-uji", server)
    big = Image.new("RGB", (4000, 1000), "white")
    assert ai_mod.vision_text(cfg, big) == "merah"
    req = FakeAI.requests[-1]
    assert req["path"] == "/v1/chat/completions"
    assert req["auth"] == "Bearer rahasia"
    body = req["body"]
    assert body["model"] == "model-uji"
    assert "max_tokens" not in body  # beberapa model (mis. gpt-5) menolak max_tokens
    parts = body["messages"][0]["content"]
    assert parts[0]["type"] == "text" and parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_chat_and_connection(server):
    cfg = ai_mod.AIConfig("other", "k", "m", server)
    assert ai_mod.chat(cfg, "sistem", "isi").startswith("# Judul")
    assert FakeAI.requests[-1]["body"]["messages"][0] == {"role": "system", "content": "sistem"}
    assert ai_mod.test_connection(cfg) == "merah"


def test_bad_key_is_friendly(server):
    FakeAI.status = 401
    cfg = ai_mod.AIConfig("other", "salah", "m", server)
    with pytest.raises(Exception) as e:
        ai_mod.chat(cfg, "s", "u")
    assert "API key ditolak" in friendly_error(e.value)
