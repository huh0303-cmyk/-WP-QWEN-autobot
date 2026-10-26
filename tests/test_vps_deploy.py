from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_server_deployment_assets_are_retired():
    retired = (
        "deploy/vps/sync_main.py",
        "deploy/vps/korea365-youtube-worker.service",
        "deploy/vps/korea365-youtube-scheduler.timer",
        "deploy/n8n/docker-compose.yml",
        "deploy/systemd/korea365-n8n-gateway.service",
        "scripts/run_youtube_vps.py",
        "scripts/youtube_vps_worker.py",
        "scripts/vps_wordpress_worker.py",
        "scripts/run_blogger33_daily_vps.py",
        "scripts/schedule_blogger33_daily_vps.py",
    )
    for relative in retired:
        assert not (ROOT / relative).exists(), f"legacy server asset remains: {relative}"


def test_github_only_youtube_worker_is_present_and_fail_closed():
    workflow = (ROOT / ".github/workflows/youtube-github-worker.yml").read_text(encoding="utf-8")
    runtime = (ROOT / "automation_hub/youtube_github_runtime.py").read_text(encoding="utf-8")
    assert "confirm_publication" in workflow
    assert "YOUTUBE_COST_HOLD" in workflow
    assert 'return value not in {"false", "0", "no", "off"}' in runtime
