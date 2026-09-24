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
SNS_POLICY = ROOT / "config" / "sns_six_channel_policy.json"
YOUTUBE_CONFIG = ROOT / "config" / "youtube_channels.json"
TISTORY_CONFIG = ROOT / "config" / "tistory_portfolio.json"
ROOMS_CONFIG = ROOT / "config" / "automation_rooms.json"

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
    "Studio_starbucks": ("일본어 Survival 교육", "레거시 이름. 실제 운영은 Japanese Survival 단일 언어 채널로 취급"),
    "Japanese Survival": ("일본어 Survival 교육", "일본어권 초급 생존 회화와 생활 표현 중심 콘텐츠"),
    "Health Clinic USA": ("미국·영어권 건강 정보", "미국 및 영어권 시청자를 위한 일반 건강·생활 정보"),
    "Seoul_Jisoo1": ("쇼핑·예약", "건강기능식품, 호텔예약, 여행·생활 예약, 생활상품 등 쇼핑·예약형 콘텐츠"),
    "Health_Clinic_Japan": ("일본·일본어권 건강 정보", "일본 및 일본어권 시청자를 위한 일반 건강·생활 정보"),
    "French Survival": ("프랑스어 교육", "초급 생존 프랑스어 표현과 상황별 회화"),
    "German Survival": ("독일어 교육", "초급 생존 독일어 표현과 상황별 회화"),
    "Spanish Survival": ("스페인어 교육", "초급 생존 스페인어 표현과 상황별 회화"),
    "Italian Survival": ("이탈리아어 교육", "초급 생존 이탈리아어 표현과 상황별 회화"),
}

LOGIN_URLS = {
    "TikTok": "https://www.tiktok.com/login",
    "Instagram": "https://www.instagram.com/accounts/login/",
    "Facebook": "https://www.facebook.com/login/",
    "Threads": "https://www.instagram.com/accounts/login/",
    "Tistory": "https://www.tistory.com/auth/login",
    "Naver": "https://nid.naver.com/nidlogin.login",
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


def _youtube_cards() -> list[dict]:
    inventory = _read(INVENTORY, {})
    configured = {r.get("channel_id"): r for r in _read(YOUTUBE_CONFIG, {}).get("channels", []) if r.get("channel_id")}
    cards = []
    for row in inventory.get("youtube", []):
        channel_id = row["channel_id"]
        profile = configured.get(channel_id, {})
        core_key = CORE_YOUTUBE.get(channel_id)
        group = profile.get("channel_type") or row.get("group") or "additional"
        role, fallback = ROLE_DETAILS.get(row["name"], (group, "채널별 확정 주제 콘텐츠"))
        cards.append({
            "key": f"youtube:{channel_id}", "platform": "YouTube", "name": row["name"],
            "identity": channel_id, "handle": row.get("handle", ""),
            "url": f"https://www.youtube.com/channel/{channel_id}", "login_url": "https://studio.youtube.com/",
            "role": role if not profile else group, "description": profile.get("tone") or fallback,
            "state_label": "제작·업로드 연결 완료" if core_key else "계정 등록 · 제작 연결 확인 필요",
            "connection_level": "publish_connected" if core_key else "identity_verified",
            "publish_mode": "비공개 영상 제작 대기열에 1건 추가합니다. 자동 공개하지 않습니다." if core_key else "YouTube Studio 로그인 후 제작 프로필을 확인합니다.",
            "can_publish": bool(core_key), "channel_key": core_key or "", "action_kind": "youtube_queue" if core_key else "login",
            "button_label": "비공개 제작 시작" if core_key else "YouTube Studio 로그인",
        })
    return cards


def _sns_cards() -> list[dict]:
    policy = _read(SNS_POLICY, {})
    roles = {r.get("key"): r for r in policy.get("roles", [])}
    cards = []
    for row in policy.get("accounts", []):
        platform = row.get("platform", "")
        role = roles.get(row.get("role"), {})
        exists = bool(row.get("account_exists"))
        identity_ok = bool(row.get("identity_verified"))
        publish_ok = bool(row.get("publish_connected"))
        if publish_ok:
            state, level = "게시 권한 연결 완료", "publish_connected"
        elif identity_ok:
            state, level = "계정 확인 · 게시 로그인 필요", "identity_verified"
        elif exists:
            state, level = "계정 보임 · ID 확인 필요", "observed"
        else:
            state, level = "계정 미확인 · 로그인 후 확인", "missing"
        cards.append({
            "key": f"{platform.lower()}:{row.get('role')}", "platform": platform,
            "name": row.get("display_name") or role.get("name") or row.get("role"),
            "identity": f"@{row['handle']}" if row.get("handle") else "로그인 후 계정 ID 확인",
            "handle": row.get("handle", ""), "url": row.get("url", ""),
            "login_url": LOGIN_URLS.get(platform, ""), "role": role.get("name", row.get("role", "")),
            "description": role.get("topic", "플랫폼별 확정 주제 콘텐츠"), "state_label": state,
            "connection_level": level,
            "publish_mode": "이 계정으로 하루 1건 공개 발행할 수 있습니다." if publish_ok else "로그인 후 정확한 계정과 게시 권한을 확인합니다. 확인 전에는 공개하지 않습니다.",
            "can_publish": publish_ok, "channel_key": "", "action_kind": "sns_publish" if publish_ok else "login",
            "button_label": "즉시발행" if publish_ok else "로그인 · 계정 연결", "note": row.get("note", ""),
        })
    return cards


def _tistory_cards() -> list[dict]:
    cards = []
    for row in _read(TISTORY_CONFIG, {}).get("sites", []):
        cards.append({
            "key": f"tistory:{row['site_id']}", "platform": "Tistory", "name": row.get("title") or row.get("current_label") or row["site_id"],
            "identity": row["site_id"], "handle": "", "url": row.get("url", ""), "login_url": LOGIN_URLS["Tistory"],
            "role": " · ".join(row.get("categories", [])), "description": row.get("description", ""),
            "state_label": "로그인 완료 보고됨 · 로컬 등록기 연결 점검", "connection_level": "identity_verified",
            "publish_mode": "하루 1건 원고를 생성해 큐에 넣고, 기존 로그인 세션의 로컬 등록기가 공개 발행·재검증합니다.",
            "can_publish": True, "channel_key": "", "action_kind": "tistory_form", "button_label": "이 채널 원고 생성",
            "site_id": row["site_id"], "note": "2026-09-25 사용자 로그인 완료 보고. 실제 세션 만료/CAPTCHA가 확인될 때만 재로그인을 요청합니다.",
        })
    return cards


def _naver_cards() -> list[dict]:
    cards = []
    rooms = [r for r in _read(ROOMS_CONFIG, {}).get("rooms", []) if r.get("platform") == "naver"]
    for row in rooms:
        destination = str(row.get("destination_id") or "").strip()
        cards.append({
            "key": f"naver:{row['room_id']}", "platform": "Naver", "name": row.get("name") or row["room_id"],
            "identity": destination or f"{row['report_code']} · 로그인 후 블로그 ID 확인", "handle": "",
            "url": destination if destination.startswith("http") else "", "login_url": LOGIN_URLS["Naver"],
            "role": "네이버 블로그 독립 채널", "description": "계정별 원고·중복 방지·발행 이력을 독립 관리합니다.",
            "state_label": "기존 로그인 세션 · 블로그 ID 매핑 완료" if destination else "로그인 완료 보고됨 · 블로그 ID 매핑 필요",
            "connection_level": "identity_verified" if destination else "missing",
            "publish_mode": "기존 로그인 세션을 정확한 N1/N2/N3 블로그 ID에 연결한 뒤 하루 1건 공개 발행합니다.",
            "can_publish": False, "channel_key": "", "action_kind": "login", "button_label": "기존 로그인 세션 연결",
            "note": "다른 네이버 계정과 섞이지 않도록 N1·N2·N3를 서로 다른 로그인 프로필로 유지합니다.",
        })
    return cards


def _cards() -> list[dict]:
    return _youtube_cards() + _sns_cards() + _tistory_cards() + _naver_cards()


def install(app):
    @app.get("/social-accounts")
    def social_accounts():
        cards = _cards()
        platforms = ["전체", "YouTube", "TikTok", "Instagram", "Facebook", "Threads", "Tistory", "Naver"]
        selected = request.args.get("platform", "전체")
        if selected not in platforms:
            selected = "전체"
        visible = cards if selected == "전체" else [c for c in cards if c["platform"] == selected]
        counts = {p: sum(c["platform"] == p for c in cards) for p in platforms[1:]}
        connected = sum(c.get("connection_level") == "publish_connected" for c in cards)
        return render_template(
            "social_accounts.html", cards=visible, counts=counts, platforms=platforms,
            selected=selected, total=len(cards), connected=connected,
            csrf_token=app.config["CONTROL_CENTER_CSRF"],
        ), 200, {"Cache-Control": "no-store"}

    @app.post("/social-accounts/publish-now")
    def social_accounts_publish_now():
        payload = request.get_json(silent=True) or {}
        if not hmac.compare_digest(str(payload.get("csrf_token", "")), str(app.config["CONTROL_CENTER_CSRF"])):
            return jsonify(message="화면을 새로고침한 뒤 다시 눌러주세요."), 403
        card = next((c for c in _cards() if c["key"] == payload.get("account_key")), None)
        if not card:
            return jsonify(message="등록된 계정 카드가 아닙니다."), 404
        if card.get("action_kind") != "youtube_queue" or not card.get("can_publish"):
            return jsonify(message=f"{card['name']}: 로그인 및 실제 게시 권한 확인이 먼저 필요합니다. 아직 공개하지 않았습니다.", review_url=card.get("login_url") or card.get("url")), 409
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
