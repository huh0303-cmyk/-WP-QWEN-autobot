from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_four_agent_pipeline_has_no_server_runtime_dependency():
    source = (ROOT / "scripts/london_four_agent_pipeline.py").read_text(encoding="utf-8")
    for forbidden in ("/etc/korea365", "/opt/korea365", "systemctl", "VPS_WP_QUEUE", "korea365-wp-publisher.service"):
        assert forbidden not in source


def test_control_center_dispatches_pipeline_to_github_actions_only():
    source = (ROOT / "control_center/london_gpt_app.py").read_text(encoding="utf-8")
    assert "london-content-pipeline.yml" in source
    assert "N8N_WEBHOOK" not in source
    assert "N8N_RERUN_WEBHOOKS" not in source
    assert "http://127.0.0.1:5678" not in source


def test_node_console_uses_github_actions_routes_not_n8n_gateway():
    server = (ROOT / "london_project_claude_console/server/server.js").read_text(encoding="utf-8")
    client = (ROOT / "london_project_claude_console/public/registry.js").read_text(encoding="utf-8")
    assert 'require("../lib/githubActions")' in server
    assert "/api/github/actions/run/" in client
    assert "/api/n8n/" not in client
    assert "n8nGateway" not in server


def test_scheduler_is_disabled_without_explicit_owner_flags():
    workflow = (ROOT / ".github/workflows/youtube-github-scheduler.yml").read_text(encoding="utf-8")
    script = (ROOT / "scripts/youtube_github_scheduler.py").read_text(encoding="utf-8")
    assert 'cron: "17 * * * *"' in workflow
    assert "YOUTUBE_AUTO_PUBLISH_ENABLED" in workflow
    assert "YOUTUBE_COST_HOLD" in workflow
    assert "has_due_calendar_row" in script
    assert "check_cost_hold()" in script
    assert "process_one()" in script
    assert "systemctl" not in workflow
    assert "appleboy/ssh-action" not in workflow


def test_pipeline_workflow_is_manual_and_cost_hold_gated():
    workflow = (ROOT / ".github/workflows/london-content-pipeline.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in workflow
    assert "confirm_run" in workflow
    assert "confirm_publication" in workflow
    assert "LONDON_PIPELINE_COST_HOLD" in workflow
    assert "systemctl" not in workflow
    assert "appleboy/ssh-action" not in workflow
