from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


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


def install(app, runtime):
    project_root = Path(__file__).resolve().parents[1]

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
                "naver": {"total": _naver_expected(project_root), "ready": None, "issues": None},
                "youtube": youtube_state,
                "sns": {"total": len(sns), "ready": None, "issues": None},
            },
            "pipeline": [
                {"id": "research", "label": "Research", "purpose": "주제·근거 조사"},
                {"id": "writer", "label": "Writer", "purpose": "플랫폼별 원고 작성"},
                {"id": "review", "label": "Review", "purpose": "사실·중복·정책 검수"},
                {"id": "image", "label": "Image", "purpose": "필요 시 이미지 생성"},
                {"id": "publish", "label": "Publish", "purpose": "API/브라우저 발행"},
                {"id": "verify", "label": "Verify", "purpose": "공개 URL·영수증 검증"},
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

    return snapshot
