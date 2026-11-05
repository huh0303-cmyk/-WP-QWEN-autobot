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
    assert "find_due_channel" in script
    assert "check_cost_hold(channel_key)" in script
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



def test_cafe_healing_has_a_channel_scoped_free_only_scheduler():
    workflow = (ROOT / ".github/workflows/cafe-healing-github-scheduler.yml").read_text(encoding="utf-8")
    runtime = (ROOT / "automation_hub/youtube_github_runtime.py").read_text(encoding="utf-8")
    scheduler = (ROOT / "scripts/youtube_github_scheduler.py").read_text(encoding="utf-8")
    assert 'cron: "17 * * * *"' in workflow
    assert "PLAYLIST_FREE_ONLY_CHANNEL: healing" in workflow
    assert 'PLAYLIST_PAID_API_ENABLED: "false"' in workflow
    assert "HEALING_VARIANT: sequential" in workflow
    assert "YOUTUBE_OAUTH_REFRESH_TOKEN_HEALING" in workflow
    assert "scripts/youtube_github_scheduler.py --channel healing" in workflow
    assert "scripts/healing_publish_direct.py" in workflow
    assert "scripts/healing_calendar_ensure.py" in workflow
    assert "python -m py_compile scripts/healing_motion.py" in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" in workflow
    assert 'if channel == "healing"' in runtime
    assert "YOUTUBE_OAUTH_REFRESH_TOKEN_HEALING" in runtime
    assert 'parser.add_argument("--channel"' in scheduler
    assert "check_cost_hold(channel_key)" in scheduler
    assert "run_now=False" in scheduler



def test_cafe_healing_rotates_five_sound_themes_with_one_visual_source():
    motion = (ROOT / "scripts/healing_motion.py").read_text(encoding="utf-8")
    runtime = (ROOT / "automation_hub/youtube_github_runtime.py").read_text(encoding="utf-8")
    for theme in ('"fire"', '"rain"', '"wind"', '"birds"', '"temple"'):
        assert theme in motion
    assert 'CATEGORY_ORDER = ("fire", "rain", "wind", "birds", "temple")' in motion
    assert "one main licensed nature scene" in motion
    assert "one main source clip is looped" in motion
    assert "record_category(MODE" in motion
    assert "FISH_AUDIO_API_KEY" in runtime
    assert "PEXELS_API_KEY" in runtime
    assert "free_natural_ambience" in runtime



def test_healing_direct_launch_is_cost_gated_and_audited():
    direct = (ROOT / "scripts/healing_publish_direct.py").read_text(encoding="utf-8")
    calendar = (ROOT / "scripts/healing_calendar_ensure.py").read_text(encoding="utf-8")
    assert 'check_cost_hold("healing")' in direct
    assert 'check_cost_hold("healing")' in calendar
    assert "EXPECTED_CHANNEL_ID = \"UC7yEsLM-HoXudngrD-4FIqg\"" in direct
    assert "EXPECTED_CHANNEL_ID = \"UC7yEsLM-HoXudngrD-4FIqg\"" in calendar
    assert "verified_channel_id" in direct
    assert "privacy_status" in direct
    assert "values().append" in direct
    assert "target_count = rng.randint(2, 3)" in calendar
    assert "insertDataOption=\"INSERT_ROWS\"" in calendar
