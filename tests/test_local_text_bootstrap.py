import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import local_text as lt


def test_no_bootstrap_unless_enabled(monkeypatch):
    monkeypatch.setattr(lt, "_reachable", lambda: False)
    monkeypatch.setattr(lt, "_bootstrapped", False)
    monkeypatch.delenv("RUNNER_OLLAMA_BOOTSTRAP", raising=False)
    assert lt.ensure_runner_ollama() is False


def test_already_running_skips_download(monkeypatch):
    monkeypatch.setattr(lt, "_reachable", lambda: True)
    assert lt.ensure_runner_ollama(download=lambda: (_ for _ in ()).throw(AssertionError("downloaded"))) is True
