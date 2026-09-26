#!/usr/bin/env python3
from __future__ import annotations
import hmac, os, subprocess
from flask import Flask, jsonify, request

app = Flask(__name__)
TOKEN = os.environ.get("N8N_GATEWAY_TOKEN", "").strip()
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
def auth_ok():
    supplied=request.headers.get("Authorization","")
    return bool(TOKEN) and hmac.compare_digest(supplied, "Bearer "+TOKEN)
@app.get("/health")
def health():
    return jsonify({"ok":True,"service":"korea365-n8n-gateway"})
@app.post("/run/<action>")
def run_action(action):
    if not auth_ok():
        return jsonify({"ok":False,"error":"unauthorized"}),401
    spec=ACTIONS.get(action)
    if not spec:
        return jsonify({"ok":False,"error":"unknown_action"}),404
    verb,unit=spec
    p=subprocess.run(["systemctl",verb,unit],capture_output=True,text=True,timeout=60)
    return jsonify({"ok":p.returncode==0,"action":action,"unit":unit,"returncode":p.returncode,"stderr":p.stderr[-400:]})
if __name__=="__main__":
    app.run(host="127.0.0.1",port=8766)
