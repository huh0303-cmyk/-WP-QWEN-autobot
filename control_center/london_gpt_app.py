from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import html
import io
import os
import re
import secrets
import threading
from urllib.parse import urlparse

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = PROJECT_ROOT / "data" / "london-pipeline"
N8N_WEBHOOK = os.environ.get(
    "LONDON_GPT_N8N_WEBHOOK",
    "http://127.0.0.1:5678/webhook/london-content-four-agent",
)
N8N_REWRITE_WEBHOOK = os.environ.get(
    "LONDON_GPT_N8N_REWRITE_WEBHOOK",
    "http://127.0.0.1:5678/webhook/london-content-rewrite",
)
N8N_RERUN_WEBHOOKS = {
    "research": os.environ.get("LONDON_GPT_N8N_RERUN_RESEARCH", "http://127.0.0.1:5678/webhook/london-content-rerun-research"),
    "write": os.environ.get("LONDON_GPT_N8N_RERUN_WRITE", "http://127.0.0.1:5678/webhook/london-content-rerun-write"),
    "image": os.environ.get("LONDON_GPT_N8N_RERUN_IMAGE", "http://127.0.0.1:5678/webhook/london-content-rerun-image"),
    "publish": os.environ.get("LONDON_GPT_N8N_RERUN_PUBLISH", "http://127.0.0.1:5678/webhook/london-content-rerun-publish"),
}
GATEWAY = os.environ.get("LONDON_GPT_GATEWAY", "http://127.0.0.1:8766").rstrip("/")
WRITER_MODELS = {"auto_free", "local_qwen", "gpt-5-mini", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite"}
IMAGE_MODELS = {"auto_free", "pexels", "pixabay", "wikimedia", "none"}


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
    payload = json.loads(
        (PROJECT_ROOT / "config" / "WP24_CATEGORY_MASTER.json").read_text(encoding="utf-8")
    )
    return {
        "https://" + str(row["domain"]).strip().lower(): [str(x) for x in row.get("categories", [])]
        for row in payload.get("sites", [])
        if row.get("domain")
    }


def _content_sites() -> list[dict]:
    from scripts.london_site_catalog import content_sites
    return content_sites()


def _state_file(run_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", run_id)
    return PIPELINE_DIR / f"{safe}.json"


def _read_run(run_id: str) -> dict:
    path = _state_file(run_id)
    if not path.exists():
        return {"run_id": run_id, "stage_status": {}, "message": "n8n 시작 대기"}
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


def _rerun_stage(stage: str, run_id: str) -> None:
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
                {"id": "publish", "label": "4. 발행·검증", "purpose": "선택 카테고리로 발행 후 URL·post ID 검증"},
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
        writer_model = str(payload.get("writer_model") or "auto_free").strip()
        image_model = str(payload.get("image_model") or "auto_free").strip()
        if writer_model not in WRITER_MODELS or image_model not in IMAGE_MODELS:
            return jsonify({"ok": False, "error": "invalid_model_choice"}), 400
        valid = {site["site_id"]: site for site in _content_sites()}
        if site_id not in valid or not valid[site_id].get("enabled", True):
            return jsonify({"ok": False, "error": "unknown_site"}), 400
        if category and category not in valid[site_id]["categories"]:
            return jsonify({"ok": False, "error": "invalid_category"}), 400
        if publish_mode not in {"draft", "publish", "manual"}:
            return jsonify({"ok": False, "error": "invalid_publish_mode"}), 400
        if not valid[site_id].get("auto_publish", True) and publish_mode != "manual":
            return jsonify({"ok": False, "error": "manual_mode_required_for_platform"}), 400

        run_id = f"lgpt-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"
        state = {
            "run_id": run_id,
            "site_id": site_id,
            "platform": valid[site_id].get("platform", "wordpress"),
            "category": category,
            "publish_mode": publish_mode,
            "writer_model": writer_model,
            "image_model": image_model,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "orchestrator": "n8n",
            "stage_status": {
                "research": "waiting",
                "write": "waiting",
                "image": "waiting",
                "publish": "waiting",
            },
        }
        _write_run(state)

        try:
            response = requests.post(
                N8N_WEBHOOK,
                json={
                    "site_id": site_id,
                    "category": category,
                    "publish_mode": publish_mode,
                    "run_id": run_id,
                },
                timeout=12,
            )
        except requests.RequestException as exc:
            state["last_error"] = {
                "stage": "start",
                "type": type(exc).__name__,
                "message": str(exc)[:1200],
                "at": datetime.now(timezone.utc).isoformat(),
            }
            _write_run(state)
            return jsonify({"ok": False, "error": "n8n_unreachable", "message": str(exc), "run_id": run_id}), 503

        if response.status_code >= 400:
            state["last_error"] = {
                "stage": "start",
                "type": "N8NWebhookError",
                "message": response.text[:1200],
                "at": datetime.now(timezone.utc).isoformat(),
            }
            _write_run(state)
            return jsonify({"ok": False, "error": "n8n_rejected", "http": response.status_code, "run_id": run_id}), 502

        return jsonify({"ok": True, "run_id": run_id, "orchestrator": "n8n", "mode": "manual-1-2-3" if publish_mode == "manual" else "auto-1-2-3-4"}), 202

    @app.post("/api/london-gpt/manual-published")
    def london_gpt_manual_published():
        from flask import jsonify, request
        payload = request.get_json(silent=True) or {}
        run_id = str(payload.get("run_id") or "").strip()
        public_url = str(payload.get("url") or "").strip()
        if not re.fullmatch(r"lgpt-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}", run_id):
            return jsonify({"ok": False, "error": "invalid_run_id"}), 400
        if not _state_file(run_id).is_file():
            return jsonify({"ok": False, "error": "unknown_run"}), 404
        state = _read_run(run_id)
        if state.get("publish_mode") != "manual":
            return jsonify({"ok": False, "error": "not_manual_run"}), 409
        if state.get("stage_status", {}).get("publish") != "manual_required":
            return jsonify({"ok": False, "error": "manual_handoff_not_ready"}), 409
        site = next((item for item in _content_sites() if item["site_id"] == state.get("site_id")), None)
        if not site:
            return jsonify({"ok": False, "error": "unknown_site"}), 400
        parsed = urlparse(public_url)
        expected = urlparse(site["url"])
        naver_parts = [part for part in parsed.path.split("/") if part]
        naver_post = (site.get("platform", "wordpress") == "naver" and parsed.hostname in {"blog.naver.com", "m.blog.naver.com"}
                      and len(naver_parts) >= 2 and naver_parts[0] == expected.path.strip("/")
                      and naver_parts[1].isdigit())
        same_site_post = parsed.hostname == expected.hostname and bool(parsed.path.strip("/"))
        if (parsed.scheme != "https" or not (naver_post if site.get("platform", "wordpress") == "naver" else same_site_post)
                or parsed.port not in (None, 443) or parsed.username or parsed.password):
            return jsonify({"ok": False, "error": "url_must_be_post_on_selected_site"}), 400
        try:
            response = requests.get(public_url, timeout=20, allow_redirects=False)
        except requests.RequestException as exc:
            return jsonify({"ok": False, "error": "public_page_unreachable", "message": str(exc)[:250]}), 502
        if response.status_code != 200 or "html" not in response.headers.get("content-type", "").lower():
            return jsonify({"ok": False, "error": "public_page_not_verified", "http": response.status_code}), 409
        title = str(state.get("article", {}).get("title") or "").strip()
        page_text = re.sub(r"<[^>]+>", " ", html.unescape(response.text))
        if title and site.get("platform") == "naver" and re.sub(r"\s+", " ", title).casefold() not in re.sub(r"\s+", " ", page_text).casefold():
            # Desktop Naver pages can be iframe shells; inspect the same post's mobile view.
            mobile_url = f"https://m.blog.naver.com/{naver_parts[0]}/{naver_parts[1]}"
            try:
                mobile = requests.get(mobile_url, timeout=20, allow_redirects=False)
                if mobile.status_code == 200 and "html" in mobile.headers.get("content-type", "").lower():
                    page_text = re.sub(r"<[^>]+>", " ", html.unescape(mobile.text))
            except requests.RequestException:
                pass
        if not title or re.sub(r"\s+", " ", title).casefold() not in re.sub(r"\s+", " ", page_text).casefold():
            return jsonify({"ok": False, "error": "article_title_not_found_on_public_page"}), 409
        state["receipt"] = {"status": "published_verified", "platform": site.get("platform", "wordpress"), "url": public_url,
                            "post_id": "manual", "title": title, "verified_at": datetime.now(timezone.utc).isoformat()}
        state["stage_status"]["publish"] = "ok"
        state["completed_at"] = datetime.now(timezone.utc).isoformat()
        if site.get("platform", "wordpress") in {"wordpress", "blogger"}:
            from scripts.london_gsc_dispatch import queue_submission
            queue_submission(state, site["url"])
        else:
            state["indexing_submission"] = {"status": "not_applicable", "url": public_url,
                                           "reason": "이 플랫폼은 GSC 사이트맵 자동 제출 대상이 아닙니다."}
        _write_run(state)
        return jsonify({"ok": True, "receipt": state["receipt"]})

    @app.post("/api/london-gpt/rewrite")
    def london_gpt_rewrite():
        from flask import jsonify, request
        payload = request.get_json(silent=True) or {}
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            return jsonify({"ok": False, "error": "run_id_required"}), 400

        state = _read_run(run_id)
        if state.get("stage_status", {}).get("research") != "ok":
            return jsonify({"ok": False, "error": "research_not_complete"}), 409
        if not str(state.get("research", {}).get("keyword") or "").strip():
            return jsonify({"ok": False, "error": "keyword_missing"}), 409

        state.setdefault("stage_status", {})["write"] = "waiting"
        state["stage_status"]["image"] = "waiting"
        state["stage_status"]["publish"] = "waiting"
        if state.get("article"):
            state["previous_article"] = state.get("article")
        if state.get("writer"):
            state["previous_writer"] = state.get("writer")
        state.pop("image", None)
        state.pop("receipt", None)
        state.pop("last_error", None)
        state["rewrite_requested_at"] = datetime.now(timezone.utc).isoformat()
        _write_run(state)

        try:
            response = requests.post(
                N8N_REWRITE_WEBHOOK,
                json={
                    "site_id": str(state.get("site_id") or ""),
                    "category": str(state.get("category") or ""),
                    "publish_mode": str(state.get("publish_mode") or "draft"),
                    "run_id": run_id,
                },
                timeout=12,
            )
        except requests.RequestException as exc:
            return jsonify({"ok": False, "error": "n8n_rewrite_unreachable", "message": str(exc)}), 503
        if response.status_code >= 400:
            return jsonify({"ok": False, "error": "n8n_rewrite_rejected", "http": response.status_code}), 502
        return jsonify({"ok": True, "run_id": run_id, "mode": "rewrite-2-3-4"}), 202

    @app.get("/api/london-gpt/run/<run_id>")
    def london_gpt_run_status(run_id: str):
        from flask import jsonify
        state = _read_run(run_id)
        if re.fullmatch(r"lgpt-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}", run_id):
            receipt_path = PROJECT_ROOT / "data" / "london-gsc-receipts" / f"{run_id}.json"
            if receipt_path.is_file():
                try:
                    submission = json.loads(receipt_path.read_text(encoding="utf-8"))
                    if submission.get("url") == (state.get("receipt") or {}).get("url"):
                        state["indexing_submission"] = submission
                except (OSError, ValueError):
                    pass
        return jsonify(state)

    @app.get("/api/london-gpt/image/<run_id>")
    def london_gpt_copy_image(run_id: str):
        from flask import jsonify, send_file
        if not re.fullmatch(r"lgpt-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}", run_id):
            return jsonify({"error": "invalid_run_id"}), 400
        image_url = str((_read_run(run_id).get("image") or {}).get("url") or "")
        parsed = urlparse(image_url)
        host = (parsed.hostname or "").lower()
        allowed = ("images.pexels.com", "pixabay.com", "i.pximg.net", "raw.githubusercontent.com", "replicate.delivery", "pbxt.replicate.delivery")
        if parsed.scheme != "https" or parsed.port not in (None, 443) or host not in allowed:
            return jsonify({"error": "image_unavailable"}), 404
        try:
            with requests.get(image_url, stream=True, timeout=20, allow_redirects=False) as response:
                if response.status_code != 200:
                    return jsonify({"error": "image_unavailable"}), 404
                kind = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if kind not in {"image/png", "image/jpeg", "image/webp"}:
                    return jsonify({"error": "unsupported_image"}), 415
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 10_000_000:
                        return jsonify({"error": "image_too_large"}), 413
                    chunks.append(chunk)
        except requests.RequestException:
            return jsonify({"error": "image_unavailable"}), 502
        return send_file(io.BytesIO(b"".join(chunks)), mimetype=kind, max_age=0)

    @app.post("/api/london-gpt/rerun/<stage>")
    def london_gpt_rerun(stage: str):
        from flask import jsonify, request
        if stage not in N8N_RERUN_WEBHOOKS:
            return jsonify({"ok": False, "error": "unknown_stage"}), 404
        payload = request.get_json(silent=True) or {}
        run_id = str(payload.get("run_id") or "").strip()
        if not run_id:
            return jsonify({"ok": False, "error": "run_id_required"}), 400

        state = _read_run(run_id)
        if state.get("publish_mode") == "manual" and stage == "publish":
            return jsonify({"ok": False, "error": "publish_is_manual"}), 409
        state.setdefault("stage_status", {})[stage] = "waiting"
        state.pop("last_error", None)
        _write_run(state)

        body = {
            "run_id": run_id,
            "site_id": str(state.get("site_id") or ""),
            "category": str(state.get("category") or ""),
            "publish_mode": str(state.get("publish_mode") or "draft"),
        }
        try:
            response = requests.post(N8N_RERUN_WEBHOOKS[stage], json=body, timeout=12)
        except requests.RequestException as exc:
            return jsonify({"ok": False, "error": "n8n_rerun_unreachable", "message": str(exc)}), 503
        if response.status_code >= 400:
            return jsonify({"ok": False, "error": "n8n_rerun_rejected", "http": response.status_code}), 502
        return jsonify({"ok": True, "run_id": run_id, "stage": stage, "orchestrator": "n8n"}), 202

    return snapshot
