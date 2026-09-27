from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import secrets

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = PROJECT_ROOT / "data" / "london-pipeline"
N8N_WEBHOOK = os.environ.get(
    "LONDON_GPT_N8N_WEBHOOK",
    "http://127.0.0.1:5678/webhook/london-content-four-agent",
)
GATEWAY = os.environ.get("LONDON_GPT_GATEWAY", "http://127.0.0.1:8766").rstrip("/")


def _safe_call(fn, fallback):
    try:
        return fn()
    except Exception:
        return fallback


def _count_status(rows, key):
    total = len(rows)
    ready = sum(1 for row in rows if bool(row.get(key) if isinstance(row, dict) else getattr(row, key, False)))
    return {"total": total, "ready": ready, "issues": max(total - ready, 0)}


def _naver_expected(project_root: Path) -> int:
    path = project_root / "config" / "london_social_account_inventory_2026-09-24.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(payload, ensure_ascii=False).lower()
        count = text.count('"platform": "naver"') + text.count('"platform":"naver"')
        return count or 3
    except Exception:
        return 3


def _categories_by_url() -> dict[str, list[str]]:
    source = (PROJECT_ROOT / "scripts" / "refresh_keyword_pool.py").read_text(encoding="utf-8")
    pattern = re.compile(
        r'\{"url":\s*"([^"]+)"[\s\S]*?"categories":\s*\[([^\]]*)\][\s\S]*?"lang":\s*"([^"]+)"\}'
    )
    out: dict[str, list[str]] = {}
    for match in pattern.finditer(source):
        url = match.group(1).rstrip("/")
        categories = re.findall(r'"([^"]+)"', match.group(2))
        out[url] = categories
    return out


def _content_sites() -> list[dict]:
    categories = _categories_by_url()
    profiles = json.loads(
        (PROJECT_ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8")
    ).get("profiles", [])
    by_url = {}
    for profile in profiles:
        wp = profile.get("wordpress") or {}
        url = str(wp.get("url") or "").rstrip("/")
        if not url or url not in categories or url in by_url:
            continue
        by_url[url] = {
            "site_key": profile.get("site_key", ""),
            "site_id": f"wp_{profile.get('site_key','')}",
            "url": url,
            "language": profile.get("language", "en"),
            "persona": wp.get("persona", ""),
            "tone": wp.get("tone", ""),
            "theme": wp.get("theme", ""),
            "categories": categories[url],
            "min_chars": wp.get("min_chars", 1800),
            "target_chars": wp.get("target_chars", 2400),
            "max_chars": wp.get("max_chars", 3200),
        }
    return [by_url[url] for url in categories if url in by_url]


def _state_file(run_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", run_id)
    return PIPELINE_DIR / f"{safe}.json"


def _read_run(run_id: str) -> dict:
    path = _state_file(run_id)
    if not path.exists():
        return {
            "run_id": run_id,
            "stage_status": {},
            "message": "n8n 시작 대기",
        }
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"run_id": run_id, "stage_status": {}, "last_error": {"message": str(exc)}}
    return state


def install(app, runtime):
    def snapshot():
        wp = _safe_call(runtime.get_site_data, [])
        blogger = _safe_call(runtime.get_blogger_data, [])
        tistory = _safe_call(runtime.get_tistory_data, [])
        youtube = _safe_call(runtime.get_youtube_data, [])
        sns = _safe_call(runtime.get_sns_data, [])

        wp_state = _count_status(wp, "auth_ready")
        blogger_state = _count_status(blogger, "connected")
        youtube_state = _count_status(youtube, "action_ready")
        tistory_state = {
            "total": len(tistory),
            "ready": sum(1 for row in tistory if bool(row.get("connected") if isinstance(row, dict) else getattr(row, "connected", False))),
        }
        tistory_state["issues"] = max(tistory_state["total"] - tistory_state["ready"], 0)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "platforms": {
                "wordpress": wp_state,
                "blogger": blogger_state,
                "tistory": tistory_state,
                "naver": {"total": _naver_expected(PROJECT_ROOT), "ready": None, "issues": None},
                "youtube": youtube_state,
                "sns": {"total": len(sns), "ready": None, "issues": None},
            },
            "sites": _content_sites(),
            "pipeline": [
                {"id": "research", "label": "1. 키워드 리서치", "purpose": "Google·Naver·미디어·GSC 조사 후 주제 확정"},
                {"id": "write", "label": "2. 글쓰기", "purpose": "사이트 페르소나·톤·언어·길이에 맞춰 원고 생성"},
                {"id": "image", "label": "3. 이미지 생성", "purpose": "필요 시 0~1장 생성·검증·안정화"},
                {"id": "publish", "label": "4. 발행·검증", "purpose": "WordPress/Blogger 발행 후 URL·post ID 영수증 확인"},
            ],
        }

    @app.get("/london-gpt")
    def london_gpt_home():
        from flask import render_template
        return render_template("london_gpt.html", snapshot=snapshot())

    @app.get("/api/london-gpt/status")
    def london_gpt_status():
        from flask import jsonify
        return jsonify(snapshot())

    @app.post("/api/london-gpt/run")
    def london_gpt_run():
        from flask import jsonify, request
        payload = request.get_json(silent=True) or {}
        site_id = str(payload.get("site_id") or "").strip()
        category = str(payload.get("category") or "").strip()
        publish_mode = str(payload.get("publish_mode") or "draft").strip().lower()
        valid = {site["site_id"]: site for site in _content_sites()}
        if site_id not in valid:
            return jsonify({"ok": False, "error": "unknown_site"}), 400
        if category and category not in valid[site_id]["categories"]:
            return jsonify({"ok": False, "error": "invalid_category"}), 400
        if publish_mode not in {"draft", "publish"}:
            return jsonify({"ok": False, "error": "invalid_publish_mode"}), 400
        run_id = f"lgpt-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"
        request_body = {
            "site_id": site_id,
            "category": category,
            "publish_mode": publish_mode,
            "run_id": run_id,
        }
        try:
            response = requests.post(N8N_WEBHOOK, json=request_body, timeout=8)
        except requests.RequestException as exc:
            return jsonify({"ok": False, "error": "n8n_unreachable", "message": str(exc), "run_id": run_id}), 503
        if response.status_code >= 400:
            return jsonify({
                "ok": False,
                "error": "n8n_rejected",
                "http": response.status_code,
                "message": response.text[:500],
                "run_id": run_id,
            }), 502
        return jsonify({"ok": True, "run_id": run_id, "site_id": site_id, "category": category, "publish_mode": publish_mode})

    @app.get("/api/london-gpt/run/<run_id>")
    def london_gpt_run_status(run_id: str):
        from flask import jsonify
        return jsonify(_read_run(run_id))

    @app.post("/api/london-gpt/rerun/<stage>")
    def london_gpt_rerun(stage: str):
        from flask import jsonify, request
        if stage not in {"research", "write", "image", "publish"}:
            return jsonify({"ok": False, "error": "unknown_stage"}), 404
        payload = request.get_json(silent=True) or {}
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            return jsonify({"ok": False, "error": "run_id_required"}), 400
        state = _read_run(run_id)
        site_id = str(state.get("site_id") or "")
        category = str(state.get("category") or "")
        publish_mode = str(state.get("publish_mode") or "draft")
        token = os.environ.get("N8N_GATEWAY_TOKEN", "").strip()
        if not token:
            return jsonify({"ok": False, "error": "gateway_token_missing"}), 503
        body = {
            "run_id": run_id,
            "site_id": site_id,
            "category": category,
            "publish_mode": publish_mode,
        }
        try:
            response = requests.post(
                f"{GATEWAY}/pipeline/{stage}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=330,
            )
        except requests.RequestException as exc:
            return jsonify({"ok": False, "error": "gateway_unreachable", "message": str(exc)}), 503
        try:
            data = response.json()
        except ValueError:
            data = {"ok": False, "message": response.text[:500]}
        return jsonify(data), response.status_code

    return snapshot
