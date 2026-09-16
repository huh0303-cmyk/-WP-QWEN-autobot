"""Read-only playlist production status page preserved from the VPS hotfix.

The page never starts production or changes publication state. It only renders
existing private-production plan data when present on the VPS.
"""
from __future__ import annotations

import json
from pathlib import Path

from flask import render_template_string

PLAN_PATH = Path("/opt/korea365/playlist-v3/production-plan.json")

PAGE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>플레이리스트 5채널 제작 현황 | Korea365</title>
<style>
body{background:#101827;color:#edf2fa;font:16px/1.7 system-ui;margin:0}main{max-width:1100px;margin:auto;padding:30px}
a{color:#9dd7ff}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}.card,section{background:#1b2739;border:1px solid #344155;padding:20px;border-radius:16px;margin-bottom:20px}h1{font-size:30px}h2{font-size:20px}strong{color:#b6efcd}.scroll{overflow:auto}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #344155}.note{color:#fbd28c}small{color:#acb8c9}
</style></head><body><main>
<a href="/">← 운영 통제실</a>
<h1>플레이리스트 5채널 · 비공개 제작 현황</h1>
<p>런던프로젝트 기준: <strong>채널별 2~3일 간격</strong> · 서로 다른 KST 시각 · 비공개 업로드 후 이사장 검수</p>
<section><h2>실제 진행 상태</h2>
<p>대기열 {{jobs|length}}건 · YouTube 예약 확인 {{scheduled}}건 · 공개 확인 {{published}}건</p>
<p>예약 실행기 마지막 확인: {{checked}}</p>
<p class="note">목표 시각은 제작 계획입니다. 비공개 업로드가 실제 video ID와 channel ID로 검증되기 전에는 완료가 아닙니다.</p></section>
<div class="cards">{% for c in channels %}<div class="card"><h2>{{c.name}}</h2><p>다음 계획: {{c.first}}</p><small>{{c.production}}</small></div>{% endfor %}</div>
<section><h2>운영 원칙</h2><p>완성본은 먼저 PRIVATE로 업로드합니다. video ID · 정확한 channel ID · privacyStatus=private를 확인하면 VERIFIED_PRIVATE입니다. 이사장 승인 전에는 공개 전환하지 않습니다.</p></section>
<section><h2>전체 제작 대기열 · KST</h2><div class="scroll"><table><tr><th>예정 시각</th><th>채널</th><th>실제 상태</th></tr>
{% for j in jobs %}<tr><td>{{j.target_at_kst[:16]|replace('T',' ')}}</td><td>{{j.channel_name}}</td><td>{{labels.get(j.status,j.status)}}</td></tr>{% endfor %}</table></div></section>
</main></body></html>'''


def install(app):
    if "playlist_v3_page" in app.view_functions:
        return

    @app.get("/playlists")
    def playlist_v3_page():
        if not PLAN_PATH.exists():
            return "플레이리스트 일정 자료를 확인할 수 없습니다.", 503
        try:
            plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
            jobs = sorted(plan.get("jobs", []), key=lambda x: x.get("target_at_kst", ""))
        except (OSError, ValueError, TypeError):
            return "플레이리스트 일정 자료 형식을 확인해야 합니다.", 503
        if not jobs:
            return "플레이리스트 대기열이 비어 있습니다.", 503
        order = ("globalmusic", "kpop", "starbucks", "healing", "mbb")
        channels = []
        for key in order:
            row = next((j for j in jobs if j.get("channel_key") == key), None)
            if row:
                channels.append({
                    "name": row.get("channel_name", key),
                    "first": str(row.get("target_at_kst", ""))[:16].replace("T", " "),
                    "production": "2~3일 간격 · 비공개 제작 · 공개 전 사람 검수",
                })
        labels = {
            "planned_not_uploaded": "제작 대기 · 미업로드",
            "ready_to_release": "검수 완료 · 비공개 업로드 대기",
            "scheduled_on_youtube": "YouTube 예약 확인",
            "private_uploaded": "비공개 업로드 확인",
            "published": "공개 발행 확인",
        }
        return render_template_string(
            PAGE,
            jobs=jobs,
            channels=channels,
            scheduled=sum(j.get("status") == "scheduled_on_youtube" for j in jobs),
            published=sum(j.get("status") == "published" for j in jobs),
            checked=plan.get("last_runner_check", "미확인"),
            labels=labels,
        )
