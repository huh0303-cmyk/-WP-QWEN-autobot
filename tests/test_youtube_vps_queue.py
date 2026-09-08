import json
from pathlib import Path

import pytest

from automation_hub.youtube_vps_queue import enqueue


def test_queue_is_durable_and_rejects_duplicate_channel(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_VPS_QUEUE_DIR", str(tmp_path))
    job = enqueue("kpop", "K-pop", "youtube_kpop")
    stored = json.loads((tmp_path / "pending" / f"{job['job_id']}.json").read_text(encoding="utf-8"))
    assert stored["channel_key"] == "kpop"
    with pytest.raises(RuntimeError, match="already queued"):
        enqueue("kpop", "K-pop", "youtube_kpop")


def test_hostinger_vps_contract_is_single_owner():
    root = Path(__file__).resolve().parents[1]
    assert "enqueue_youtube_vps" in (root / "control_center" / "app.py").read_text(encoding="utf-8")
    assert "--daemon" in (root / "deploy" / "vps" / "korea365-youtube-worker.service").read_text(encoding="utf-8")
    vps_readme = (root / "deploy" / "vps" / "README.md").read_text(encoding="utf-8")
    assert "Hostinger VPS is the sole production host" in vps_readme
    assert "--enqueue-channel globalmusic" in vps_readme
    for name in ("youtube-control-scheduler.yml", "generate-youtube-playlist.yml", "curio-longform-daily.yml"):
        assert "if: ${{ false }}" in (root / ".github" / "workflows" / name).read_text(encoding="utf-8")
