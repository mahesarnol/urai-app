import shutil
import threading

import pytest

from urai.paths import samples_dir


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Pengaturan dan folder Dokumen di folder sementara, supaya uji tidak menyentuh data pengguna."""
    home = tmp_path / "home"
    (home / "Documents").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "appdata"))

    class NoKeyring:
        @staticmethod
        def get_password(*a):
            raise RuntimeError("no keyring")

        set_password = delete_password = get_password

    monkeypatch.setitem(__import__("sys").modules, "keyring", NoKeyring)
    yield home


@pytest.fixture
def samples():
    return {p.name: p for p in samples_dir().iterdir() if p.is_file()}


@pytest.fixture
def has_tesseract():
    from urai.ocr import engine, reset_engine

    reset_engine()
    t = engine()
    if not t.available or not {"ind", "eng"} <= set(t.languages()):
        pytest.skip("Tesseract dengan bahasa ind dan eng tidak terpasang")
    return t


def collect_events():
    events, lock = [], threading.Lock()

    def emit(kind, data):
        with lock:
            events.append((kind, data))

    return events, emit


@pytest.fixture
def events():
    return collect_events()


@pytest.fixture
def copy_samples(tmp_path, samples):
    """Salinan file contoh di folder sementara (untuk uji 'simpan di folder yang sama')."""
    d = tmp_path / "docs"
    d.mkdir()
    for name, p in samples.items():
        shutil.copy(p, d / name)
    return d
