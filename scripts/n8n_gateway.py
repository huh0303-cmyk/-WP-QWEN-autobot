#!/usr/bin/env python3
from __future__ import annotations
import hmac, json, os, subprocess, sys
from pathlib import Path
from flask import Flask, jsonify, request

app = Flask(__name__)
TOKEN = os.environ.get("N8N_GATEWAY_TOKEN", "").strip()
ROOT = Path("/opt/korea365")
PIPELINE = ROOT / "scripts" / "london_four_agent_pipeline.py"

ACTIONS = {
    "wp25_tick": ("restart", "korea365-wp-publisher.service"),
    "blogger33_daily": ("start", "korea365-blogger33-daily.service"),
    "news2": ("start", "korea365-daily-52-plan.service"),
    "youtube_playlist": ("start", "korea365-playlist-v3.service"),
    "youtube_private": ("start", "korea365-youtube-private-weekly.service"),
    "metrics": ("start", "korea365-channel-metrics.service"),
    "evidence": ("start", "korea365-publication-evidence.service"),
    "account_schedule": ("start", "korea365-account-schedule.service"),
}
PIPELINE_TIMEOUT = {"research": 300, "write": 300, "image": 240, "publish": 240}

def auth_ok():
    supplied = request.headers.get("Authorization", "")
    return bool(TOKEN) and hmac.compare_digest(supplied, "Bearer " + TOKEN)

@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "korea365-n8n-gateway", "pipeline": PIPELINE.exists()})

@app.post("/run/<action>")
def run_action(action):
    if not auth_ok():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    spec = ACTIONS.get(action)
    if not spec:
        return jsonify({"ok": False, "error": "unknown_action"}), 404
    verb, unit = spec
    p = subprocess.run(["systemctl", verb, unit], capture_output=True, text=True, timeout=60)
    return jsonify({"ok": p.returncode == 0, "action": action, "unit": unit,
                    "returncode": p.returncode, "stderr": p.stderr[-400:]})

@app.post("/pipeline/<stage>")
def pipeline_stage(stage):
    if not auth_ok():
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    if stage not in PIPELINE_TIMEOUT:
        return jsonify({"ok": False, "error": "unknown_stage", "stage": stage}), 404
    payload = request.get_json(silent=True) or {}
    run_id = str(payload.get("run_id") or "").strip()
    site_id = str(payload.get("site_id") or "").strip()
    publish_mode = str(payload.get("publish_mode") or "draft").strip().lower()
    category = str(payload.get("category") or "").strip()
    if not run_id:
        return jsonify({"ok": False, "error": "run_id_required"}), 400
    if publish_mode not in {"draft", "publish"}:
        return jsonify({"ok": False, "error": "invalid_publish_mode"}), 400
    cmd = [sys.executable, str(PIPELINE), "--stage", stage, "--run-id", run_id,
           "--publish-mode", publish_mode]
    if stage == "research":
        if not site_id:
            return jsonify({"ok": False, "error": "site_id_required"}), 400
        cmd += ["--site-id", site_id]
        if category:
            cmd += ["--category", category]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           timeout=PIPELINE_TIMEOUT[stage])
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "stage": stage, "run_id": run_id,
                        "error": "stage_timeout"}), 504
    stdout = p.stdout[-12000:]
    stderr = p.stderr[-4000:]
    result = None
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                result = parsed
                break
        except ValueError:
            pass
    body = {"ok": p.returncode == 0, "stage": stage, "run_id": run_id,
            "site_id": site_id, "returncode": p.returncode,
            "result": result, "stderr": stderr}
    if p.returncode != 0:
        body["stdout_tail"] = stdout[-2500:]
        return jsonify(body), 500
    return jsonify(body)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8766)
