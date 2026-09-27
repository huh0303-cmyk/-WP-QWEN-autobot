from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import secrets
import threading

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = PROJECT_ROOT / "data" / "london-pipeline"
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
    """OWNER-LOCKED 24-site category master."""
    payload = json.loads(
        (PROJECT_ROOT / "config" / "WP24_CATEGORY_MASTER.json").read_text(encoding="utf-8")
    )
    return {
        "https://" + str(row["domain"]).strip().lower(): [str(x) for x in row.get("categories", [])]
        for row in payload.get("sites", [])
        if row.get("domain")
    }


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
        return {"run_id": run_id, "stage_status": {}, "message": "실행 대기"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"run_id": run_id, "stage_status": {}, "last_error": {"message": str(exc)}}


def _write_run(state: dict) -> None:
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    path = _state_file(str(state.get("run_id") or ""))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _gateway_call(stage: str, run_id: str) -> None:
    """Run exactly one visible agent in background."""
    state = _read_run(run_id)
    token = os.environ.get("N8N_GATEWAY_TOKEN", "").strip()
    if not token:
        state.setdefault("stage_status", {})[stage] = "failed"
        state["last_error"] = {
            "stage": stage,
            "type": "ConfigurationError",
            "message": "N8N_GATEWAY_TOKEN is missing on the VPS",
            "at": datetime.now(timezone.utc).isoformat(),
        }
        _write_run(state)
        return
    body = {
        "run_id": run_id,
        "site_id": str(state.get("site_id") or ""),
        "category": str(state.get("category") or ""),
        "publish_mode": str(state.get("publish_mode") or "draft"),
    }
    try:
        response = requests.post(
            f"{GATEWAY}/pipeline/{stage}",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
            timeout=330,
        )
        if response.status_code >= 400:
            latest = _read_run(run_id)
            if latest.get("stage_status", {}).get(stage) != "failed":
                latest.setdefault("stage_status", {})[stage] = "failed"
                latest["last_error"] = {
                    "stage": stage,
                    "type": "GatewayStageError",
                    "message": response.text[:1200],
                    "at": datetime.now(timezone.utc).isoformat(),
                }
                _write_run(latest)
    except requests.RequestException as exc:
        latest = _read_run(run_id)
        latest.setdefault("stage_status", {})[stage] = "failed"
        latest["last_error"] = {
            "stage": stage,
            "type": type(exc).__name__,
            "message": str(exc)[:1200],
            "at": datetime.now(timezone.utc).isoformat(),
        }
        _write_run(latest)


def _start_stage(stage: str, run_id: str) -> None:
    threading.Thread(target=_gateway_call, args=(stage, run_id), daemon=True).start()


def _run_sequence(run_id: str, start_stage: str = "research") -> None:
    """Run 1→2→3→4 automatically. Stop exactly at the failed agent."""
    stages = ["research", "write", "image", "publish"]
    try:
        start_index = stages.index(start_stage)
    except ValueError:
        start_index = 0
    for stage in stages[start_index:]:
        state = _read_run(run_id)
        state.setdefault("stage_status", {})[stage] = "running"
        state.pop("last_error", None)
        _write_run(state)
        _gateway_call(stage, run_id)
        state = _read_run(run_id)
        if state.get("stage_status", {}).get(stage) != "ok":
            return


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
                {"id": "research", "label": "1. 키워드/주제어", "purpose": "Google·Naver·미디어·GSC 리서치 후 주제 확정"},
                {"id": "write", "label": "2. 글쓰기", "purpose": "확정 키워드로 사이트 페르소나·톤·언어에 맞춰 작성"},
                {"id": "image", "label": "3. 이미지", "purpose": "필요 시 0~1장 생성·검증"},
                {"id": "publish", "label": "4. 발행", "purpose": "선택 카테고리로 발행 후 URL·post ID 검증"},
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
        state = {
            "run_id": run_id,
            "site_id": site_id,
            "platform": "wordpress",
            "category": category,
            "publish_mode": publish_mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stage_status": {
                "research": "waiting",
                "write": "waiting",
                "image": "waiting",
                "publish": "waiting",
            },
        }
        _write_run(state)
        threading.Thread(target=_run_sequence, args=(run_id, "research"), daemon=True).start()
        return jsonify({"ok": True, "run_id": run_id, "mode": "auto-1-2-3-4"}), 202

    @app.post("/api/london-gpt/research")
    def london_gpt_research():
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
        state = {
            "run_id": run_id,
            "site_id": site_id,
            "platform": "wordpress",
            "category": category,
            "publish_mode": publish_mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stage_status": {
                "research": "running",
                "write": "waiting",
                "image": "waiting",
                "publish": "waiting",
            },
        }
        _write_run(state)
        _start_stage("research", run_id)
        return jsonify({"ok": True, "run_id": run_id, "stage": "research"}), 202

    @app.post("/api/london-gpt/keyword")
    def london_gpt_keyword():
        from flask import jsonify, request
        payload = request.get_json(silent=True) or {}
        run_id = str(payload.get("run_id") or "").strip()
        keyword = str(payload.get("keyword") or "").strip()
        if not run_id or not 3 <= len(keyword) <= 80:
            return jsonify({"ok": False, "error": "invalid_keyword"}), 400
        state = _read_run(run_id)
        if state.get("stage_status", {}).get("research") != "ok":
            return jsonify({"ok": False, "error": "research_not_complete"}), 409
        state.setdefault("research", {})["keyword"] = keyword
        state["research"]["keyword_confirmed"] = True
        _write_run(state)
        return jsonify({"ok": True, "run_id": run_id, "keyword": keyword})

    @app.post("/api/london-gpt/stage/<stage>")
    def london_gpt_stage(stage: str):
        from flask import jsonify, request
        if stage not in {"write", "image", "publish"}:
            return jsonify({"ok": False, "error": "unknown_stage"}), 404
        payload = request.get_json(silent=True) or {}
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            return jsonify({"ok": False, "error": "run_id_required"}), 400
        state = _read_run(run_id)
        required = {"write": "research", "image": "write", "publish": "image"}[stage]
        if state.get("stage_status", {}).get(required) != "ok":
            return jsonify({"ok": False, "error": f"{required}_not_complete"}), 409
        if stage == "write" and not str(state.get("research", {}).get("keyword") or "").strip():
            return jsonify({"ok": False, "error": "keyword_required"}), 409

        state.setdefault("stage_status", {})[stage] = "running"
        state.pop("last_error", None)
        _write_run(state)
        _start_stage(stage, run_id)
        return jsonify({"ok": True, "run_id": run_id, "stage": stage}), 202

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
        state.setdefault("stage_status", {})[stage] = "waiting"
        state.pop("last_error", None)
        _write_run(state)
        threading.Thread(target=_run_sequence, args=(run_id, stage), daemon=True).start()
        return jsonify({"ok": True, "run_id": run_id, "stage": stage, "continues_to_finish": True}), 202

    return snapshot
