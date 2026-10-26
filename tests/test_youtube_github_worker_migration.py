import pytest
from pathlib import Path
from automation_hub import youtube_github_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]


def test_cost_hold_defaults_to_blocked(monkeypatch):
    monkeypatch.delenv("YOUTUBE_COST_HOLD", raising=False)
    assert runtime.cost_hold_active()
    with pytest.raises(RuntimeError):
        runtime.check_cost_hold()


@pytest.mark.parametrize("value", ["", "true", "1", "yes", "on"])
def test_cost_hold_is_blocked_without_explicit_false(monkeypatch, value):
    monkeypatch.setenv("YOUTUBE_COST_HOLD", value)
    assert runtime.cost_hold_active()


@pytest.mark.parametrize("value", ["false", "0", "no", "off", "FALSE"])
def test_only_explicit_false_releases_hold(monkeypatch, value):
    monkeypatch.setenv("YOUTUBE_COST_HOLD", value)
    assert not runtime.cost_hold_active()


def test_github_queue_path(monkeypatch):
    monkeypatch.delenv("YOUTUBE_GITHUB_QUEUE_DIR", raising=False)
    assert runtime.queue_root() == ROOT / "data" / "youtube_github_queue"


def test_enqueue_requires_hold_release(tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_COST_HOLD", "false")
    monkeypatch.setenv("YOUTUBE_GITHUB_QUEUE_DIR", str(tmp_path / "queue"))
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    job = runtime.enqueue("healing", "Cafe healing", "youtube_healing", run_now=True)
    assert job["runner"] == "github-actions"
    assert job["job_id"].startswith("gh-12345-")
    assert (tmp_path / "queue" / "pending" / f"{job['job_id']}.json").exists()


def test_duplicate_channel_is_rejected_in_one_run(tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_COST_HOLD", "false")
    monkeypatch.setenv("YOUTUBE_GITHUB_QUEUE_DIR", str(tmp_path / "queue"))
    monkeypatch.setenv("GITHUB_RUN_ID", "67890")
    runtime.enqueue("healing", "Cafe healing", "youtube_healing")
    with pytest.raises(RuntimeError):
        runtime.enqueue("healing", "Cafe healing", "youtube_healing")


def test_github_worker_does_not_use_server_paths():
    source = (ROOT / "scripts" / "youtube_github_worker.py").read_text(encoding="utf-8")
    assert "/opt/" not in source
    assert "/etc/" not in source
    assert "youtube_vps_queue" not in source
    assert "WORKER_WORKFLOW=\"youtube-github-worker\"" in source


def test_github_worker_files_compile():
    import py_compile
    for relative in ("automation_hub/youtube_github_runtime.py", "scripts/youtube_github_worker.py"):
        py_compile.compile(str(ROOT / relative), doraise=True)
