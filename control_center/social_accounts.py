from __future__ import annotations

import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import jsonify, render_template, request

from automation_hub.youtube_vps_queue import enqueue as enqueue_youtube_vps


ROOT = Path("/opt/korea365")
DATA = ROOT / "data"
INVENTORY = DATA / "london-social-account-inventory-2026-09-24.json"
YOUTUBE_CONFIG = ROOT / "config" / "youtube_channels.json"

CORE_YOUTUBE = {
    "UCbJfEtsffpgI5MsKkB7BYvQ": "globalmusic",
    "UC7yEsLM-HoXudngrD-4FIqg": "healing",
    "UC_e-sbLkVgwJNYEeobolNog": "starbucks",
    "UC7jOhyMa-FIrzZuea97z1Pw": "mbb",
    "UCKZsfAWyCmY0jckf4IWZrqw": "kpop",
    "UCtNLZO07Oh3UnXPI2CjOgNg": "nasa",
    "UCVBvZwodUF4s57KeNicxQ3w": "history",
    "UCgNj-yS93A_fOHXXvG49fww": "invention",
    "UCLvy6kSpC8-7o3hnSrfQ47g": "silent_era",
    "UCwh49EokdWFJqYFE_zA6XDQ": "retro_reels",
}

ROLE_DETAILS = {
    "서울국제대학-TOPIK센터": ("한국어·TOPIK 교육", "TOPIK 학습, 한국어 표현, 유학생 대상 교육 콘텐츠"),
    "English Survival": ("생활 영어 교육", "실생활 영어 표현과 생존 회화 중심 콘텐츠"),
    "Studio_starbucks": ("다국어 음악·교육", "등록 목적과 실제 운영 주제를 다시 확인해야 하는 채널"),
    "Health Clinic USA": ("영어권 건강 정보", "영어권 시청자를 위한 일반 건강·생활 정보"),
    "Seoul_Jisoo1": ("한국 생활·건강", "서울 생활과 건강·뷰티 정보를 결합한 콘텐츠"),
    "Health_Clinic_Japan": ("일본어 건강 정보", "일본어권 시청자를 위한 일반 건강·생활 정보"),
    "French Survival": ("프랑스어 교육", "초급 생존 프랑스어 표현과 상황별 회화"),
    "German Survival": ("독일어 교육", "초급 생존 독일어 표현과 상황별 회화"),
    "Spanish Survival": ("스페인어 교육", "초급 생존 스페인어 표현과 상황별 회화"),
    "Italian Survival": ("이탈리아어 교육", "초급 생존 이탈리아어 표현과 상황별 회화"),
    "SIS Korean · TOPIK": ("한국어·TOPIK", "TOPIK 학습과 한국어 교육용 숏폼"),
    "SIS English · Survival": ("생활 영어", "짧은 생활 영어와 생존 회화 숏폼"),
    "지수의 하루 · Jisoo Picks": ("건강·뷰티·여행 쇼핑", "생활용품, 여행용품, 건강·뷰티 상품 소개"),
    "지수의 생활 발견": ("생활·여행용품", "실용적인 생활용품과 여행용품 추천"),
    "지수의 여행과 생활": ("여행·생활정보", "한국 여행과 일상생활에 필요한 정보"),
    "지수의 건강 노트": ("건강·건기식", "일반 건강 정보와 건강기능식품 주의사항"),
}


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_state(group: str, state: dict) -> None:
    target = DATA / f"bulk_publish_state_{group}.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, target)


def _cards() -> list[dict]:
    inventory = _read(INVENTORY, {})
    youtube_config = {r.get("channel_id"): r for r in _read(YOUTUBE_CONFIG, {}).get("channels", []) if r.get("channel_id")}
    cards = []
    for row in inventory.get("youtube", []):
        channel_id = row["channel_id"]
        configured = youtube_config.get(channel_id, {})
        core_key = CORE_YOUTUBE.get(channel_id)
        group = configured.get("channel_type") or row.get("group") or "additional"
        role, fallback = ROLE_DETAILS.get(row["name"], (group, "채널별 확정 주제 콘텐츠"))
        cards.append({
            "key": f"youtube:{channel_id}", "platform": "YouTube", "name": row["name"],
            "identity": channel_id, "handle": row.get("handle", ""),
            "url": f"https://www.youtube.com/channel/{channel_id}", "role": role if not configured else group,
            "description": configured.get("tone") or fallback,
            "state_label": "제작·업로드 연결 완료" if core_key else ("분석 연결 확인" if row.get("state") == "analytics_connected" else "등록됨 · 최신 연결 재확인 필요"),
            "publish_mode": "공개하지 않고 비공개 영상 제작 대기열에 1건 추가합니다." if core_key else "채널은 확인됐지만 통제실 제작 프로필이 아직 연결되지 않았습니다.",
            "can_publish": bool(core_key), "channel_key": core_key or "",
            "button_label": "즉시발행 · 비공개 제작" if core_key else "즉시발행 · 연결 필요",
        })
    urls = {"TikTok": "https://www.tiktok.com/@{handle}", "Instagram": "https://www.instagram.com/{handle}/", "Threads": "https://www.threads.com/@{handle}"}
    for platform, source_key in (("TikTok", "tiktok"), ("Instagram", "instagram"), ("Threads", "threads")):
        for row in inventory.get(source_key, []):
            role, description = ROLE_DETAILS.get(row["name"], ("확정 주제 유지", "플랫폼별 확정 주제 콘텐츠"))
            cards.append({
                "key": f"{source_key}:{row['handle']}", "platform": platform, "name": row["name"],
                "identity": f"@{row['handle']}", "handle": row["handle"], "url": urls[platform].format(handle=row["handle"]),
                "role": role, "description": description, "state_label": "계정 확인 · 게시 인증 필요",
                "publish_mode": "게시 API 권한이 없어 공개 발행하지 않고 필요한 연결을 안내합니다.",
                "can_publish": False, "channel_key": "", "button_label": "즉시발행 · 인증 필요",
            })
    return cards


def install(app):
    @app.get("/social-accounts")
    def social_accounts():
        cards = _cards()
        platforms = ["전체", "YouTube", "TikTok", "Instagram", "Threads"]
        selected = request.args.get("platform", "전체")
        if selected not in platforms:
            selected = "전체"
        visible = cards if selected == "전체" else [c for c in cards if c["platform"] == selected]
        counts = {p: sum(c["platform"] == p for c in cards) for p in platforms[1:]}
        return render_template("social_accounts.html", cards=visible, counts=counts, platforms=platforms,
                               selected=selected, total=len(cards), csrf_token=app.config["CONTROL_CENTER_CSRF"]), 200, {"Cache-Control": "no-store"}

    @app.post("/social-accounts/publish-now")
    def social_accounts_publish_now():
        payload = request.get_json(silent=True) or {}
        if not hmac.compare_digest(str(payload.get("csrf_token", "")), str(app.config["CONTROL_CENTER_CSRF"])):
            return jsonify(message="화면을 새로고침한 뒤 다시 눌러주세요."), 403
        card = next((c for c in _cards() if c["key"] == payload.get("account_key")), None)
        if not card:
            return jsonify(message="등록된 계정 카드가 아닙니다."), 404
        if not card["can_publish"]:
            return jsonify(message=f"{card['name']}: 실제 게시 인증이 없어 공개하지 않았습니다. 연결 상태를 먼저 보완해야 합니다.",
                           review_url=f"/channel-check/{card['platform'].lower()}"), 409
        channel_key = card["channel_key"]
        group = f"youtube_{channel_key}"
        try:
            job = enqueue_youtube_vps(channel_key, card["name"], group, run_now=True)
        except RuntimeError as exc:
            return jsonify(message=str(exc)), 409
        item = {"job_id": job["job_id"], "label": card["name"], "platform": "youtube", "site_id": channel_key,
                "workflow": "youtube-vps-worker", "run_id": None, "run_url": "", "status": "queued",
                "conclusion": None, "reason": "VPS 비공개 제작 대기"}
        _write_state(group, {"status": "polling", "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None, "items": [item]})
        return jsonify(message=f"{card['name']}: 비공개 영상 제작을 접수했습니다. 자동 공개하지 않습니다.", job_id=job["job_id"]), 202
