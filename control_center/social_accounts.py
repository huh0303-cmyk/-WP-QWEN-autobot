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
INVENTORY = ROOT / "config" / "london_social_account_inventory_2026-09-24.json"
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

YOUTUBE_GROUP_ORDER = {"language": 0, "playlist": 1, "knowledge": 2, "health": 3, "shopping": 4, "additional": 5}
YOUTUBE_GROUP_LABEL = {"language": "언어 Survival", "playlist": "플레이리스트", "knowledge": "지식", "health": "헬스", "shopping": "쇼핑·예약", "additional": "기타"}
YOUTUBE_LANGUAGE_ORDER = {
    "서울국제대학-TOPIK센터": 0, "German Survival": 1, "French Survival": 2,
    "Italian Survival": 3, "Spanish Survival": 4, "Chinese Survival": 5,
    "Portuguese Survival": 6, "Vietnamese Survival": 7,
    "English Survival": 8, "Japanese Survival": 9,
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
    for inventory_order, row in enumerate(inventory.get("youtube", [])):
        channel_id = row["channel_id"]
        profile = configured.get(channel_id, {})
        core_key = CORE_YOUTUBE.get(channel_id)
        group = profile.get("channel_type") or row.get("group") or "additional"
        role, fallback = ROLE_DETAILS.get(row["name"], (group, "채널별 확정 주제 콘텐츠"))
        group_label = YOUTUBE_GROUP_LABEL.get(group, group)
        operational_role = {
            "language": "언어별 Survival 콘텐츠 생산",
            "playlist": "음악·플레이리스트 영상 생산",
            "knowledge": "지식·아카이브 다큐 영상 생산",
            "health": "언어권별 건강정보 영상 생산",
            "shopping": "쇼핑·예약형 영상 생산",
        }.get(group, role)
        cards.append({
            "key": f"youtube:{channel_id}", "platform": "YouTube", "name": row["name"],
            "identity": channel_id, "handle": row.get("handle", ""),
            "url": f"https://www.youtube.com/channel/{channel_id}", "login_url": "https://studio.youtube.com/",
            "group": group, "group_label": group_label, "inventory_order": inventory_order, "role": operational_role,
            "description": profile.get("tone") or fallback,
            "state_label": "제작·즉시 공개 가능 · 채널 ID 검증 필수" if core_key else "채널 확인됨 · 업로드 로그인/권한 필요",
            "connection_level": "publish_connected" if core_key else "identity_verified",
            "publish_mode": "비공개 영상 제작 대기열에 1건 추가합니다. 자동 공개하지 않습니다." if core_key else "YouTube Studio 로그인 후 제작 프로필을 확인합니다.",
            "can_publish": bool(core_key), "channel_key": core_key or "", "action_kind": "youtube_queue" if core_key else "login",
            "button_label": "제작·바로 공개" if core_key else "YouTube Studio 로그인",
        })
    for row in inventory.get("unconfirmed", []):
        if row.get("platform") != "youtube":
            continue
        name = str(row.get("name") or "미확인 YouTube")
        language = name.removeprefix("Survival ")
        group = str(row.get("group") or ("language" if "Survival" in name else "additional"))
        cards.append({
            "key": f"youtube:unconfirmed:{name.lower().replace(' ', '-')}", "platform": "YouTube", "name": name,
            "identity": "정확한 UC ID 확인 필요", "handle": row.get("handle", ""), "url": "", "login_url": "https://studio.youtube.com/",
            "group": group, "group_label": YOUTUBE_GROUP_LABEL.get(group, group), "inventory_order": 100,
            "role": "언어별 Survival 콘텐츠 생산" if group == "language" else "다국어 쇼핑·상품소개 영상 생산" if group == "shopping" else "채널 역할 확인 필요",
            "description": f"{language} 초급 생존 회화와 생활 표현" if group == "language" else row.get("topic") or "UC ID 확인 후 역할과 자동화를 연결합니다.",
            "state_label": "Jisoo2 운영 매핑 · UC ID 확인 필요" if name == "Jisoo2" else "공개 핸들 확인 실패 · UC ID 필요", "connection_level": "missing",
            "publish_mode": "YouTube Studio에서 정확한 UC ID와 업로드 권한을 확인합니다.",
            "can_publish": False, "channel_key": "", "action_kind": "login", "button_label": "YouTube Studio에서 확인",
        })
    return sorted(cards, key=lambda c: (
        YOUTUBE_GROUP_ORDER.get(c.get("group"), 99),
        YOUTUBE_LANGUAGE_ORDER.get(c.get("name"), c.get("inventory_order", 999)) if c.get("group") == "language" else c.get("inventory_order", 999),
    ))


def _sns_cards() -> list[dict]:
    policy = _read(SNS_POLICY, {})
    roles = {r.get("key"): r for r in policy.get("roles", [])}
    cards = []
    for row in policy.get("accounts", []):
        platform = row.get("platform", "")
        if platform in {"Instagram", "Threads", "Facebook", "TikTok"} and row.get("role") not in {
            "korean_topik", "english", "japanese", "hot_item_shop"
        }:
            continue
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
            "group": "sns", "group_label": role.get("name", "SNS"),
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
            "state_label": "대상 확인 · 공개발행 영수증 검증 대기", "connection_level": "identity_verified",
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
            "state_label": "블로그 ID 연결 · 공개발행 영수증 검증 대기" if destination else "블로그 ID 매핑 필요",
            "connection_level": "identity_verified" if destination else "missing",
            "publish_mode": "기존 로그인 세션을 정확한 N1/N2/N3 블로그 ID에 연결한 뒤 하루 1건 공개 발행합니다.",
            "can_publish": False, "channel_key": "", "action_kind": "login", "button_label": "기존 로그인 세션 연결",
            "note": "다른 네이버 계정과 섞이지 않도록 N1·N2·N3를 서로 다른 로그인 프로필로 유지합니다.",
        })
    return cards


def _wordpress_cards(get_site_data) -> list[dict]:
    """Build WordPress cards from the same live metrics used by the main dashboard."""
    if get_site_data is None:
        return []
    sites = sorted(
        get_site_data(),
        key=lambda site: (
            site.get("today_visitors") is None,
            -(site.get("today_visitors") or 0),
            -(site.get("total_visitors") or 0),
            str(site.get("domain", "")),
        ),
    )
    cards = []
    for rank, site in enumerate(sites, 1):
        auth_ready = bool(site.get("auth_ready"))
        domain = str(site.get("domain", "")).strip()
        admin_url = site.get("admin_review_url") or f"https://{domain}/wp-admin/edit.php?post_status=draft&post_type=post"
        cards.append({
            "key": f"wordpress:{site['site_id']}", "platform": "WordPress", "name": domain,
            "identity": str(site["site_id"]), "handle": "", "url": f"https://{domain}",
            "login_url": admin_url, "admin_review_url": admin_url,
            "role": site.get("category") or "WordPress 독립 사이트",
            "description": (site.get("cadence") or {}).get("label") or "사이트별 주제에 맞춘 독립 원고",
            "state_label": "글쓰기·개별 발행 연결 완료" if auth_ready else "WordPress 인증 연결 필요",
            "connection_level": "publish_connected" if auth_ready else "missing",
            "publish_mode": "이미지 1장을 기본값으로 검토용 초안을 만들고, 확인 후 이 사이트만 개별 발행합니다.",
            "can_publish": auth_ready, "channel_key": "", "action_kind": "wordpress_forms" if auth_ready else "login",
            "button_label": "① 글쓰기 트리거", "site_id": site["site_id"],
            "today_visitors": site.get("today_visitors"), "total_visitors": site.get("total_visitors"),
            "rank": rank, "image_count_default": 1,
            "note": "오늘 방문자 수 내림차순이며 미집계 사이트는 맨 아래에 표시됩니다.",
        })
    return cards


def _cards(get_site_data=None) -> list[dict]:
    return _wordpress_cards(get_site_data) + _youtube_cards() + _sns_cards() + _tistory_cards() + _naver_cards()


def install(app, get_site_data=None):
    @app.get("/social-accounts")
    def social_accounts():
        cards = _cards(get_site_data)
        media_platforms = {"YouTube", "TikTok", "Instagram", "Facebook", "Threads"}
        media_order = {"YouTube": 0, "Facebook": 1, "Threads": 2, "Instagram": 3, "TikTok": 4}
        media_cards = sorted(
            (c for c in cards if c["platform"] in media_platforms),
            key=lambda c: (media_order.get(c["platform"], 99), str(c.get("name") or "").casefold()),
        )
        platforms = ["전체", "로그인·권한 필요", "YouTube", "Facebook", "Threads", "Instagram", "TikTok"]
        selected = request.args.get("platform", "전체")
        # Legacy subdomain roots still send SNS/YouTube; both now open the
        # owner's single combined media sheet instead of separate products.
        if selected in {"SNS", "통합"} or (selected == "YouTube" and request.host.split(":", 1)[0].lower() == "youtube.korea365.org"):
            selected = "전체"
        if selected not in platforms:
            selected = "전체"
        if selected == "전체":
            visible = media_cards
        elif selected == "로그인·권한 필요":
            visible = [c for c in media_cards if c.get("connection_level") != "publish_connected"]
        else:
            visible = [c for c in media_cards if c["platform"] == selected]
        counts = {p: sum(c["platform"] == p for c in media_cards) for p in platforms[2:]}
        counts["전체"] = len(media_cards)
        counts["로그인·권한 필요"] = sum(c.get("connection_level") != "publish_connected" for c in media_cards)
        connected = sum(c.get("connection_level") == "publish_connected" for c in media_cards)
        return render_template(
            "social_accounts.html", cards=visible, counts=counts, platforms=platforms,
            selected=selected, total=len(media_cards), connected=connected,
            csrf_token=app.config["CONTROL_CENTER_CSRF"],
        ), 200, {"Cache-Control": "no-store"}

    @app.post("/social-accounts/publish-now")
    def social_accounts_publish_now():
        payload = request.get_json(silent=True) or {}
        if not hmac.compare_digest(str(payload.get("csrf_token", "")), str(app.config["CONTROL_CENTER_CSRF"])):
            return jsonify(message="화면을 새로고침한 뒤 다시 눌러주세요."), 403
        card = next((c for c in _cards(get_site_data) if c["key"] == payload.get("account_key")), None)
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
                "conclusion": None, "reason": "VPS 제작·즉시 공개 대기"}
        _write_state(group, {"status": "polling", "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None, "items": [item]})
        return jsonify(message=f"{card['name']}: 비공개 영상 제작을 접수했습니다. 자동 공개하지 않습니다.", job_id=job["job_id"]), 202
